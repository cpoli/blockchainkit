Breakthroughs in Smart Contracts
================================

.. include:: /_generated/nav/contracts.rst

.. epigraph::

   "Program testing can be used to show the presence of bugs, but never to
   show their absence!"
   -- Edsger W. Dijkstra, *Notes on Structured Programming*, 1970

A *blockchain* is a shared record, like a Python list of blocks of
transactions. Many computers keep copies of it in step, without trusting
each other. *Ethereum* is a blockchain that stores programs as well as
payments. A *smart contract* is one of those programs. Think of it as a
Python object that lives on the blockchain. It has attributes (its
*storage*) and public methods. It can also hold money. Anyone can call its
methods, and every computer in the network runs the call and gets the same
result. Once deployed, its code cannot be changed.

The page uses a few terms throughout:

- An *account* is identified by an *address*, a 20-byte number. People
  have accounts, and so do contracts.
- *Ether* is Ethereum's currency.
- A *transaction* is a signed request from a person's account: "send this
  ether" or "call this method with these arguments". One transaction can
  set off a chain of calls from contract to contract.
- *Gas* measures computing work. Every instruction costs a fixed amount of
  gas, and the sender of the transaction pays for it in ether. A transaction that runs out of
  gas fails.
- A call that fails *reverts*. All its changes are undone, as if it had
  never run, like a database transaction that is rolled back. This is
  called *atomic failure*: a call either completes fully or has no effect.
- The *EVM* (Ethereum Virtual Machine) is the machine that runs contracts.
  Contracts are written in a language such as Solidity, then compiled to
  *bytecode*, a list of simple machine instructions, like Python's own
  bytecode.
- A *hash function* :math:`H` is like Python's ``hash()``, but built so that
  nobody can find two inputs with the same output. Its output, the *hash*
  or *digest*, works as a short fingerprint of any data. :math:`\|` joins
  two byte strings (``a + b`` in Python).
- A *token* is a balance kept by a contract rather than by Ethereum itself:
  in effect a dict ``balances = {address: amount}`` plus methods to move
  amounts between keys.
- *Formal verification* means proving, with logic, that a program meets
  its specification for every input, not just the inputs that were tested.

:doc:`vm_breakthroughs` shows how contracts *execute*: the machine, gas,
atomic failure and bytecode verification. This chronology follows how they
are *engineered*: the standards that let contracts work together, the
mistakes behind the field's largest losses, and the methods that check a
contract before it holds money. Three contract entries stay on the execution
page:

- Szabo's vending machine, his example of a contract built into a
  machine.
- The DAO's *reentrancy*: a contract was called back before it had updated
  its records.
- The BeautyChain *overflow*: a number grew too big for its 256-bit slot and
  wrapped round to a small one, as with ``% 2**256``.

The Oyente entry below finds that overflow again, in bytecode.

Everything here runs on :class:`~blockchainkit.contracts.systems.world.World`,
a model of the EVM's call semantics in which contracts are short Python
classes. *Call semantics* means the rules for what happens when one
contract calls another: who pays, whose storage changes, and what is undone
on failure. :doc:`/protocol` lists exactly where it differs from Ethereum.

.. contents:: Timeline
   :local:
   :depth: 1

1967-1969 -- Floyd and Hoare: Proving Programs Correct with Assertions
----------------------------------------------------------------------

Tests check a program on some inputs. Floyd and Hoare wanted to prove that
a program is correct on *all* inputs.

The idea is to attach an *assertion* to each point in the program. An
assertion is a true-or-false statement about the variables, like a Python
``assert x > 0``. Floyd drew programs as flowcharts and put an assertion on
every arrow. He then required each instruction to turn a true assertion
before it into a true assertion after it. If every step does that, the
assertion at the exit describes what the program computes.

Hoare turned the method into a logic of *triples*. The triple
:math:`\{P\}\,S\,\{Q\}` says: if the condition P holds before the code S,
and S finishes, then the condition Q holds after it.

- P is the *precondition*: what must be true before.
- Q is the *postcondition*: what is then guaranteed after.
- The triple says nothing about whether S finishes at all. A program
  stuck in an endless loop satisfies every triple. Proving that it stops is
  a separate task.

