"""Constant-product market makers: Uniswap (2018) and impermanent loss.

An order book needs market makers who constantly post and cancel orders,
which costs too much gas on a blockchain. Uniswap replaced the order book
with a pool of two tokens whose reserves ``x`` and ``y`` must keep their
product constant: a trader who adds ``dx`` (after a 0.3% fee) takes out
the ``dy`` that preserves

.. math::

   (x + dx)(y - dy) = x y,

so the price ``y / x`` moves against every trade, more for a large trade
than for a small one. Anyone can deposit both tokens in proportion and
receive pool *shares*, earning the fees. A depositor is however always
worse off than if it had held the tokens: if the price moves by a factor
``r``, the deposit is worth :math:`2\\sqrt{r}/(1 + r)` of holding, a loss
called *impermanent* because it vanishes if the price returns.

:class:`ConstantProductPool` is a contract on the
:class:`~blockchainkit.contracts.systems.world.World` model; its price
oracle, :meth:`ConstantProductPool.previous_price`, records the price at the
start of each block, the idea behind Uniswap V2's time-weighted average.
"""

from fractions import Fraction
from math import isqrt, sqrt

from blockchainkit._validation import integer, positive
from blockchainkit.contracts.systems.world import Contract

FEE_BPS = 30
"""Uniswap V2's swap fee, in basis points (0.3%)."""


def amount_out(reserve_in: int, reserve_out: int, amount_in: int, *, fee_bps: int = FEE_BPS) -> int:
    """Tokens received for ``amount_in``, as Uniswap V2's ``getAmountOut`` computes them.

    The fee is taken from the input, and the result is rounded down so the
    product of the reserves never decreases.

    Examples
    --------
    >>> from blockchainkit.economics import amount_out
    >>> amount_out(1_000, 1_000, 100, fee_bps=0)  # 1,000,000 / 1,100 = 909.09
    90
    >>> amount_out(1_000, 1_000, 100)
    90
    """
    integer(reserve_in, "reserve_in", 1)
    integer(reserve_out, "reserve_out", 1)
    integer(amount_in, "amount_in")
    integer(fee_bps, "fee_bps")
    if fee_bps >= 10_000:
        raise ValueError("fee_bps must be below 10,000")
    with_fee = amount_in * (10_000 - fee_bps)
    return with_fee * reserve_out // (reserve_in * 10_000 + with_fee)


def impermanent_loss(price_ratio: float) -> float:
    """A depositor's loss against holding, when the price moves by ``price_ratio``.

    It is :math:`2\\sqrt{r}/(1+r) - 1`: zero for ``r = 1``, about -5.7% when
    the price doubles or halves, and -20% when it moves fourfold.

    Examples
    --------
    >>> from blockchainkit.economics import impermanent_loss
    >>> impermanent_loss(1.0), round(impermanent_loss(4.0), 4), round(impermanent_loss(0.25), 4)
    (0.0, -0.2, -0.2)
    """
    positive(price_ratio, "price_ratio")
    return float(2 * sqrt(price_ratio) / (1 + price_ratio) - 1)


