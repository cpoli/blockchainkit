"""Arithmetic circuits and rank-1 constraint systems (R1CS).

SNARKs prove statements written as arithmetic over a prime field. A rank-1
constraint system lists constraints of the form

    <a_j, z> * <b_j, z> = <c_j, z>,

over a witness vector z = (1, public inputs, private values). Additions
and multiplications by constants are free: they only change the linear
combinations. Each multiplication of two unknowns costs one constraint.

:class:`Circuit` builds an R1CS while computing the witness: a
:class:`Wire` is a linear combination of variables that also carries its
value, so ``x * x * x + x + 5`` written with :meth:`Circuit.mul` produces
both the constraints and the satisfying assignment.
"""

from __future__ import annotations

from blockchainkit.proofs.core.base import R1CS
from blockchainkit.proofs.utils.polynomials import FIELD_PRIME, _check_prime


class Wire:
    """A linear combination of circuit variables, and its value in the current witness.

    Wires support ``+``, ``-``, negation, and multiplication by an integer
    constant. Multiplying two wires is a constraint: use :meth:`Circuit.mul`.
    """

    __slots__ = ("prime", "terms", "value")

    def __init__(self, terms: dict[int, int], value: int, prime: int) -> None:
        self.terms = {i: c % prime for i, c in terms.items() if c % prime}
        self.value = value % prime
        self.prime = prime

    def __repr__(self) -> str:
        return f"Wire(value={self.value}, terms={self.terms})"

    def _as_wire(self, other: object) -> Wire | None:
        if isinstance(other, Wire):
            if other.prime != self.prime:
                raise ValueError("wires belong to circuits over different fields")
            return other
        if type(other) is int:
            return Wire({0: other}, other, self.prime)
        return None

    def __add__(self, other: Wire | int) -> Wire:
        right = self._as_wire(other)
        if right is None:
            return NotImplemented
        terms = dict(self.terms)
        for i, c in right.terms.items():
            terms[i] = terms.get(i, 0) + c
        return Wire(terms, self.value + right.value, self.prime)

    __radd__ = __add__

    def __neg__(self) -> Wire:
        return self * -1

    def __sub__(self, other: Wire | int) -> Wire:
        right = self._as_wire(other)
        if right is None:
            return NotImplemented
        return self + -right

    def __rsub__(self, other: int) -> Wire:
        return -self + other

    def __mul__(self, other: int) -> Wire:
        if type(other) is not int:
            if isinstance(other, Wire):
                raise TypeError("multiplying two wires is a constraint: use Circuit.mul")
            return NotImplemented
        return Wire({i: c * other for i, c in self.terms.items()}, self.value * other, self.prime)

    __rmul__ = __mul__


class Circuit:
    """Build an R1CS and its witness together.

    Declare every public input first, then private inputs and gates. The
    witness vector is ``(1, public..., private...)``.

    Parameters
    ----------
    prime : int
        Field modulus; defaults to the BabyBear prime, the scalar field of
        :data:`~blockchainkit.proofs.systems.pairing.PAIRING_CURVE`.

    Examples
    --------
    >>> from blockchainkit.proofs import Circuit
    >>> circuit = Circuit()
    >>> out = circuit.public(35)
    >>> x = circuit.private(3)
    >>> x3 = circuit.mul(circuit.mul(x, x), x)
    >>> circuit.assert_equal(x3 + x + 5, out)
    >>> r1cs = circuit.r1cs()
    >>> r1cs.num_constraints, r1cs.is_satisfied(circuit.witness())
    (5, True)
    """

    def __init__(self, prime: int = FIELD_PRIME) -> None:
        _check_prime(prime)
        self.prime = prime
        self._values = [1]
        self._num_public = 0
        self._constraints: list[tuple[dict[int, int], dict[int, int], dict[int, int]]] = []

    @property
    def one(self) -> Wire:
        """The constant 1, variable 0 of every witness."""
        return Wire({0: 1}, 1, self.prime)

    @property
    def num_constraints(self) -> int:
        """Constraints so far, not counting the public-input rows :meth:`r1cs` adds."""
        return len(self._constraints)

    def _new(self, value: int) -> Wire:
        if type(value) is not int:
            raise TypeError(f"value must be an integer, not {type(value).__name__}")
        self._values.append(value % self.prime)
        return Wire({len(self._values) - 1: 1}, value, self.prime)

    def public(self, value: int) -> Wire:
        """Declare a public input with its value."""
        if len(self._values) - 1 != self._num_public:
            raise ValueError("declare every public input before private values")
        self._num_public += 1
        return self._new(value)

    def private(self, value: int) -> Wire:
        """Declare a private input (part of the witness only the prover knows)."""
        return self._new(value)

    def _check(self, *wires: Wire) -> None:
        for wire in wires:
            if not isinstance(wire, Wire) or wire.prime != self.prime:
                raise TypeError("expected wires of this circuit")

    def assert_product(self, left: Wire, right: Wire, output: Wire) -> None:
        """Add the constraint ``left * right = output``."""
        self._check(left, right, output)
        self._constraints.append((left.terms, right.terms, output.terms))

    def mul(self, left: Wire, right: Wire) -> Wire:
        """Return a new variable constrained to equal ``left * right``."""
        self._check(left, right)
        output = self._new(left.value * right.value)
        self.assert_product(left, right, output)
        return output

    def assert_equal(self, left: Wire | int, right: Wire | int) -> None:
        """Add the constraint ``(left - right) * 1 = 0``."""
        difference = self.one * 0 + left - right
        self.assert_product(difference, self.one, self.one * 0)

    def assert_boolean(self, wire: Wire) -> None:
        """Add the constraint ``wire * (1 - wire) = 0``: the wire is 0 or 1."""
        self._check(wire)
        self.assert_product(wire, 1 - wire, self.one * 0)

    def witness(self) -> tuple[int, ...]:
        """Return ``(1, public..., private...)``."""
        return tuple(self._values)

    def public_inputs(self) -> tuple[int, ...]:
        """Return the public inputs, without the leading 1."""
        return tuple(self._values[1 : self._num_public + 1])

    def r1cs(self) -> R1CS:
        """Freeze the constraints into an R1CS.

        One row ``x_i * 0 = 0`` is appended for the constant and for each
        public input, as Bellman and snarkjs do: it makes the public inputs'
        polynomials linearly independent, so a Groth16 proof binds them even
        if a public input appears in no other constraint.
        """
        rows = list(self._constraints)
        rows += [({i: 1}, {}, {}) for i in range(self._num_public + 1)]

        def frozen(k: int) -> tuple[tuple[tuple[int, int], ...], ...]:
            return tuple(tuple(sorted(row[k].items())) for row in rows)

        return R1CS(
            self.prime, len(self._values), self._num_public, frozen(0), frozen(1), frozen(2)
        )