Hoare's rule for an assignment ``x = e`` works backwards from the end:

.. math::

   \{Q[e/x]\}\; x := e\; \{Q\},

Here :math:`Q[e/x]` means "Q with every x replaced by e". In words: Q holds
after the assignment exactly when Q, with e written in place of x, held
before it. For example, take ``x = y + 1`` and the postcondition
``x > 0``. The precondition is ``y + 1 > 0``.

Applying this rule statement by statement, from the last to the first,
pushes a postcondition back through the code. The result is a condition on
the inputs alone. Dijkstra later called it the *weakest precondition*
:math:`\mathrm{wp}`: the least demanding condition on the inputs that still
guarantees Q. To prove a triple :math:`\{P\}\,S\,\{Q\}`, it then suffices to
show that P implies :math:`\mathrm{wp}(S, Q)`. Formal verification of
contracts rests on this idea. Two examples are the K framework, which
describes the EVM's rules in logic, and Certora's prover, a commercial
contract checker.

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

A test runs a program on chosen inputs, and may miss the one input that
triggers a bug. James King wanted a way to find that input.

His idea was to run the program on *symbols* instead of numbers. Picture
calling ``f(a, b)`` where ``a`` and ``b`` stay unknown. Each variable then
holds an expression over the inputs, such as ``2*a + 1``, not a value. This
is *symbolic execution*.

#. Start with each input as a named symbol.
#. Run each statement on expressions: after ``y = 2*a + 1`` the variable
   ``y`` holds the expression ``2*a + 1``.
#. At a branch such as ``if y > b:`` the outcome is unknown, so fork. One
   copy assumes ``2*a + 1 > b``. The other assumes it is false.
#. Each copy records the branch decisions it has made. Their combination is
   its *path condition*.
#. When a copy reaches a failed ``assert``, search for inputs that make its
   path condition true. Those inputs trigger the bug.

The path condition is an "and" of the decisions along the path:

.. math::

   \mathrm{pc} = c_1 \wedge \neg c_2 \wedge \dots \wedge c_k,

Here :math:`\wedge` means "and" and :math:`\neg` means "not". This path
took branch 1, did not take branch 2, and so on. Every input that satisfies
pc follows exactly this path.

Its limits:

- The number of paths can grow exponentially with the number of branches.
  Forty ``if`` statements in a row give up to :math:`2^{40} \approx 10^{12}`
  paths. Symbolic executors therefore bound their search.
- Step 5 needs a *solver*: a program that finds values making a formula
  true, or shows that none exist. King used a theorem prover. Modern tools
  use *SMT solvers* such as Z3, which handle formulas over integers, bit
  strings and arrays.

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

When a function goes wrong, is the bug in the function or in its caller?
Bertrand Meyer answered this by writing the specification into the code
itself, in his language Eiffel.

A *routine* (a method, in Python terms) gets three kinds of check:

- The *precondition* is what the caller must make true before calling, for
  example "the amount is positive".
- The *postcondition* is what the routine then guarantees on return.
- The class *invariant* is a condition on the object's attributes that
  every public routine must leave true. For a token, an example is "the
  balances sum to the total supply".

Together they form a Hoare triple for each routine r:

.. math::

   \{\mathrm{pre}_r \wedge \mathrm{INV}\}\; r\; \{\mathrm{post}_r \wedge \mathrm{INV}\}.

In words: if the caller meets the precondition and the invariant holds,
then r ends with its postcondition and the invariant both true.

When the checks run while the program runs, a failed check names the
guilty party:

- A failed precondition is the caller's bug.
- A failed postcondition or invariant is the routine's bug.

Solidity has the same split. ``require`` checks inputs and reverts if they
are bad. ``assert`` checks an internal invariant that should never fail.
Token invariants such as "the balances sum to the supply" are the
properties that every later tool on this page checks.

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

A digital payment should never leave doubt about which legal terms it
falls under. Ian Grigg designed the *Ricardian contract* to issue bonds
and currencies on the Ricardo payment system, so that every payment named
its terms exactly. A *bond* is a promise to repay borrowed money. The
*issuer* is whoever makes that promise.

