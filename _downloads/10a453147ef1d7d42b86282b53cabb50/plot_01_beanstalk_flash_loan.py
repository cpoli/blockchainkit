r"""
Governance attacks: Beanstalk's flash-loan vote (2022)
======================================================

A *flash loan* lends any amount without collateral, on one condition: it
is repaid before the transaction ends, or the whole transaction, loan
included, reverts. For the length of one transaction, anyone can be as
rich as the lender.

Beanstalk let token holders pass a proposal at once with an
``emergencyCommit``, given two thirds of the voting power and a day after
the proposal was made. On 17 April 2022 an attacker who had proposed
sending the treasury to itself the day before took flash loans worth about
a billion dollars, turned them into voting power, voted, committed the
proposal and repaid, netting about 80 million dollars. The vote passed
because

.. math::

   \frac{\text{borrowed} + \text{own}}{\text{supply}} \ge \frac{2}{3}

held for the duration of a single transaction. Counting votes at a
*snapshot*, the balances at the end of the block before the proposal,
defeats the attack: no flash loan can change the past.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts.visualizers import plot_call_tree

# %%
# A treasury, a lender, and a proposal
# ------------------------------------


def stage(snapshot):
    world = bk.contracts.World()
    token = world.deploy("dao", bk.contracts.VotesToken, 1_000_000, name="token")
    governance = world.deploy("dao", bk.contracts.Governance, token, snapshot, name="governance")
    world.fund("dao", 10_000)
    world.transact("dao", governance, value=10_000)
    lender = world.deploy("bank", bk.contracts.FlashLender, token, name="lender")
    world.transact("dao", token, "transfer", lender, 900_000)
    attacker = world.deploy("attacker", bk.contracts.GovernanceAttacker, name="attack contract")
    world.advance()
    pid = world.transact("attacker", governance, "propose", attacker, 10_000).result
    world.advance(blocks=7_200, seconds=86_400)  # A day later.
    receipt = world.transact("attacker", attacker, "attack", lender, governance, pid, 900_000)
    return world, token, lender, receipt


world, token, lender, attack = stage(snapshot=False)
print("current-balance voting:", attack.success, "attacker gains", world.balance("attacker"))
assert attack.success and world.balance("attacker") == 10_000
assert world.view(token, "balance_of", lender) == 900_000  # The loan was repaid.

safe_world, _, _, defended = stage(snapshot=True)
print("snapshot voting:", defended.error)
assert defended.error == "below the two-thirds majority" and safe_world.balance("attacker") == 0

fig, ax = plt.subplots(figsize=(10, 5))
plot_call_tree(attack, names=world.name, ax=ax)
ax.set_title("One transaction: borrow, vote, commit, repay. " + ax.get_title())
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# With snapshot voting, could the attacker still win by flash-borrowing in
# the block *before* proposing? What does that require of the lender, and
# why does a delay between proposal and vote also help?
