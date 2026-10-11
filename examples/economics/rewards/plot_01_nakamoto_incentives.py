r"""
Nakamoto's incentive: block rewards and fees (2008)
===================================================

Section 6 of the Bitcoin paper pays whoever creates a block in new coins
and in the fees of the transactions it includes. The reward distributes the
currency, pays for the work that secures the chain, and, Nakamoto argued,
keeps even a powerful miner honest: it "ought to find it more profitable to
play by the rules ... than to undermine the system and the validity of his
own wealth."

The experiment makes the argument quantitative. A miner of share
:math:`\alpha` can mine :math:`m = z + 1` blocks honestly, earning
:math:`mR`, or spend them on a private chain that reverses a payment of
value :math:`V` to a merchant waiting :math:`z` confirmations. With the
catch-up probability :math:`P_z` of the whitepaper,

.. math::

   \text{attack} = P_z \left(V + (1 - d)\, m R\right) \quad \text{vs} \quad \text{honest} = m R,

where :math:`d` is the fraction of its rewards' worth the attacker expects
to lose if the attack shakes confidence in the coin.
"""

# %%
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

# %%
# What a block pays
# -----------------

# The first block after the fourth halving, in April 2024, collected over 37 BTC
# in fees, more than ten times its subsidy; a typical block then paid well under 1 BTC.
COIN = 100_000_000
height = 840_000
subsidy = bk.economics.block_subsidy(height)
for fees in (37 * COIN, COIN // 4):
    reward = bk.economics.block_reward(height, fees)
    print(f"block {height}: subsidy {subsidy / COIN} BTC, reward {reward / COIN:.2f} BTC")
assert bk.economics.block_reward(height, 37 * COIN) > 10 * subsidy

# %%
# When a double spend pays
# ------------------------

alphas = np.linspace(0.05, 0.6, 56)
DEVALUATION = 0.5
fig, ax = plt.subplots(figsize=(7.5, 4.5))
for confirmations, color in ((1, "#dc2626"), (3, "#d97706"), (6, "#2563eb")):
    m = confirmations + 1
    breakeven = []
    for alpha in alphas:
        p = bk.economics.double_spend_incentive(
            alpha, reward=1, payment=1, confirmations=confirmations
        ).success_probability
        # The payment, in block rewards, at which attacking and mining honestly tie.
        v = m * (1 - p * (1 - DEVALUATION)) / p
        for factor, pays in ((0.99, False), (1.01, True)):
            result = bk.economics.double_spend_incentive(
                alpha,
                reward=1,
                payment=v * factor,
                confirmations=confirmations,
                devaluation=DEVALUATION,
            )
            assert result.attack_pays == pays
        breakeven.append(v)
    ax.semilogy(alphas, breakeven, color=color, label=f"{confirmations} confirmations")
ax.axvline(0.5, color="black", linestyle=":")
ax.set(xlabel="attacker hashrate alpha", ylabel="payment worth attacking (block rewards)")
ax.set_title("Honest mining pays unless the payment is worth many blocks")
ax.legend()
fig.tight_layout()

small = bk.economics.double_spend_incentive(0.1, reward=3.125, payment=100, confirmations=6)
print(
    f"10% miner, 100 BTC payment: P = {small.success_probability:.1e}, "
    f"attack pays: {small.attack_pays}"
)
assert not small.attack_pays
majority = bk.economics.double_spend_incentive(
    0.6, reward=3.125, payment=5, confirmations=6, devaluation=0.5
)
assert majority.success_probability == 1 and not majority.attack_pays  # Its own wealth at stake.

plt.show()

# %%
# Exercise
# --------
# Without devaluation (d = 0), a majority miner's attack always pays. How
# large must the devaluation be for a 60% miner to leave a 5 BTC payment
# alone, with a 3.125 BTC reward and six confirmations?