The idea is a single document that is two things at once:

- a legal contract that a person can read (the *prose*);
- a set of *parameters*, such as the currency and interest rate, that a
  program can parse.

It works in three steps:

#. The issuer writes the document and *signs* it. A *digital signature* is
   a value that only the holder of a secret key can produce, but that
   anyone can check against the matching public key.
#. The hash of the document becomes the name of the new *instrument* (the
   bond or currency it creates).
#. Every payment cites that name.

.. math::

   \mathrm{id} = H(\mathrm{prose} \,\|\, \mathrm{parameters}).

In words: the instrument's identifier is the fingerprint of its prose
joined to its parameters.

Why it works:

- Every payment cites the identifier, so the terms of a payment are never
  in doubt.
- Changing one word of the prose changes the hash, so it creates a
  different instrument. Nobody can quietly edit the terms.

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

Programs from strangers must be able to work together without being able
to harm each other. Mark Miller's E language built distributed programs,
and money, on one rule.

That rule is *object capabilities*. The only way to act on an object is to
hold a reference to it, as in Python, where you can call ``obj.pay()`` only
if some variable points at ``obj``. A program gets a reference in only
three ways:

- it created the object;
- someone passed the reference to it;
- it held the reference from the start.

There is no *ambient authority*: no global variable, like ``os.environ``,
or "current user", that any code can look up to gain power.

E's money shows the rule at work. A *mint* creates a currency, and a
*purse* holds an amount of it.

#. The payer asks the mint for a new, empty purse.
#. The payer moves exactly the payment from their own purse into it.
#. The payer hands the new purse to the payee.
#. The payee moves its contents into their own purse.

The payee receives a reference to that one purse and nothing else, so they
can reach nothing else.

Ambient authority is what makes a *confused deputy* (Hardy, 1988): a
program that uses authority it holds for one party on behalf of another.
Hardy's example was a compiler that was allowed to write to a billing file.
A user asked it to write its output to that file, and it obeyed.

Ethereum has an ambient value of this kind, ``tx.origin``: the account that
signed the transaction that started the whole chain of calls. Compare
``msg.sender``, the account or contract that made the current call. A
wallet contract that trusts ``tx.origin`` can be emptied:

#. The wallet pays out whenever ``tx.origin == owner``.
#. An attacker deploys a malicious contract and lures the owner into
   calling it, for example by promising free tokens.
#. The owner sends a transaction to the malicious contract. ``tx.origin`` is
   now the owner.
#. The malicious contract calls the wallet: "pay everything to me". The
   wallet sees ``tx.origin == owner`` and pays.

A wallet that checks ``msg.sender`` instead sees the malicious contract and
refuses. The flaw in one line:

.. math::

   \texttt{tx.origin} = \text{owner} \;\not\Rightarrow\; \text{the owner intended this call}.

In words: that the owner started the transaction does not mean that the
owner meant this particular call to happen.

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

Each new token used to come with its own methods, so every wallet and
exchange had to be adapted to it. ERC-20 fixed one *interface* for
*fungible* tokens, ones where every unit is the same as every other, like
coins. Any wallet or exchange could then hold any token. Thousands of tokens
were issued on it.

The interface is a short list of methods:

- ``balanceOf(a)`` returns the balance of account ``a``.
- ``transfer(to, n)`` moves n tokens from the caller to ``to``.
- ``approve(spender, n)`` lets ``spender`` move up to n of the caller's
  tokens. This limit is the *allowance*.
- ``transferFrom(owner, to, n)``, called by the spender, moves n tokens
  and lowers the allowance by n.

``approve`` overwrites the allowance; it does not adjust it. That opens a
race. A transaction waits in public for a few seconds before it is mined,
that is, added to a block. Anyone can watch the waiting ones. The owner
(Alice) wants to lower the allowance of a spender (Bob) from N to M:

#. Earlier, Alice called ``approve(Bob, N)``.
#. Alice sends ``approve(Bob, M)``. It waits to be mined.
#. Bob sees it waiting. He sends ``transferFrom(Alice, Bob, N)`` with a
   higher fee, so that it is mined first.
