Breakthroughs in Blockchain Fraud
=================================

.. include:: /_generated/nav/fraud.rst

.. epigraph::

   "Trust, but verify."
   -- Russian proverb, as quoted by Ronald Reagan, 1987

Most of the money lost in cryptocurrencies is lost to fraud, not to broken
cryptography or consensus: Ponzi schemes, pump-and-dumps, rug pulls,
phishing, and custodians that lose or lend their customers' coins. The
schemes are old; the blockchain changes how they run and what evidence they
leave. A public ledger makes fraud measurable, and some honesty provable:
an exchange can prove what it holds and what it owes. This chronology
follows both sides, from Ponzi's scheme and Benford's law to proofs of
solvency, the contracts whose source deceives the reader who checks it, and
the manipulation and phishing of the last few years.

Several neighbours live elsewhere: the GovernMental Ponzi game and ERC-20's
approve race are in :doc:`contracts_breakthroughs`, transaction
malleability itself in :doc:`structures_breakthroughs`, and flash loans,
oracle manipulation and front-running in :doc:`economics_breakthroughs`.

The models in :mod:`blockchainkit.fraud` are pure functions, small seeded
simulations, and contracts on
:class:`~blockchainkit.contracts.systems.world.World`. Solidity appears only
as what a victim reads: each scam contract's example shows the source, then
reproduces its behavior in Python. :doc:`/protocol` lists where the models
depart from deployed systems.

.. contents:: Timeline
   :local:
   :depth: 1

1920 -- Ponzi's Scheme: Paying Old Investors with New Money
-----------------------------------------------------------

Charles Ponzi promised Boston investors a 50% return in 45 days, supposedly
from buying international reply coupons cheaply abroad and redeeming them
in the United States. He bought almost none: every payout came from later
deposits. Such a scheme meets its promises only while new money grows fast
enough. A deposit :math:`D` made :math:`\tau` periods ago is owed
:math:`(1 + r)D` today, and must be paid from today's deposits, of which
the operator keeps a fraction :math:`s`. If deposits grow by :math:`g` per
period, today's are :math:`(1 + g)^\tau D`, so the scheme keeps up exactly
when

.. math::

   (1 - s)(1 + g)^\tau \ge 1 + r .

On Ponzi's terms, with one 45-day period and nothing kept, deposits must
grow by half every 45 days, and no pool of investors grows like that for
long. Once growth falls below that rate, each payout is larger than the
deposits that fund it, the cash runs out, and the latest investors lose
what they paid in. Ponzi collapsed
within eight months, in August 1920.

*Implementation:* :func:`blockchainkit.fraud.systems.ponzi.simulate_ponzi`
and :func:`blockchainkit.fraud.systems.ponzi.breakeven_growth`. Every
deposit is repaid once, after a fixed term, and nobody reinvests; Ponzi's
investors mostly rolled their returns over, which delayed the collapse.

*References:* M. Zuckoff, *Ponzi's Scheme: The True Story of a Financial
Legend*, Random House (2005); M. Artzrouni, *The mathematics of Ponzi
schemes*, Mathematical Social Sciences 58(2), 190–201 (2009).

.. minigallery:: ../../examples/fraud/schemes/plot_01_ponzi_scheme.py

1938 -- Benford's Law: Detecting Fabricated Figures
---------------------------------------------------

Simon Newcomb noticed in 1881 that the first pages of books of logarithms
were dirtier than the last. Frank Benford tested the observation on 20,229
numbers, from river areas to street addresses, and found the same law: in
data spread over several orders of magnitude, the leading digit is
:math:`d` with probability

.. math::

   P(d) = \log_{10}\left(1 + \frac{1}{d}\right),

30.1% for 1 and 4.6% for 9. The reason is logarithmic: a number has
leading digit :math:`d` exactly when the fractional part of its base-10
logarithm lies between :math:`\log_{10} d` and :math:`\log_{10}(d + 1)`, an
interval of length :math:`P(d)`. If that fractional part is spread evenly,
as it is for data covering several orders of magnitude, each digit occurs
in proportion to its interval. Products of many random factors, such as
payments and prices, have logarithms that are sums of many terms and so
spread widely. People inventing numbers instead spread the first digit far
more evenly. That difference is why auditors, following Nigrini, test
reported figures against the law, and why it has been used to question the
volumes cryptocurrency exchanges report.

