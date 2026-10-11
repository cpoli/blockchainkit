Breakthroughs in Smart Contracts
================================

.. include:: /_generated/nav/contracts.rst

.. epigraph::

   "Program testing can be used to show the presence of bugs, but never to
   show their absence!"
   -- Edsger W. Dijkstra, *Notes on Structured Programming*, 1970

:doc:`vm_breakthroughs` shows how contracts *execute*: the machine, gas,
atomic failure and bytecode verification. This chronology follows how they
are *engineered*: the standards that let contracts work together, the
mistakes behind the field's largest losses, and the methods that check a
contract before it holds money. Three contract entries stay on the execution
page: Szabo's vending machine, the DAO's reentrancy and the BeautyChain
overflow; the Oyente entry below finds that overflow again, in bytecode.

Everything here runs on :class:`~blockchainkit.contracts.systems.world.World`,
a model of the EVM's call semantics in which contracts are short Python
classes. :doc:`/protocol` lists exactly where it differs from Ethereum.

.. contents:: Timeline
   :local:
   :depth: 1

1967-1969 -- Floyd and Hoare: Proving Programs Correct with Assertions
----------------------------------------------------------------------

Floyd attached an assertion to every edge of a flowchart and required each
instruction to carry a true assertion to a true one, so that the assertion
at the exit described what the program computes. Hoare turned the method
into a logic of triples: :math:`\{P\}\,S\,\{Q\}` states that if P holds
before S and S terminates, Q holds after. The assignment axiom runs
backwards,

.. math::

   \{Q[e/x]\}\; x := e\; \{Q\},

so a postcondition can be pushed through the code to a condition on the
inputs, which Dijkstra later called the weakest precondition. Proving a
program correct then means proving that its precondition implies it. Formal
verification of contracts, from the K framework's EVM semantics to
Certora's prover, rests on this idea.

*Implementation:* :func:`blockchainkit.contracts.systems.hoare.weakest_precondition`
computes :math:`\mathrm{wp}` for straight-line code with branches, and
:func:`blockchainkit.contracts.systems.hoare.check_triple` checks a triple on
every state of a finite domain, optionally with wrapping words. There are no
loops, so no loop invariants, and no theorem prover: the check is
exhaustive over the domain given, not a proof for all inputs.

*References:* R. W. Floyd, *Assigning meanings to programs*, Proc. Symposia
in Applied Mathematics 19, 19–32 (1967); C. A. R. Hoare, *An axiomatic basis
for computer programming*, Communications of the ACM 12(10), 576–580 (1969).
`DOI <https://doi.org/10.1145/363235.363259>`__.

.. minigallery:: ../../examples/contracts/verification/plot_01_floyd_hoare.py

1976 -- King's Symbolic Execution
---------------------------------

Testing runs a program on chosen inputs; King ran it on *symbols*. Each
variable holds an expression over the inputs, and each branch on such an
expression forks the execution. A path then carries its *path condition*,
the conjunction of the branch decisions it took,

.. math::

   \mathrm{pc} = c_1 \wedge \neg c_2 \wedge \dots \wedge c_k,

and every input satisfying it follows exactly that path. Solving the
condition of a path that reaches a failed assertion produces an input that
triggers the bug. The number of paths can grow exponentially with the
number of branches, which is why symbolic executors bound their search.

*Implementation:* :func:`blockchainkit.contracts.systems.symbolic.symbolic_execute`
explores every path of the same small language, and
:func:`blockchainkit.contracts.systems.symbolic.solve` searches for inputs.
King used a theorem prover, and modern tools use SMT solvers; this solver
only tries boundary values (0, 1, the program's constants and their
neighbors), so finding nothing is not a proof.

*References:* J. C. King, *Symbolic execution and program testing*,
Communications of the ACM 19(7), 385–394 (1976).
`DOI <https://doi.org/10.1145/360248.360252>`__.

.. minigallery:: ../../examples/contracts/verification/plot_02_symbolic_execution.py

