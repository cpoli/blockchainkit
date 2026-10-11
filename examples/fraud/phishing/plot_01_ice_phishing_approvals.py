r"""
Approval ("ice") phishing on ERC-20 allowances (2022)
=====================================================

An ERC-20 ``approve`` lets a spender move the owner's tokens later without
asking again. Exchanges ask once for an unlimited allowance, so users learn
to sign approvals without reading them. In February 2022 Microsoft named
*ice phishing* the attack that exploits this: a fake airdrop or mint page
asks the victim to approve the attacker's contract, and the attacker
empties the wallet whenever it likes. Nothing is stolen from the keys; the
signature the victim reads in the wallet is the whole attack:

.. code-block:: solidity

   token.approve(0x9a1f...c3d7, type(uint256).max);   // "Claim your airdrop"

What a wallet stands to lose is the sum, over its tokens, of

.. math::

   \min\Big(\text{balance},\; \sum_{\text{spenders}} \text{allowance}\Big),

and revoking, approving 0, brings a spender's share back to nothing.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# One signature on a fake airdrop page
# ------------------------------------

world = bk.contracts.World()
usdc = world.deploy("issuer", bk.contracts.ERC20, 10**6, name="USDC")
dai = world.deploy("issuer", bk.contracts.ERC20, 10**6, name="DAI")
world.transact("issuer", usdc, "transfer", "victim", 5_000)
world.transact("issuer", dai, "transfer", "victim", 3_000)
drainer = world.deploy("attacker", bk.fraud.Drainer, name="AirdropClaim")
receipts = [
    world.transact("victim", usdc, "approve", "dex", bk.fraud.UNLIMITED),  # A real exchange.
    world.transact("victim", usdc, "approve", drainer, bk.fraud.UNLIMITED),  # The phish.
    world.transact("victim", dai, "approve", drainer, 1_000),
]
approvals = bk.fraud.open_approvals(receipts, "victim")
exposed = bk.fraud.allowance_exposure(world, "victim", approvals)
print("standing approvals:", len(approvals), "| at risk:", exposed)
assert exposed == 6_000

# %%
# Months later: one revoked, one forgotten
# ----------------------------------------

world.advance(blocks=200_000)
receipts.append(world.transact("victim", dai, "approve", drainer, 0))
remaining = bk.fraud.open_approvals(receipts, "victim")
print("after revoking DAI:", bk.fraud.allowance_exposure(world, "victim", remaining), "at risk")
swept = [world.transact("attacker", drainer, "sweep", t, "victim").result for t in (usdc, dai)]
print("swept USDC, DAI:", swept)
assert swept == [5_000, 0]

fig, ax = plt.subplots(figsize=(7, 3.5))
labels = ["USDC (approved, forgotten)", "DAI (approved, revoked)"]
ax.barh(labels, [5_000, 3_000], color="#cbd5e1", label="held")
ax.barh(labels, swept, color="#dc2626", label="taken by the drainer")
ax.set(xlabel="tokens", title="An allowance outlives the page that asked for it")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# EIP-2612 replaces the ``approve`` transaction with a signed ``permit``
# message that anyone can submit. Why does this make ice phishing easier to
# carry out and harder to notice?