*Implementation:* :func:`blockchainkit.fraud.systems.benford.benford_test`,
which returns Pearson's chi-square statistic with its exact p-value
(:func:`blockchainkit.fraud.systems.benford.chi_square_survival`) and
Nigrini's mean absolute deviation with his conformity bounds. Only the
first digit is tested; Nigrini's practice adds second-digit and
first-two-digit tests.

*References:* F. Benford, *The law of anomalous numbers*, Proceedings of
the American Philosophical Society 78(4), 551–572 (1938); S. Newcomb,
*Note on the frequency of use of the different digits in natural numbers*,
American Journal of Mathematics 4(1), 39–40 (1881).
`DOI <https://doi.org/10.2307/2369148>`__; M. J. Nigrini, *Benford's Law*,
Wiley (2012).

.. minigallery:: ../../examples/fraud/figures/plot_01_benford_law.py

2013 -- Maxwell's Merkle-Sum-Tree Proof of Reserves
---------------------------------------------------

An exchange can prove that it holds coins by moving them or signing with
their keys, but holdings mean nothing without the debts they must cover.
Gregory Maxwell proposed that the exchange also prove its liabilities, by
publishing the root of a Merkle tree over its customer balances in which
every node carries the sum of the balances below it, and every hash covers
both children's sums:

.. math::

   \text{node} = \big(H(s_L \,\|\, s_R \,\|\, h_L \,\|\, h_R),\; s_L + s_R\big).

Because the sums are hashed, the root fixes every sum in the tree, and the
exchange cannot show different customers different totals. The root's sum
is the declared total liabilities, which the public compares with the
reserves; each customer checks a proof of logarithmic size, the sibling
hashes and sums on its path, that its balance is counted. The exchange can
lower the declared total in only two ways. It can leave customers out, but
those left out can notice: if each checks independently with probability
:math:`f`, cheating :math:`k` of them goes unnoticed with probability
:math:`(1 - f)^k`. Or it can add a fake account with a negative balance to
cancel real ones; customers reject any negative sibling sum on their path,
so such an account is caught by those whose proofs include it.

*Implementation:* :class:`blockchainkit.fraud.utils.merkle_sum.MerkleSumTree`,
:func:`blockchainkit.fraud.utils.merkle_sum.verify_sum_proof`,
:func:`blockchainkit.fraud.systems.reserves.liability_tree`,
:func:`blockchainkit.fraud.systems.reserves.audit` and
:func:`blockchainkit.fraud.systems.reserves.detection_probability`. Leaves
hash a label, a balance and a salt with SHA-256 and canonical JSON; the
reserves side, signing with the exchange's keys, is not modelled.

*References:* Z. Wilcox, *Proving your bitcoin reserves*, Bitcoin Forum
(February 2014), describing Maxwell's 2013 proposal; Y. Ji and K. Chalkias,
*Generalized proof of liabilities*, ACM CCS 2021.

.. minigallery:: ../../examples/fraud/solvency/plot_01_maxwell_proof_of_reserves.py

2014 -- The Mt. Gox Collapse and the Malleability Excuse
--------------------------------------------------------

On 7 February 2014 Mt. Gox, the largest bitcoin exchange, halted
withdrawals and blamed transaction malleability: an attacker could alter a
withdrawal's signature in flight, so that it confirmed under a different
txid; the exchange, which looked for its withdrawals by txid, would believe
them failed and pay again. Within three weeks it filed for bankruptcy,
about 850,000 bitcoins short. An exchange losing to malleability loses
exactly the withdrawals it re-sends, those whose original txid never
appears on the chain:

.. math::

   \text{loss} = \sum_{w \,:\, \mathrm{txid}(w) \notin \text{chain}} a_w .

Each such loss therefore requires a malleated copy of the withdrawal to
have been broadcast and confirmed, and broadcasts are public. Decker and
Wattenhofer had been recording the network's transactions and counted the
malleated ones: before the announcement, they could account for at most 386
bitcoins, a tiny fraction of the shortfall. The coins had been leaving for
years; the excuse covered a long insolvency.

