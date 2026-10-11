r"""
Groth16: three group elements per proof (2016)
==============================================

Groth found the shortest pairing-based SNARK: a proof is three group
elements :math:`(A, B, C)`, and the verifier checks one equation,

.. math::

   e(A, B) = e(\alpha, \beta)\; e\Big(\sum_{i \le \ell} x_i L_i, \gamma\Big)\; e(C, \delta),

where the setup encodes the circuit's QAP at a secret point :math:`\tau`,
blinded by secrets :math:`\alpha, \beta, \gamma, \delta`. The prover adds
fresh random :math:`r, s` to every proof, so two proofs of the same
statement look unrelated: they reveal nothing but the public inputs.
Proofs stay the same size however large the circuit, which is why Zcash
(Sapling), Tornado Cash and many rollups use Groth16.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

TRAPDOOR = bk.proofs.Groth16Trapdoor(tau=1001, alpha=22, beta=33, gamma=44, delta=55)

# %%
# Prove x**3 + x + 5 = 35 without revealing x
# -------------------------------------------

circuit = bk.proofs.Circuit()
out, x = circuit.public(35), circuit.private(3)
circuit.assert_equal(circuit.mul(circuit.mul(x, x), x) + x + 5, out)
key = bk.proofs.groth16_setup(circuit.r1cs(), TRAPDOOR)
first = bk.proofs.groth16_prove(key, circuit.witness(), seed=1)
second = bk.proofs.groth16_prove(key, circuit.witness(), seed=2)
vk = key.verifying_key
assert bk.proofs.groth16_verify(vk, [35], first) and bk.proofs.groth16_verify(vk, [35], second)
assert first != second  # Rerandomized: nothing links the two proofs.
assert not bk.proofs.groth16_verify(vk, [36], first)
print("proof A:", first.a)

# %%
# The proof does not grow with the circuit
# ----------------------------------------
# Prove knowledge of a cube root chain: y = x**(3**k) for growing k.

constraints, elements = [], []
for k in (1, 4, 16, 64, 256):
    chain = bk.proofs.Circuit()
    y = chain.public(pow(2, 3**k, bk.proofs.FIELD_PRIME))
    value = chain.private(2)
    for _ in range(k):
        value = chain.mul(chain.mul(value, value), value)
    chain.assert_equal(value, y)
    chain_key = bk.proofs.groth16_setup(chain.r1cs(), TRAPDOOR)
    proof = bk.proofs.groth16_prove(chain_key, chain.witness())
    assert bk.proofs.groth16_verify(chain_key.verifying_key, chain.public_inputs(), proof)
    constraints.append(chain.r1cs().num_constraints)
    elements.append(3)
print("constraints:", constraints, "-> always 3 group elements")

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.loglog(constraints, constraints, "o-", color="#dc2626", label="witness size (field elements)")
ax.loglog(constraints, elements, "o-", color="#2563eb", label="Groth16 proof (group elements)")
ax.set(xlabel="constraints", ylabel="elements", title="Groth16 proofs have constant size")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The verifier's work is three pairings plus one point multiplication per
# public input. Add 10 public inputs to the cube-chain circuit and check that
# proofs still verify; which part of the verifying key grew?