1986 -- Meyer's Design by Contract
----------------------------------

Meyer's Eiffel made a routine's specification part of its code. The caller
must establish the *precondition*, the routine then guarantees the
*postcondition*, and every public routine preserves the class *invariant*:

.. math::

   \{\mathrm{pre}_r \wedge \mathrm{INV}\}\; r\; \{\mathrm{post}_r \wedge \mathrm{INV}\}.

Checked at run time, a violated clause points at the guilty party: a failed
precondition is the caller's bug, a failed postcondition or invariant the
routine's. Solidity's ``require`` (an input check that reverts) and
``assert`` (an internal invariant) carry the same split, and token
invariants such as "the balances sum to the supply" are the properties
every later tool checks.

*Implementation:* the decorators
:func:`blockchainkit.contracts.systems.design_by_contract.requires` and
:func:`blockchainkit.contracts.systems.design_by_contract.ensures`, and
:meth:`blockchainkit.contracts.systems.world.Contract.invariant`, which the
world checks after every call; a violation reverts. Checks cost no gas here,
whereas on chain every check is paid for.

*References:* B. Meyer, *Design by contract*, Technical Report TR-EI-12/CO,
Interactive Software Engineering (1986); B. Meyer, *Applying "design by
contract"*, IEEE Computer 25(10), 40–51 (1992).
`DOI <https://doi.org/10.1109/2.161279>`__.

.. minigallery:: ../../examples/contracts/verification/plot_03_design_by_contract.py

1996 -- Grigg's Ricardian Contracts
-----------------------------------

Ian Grigg designed the Ricardian contract to issue bonds and currencies on
the Ricardo payment system. A single document is at once a legal contract
that a person can read and a set of parameters that a program can parse;
the issuer signs it, and its hash names the instrument:

.. math::

   \mathrm{id} = H(\mathrm{prose} \,\|\, \mathrm{parameters}).

Every payment cites the identifier, so the terms of a payment are never in
doubt, and editing one word of the prose creates a different instrument.
The idea of binding code to legal text by hash recurs in token terms, in
the hashes that document registries record, and in the debate over whether
code alone can be the contract.

*Implementation:* :func:`blockchainkit.contracts.systems.ricardian.ricardian_contract`
signs the prose and parameters with this package's Schnorr signatures, and
:class:`blockchainkit.contracts.systems.ricardian.RicardianToken` accepts
only payments that cite the digest. Grigg's documents were OpenPGP-signed
text files with a structured header, not JSON.

*References:* I. Grigg, *The Ricardian contract*, Proc. First IEEE
International Workshop on Electronic Contracting, 25–31 (2004).
`DOI <https://doi.org/10.1109/WEC.2004.1319505>`__.

.. minigallery:: ../../examples/contracts/foundations/plot_01_ricardian_contracts.py

1997-2006 -- Miller's E Language and Capability-Based Security
--------------------------------------------------------------

In an object-capability system, the only way to act on an object is to hold
a reference to it, and references are only created, received, or held from
the start: there is no ambient authority to look up. Mark Miller's E
language built distributed programs and money on this rule. With its mint
and purses, paying means handing over a purse holding exactly the payment,
and the payee can reach nothing else.

Ambient authority is what makes a *confused deputy* (Hardy, 1988): a program
that uses authority it holds for one party on behalf of another. Ethereum's
``tx.origin`` is ambient. A wallet that trusts it pays out whenever its
owner's transaction passes through, so an owner lured into calling a
malicious contract empties the wallet:

.. math::

   \texttt{tx.origin} = \text{owner} \;\not\Rightarrow\; \text{the owner intended this call}.

*Implementation:* :class:`blockchainkit.contracts.systems.capabilities.Mint`
and :class:`blockchainkit.contracts.systems.capabilities.Purse` in plain
Python, whose attributes cannot be hidden the way E hides them; and the
contracts :class:`~blockchainkit.contracts.systems.capabilities.OriginWallet`,
:class:`~blockchainkit.contracts.systems.capabilities.SenderWallet` and
:class:`~blockchainkit.contracts.systems.capabilities.AirdropPhisher`.