*Implementation:* :func:`blockchainkit.fraud.systems.custody.reissue_missing`
on :class:`~blockchainkit.structures.systems.transaction.Transaction`.
Bitcoin's malleation re-encoded a signature without its key; here a
second signature by the exchange over the same payment stands in for it,
since the teaching Schnorr signatures cannot be altered by a third party.
Tracking by ``unsigned_id``, like segregated witness's txid, loses nothing.

*References:* C. Decker and R. Wattenhofer, *Bitcoin transaction
malleability and MtGox*, ESORICS 2014, LNCS 8713, 313–326.
`DOI <https://doi.org/10.1007/978-3-319-11212-1_18>`__.

.. minigallery:: ../../examples/fraud/solvency/plot_02_mtgox_malleability_excuse.py

2015 -- Provisions: Privacy-Preserving Proofs of Solvency
---------------------------------------------------------

Maxwell's proof reveals the total liabilities, and a proof of reserves
reveals which addresses the exchange owns; few exchanges were willing to
publish either. Dagher, Bünz, Bonneau, Clark and Boneh hid both behind
Pedersen commitments :math:`C(v, r) = g^v h^r`, which hide :math:`v` behind
the random :math:`r` and multiply into a commitment to the sum. For every
address :math:`i` of a large public set, with public balance :math:`b_i`,
the exchange commits to :math:`s_i b_i`, where :math:`s_i` is 1 if it owns
the address and 0 if not, so the set hides which addresses are its own. It
also commits to every customer balance :math:`\ell_j`, and the quotient

.. math::

   \frac{\prod_i C(s_i b_i, r_i)}{\prod_j C(\ell_j, t_j)}
   = C\Big(\sum_i s_i b_i - \sum_j \ell_j,\; \sum_i r_i - \sum_j t_j\Big)

commits to its surplus, reserves minus liabilities. Commitments alone
would let the exchange cheat, so zero-knowledge proofs close each gap: each
asset commitment holds 0 or the public balance, so assets cannot be
inflated; and every liability and the surplus lie in a range
:math:`[0, 2^n)`, so no fake negative balance cancels real ones and the
surplus is not negative. A range proof commits to each bit and proves it
is 0 or 1. Customers check their own commitment with a blinding factor
sent to them privately. Nothing else is revealed.

*Implementation:* :class:`blockchainkit.fraud.systems.provisions.SolvencyProver`
and :func:`blockchainkit.fraud.systems.provisions.verify_solvency`, with
Cramer-Damgård-Schoenmakers OR proofs
(:func:`blockchainkit.fraud.systems.provisions.prove_either`) and bitwise
range proofs (:func:`blockchainkit.fraud.systems.provisions.prove_range`)
in the 62-bit teaching group. Provisions also proves knowledge of each
owned address's key and, in its third protocol, that no two exchanges
claim the same address; neither is modelled here.

*References:* G. G. Dagher, B. Bünz, J. Bonneau, J. Clark and D. Boneh,
*Provisions: Privacy-preserving proofs of solvency for Bitcoin exchanges*,
ACM CCS 2015, 720–731. `DOI <https://doi.org/10.1145/2810103.2813674>`__;
R. Cramer, I. Damgård and B. Schoenmakers, *Proofs of partial knowledge
and simplified design of witness hiding protocols*, CRYPTO 1994, LNCS 839,
174–187. `DOI <https://doi.org/10.1007/3-540-48658-5_19>`__.

.. minigallery:: ../../examples/fraud/solvency/plot_03_provisions_proof_of_solvency.py

2016 -- Verified Source Code, and Why a Verified Source Can Still Deceive
-------------------------------------------------------------------------

Contracts are deployed as bytecode. Block explorers let authors publish the
source and *verify* it by recompiling it and comparing the result with the
code at the address; Solidity's metadata hash, added in version 0.4.7 in
December 2016, pins the compiler and settings so that the match is exact.
Users came to read the "verified" badge as "safe". It certifies only which
code sits at one address. A proxy's verified source shows that every call
is forwarded, by ``DELEGATECALL``, to an implementation address held in
storage, which its admin may change at any time, so the behavior that runs
is

.. math::

   \text{code}(\text{proxy}) \circ \text{code}\big(\text{storage}_{\text{proxy}}[\text{slot}]\big),

and only the first factor was verified: the admin can swap the second after
users have read the source. The same holds for code reached
through a constructor argument, an external library, or a parent contract
the reader skips.

