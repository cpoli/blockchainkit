"""
Partial synchrony: timeouts that eventually work (Dwork, Lynch and Stockmeyer 1988)
===================================================================================

Real networks are usually fast but sometimes not. Dwork, Lynch and
Stockmeyer modelled this as partial synchrony: message delays are unbounded
until an unknown Global Stabilization Time (GST), and bounded by an unknown
Delta afterwards. A leader-based protocol keeps safety at all times and
waits out each leader with a timeout. Doubling the timeout every failed view
guarantees it eventually exceeds Delta, whatever Delta is.

What to look for
----------------

Views fail until GST; the first view that starts after GST with a long
enough timeout makes progress. With a fixed timeout below Delta, no view
ever succeeds. PBFT, Tendermint and HotStuff all rely on this model.

The history behind this experiment: :doc:`/history/consensus_breakthroughs`.
"""

# %%
# Views before and after GST
# --------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk

run = bk.consensus.view_changes(gst=300, delta=40, base_timeout=5)
print(f"view {run.decided_view} decides at t = {run.decision_time}")
assert run.view_starts[run.decided_view] >= 300 and run.timeouts[run.decided_view] >= 40

try:
    bk.consensus.view_changes(gst=0, delta=40, base_timeout=5, growth=1, max_views=100)
except TimeoutError:
    print("fixed 5-tick timeouts never outlast a 40-tick delay")

# %%
# Progress time grows only linearly with GST
# ------------------------------------------
gsts = list(range(0, 2001, 100))
decisions = [bk.consensus.view_changes(gst=g, delta=40, base_timeout=5).decision_time for g in gsts]
assert all(d >= g for d, g in zip(decisions, gsts, strict=True))
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(gsts, decisions, "o-", label="decision time")
ax.plot(gsts, gsts, "--", color="black", label="GST")
ax.set(
    xlabel="global stabilization time",
    ylabel="time",
    title="Doubling timeouts: progress soon after GST",
)
ax.legend()
fig.tight_layout()

# %%
# Exercise
# --------
# Doubling can overshoot: after a long asynchronous period the timeout may be
# far larger than Delta. What does that cost after GST, and why do some
# protocols reset the timeout after a successful view?