#. Bob's transfer runs: he takes N.
#. Alice's ``approve`` runs: the allowance is now M.
#. Bob calls ``transferFrom`` again and takes M more.

.. math::

   \text{spent} = N + M \quad\text{instead of at most}\quad \max(N, M).

In words: Alice meant Bob to spend either the old limit or the new one,
whichever applied when he spent. He spent both.

Vladimirov and Khovratovich described the attack in 2016. The common fixes:

- Change the allowance relative to what is left, with
  ``increaseAllowance`` and ``decreaseAllowance``. If Bob has already
  spent the old allowance, a decrease reverts instead of handing him a
  fresh one.
- Require the allowance to be zero before a new value is set.

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

A contract that pays other accounts can fail when one of them cannot, or
will not, accept the payment. *King of the Ether* showed both failures.

The contract sold a throne:

#. A claimant sends more ether than the current price.
#. The contract pays that ether, less a fee, to the deposed king.
#. The claimant becomes king, and the price rises.

The contract paid with ``send``. It has two quirks:

- It forwards only 2,300 gas, a *stipend*. That is enough for the
  recipient to record a log message, but not to write to its storage.
- It returns ``False`` on failure instead of reverting, so the caller
  carries on unless it checks.

In February 2016 some kings used contract wallets made by the Mist app. The
code these wallets ran on receiving ether needed more than 2,300 gas, so
every ``send`` to them failed. The contract ignored the ``False`` and kept
their money.

Checking the result only moves the problem. If the contract reverts when
``send`` fails, a king whose contract refuses every payment can never be
deposed, since crowning anyone requires paying him.

The lasting fix is the *pull-payment* pattern. The contract never pushes
money out during the game:

#. When a king is deposed, the contract adds the payment to a dict,
   ``owed[king] += payment``.
#. Later, each recipient calls ``withdraw()`` in a transaction of their own.
#. ``withdraw`` sends the caller what they are owed.

.. math::

   \mathrm{owed}[k] \mathrel{+}= \text{payment}, \qquad
   \texttt{withdraw}(): \text{send } \mathrm{owed}[\texttt{msg.sender}],

In words: record the debt now, and let each creditor collect it later.
A recipient who cannot accept payment harms only itself.

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

Each block has a *block gas limit*: a cap on the total gas that all its
transactions may use. A single transaction can never use more. So a loop
whose length users can grow will, one day, cost more than any transaction
can pay.

GovernMental was a *Ponzi* game, one that pays earlier players with the
money of later ones:

#. Investors paid in, and the contract stored each one in an array of
   creditors.
#. If 12 hours passed with no new investor, the last investor could claim
   the jackpot.
#. The payout then reset the game by clearing the array, one storage write
   per entry.

In April 2016 the array had grown so long that clearing it needed more gas
than a block allowed. The payout could not run, and its jackpot of about
1,100 ether was stuck. With :math:`n` creditors the payout fails once

.. math::

   G_{\text{base}} + n\,G_{\text{write}} > G_{\text{block}}.

In words: the fixed cost plus n storage writes exceeds the block's gas
limit. The cost grows as O(n), but the limit is fixed. With this model's
5,000 gas per write and the 2016 limit of 4,712,388 gas, about 940
creditors are already too many.

Any loop over a collection that users can grow is a *denial of service* in
waiting: something that makes a service unusable for everyone. The cures:

- a constant-cost reset, as here: start a new round instead of deleting
  the old entries;
- letting each user process their own entry, in their own transaction.

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

By 2016 Ethereum held thousands of contracts, and nobody knew how many were
broken. Luu, Chu, Olickel, Saxena and Hobor built Oyente to find out. It is
a symbolic executor, as in King's entry above, for EVM bytecode. It uses
the Z3 solver to find inputs.

They ran it on 19,366 contracts then on Ethereum. It flagged 8,833 as
potentially vulnerable, among them the DAO. It looked for four kinds of
bug:

- *Transaction-ordering dependence*: the result depends on which of two
  waiting transactions is mined first, as in the ERC-20 race above.
- *Timestamp dependence*: the result depends on the block's time stamp,
  which the miner, the computer that builds the block, can shift a little.
- *Mishandled exceptions*: a failed call returns ``False`` and the caller
  ignores it, as in King of the Ether.
