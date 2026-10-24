Breakthroughs in Blockchain Economics
=====================================

.. include:: /_generated/nav/economics.rst

.. epigraph::

   "It is not from the benevolence of the butcher, the brewer, or the baker
   that we expect our dinner, but from their regard to their own interest."
   -- Adam Smith, *The Wealth of Nations*, 1776

Cryptography makes cheating detectable. Incentives make honesty the best
course: the rewards and penalties are set so that following the rules pays
more than breaking them. This page is about those incentives.

Some vocabulary first.

- A *blockchain* is a shared record of payments. Think of a Python list of
  *blocks*, where each block holds a batch of *transactions*: signed
  instructions such as "pay Bob 5 coins". Thousands of computers keep copies
  of the list in step, without trusting each other.
- *Consensus* is the set of rules by which those computers agree on which
  block comes next.
- In *proof of work* (Bitcoin), *miners* add blocks. They race to solve a
  brute-force puzzle: hash candidate blocks until a hash falls below a target.
  A miner's *hashrate* is how many guesses it makes per second. Its chance of
  finding the next block equals its share of the total hashrate.
- In *proof of stake* (Ethereum since 2022), *validators* add blocks. Each
  locks up coins as a *stake*, and the protocol picks one at random, weighted
  by stake, to propose each block.
- Whoever adds a block is paid for it. Users also pay *fees* to get their
  transactions into a block, because each block has limited space.
- A *smart contract*, or just *contract*, is a program stored on the
  blockchain. It can hold coins and runs when a transaction calls it. It is
  like a Python object whose methods anyone can call but whose code nobody can
  change. A *token* is a coin defined by such a contract. *Ether* (ETH) is
  Ethereum's own coin.

A blockchain pays the miners and validators who secure it. It sells its
scarce block space to the users who want it. It also hosts markets whose
prices and ordering can be exploited. :doc:`consensus_breakthroughs` covers
two incentive attacks on consensus itself, selfish mining and nothing at
stake; :doc:`contracts_breakthroughs` covers the flash loan as a contract.
This chronology follows the economics:

- the game theory and auction theory the field borrowed;
- how block rewards and fees pay for security;
- how fee markets price block space;
- how decentralized exchanges and stablecoins work;
- how the order of transactions became a market of its own.

The models in :mod:`blockchainkit.economics` are pure functions and small
seeded simulations. The stablecoin, the exchange and the lender are
contracts on :class:`~blockchainkit.contracts.systems.world.World`.
:doc:`/protocol` lists where they depart from deployed systems.

.. contents:: Timeline
   :local:
   :depth: 1

1960 -- Schelling's Focal Points: Coordinating without Communicating
--------------------------------------------------------------------

Two people must meet somewhere in New York. They cannot talk to agree on a
place or a time. How can they end up together?

*Game theory* studies situations like this one, called *games*. Each
*player* picks a *strategy*, meaning a choice of what to do. Each player's
payoff depends on everyone's choices. An *equilibrium* is a set of choices in
which no player can do better by changing only their own choice.

In *The Strategy of Conflict*, Schelling asked people this very question.
Any place and time is an equilibrium: if both choose it, neither gains by
switching. So the mathematics alone does not pick an answer. Yet most people
chose the same one: noon at Grand Central Station. A *focal point* is an
equilibrium that stands out, by convention, uniqueness or salience (being
the obvious one to notice). Players reach it because each expects the others
to.

To see why salience matters, model it with :math:`k` players and :math:`n`
options. Each player chooses independently:

#. With probability :math:`s`, the player picks the salient option.
#. Otherwise, with probability :math:`1-s`, the player picks uniformly among
   all :math:`n` options, the salient one included, like
   ``random.choice(options)``.

The salient option is then chosen with probability :math:`s + (1-s)/n` and
each other one with :math:`(1-s)/n`. All players coincide with probability

.. math::

   P = \left(s + \frac{1-s}{n}\right)^k + (n - 1)\left(\frac{1-s}{n}\right)^k.

In words: the first term is the chance that everyone lands on the salient
option. The second adds the chance that everyone lands on the same one of
the other :math:`n - 1` options.

- **Without salience** (:math:`s = 0`), :math:`P = n^{1-k}`. Each extra
  player divides the chance of agreement by :math:`n`. Ten options and five
  players give one chance in 10,000.
- **With salience**, each extra player multiplies it by only about
  :math:`s + (1-s)/n`. With :math:`s = 0.9` and the same ten options and five
  players, :math:`P \approx 0.91^5 \approx 0.62`.
