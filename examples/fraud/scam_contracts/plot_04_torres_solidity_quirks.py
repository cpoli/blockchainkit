r"""
Torres et al.: the Solidity quirks honeypots exploit (2019)
===========================================================

Four of the honeypot techniques Torres, Steichen and State classified are
quirks of the Solidity language or compiler of the time, which the reader
of the source does not suspect. They are reproduced here by their effect;
nothing is compiled. *Inheritance disorder*: the child redeclares
``owner``, so the bidder who becomes ``owner`` is not the one the parent's
modifier checks.

.. code-block:: solidity

   contract Ownable {
       address owner = msg.sender;
       modifier onlyOwner { require(msg.sender == owner); _; }
   }
   contract KingOfTheHill is Ownable {
       address public owner;
       function() payable { if (msg.value > jackpot) owner = msg.sender; jackpot += msg.value; }
       function takeAll() onlyOwner { msg.sender.transfer(this.balance); jackpot = 0; }
   }

*Uninitialised storage struct*: ``GuessHistory guessHistory;`` without
``memory`` points at slot 0, so recording the player's address overwrites
the "private" number the reader read from storage. *Type deduction
overflow*: ``for (var i = 0; i < 2 * msg.value; i++)`` makes ``i`` a
``uint8``, and the doubled counter wraps at :math:`2 \cdot 128 \equiv 0
\pmod{256}`, ending the loop with a payout of 254 wei. *Skipped empty
string literal*: before Solidity 0.4.12, the call
``loggedTransfer(amount, "", msg.sender, owner)`` was encoded without the
``""``, so the owner received the investor's refund.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

world = bk.contracts.World()
world.fund("creator", 20_000)
losses = {}


def victim(name, amount):
    world.fund(name, amount)
    return name


# %%
# Inheritance disorder
# --------------------

hill = world.deploy("creator", bk.fraud.KingOfTheHill, name="KingOfTheHill")
world.transact("creator", hill, value=1_000)
king = victim("bidder", 1_500)
world.transact(king, hill, value=1_500)
print(
    "public owner:",
    world.view(hill, "owner"),
    "| takeAll:",
    world.transact(king, hill, "take_all").error,
)
losses["inheritance disorder"] = 1_500 - world.balance(king)

# %%
# Uninitialised storage struct
# ----------------------------

game = world.deploy("creator", bk.fraud.GuessNumber, 7, 100, name="GuessNumber")
world.transact("creator", game, value=1_000)
secret = world.read(game, "number")  # "private" is not secret on a public chain.
guesser = victim("guesser", 100)
world.transact(guesser, game, "guess", secret, value=100)
print("the secret was", secret, "and slot 0 now holds", world.read(game, "number"))
losses["uninitialised struct"] = 100 - world.balance(guesser)

# %%
# Type deduction overflow
# -----------------------

doubler = world.deploy("creator", bk.fraud.ForTest, 1_000, name="For_Test")
world.transact("creator", doubler, value=5_000)
sender = victim("doubler", 2_000)
world.transact(sender, doubler, "test", value=2_000)
print("sent 2,000, got back", world.balance(sender))
losses["type deduction overflow"] = 2_000 - world.balance(sender)
assert world.balance(sender) == 254

# %%
# Skipped empty string literal
# ----------------------------

fund = world.deploy("creator", bk.fraud.DividendDistributor, name="DividendDistributor")
investor = victim("investor", 1_000)
world.transact(investor, fund, "invest", value=1_000)
refund = world.transact(investor, fund, "divest", 1_000)
print("refund paid to:", refund.events[0].fields["target"])
losses["skipped empty string"] = 1_000 - world.balance(investor)

assert all(loss > 0 for loss in losses.values())
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.barh(list(losses), list(losses.values()), color="#9333ea")
ax.set(xlabel="ether lost by the victim", title="Four Solidity quirks, by their effect")
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# In the type-deduction honeypot, what is the largest payout the loop can
# ever compute, whatever the deposit? Replay the loop by hand for a deposit
# of 50 wei and explain why the honeypot sets a minimum deposit.
