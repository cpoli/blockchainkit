Breakthroughs in Blockchain Economics
=====================================

.. include:: /_generated/nav/economics.rst

.. epigraph::

   "It is not from the benevolence of the butcher, the brewer, or the baker
   that we expect our dinner, but from their regard to their own interest."
   -- Adam Smith, *The Wealth of Nations*, 1776

Cryptography makes cheating detectable; incentives make honesty the best
course. A blockchain pays the miners and validators who secure it, sells
its scarce block space to the users who want it, and hosts markets whose
prices and ordering can be exploited. :doc:`consensus_breakthroughs` covers
two incentive attacks on consensus itself, selfish mining and nothing at
stake; :doc:`contracts_breakthroughs` covers the flash loan as a contract.
This chronology follows the economics: the game theory and auction theory
the field borrowed, how block rewards and fees pay for security, how fee
markets price block space, how decentralized exchanges and stablecoins
work, and how the order of transactions became a market of its own.

The models in :mod:`blockchainkit.economics` are pure functions and small
seeded simulations; the stablecoin, the exchange and the lender are
contracts on :class:`~blockchainkit.contracts.systems.world.World`.
:doc:`/protocol` lists where they depart from deployed systems.

.. contents:: Timeline
   :local:
   :depth: 1

1960 -- Schelling's Focal Points: Coordinating without Communicating
--------------------------------------------------------------------

In *The Strategy of Conflict*, Schelling asked people to choose where and
when to meet a stranger in New York without any way to agree in advance.
Any place and time is an equilibrium: if both choose it, neither gains by
switching. Yet most chose the same one, noon at Grand Central Station. A
*focal point* is an equilibrium that stands out, by convention, uniqueness
or salience, and players reach it because each expects the others to.

To see why salience matters, suppose each of :math:`k` players picks the
salient option with probability :math:`s`, and otherwise picks uniformly
among all :math:`n` options, the salient one included. The salient option is
then chosen with probability :math:`s + (1-s)/n` and each other one with
:math:`(1-s)/n`, so all players coincide with probability

.. math::

   P = \left(s + \frac{1-s}{n}\right)^k + (n - 1)\left(\frac{1-s}{n}\right)^k.

Without salience, :math:`P = n^{1-k}`, and each extra player divides the
chance of agreement by :math:`n`. With salience, each extra player
multiplies it by only about :math:`s + (1-s)/n`, so a strongly salient
answer keeps even a large group coordinated. Blockchain oracles and voting
games rely on the truth being that salient answer.

*Implementation:* :func:`blockchainkit.economics.systems.coordination.coordination_probability`
and :func:`blockchainkit.economics.systems.coordination.play_coordination`.
Salience is a single probability shared by every player; Schelling's
experiments measured it rather than assuming it.

*References:* T. C. Schelling, *The Strategy of Conflict*, Harvard
University Press (1960), chapter 3.

.. minigallery:: ../../examples/economics/coordination/plot_01_schelling_focal_points.py

1961 -- Vickrey's Second-Price Auction and Truthful Bidding
-----------------------------------------------------------

In a sealed-bid first-price auction, the winner pays its bid. Bidding one's
true value then guarantees zero profit, so every bidder shades its bid
below its value by an amount that depends on what it guesses the others
will bid. Vickrey charged the winner the second-highest bid instead. A bid
then decides only whether one wins, never the price, and the bidder with
value :math:`v_i` has utility

.. math::

   u_i(b_i) = \begin{cases} v_i - \max_{j \ne i} b_j & \text{if } b_i > \max_{j \ne i} b_j,\\
   0 & \text{otherwise.} \end{cases}

Bidding the true value :math:`b_i = v_i` wins exactly when the price
:math:`\max_{j \ne i} b_j` is below :math:`v_i`, that is, exactly when
winning is profitable. Bidding more adds only wins at a price above
:math:`v_i`, which lose money; bidding less gives up only wins at a price
below :math:`v_i`, which would have made money. So truthful bidding is
optimal whatever the others do: it is a dominant strategy. Mechanisms that
make honest reporting optimal are the template for fee mechanisms and
builder auctions on blockchains.