*References:* M. S. Miller, C. Morningstar and B. Frantz, *Capability-based
financial instruments*, Financial Cryptography 2000, LNCS 1962, 349–378
(2001). `DOI <https://doi.org/10.1007/3-540-45472-1_24>`__; M. S. Miller,
*Robust composition: towards a unified approach to access control and
concurrency control*, PhD thesis, Johns Hopkins University (2006); N. Hardy,
*The confused deputy*, ACM SIGOPS Operating Systems Review 22(4), 36–38
(1988). `DOI <https://doi.org/10.1145/54289.871709>`__.

.. minigallery:: ../../examples/contracts/foundations/plot_02_capabilities.py

2015 -- ERC-20 Tokens and the Approve/TransferFrom Race
-------------------------------------------------------

ERC-20 gave fungible tokens one interface, so that any wallet or exchange
could hold any token: ``transfer``, ``balanceOf``, and a two-step
delegation in which ``approve(spender, n)`` lets the spender move up to n
tokens with ``transferFrom``. Thousands of tokens were issued on it.

``approve`` overwrites the allowance. When an owner lowers an allowance
from N to M, the spender can see the pending transaction and get a
``transferFrom`` of N mined first, then spend the fresh M as well:

.. math::

   \text{spent} = N + M \quad\text{instead of at most}\quad \max(N, M).

Vladimirov and Khovratovich described the attack in 2016. The common
mitigations change the allowance relative to what is left
(``increaseAllowance`` and ``decreaseAllowance``) or require it to be zero
before a new value is set.

*Implementation:* :class:`blockchainkit.contracts.systems.tokens.ERC20`,
with ``decrease_allowance`` reverting below zero. Function names follow
Python style, functions are matched by name rather than by 4-byte selector,
and transaction order is chosen by the experiment rather than by a mempool
and fee auction.

*References:* F. Vogelsteller and V. Buterin, *EIP-20: Token standard*
(2015). `Specification <https://eips.ethereum.org/EIPS/eip-20>`__;
M. Vladimirov and D. Khovratovich, *ERC20 API: an attack vector on
approve/transferFrom methods* (2016).

.. minigallery:: ../../examples/contracts/tokens/plot_01_erc20_approve_race.py

2016 -- Unchecked Send and the Pull-Payment Pattern: King of the Ether
----------------------------------------------------------------------

*King of the Ether* sold a throne: each claimant paid more than the current
price, and the deposed king received the payment less a fee. The contract
paid with ``send``, which forwards a stipend of only 2,300 gas and returns
False on failure instead of reverting. In February 2016 kings using Mist's
contract wallets, whose code for receiving ether needed more gas than that,
were never paid: the contract ignored the False and kept their money.

Checking the result moves the problem: a king who refuses every payment
then can never be deposed, since crowning anyone requires paying him. The
lasting fix is the *pull-payment* pattern, in which the contract records
what each recipient is owed and each withdraws it in a transaction of its
own,

.. math::

   \mathrm{owed}[k] \mathrel{+}= \text{payment}, \qquad
   \texttt{withdraw}(): \text{send } \mathrm{owed}[\texttt{msg.sender}],

so a failing recipient harms only itself.

*Implementation:* :class:`blockchainkit.contracts.systems.payments.KingOfTheEther`,
:class:`~blockchainkit.contracts.systems.payments.CheckedKingOfTheEther` and
:class:`~blockchainkit.contracts.systems.payments.PullKingOfTheEther`, with
:class:`~blockchainkit.contracts.systems.payments.ContractWallet` (whose
``receive`` writes storage) and
:class:`~blockchainkit.contracts.systems.payments.Usurper` (which refuses
payment). :meth:`~blockchainkit.contracts.systems.world.Contract.send`
gives the 2,300-gas stipend; the rest of the gas schedule is a teaching
approximation.