class ConstantProductPool(Contract):
    """A Uniswap V2-style pool of two ERC-20 tokens.

    Callers must first ``approve`` the pool to move their tokens. The
    invariant checks that the shares sum to the total supply of shares.

    Parameters
    ----------
    token0, token1 : str
        The two :class:`~blockchainkit.contracts.systems.tokens.ERC20` tokens.
    fee_bps : int
        Swap fee in basis points.
    """

    layout = (
        "token0",
        "token1",
        "fee_bps",
        "reserve0",
        "reserve1",
        "total_shares",
        "shares",
        "last_block",
        "last_price",
    )

    def constructor(self, token0: str, token1: str, fee_bps: int = FEE_BPS) -> None:
        self.require(token0 != token1, "the tokens must differ")
        self.write("token0", token0)
        self.write("token1", token1)
        self.write("fee_bps", fee_bps)

    def reserves(self) -> tuple[int, int]:
        """The pool's holdings of token0 and token1."""
        return int(self.read("reserve0")), int(self.read("reserve1"))

    def price(self) -> Fraction:
        """The spot price of token0 in token1, ``reserve1 / reserve0``."""
        reserve0, reserve1 = self.reserves()
        self.require(reserve0 > 0, "the pool is empty")
        return Fraction(reserve1, reserve0)

    def previous_price(self) -> Fraction:
        """The spot price as it stood before the first trade of the current block.

        No transaction can move it: a flash loan within the block comes too late.
        """
        self._observe()
        price = self.read("last_price")
        self.require(price != 0, "no price recorded yet")
        return Fraction(price)

    def shares_of(self, owner: str) -> int:
        """Pool shares held by ``owner``."""
        return int(self.read("shares", owner))

    def _observe(self) -> None:
        if self.block_number > self.read("last_block"):
            reserve0, reserve1 = self.reserves()
            if reserve0:
                self.write("last_price", Fraction(reserve1, reserve0))
            self.write("last_block", self.block_number)

    def add_liquidity(self, amount0: int, amount1: int) -> int:
        """Deposit both tokens and receive shares; the first deposit sets the price."""
        self._observe()
        self.require(type(amount0) is int and type(amount1) is int, "amounts must be integers")
        self.require(amount0 > 0 and amount1 > 0, "deposit both tokens")
        self.call(self.read("token0"), "transfer_from", self.sender, self.address, amount0)
        self.call(self.read("token1"), "transfer_from", self.sender, self.address, amount1)
        reserve0, reserve1 = self.reserves()
        total = self.read("total_shares")
        if total == 0:
            minted = isqrt(amount0 * amount1)
        else:
            minted = min(amount0 * total // reserve0, amount1 * total // reserve1)
        self.require(minted > 0, "deposit too small")
        self.write("reserve0", reserve0 + amount0)
        self.write("reserve1", reserve1 + amount1)
        self.write("total_shares", total + minted)
        self.write("shares", self.sender, self.read("shares", self.sender) + minted)
        return int(minted)

    def remove_liquidity(self, shares: int) -> tuple[int, int]:
        """Burn ``shares`` and withdraw the same fraction of both reserves."""
        self._observe()
        held = self.read("shares", self.sender)
        self.require(type(shares) is int and 0 < shares <= held, "not enough shares")
        reserve0, reserve1 = self.reserves()
        total = self.read("total_shares")
        out0, out1 = reserve0 * shares // total, reserve1 * shares // total
        self.write("shares", self.sender, held - shares)
        self.write("total_shares", total - shares)
        self.write("reserve0", reserve0 - out0)
        self.write("reserve1", reserve1 - out1)
        self.call(self.read("token0"), "transfer", self.sender, out0)
        self.call(self.read("token1"), "transfer", self.sender, out1)
        return int(out0), int(out1)

    def swap(self, token_in: str, amount_in: int, min_out: int = 0) -> int:
        """Sell ``amount_in`` of ``token_in`` for the other token; revert below ``min_out``.

        ``min_out`` is the trader's slippage limit, the one defense against
        being sandwiched.
        """
        self._observe()
        token0, token1 = self.read("token0"), self.read("token1")
        self.require(token_in in (token0, token1), "not a token of this pool")
        self.require(type(amount_in) is int and amount_in > 0, "amount must be positive")
        reserve0, reserve1 = self.reserves()
        self.require(reserve0 > 0, "the pool is empty")
        selling0 = token_in == token0
        reserve_in, reserve_out = (reserve0, reserve1) if selling0 else (reserve1, reserve0)
        out = amount_out(reserve_in, reserve_out, amount_in, fee_bps=self.read("fee_bps"))
        self.require(out >= min_out, "slippage limit exceeded")
        self.call(token_in, "transfer_from", self.sender, self.address, amount_in)
        if selling0:
            self.write("reserve0", reserve0 + amount_in)
            self.write("reserve1", reserve1 - out)
        else:
            self.write("reserve1", reserve1 + amount_in)
            self.write("reserve0", reserve0 - out)
        self.call(token1 if selling0 else token0, "transfer", self.sender, out)
        self.emit("Swap", sender=self.sender, token_in=token_in, amount_in=amount_in, out=out)
        return int(out)

    def invariant(self) -> bool:
        return bool(self.read("total_shares") == sum(self.entries("shares").values()))
