"""Bulletproofs: short range proofs without a trusted setup (2018).

Confidential amounts hide a value v in a Pedersen commitment
``V = g**v h**gamma``, which is useless unless the value is shown to lie in
``[0, 2**n)``: otherwise a "negative" output mints money. Bünz, Bootle,
Boneh, Poelstra, Wuille and Maxwell write v's bits as a vector a_L, set
``a_R = a_L - 1``, and reduce the three facts

    <a_L, 2**n> = v,    a_L o a_R = 0,    a_L - a_R - 1 = 0

with random challenges y and z to one inner product ``t = <l, r>``. The
prover commits to l and r with vectors of independent generators, and
proves the inner product by *halving*: each round it sends two group
elements L and R, the verifier sends a challenge x, and both fold the
vectors and generators to half their length,

    a' = x a_lo + x**-1 a_hi,    G' = G_lo**(x**-1) o G_hi**x.

After log2(n) rounds one scalar pair remains: a proof of
``2 log2(n) + 4`` group elements and 5 scalars, with no trusted setup,
because the generators are hashed into the group (Bootle, Cerulli,
Chaidos, Groth and Petit, 2016).

This version works in the 62-bit Schnorr group
:data:`~blockchainkit.crypto.systems.asymmetric.TEACHING_GROUP`
(multiplicatively); deployments use elliptic curves such as Curve25519.
"""

from random import Random

from blockchainkit import _validation
from blockchainkit._validation import integer
from blockchainkit.crypto.systems.asymmetric import TEACHING_GROUP
from blockchainkit.proofs.core.base import RangeProof
from blockchainkit.proofs.utils.groups import independent_generators, multi_exponent
from blockchainkit.proofs.utils.transcript import Transcript

_GROUP = TEACHING_GROUP


def _generators(n: int) -> tuple[int, int, int, tuple[int, ...], tuple[int, ...]]:
    gens = independent_generators(3 + 2 * n, "bulletproofs")
    return gens[0], gens[1], gens[2], gens[3::2], gens[4::2]


def range_commitment(value: int, blinding: int) -> int:
    """The Pedersen commitment ``g**value h**blinding`` that a range proof is about."""
    integer(value, "value")
    integer(blinding, "blinding")
    g, h, *_ = _generators(1)
    return pow(g, value, _GROUP.p) * pow(h, blinding % _GROUP.q, _GROUP.p) % _GROUP.p


def _inner(a: list[int], b: list[int]) -> int:
    return sum(x * y for x, y in zip(a, b, strict=True)) % _GROUP.q


def _check_bits(bits: int) -> None:
    integer(bits, "bits", 1)
    if bits & (bits - 1) or bits > 64:
        raise ValueError("bits must be a power of two, at most 64")


def range_proof(value: int, blinding: int, bits: int = 32, *, seed: int = 0) -> RangeProof:
    """Prove that the commitment to ``value`` hides a number in ``[0, 2**bits)``.

    Parameters
    ----------
    value : int
        The hidden amount.
    blinding : int
        The commitment's randomness gamma.
    bits : int
        A power of two up to 64.
    seed : int
        Seed of the prover's blinding vectors and scalars.

    Raises
    ------
    ValueError
        ``value`` is not below ``2**bits``: no proof exists.

    Examples
    --------
    >>> from blockchainkit.proofs import range_proof, verify_range_proof
    >>> proof = range_proof(1000, blinding=77, bits=16)
    >>> verify_range_proof(proof, bits=16), len(proof.left)
    (True, 4)
    """
    _check_bits(bits)
    integer(value, "value")
    integer(blinding, "blinding")
    _validation.seed(seed)
    if value >= 2**bits:
        raise ValueError(f"value must be below 2**{bits}")
    p, q, n = _GROUP.p, _GROUP.q, bits
    g, h, u, gs, hs = _generators(n)
    rng = Random(seed)
    a_left = [value >> i & 1 for i in range(n)]
    a_right = [(bit - 1) % q for bit in a_left]
    alpha, rho, tau1, tau2 = (rng.randrange(1, q) for _ in range(4))
    s_left = [rng.randrange(q) for _ in range(n)]
    s_right = [rng.randrange(q) for _ in range(n)]
    commitment = range_commitment(value, blinding)
    a = pow(h, alpha, p) * multi_exponent(gs + hs, a_left + a_right, _GROUP) % p
    s = pow(h, rho, p) * multi_exponent(gs + hs, s_left + s_right, _GROUP) % p
    transcript = Transcript(b"bulletproofs-range")
    transcript.append("statement", [n, commitment, a, s])
    y, z = transcript.challenge("y", q), transcript.challenge("z", q)
    ys = [pow(y, i, q) for i in range(n)]
    l0 = [(x - z) % q for x in a_left]
    r0 = [(ys[i] * (a_right[i] + z) + z * z * 2**i) % q for i in range(n)]
    r1 = [ys[i] * s_right[i] % q for i in range(n)]
    t1 = (_inner(l0, r1) + _inner(s_left, r0)) % q
    t2 = _inner(s_left, r1)
    big_t1 = pow(g, t1, p) * pow(h, tau1, p) % p
    big_t2 = pow(g, t2, p) * pow(h, tau2, p) % p
    transcript.append("t", [big_t1, big_t2])
    x = transcript.challenge("x", q)
    left = [(l0[i] + s_left[i] * x) % q for i in range(n)]
    right = [(r0[i] + r1[i] * x) % q for i in range(n)]
    t_hat = _inner(left, right)
    tau_x = (tau2 * x * x + tau1 * x + z * z * blinding) % q
    mu = (alpha + rho * x) % q
    transcript.append("scalars", [tau_x, mu, t_hat])
    w = transcript.challenge("w", q)
    y_inverse = pow(y, -1, q)
    hs_prime = [pow(hs[i], pow(y_inverse, i, q), p) for i in range(n)]
    ls, rs = [], []
    gv, hv, av, bv = list(gs), hs_prime, left, right
    uw = pow(u, w, p)
    while len(av) > 1:
        half = len(av) // 2
        c_left, c_right = _inner(av[:half], bv[half:]), _inner(av[half:], bv[:half])
        big_l = (
            multi_exponent(gv[half:] + hv[:half], av[:half] + bv[half:], _GROUP)
            * pow(uw, c_left, p)
            % p
        )
        big_r = (
            multi_exponent(gv[:half] + hv[half:], av[half:] + bv[:half], _GROUP)
            * pow(uw, c_right, p)
            % p
        )
        ls.append(big_l)
        rs.append(big_r)
        transcript.append("round", [big_l, big_r])
        e = transcript.challenge("e", q)
        e_inverse = pow(e, -1, q)
        gv = [pow(gv[i], e_inverse, p) * pow(gv[half + i], e, p) % p for i in range(half)]
        hv = [pow(hv[i], e, p) * pow(hv[half + i], e_inverse, p) % p for i in range(half)]
        av = [(av[i] * e + av[half + i] * e_inverse) % q for i in range(half)]
        bv = [(bv[i] * e_inverse + bv[half + i] * e) % q for i in range(half)]
    return RangeProof(
        commitment, a, s, big_t1, big_t2, tau_x, mu, t_hat, tuple(ls), tuple(rs), av[0], bv[0]
    )