*Implementation:* :func:`blockchainkit.economics.systems.auctions.second_price_auction`
and :func:`blockchainkit.economics.systems.auctions.first_price_auction`,
whose :class:`~blockchainkit.economics.core.base.AuctionResult` reports each
bidder's utility. Bids are sealed by fiat; on a public blockchain they must
be hidden by commit-reveal or encryption, or the auction is not sealed at
all.

*References:* W. Vickrey, *Counterspeculation, auctions, and competitive
sealed tenders*, The Journal of Finance 16(1), 8–37 (1961).
`DOI <https://doi.org/10.1111/j.1540-6261.1961.tb02789.x>`__.

.. minigallery:: ../../examples/economics/auctions/plot_01_vickrey_second_price.py

1981 -- Myerson's Optimal Auctions and Revenue Equivalence
----------------------------------------------------------

Myerson asked which auction maximizes the seller's expected revenue, when
each bidder's value is private and drawn from a distribution :math:`F` with
density :math:`f`. A seller cannot charge each bidder its value, because a
bidder would then pretend to value the item less; to keep bidders honest,
it must leave each one an *information rent*. Myerson accounted for this
rent by replacing each value with its *virtual value*,

.. math::

   \varphi(v) = v - \frac{1 - F(v)}{f(v)},

and showed that expected revenue equals the expected virtual value of the
winner. Maximizing revenue therefore means selling to the bidder with the
highest virtual value, and not selling at all when every virtual value is
negative. For identical bidders whose virtual value rises with their value,
that is a second-price auction with the reserve price
:math:`\varphi^{-1}(0)`, which is :math:`h/2` for values uniform on
:math:`[0, h]`. The same identity gives *revenue equivalence*: two auctions
that allocate the item to the same bidders, and in which a bidder with the
lowest possible value pays nothing, raise the same expected revenue. A
first-price auction with shaded bids thus earns what a second-price one
earns with truthful bids. Blockchain fee mechanisms, from EIP-1559's base
fee to builder auctions, are analyzed with these tools.

*Implementation:* :func:`blockchainkit.economics.systems.auctions.virtual_value`,
:func:`blockchainkit.economics.systems.auctions.optimal_reserve`,
:func:`blockchainkit.economics.systems.auctions.equilibrium_bid`,
:func:`blockchainkit.economics.systems.auctions.expected_revenue` and
:func:`blockchainkit.economics.systems.auctions.simulate_revenue`. Values
are independent and uniform on :math:`[0, h]`, the case with closed forms;
Myerson's result covers any regular distribution.

*References:* R. B. Myerson, *Optimal auction design*, Mathematics of
Operations Research 6(1), 58–73 (1981).
`DOI <https://doi.org/10.1287/moor.6.1.58>`__.

.. minigallery:: ../../examples/economics/auctions/plot_02_myerson_optimal_auction.py

2003 -- Hanson's Logarithmic Market Scoring Rule
------------------------------------------------

A prediction market pays 1 per share of the outcome that happens. A trader
who believes an outcome has probability :math:`p` buys its shares while
they cost less than :math:`p`, so prices read as the market's
probabilities. But thin markets have empty order books, and a trader with
information finds nobody to trade with. Hanson proposed an automated market
maker that always quotes a price. It tracks the shares :math:`q_i` sold of
each of :math:`n` outcomes and charges each trade the change in the cost
function :math:`C`, whose derivatives are the prices:

.. math::

   C(q) = b \ln \sum_i e^{q_i/b}, \qquad p_i = \frac{\partial C}{\partial q_i} = \frac{e^{q_i/b}}{\sum_j e^{q_j/b}}.

The prices are positive and sum to one, like probabilities. The market
maker starts at :math:`C(0) = b \ln n` and finally pays :math:`q_w` for the
winning outcome :math:`w`; since :math:`C(q) \ge q_w`, the traders have paid
it :math:`C(q) - C(0) \ge q_w - b \ln n`. Its loss is therefore at most
:math:`b \ln n`, a bounded subsidy that buys information, with the
liquidity parameter :math:`b` setting how far each trade moves the price. On-chain prediction
markets adopted it, and it is the ancestor of the formula-priced pools of
decentralized exchanges.

