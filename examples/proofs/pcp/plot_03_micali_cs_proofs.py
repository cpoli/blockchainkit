r"""
Micali's computationally sound proofs: hashing the verifier away (1994)
=======================================================================

Micali made Kilian's argument non-interactive: the queries are derived by
hashing the Merkle root, so the prover can write the whole argument down at
once, and anyone can check it later. If the hash behaves like a random
oracle, the prover cannot predict which bits will be read before committing.

But it can try again. A cheating prover recommits (here, it changes a salt
hashed with the root) until the derived queries happen to miss its lies. If
one repetition catches a false proof with probability 1/2, the expected
number of attempts is

.. math::

   \mathbb{E}[\text{attempts}] = 2^{k}

for :math:`k` repetitions: the soundness of a non-interactive proof is a
cost in hashing, which is why deployed systems target :math:`2^{100}` or more.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# An honest proof anyone can check
# --------------------------------

system = bk.proofs.QuadraticSystem(
    3, ((((0, 1), (2, 2)), 1), (((1, 2),), 0), (((0, 0), (1, 1)), 0))
)
honest = bk.proofs.micali_proof(system, bk.proofs.hadamard_proof([1, 1, 0]), repetitions=8)
assert bk.proofs.verify_cs_proof(system, honest, repetitions=8)
print(f"a CS proof of {len(honest.openings)} openings and {honest.size} bytes")

# %%
# Grinding: a false proof, rehashed until the queries miss
# --------------------------------------------------------

false_proof = bk.proofs.hadamard_proof([1, 0, 1])  # Encodes a non-solution.
repetitions = range(1, 8)
attempts = []
for k in repetitions:
    tries = []
    for start in range(0, 6 * 2**k * 4, 6 * 2**k):  # Four independent searches.
        salt = start
        while not bk.proofs.verify_cs_proof(
            system,
            bk.proofs.micali_proof(system, false_proof, repetitions=k, salt=salt),
            repetitions=k,
        ):
            salt += 1
        tries.append(salt - start + 1)
    attempts.append(sum(tries) / len(tries))
    print(f"{k} repetitions: about {attempts[-1]:.0f} attempts to forge")
assert attempts[-1] > 8 * attempts[0]

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.semilogy(repetitions, attempts, "o", color="#dc2626", label="measured, mean of 4 searches")
ax.semilogy(repetitions, [2**k for k in repetitions], color="#2563eb", label="2**k")
ax.set(xlabel="repetitions k", ylabel="attempts until a false proof passes")
ax.set_title("Non-interactive soundness is a price in hashes")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# How many repetitions would make grinding cost 2**80 hashes, if every
# attempt rebuilds a 520-leaf Merkle tree? How many bytes is the proof then?