*Implementation:* :func:`blockchainkit.fraud.systems.verification.verify_source`
compares the class at an address, and
:func:`blockchainkit.fraud.systems.verification.effective_code` follows an
:class:`~blockchainkit.contracts.systems.proxies.EIP1967Proxy`;
:class:`~blockchainkit.fraud.systems.verification.SeizableToken` is the
upgrade that lets the owner take any balance. There is no compiler and no
bytecode: code is compared by class identity.

*References:* Solidity documentation, *Contract metadata* (introduced in
version 0.4.7, 2016); P. Murray, N. Welch and J. Messerman, *EIP-1967:
Proxy storage slots* (2019). `URL <https://eips.ethereum.org/EIPS/eip-1967>`__.

.. minigallery:: ../../examples/fraud/scam_contracts/plot_01_verified_source_deception.py

2017 -- Bartoletti et al.: Dissecting Ponzi Schemes on Ethereum
---------------------------------------------------------------

Bartoletti, Carta, Cimoli and Saia collected 184 Ponzi schemes running as
Ethereum contracts, most of them with public source code, and classified
them by how they pay: *chain-shaped*, where each deposit is queued and paid
a multiple of itself out of later deposits in order of arrival;
*tree-shaped*, paying the investor who referred each newcomer;
*waterfall*, pouring each deposit down the list of earlier investors from
the first; and *handover*, passing each newcomer's payment to the investor
before. In a chain paying :math:`m` times every deposit, with an owner's
fee :math:`f`, all payouts come from the :math:`1 - f` of deposits left
after the fee. With :math:`N` equal deposits, at most
:math:`(1 - f)N/m` investors can be paid, so at least a fraction

.. math::

   1 - \frac{1 - f}{m}

of the investors is unpaid when deposits stop. Their transactions show the
mechanism: payouts leave in the same transactions as newer deposits, and
most investors end below what they paid. They found that such schemes had
taken about 10 million dollars from thousands of users.

*Implementation:* :class:`blockchainkit.fraud.systems.ponzi.ChainPonzi`,
with :func:`blockchainkit.fraud.systems.ponzi.value_flows`, which lists
the transfers a block explorer shows, and
:func:`blockchainkit.fraud.systems.ponzi.ponzi_features`. The features are
two of the simplest; later detectors trained classifiers on dozens of
transaction and bytecode features.

*References:* M. Bartoletti, S. Carta, T. Cimoli and R. Saia, *Dissecting
Ponzi schemes on Ethereum: identification, analysis, and impact*, Future
Generation Computer Systems 102, 259–277 (2020); arXiv:1703.03779 (2017).
`DOI <https://doi.org/10.1016/j.future.2019.08.014>`__.

.. minigallery:: ../../examples/fraud/schemes/plot_02_bartoletti_ponzi_contracts.py

2017-2018 -- ICO Exit Scams and the DAICO
-----------------------------------------

Initial coin offerings raised billions of dollars in 2017 for projects that
existed only as white papers, and nothing tied the team to the money. An
*exit scam* takes the proceeds and disappears; in December 2017 the SEC's
new Cyber Unit obtained an emergency freeze of the PlexCoin sale, whose
promoters had promised a 1,354% return in under a month. Buterin's DAICO
proposal of January 2018 keeps the ether in the sale contract, releases it
to the team at a capped *tap* rate :math:`\tau`, and lets contributors vote
to refund the rest. Since the team can withdraw no faster than the tap, a
team that vanishes after time :math:`t` takes at most

.. math::

   \min(\tau t,\ \text{raised}),

and contributors recover the remainder in proportion to their tokens.

*Implementation:* :class:`blockchainkit.fraud.systems.token_sales.TokenSale`,
with ``tap = 0`` for an ordinary sale. Tokens are a per-contributor count
rather than an ERC-20; the tap can only be set at deployment, and a refund
needs more than half of the tokens, where Buterin's design also lets
holders vote to raise the tap.

*References:* V. Buterin, *Explanation of DAICOs*, Ethereum Research forum
(January 2018). `URL <https://ethresear.ch/t/explanation-of-daicos/465>`__;
U.S. Securities and Exchange Commission, *SEC Emergency Action Halts ICO
Scam*, press release (4 December 2017).

.. minigallery:: ../../examples/fraud/scam_contracts/plot_02_ico_exit_scams_daico.py