*Implementation:* :func:`blockchainkit.economics.systems.lmsr.lmsr_cost`,
:func:`blockchainkit.economics.systems.lmsr.lmsr_prices`,
:func:`blockchainkit.economics.systems.lmsr.lmsr_trade` and
:func:`blockchainkit.economics.systems.lmsr.lmsr_max_loss`, in floating
point; a contract would use fixed-point arithmetic, for which the
exponential is costly.

*References:* R. Hanson, *Combinatorial information market design*,
Information Systems Frontiers 5(1), 107–119 (2003).

.. minigallery:: ../../examples/economics/auctions/plot_03_hanson_lmsr.py

2008 -- Nakamoto's Incentive: Block Rewards and Fees
----------------------------------------------------

Section 6 of the Bitcoin paper pays the creator of each block in new coins
and in the fees of its transactions. The reward distributes the currency,
pays for the work that secures the chain, and, Nakamoto argued, keeps even
a powerful miner honest: it "ought to find it more profitable to play by
the rules."

The argument compares two uses of the same hashrate. An attacker pays a
merchant :math:`V`, and the merchant waits for :math:`z` confirmations;
meanwhile the attacker mines a private chain without the payment, which
takes about :math:`m = z + 1` blocks to overtake the public one. Mined
honestly, those blocks earn :math:`mR` for a reward :math:`R` per block. In
the attack they earn nothing unless the private chain wins, with the
whitepaper's catch-up probability :math:`P_z`; if it does, the attacker
keeps :math:`V` as well as its blocks' rewards, of which a fraction
:math:`d` has lost its worth because the attack shook confidence in the
coin. Attacking pays when

.. math::

   P_z \left(V + (1 - d)\, m R\right) > m R .

A small miner rarely catches up, so :math:`P_z` is tiny and only a payment
worth many blocks tempts it. A majority miner always catches up,
:math:`P_z = 1`, and the condition becomes :math:`V > d\, m R`: it is
deterred only by the loss :math:`d` on "the validity of his own wealth."

*Implementation:* :func:`blockchainkit.economics.systems.rewards.block_reward`
and :func:`blockchainkit.economics.systems.rewards.double_spend_incentive`,
using :func:`~blockchainkit.consensus.systems.catch_up.attacker_success_probability`.
The comparison counts the attacker's own blocks, not time, and ignores
propagation delay and the cost of the hardware.

*References:* S. Nakamoto, *Bitcoin: A peer-to-peer electronic cash system*
(2008), sections 6 and 11.

.. minigallery:: ../../examples/economics/rewards/plot_01_nakamoto_incentives.py

2009 -- Fixed Supply and the Halving Schedule
---------------------------------------------

The first Bitcoin release set the monetary policy in code. The block at
height :math:`h` creates

.. math::

   S(h) = \left\lfloor 50 \cdot 10^8 / 2^{\lfloor h/210\,000 \rfloor} \right\rfloor \text{ satoshis},

so the subsidy halves every 210,000 blocks, about every four years at ten
minutes a block. Each period issues half as many coins as the one before,
so the total approaches the geometric sum
:math:`210\,000 \times 50 \times (1 + \tfrac12 + \tfrac14 + \cdots) = 21`
million coins. The floor drops fractions of a satoshi at every halving, so
the total falls slightly short: the subsidy, :math:`5 \times 10^9` satoshis
at first, reaches zero at the 33rd halving, around 2140, with
20,999,999.9769 coins issued. A fixed, predictable supply was a deliberate
contrast with central-bank money; it also means that miners must eventually
be paid by fees alone.

*Implementation:* :func:`blockchainkit.economics.systems.rewards.block_subsidy`,
the logic of Bitcoin Core's ``GetBlockSubsidy``, and
:func:`blockchainkit.economics.systems.rewards.issued_supply`, which counts
the genesis block's 50 coins although Bitcoin can never spend them.