def verify_range_proof(proof: RangeProof, bits: int = 32) -> bool:
    """Check a range proof: one equation for t, then the folded inner-product argument.

    Malformed proofs return False.
    """
    _check_bits(bits)
    if not isinstance(proof, RangeProof) or len(proof.left) != len(proof.right):
        return False
    p, q, n = _GROUP.p, _GROUP.q, bits
    if 2 ** len(proof.left) != n:
        return False
    elements = (proof.commitment, proof.a, proof.s, proof.t1, proof.t2, *proof.left, *proof.right)
    scalars = (proof.tau_x, proof.mu, proof.t_hat, proof.final_a, proof.final_b)
    if any(type(e) is not int or not 0 < e < p or pow(e, q, p) != 1 for e in elements):
        return False
    if any(type(s) is not int or not 0 <= s < q for s in scalars):
        return False
    g, h, u, gs, hs = _generators(n)
    transcript = Transcript(b"bulletproofs-range")
    transcript.append("statement", [n, proof.commitment, proof.a, proof.s])
    y, z = transcript.challenge("y", q), transcript.challenge("z", q)
    transcript.append("t", [proof.t1, proof.t2])
    x = transcript.challenge("x", q)
    transcript.append("scalars", [proof.tau_x, proof.mu, proof.t_hat])
    w = transcript.challenge("w", q)
    ys = [pow(y, i, q) for i in range(n)]
    delta = ((z - z * z) * sum(ys) - z**3 * (2**n - 1)) % q
    left = pow(g, proof.t_hat, p) * pow(h, proof.tau_x, p) % p
    right = pow(proof.commitment, z * z % q, p) * pow(g, delta, p) % p
    right = right * pow(proof.t1, x, p) * pow(proof.t2, x * x % q, p) % p
    if left != right:
        return False
    y_inverse = pow(y, -1, q)
    hs_prime = [pow(hs[i], pow(y_inverse, i, q), p) for i in range(n)]
    exponents_g = [-z % q] * n
    exponents_h = [(z * ys[i] + z * z * 2**i) % q for i in range(n)]
    uw = pow(u, w, p)
    target = (
        proof.a
        * pow(proof.s, x, p)
        * multi_exponent([*gs, *hs_prime], exponents_g + exponents_h, _GROUP)
    )
    target = target * pow(h, -proof.mu % q, p) * pow(uw, proof.t_hat, p) % p
    gv, hv = list(gs), hs_prime
    for big_l, big_r in zip(proof.left, proof.right, strict=True):
        transcript.append("round", [big_l, big_r])
        e = transcript.challenge("e", q)
        e_inverse = pow(e, -1, q)
        half = len(gv) // 2
        gv = [pow(gv[i], e_inverse, p) * pow(gv[half + i], e, p) % p for i in range(half)]
        hv = [pow(hv[i], e, p) * pow(hv[half + i], e_inverse, p) % p for i in range(half)]
        target = pow(big_l, e * e % q, p) * target * pow(big_r, pow(e_inverse, 2, q), p) % p
    a, b = proof.final_a, proof.final_b
    return target == pow(gv[0], a, p) * pow(hv[0], b, p) * pow(uw, a * b % q, p) % p