- So a strongly salient answer keeps even a large group coordinated.
  Blockchain oracles and voting games rely on the truth being that salient
  answer.

*Implementation:* :func:`blockchainkit.economics.systems.coordination.coordination_probability`
and :func:`blockchainkit.economics.systems.coordination.play_coordination`.
Salience is a single probability shared by every player; Schelling's
experiments measured it rather than assuming it.

*References:* T. C. Schelling, *The Strategy of Conflict*, Harvard
University Press (1960), chapter 3.

.. minigallery:: ../../examples/economics/coordination/plot_01_schelling_focal_points.py

1961 -- Vickrey's Second-Price Auction and Truthful Bidding
-----------------------------------------------------------

In a *sealed-bid* auction, each bidder writes down one secret bid and the
highest bid wins. In a *first-price* auction, the winner pays its own bid.
Each bidder has a *value*: the most the item is worth to it. Bidding that
true value guarantees zero profit, even when you win. So every bidder
*shades* its bid: it bids below its value. By how much depends on what it
guesses the others will bid, and a wrong guess costs money.

Vickrey changed one rule. The winner pays the second-highest bid instead.
A bid then decides only whether you win, never the price you pay.

#. Each bidder :math:`i` submits a sealed bid :math:`b_i`.
#. The highest bid wins.
#. The winner pays the highest of the other bids,
   :math:`\max_{j \ne i} b_j`, like ``max(b for j, b in bids.items() if j != i)``.

Economists measure a bidder's gain by its *utility*, here simply its profit
in money. The bidder with value :math:`v_i` has utility

.. math::

   u_i(b_i) = \begin{cases} v_i - \max_{j \ne i} b_j & \text{if } b_i > \max_{j \ne i} b_j,\\
   0 & \text{otherwise.} \end{cases}

In words: if your bid beats every other bid, your profit is your value minus
the best rival bid. Otherwise you get nothing and pay nothing.

Why bidding your true value :math:`b_i = v_i` is best:

- It wins exactly when the price :math:`\max_{j \ne i} b_j` is below
  :math:`v_i`, that is, exactly when winning is profitable.
- Bidding more adds only wins at a price above :math:`v_i`. Those lose money.
- Bidding less gives up only wins at a price below :math:`v_i`. Those would
  have made money.

For example, take :math:`v_i = 10`. If the best rival bids 7, bidding 10 wins
and earns 3, while bidding 6 loses and earns 0. If the best rival bids 12,
bidding 10 loses and earns 0, while bidding 13 wins and earns :math:`-2`.

So truthful bidding is optimal whatever the others do. Game theorists call
this a *dominant strategy*: a choice that is best no matter what the others
choose. A *mechanism* is a set of rules that turns everyone's reports into an
outcome and payments, like a function from bids to a winner and a price.
Mechanisms that make honest reporting optimal are the template for fee
mechanisms and builder auctions on blockchains.

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

Myerson asked which auction gives the seller the most *expected revenue*:
the average it earns if the auction were run many times. Each bidder's value
is *private*: only the bidder knows it. The seller knows only how values are
spread, as a probability distribution.

- :math:`F(v)` is the probability that a value is at most :math:`v` (the
  *cumulative distribution function*).
- :math:`f(v) = F'(v)` is its *density*, the height of the histogram at
  :math:`v`.
- For values uniform on :math:`[0, h]`, :math:`F(v) = v/h` and
  :math:`f(v) = 1/h`.

The seller cannot charge each bidder its value. A bidder would then pretend
to value the item less. To keep bidders honest, the seller must leave each
one some profit, called an *information rent*: the bidder earns it only
because it alone knows its value. Myerson accounted for this rent by
replacing each value with its *virtual value*:

.. math::

   \varphi(v) = v - \frac{1 - F(v)}{f(v)},

In words: the virtual value is the value minus a correction for the rent
the seller must leave. For the uniform case it is
:math:`\varphi(v) = 2v - h`.

Myerson showed that expected revenue equals the expected virtual value of
the winner. Maximizing revenue therefore means selling to the bidder with
the highest virtual value, and not selling at all when every virtual value
is negative. A distribution is *regular* when the virtual value rises with
the value. For identical bidders with a regular distribution, the best
auction runs as follows:

#. The seller announces a *reserve price* :math:`r = \varphi^{-1}(0)`, the
   value whose virtual value is zero. It is :math:`h/2` for values uniform on
   :math:`[0, h]`.
#. Each bidder submits a sealed bid. Bids below :math:`r` are ignored.
#. If no bid reaches :math:`r`, the item stays unsold.
#. Otherwise the highest bid wins and pays the larger of :math:`r` and the
   second-highest bid.

