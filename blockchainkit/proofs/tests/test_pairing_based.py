"""The toy pairing, KZG, ceremonies, circuits and QAPs, Groth16, Zerocash, and PLONK."""

from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from blockchainkit.crypto import TOY_CURVE, add, multiply
from blockchainkit.proofs import (
    FIELD_PRIME,
    PAIRING_CURVE,
    R1CS,
    SRS,
    Circuit,
    Contribution,
    Groth16Proof,
    Groth16Trapdoor,
    KZGOpening,
    Note,
    PlonkCircuit,
    PlonkProof,
    ShieldedPool,
    Wire,
    contribute,
    domain_size,
    forge_opening,
    groth16_prove,
    groth16_setup,
    groth16_verify,
    gt_multiply,
    gt_power,
    kzg_commit,
    kzg_open,
    kzg_verify,
    mimc_gadget,
    mimc_hash,
    note_commitment,
    nullifier,
    owner_key,
    pairing,
    permutation_product,
    plonk_prove,
    plonk_setup,
    plonk_verify,
    prove_spend,
    qap_divide,
    r1cs_to_qap,
    spend_circuit,
    spend_setup,
    start_ceremony,
    trusted_setup,
    verify_contribution,
)

E = PAIRING_CURVE
G = E.generator
TRAPDOOR = Groth16Trapdoor(11, 22, 33, 44, 55)


def cubic_circuit(x=3, out=35):
    circuit = Circuit()
    public = circuit.public(out)
    secret = circuit.private(x)
    circuit.assert_equal(circuit.mul(circuit.mul(secret, secret), secret) + secret + 5, public)
    return circuit


@settings(max_examples=20, deadline=None)
@given(st.integers(1, E.order - 1), st.integers(1, E.order - 1))
def test_pairing_is_bilinear(a, b):
    base = pairing(G, G)
    assert pairing(multiply(a, G, E), multiply(b, G, E)) == gt_power(base, a * b)
    assert pairing(multiply(a, G, E), G) == pairing(G, multiply(a, G, E))


def test_pairing_is_nondegenerate_and_validates():
    base = pairing(G, G)
    assert base != (1, 0) and gt_power(base, E.order) == (1, 0)
    assert pairing(None, G) == (1, 0) == pairing(G, None)
    assert gt_multiply(base, gt_power(base, -1)) == (1, 0)
    with pytest.raises(TypeError):
        gt_power(base, 1.0)
    with pytest.raises(ValueError, match="curve"):
        pairing((1, 1), G)
    with pytest.raises(ValueError, match="subgroup"):
        pairing(next_point_outside_subgroup(), G)
    with pytest.raises(ValueError, match="x\\*\\*3"):
        pairing(G, G, TOY_CURVE)
    with pytest.raises(TypeError):
        gt_multiply(base, base, "curve")