2018 -- Gandal et al.: Price Manipulation in the Bitcoin Ecosystem
------------------------------------------------------------------

Between February and November 2013, two accounts on Mt. Gox, later dubbed
the Markus and Willy bots, bought about 600,000 bitcoins without paying for
them, credited with dollars the exchange did not have. Over the same months
the price rose from about 150 to over 1,000 dollars. Gandal, Hamrick, Moore
and Oberman used the leaked Mt. Gox trade records to compare the price
change on days the bots traded with the other days: about 4% a day against
a slight fall. In a thin market buying moves the price; with a net purchase
:math:`q_t` on day :math:`t`, a linear impact :math:`\lambda` and random
noise :math:`\sigma \varepsilon_t`,

.. math::

   \log p_{t+1} = \log p_t + \lambda q_t + \sigma \varepsilon_t .

A genuine buyer is limited by its money; a buyer who need not pay for
:math:`q_t` can raise the price as far as it likes. The noise averages out
across days, so the bots' effect shows up as a higher mean return on the
days they traded and none on the others, which is the pattern Gandal et
al. found.

*Implementation:* :func:`blockchainkit.fraud.systems.manipulation.simulate_bot_market`
and :func:`blockchainkit.fraud.systems.manipulation.return_by_activity`.
The price is a log-normal random walk with Kyle's linear impact; Gandal et
al. regressed actual daily returns on the bots' activity with controls.

*References:* N. Gandal, J. T. Hamrick, T. Moore and T. Oberman, *Price
manipulation in the Bitcoin ecosystem*, Journal of Monetary Economics 95,
86–96 (2018). `DOI <https://doi.org/10.1016/j.jmoneco.2017.12.004>`__.

.. minigallery:: ../../examples/fraud/manipulation/plot_01_willy_bot_price_manipulation.py

2018 -- BitConnect and Lending-Platform Ponzis
----------------------------------------------

BitConnect took bitcoin deposits into a "lending program" said to earn
around 1% a day from a trading bot, and paid recruiters commissions down
several levels of the investors they brought in. Nothing was traded:
interest and withdrawals came from new deposits. Credited balances
compound at the daily rate :math:`i`, so with deposits :math:`D_t` and
withdrawals :math:`W_t` the liabilities grow as

.. math::

   L_t = L_{t-1}(1 + i) + D_t - W_t, \qquad (1.01)^{365} \approx 38,

while the cash grows only by :math:`D_t - W_t`. A balance left for a year
is owed 38 times over, so the gap between what is owed and what is held
widens every day, and only ever-faster deposits can hide it. In January
2018 the Texas and North Carolina securities regulators ordered it to stop;
deposits dried up and the lending platform closed on 16 January. The SEC later charged its
founder and promoters with a fraud of about two billion dollars.

*Implementation:* :func:`blockchainkit.fraud.systems.ponzi.simulate_lending_ponzi`
and :func:`blockchainkit.fraud.systems.ponzi.referral_commissions`.
Withdrawals are a fixed fraction of balances each day and commissions are
paid at once, in the scheme's own currency rather than in a token whose
price it also propped up.

*References:* U.S. Securities and Exchange Commission, *SEC Charges Global
Crypto Lending Platform and Top Executives in $2 Billion Fraud*, press
release (1 September 2021); Texas State Securities Board,
emergency cease and desist order against BitConnect (4 January 2018).

.. minigallery:: ../../examples/fraud/schemes/plot_03_bitconnect_lending_ponzi.py

2019 -- Torres et al.: Honeypots That Trap Would-Be Thieves
-----------------------------------------------------------

A honeypot is a contract that holds ether and seems to leak it to anyone
who reads its source closely enough to spot a flaw. The reader sends ether
to exploit it, and the flaw is a trap: the ether stays in the contract,
where only its creator can reach it. Torres, Steichen and State found 690
honeypots and classified eight techniques. Four rest on EVM semantics or on
what the explorer shows. In *balance disorder*, the source seems to pay
anyone who sends at least the contract's balance :math:`b`; but by the time
the check runs, ``this.balance`` already includes the sender's
:math:`v`, so the condition becomes :math:`v \ge b + v`, which fails for
any bait :math:`b > 0`. A *hidden state update* changes the contract
through a call carrying no ether, which the explorer did not list, so the
reader judges stale state. A *hidden transfer* is pushed out of sight past
the right edge of the explorer's code view by whitespace. The *straw man
contract* is given, in its constructor, an address holding different code
from the source shown. The other four are quirks of Solidity:
*inheritance disorder*, an *uninitialised storage struct* overwriting slot
0, *type deduction overflow* of a ``var`` loop counter in ``uint8``, and
the *skipped empty string literal* of compilers before 0.4.12. Their tool,
HoneyBadger, finds them by symbolic execution of the bytecode.