*References:* S. Nakamoto, Bitcoin v0.1 source code, ``main.cpp``,
``GetBlockValue`` (January 2009); Bitcoin Core, ``validation.cpp``,
``GetBlockSubsidy``.

.. minigallery:: ../../examples/economics/rewards/plot_02_halving_schedule.py

2014 -- SchellingCoin and Decentralized Oracles
-----------------------------------------------

Contracts cannot see the world, so prices and outcomes must be reported to
them. Buterin's SchellingCoin asks many reporters, each with a deposit
:math:`D`, publishes the median report, and pays those whose report
:math:`r_i` lies between the lower and upper quartiles of all reports:

.. math::

   \text{payout}_i = \begin{cases} R & q_{1/4} \le r_i \le q_{3/4},\\
   -D & \text{otherwise.} \end{cases}

A reporter is paid for agreeing with the others, so its best report is the
one it expects the others to make. Each reporter knows the truth, and
expects the others to know it, so the truth is the focal point: if
everyone else reports it, reporting it too is best. The scheme is only as
honest as its majority. A cartel that reports one false value is paid once
it exceeds a quarter of the reports, since its value then reaches the
quartile; above half it sets the median; and above three quarters it pushes
the honest reports outside the quartiles and takes their deposits.
Buterin's later P + epsilon attack showed that even a bribe that is never
paid can move the focal point: promise reporters of a false answer a reward
if that answer loses, and reporting it becomes the safer choice for each, so
it wins and the promise costs nothing. UMA's and Kleros's dispute resolution build on
the same idea.

*Implementation:* :func:`blockchainkit.economics.systems.oracles.schelling_round`,
which settles one round; there are no rounds over time, no commit-reveal of
reports, and no token whose value depends on the oracle's honesty.

*References:* V. Buterin, *SchellingCoin: a minimal-trust universal data
feed*, Ethereum Blog (March 2014); V. Buterin, *The P + epsilon attack*,
Ethereum Blog (January 2015).

.. minigallery:: ../../examples/economics/coordination/plot_02_schellingcoin_oracle.py

2016 -- Carlsten et al.: the Instability of Bitcoin without the Block Reward
----------------------------------------------------------------------------

Once the subsidy is gone, a block earns only the fees it collects. Fees
arrive at a steady rate while blocks arrive at random, so a block's reward
is proportional to the time since the last one, and a block found right
after another holds almost nothing. Carlsten, Kalodner, Weinberg and
Narayanan showed two consequences. First, :math:`t` seconds after a block,
the next one is worth :math:`S + ft` for a subsidy :math:`S` and a fee rate
:math:`f`. While that is less than :math:`c`, what a miner spends on
electricity per block it expects to find, mining loses money, so miners
pause for a *mining gap* of

.. math::

   t^* = \max\left(0, \frac{c - S}{f}\right)

seconds, which is zero while the subsidy covers the cost. Second, a miner
can fork the tip instead of extending it, re-mining its height to claim the
tip's fees as well as the pending ones. If the tip claimed more fees than
remain in the mempool, the fork offers more; by *undercutting*, claiming
only part of the fees and leaving the rest for the next block, the miner
makes its fork the more lucrative branch for other miners to build on.
They also showed that selfish mining becomes profitable for arbitrarily
small miners.

*Implementation:* :func:`blockchainkit.economics.systems.fee_only.simulate_block_rewards`,
:func:`blockchainkit.economics.systems.fee_only.mining_gap` and
:func:`blockchainkit.economics.systems.fee_only.undercutting_payoffs`. The
undercutting model is a one-shot comparison in which other miners follow
the more lucrative branch; the paper simulates repeated play with learning
miners.

*References:* M. Carlsten, H. Kalodner, S. M. Weinberg and A. Narayanan,
*On the instability of Bitcoin without the block reward*, Proc. ACM CCS
2016, 154–167 (2016).

.. minigallery:: ../../examples/economics/rewards/plot_03_carlsten_fee_only_instability.py

2016 -- Kiayias et al.: Mining Games and When Honest Mining Is an Equilibrium
-----------------------------------------------------------------------------

