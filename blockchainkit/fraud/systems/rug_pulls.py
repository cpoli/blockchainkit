"""Rug pulls and hidden-mint tokens: the Squid Game token (2021).

Anyone can create a token and a market for it on a decentralized exchange.
A *rug pull* is a token whose creator, once buyers have paid in, takes the
money out: by withdrawing the liquidity it supplied, by minting itself
tokens through a hidden function and selling them, or by blocking everyone
else from selling, so that the price can only rise until it leaves. In
November 2021 the Squid Game token rose from a cent to 2,861 dollars while
its holders could not sell, then fell to nothing in minutes as its creators
sold and vanished.

The defence is to try before buying: on a fork of the chain, buy a little
and sell it back (:func:`sell_test`), as honeypot scanners do.
"""

from typing import ClassVar

from blockchainkit.contracts.systems.tokens import ERC20
from blockchainkit.contracts.systems.world import World


class HiddenMintToken(ERC20):
    """An ERC-20 token whose ``sync_rewards`` mints to the owner, whatever its name suggests.

    The source shows a ``sync_rewards`` function guarded by an
    ``only_reward_manager`` modifier, which reads like reward bookkeeping;
    the reward manager is the deployer, and the function creates tokens.
    """

    layout: ClassVar[tuple[str, ...]] = (*ERC20.layout, "reward_manager")

    def constructor(self, supply: int) -> None:
        super().constructor(supply)
        self.write("reward_manager", self.sender)

    def sync_rewards(self, amount: int) -> None:
        """Mint ``amount`` to the reward manager, under the name of syncing staking rewards."""
        manager = self.read("reward_manager")
        self.require(self.sender == manager, "only the reward manager")
        self.require(type(amount) is int and amount > 0, "amount must be positive")
        self.write("total_supply", self.read("total_supply") + amount)
        self.write("balances", manager, self.read("balances", manager) + amount)


class SellBlockToken(ERC20):
    """An ERC-20 token that only its owner can sell into its market.

    Transfers *to* the registered pool, which is what a sale is, revert
    unless the seller is exempt; buying from the pool works. The Squid Game
    token presented the rule as an "anti-dump" mechanism.
    """

    layout: ClassVar[tuple[str, ...]] = (*ERC20.layout, "owner", "pool", "exempt")

    def constructor(self, supply: int) -> None:
        super().constructor(supply)
        self.write("owner", self.sender)
        self.write("exempt", self.sender, 1)

    def set_pool(self, pool: str) -> None:
        """Register the market's pool; owner only."""
        self.require(self.sender == self.read("owner"), "only the owner")
        self.write("pool", pool)

    def _move(self, source: str, destination: str, amount: int) -> None:
        if destination == self.read("pool"):
            self.require(self.read("exempt", source), "anti-dump: selling is not enabled")
        super()._move(source, destination, amount)


def sell_test(world: World, pool: str, token: str, quote: str, buyer: str, spend: int) -> bool:
    """Buy ``spend`` of ``quote`` worth of ``token`` and sell it back, on a fork of ``world``.

    ``pool`` is a :class:`~blockchainkit.economics.systems.amm.ConstantProductPool`
    of the two tokens, and ``buyer`` must hold ``spend`` of ``quote``.
    Returns True if both trades succeed; ``world`` itself is unchanged.
    """
    trial = world.fork()
    trial.transact(buyer, quote, "approve", pool, spend)
    bought = trial.transact(buyer, pool, "swap", quote, spend)
    if not bought.success:
        return False
    trial.transact(buyer, token, "approve", pool, bought.result)
    return trial.transact(buyer, pool, "swap", token, bought.result).success
