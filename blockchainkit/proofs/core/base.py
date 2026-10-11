"""Shared types and result containers for blockchainkit.proofs."""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

from blockchainkit._validation import integer
from blockchainkit.crypto.core.base import Point
from blockchainkit.crypto.systems.curves import Curve
from blockchainkit.structures.core.base import MerkleProof

Polynomial = tuple[int, ...]
"""Coefficients, constant term first, with no trailing zeros."""


@dataclass(frozen=True)
class IdentityTest:
    """The outcome of testing two polynomials for equality at random points.

    Attributes
    ----------
    equal : bool
        Whether the two agreed at every point tried. ``True`` may be wrong,
        with probability at most degree / field size per point; ``False``
        is always right.
    trials : int
        Points tried.
    witness : tuple of int or None
        A point where they differ, if one was found.
    """

    equal: bool
    trials: int
    witness: tuple[int, ...] | None


@dataclass(frozen=True)
class CNF:
    """A Boolean formula in conjunctive normal form, and its arithmetization.

    Parameters
    ----------
    num_variables : int
        Variables are numbered 1 to ``num_variables``.
    clauses : tuple of tuple of int
        Each clause lists literals: ``i`` for variable i, ``-i`` for its
        negation, as in the DIMACS format.

    Examples
    --------
    >>> from blockchainkit.proofs import CNF
    >>> xor = CNF(2, ((1, 2), (-1, -2)))
    >>> xor.count_solutions(), xor.evaluate((1, 0), 97), xor.evaluate((1, 1), 97)
    (2, 1, 0)
    """

    num_variables: int
    clauses: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        integer(self.num_variables, "num_variables", 1)
        if not isinstance(self.clauses, tuple) or not self.clauses:
            raise ValueError("clauses must be a non-empty tuple")
        for clause in self.clauses:
            if not isinstance(clause, tuple) or not clause:
                raise ValueError("each clause must be a non-empty tuple of literals")
            for literal in clause:
                if type(literal) is not int or not 0 < abs(literal) <= self.num_variables:
                    raise ValueError("literals must be nonzero integers naming a variable")

    @property
    def degree(self) -> int:
        """The arithmetization's degree in any one variable, its most occurrences."""
        counts = [0] * (self.num_variables + 1)
        for clause in self.clauses:
            for literal in clause:
                counts[abs(literal)] += 1
        return max(counts)

    def evaluate(self, point: Sequence[int], prime: int) -> int:
        """Evaluate the arithmetized formula at a point of the field.

        A literal becomes ``x`` or ``1 - x``, a clause becomes
        ``1 - prod(1 - literal)``, and the formula the product of its
        clauses. On 0/1 inputs this is the formula's truth value.
        """
        if len(point) != self.num_variables:
            raise ValueError(f"need {self.num_variables} coordinates")
        result = 1
        for clause in self.clauses:
            falsified = 1
            for literal in clause:
                x = point[abs(literal) - 1]
                falsified = falsified * ((1 - x) if literal > 0 else x) % prime
            result = result * (1 - falsified) % prime
        return result

    def is_satisfied(self, assignment: Sequence[int]) -> bool:
        """Whether a 0/1 assignment satisfies every clause."""
        if any(bit not in (0, 1) for bit in assignment):
            raise ValueError("an assignment is a sequence of 0s and 1s")
        return self.evaluate(assignment, 2) == 1

    def count_solutions(self) -> int:
        """Count the satisfying assignments by trying all 2**n of them."""
        return sum(self.is_satisfied(bits) for bits in product((0, 1), repeat=self.num_variables))


@dataclass(frozen=True)
class SumcheckRun:
    """One run of the sum-check protocol between a prover and a verifier.

    Attributes
    ----------
    claim : int
        The sum the prover asserted.
    true_sum : int
        The actual sum over the Boolean cube.
    polynomials : tuple of Polynomial
        The univariate polynomial the prover sent in each round.
    challenges : tuple of int
        The verifier's random field element after each round.
    accepted : bool
        Whether every round check and the final oracle query passed.
    """

    claim: int
    true_sum: int
    polynomials: tuple[Polynomial, ...]
    challenges: tuple[int, ...]
    accepted: bool