Kiayias, Koutsoupias, Kyropoulou and Tselekounis modeled mining as a
stochastic game in which miners choose which block to extend and when to
publish. When every miner's hashrate is small, honest mining is a best
response to honest mining; a large miner gains by deviating, and other
equilibria arise. The same year, Sapirshtein, Sompolinsky and Zohar
computed a miner's best deviation exactly. A miner with a share
:math:`\alpha` of the hashrate chooses, in each state :math:`(a, h)` given
by the lengths of its private branch and of the public one, whether to
publish, wait or give up; :math:`\gamma` is the fraction of the other
miners that build on its block when two branches tie. Over all strategies
:math:`\pi`, its best long-run share of the blocks in the chain is

.. math::

   \rho^*(\alpha, \gamma) = \max_\pi \lim \frac{R_\text{miner}}{R_\text{miner} + R_\text{others}}.

A ratio is hard to optimize directly, but a share above :math:`\rho` is
achievable exactly when some strategy makes the per-block reward
:math:`r_\text{miner} - \rho (r_\text{miner} + r_\text{others})` positive on
average, which is an ordinary Markov decision problem; bisection on
:math:`\rho` then finds :math:`\rho^*`. Mining honestly earns
:math:`\alpha`, so honest mining is an equilibrium exactly when
:math:`\rho^* = \alpha`. With :math:`\gamma = 0`, ties going to honest
blocks, that holds up to about :math:`\alpha = 0.33`.

*Implementation:* :func:`blockchainkit.economics.systems.mining_games.optimal_mining_revenue`
and :func:`blockchainkit.economics.systems.mining_games.honest_mining_is_equilibrium`,
by relative value iteration. Both branches are capped at ``max_lead``
blocks, which can only underestimate the best deviation; the full games
of Kiayias et al., with several strategic miners, are not modeled.

*References:* A. Kiayias, E. Koutsoupias, M. Kyropoulou and Y.
Tselekounis, *Blockchain mining games*, Proc. ACM EC 2016, 365–382 (2016),
`arXiv:1607.02420 <https://arxiv.org/abs/1607.02420>`__; A. Sapirshtein,
Y. Sompolinsky and A. Zohar, *Optimal selfish mining strategies in
Bitcoin*, Financial Cryptography 2016, LNCS 9603, 515–532 (2017).

.. minigallery:: ../../examples/economics/rewards/plot_04_kiayias_mining_games.py

2017 -- MakerDAO's Dai: a Collateralized Stablecoin and Liquidation
-------------------------------------------------------------------

A stablecoin aims at a fixed price. Dai, launched in December 2017, is
backed by ether locked in contracts rather than dollars in a bank. A user
locks ether in a *vault* (then a collateralized debt position) and draws
newly minted Dai, as long as

.. math::

   \text{collateral} \times \text{price} \ge 1.5 \times \text{debt}

at the price reported by an oracle. If a fall in the price breaks this
inequality, anyone may liquidate the vault: repay its debt, which burns
that Dai, and take collateral worth the debt plus a 13% penalty. The margin
is what keeps every Dai backed. At the moment of liquidation the vault
holds collateral worth 1.5 times its debt, more than the 1.13 times the
liquidator takes, and the price can fall by a third before the collateral
is worth less than the debt. Dai becomes undercollateralized only if the
price falls faster than liquidations can follow, as on 12 March 2020, when
congestion let some liquidators win collateral for almost nothing.

*Implementation:* :class:`blockchainkit.economics.systems.lending.VaultEngine`,
:class:`~blockchainkit.economics.systems.lending.Stablecoin` and
:class:`~blockchainkit.economics.systems.lending.PriceFeed`, with
Single-Collateral Dai's 150% ratio and 13% penalty. The liquidator buys the
collateral at the oracle price instead of in an auction, and there is no
stability fee, savings rate or governance.

*References:* The Maker Team, *The Dai stablecoin system* (December 2017).

.. minigallery:: ../../examples/economics/defi/plot_01_dai_liquidation.py

