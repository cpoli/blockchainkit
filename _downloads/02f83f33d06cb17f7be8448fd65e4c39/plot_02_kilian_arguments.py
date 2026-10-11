r"""
Kilian's succinct arguments: a Merkle-committed PCP (1992)
==========================================================

A PCP is cheap to check but expensive to send. Kilian's argument sends only
a Merkle root of it. The verifier then chooses its queries, and the prover
opens each queried bit with its authentication path. Changing an answer
after committing would mean finding a SHA-256 collision, so the prover is
bound to one proof, and the conversation costs

.. math::

   32 + q \left(1 + 32 \lceil \log_2 N \rceil\right) \text{ bytes}

for :math:`q` queries into an :math:`N`-bit proof: logarithmic in the proof
it stands for. Soundness now holds only against provers who cannot find
collisions, which makes this an *argument* rather than a proof.
"""

# %%
import math

import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# One run, and a prover who changes its answers
# ---------------------------------------------

system = bk.proofs.QuadraticSystem(3, ((((0, 1), (2, 2)), 1), (((1, 2),), 0)))
proof = bk.proofs.hadamard_proof(list(system.solutions()[0]))
run = bk.proofs.kilian_argument(system, proof, repetitions=4, seed=1)
print(
    f"{run.queries} bits opened, {run.communication} bytes sent, for a {run.proof_length}-bit PCP"
)
assert run.accepted

lying = bk.proofs.kilian_argument(
    system, proof, repetitions=4, seed=1, respond=lambda i: 1 - proof.bits[i]
)
assert not lying.accepted  # Its answers no longer match the committed root.

# %%
# Communication grows with log N, the PCP with N
# ----------------------------------------------

sizes, sent = [], []
for n in range(1, 5):
    statement = bk.proofs.QuadraticSystem(n, ((((0, 0),), 1),))
    pcp = bk.proofs.hadamard_proof([1] * n)
    result = bk.proofs.kilian_argument(statement, pcp, repetitions=20)
    assert result.accepted
    sizes.append(result.proof_length)
    sent.append(result.communication)
for n in range(5, 9):  # Beyond n = 4 the PCP is too long to build; count its bytes instead.
    length = 2**n + 2 ** (n * n)
    sizes.append(length)
    sent.append(32 + 280 * (9 + 32 * math.ceil(math.log2(length))))
print("PCP bits:", sizes[-1], "argument bytes:", sent[-1])
assert sent[-1] * 8 < sizes[-1]

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.loglog(sizes, [s / 8 for s in sizes], "o-", color="#dc2626", label="sending the whole PCP")
ax.loglog(sizes, sent, "o-", color="#2563eb", label="Kilian: root plus 280 openings")
ax.axvline(sizes[3], color="#64748b", linestyle=":", label="measured up to here")
ax.set(xlabel="PCP length (bits)", ylabel="bytes the prover sends")
ax.set_title("Merkle commitments make PCPs succinct")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Kilian's verifier must pick its queries *after* receiving the root. Show
# what goes wrong if the prover learns the queries first: write a ``respond``
# function that answers the queried bits so that a non-solution passes.