@dataclass(frozen=True)
class QBF:
    """A fully quantified Boolean formula: one quantifier per variable, then a CNF.

    Parameters
    ----------
    quantifiers : str
        ``"A"`` (for all) or ``"E"`` (there exists) for variables 1, 2, ...
    formula : CNF
        The quantifier-free matrix.

    Examples
    --------
    >>> from blockchainkit.proofs import CNF, QBF
    >>> QBF("AE", CNF(2, ((1, 2), (-1, -2)))).evaluate()  # for all x, some y differs
    True
    """

    quantifiers: str
    formula: CNF

    def __post_init__(self) -> None:
        if not isinstance(self.formula, CNF):
            raise TypeError("formula must be a CNF")
        if not isinstance(self.quantifiers, str) or set(self.quantifiers) - {"A", "E"}:
            raise ValueError('quantifiers must be a string of "A" and "E"')
        if len(self.quantifiers) != self.formula.num_variables:
            raise ValueError("need one quantifier per variable")

    def evaluate(self) -> bool:
        """Decide the formula by trying every assignment: exponential time, linear space."""

        def value(assigned: tuple[int, ...]) -> bool:
            if len(assigned) == len(self.quantifiers):
                return self.formula.is_satisfied(assigned)
            branches = (value((*assigned, 0)), value((*assigned, 1)))
            return all(branches) if self.quantifiers[len(assigned)] == "A" else any(branches)

        return value(())


@dataclass(frozen=True)
class TQBFRound:
    """One round of Shamir's protocol: an operator, its variable, and the prover's polynomial.

    Attributes
    ----------
    operator : str
        ``"A"`` (product), ``"E"`` (complemented product) or ``"L"``
        (linearization).
    variable : int
        The variable it acts on, from 1.
    polynomial : Polynomial
        The prover's claim for the inner expression as a polynomial in that
        variable.
    challenge : int
        The random value the verifier then assigned to the variable.
    """

    operator: str
    variable: int
    polynomial: Polynomial
    challenge: int


@dataclass(frozen=True)
class TQBFRun:
    """One run of the interactive proof that a quantified Boolean formula is true.

    Attributes
    ----------
    claim : int
        The truth value the prover asserted, 1 or 0.
    true_value : int
        The formula's actual value.
    rounds : tuple of TQBFRound
    accepted : bool
    """

    claim: int
    true_value: int
    rounds: tuple[TQBFRound, ...]
    accepted: bool

    @property
    def max_degree(self) -> int:
        """The largest degree among the prover's polynomials."""
        return max(len(r.polynomial) - 1 for r in self.rounds)


@dataclass(frozen=True)
class QuadraticSystem:
    """Quadratic equations over GF(2): the NP-complete language of the Hadamard PCP.

    Parameters
    ----------
    num_variables : int
        Variables u_0, ..., u_{n-1}, with n between 1 and 4.
    equations : tuple
        Each equation is ``(terms, constant)``: it says that the sum of
        ``u_i u_j`` over the pairs ``(i, j)`` in ``terms`` is ``constant``
        modulo 2. A linear term ``u_i`` is the pair ``(i, i)``.

    Examples
    --------
    >>> from blockchainkit.proofs import QuadraticSystem
    >>> system = QuadraticSystem(2, ((((0, 1),), 1), (((0, 0), (1, 1)), 0)))
    >>> system.solutions()  # u0 u1 = 1 and u0 + u1 = 0
    ((1, 1),)
    """

    num_variables: int
    equations: tuple[tuple[tuple[tuple[int, int], ...], int], ...]

    def __post_init__(self) -> None:
        integer(self.num_variables, "num_variables", 1)
        if self.num_variables > 4:
            raise ValueError("at most 4 variables: the proof has 2**(n**2) bits")
        if not isinstance(self.equations, tuple) or not self.equations:
            raise ValueError("equations must be a non-empty tuple")
        for equation in self.equations:
            terms, constant = equation
            if constant not in (0, 1) or type(constant) is not int:
                raise ValueError("each constant must be 0 or 1")
            for i, j in terms:
                for index in (i, j):
                    if type(index) is not int or not 0 <= index < self.num_variables:
                        raise ValueError("terms must pair variable indices")

    def is_satisfied(self, assignment: Sequence[int]) -> bool:
        """Whether a 0/1 assignment satisfies every equation."""
        if len(assignment) != self.num_variables or any(b not in (0, 1) for b in assignment):
            raise ValueError(f"an assignment is {self.num_variables} bits")
        return all(
            sum(assignment[i] * assignment[j] for i, j in terms) % 2 == constant
            for terms, constant in self.equations
        )

    def solutions(self) -> tuple[tuple[int, ...], ...]:
        """Every satisfying assignment, by trying all 2**n."""
        return tuple(
            bits for bits in product((0, 1), repeat=self.num_variables) if self.is_satisfied(bits)
        )


