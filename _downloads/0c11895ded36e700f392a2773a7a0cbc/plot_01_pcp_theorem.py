r"""
The PCP theorem: checking a proof by reading a few bits (1992)
==============================================================

Arora and Safra, and Arora, Lund, Motwani, Sudan and Szegedy, proved that
every NP statement has a *probabilistically checkable proof*: a verifier
tosses coins, reads a constant number of the proof's bits, and accepts a
correct proof always and an incorrect one with probability at most 1/2.
Repeating drives the error down to :math:`2^{-k}`.

Its first ingredient is a proof that is exponentially long but very easy to
check. To show that quadratic equations over GF(2) have a solution
:math:`u`, write out every parity :math:`\langle u, x\rangle` and every
:math:`\langle u \otimes u, y\rangle`. The verifier checks with 14 queries
that both tables are linear (the Blum-Luby-Rubinfeld test,
:math:`f(x) + f(y) = f(x + y)`), that the second is the tensor square of the
first, and that a random sum of the equations holds.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A system with two solutions
# ---------------------------
# u0 u1 + u2 = 1, u1 u2 = 0, and u0 + u1 = 0.

system = bk.proofs.QuadraticSystem(
    3, ((((0, 1), (2, 2)), 1), (((1, 2),), 0), (((0, 0), (1, 1)), 0))
)
print("solutions:", system.solutions())
proof = bk.proofs.hadamard_proof([1, 1, 0])
print(f"the proof has {len(proof.bits)} bits for a 3-bit witness")
assert all(bk.proofs.pcp_verify(system, proof, seed=s).accepted for s in range(200))

# %%
# Wrong proofs are caught with constant probability per repetition
# ----------------------------------------------------------------

wrong_assignment = bk.proofs.hadamard_proof([1, 0, 1])  # Well formed, but not a solution.
corrupted_bits = list(proof.bits)
for i in range(8, 520, 3):
    corrupted_bits[i] ^= 1  # A third of the quadratic table flipped.
corrupted = bk.proofs.HadamardProof(tuple(corrupted_bits[:8]), tuple(corrupted_bits[8:]))
unsatisfiable = bk.proofs.QuadraticSystem(2, ((((0, 0),), 1), (((0, 0),), 0)))

repetitions = range(1, 9)
cases = {
    "non-solution, encoded correctly": (system, wrong_assignment),
    "solution, one third corrupted": (system, corrupted),
    "unsatisfiable system": (unsatisfiable, bk.proofs.hadamard_proof([1, 0])),
}
rates = {}
for label, (statement, candidate) in cases.items():
    rates[label] = [
        sum(
            bk.proofs.pcp_verify(statement, candidate, repetitions=k, seed=s).accepted
            for s in range(400)
        )
        / 400
        for k in repetitions
    ]
    print(
        f"{label}: accepted {rates[label][0]:.0%} with 14 queries, {rates[label][-1]:.1%} with 112"
    )
    assert rates[label][-1] < 0.05

fig, ax = plt.subplots(figsize=(7, 4.5))
for (label, rate), color in zip(rates.items(), ("#2563eb", "#dc2626", "#16a34a"), strict=True):
    ax.semilogy(
        [14 * k for k in repetitions], [max(r, 1e-3) for r in rate], "o-", color=color, label=label
    )
ax.semilogy(
    [14 * k for k in repetitions], [0.5**k for k in repetitions], "k:", label="1 / 2 per repetition"
)
ax.set(xlabel="proof bits read", ylabel="probability a wrong proof is accepted")
ax.set_title("A Hadamard PCP read a few bits at a time")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A Hadamard proof for n variables has 2**n + 2**(n**2) bits. For n = 10, how
# many bits is that, and how many does the verifier read for an error below
# one in a million, assuming each repetition halves it?
# A worked solution is in :doc:`/exercises/proofs`.