*Implementation:* the contracts in :mod:`blockchainkit.fraud.systems.honeypots`.
Three of the EVM and explorer techniques are modelled directly:
:class:`~blockchainkit.fraud.systems.honeypots.MultiplicatorX3`,
:class:`~blockchainkit.fraud.systems.honeypots.GiftBox` with
:func:`~blockchainkit.fraud.systems.honeypots.explorer_view`, and
:class:`~blockchainkit.fraud.systems.honeypots.PrivateBank` with
:class:`~blockchainkit.fraud.systems.honeypots.TrapLog`. The Solidity quirks
are reproduced by their effect only, with no compiler or parser:
:class:`~blockchainkit.fraud.systems.honeypots.KingOfTheHill` keeps two
owner fields, :class:`~blockchainkit.fraud.systems.honeypots.GuessNumber`
writes to slots 0 and 1, :class:`~blockchainkit.fraud.systems.honeypots.ForTest`
counts modulo 256, and
:class:`~blockchainkit.fraud.systems.honeypots.DividendDistributor` passes
the shifted arguments. The hidden transfer, a matter of how the explorer
lays out text, is not shown.

*References:* C. F. Torres, M. Steichen and R. State, *The art of the scam:
Demystifying honeypots in Ethereum smart contracts*, USENIX Security 2019,
1591–1607.

.. minigallery::
   ../../examples/fraud/scam_contracts/plot_03_torres_evm_honeypots.py
   ../../examples/fraud/scam_contracts/plot_04_torres_solidity_quirks.py

2019 -- Xu and Livshits: The Anatomy of a Pump-and-Dump
-------------------------------------------------------

Telegram groups with tens of thousands of members announce a coin at a set
minute; members rush to buy, and the price jumps within seconds. The
organizers bought beforehand and sell into the rush. Xu and Livshits
studied 412 such pumps between June 2018 and February 2019, measured who
gained, and predicted which coin would be pumped from its market's
features. On a constant-product market with :math:`x` coins against
:math:`y` of the quote currency, a buyer paying :math:`\Delta y` gets
:math:`x\,\Delta y / (y + \Delta y)` coins, and each purchase raises the
price for the next. A fee-free pool neither gains nor loses on a round
trip: once every coin bought has been sold back, :math:`x` and :math:`y`
are where they started. The traders' profits therefore sum to zero, so
whoever buys early and sells first, above all the organizers, wins exactly
what the late buyers lose:

.. math::

   \pi_{\text{organizers}} + \sum_i \pi_i \approx 0 ,

approximately only because some late buyers are still holding coins.

The pump leaves a spike in both price and volume far above their recent
averages, which simple anomaly rules catch.

*Implementation:* :func:`blockchainkit.fraud.systems.manipulation.simulate_pump_and_dump`
on a fee-free constant-product market, and
:func:`blockchainkit.fraud.systems.manipulation.detect_pumps`, Kamps and
Kleinberg's anomaly rule on hourly closes. The pumps Xu and Livshits
studied ran on centralized exchanges' order books, and their prediction
model, a random forest, is not reproduced.

*References:* J. Xu and B. Livshits, *The anatomy of a cryptocurrency
pump-and-dump scheme*, USENIX Security 2019, 1609–1625; J. Kamps and B.
Kleinberg, *To the moon: defining and detecting cryptocurrency
pump-and-dumps*, Crime Science 7, 18 (2018).
`DOI <https://doi.org/10.1186/s40163-018-0093-5>`__.

.. minigallery:: ../../examples/fraud/manipulation/plot_02_pump_and_dump.py

2021 -- Rug Pulls and Hidden-Mint Tokens: the Squid Game Token
--------------------------------------------------------------

