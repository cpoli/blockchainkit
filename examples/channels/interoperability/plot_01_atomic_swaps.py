r"""
Tier Nolan's atomic cross-chain swaps (2013)
============================================

Alice has coins on chain A, Bob on chain B, and neither will pay first.
Tier Nolan's protocol ties both payments to one secret. Alice locks her
coins to Bob behind the hash of a secret, refundable to her at
:math:`T_A`; Bob locks his to Alice behind the same hash, refundable at
:math:`T_B`. Alice claims on B by revealing the secret, and Bob reads it
there and claims on A. The swap is atomic if

.. math::

   T_A > T_B + \text{Bob's reaction time},

because Alice must reveal before :math:`T_B` to be paid, and Bob then has
until :math:`T_A` to use the secret.
"""

# %%
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

# %%
# Honest parties, and Alice walking away
# --------------------------------------


def new_swap(timeout_a, timeout_b):
    swap = bk.channels.AtomicSwap(
        7, 5, b"swap secret", amount_a=10, amount_b=3, timeout_a=timeout_a, timeout_b=timeout_b
    )
    swap.lock_bob()
    return swap


honest = new_swap(48, 24)
assert honest.claim_b(height=10) and honest.claim_a(height=11)
print("honest:", honest.outcome())

walked = new_swap(48, 24)  # Alice never claims; both refund.
assert walked.refund_b(height=24) and walked.refund_a(height=48)
assert walked.outcome().refunded

# %%
# Alice's best strategy against each pair of timeouts
# ---------------------------------------------------
# Alice reveals the secret on B at some height before Bob's refund at
# T_B = 24, and also takes her refund on A the moment T_A arrives. Bob
# claims on A one block after the secret appears.

margins = range(-12, 13, 3)  # T_A - T_B.
claims = range(4, 24, 3)  # The height at which Alice reveals.
grid = np.zeros((len(claims), len(margins)))
for j, margin in enumerate(margins):
    timeout_b = 24
    for i, reveal in enumerate(claims):
        swap = new_swap(timeout_b + margin, timeout_b)
        events = sorted([(reveal, "claim"), (timeout_b + margin, "refund")])
        for height, action in events:
            if action == "claim" and swap.claim_b(height=height):
                swap.claim_a(height=height + 1)
            elif action == "refund":
                swap.refund_a(height=height)
        grid[i, j] = swap.outcome().atomic
print("atomic for every reveal height when T_A - T_B >= 3:", grid[:, margins.index(3)].all())
assert grid[:, margins.index(3) :].all() and not grid[:, : margins.index(0)].all()

fig, ax = plt.subplots(figsize=(8, 4))
ax.imshow(grid, origin="lower", cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)
ax.set_xticks(range(len(margins)), labels=list(margins))
ax.set_yticks(range(len(claims)), labels=list(claims))
ax.set(xlabel="T_A - T_B (blocks)", ylabel="height at which Alice reveals")
ax.set_title("Green: nobody loses. Red: Alice keeps both coins")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# Even with safe timeouts, Alice holds a free option: after Bob locks, she
# can wait until just before ``T_B`` and complete the swap only if the
# exchange rate has moved in her favour. How long does the option last,
# and what could Bob charge for it?