That is a second-price auction with a reserve price. With values uniform on
:math:`[0, 100]`, the reserve is 50. Selling to a lone bidder at 40 would
earn less on average than holding out for 50.

The same identity gives *revenue equivalence*:

- Take two auctions that give the item to the same bidders, and in which a
  bidder with the lowest possible value pays nothing.
- They raise the same expected revenue.
- So a first-price auction with shaded bids earns what a second-price one
  earns with truthful bids. With two bidders uniform on :math:`[0, h]`,
  bidders in the first-price auction bid half their value, and both auctions
  earn :math:`h/3` on average.

Blockchain fee mechanisms, from EIP-1559's base fee to builder auctions
(both later on this page), are analyzed with these tools.

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

A *prediction market* sells shares in possible outcomes, such as "it rains
tomorrow". Each share pays 1 if its outcome happens and 0 otherwise. A
trader who believes an outcome has probability :math:`p` buys its shares
while they cost less than :math:`p`, since each then pays back more than it
costs on average. So prices read as the market's probabilities.

But a market with few traders has an empty *order book*: the list of
standing offers to buy and sell, like a dict from price to quantity waiting
to be matched. A trader with information then finds nobody to trade with.

Hanson proposed an *automated market maker*. A *market maker* is a trader
who always stands ready to buy or sell. Hanson's is a program that always
quotes a price, using a formula instead of a human.

#. The market maker stores :math:`q_i`, the number of shares sold of each of
   :math:`n` outcomes, as a list ``q``.
#. A trader asks to buy shares, which changes ``q`` to a new list ``q2``.
#. The trader pays ``C(q2) - C(q)``, the change in a *cost function*
   :math:`C`.
#. When the outcome :math:`w` is known, the market maker pays 1 per winning
   share, :math:`q_w` in total.

The price of each outcome is the derivative of :math:`C`: how fast the cost
grows per extra share of that outcome.

.. math::

   C(q) = b \ln \sum_i e^{q_i/b}, \qquad p_i = \frac{\partial C}{\partial q_i} = \frac{e^{q_i/b}}{\sum_j e^{q_j/b}}.

In words: :math:`C` is a smooth version of ``max(q)``, always between
``max(q)`` and ``max(q) + b * log(n)``. The prices are the *softmax* of
:math:`q/b`, ``[exp(qi / b) / sum(exp(qj / b) for qj in q) for qi in q]``.

- **Prices behave like probabilities.** They are positive and sum to one.
- **The market maker's loss is bounded.** It starts at
  :math:`C(0) = b \ln n` and finally pays :math:`q_w` for the winning outcome
  :math:`w`. Since :math:`C(q) \ge q_w`, the traders have paid it
  :math:`C(q) - C(0) \ge q_w - b \ln n`. Its loss is therefore at most
  :math:`b \ln n`. For two outcomes and :math:`b = 100`, that is about 69.
  This bounded subsidy buys information.
- **The parameter** :math:`b` **sets the liquidity.** *Liquidity* is how much
  you can trade without moving the price much. A larger :math:`b` means each
  trade moves the price less, but the maximum loss is larger.

On-chain prediction markets adopted it. It is also the ancestor of the
formula-priced pools of *decentralized exchanges*: exchanges run by smart
contracts instead of companies.

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

Bitcoin's miners are strangers. Why should they follow the rules?

Section 6 of the Bitcoin paper pays the creator of each block in two ways:
new coins, called the *block reward* or *subsidy*, and the fees of the
block's transactions. The reward does three jobs:

- it distributes the currency;
- it pays for the work that secures the chain;
- Nakamoto argued, it keeps even a powerful miner honest: such a miner "ought
  to find it more profitable to play by the rules."

The argument compares two uses of the same hashrate. The dishonest use is a
*double spend*: paying someone and then erasing the payment. It relies on the
rule that everyone follows the longest chain. A merchant waits for :math:`z`
*confirmations*, meaning :math:`z` blocks built on top of the payment, before
handing over the goods.

#. The attacker pays a merchant :math:`V`.
#. The merchant waits for :math:`z` confirmations and hands over the goods.
#. Meanwhile, the attacker secretly mines a private chain that leaves out the
   payment. It needs about :math:`m = z + 1` blocks to overtake the public
   chain.
#. If the private chain becomes longer, the attacker publishes it. Everyone
   switches to it, the payment vanishes, and the attacker keeps both the
   goods and the coins.