*References:* Kieran Elby, *King of the Ether Throne: post mortem
investigation* (February 2016); N. Atzei, M. Bartoletti and T. Cimoli,
*A survey of attacks on Ethereum smart contracts (SoK)*, POST 2017, LNCS
10204, 164–186 (2017). `DOI <https://doi.org/10.1007/978-3-662-54455-6_8>`__.

.. minigallery:: ../../examples/contracts/payments/plot_01_king_of_the_ether.py

2016 -- Unbounded Loops and Gas Denial of Service: GovernMental
---------------------------------------------------------------

GovernMental was a Ponzi game that paid its jackpot to the last investor
after 12 hours without a new one, then reset itself by clearing its array
of creditors, one storage write per entry. In April 2016 the array had
grown so long that clearing it needed more gas than a block allowed, so the
payout could not run and its jackpot of about 1,100 ether was stuck. With
:math:`n` creditors the payout fails once

.. math::

   G_{\text{base}} + n\,G_{\text{write}} > G_{\text{block}}.

Any loop over a collection that users can grow is a denial of service in
waiting; the cures are a constant-cost reset, as here, or letting each user
process their own entry.

*Implementation:* :class:`blockchainkit.contracts.systems.payments.GovernMental`,
whose ``lazy_reset`` option starts a new round instead of deleting entries.
The experiment uses the 2016 block gas limit of 4,712,388 and this model's
5,000 gas per storage write; the real contract also paid investors and the
operator, which is not modeled.

*References:* N. Atzei, M. Bartoletti and T. Cimoli, *A survey of attacks on
Ethereum smart contracts (SoK)*, POST 2017, LNCS 10204, 164–186 (2017).
`DOI <https://doi.org/10.1007/978-3-662-54455-6_8>`__.

.. minigallery:: ../../examples/contracts/payments/plot_02_governmental_gas.py

2016 -- Oyente: Symbolic Execution Finds Contract Bugs
------------------------------------------------------

Luu, Chu, Olickel, Saxena and Hobor built Oyente, a symbolic executor for
EVM bytecode backed by the Z3 solver, and ran it on 19,366 contracts then on
Ethereum. It flagged 8,833 as potentially vulnerable, among them the DAO,
to transaction-ordering dependence, timestamp dependence, mishandled
exceptions and reentrancy. Analyzing bytecode means analyzing what actually
runs, whatever the source said; the same paper proposed semantic changes to
Ethereum to rule some bug classes out.

A bug becomes a condition on the final state of a path. For a token
transfer from slot 1 to slot 2, "tokens created from nothing" is

.. math::

   \mathrm{slot}_1' \ge s_1 \;\wedge\; \mathrm{slot}_2' > s_2,

and a solution of the path condition together with it is an attack.

*Implementation:* :func:`blockchainkit.contracts.systems.symbolic.symbolic_bytecode`
executes programs of :mod:`blockchainkit.vm` symbolically, and the
experiment finds BeautyChain's :math:`2^{255}` in
:func:`blockchainkit.vm.systems.programs.batch_transfer`. Oyente did not
check integer overflow (Osiris added it in 2018); its four bug classes are
not modeled.

*References:* L. Luu, D.-H. Chu, H. Olickel, P. Saxena and A. Hobor,
*Making smart contracts smarter*, Proc. ACM CCS 2016, 254–269 (2016).
`DOI <https://doi.org/10.1145/2976749.2978309>`__.

.. minigallery:: ../../examples/contracts/verification/plot_04_oyente.py

2016 -- Commit-Reveal Schemes and On-Chain Randomness
-----------------------------------------------------

Every node must compute the same result, so a contract has no secret
randomness. Lotteries that drew from the previous block's hash were beaten
by contracts that read the same hash in the same block and played only to
win, and a miner could discard a block whose hash it disliked.