Anyone can issue a token and open a market for it on a decentralized
exchange, and many do so to take the buyers' money: by withdrawing the
liquidity they supplied, by minting themselves tokens through a function
with an innocent name, or by blocking everyone else from selling. Xia et
al. found that a large share of the tokens listed on Uniswap were scams. In
November 2021 a token named after the Squid Game series rose from a cent to
2,861 dollars in a week while its holders could not sell; its creators sold
and vanished, and the price fell to nothing in minutes. On a
constant-product market :math:`xy = k`, with :math:`x` tokens against
:math:`y` of the quote currency, selling :math:`\Delta x` tokens returns

.. math::

   \frac{y\,\Delta x}{x + \Delta x} \to y \quad \text{as } \Delta x \to \infty .

Blocking other sellers keeps the buyers' money in the pool, and a hidden
mint lets the creator make :math:`\Delta x` as large as it likes, so the
creator's sale takes almost the whole quote reserve. Neither trap is
visible when buying; it shows only on selling. The defence is therefore to
buy a little and sell it back on a fork of the chain, which costs nothing,
before buying for real.

*Implementation:* :class:`blockchainkit.fraud.systems.rug_pulls.SellBlockToken`,
:class:`blockchainkit.fraud.systems.rug_pulls.HiddenMintToken` and
:func:`blockchainkit.fraud.systems.rug_pulls.sell_test`, on
:class:`~blockchainkit.economics.systems.amm.ConstantProductPool` and
:meth:`~blockchainkit.contracts.systems.world.World.fork`. The Squid Game
token ran on BNB Chain with PancakeSwap; the pool here has no router and no
liquidity token.

*References:* P. Xia, H. Wang, B. Gao, W. Su, Z. Yu, X. Luo, C. Zhang, X.
Xiao and G. Xu, *Trade or trick? Detecting and characterizing scam tokens
on Uniswap decentralized exchange*, Proceedings of the ACM on Measurement
and Analysis of Computing Systems 5(3) (2021).

.. minigallery:: ../../examples/fraud/scam_contracts/plot_05_squid_game_rug_pull.py

2022 -- Von Wachter et al.: Wash Trading in NFT Markets
-------------------------------------------------------

A wash trade is a sale between parties who are really one. On NFT markets
it fakes a price history for a token or earns trading rewards: in early
2022 LooksRare paid its own token to traders in proportion to volume, and
most of that volume was washed. Von Wachter, Jensen, Regner and Ross looked
for the shape such trading leaves on a public ledger, a token passing
through a few accounts and returning to one that held it,

.. math::

   a_1 \to a_2 \to \cdots \to a_\ell \to a_1 ,

which changes nobody's holdings, only the volume. They found suspicious
activity in a few percent of the collections they studied, accounting for
a far larger share of their volume.

*Implementation:* :func:`blockchainkit.fraud.systems.wash_trading.find_wash_trades`
flags every trade on a cycle of at most ``max_length`` sales and groups
the accounts into rings as the components of a
:class:`~blockchainkit.network.systems.topology.Graph`;
:func:`blockchainkit.fraud.systems.wash_trading.simulate_nft_market`
supplies a market with a known ring. Von Wachter et al. used the strongly
connected components of each token's trade graph, together with common
funding of the accounts, which is not modelled.

*References:* V. von Wachter, J. R. Jensen, F. Regner and O. Ross, *NFT
wash trading: Quantifying suspicious behaviour in NFT markets*, Financial
Cryptography and Data Security workshops (2022); arXiv:2202.03866.

.. minigallery:: ../../examples/fraud/manipulation/plot_03_nft_wash_trading.py

2022 -- Approval ("Ice") Phishing on ERC-20 Allowances
------------------------------------------------------

An ERC-20 ``approve`` lets a spender move the owner's tokens later without
asking again, and exchanges ask once for an unlimited allowance to spare
their users a transaction per trade. In February 2022 Microsoft named *ice
phishing* the attack that exploits the habit: a fake airdrop or mint page
asks the victim to approve the attacker's contract, which can then call
``transferFrom`` to empty the wallet whenever the attacker likes, months
later if need be. No key is stolen. Each token can be taken up to the
total its spenders are allowed, but no more than the wallet holds, so what
a wallet stands to lose is

.. math::

   \sum_{\text{tokens}} \min\Big(\text{balance},\; \sum_{\text{spenders}} \text{allowance}\Big),