- *Reentrancy*: a contract calls out to another, and that one calls back
  in before the first has updated its records.

Two further points:

- Analyzing bytecode means analyzing what actually runs, whatever the
  source code said.
- The same paper proposed changes to Ethereum's rules that would rule
  some bug classes out entirely.

A bug becomes a condition on the state at the end of a path. Take a token
transfer that moves a balance from storage slot 1 (the sender) to slot 2
(the receiver). Primes mark values after the transfer, and :math:`s_1, s_2`
are the values before. "Tokens created from nothing" is

.. math::

   \mathrm{slot}_1' \ge s_1 \;\wedge\; \mathrm{slot}_2' > s_2,

In words: the sender lost nothing, yet the receiver gained. Any input that
satisfies both the path condition and this formula is an attack.

BeautyChain's bug is an example. Its ``batchTransfer`` multiplied the
number of receivers by the value each one gets. EVM numbers are 256 bits
wide, so the product wraps: ``(2 * 2**255) % 2**256 == 0``. With two
receivers and a value of :math:`2^{255}`, the sender is charged 0, and each
receiver gets :math:`2^{255}` tokens.

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

Every computer in the network must compute the same result, so a contract
cannot draw a secret random number. Everything it reads, everyone can
read. Early lotteries drew from the previous block's hash, and lost in two
ways:

- An attacker's contract read the same hash in the same block. It worked
  out the result first and played only when it would win.
- A miner could throw away a block whose hash it disliked and build
  another.

A *commit-reveal* scheme, as in RANDAO (2016), splits the draw into two
phases. It is like everyone writing a number in a sealed envelope before
any envelope is opened.

#. Commit: each participant :math:`i` picks a secret :math:`s_i` and a
   random *salt* :math:`r_i`, extra random bytes. They publish only the hash
   :math:`c_i = H(\text{participant}, s_i, r_i)`, their *commitment*.
#. Once every commitment is in, each participant reveals :math:`s_i` and
   :math:`r_i`.
#. The contract recomputes each hash and checks it against :math:`c_i`.
#. The result combines every secret:

.. math::

   R = s_1 \oplus s_2 \oplus \dots \oplus s_n,

Here :math:`\oplus` is XOR (``^`` in Python). If even one secret is random
and was fixed without seeing the others, R is uniformly random.

Why it works, and its limits:

- Nobody can choose a secret after seeing the others, since the hash fixes
  each secret before any is revealed.
- The salt stops anyone from guessing a small secret by hashing every
  possible value.
- Putting the participant's address in the hash stops anyone copying
  another's commitment.
- The last to reveal still sees R first, and may refuse to reveal. Fines
  for not revealing address this. So, later, did *verifiable delay
  functions*: computations that take a known long time even on many
  computers, so that nobody can learn R before the deadline.

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

A *multisig* (multi-signature) wallet is a contract that holds ether and
moves it only when enough of its owners approve, say 2 of 3. Parity made
such wallets. To save on deployment costs, every wallet shared one copy of
the code, a *library*.

Each wallet was a small *stub*. It held the ether and the storage, and
forwarded every call it did not recognize to the library with
``DELEGATECALL``. ``DELEGATECALL`` runs another contract's code on the
caller's own storage. In Python terms, it is like calling a method of one
class on an object of another: ``Library.init_wallet(wallet, ...)`` runs the
library's code, but changes ``wallet``'s attributes.

The library's ``initWallet`` set the owners and the number of approvals
needed. It was meant to run once, at creation. Nothing stopped a second
call. On 19 July 2017 an attacker:

#. called ``initWallet`` on three wallets. Each stub forwarded the call to
   the library, which ran on the wallet's storage;
#. named itself the sole owner;
#. withdrew 153,037 ether.

.. math::

   \text{owners} \leftarrow \text{the last caller of } \texttt{initWallet}.

In words: whoever called the setup function last owned the wallet.

A *white-hat* group, hackers acting to protect users, then drained other
vulnerable wallets themselves to keep the ether safe.

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

Parity fixed ``initWallet`` so that it ran only on storage that had not yet
been set up. But the library was itself a contract with its own storage,
and nobody had ever set that storage up. ``selfdestruct`` is an instruction
that deletes the contract running it.