@dataclass(frozen=True)
class HadamardProof:
    """The exponentially long proof of the Hadamard PCP.

    Attributes
    ----------
    linear : tuple of int
        ``<u, x> mod 2`` for every x in {0, 1}**n, indexed by x as a binary
        number (bit i is x_i).
    quadratic : tuple of int
        ``<u (x) u, y> mod 2`` for every y in {0, 1}**(n**2), where bit
        ``i n + j`` of y pairs with ``u_i u_j``.
    """

    linear: tuple[int, ...]
    quadratic: tuple[int, ...]

    @property
    def bits(self) -> tuple[int, ...]:
        """Both tables concatenated, the string a PCP verifier queries."""
        return self.linear + self.quadratic


@dataclass(frozen=True)
class PCPRun:
    """The PCP verifier's verdict.

    Attributes
    ----------
    accepted : bool
    queries : int
        Proof bits read.
    failed_test : str or None
        The first test that failed.
    """

    accepted: bool
    queries: int
    failed_test: str | None


@dataclass(frozen=True)
class KilianRun:
    """One run of Kilian's interactive argument: a Merkle-committed PCP, opened where queried.

    Attributes
    ----------
    root : bytes
        The prover's commitment to the whole PCP.
    accepted : bool
        Whether every opening matched the root and the PCP verifier accepted.
    queries : int
        PCP bits opened.
    communication : int
        Bytes the prover sent: the root, then each bit with its Merkle path.
    proof_length : int
        Bits in the PCP itself, which the prover never sends.
    """

    root: bytes
    accepted: bool
    queries: int
    communication: int
    proof_length: int


@dataclass(frozen=True)
class Opening:
    """One PCP bit and its Merkle path."""

    position: int
    bit: int
    path: MerkleProof


@dataclass(frozen=True)
class CSProof:
    """Micali's computationally sound proof: a root, a salt, and the openings it selects.

    Attributes
    ----------
    root : bytes
        Merkle root of the PCP.
    salt : int
        Hashed with the root to select the queries; varying it is how a
        cheating prover grinds.
    openings : tuple of Opening
        The queried bits, in the order the verifier reads them.
    """

    root: bytes
    salt: int
    openings: tuple[Opening, ...]

    @property
    def size(self) -> int:
        """Bytes sent for the root, the salt, and each opening's bit, position and path."""
        return 40 + sum(9 + 32 * sum(s is not None for s in o.path.siblings) for o in self.openings)


@dataclass(frozen=True)
class SRS:
    """A structured reference string: ``[tau**i] G`` for i = 0, ..., max_degree.

    Attributes
    ----------
    powers : tuple of Point
    curve : Curve
        The pairing curve the points lie on.
    """

    powers: tuple[Point, ...]
    curve: Curve

    def __post_init__(self) -> None:
        if len(self.powers) < 2:
            raise ValueError("a reference string needs at least [1] G and [tau] G")

    @property
    def max_degree(self) -> int:
        """The largest degree it can commit to."""
        return len(self.powers) - 1


@dataclass(frozen=True)
class KZGOpening:
    """A claimed evaluation ``f(point) = value`` and its witness ``[q(tau)] G``."""

    point: int
    value: int
    witness: Point