Mined honestly, those :math:`m` blocks earn :math:`mR` for a reward
:math:`R` per block. In the attack they earn nothing unless the private
chain wins. That happens with the whitepaper's *catch-up probability*
:math:`P_z`: the chance that an attacker starting :math:`z` blocks behind
ever draws level. If it wins, the attacker keeps :math:`V` as well as its
blocks' rewards. But a fraction :math:`d` of those rewards has lost its
worth, because the attack shook confidence in the coin. Attacking pays when

.. math::

   P_z \left(V + (1 - d)\, m R\right) > m R .

In words: the attacker's expected gain from attacking (left) beats the sure
income from mining honestly (right).

- **A small miner** rarely catches up, so :math:`P_z` is tiny and only a
  payment worth many blocks tempts it. With 10% of the hashrate and
  :math:`z = 6`, the whitepaper gives :math:`P_z \approx 0.00024`. The
  payment would then have to be worth tens of thousands of block rewards.
- **A majority miner** always catches up, :math:`P_z = 1`, and the condition
  becomes :math:`V > d\, m R`. It is deterred only by the loss :math:`d` on
  "the validity of his own wealth."

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

How many coins should exist, and who creates them? The first Bitcoin
release fixed this *monetary policy* in code.

Two terms:

- A block's *height* :math:`h` is its position in the chain, its index in
  the list. The first block, the *genesis block*, has height 0.
- A *satoshi* is the smallest unit, :math:`10^{-8}` bitcoin. Amounts are
  stored as integers of satoshis, the way prices are often stored in cents.

The block at height :math:`h` creates

.. math::

   S(h) = \left\lfloor 50 \cdot 10^8 / 2^{\lfloor h/210\,000 \rfloor} \right\rfloor \text{ satoshis},