2018 -- Uniswap's Constant-Product Market Maker and Impermanent Loss
--------------------------------------------------------------------

An order book needs market makers who post and cancel orders constantly,
which is too expensive on chain, where every update is a paid transaction.
Uniswap, launched in November 2018, replaced it with a pool of two tokens
whose reserves :math:`x` and :math:`y` keep their product constant. A trader
who pays in :math:`\Delta x` has 0.3% kept as a fee and takes out the
:math:`\Delta y` that restores the product:

.. math::

   (x + 0.997\,\Delta x)(y - \Delta y) = x y.

The pool's price is the ratio :math:`p = y/x`, and every trade moves it: the
more of a token is bought, the scarcer and dearer it becomes, so no trade
can empty the pool. Anyone can deposit both tokens and earn the fees, but
bears *impermanent loss*. When the market price moves by a factor :math:`r`,
arbitrageurs trade the pool to the new price, buying from it the token that
rose. With the product fixed, :math:`x = \sqrt{xy/p}` and
:math:`y = \sqrt{xy\,p}`, so the deposit's value :math:`px + y = 2\sqrt{xy\,p}`
grows by a factor :math:`\sqrt{r}`, while holding the two tokens grows by
:math:`(1 + r)/2`. The ratio :math:`2\sqrt{r}/(1+r)` is at most one, with
equality only at :math:`r = 1`. The loss
is impermanent because it vanishes if the price returns. Uniswap V2 (2020)
added a price oracle that reads the price before the first trade of each
block. A transaction moves the price only after that reading, so no single
transaction can move the oracle.