def next_point_outside_subgroup():
    p = E.p
    for x in range(2, 50):
        rhs = (x**3 + x) % p
        y = pow(rhs, (p + 1) // 4, p)
        if y * y % p == rhs and multiply(E.order, (x, y), E) is not None:
            return x, y
    raise AssertionError("no such point")


def test_kzg_commitments_open_correctly_and_bind():
    srs = trusted_setup(8, 1234)
    assert srs.max_degree == 8
    f = [5, 0, 1, 7]
    commitment = kzg_commit(f, srs)
    opening = kzg_open(f, 3, srs)
    assert opening.value == (5 + 9 + 7 * 27) % FIELD_PRIME
    assert kzg_verify(commitment, opening, srs)
    assert not kzg_verify(commitment, replace(opening, value=opening.value + 1), srs)
    assert not kzg_verify(commitment, replace(opening, point=4), srs)
    assert not kzg_verify(kzg_commit([5, 0, 1, 8], srs), opening, srs)
    assert not kzg_verify(commitment, "opening", srs)
    assert not kzg_verify(commitment, replace(opening, value=1.5), srs)
    assert not kzg_verify((1, 1), opening, srs)
    assert kzg_commit([], srs) is None
    with pytest.raises(ValueError, match="degree"):
        kzg_commit(range(10), srs)
    with pytest.raises(ValueError):
        trusted_setup(4, E.order)
    with pytest.raises(ValueError):
        SRS((G,), E)


def test_the_toxic_waste_forges_any_opening():
    srs = trusted_setup(4, 1234)
    commitment = kzg_commit([1, 2, 3], srs)
    forged = forge_opening(commitment, 10, 999, 1234, srs)
    assert kzg_verify(commitment, forged, srs) and forged.value == 999
    assert not kzg_verify(commitment, forge_opening(commitment, 10, 999, 4321, srs), srs)
    with pytest.raises(ValueError, match="secret point"):
        forge_opening(commitment, 1234, 1, 1234, srs)


def test_ceremony_contributions_compose_and_are_checked():
    srs = start_ceremony(5)
    first = contribute(srs, 11)
    second = contribute(first.srs, 13)
    assert verify_contribution(srs, first) and verify_contribution(first.srs, second)
    assert second.srs == trusted_setup(5, 11 * 13)
    assert not verify_contribution(srs, second)  # Does not build on this string.
    powers = list(second.srs.powers)
    powers[3] = add(powers[3], G, E)
    assert not verify_contribution(first.srs, replace(second, srs=SRS(tuple(powers), E)))
    assert not verify_contribution(first.srs, replace(second, public=None))
    assert not verify_contribution(first.srs, replace(second, srs=start_ceremony(4)))
    shifted = SRS((multiply(2, G, E),) + second.srs.powers[1:], E)
    assert not verify_contribution(first.srs, replace(second, srs=shifted))
    assert not verify_contribution(first.srs, replace(second, public=(1, 1)))
    with pytest.raises(ValueError):
        contribute(srs, E.order)
    assert isinstance(first, Contribution)


def test_circuits_build_r1cs_and_witnesses():
    circuit = cubic_circuit()
    r1cs = circuit.r1cs()
    assert r1cs.num_constraints == 5 and r1cs.num_public == 1 and r1cs.num_variables == 5
    assert circuit.witness() == (1, 35, 3, 9, 27) and circuit.public_inputs() == (35,)
    assert r1cs.is_satisfied(circuit.witness())
    assert not r1cs.is_satisfied((1, 36, 3, 9, 27))
    bit = circuit.private(1)
    circuit.assert_boolean(bit)
    assert circuit.r1cs().is_satisfied(circuit.witness())
    w = circuit.one * 3 - 1
    assert (2 - w).value == 0 and (-w).value == FIELD_PRIME - 2 and (w + w).value == 4
    assert repr(w).startswith("Wire(value=2")
    with pytest.raises(TypeError, match="Circuit.mul"):
        w * w
    with pytest.raises(TypeError):
        w * 1.5
    with pytest.raises(TypeError):
        w + "x"
    with pytest.raises(TypeError):
        w - "x"
    with pytest.raises(ValueError, match="fields"):
        w + Wire({0: 1}, 1, 97)
    with pytest.raises(TypeError):
        circuit.mul(w, Wire({0: 1}, 1, 97))
    with pytest.raises(ValueError, match="public"):
        circuit.public(1)
    with pytest.raises(TypeError):
        circuit.private(1.0)


def test_r1cs_validation():
    with pytest.raises(ValueError, match="rows"):
        R1CS(97, 2, 0, ((),), (), ())
    with pytest.raises(ValueError, match="num_public"):
        R1CS(97, 2, 2, (), (), ())
    with pytest.raises(ValueError, match="outside"):
        R1CS(97, 2, 0, (((5, 1),),), ((),), ((),))
    with pytest.raises(ValueError, match="starts with 1"):
        cubic_circuit().r1cs().is_satisfied((0, 35, 3, 9, 27))


def test_qap_turns_constraints_into_divisibility():
    circuit = cubic_circuit()
    qap = r1cs_to_qap(circuit.r1cs())
    assert qap.domain_size == 8 == domain_size(circuit.r1cs())
    division = qap_divide(qap, circuit.witness())
    assert division.satisfied and len(division.quotient) <= 7
    assert not qap_divide(qap, (1, 35, 4, 16, 64)).satisfied
    zero = cubic_circuit(x=0, out=5)  # A zero witness entry contributes nothing.
    assert qap_divide(qap, zero.witness()).satisfied
    with pytest.raises(ValueError):
        qap_divide(qap, (1, 2))
    with pytest.raises(TypeError):
        r1cs_to_qap("r1cs")


def test_groth16_proves_and_rejects():
    circuit = cubic_circuit()
    key = groth16_setup(circuit.r1cs(), TRAPDOOR)
    vk = key.verifying_key
    proof = groth16_prove(key, circuit.witness(), seed=1)
    assert groth16_verify(vk, [35], proof)
    assert not groth16_verify(vk, [36], proof)
    other = groth16_prove(key, circuit.witness(), seed=2)
    assert other != proof and groth16_verify(vk, [35], other)
    assert not groth16_verify(vk, [35], replace(proof, c=other.c))
    assert not groth16_verify(vk, [35, 1], proof)
    assert not groth16_verify(vk, [35], "proof")
    assert not groth16_verify(vk, [35], Groth16Proof((1, 1), proof.b, proof.c))
    with pytest.raises(ValueError, match="satisfy"):
        groth16_prove(key, (1, 35, 4, 16, 64))


def test_groth16_setup_validation():
    r1cs = cubic_circuit().r1cs()
    with pytest.raises(TypeError):
        groth16_setup(r1cs, (1, 2, 3, 4, 5))
    with pytest.raises(ValueError, match="nonzero"):
        groth16_setup(r1cs, Groth16Trapdoor(0, 1, 2, 3, 4))
    with pytest.raises(ValueError, match="domain"):
        groth16_setup(r1cs, Groth16Trapdoor(1, 2, 3, 4, 5))  # tau = 1 is a root of unity.
    small = Circuit(97)
    small.assert_equal(small.public(1), 1)
    with pytest.raises(ValueError, match="scalar field"):
        groth16_setup(small.r1cs(), TRAPDOOR)


def test_mimc_hash_and_its_gadget_agree():
    assert mimc_hash(1, 2) != mimc_hash(2, 1)
    circuit = Circuit()
    out = mimc_gadget(circuit, circuit.private(123), circuit.private(456))
    assert out.value == mimc_hash(123, 456)
    assert circuit.num_constraints == 48 and circuit.r1cs().is_satisfied(circuit.witness())
    assert nullifier(5, 6) == mimc_hash(5, 6) and owner_key(5) == mimc_hash(5, 0)
    with pytest.raises(ValueError):
        Note(1, -1, 0, 0)


@pytest.fixture(scope="module")
def spend_key():
    return spend_setup(2, Groth16Trapdoor(5, 6, 7, 8, 9))


def test_zerocash_spends_once_and_hides_the_note(spend_key):
    pool = ShieldedPool(2, spend_key.verifying_key)
    alice, bob = 1111, 2222
    coin = Note(owner_key(alice), 100, rho=1, randomness=77)
    assert pool.mint(coin) == 0 and pool.supply == 100
    assert pool.commitments == (note_commitment(coin),)
    payment = Note(owner_key(bob), 60, rho=2, randomness=88)
    spend = prove_spend(spend_key, pool, alice, coin, 0, payment, 40)
    assert spend.nullifier == nullifier(alice, 1) and spend.public_value == 40
    assert pool.spend(spend) == 1 and pool.supply == 60
    assert pool.nullifiers == {spend.nullifier}
    with pytest.raises(ValueError, match="double spend"):
        pool.spend(spend)
    change = Note(owner_key(alice), 60, rho=3, randomness=9)
    second = prove_spend(spend_key, pool, bob, payment, 1, change, 0, seed=4)
    with pytest.raises(ValueError, match="invalid"):
        pool.spend(replace(second, public_value=10))
    with pytest.raises(ValueError, match="range"):
        pool.spend(replace(second, public_value=-1))
    with pytest.raises(ValueError, match="root"):
        pool.spend(replace(second, root=12345))
    assert pool.spend(second) == 2


def test_zerocash_rejects_thieves_and_inflation(spend_key):
    pool = ShieldedPool(2, spend_key.verifying_key)
    coin = Note(owner_key(1111), 100, rho=1, randomness=77)
    pool.mint(coin)
    with pytest.raises(ValueError, match="satisfy"):
        prove_spend(spend_key, pool, 9999, coin, 0, Note(owner_key(9999), 100, 2, 3), 0)
    inflated = Note(owner_key(1111), FIELD_PRIME - 1000, 2, 3)  # A "negative" 1000 coins.
    with pytest.raises(ValueError, match="satisfy"):
        prove_spend(spend_key, pool, 1111, coin, 0, inflated, 1100)


def test_shielded_pool_bookkeeping(spend_key):
    pool = ShieldedPool(1, spend_setup(1, Groth16Trapdoor(5, 6, 7, 8, 9)).verifying_key)
    pool.mint(Note(1, 1, 1, 1))
    pool.mint(Note(1, 1, 2, 1))
    with pytest.raises(ValueError, match="full"):
        pool.mint(Note(1, 1, 3, 1))
    with pytest.raises(IndexError):
        pool.siblings(2)
    with pytest.raises(TypeError):
        pool.mint((1, 1, 1, 1))
    with pytest.raises(TypeError):
        ShieldedPool(2, "key")
    with pytest.raises(ValueError):
        spend_circuit(2, 1, Note(1, 1, 1, 1), [0], 0, Note(1, 1, 1, 1), 0)


def plonk_cubic(x=3, total=30):
    circuit = PlonkCircuit()
    v = circuit.variable(x)
    circuit.assert_constant(circuit.add(circuit.mul(circuit.mul(v, v), v), v), total)
    return circuit


def test_plonk_proves_and_rejects_with_one_universal_setup():
    srs = trusted_setup(48, 4321)
    circuit = plonk_cubic()
    assert circuit.is_satisfied() and circuit.wire_values()[0] == (3, 3, 9)
    key = plonk_setup(circuit, srs)
    proof = plonk_prove(key, srs, circuit.wire_values())
    assert plonk_verify(key, srs, proof)
    other = PlonkCircuit()
    v = other.variable(2)
    for _ in range(5):
        v = other.mul(v, v)
    other.assert_constant(v, 2**32 % FIELD_PRIME)
    other_key = plonk_setup(other, srs)
    other_proof = plonk_prove(other_key, srs, other.wire_values())
    assert plonk_verify(other_key, srs, other_proof)
    assert not plonk_verify(key, srs, other_proof)
    evaluations = list(proof.evaluations)
    evaluations[0] += 1
    assert not plonk_verify(key, srs, replace(proof, evaluations=tuple(evaluations)))
    evaluations = list(proof.evaluations)
    evaluations[13] += 1
    assert not plonk_verify(key, srs, replace(proof, evaluations=tuple(evaluations)))
    assert not plonk_verify(key, srs, replace(proof, opening=proof.shifted_opening))
    assert not plonk_verify(key, srs, replace(proof, evaluations=proof.evaluations[:13]))
    assert not plonk_verify(key, srs, "proof")
    assert not plonk_verify(key, srs, replace(proof, t=(1, 1)))
    assert not plonk_verify(key, srs, replace(proof, evaluations=("x",) * 14))
    assert isinstance(proof, PlonkProof)


def test_plonk_copy_constraints_need_the_grand_product():
    srs = trusted_setup(24, 4321)
    circuit = plonk_cubic()
    key = plonk_setup(circuit, srs)
    honest = permutation_product(key, circuit.wire_values(), 5, 7)
    assert honest[0] == 1 and honest[-1] == 1 and len(honest) == key.n + 1
    rows = [list(row) for row in circuit.wire_values()]
    rows[0] = [2, 2, 4]  # Still a valid multiplication, but x is now 2 here and 3 elsewhere.
    assert permutation_product(key, rows, 5, 7)[-1] != 1
    with pytest.raises(ValueError, match="copy constraint"):
        plonk_prove(key, srs, rows)
    rows[0] = [3, 3, 10]
    with pytest.raises(ValueError, match="gate 0"):
        plonk_prove(key, srs, rows)
    with pytest.raises(ValueError, match="rows"):
        permutation_product(key, [[1, 2]], 5, 7)


def test_plonk_validation():
    circuit = PlonkCircuit()
    v = circuit.variable(1)
    with pytest.raises(IndexError):
        circuit.gate(v, v, 5)
    with pytest.raises(TypeError):
        circuit.gate(v, v, v, ql=1.0)
    with pytest.raises(TypeError):
        circuit.variable(1.0)
    with pytest.raises(ValueError, match="at least one gate"):
        plonk_setup(circuit, trusted_setup(8, 3))
    circuit.assert_constant(v, 1)
    with pytest.raises(ValueError, match="degree"):
        plonk_setup(circuit, trusted_setup(4, 3))
    small = PlonkCircuit(97)
    small.assert_constant(small.variable(1), 1)
    with pytest.raises(ValueError, match="scalar field"):
        plonk_setup(small, trusted_setup(8, 3))


def test_kzg_on_a_curve_without_pairing_fails_closed():
    srs = SRS((TOY_CURVE.generator,) * 2, TOY_CURVE)
    assert not kzg_verify(TOY_CURVE.generator, KZGOpening(0, 0, None), srs)