and revoking an approval, setting it to 0, removes that spender's share.

*Implementation:* :class:`blockchainkit.fraud.systems.phishing.Drainer`,
:func:`blockchainkit.fraud.systems.phishing.open_approvals`, which reads a
wallet's standing allowances from its ``Approval`` events, and
:func:`blockchainkit.fraud.systems.phishing.allowance_exposure`, on
:class:`~blockchainkit.contracts.systems.tokens.ERC20`. Signed ``permit``
approvals (EIP-2612), the commoner vector since, are not modelled.

*References:* Microsoft 365 Defender Research Team, *"Ice phishing" on the
blockchain*, Microsoft Security Blog (16 February 2022).
`URL <https://www.microsoft.com/en-us/security/blog/2022/02/16/ice-phishing-on-the-blockchain/>`__.

.. minigallery:: ../../examples/fraud/phishing/plot_01_ice_phishing_approvals.py

2022 -- FTX, Commingled Customer Funds, and Proof of Liabilities
----------------------------------------------------------------

In November 2022 FTX, one of the largest exchanges, could not meet a rush
of withdrawals and filed for bankruptcy. Its affiliated trading firm,
Alameda Research, had been exempt from the exchange's liquidation engine
and allowed a negative balance, and had spent billions of dollars of
customer deposits. The books still showed every customer's balance; the
coins were gone. With reserves :math:`R` and liabilities :math:`L`, a run
on an exchange whose reserve ratio is below one pays the first customers
in full until the reserves run out, and the rest nothing:

.. math::

   \rho = \frac{R}{L} < 1, \qquad \text{paid} = \min(R, L) = \rho L .

Solvency depends on :math:`R` and :math:`L` together. A proof of reserves
shows only :math:`R`, and FTX's reserves were real and large; the shortfall
appears only beside the liabilities. Weeks after the collapse, exchanges began publishing Merkle-sum
proofs of liabilities beside their reserves.

*Implementation:* :class:`blockchainkit.fraud.systems.custody.Custodian`,
whose operator may lend deposits to an affiliate up to a credit line, with
:func:`blockchainkit.fraud.systems.reserves.liability_tree` and
:func:`blockchainkit.fraud.systems.reserves.reserve_ratio`. Customers hold
ether only; FTX's books mixed dozens of assets and its own FTT token, which
Alameda used as collateral.

*References:* J. J. Ray III, *First Interim Report of John J. Ray III to
the Independent Directors on Control Failures at the FTX Exchanges*, In re
FTX Trading Ltd., No. 22-11068 (Bankr. D. Del., 9 April 2023).

.. minigallery:: ../../examples/fraud/solvency/plot_04_ftx_commingled_funds.py

2022-2023 -- Address Poisoning with Look-Alike Addresses
--------------------------------------------------------

An Ethereum address is 40 hexadecimal digits, and wallets show only the
first and last few. From late 2022, poisoners watched for payments, ground
out an address matching the ends of the payee's, and sent the payer a
worthless transfer from it, so that the look-alike sat in the payer's
history next to the real one; the next payment copied from there went to
the poisoner. Tsuchiya, Dong, Soska and Christin measured hundreds of
millions of such attempts on Ethereum and BNB Chain. The attack is cheap
because the poisoner need match only the digits users look at. Each random
candidate address matches :math:`k` chosen hex digits with probability
:math:`16^{-k}`, so the number of candidates to try is geometric with mean

.. math::

   \mathbb{E}[\text{trials}] = 16^{k},

about four billion for the eight digits a hurried user checks: seconds on a
graphics card.

*Implementation:* :func:`blockchainkit.fraud.systems.poisoning.grind_lookalike`
over hash-derived candidates
(:func:`blockchainkit.fraud.systems.poisoning.candidate_address`),
:func:`blockchainkit.fraud.systems.poisoning.looks_alike` and
:func:`blockchainkit.fraud.systems.poisoning.poisoning_suspects`. Candidates
are hashes rather than addresses derived from key pairs, and a few hex
digits replace the eight or more that real poisoners match.

*References:* T. Tsuchiya, J.-D. Dong, K. Soska and N. Christin,
*Blockchain address poisoning*, USENIX Security 2025; arXiv:2501.16681.

.. minigallery:: ../../examples/fraud/phishing/plot_02_address_poisoning.py