A commit-reveal scheme, as in RANDAO (2016), splits the draw in two phases.
Each participant first publishes :math:`c_i = H(\text{participant}, s_i,
r_i)` for a secret :math:`s_i` and a salt :math:`r_i`, then reveals; the
result combines every secret,

.. math::

   R = s_1 \oplus s_2 \oplus \dots \oplus s_n,

so nobody can choose a secret after seeing the others. The last revealer
still sees R first and may withhold, which penalties and, later,
verifiable delay functions address.

*Implementation:* :class:`blockchainkit.contracts.systems.randomness.BlockhashLottery`
and :class:`~blockchainkit.contracts.systems.randomness.LotteryPredictor`,
and :class:`~blockchainkit.contracts.systems.randomness.CommitRevealLottery`
with :func:`~blockchainkit.contracts.systems.randomness.commitment`. Block
hashes come from a seeded hash rather than from mining, and the lottery
applies no penalty to a player who does not reveal.

*References:* J. Bonneau, J. Clark and S. Goldfeder, *On Bitcoin as a public
randomness source*, IACR Cryptology ePrint Archive 2015/1015 (2015);
`RANDAO <https://github.com/randao/randao>`__ (2016).

.. minigallery:: ../../examples/contracts/payments/plot_03_commit_reveal.py

2017 -- The Parity Multisig Hack: An Unprotected Initializer
------------------------------------------------------------

Parity's multisig wallets kept their logic in a shared library. Each wallet
was a stub holding the ether and storage, forwarding unknown calls to the
library with ``DELEGATECALL``, which runs the library's code on the
wallet's own storage. The library's ``initWallet`` set the owners and the
number of approvals needed, and nothing stopped a second call. On 19 July
2017 an attacker called it through three wallets, became each one's sole
owner, and withdrew 153,037 ether:

.. math::

   \text{owners} \leftarrow \text{the last caller of } \texttt{initWallet}.

A white-hat group then drained other vulnerable wallets to protect them.

*Implementation:* :class:`blockchainkit.contracts.systems.wallets.WalletLibrary`
and :class:`~blockchainkit.contracts.systems.wallets.Wallet` are m-of-n
wallets approved by this package's Schnorr signatures
(:func:`~blockchainkit.contracts.systems.wallets.approve_action`); Parity's
owners confirmed by sending transactions, and its library also managed daily
limits.

*References:* Parity Technologies, *The multi-sig hack: a postmortem*
(20 July 2017); S. Palladino, *The Parity wallet hack explained*,
OpenZeppelin (2017).

.. minigallery:: ../../examples/contracts/wallets/plot_01_parity_multisig_hack.py

2017 -- The Parity Library Freeze: Selfdestruct behind DELEGATECALL
-------------------------------------------------------------------

The fixed library let ``initWallet`` run only on uninitialized storage, but
the library was itself a contract with storage, and nobody had initialized
it. On 6 November 2017 a user called ``initWallet`` on the library directly,
became its owner, and called ``kill``, which executed ``selfdestruct``. A
``DELEGATECALL`` to an address without code does not fail; it runs nothing
and succeeds. Every wallet built on the library kept its ether and lost
every function that could move it, freezing 513,774 ether:

.. math::

   \texttt{DELEGATECALL}(\text{empty account}) \;\Rightarrow\; \text{success, no effect}.

Code reached by ``DELEGATECALL`` is part of every caller, so libraries are
now written without state and without ``selfdestruct``, and EIP-6780 (2024)
has since restricted ``selfdestruct`` itself.

*Implementation:* :class:`blockchainkit.contracts.systems.wallets.PatchedWalletLibrary`
on the same wallet stub. ``selfdestruct`` here removes the code at once
rather than at the end of the transaction.

*References:* Parity Technologies, *A postmortem on the Parity multi-sig
library self-destruct* (15 November 2017).

.. minigallery:: ../../examples/contracts/wallets/plot_02_parity_library_freeze.py

2018 -- ERC-721 Non-Fungible Tokens
-----------------------------------

ERC-721 gave each token an identity: a map from token ids to owners rather
than a balance per owner,