On 6 November 2017 a user:

#. called ``initWallet`` on the library directly, not through a wallet;
#. became the library's owner;
#. called its ``kill`` function, which executed ``selfdestruct``. The
   library's code was gone.

A ``DELEGATECALL`` to an address without code does not fail. It runs
nothing and reports success. So every wallet built on the library kept its
ether, but lost every function that could move it. 513,774 ether was
frozen.

.. math::

   \texttt{DELEGATECALL}(\text{empty account}) \;\Rightarrow\; \text{success, no effect}.

In words: calling into deleted code is not an error; it silently does
nothing.

The lessons:

- Code reached by ``DELEGATECALL`` is part of every contract that calls it.
- Libraries are therefore now written without state of their own and
  without ``selfdestruct``.
- EIP-6780 (2024), a change to Ethereum's rules, has since restricted
  ``selfdestruct`` itself.

*Implementation:* :class:`blockchainkit.contracts.systems.wallets.PatchedWalletLibrary`
on the same wallet stub. ``selfdestruct`` here removes the code at once
rather than at the end of the transaction.

*References:* Parity Technologies, *A postmortem on the Parity multi-sig
library self-destruct* (15 November 2017).

.. minigallery:: ../../examples/contracts/wallets/plot_02_parity_library_freeze.py

2018 -- ERC-721 Non-Fungible Tokens
-----------------------------------

ERC-20 tokens are interchangeable, like coins. Collectibles, game items
and property titles are not: each one is distinct. CryptoKitties, a game of
collectible cats, had shown the demand in late 2017.

ERC-721 gave each token an identity, a token id, creating the *non-fungible
token* (NFT). The contract keeps a dict
from token ids to owners, rather than a balance per owner:

.. math::

   \mathrm{owner}: \mathrm{id} \mapsto \mathrm{address}, \qquad
   \mathrm{balance}(a) = |\{\mathrm{id} : \mathrm{owner}(\mathrm{id}) = a\}|,

In words: ``owner`` is a dict ``{id: address}``, and an account's balance
is the number of ids it owns,
``sum(1 for o in owner.values() if o == a)``. Collectibles could then be
held and traded like coins.

Tokens sent to a contract that cannot move them are lost for good.
``safeTransferFrom`` guards against this:

#. It moves the token to the recipient.
#. If the recipient is a contract, it calls the recipient's
   ``onERC721Received`` method.
#. It reverts unless the recipient answers with an agreed value, which
   proves that the recipient knows how to handle NFTs.

That check has a cost. The callback is an external call in the middle of a
transfer, which is exactly the setting for reentrancy. Several NFT
mints (sales of newly created tokens) were later drained through it: the
recipient called back into the mint and took more tokens than allowed.

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

Deployed code cannot change, so a bug in a contract is permanent. To make a
contract upgradeable, developers split it in two:

- a *proxy*, which holds the address, the ether and the storage;
- an *implementation*, which holds the code.

It works like this:

#. A user calls the proxy.
#. The proxy forwards every call by ``DELEGATECALL`` to the implementation.
   The implementation's code then runs on the proxy's storage.
#. To upgrade, the owner points the proxy at a new implementation. The
   address and the data stay the same.

EIP-897 (2018) standardized such proxies.

Storage is a numbered row of 32-byte *slots*, like a list. Each contract
gives its fields slots in order: the first field gets slot 0, the next
slot 1, and so on. The proxy and the implementation now read one storage
through two different layouts. A proxy field, such as "address of the
implementation", and an implementation field in the same slot overwrite
each other. This is a *storage collision*. It was behind the 2022 Audius
hack, among others.

EIP-1967 moves the proxy's own fields to slots computed from a hash:

.. math::

   \mathrm{slot} = H(\texttt{"eip1967.proxy.implementation"}) - 1,

In words: hash a fixed string and subtract one. The result is a
random-looking number between 0 and :math:`2^{256}`. Ordinary fields use
slots 0, 1, 2, …, so they will never reach it. Subtracting one ensures
that the slot is not the hash of any known input, so no other hashed slot
lands on it either.