*Implementation:* :func:`blockchainkit.economics.systems.amm.amount_out`
(V2's ``getAmountOut``), :func:`blockchainkit.economics.systems.amm.impermanent_loss`
and the contract :class:`blockchainkit.economics.systems.amm.ConstantProductPool`,
whose :meth:`~blockchainkit.economics.systems.amm.ConstantProductPool.previous_price`
stores the price before a block's first trade rather than V2's
time-weighted accumulator. Shares are not tokens, and no liquidity is
locked at the first deposit.

*References:* H. Adams, *Uniswap whitepaper* (November 2018); H. Adams,
N. Zinsmeister and D. Robinson, *Uniswap v2 core* (March 2020).

.. minigallery:: ../../examples/economics/defi/plot_02_uniswap_impermanent_loss.py

2019 -- Flash Boys 2.0: Front-Running and Priority Gas Auctions
---------------------------------------------------------------

Daian et al. watched arbitrage bots on decentralized exchanges compete for
the same opportunity by repeatedly replacing their pending transaction with
one paying a higher fee, in a *priority gas auction*: miners order
transactions by fee, so the highest bid is executed first and takes the
opportunity. Each replacement must raise the fee by at least a fraction
:math:`\beta`. Bots that all value the opportunity at :math:`V` keep
outbidding each other while a raise still leaves a profit, and stop at a
price whose next raise would exceed :math:`V`:
:math:`(1 + \beta)\,\text{price} > V`. The winner therefore keeps

.. math::

   V - \text{price} < V - \frac{V}{1 + \beta} = \frac{\beta}{1 + \beta}\, V,

and the rest goes in fees to whoever orders the block. They called this
value *miner extractable value* (MEV). When a past block holds more MEV
than the reward for a new one, a miner gains by forking the chain to
re-mine that block and capture it, a threat to consensus itself.

*Implementation:* :func:`blockchainkit.economics.systems.ordering.priority_gas_auction`,
in which bots respond one at a time with the minimum raise; real bots
raced on latency, mempool visibility and gas estimates.

*References:* P. Daian, S. Goldfeder, T. Kell, Y. Li, X. Zhao, I. Bentov,
L. Breidenbach and A. Juels, *Flash Boys 2.0: frontrunning, transaction
reordering, and consensus instability in decentralized exchanges*, IEEE
Symposium on Security and Privacy 2020 (2019),
`arXiv:1904.05234 <https://arxiv.org/abs/1904.05234>`__.

.. minigallery:: ../../examples/economics/mev/plot_01_flash_boys_gas_auctions.py

2020 -- Flash Loans and Oracle Manipulation: the bZx Attacks
------------------------------------------------------------

In February 2020, two attacks on the bZx lending protocol took flash
loans, used them to move a decentralized exchange's spot price within one
transaction, and exploited protocols that trusted that price. A flash loan
must be repaid in the same transaction, so it needs no collateral, and
anyone can briefly command a large sum.

In its simplest form, the attacker flash-borrows :math:`U` dollars and
spends them on a token from a constant-product pool holding :math:`x`
tokens and :math:`y` dollars. The purchase leaves :math:`y + U` dollars and
:math:`xy/(y+U)` tokens in the pool, so the attacker receives
:math:`xU/(y+U)` tokens and the spot price rises to
:math:`(y+U)^2/(xy)`. At that price the tokens bought appear worth
:math:`U(y + U)/y`, more than the :math:`U` they cost. Deposited with a
lender that reads the spot price and demands 150% collateral, they borrow

.. math::

   \frac{U(y + U)}{1.5\,y} > U \quad\text{whenever}\quad U > \frac{y}{2}.

The attacker repays the flash loan from the new loan and keeps the
difference, and the lender is left holding tokens worth far less than it
lent once the price recovers. A price recorded before the transaction, like
Uniswap V2's, cannot be moved this way.

*Implementation:* :class:`blockchainkit.economics.systems.lending.OracleLender`,
reading :class:`~blockchainkit.economics.systems.amm.ConstantProductPool`'s
spot price or its price before the block, attacked by
:class:`~blockchainkit.economics.systems.lending.OracleAttacker` with
:class:`~blockchainkit.contracts.systems.governance.FlashLender`. The model
reduces the second attack to its mechanism; the first combined a margin
trade on bZx with the manipulated price, across several protocols.

*References:* K. Qin, L. Zhou, B. Livshits and A. Gervais, *Attacking the
DeFi ecosystem with flash loans for fun and profit*, Financial Cryptography
2021, LNCS 12674, 3–32 (2021).
`DOI <https://doi.org/10.1007/978-3-662-64322-8_1>`__.

.. minigallery:: ../../examples/economics/defi/plot_03_bzx_oracle_manipulation.py

2020 -- EIP-1559's Base Fee and Burn, with Roughgarden's Analysis
-----------------------------------------------------------------

Bitcoin sells block space by a first-price auction, and Ethereum did until
the London upgrade of August 2021. As Vickrey's analysis predicts, users
must guess how much to shade their bids, no bid is obviously right, and
prices swing with demand. EIP-1559 instead sets a protocol price per unit
of gas, the *base fee* :math:`b_t`. After each block it moves by up to an
eighth, up when the block used more gas :math:`g_t` than the target
:math:`g^*`, half the block's capacity, and down when it used less:

.. math::

   b_{t+1} = b_t \left(1 + \frac{1}{8}\, \frac{g_t - g^*}{g^*}\right).

Every transaction pays the base fee, which is burned, plus a tip to the
producer. Because the price is posted rather than bid, Roughgarden's
analysis showed that, outside sudden rises in demand, bidding the base fee
plus a small tip is optimal for users. Because the base fee is burned, a
producer gains nothing by raising it with fake transactions, and a myopic
producer has no reason to deviate from including the highest tips; nor can
users and producers profit from an off-chain deal that skips the base fee,
since it goes to neither of them.

*Implementation:* :func:`blockchainkit.economics.systems.fee_market.next_base_fee`,
the specification's integer update, and
:func:`blockchainkit.economics.systems.fee_market.simulate_fee_market`,
which runs a mempool through either mechanism. Every transaction is a
transfer of 21,000 gas, values are uniform, and first-price bidders shade
by a fixed fraction rather than strategically.

*References:* V. Buterin, E. Conner, R. Dudley, M. Slipper, I. Norden and
A. Bakhta, *EIP-1559: fee market change for ETH 1.0 chain* (2019);
T. Roughgarden, *Transaction fee mechanism design for the Ethereum
blockchain: an economic analysis of EIP-1559* (December 2020),
`arXiv:2012.00854 <https://arxiv.org/abs/2012.00854>`__.

.. minigallery:: ../../examples/economics/fees/plot_01_eip1559_base_fee.py

2021 -- Sandwich Attacks on Decentralized Exchanges
---------------------------------------------------

A swap waits in the public mempool before it is mined, where anyone can see
it. A *sandwich* attacker buys the same token just before it, which raises
the price the victim pays, and sells just after, at the price the victim's
purchase pushed up further. The victim's only protection is its slippage
tolerance :math:`s`: its swap reverts if it would receive less than a
fraction :math:`1 - s` of the output quoted before the attack. A larger
front-run :math:`a` moves the price more and earns the attacker more, but
the victim's output :math:`\text{out}_\text{victim}(a)` falls as :math:`a`
grows, and the attacker gets nothing if the victim's swap reverts. So the
attacker maximizes its profit over the front-runs that keep

.. math::

   \text{out}_\text{victim}(a) \ge (1 - s)\,\text{out}_\text{victim}(0),

which for a large victim trade means the largest front-run allowed. The
attacker also pays the pool's fee twice, so a trade too small to move the
price by more than those two fees is not worth attacking.

Zhou, Qin, Torres, Le and Gervais derived this optimal attack, measured
sandwiches on Uniswap, and showed that a looser tolerance hands more of
each trade to the attacker. Private transaction relays and batch auctions
are among the responses.

*Implementation:* :func:`blockchainkit.economics.systems.ordering.sandwich_profit`
and :func:`blockchainkit.economics.systems.ordering.sandwich_attack`, which
bounds the front-run by bisection and maximizes the profit by ternary
search; the attacker is assumed to control the order of the three
transactions and to hold the capital.

*References:* L. Zhou, K. Qin, C. F. Torres, D. V. Le and A. Gervais,
*High-frequency trading on decentralized on-chain exchanges*, IEEE
Symposium on Security and Privacy 2021 (2021),
`arXiv:2009.14021 <https://arxiv.org/abs/2009.14021>`__.

.. minigallery:: ../../examples/economics/mev/plot_02_sandwich_attacks.py

2022 -- Proposer-Builder Separation and MEV-Boost
-------------------------------------------------

Extracting MEV takes searchers, order flow and infrastructure. A validator
that has them earns more per unit of stake than one that does not, so
stakers move to it, and MEV pushes proof of stake toward a few large
operators. Proposer-builder separation lets specialized *builders*
assemble blocks and bid for each slot, while the proposer, any validator,
only signs the best bid. A block holds fees :math:`f` and an MEV
opportunity :math:`M`, of which builder :math:`b` can capture a fraction
:math:`\sigma_b`, so it values the block at :math:`v_b = f + \sigma_b M`. In
a second-price auction builders bid these values, and the proposer
receives the runner-up's, or what it could build itself if that is more:

.. math::

   \text{revenue} \ge v_{(2)} = f + \sigma_{(2)} M.

This bound does not depend on the proposer's own skill. With two or more
capable builders, :math:`\sigma_{(2)}` is close to one, so a solo staker
earns about as much per slot as a professional operator. Flashbots'
MEV-Boost ran the auction outside the protocol from Ethereum's move to
proof of stake in September 2022, through relays that both builders and
proposers must trust; enshrining it in the protocol remains open.

*Implementation:* :func:`blockchainkit.economics.systems.pbs.simulate_pbs`,
which picks proposers with :class:`~blockchainkit.consensus.systems.pos.StakeSampler`
and sells each slot by
:func:`~blockchainkit.economics.systems.auctions.second_price_auction`.
MEV-Boost's auction is first-price with open bids through relays; with
many builders the price approaches the runner-up's value either way.

*References:* V. Buterin, *Proposer/block builder separation-friendly fee
market designs*, ethresear.ch (June 2021); Flashbots, *MEV-Boost* (2022).

.. minigallery:: ../../examples/economics/mev/plot_03_mev_boost_pbs.py
