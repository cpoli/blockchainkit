r"""
Traceability in Monero: when decoys fail (2018)
===============================================

Möser, Soska, Heilman, Lee, Heffan, Srivastava, Hogan, Hennessey, Miller,
Narayanan and Christin, and independently Kumar, Fischer, Tople and
Saxena, showed that most early Monero inputs could be traced.

- **Zero-mixin chain reaction.** A ring with no decoys reveals its
  output. Struck from every other ring, it can leave some of them with one
  member, which reveals theirs, and so on.
- **Guess-newest.** Coins are usually spent soon after they arrive, but
  decoys were drawn uniformly from all history, so the newest member was
  usually the real one.

If a ring of size :math:`n` mixes the real output with decoys of the same
age distribution, guessing the newest is right with probability about
:math:`1/n`; with uniform decoys, it approaches 1 as the chain grows.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.privacy.visualizers import plot_ring_positions

# %%
# The chain reaction
# ------------------
# Early Monero: rings of two, most without decoys.

early = bk.privacy.simulate_rings(2_000, 900, ring_size=2, zero_mixin=0.6, seed=5)
report = bk.privacy.trace_rings(early)
cascade = report.deduced - report.zero_mixin
print(f"{report.zero_mixin} zero-mixin inputs; the chain reaction traces {cascade} more")
assert cascade > 0
larger = bk.privacy.trace_rings(
    bk.privacy.simulate_rings(2_000, 900, ring_size=5, zero_mixin=0.6, seed=5)
)
print(f"with rings of five it traces {larger.deduced - larger.zero_mixin} more")

# %%
# Guess-newest, and the fix
# -------------------------

uniform = bk.privacy.simulate_rings(5_000, 1_000, ring_size=5, sampling="uniform", seed=7)
recent = bk.privacy.simulate_rings(5_000, 1_000, ring_size=5, sampling="recent", seed=7)
for name, rings in (("uniform decoys", uniform), ("age-matched decoys", recent)):
    print(f"{name}: newest is real in {bk.privacy.trace_rings(rings).newest_correct / 10:.0f}%")
assert (
    bk.privacy.trace_rings(uniform).newest_correct
    > 2 * bk.privacy.trace_rings(recent).newest_correct
)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
plot_ring_positions(uniform, ax=ax1)
ax1.set_title("Uniform decoys: " + ax1.get_title())
plot_ring_positions(recent, ax=ax2)
ax2.set_title("Age-matched decoys: " + ax2.get_title())
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Monero made rings of size 11 mandatory in 2018. Using
# :func:`~blockchainkit.privacy.systems.traceability.simulate_rings`, how
# much of a ledger with 60% zero-mixin rings of size 2 does the chain
# reaction trace, and how much once the other 40% have size 11?
# A worked solution is in :doc:`/exercises/privacy`.