.. math::

   \mathrm{owner}: \mathrm{id} \mapsto \mathrm{address}, \qquad
   \mathrm{balance}(a) = |\{\mathrm{id} : \mathrm{owner}(\mathrm{id}) = a\}|,

so that collectibles, game items and titles could be held and traded like
coins; CryptoKitties had shown the demand in late 2017. Tokens sent to a
contract that cannot move them are lost, so ``safeTransferFrom`` calls
``onERC721Received`` on a contract recipient and reverts unless it answers
with the agreed value. That callback is itself an external call in the
middle of a transfer, and several NFT mints were later drained through it
by reentrancy.

*Implementation:* :class:`blockchainkit.contracts.systems.tokens.ERC721`
and :class:`~blockchainkit.contracts.systems.tokens.NFTVault`. There is no
metadata or enumeration extension, no operator approval for all tokens,
and no ERC-165 interface detection.

*References:* W. Entriken, D. Shirley, J. Evans and N. Sachs, *EIP-721:
Non-fungible token standard* (2018).
`Specification <https://eips.ethereum.org/EIPS/eip-721>`__.

.. minigallery:: ../../examples/contracts/tokens/plot_02_erc721_safe_transfers.py

2018 -- Upgradeable Proxies and Storage Collisions
--------------------------------------------------

Deployed code cannot change, so upgradeable contracts split into a *proxy*
that holds the address and storage and forwards every call by
``DELEGATECALL`` to an *implementation* that holds the code; upgrading
re-points the proxy. EIP-897 (2018) standardized such proxies. Both
contracts then read one storage through two layouts, so a proxy field and
an implementation field in the same slot overwrite each other: a *storage
collision*, behind the 2022 Audius hack among others. EIP-1967 moves the
proxy's fields to slots derived from a hash,

.. math::

   \mathrm{slot} = H(\texttt{"eip1967.proxy.implementation"}) - 1,

and new implementation versions must keep old fields in place and only
append.

*Implementation:* :class:`blockchainkit.contracts.systems.proxies.NaiveProxy`,
:class:`~blockchainkit.contracts.systems.proxies.EIP1967Proxy`, and the
implementations :class:`~blockchainkit.contracts.systems.proxies.BoxV1`,
:class:`~blockchainkit.contracts.systems.proxies.BoxV2` and
:class:`~blockchainkit.contracts.systems.proxies.BoxV2Reordered`. Slots are
numbered by field position, mappings use tuple keys rather than Keccak
hashes, and the hashed slots use SHA-256.

*References:* J. Izquierdo and M. Araoz, *EIP-897: DelegateProxy* (2018).
`Specification <https://eips.ethereum.org/EIPS/eip-897>`__; S. Palladino,
*EIP-1967: Proxy storage slots* (2019).
`Specification <https://eips.ethereum.org/EIPS/eip-1967>`__.

.. minigallery:: ../../examples/contracts/upgrades/plot_01_proxy_storage_collision.py

2019 -- CREATE2 and Counterfactual Addresses
--------------------------------------------

``CREATE`` derives a new contract's address from its deployer and the
deployer's nonce, so the address depends on the deployer's history.
EIP-1014, activated in the Constantinople upgrade of February 2019, added
``CREATE2``:

.. math::

   \mathrm{address} = H(\mathtt{0xff} \,\|\, \mathrm{deployer} \,\|\,
   \mathrm{salt} \,\|\, H(\mathrm{init\ code}))_{[12:]}.

The address depends only on the deployer, a salt and the code, so it is
known before deployment, and funds can be sent to a contract that does not
exist yet: it is *counterfactual*. State channels deploy their dispute
contracts only when a dispute happens, and smart-contract wallets are
deployed on first use at the address their owner has already been using.