@dataclass(frozen=True)
class Contribution:
    """One participant's update to a ceremony: the new string and ``[secret] G``."""

    srs: SRS
    public: Point


Row = tuple[tuple[int, int], ...]
"""One sparse row of an R1CS matrix, as ``(variable index, coefficient)`` pairs."""


@dataclass(frozen=True)
class R1CS:
    """A rank-1 constraint system: ``<a_j, z> * <b_j, z> = <c_j, z>`` for every row j.

    Attributes
    ----------
    prime : int
        Field modulus.
    num_variables : int
        Length of the witness z, including the leading constant 1.
    num_public : int
        Public inputs, which follow the constant in z.
    a, b, c : tuple of Row
        The sparse rows of the three matrices.
    """

    prime: int
    num_variables: int
    num_public: int
    a: tuple[Row, ...]
    b: tuple[Row, ...]
    c: tuple[Row, ...]

    def __post_init__(self) -> None:
        if not len(self.a) == len(self.b) == len(self.c):
            raise ValueError("the three matrices need the same number of rows")
        if not 0 <= self.num_public < self.num_variables:
            raise ValueError("need 0 <= num_public < num_variables")
        for matrix in (self.a, self.b, self.c):
            for row in matrix:
                if any(not 0 <= i < self.num_variables for i, _ in row):
                    raise ValueError("a row refers to a variable outside the witness")

    @property
    def num_constraints(self) -> int:
        """Number of rows."""
        return len(self.a)

    def row_values(self, witness: Sequence[int]) -> tuple[tuple[int, int, int], ...]:
        """Return ``(<a_j, z>, <b_j, z>, <c_j, z>)`` for every row."""
        if len(witness) != self.num_variables or witness[0] % self.prime != 1:
            raise ValueError(f"a witness has {self.num_variables} entries and starts with 1")
        p = self.prime

        def dot(row: Row) -> int:
            return sum(c * witness[i] for i, c in row) % p

        return tuple(
            (dot(a), dot(b), dot(c)) for a, b, c in zip(self.a, self.b, self.c, strict=True)
        )

    def is_satisfied(self, witness: Sequence[int]) -> bool:
        """Whether every constraint holds for ``witness``."""
        return all(a * b % self.prime == c for a, b, c in self.row_values(witness))


@dataclass(frozen=True)
class QAP:
    """A quadratic arithmetic program: one polynomial per variable and matrix.

    Attributes
    ----------
    prime : int
    domain_size : int
        n, the size of the domain ``{w**j}`` of roots of unity.
    a, b, c : tuple of Polynomial
        ``A_i``, ``B_i``, ``C_i`` for each witness variable i.
    target : Polynomial
        ``t(X) = X**n - 1``, which vanishes on the domain.
    """

    prime: int
    domain_size: int
    a: tuple[Polynomial, ...]
    b: tuple[Polynomial, ...]
    c: tuple[Polynomial, ...]
    target: Polynomial


@dataclass(frozen=True)
class QAPDivision:
    """``A B - C = H t + R`` for one witness.

    Attributes
    ----------
    left, right, output : Polynomial
        A(X), B(X) and C(X).
    quotient : Polynomial
        H(X).
    remainder : Polynomial
        R(X), zero exactly when the witness satisfies every constraint.
    """

    left: Polynomial
    right: Polynomial
    output: Polynomial
    quotient: Polynomial
    remainder: Polynomial

    @property
    def satisfied(self) -> bool:
        """Whether the target divides ``A B - C``."""
        return not self.remainder


@dataclass(frozen=True)
class Groth16Trapdoor:
    """The setup's toxic waste: five secret field elements that must be destroyed.

    Anyone who keeps them can prove false statements.
    """

    tau: int
    alpha: int
    beta: int
    gamma: int
    delta: int


@dataclass(frozen=True)
class VerifyingKey:
    """What a Groth16 verifier needs: four points and one point per public input.

    Attributes
    ----------
    alpha, beta, gamma, delta : Point
    public_query : tuple of Point
        ``[(beta A_i(tau) + alpha B_i(tau) + C_i(tau)) / gamma] G`` for the
        constant and each public input.
    curve : Curve
    """

    alpha: Point
    beta: Point
    gamma: Point
    delta: Point
    public_query: tuple[Point, ...]
    curve: Curve