The second rule: a new implementation must keep the old fields where they
are and only add new fields at the end. Reordering them makes the new code
read the old data in the wrong slots.

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

The old ``CREATE`` instruction gives a new contract an address computed
from two things: the deployer's address and the deployer's *nonce*. The
nonce is a counter of how many transactions (or, for a contract, how many
contracts) the deployer has made so far. So the address depends on the
deployer's history, and is hard to predict.

EIP-1014, activated in the Constantinople upgrade of February 2019, added
``CREATE2``:

.. math::

   \mathrm{address} = H(\mathtt{0xff} \,\|\, \mathrm{deployer} \,\|\,
   \mathrm{salt} \,\|\, H(\mathrm{init\ code}))_{[12:]}.

In words: hash a fixed byte, the deployer, a chosen number (the *salt*)
and the hash of the code that sets up the contract (the *init code*). Keep
the last 20 bytes of the 32-byte result, ``digest[12:]`` in Python.

Nothing in the formula depends on the past, so the address is known before
the contract exists. That has a striking consequence:

#. Compute the address from the deployer, salt and code.
#. Send funds to that address, though no contract is there yet.
#. Deploy the contract later, only if it is needed. It appears at exactly
   that address and finds the funds waiting.

Such a contract is *counterfactual*: it acts as if it existed before it
does. Two uses:

- *State channels*, where two parties trade signed updates off the chain,
  deploy their dispute contract only when a dispute actually happens.
- Smart-contract wallets are deployed on first use, at the address their
  owner has already been receiving money on.

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

Unit tests check the cases their author thought of. Bugs live in the cases
nobody thought of.

QuickCheck (Claessen and Hughes, 2000) introduced *property-based
testing*. Instead of writing single cases, the author states a property
that must always hold, and the tool tries it on many random inputs. When it
finds a failure, it *shrinks* it: it simplifies the input step by step
while the failure persists, to report the smallest one. Python's
``hypothesis`` library works this way.

Echidna, from Trail of Bits, applies this to contracts. It is a *fuzzer*: a
tool that feeds a program random inputs to make it fail.

#. The author writes properties, such as "the balances sum to the
   supply".
#. Echidna builds a random sequence of transactions, with random senders
   and arguments.
#. It runs them one by one, checking the properties after each.
#. On a failure, it shrinks the sequence and reports it.

.. math::

   \forall\ \text{transaction sequences}: \quad \sum_a \mathrm{balance}(a) = \mathrm{supply},

In words: for every possible sequence of transactions, the balances of all
accounts add up to the total supply.

Strengths and limits:

- Fuzzing needs no model of the code.
- It never reports a false bug: every failure comes with a sequence that
  really breaks the property.
- It finds only what random sequences reach, so a bug behind one exact
  value can be missed.
- It is now run on most audited contracts, alongside the tools Foundry and
  Medusa.

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

Some projects are run by *governance*: holders of a token vote on
proposals, and a passed proposal runs automatically. A vote that counts
balances at the moment of voting can be bought for the length of one
transaction.

A *flash loan* lends any amount, with no *collateral* (no security
deposit), on one condition: repay within the same transaction, or the whole
transaction reverts. It is like a ``try`` block where the lender's money is
handed back automatically if the loan is not repaid. For one transaction,
anyone can be as rich as the lender.

Beanstalk let holders pass a proposal at once, by ``emergencyCommit``, with
two thirds of the voting power, a day after it was proposed. On 17 April
2022 an attacker:

#. the day before, proposed sending Beanstalk's treasury, its pool of
   funds, to the attacker;
#. borrowed about a billion dollars in flash loans;
#. turned them into voting power;
#. voted for the proposal and committed it, which sent the treasury out;
#. repaid the loans, all in the same transaction, keeping about 80
   million dollars.

The vote held because, within that single transaction,

.. math::

   \frac{\text{borrowed} + \text{own}}{\text{supply}} \ge \frac{2}{3}.

In words: borrowed and owned tokens together made up at least two thirds
of all voting power.

The fix is to count votes at a *snapshot*: the balances in the block before
the proposal was made. No flash loan can change the past, since the loan
exists only inside a later transaction.

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
