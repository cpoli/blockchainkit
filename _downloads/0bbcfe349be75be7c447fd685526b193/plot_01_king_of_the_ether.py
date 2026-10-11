r"""
King of the Ether: unchecked send and the pull-payment pattern (2016)
=====================================================================

*King of the Ether* sold a throne. Each claimant paid more than the
current price, the deposed king received the payment less a 1% fee, and
the price rose by half. The contract paid with ``send``, which forwards
only 2,300 gas and returns False on failure. In February 2016 some kings
used Mist's contract wallets, whose code for receiving ether needed more
than 2,300 gas; their payments failed, the contract ignored the False,
crowned the next king, and kept the money.

Checking the result only moves the problem: a king who *refuses* every
payment then reigns forever, since nobody can be crowned without paying
him. The lasting fix is the *pull-payment* pattern: record what each
deposed king is owed and let each withdraw it, with as much gas as they
like, in their own transaction. A failure then harms only the one who
causes it.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A contract wallet becomes king, then is deposed
# -----------------------------------------------


def reign(throne_code):
    world = bk.contracts.World()
    for account in ("owner", "alice", "bob"):
        world.fund(account, 10_000)
    throne = world.deploy("owner", throne_code, 100, name="throne")
    wallet = world.deploy("alice", bk.contracts.ContractWallet, name="alice's wallet")
    world.fund(wallet, 1_000)
    world.transact("alice", wallet, "forward", throne, "claim_throne", 100)
    deposed = world.transact("bob", throne, "claim_throne", value=1_000)
    if throne_code is bk.contracts.PullKingOfTheEther:
        world.transact("alice", wallet, "forward", throne, "withdraw", 0)
    return world, throne, wallet, deposed


summary = {}
for code in (
    bk.contracts.KingOfTheEther,
    bk.contracts.CheckedKingOfTheEther,
    bk.contracts.PullKingOfTheEther,
):
    world, throne, wallet, deposed = reign(code)
    compensation = world.balance(wallet) - 900
    summary[code.__name__] = (deposed.success, compensation, world.view(throne, "king"))
    print(f"{code.__name__:22s} Bob crowned: {deposed.success}, Alice compensated: {compensation}")

assert summary["KingOfTheEther"][:2] == (True, 0)  # Crowned, but Alice lost her 990.
assert summary["CheckedKingOfTheEther"][0] is False  # Nobody can dethrone her.
assert summary["PullKingOfTheEther"][:2] == (True, 990)

# %%
# A king who refuses payment
# --------------------------

world = bk.contracts.World()
world.fund("mallory", 1_000)
world.fund("carol", 100_000)
throne = world.deploy("owner", bk.contracts.CheckedKingOfTheEther, 100)
usurper = world.deploy("mallory", bk.contracts.Usurper)
world.transact("mallory", usurper, "claim", throne, value=100)
offers = [150, 1_000, 10_000, 90_000]
blocked = [not world.transact("carol", throne, "claim_throne", value=v).success for v in offers]
assert all(blocked) and world.view(throne, "king") == usurper

fig, ax = plt.subplots(figsize=(8, 4))
names = list(summary)
ax.bar(names, [summary[n][1] for n in names], color=["#dc2626", "#d97706", "#16a34a"])
for i, name in enumerate(names):
    note = "Bob crowned" if summary[name][0] else "Bob refused"
    ax.text(i, 30, note, ha="center", color="white")
ax.axhline(990, color="#64748b", linestyle=":", label="what Alice was owed")
ax.set(ylabel="ether reaching the deposed king", title="Push, checked push, and pull")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# In the unchecked version, where did Alice's 990 go? Read the throne's
# balance, and the call tree of Bob's claim with ``plot_call_tree``: which
# call failed, and with what error?