that is, start at 50 bitcoin and halve every 210,000 blocks, rounding down.
:math:`\lfloor x \rfloor` is rounding down, ``//`` in Python. The whole
formula is ``(50 * 10**8) >> (h // 210_000)``.

- Blocks 0 to 209,999 create 50 bitcoin each.
- Blocks 210,000 to 419,999 create 25 each.
- And so on, halving about every four years at ten minutes a block.

Each period issues half as many coins as the one before. So the total
approaches the geometric sum
:math:`210\,000 \times 50 \times (1 + \tfrac12 + \tfrac14 + \cdots) = 21`
million coins.

The rounding down drops fractions of a satoshi at every halving, so the
total falls slightly short. The subsidy, :math:`5 \times 10^9` satoshis at
first, reaches zero at the 33rd halving, around 2140, because
:math:`2^{33} > 5 \times 10^9`. By then 20,999,999.9769 coins are issued.

Consequences:

- **A fixed, predictable supply.** This was a deliberate contrast with
  central-bank money, which a central bank can create when it chooses.
- **Fees must take over.** Miners must eventually be paid by fees alone.

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

Contracts cannot see the world. They do not know the price of ether in
dollars, or who won an election. Someone must report such facts to them. A
service that does this is an *oracle*. A single reporter could simply lie.

Buterin's SchellingCoin asks many reporters and pays them for agreeing with
each other.

#. Each reporter locks a *deposit* :math:`D` in the contract.
#. Each reporter submits a report :math:`r_i`.
#. The contract publishes the *median* report as the answer: the middle value
   of the sorted reports.
#. It pays a reward :math:`R` to each reporter whose report lies between the
   lower and upper *quartiles*, the values a quarter and three quarters of the
   way along the sorted reports (roughly ``sorted(r)[len(r) // 4]`` and
   ``sorted(r)[3 * len(r) // 4]``). Every other reporter loses its deposit.

.. math::

   \text{payout}_i = \begin{cases} R & q_{1/4} \le r_i \le q_{3/4},\\
   -D & \text{otherwise.} \end{cases}

In words: reports in the middle half earn :math:`R`; reports outside it lose
:math:`D`.

Why it works:

- A reporter is paid for agreeing with the others. So its best report is the
  one it expects the others to make.
- Each reporter knows the truth, and expects the others to know it. So the
  truth is the focal point: if everyone else reports it, reporting it too is
  best.

Its limits:

- **It is only as honest as its majority.** A *cartel*, a group that secretly
  coordinates, can report one false value.

  - Above a quarter of the reports, the cartel is paid, since its value then
    reaches the quartile.
  - Above half, it sets the median.
  - Above three quarters, it pushes the honest reports outside the quartiles
    and takes their deposits.

- **A bribe that is never paid can move the focal point.** This is Buterin's
  later *P + epsilon attack*:

  #. The attacker publicly promises a reward to everyone who reports a false
     answer :math:`X`, payable only if :math:`X` loses. The reward is
     slightly more than they would have earned by reporting the truth.
  #. Now reporting :math:`X` is the safer choice for each reporter. If
     :math:`X` wins, they are paid by the scheme. If :math:`X` loses, they
     are paid by the attacker.
  #. So everyone reports :math:`X`, :math:`X` wins, and the promise costs
     nothing.

UMA's and Kleros's dispute resolution build on the same idea.

*Implementation:* :func:`blockchainkit.economics.systems.oracles.schelling_round`,
which settles one round; there are no rounds over time, no commit-reveal of
reports, and no token whose value depends on the oracle's honesty.

*References:* V. Buterin, *SchellingCoin: a minimal-trust universal data
feed*, Ethereum Blog (March 2014); V. Buterin, *The P + epsilon attack*,
Ethereum Blog (January 2015).

.. minigallery:: ../../examples/economics/coordination/plot_02_schellingcoin_oracle.py

2016 -- Carlsten et al.: the Instability of Bitcoin without the Block Reward
----------------------------------------------------------------------------

Once the subsidy is gone, a block earns only the fees it collects. What
does that do to miners?

Pending transactions wait in the *mempool*, a pool of unconfirmed
transactions that each miner keeps, like a dict from transaction id to
transaction. Fees arrive in the mempool at a steady rate. Blocks, however,
arrive at random: finding one is a lottery, with one win every ten minutes
on average. So a block's reward is proportional to the time since the last
one, and a block found right after another holds almost nothing. Carlsten,
Kalodner, Weinberg and Narayanan showed two consequences.

**First, the mining gap.** :math:`t` seconds after a block, the next one is
worth :math:`S + ft` for a subsidy :math:`S` and a fee rate :math:`f`. Let
:math:`c` be what a miner spends on electricity per block it expects to
find. While :math:`S + ft < c`, mining loses money, so miners pause for a
*mining gap* of

.. math::

   t^* = \max\left(0, \frac{c - S}{f}\right)

seconds. In words: the time it takes fees to pile up enough to cover the
cost the subsidy does not. It is zero while the subsidy covers the cost.
While miners pause, less hashrate protects the chain.

**Second, undercutting.** A *fork* is a split in the chain: two competing
blocks at the same height, like two branches in git. The *tip* is the latest
block of the chain. A miner can fork the tip instead of extending it.

#. The tip has just claimed more fees than remain in the mempool.
#. A miner re-mines the tip's height, in a rival block that claims the tip's
   fees as well as the pending ones. The fork offers more than building on
   the tip.
#. By *undercutting*, the miner claims only part of the fees in its own
   block. It leaves the rest for the next block.
#. That makes its fork the more lucrative branch for other miners to build
   on. If they do, the original tip is dropped and its miner loses its
   reward.

They also showed that *selfish mining* becomes profitable for arbitrarily
small miners. Selfish mining means hiding found blocks and releasing them at
the best moment, to waste other miners' work.

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

Is mining honestly always a miner's best choice?

Kiayias, Koutsoupias, Kyropoulou and Tselekounis modeled mining as a
*stochastic game*: a game played over many rounds, in which chance (who
finds the next block) moves the players between states. Each miner chooses
which block to extend and when to publish. A *best response* is the best
strategy given what the others do.

- When every miner's hashrate is small, honest mining is a best response to
  honest mining.
- A large miner gains by deviating, and other equilibria arise.

The same year, Sapirshtein, Sompolinsky and Zohar computed a miner's best
deviation exactly. Their model:

#. A miner has a share :math:`\alpha` of the hashrate. Each new block is the
   miner's with probability :math:`\alpha` and the others' with probability
   :math:`1 - \alpha`.
#. The state :math:`(a, h)` is the pair of lengths of the miner's private
   branch and of the public one.
#. In each state, the miner chooses whether to publish, wait or give up and
   adopt the public chain.
#. When two branches tie, a fraction :math:`\gamma` of the other miners
   build on the miner's block.

A strategy :math:`\pi` is a rule for what to do in each state, like a dict
``policy[(a, h)] = "wait"``. Over all strategies, the miner's best long-run
share of the blocks in the chain is

.. math::

   \rho^*(\alpha, \gamma) = \max_\pi \lim \frac{R_\text{miner}}{R_\text{miner} + R_\text{others}}.

In words: run the best strategy forever, and count what fraction of the
final chain's blocks are the miner's.

A ratio is hard to optimize directly. A *Markov decision problem* is easier:
choose an action in each state of a random process to maximize the average
reward per step. Standard algorithms solve it, for example *value
iteration*, which repeatedly improves an estimate of each state's worth. The
trick turns the ratio into such a problem:

#. Guess a share :math:`\rho`.
#. Pay the miner :math:`r_\text{miner} - \rho (r_\text{miner} + r_\text{others})`
   per block: its own blocks minus :math:`\rho` times all blocks.
#. A share above :math:`\rho` is achievable exactly when some strategy makes
   this reward positive on average. Solve the problem to find out.
#. Raise or lower the guess, and repeat. This *bisection*, a binary search
   on a real number, finds :math:`\rho^*`.

What it shows:

- Mining honestly earns :math:`\alpha`. So honest mining is an equilibrium
  exactly when :math:`\rho^* = \alpha`.
- With :math:`\gamma = 0`, ties going to honest blocks, that holds up to
  about :math:`\alpha = 0.33`. A miner with less than about a third of the
  hashrate cannot gain by deviating.

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

Coin prices swing wildly, which makes them awkward for payments. A
*stablecoin* aims at a fixed price, usually one US dollar. Dai, launched in
December 2017, is backed by ether locked in contracts rather than dollars in
a bank. The locked ether is *collateral*: something of value pledged to
secure a loan, as at a pawnshop.

#. A user locks ether in a *vault* (then called a collateralized debt
   position).
#. The user draws newly *minted* (created) Dai as a loan. The vault records
   this as its *debt*.
#. An oracle keeps reporting the price of ether.
#. The vault must always satisfy the rule below at that price.

.. math::

   \text{collateral} \times \text{price} \ge 1.5 \times \text{debt}

In words: the collateral must be worth at least 150% of the debt. Lock 3
ether at $100 each, worth $300, and you can draw up to 200 Dai.

If a fall in the price breaks this inequality:

#. Anyone may *liquidate* the vault.
#. The liquidator repays its debt in Dai, which *burns* that Dai: it is
   destroyed and leaves circulation.
#. The liquidator takes collateral worth the debt plus a 13% penalty.

The margin is what keeps every Dai backed:

- At the moment of liquidation, the vault holds collateral worth 1.5 times
  its debt. That is more than the 1.13 times the liquidator takes.
- The price can fall by a third before the collateral is worth less than the
  debt, since :math:`1.5 \times 2/3 = 1`.
- Dai becomes *undercollateralized* (backed by less than its value) only if
  the price falls faster than liquidations can follow. That happened on 12
  March 2020. The network was congested, so transactions were delayed, and
  some liquidators won collateral for almost nothing.

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

An order book needs market makers who post and cancel orders constantly.
That is too expensive on chain, where every update is a paid transaction.

Uniswap, launched in November 2018, replaced the order book with a *pool*: a
contract holding reserves of two tokens, :math:`x` of one and :math:`y` of
the other. Like Hanson's market maker, a formula sets the price. The rule is
that trades keep the product :math:`xy` constant.

#. A trader pays in :math:`\Delta x` of the first token.
#. The pool keeps 0.3% as a fee, so only :math:`0.997\,\Delta x` counts.
#. The pool pays out the :math:`\Delta y` of the second token that restores
   the product. In integers, as Uniswap V2 computes it:
   ``dy = y * 997 * dx // (1000 * x + 997 * dx)``.

.. math::

   (x + 0.997\,\Delta x)(y - \Delta y) = x y.

In words: after the trade, the reserves, counting only the input after the
fee, multiply to the same product as before.

- **Every trade moves the price.** The pool's price is the ratio
  :math:`p = y/x`. The more of a token is bought, the scarcer and dearer it
  becomes.
- **No trade can empty the pool.** :math:`\Delta y` is always less than
  :math:`y`.

Anyone can deposit both tokens and earn the fees. Such a depositor is a
*liquidity provider*. It bears *impermanent loss*:

#. The provider deposits at a price :math:`p`.
#. The market price elsewhere moves by a factor :math:`r`.
#. *Arbitrageurs*, traders who profit from price differences between
   markets, trade with the pool until its price matches. They buy from it
   the token that rose.
#. With the product fixed, :math:`x = \sqrt{xy/p}` and
   :math:`y = \sqrt{xy\,p}`. So the deposit's value
   :math:`px + y = 2\sqrt{xy\,p}` grows by a factor :math:`\sqrt{r}`.
#. Holding the two tokens instead would have grown by :math:`(1 + r)/2`.

The ratio :math:`2\sqrt{r}/(1+r)` is at most one, with equality only at
:math:`r = 1`. If the price quadruples, :math:`r = 4`, the ratio is
:math:`4/5`: the deposit is worth 20% less than holding. The loss is
impermanent because it vanishes if the price returns.

Uniswap V2 (2020) added a price oracle that reads the price before the first
trade of each block. A transaction moves the price only after that reading,
so no single transaction can move the oracle.

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

On Ethereum, a transaction's fee is set by its *gas*: a unit of computing
work. Each transaction offers a price per unit of gas. Miners then ordered
transactions by fee, highest first.

Daian et al. watched arbitrage bots on decentralized exchanges. When an
opportunity appeared, only the first transaction to reach it could take it.
So the bots competed in a *priority gas auction*:

#. A bot sends a transaction with some fee.
#. A rival sees it in the public mempool and replaces its own pending
   transaction with one paying a higher fee. Each replacement must raise the
   fee by at least a fraction :math:`\beta`.
#. The bots keep outbidding each other while a raise still leaves a profit.
#. The miner puts the highest bid first, and that bot takes the opportunity.

Suppose every bot values the opportunity at :math:`V`. Bidding stops at a
price whose next raise would exceed :math:`V`:
:math:`(1 + \beta)\,\text{price} > V`. The winner therefore keeps

.. math::

   V - \text{price} < V - \frac{V}{1 + \beta} = \frac{\beta}{1 + \beta}\, V,

and the rest goes in fees to whoever orders the block. In words: the winner
keeps only a small slice of the prize. With :math:`\beta = 0.1`, it keeps
less than :math:`1/11`, about 9%.

They called this value *miner extractable value* (MEV): what a block
producer can capture by choosing which transactions go in a block and in
what order. MEV also threatens consensus itself:

- Suppose a past block holds more MEV than the reward for a new one.
- Then a miner gains by forking the chain to re-mine that block and capture
  the MEV.

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

In February 2020, two attacks hit the bZx lending protocol. Both used flash
loans to move a decentralized exchange's price within one transaction. Then
they exploited protocols that trusted that price.

A *flash loan* must be repaid in the same transaction. If it is not, the
whole transaction *reverts*: it is undone, like an exception that rolls back
every change. The lender can never lose its money, so it needs no
collateral. Anyone can briefly command a large sum.

In its simplest form, the attack uses a constant-product pool holding
:math:`x` tokens and :math:`y` dollars. The *spot price* is the pool's price
right now, :math:`y/x`.

#. The attacker flash-borrows :math:`U` dollars.
#. It spends them on the token in the pool. The pool is left with
   :math:`y + U` dollars and :math:`xy/(y+U)` tokens. So the attacker
   receives :math:`xU/(y+U)` tokens, and the spot price rises to
   :math:`(y+U)^2/(xy)`.
#. At that price, the tokens bought appear worth :math:`U(y + U)/y`, more
   than the :math:`U` they cost.
#. The attacker deposits them with a lender that reads the spot price and
   demands 150% collateral, and borrows against them.
#. It repays the flash loan from the new loan and keeps the difference.

The loan in step 4 is

.. math::

   \frac{U(y + U)}{1.5\,y} > U \quad\text{whenever}\quad U > \frac{y}{2}.

In words: once the attacker spends more than half the pool's dollars, the
new loan exceeds the flash loan, and the attack profits. With
:math:`y = 1{,}000{,}000` and :math:`U = 2{,}000{,}000`, the attacker
borrows 4,000,000 and keeps 2,000,000.

- **The lender loses.** It is left holding tokens worth far less than it
  lent once the price recovers.
- **The defence is an older price.** A price recorded before the
  transaction, like Uniswap V2's, cannot be moved this way.

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

Bitcoin sells block space by a first-price auction: each user bids a fee,
and the block's producer takes the highest bids. Ethereum did the same until
the London upgrade of August 2021. Vickrey's analysis predicts the problems:

- users must guess how much to shade their bids;
- no bid is obviously right;
- prices swing with demand.

EIP-1559 instead posts a price, like a price tag in a shop, and adjusts it
with demand. That price is the *base fee* :math:`b_t` per unit of gas.

#. Each block has a gas *target* :math:`g^*`, half the block's capacity.
#. Every transaction pays the base fee, which is *burned*: destroyed, so that
   nobody receives it.
#. Every transaction also pays a *tip* to the block's producer.
#. After each block, the base fee moves by up to an eighth. It goes up when
   the block used more gas :math:`g_t` than the target, and down when it used
   less.

.. math::

   b_{t+1} = b_t \left(1 + \frac{1}{8}\, \frac{g_t - g^*}{g^*}\right).

In words: a full block raises the base fee by 12.5%, an empty block lowers it
by 12.5%, and a block exactly at the target leaves it unchanged. It works
like a thermostat.

Roughgarden's analysis showed why this helps:

- **Bidding is easy.** The price is posted rather than bid. So, outside
  sudden rises in demand, bidding the base fee plus a small tip is optimal
  for users.
- **Producers cannot inflate it.** The base fee is burned. So a producer
  gains nothing by raising it with fake transactions.
- **Producers have no reason to deviate.** A *myopic* producer, one that
  cares only about the current block, does best by including the highest
  tips.
- **Side deals do not pay.** Users and producers cannot profit from an
  off-chain deal that skips the base fee, since it goes to neither of them.

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

A *swap* is a trade with a pool. Before it is mined, it waits in the public
mempool, where anyone can see it. The victim's only protection is its
*slippage tolerance* :math:`s`: its swap reverts if it would receive less
than a fraction :math:`1 - s` of the output quoted before the attack.

A *sandwich* attacker wraps the victim's swap between two of its own:

#. The attacker sees the victim's purchase in the mempool.
#. It *front-runs*: it buys the same token, an amount :math:`a`, just before
   the victim. That raises the price the victim pays.
#. The victim's swap runs at the higher price and pushes the price up
   further.
#. The attacker *back-runs*: it sells just after, at that higher price.

A larger front-run :math:`a` moves the price more and earns the attacker
more. But the victim's output :math:`\text{out}_\text{victim}(a)` falls as
:math:`a` grows, and the attacker gets nothing if the victim's swap reverts.
So the attacker maximizes its profit over the front-runs that keep

.. math::

   \text{out}_\text{victim}(a) \ge (1 - s)\,\text{out}_\text{victim}(0),

that is, after the front-run, the victim must still get at least
:math:`1 - s` times what it would have got with no attack.

- **Large trades suffer most.** For a large victim trade, the best attack is
  the largest front-run allowed.
- **Small trades are safe.** The attacker pays the pool's fee twice. So a
  trade too small to move the price by more than those two fees is not worth
  attacking.

Zhou, Qin, Torres, Le and Gervais derived this optimal attack and measured
sandwiches on Uniswap. They showed that a looser tolerance hands more of
each trade to the attacker. Responses include:

- *private transaction relays*, which send a transaction straight to a block
  producer and skip the public mempool;
- *batch auctions*, which execute a batch of orders together at one price,
  so their order no longer matters.

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

Extracting MEV takes *searchers* (bots that find MEV opportunities), *order
flow* (a stream of users' transactions) and infrastructure. A validator that
has them earns more per unit of stake than one that does not. So *stakers*,
people who entrust their coins to a validator, move to it. MEV pushes proof
of stake toward a few large operators.

*Proposer-builder separation* splits the job in two. Specialized *builders*
assemble blocks and bid for each *slot*, the 12-second window in which one
block is added. The *proposer*, any validator, only signs the best bid.

#. The protocol picks a validator as proposer for the slot.
#. Each builder :math:`b` assembles a block. The block holds fees :math:`f`
   and an MEV opportunity :math:`M`, of which the builder can capture a
   fraction :math:`\sigma_b`. So it values the block at
   :math:`v_b = f + \sigma_b M`.
#. In a second-price auction, the builders bid these values.
#. The proposer signs the winning block. It receives the runner-up's value,
   or what it could build itself if that is more.

.. math::

   \text{revenue} \ge v_{(2)} = f + \sigma_{(2)} M.

In words: the proposer earns at least the second-highest builder's value for
the block.

- **Skill no longer matters.** This bound does not depend on the proposer's
  own skill.
- **Small stakers keep up.** With two or more capable builders,
  :math:`\sigma_{(2)}` is close to one. So a solo staker earns about as much
  per slot as a professional operator.
- **Trust remains.** Flashbots' MEV-Boost ran the auction outside the
  protocol from Ethereum's move to proof of stake in September 2022. It runs
  through *relays*, middlemen that hold the builder's block until the
  proposer signs. Both builders and proposers must trust them. Enshrining
  the auction in the protocol remains open.

*Implementation:* :func:`blockchainkit.economics.systems.pbs.simulate_pbs`,
which picks proposers with :class:`~blockchainkit.consensus.systems.pos.StakeSampler`
and sells each slot by
:func:`~blockchainkit.economics.systems.auctions.second_price_auction`.
MEV-Boost's auction is first-price with open bids through relays; with
many builders the price approaches the runner-up's value either way.

*References:* V. Buterin, *Proposer/block builder separation-friendly fee
market designs*, ethresear.ch (June 2021); Flashbots, *MEV-Boost* (2022).

.. minigallery:: ../../examples/economics/mev/plot_03_mev_boost_pbs.py