*Implementation:* :func:`blockchainkit.contracts.systems.world.create2_address`,
the ``salt`` of :meth:`~blockchainkit.contracts.systems.world.World.deploy`
and :meth:`~blockchainkit.contracts.systems.world.Contract.create`, and
:class:`blockchainkit.contracts.systems.factory.Factory`. The hash is
SHA-256 with a domain tag, and the "init code" is the contract class and its
constructor arguments.

*References:* V. Buterin, *EIP-1014: Skinny CREATE2* (2018).
`Specification <https://eips.ethereum.org/EIPS/eip-1014>`__.

.. minigallery:: ../../examples/contracts/upgrades/plot_02_create2_counterfactual.py

2020 -- Property-Based Fuzzing of Contracts: Echidna
----------------------------------------------------

QuickCheck (Claessen and Hughes, 2000) tested a function by checking a
stated property on many random inputs and shrinking any failure to a small
one. Echidna, from Trail of Bits, applies this to contracts: the author
writes properties such as

.. math::

   \forall\ \text{transaction sequences}: \quad \sum_a \mathrm{balance}(a) = \mathrm{supply},

and the fuzzer sends random sequences of transactions, with random senders
and arguments, checking the properties after each one. Fuzzing needs no
model of the code and never reports a false bug, but finds only what random
sequences reach; it is now run on most audited contracts, alongside Foundry
and Medusa.

*Implementation:* :func:`blockchainkit.contracts.systems.fuzzing.fuzz` and
:func:`~blockchainkit.contracts.systems.fuzzing.shrink`. Arguments are drawn
uniformly from given candidates; Echidna also uses coverage feedback and
values mined from the bytecode to guide the search.

*References:* G. Grieco, W. Song, A. Cygan, J. Feist and A. Groce, *Echidna:
effective, usable, and fast fuzzing for smart contracts*, Proc. ISSTA 2020,
557–560 (2020). `DOI <https://doi.org/10.1145/3395363.3404366>`__;
K. Claessen and J. Hughes, *QuickCheck: a lightweight tool for random
testing of Haskell programs*, Proc. ICFP 2000, 268–279 (2000).
`DOI <https://doi.org/10.1145/351240.351266>`__.

.. minigallery:: ../../examples/contracts/verification/plot_05_echidna_fuzzing.py

2022 -- Governance Attacks: Beanstalk's Flash-Loan Vote
-------------------------------------------------------

A flash loan lends any amount without collateral on one condition: repay
within the same transaction, or the whole transaction reverts. For one
transaction anyone can be as rich as the lender. Beanstalk let holders pass
a proposal at once by ``emergencyCommit`` with two thirds of the voting
power, a day after it was proposed. On 17 April 2022 an attacker who had
proposed sending the treasury to itself the day before borrowed about a
billion dollars in flash loans, turned them into voting power, voted,
committed, and repaid, keeping about 80 million dollars. The vote held
because, within that single transaction,

.. math::

   \frac{\text{borrowed} + \text{own}}{\text{supply}} \ge \frac{2}{3}.

Counting votes at a *snapshot*, the balances at the block before the
proposal, defeats it: no flash loan can change the past.

*Implementation:* :class:`blockchainkit.contracts.systems.governance.Governance`
with ``snapshot`` voting over
:class:`~blockchainkit.contracts.systems.governance.VotesToken`'s
checkpoints, :class:`~blockchainkit.contracts.systems.governance.FlashLender`
and :class:`~blockchainkit.contracts.systems.governance.GovernanceAttacker`.
The attacker borrows the governance token directly; the real attack
borrowed stablecoins and converted them into Beanstalk's voting power
through liquidity pools.

*References:* K. Qin, L. Zhou, B. Livshits and A. Gervais, *Attacking the
DeFi ecosystem with flash loans for fun and profit*, Financial Cryptography
2021, LNCS 12674, 3–32 (2021).
`DOI <https://doi.org/10.1007/978-3-662-64322-8_1>`__; Beanstalk Farms,
*BIP-18 governance exploit post-mortem* (April 2022).

.. minigallery:: ../../examples/contracts/governance/plot_01_beanstalk_flash_loan.py