@dataclass(frozen=True)
class ProvingKey:
    """What a Groth16 prover needs: the circuit and the encoded QAP at the secret point.

    Attributes
    ----------
    r1cs : R1CS
    domain_size : int
    a_query, b_query : tuple of Point
        ``[A_i(tau)] G`` and ``[B_i(tau)] G`` for every variable.
    private_query : tuple of Point
        ``[(beta A_i(tau) + alpha B_i(tau) + C_i(tau)) / delta] G`` for the
        private variables.
    h_query : tuple of Point
        ``[tau**k t(tau) / delta] G`` for k = 0, ..., n - 2.
    verifying_key : VerifyingKey
    """

    r1cs: R1CS
    domain_size: int
    a_query: tuple[Point, ...]
    b_query: tuple[Point, ...]
    private_query: tuple[Point, ...]
    h_query: tuple[Point, ...]
    verifying_key: VerifyingKey


@dataclass(frozen=True)
class Groth16Proof:
    """Three group elements, whatever the size of the circuit."""

    a: Point
    b: Point
    c: Point


@dataclass(frozen=True)
class Note:
    """A Zerocash note: who owns it, its value, its unique serial seed, and commitment randomness.

    Attributes
    ----------
    owner : int
        The owner's public key ``H(sk, 0)``.
    value : int
    rho : int
        Unique per note; its nullifier is ``H(sk, rho)``.
    randomness : int
        Hides the note inside its commitment.
    """

    owner: int
    value: int
    rho: int
    randomness: int

    def __post_init__(self) -> None:
        for name in ("owner", "value", "rho", "randomness"):
            integer(getattr(self, name), name)


@dataclass(frozen=True)
class SpendTransaction:
    """What a Zerocash spend publishes: root, nullifier, new commitment, amount and proof."""

    root: int
    nullifier: int
    new_commitment: int
    public_value: int
    proof: Groth16Proof


@dataclass(frozen=True)
class PlonkKey:
    """A preprocessed PLONK circuit: selector and permutation polynomials, and their commitments.

    Attributes
    ----------
    prime : int
    n : int
        Rows of the padded circuit, a power of two.
    omega : int
        Generator of the domain of n-th roots of unity.
    wiring : tuple of tuple of int
        The variables on each row's left, right and output wires.
    selectors : tuple of Polynomial
        ``q_L, q_R, q_O, q_M, q_C``.
    sigmas : tuple of Polynomial
        The permutation, one polynomial per wire column.
    sigma_labels : tuple of tuple of int
        The permutation's values on the domain.
    selector_commitments, sigma_commitments : tuple of Point
        What the verifier holds.
    """

    prime: int
    n: int
    omega: int
    wiring: tuple[tuple[int, int, int], ...]
    selectors: tuple[Polynomial, ...]
    sigmas: tuple[Polynomial, ...]
    sigma_labels: tuple[tuple[int, ...], ...]
    selector_commitments: tuple[Point, ...]
    sigma_commitments: tuple[Point, ...]


@dataclass(frozen=True)
class PlonkProof:
    """Five commitments, fourteen evaluations and two opening witnesses.

    Attributes
    ----------
    wires : tuple of Point
        Commitments to the wire polynomials a, b, c.
    z : Point
        Commitment to the running product of the permutation argument.
    t : Point
        Commitment to the quotient polynomial.
    evaluations : tuple of int
        a, b, c, sigma_1..3, q_L, q_R, q_O, q_M, q_C, z and t at zeta, then
        z at ``zeta omega``.
    opening, shifted_opening : Point
        Batched KZG witnesses at zeta and at ``zeta omega``.
    """

    wires: tuple[Point, ...]
    z: Point
    t: Point
    evaluations: tuple[int, ...]
    opening: Point
    shifted_opening: Point


@dataclass(frozen=True)
class RangeProof:
    """A Bulletproofs range proof for the commitment ``V = g**v h**gamma``.

    Attributes
    ----------
    commitment : int
        V.
    a, s, t1, t2 : int
        Commitments to the bit vectors, the blinding vectors, and the
        coefficients of t(X).
    tau_x, mu, t_hat : int
        The blinding of t(x), the blinding of A S**x, and t(x).
    left, right : tuple of int
        L and R from each halving round of the inner-product argument.
    final_a, final_b : int
        The last scalars of the folded vectors.
    """

    commitment: int
    a: int
    s: int
    t1: int
    t2: int
    tau_x: int
    mu: int
    t_hat: int
    left: tuple[int, ...]
    right: tuple[int, ...]
    final_a: int
    final_b: int

    @property
    def size(self) -> tuple[int, int]:
        """``(group elements, scalars)`` sent, not counting the commitment V."""
        return 4 + 2 * len(self.left), 5


@dataclass(frozen=True)
class IPAOpening:
    """An inner-product-argument opening of a polynomial commitment.

    Attributes
    ----------
    point, value : int
        The claim ``f(point) = value``.
    left, right : tuple of int
        L and R from each halving round.
    final : int
        The last coefficient after folding.
    g_final : int
        The prover's claim for the folded generator, which a full verifier
        recomputes and a Halo verifier defers.
    """

    point: int
    value: int
    left: tuple[int, ...]
    right: tuple[int, ...]
    final: int
    g_final: int


@dataclass(frozen=True)
class HaloAccumulator:
    """A deferred claim: ``g_final`` commits to ``prod (1 + c_j X**(2**(k-j)))``.

    Attributes
    ----------
    challenges : tuple of int
        The halving challenges c_j that define the polynomial.
    g_final : int
        The claimed commitment to it.
    """

    challenges: tuple[int, ...]
    g_final: int


@dataclass(frozen=True)
class AccumulationProof:
    """The opening that merges several accumulators into one."""

    opening: IPAOpening


@dataclass(frozen=True)
class FRILayerOpening:
    """The two values of one layer that fold together, f(x) and f(-x), with their Merkle paths."""

    low: int
    low_path: MerkleProof
    high: int
    high_path: MerkleProof


@dataclass(frozen=True)
class FRIQuery:
    """One query: a position of the first layer and its openings in every layer."""

    index: int
    layers: tuple[FRILayerOpening, ...]


@dataclass(frozen=True)
class FRIProof:
    """A FRI proof: one Merkle root per layer, the final constant, and the queries.

    Attributes
    ----------
    roots : tuple of bytes
    final : int
    queries : tuple of FRIQuery
    """

    roots: tuple[bytes, ...]
    final: int
    queries: tuple[FRIQuery, ...]

    @property
    def size(self) -> int:
        """Bytes sent for the roots, the constant, and each opened value with its path."""
        opened = sum(
            16 + 32 * sum(s is not None for s in o.low_path.siblings + o.high_path.siblings)
            for query in self.queries
            for o in query.layers
        )
        return 32 * len(self.roots) + 8 + opened


@dataclass(frozen=True)
class TraceOpening:
    """Trace values at x, g x and g**2 x, with their Merkle paths."""

    values: tuple[int, ...]
    paths: tuple[MerkleProof, ...]


@dataclass(frozen=True)
class StarkProof:
    """A STARK: the trace's Merkle root, a FRI proof, and the trace openings it needs.

    Attributes
    ----------
    trace_root : bytes
        Commitment to the low-degree extension of the trace.
    fri : FRIProof
        Proves that the constraint composition has low degree.
    trace_openings : tuple of TraceOpening
        Two per FRI query, one for each value of the first layer.
    """

    trace_root: bytes
    fri: FRIProof
    trace_openings: tuple[TraceOpening, ...]

    @property
    def size(self) -> int:
        """Bytes sent for the root, the FRI proof, and the opened trace values with paths."""
        opened = sum(
            8 * len(o.values) + 32 * sum(s is not None for p in o.paths for s in p.siblings)
            for o in self.trace_openings
        )
        return 32 + self.fri.size + opened
