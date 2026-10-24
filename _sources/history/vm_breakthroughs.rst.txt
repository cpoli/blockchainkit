Breakthroughs in Replicated Execution
=====================================

.. include:: /_generated/nav/vm.rst

.. epigraph::

   "A smart contract is a set of promises, specified in digital form,
   including protocols within which the parties perform on these promises."
   -- Nick Szabo, *Smart Contracts: Building Blocks for Digital Markets*, 1996

A *blockchain* is a shared record, like a Python list of blocks of
transactions. Many computers keep copies of it in step, without trusting
each other. Each of these computers is called a *node*. Some blockchains
also run programs. Then every node runs every program, and all nodes must
end up with the same *state*: the same stored data, like the same contents
in a big Python dict. That only works if every node gets exactly the same
result from the same program, and if no program can run forever.

The page uses a few terms throughout:

- *Bitcoin* (2009) is the first blockchain. Its coins are guarded by tiny
  programs in a language called *Script*.
- *Ethereum* (2015) is a blockchain that stores general programs as well as
  payments. Its currency is *ether*.
- A *smart contract*, or just *contract*, is a program stored on a
  blockchain. Think of it as a Python object that lives on the blockchain.
  It has saved data and public methods, and anyone can call those methods.
- A *virtual machine* is a computer simulated in software, like the
  interpreter that runs Python's bytecode. The *EVM* (Ethereum Virtual
  Machine) is the one that runs Ethereum's contracts.
- A *stack* is a list used only at one end, like a Python list with only
  ``append`` (*push*) and ``pop``. A *stack machine* is a machine that keeps
  all its working values on such a stack.
- A computation is *deterministic* if the same inputs always give the same
  output. Python's ``sorted`` is deterministic. ``random.random()`` and
  ``time.time()`` are not.
- *All-or-nothing* means a call either completes fully or leaves no trace.

This chronology traces the ideas behind :mod:`blockchainkit.vm`, from
reverse Polish notation to the *overflow* bugs of *token* contracts. (An
overflow is a number that grows too big for its slot and wraps round to a
small one. A token is a balance kept by a contract, such as a dict
``{owner: amount}``.) The argument runs in four steps.

#. Stack machines give a simple, portable way to run programs (1924-1970).
#. Computability theory, the mathematics of what programs can and cannot
   do, shows that nobody can predict whether an arbitrary program stops. So
   execution must be bounded by a budget instead (1936-1966).
#. Keeping many copies in step (*replication*) needs execution to be
   deterministic and all-or-nothing (1978-1981).
#. Smart contracts and blockchains then put these pieces together. Their
   attacks show what happens when one piece is missing (1994-2018).

The stack machine is a small teaching design, not the EVM; :doc:`/protocol` lists exactly where it differs.
How contracts are designed, broken and verified continues in
:doc:`contracts_breakthroughs`.

.. contents:: Timeline
   :local:
   :depth: 1

1924-1957 -- Polish and Reverse Polish Notation
-----------------------------------------------

We write ``(1 + 2) * 3`` with brackets, and rely on rules such as "``*``
before ``+``" (*precedence*). A machine must sort all of that out before it
can compute anything. Is there a way of writing formulas that needs neither?

Jan Łukasiewicz, a Polish logician, found one. He wrote each *operator*
(``+``, ``*``, ...) before its *operands* (the values it acts on): ``+ 1 2``
instead of ``1 + 2``. Then no brackets and no precedence rules are needed.
Charles Hamblin was writing *compilers* for early Australian computers. (A
compiler is a program that translates a programming language into machine
instructions.) He reversed the order. In *reverse Polish notation* (RPN)
each operator comes after its operands. That is exactly the order in which a
stack machine computes, reading left to right:

#. Read the next item.
#. If it is a number, push it onto the stack.
#. If it is an operator, pop two values, apply the operator, and push the
   result.
#. Repeat until the input ends. The answer is the one value left on the
   stack.

The ordinary formula on the left becomes the RPN sequence on the right:

.. math::

   (1 + 2) \times 3 \quad\longrightarrow\quad 1\ 2\ +\ 3\ \times.

Run the steps on it. Push 1, push 2. ``+`` pops both and pushes 3. Push 3.
``×`` pops both and pushes 9.

Edsger Dijkstra's *shunting-yard algorithm* (1961) converts ordinary
*infix* notation (operator between operands, as we usually write) into RPN.
It is named after a railway yard where wagons are sorted onto side tracks.
Operators wait on a side stack until their operands have passed:

#. Send each number straight to the output.
#. Before pushing an operator onto the side stack, first move to the output
   every waiting operator of higher or equal precedence.
#. Push ``(`` onto the side stack. On ``)``, move operators to the output
   until the matching ``(``, then drop both brackets.
#. At the end, move every remaining operator to the output.

Every stack virtual machine, including Bitcoin Script and the EVM, runs code
in this form.

*Implementation:* :func:`blockchainkit.vm.systems.expressions.to_rpn` (shunting
yard) and :func:`blockchainkit.vm.systems.expressions.compile_expression`.

*References:* J. Łukasiewicz, *Elementy logiki matematycznej* (1929);
C. L. Hamblin, *Translation to and from Polish notation*, The Computer Journal
5(3), 210–213 (1962). `DOI <https://doi.org/10.1093/comjnl/5.3.210>`__.

.. minigallery:: ../../examples/vm/foundations/plot_01_reverse_polish.py

1936 -- Turing Machines and the Halting Problem
-----------------------------------------------

Can a program look at any other program and tell whether it will ever stop?
Alan Turing proved that it cannot.

First he needed a precise model of "a program". A *Turing machine* has:

- a *tape*, an unbounded row of cells, each holding one symbol, like a
  Python list that grows whenever you walk off its end;
- a head that reads and writes one cell at a time and moves one step left
  or right;
- a finite table of rules, like a dict
  ``{(state, symbol): (write, move, next_state)}``. One special state means
  "halt" (stop).

A problem is *decidable* if some program answers it correctly for every
input and always finishes. Turing showed that the *halting problem* is not
decidable: no machine can say, for every machine and input, whether it
halts. His proof uses *diagonalization*, which here means feeding a program
its own code. In Python terms:

#. Suppose someone has written ``halts(prog, data)``. It always finishes,
   and returns ``True`` exactly when ``prog(data)`` would eventually stop.
#. Write ``def g(p):`` that calls ``halts(p, p)``. If the answer is
   ``True``, ``g`` loops forever (``while True: pass``). Otherwise it
   returns.
#. Ask what ``g(g)`` does. If it stops, then ``halts(g, g)`` was ``True``,
   so ``g`` loops forever. If it loops forever, then ``halts(g, g)`` was
   ``False``, so ``g`` returns. Both cases contradict themselves.
#. So ``halts`` cannot exist.

Rice's theorem extends this to every *nontrivial* property of a program's
behavior. A property is nontrivial if some programs have it and some do
not, for example "returns 0 on every input" or "never divides by zero".
None of these can be decided by a program.

For a blockchain, this means a node cannot inspect a stranger's contract and
reject it in advance for never finishing. It can only give each call a
budget. Ethereum's answer is *gas*, a step budget for each call:

#. Whoever sends a call attaches a finite amount of gas to it.
#. Every instruction the call runs subtracts its fixed cost from that
   amount.
#. If the amount would drop below zero, execution stops with an error.

So every call ends, either by finishing or by running out of gas. The
budget does not decide halting. It makes the question irrelevant.

*Implementation:* :func:`blockchainkit.vm.systems.turing.run_turing_machine`
(with exact cycle detection) and
:func:`blockchainkit.vm.systems.turing.enumerate_machines`.

*References:* A. M. Turing, *On computable numbers, with an application to the
Entscheidungsproblem*, Proceedings of the London Mathematical Society
s2-42(1), 230–265 (1937; read 1936). `DOI
<https://doi.org/10.1112/plms/s2-42.1.230>`__.

.. minigallery:: ../../examples/vm/foundations/plot_02_halting_problem.py

1961 -- A Hardware Stack: The Burroughs B5000
---------------------------------------------

Most processors hold intermediate results in *registers*: a few named,
very fast storage slots, like a handful of fixed global variables. The
compiler must decide which value goes in which register at each moment.
This is called *register allocation*, and it is hard to do well.

Robert Barton designed the Burroughs B5000 computer to keep intermediate
results on a hardware stack instead. Programs written in Algol, an early
programming language, then mapped directly onto machine operations. The
stack needs no register allocation. But it has a cost:

- The stack is a finite resource.
- The shape of an expression decides how much stack its evaluation needs.

Evaluated left to right, :math:`((1 + 2) + 3) + 4` never holds more than two
values, because each sum is finished before the next operand arrives. In RPN
it is ``1 2 + 3 + 4 +``. :math:`1 + (2 + (3 + 4))` holds all four at once,
because every addition waits for the one inside it. In RPN it is
``1 2 3 4 + + +``.

Virtual machines inherit the limit. A *word* is the machine's basic unit of
data, one stack slot.

- The EVM caps its stack at 1024 words.
- Bitcoin has a main stack and a second "alt" stack, and caps the two
  together at 1000 items.

*Implementation:* the ``stack_limit`` of
:func:`blockchainkit.vm.systems.stack_machine.execute`;
:func:`blockchainkit.vm.visualizers.plots.plot_stack_height`.

*References:* R. S. Barton, *A new approach to the functional design of a
digital computer*, Proc. Western Joint Computer Conference, 393–396 (1961).
`DOI <https://doi.org/10.1145/1460690.1460736>`__.

.. minigallery:: ../../examples/vm/foundations/plot_03_hardware_stack.py

1962 -- Radó's Busy Beaver
--------------------------

Among all tiny programs that eventually stop, which runs longest? Tibor
Radó turned this into a precise question.

Take every Turing machine with :math:`n` states and two tape symbols (0 and
1). Start each one on a *blank* tape (all 0s). Some run forever. Among those
that halt, the *busy-beaver function* :math:`S(n)` is the largest number of
steps any of them takes. For each :math:`n` there are only finitely many
such machines, so :math:`S(n)` is a well-defined whole number.

Radó proved that :math:`S` is not *computable*: no program can output
:math:`S(n)` for every :math:`n`. The reason is short. Suppose such a
program existed. Then this procedure would decide halting on a blank tape:

#. Given an :math:`n`-state machine, compute :math:`S(n)`.
#. Run the machine for :math:`S(n)` steps.
#. If it has stopped, answer "halts". If not, answer "runs forever": any
   halting :math:`n`-state machine stops within :math:`S(n)` steps, by the
   definition of :math:`S`.

But halting on a blank tape is just as undecidable as Turing's halting
problem. So no such program exists.

Radó also proved more: :math:`S` eventually grows faster than every
computable function. Pick any function ``f`` you could write in Python.
Then :math:`S(n) > f(n)` for every large enough :math:`n`. The known values
show how fast it takes off:

.. math::

   S(1) = 1,\quad S(2) = 6,\quad S(3) = 21,\quad S(4) = 107,\quad
   S(5) = 47{,}176{,}870.

So the longest-running halting 5-state machine takes about 47 million
steps, while the 4-state record is only 107.

Lin and Radó settled :math:`S(3)` by computer in 1965. :math:`S(5)` was
proved by the bbchallenge collaboration, an online group of volunteers, in
2024.

A gas limit plays the role that :math:`S(n)` would play: a step count
beyond which execution stops. Because the true bound cannot be computed,
the limit is chosen by policy instead.

*Implementation:* :func:`blockchainkit.vm.systems.turing.busy_beaver` searches
every machine of a given size.

*References:* T. Radó, *On non-computable functions*, Bell System Technical
Journal 41(3), 877–884 (1962). `DOI
<https://doi.org/10.1002/j.1538-7305.1962.tb00480.x>`__; S. Lin and T. Radó,
*Computer studies of Turing machine problems*, Journal of the ACM 12(2),
196–212 (1965). `DOI <https://doi.org/10.1145/321264.321270>`__.

.. minigallery:: ../../examples/vm/foundations/plot_04_busy_beaver.py

1966 -- Böhm and Jacopini: Sequence, Selection, Iteration
---------------------------------------------------------

Early programs were drawn as *flowcharts*: boxes joined by arrows, where any
arrow could jump anywhere, like ``goto``. Which kinds of jump does a
programmer really need?

Corrado Böhm and Giuseppe Jacopini proved that three building blocks
suffice to express any flowchart. Sometimes the program needs extra
Boolean (``True``/``False``) flag variables to do it. The blocks are the
ones Python offers:

- *sequence*: do this, then that (one statement after another);
- *selection*: choose between two paths (``if``/``else``);
- *iteration*: repeat while a condition holds (``while``).

Dijkstra's *Go To Statement Considered Harmful* (1968) turned the result
into a discipline: write programs from these three blocks only. On a stack
machine the three blocks become:

- straight-line code, run in order;
- a *conditional jump*: "go to instruction number L if the top of the stack
  is nonzero";
- a *backward jump*: a jump to an earlier instruction, which makes a loop.

Only iteration can make a program run longer than it is:

- Without backward jumps, each instruction runs at most once. So running
  time is bounded by program length: O(n) steps for n instructions.
- With them, a loop can run for as long as its input asks. That is what
  makes gas necessary.
- Bitcoin Script leaves out backward jumps entirely.

Programs with jumps are usually written with named *labels* in place of
instruction numbers. An *assembler* turns this readable text into the list
of instructions. A *two-pass* assembler goes over the text twice:

#. On the first pass, it records the address (position) of each label in a
   dict ``{label: address}``.
#. On the second pass, it replaces each label in a jump by its address.

*Implementation:* :func:`blockchainkit.vm.systems.assembler.assemble`, a
two-pass assembler that resolves labels to addresses.

*References:* C. Böhm and G. Jacopini, *Flow diagrams, Turing machines and
languages with only two formation rules*, Communications of the ACM 9(5),
366–371 (1966). `DOI <https://doi.org/10.1145/355592.365646>`__.

.. minigallery:: ../../examples/vm/foundations/plot_05_structured_programming.py

1970 -- Forth and Stack Words
-----------------------------

Without named variables, how does a stack program get at a value that is
not on top of the stack?

Charles Moore developed the Forth language around 1970 to control radio
telescopes. Instead of naming variables, a Forth program shuffles the values
on its data stack with a few small commands, called *words*. Each word is
documented by a *stack diagram* ``( before -- after )``, with the top of the
stack on the right. For a Python list ``s`` used as a stack:

- ``DUP ( a -- a a )`` copies the top value: ``s.append(s[-1])``.
- ``DROP ( a -- )`` discards it: ``s.pop()``.
- ``SWAP ( a b -- b a )`` swaps the top two: ``s[-2], s[-1] = s[-1], s[-2]``.
- ``OVER ( a b -- a b a )`` copies the second value to the top:
  ``s.append(s[-2])``.
- ``ROT ( a b c -- b c a )`` moves the third value to the top:
  ``s.append(s.pop(-3))``.

The language is tiny, fast, and easy to implement on small machines.
Bitcoin's Script is explicitly Forth-like, and the EVM has whole families
of ``DUP`` and ``SWAP`` instructions.

*Implementation:* the ``DUP``, ``DROP``, ``SWAP``, ``OVER`` and ``ROT`` opcodes
of :func:`blockchainkit.vm.systems.stack_machine.execute`, whose stack effects
are listed in :data:`blockchainkit.vm.systems.stack_machine.STACK_EFFECTS`.

*References:* E. D. Rather, D. R. Colburn and C. H. Moore, *The evolution of
Forth*, HOPL-II, 177–199 (1993). `DOI <https://doi.org/10.1145/154766.155369>`__.

.. minigallery:: ../../examples/vm/foundations/plot_06_forth.py

1978-1990 -- State-Machine Replication
--------------------------------------

One computer can crash. How do you build a service that keeps working when
some of its computers fail (a *fault-tolerant* service)?

Run several copies. Here a *state machine* is any program whose state
changes only when it applies a command, like an object whose only method
is ``apply(command)``. Leslie Lamport's 1978 paper showed how separate
computers can act as one state machine: they agree on a *total order* of
commands, one single sequence that everyone follows. Fred Schneider's 1990
tutorial made *state machine replication* the general recipe:

#. Start every copy in the same state.
#. Agree on one order for all incoming requests.
#. Each copy applies the requests, one by one, in that order.

Copies that start alike and apply the same requests in the same order stay
identical. The recipe needs two things:

- agreement on the order of inputs;
- deterministic execution, so that the same request has the same effect on
  every copy.

A blockchain supplies the first with *consensus*, a protocol by which nodes
agree on one list of transactions. It supplies the second with a virtual
machine that has no access to clocks, randomness or the network. Each of
those could give different answers on different nodes, as ``time.time()``
does.

*Implementation:* the determinism of
:func:`blockchainkit.vm.systems.stack_machine.execute`: the same program,
storage and arguments always give the same result.

*References:* L. Lamport, *Time, clocks, and the ordering of events in a
distributed system*, Communications of the ACM 21(7), 558–565 (1978);
F. B. Schneider, *Implementing fault-tolerant services using the state machine
approach: a tutorial*, ACM Computing Surveys 22(4), 299–319 (1990). `DOI
<https://doi.org/10.1145/98163.98167>`__.

.. minigallery:: ../../examples/vm/replication/plot_01_state_machine_replication.py

1981 -- Gray's Transaction Concept
----------------------------------

A bank transfer takes money from one account and adds it to another. If the
computer fails between the two steps, money vanishes. A transfer must either
fully happen or not happen at all.

Jim Gray defined a *transaction* as a unit of work with these properties:

- *atomic*: it happens completely or not at all;
- *consistent*: it takes valid data to valid data (for example, the total
  money stays the same);
- *durable*: once it has completed, its effect survives later crashes.

Isolation (transactions running at the same time do not see each other's
half-done work) was added later, giving the four *ACID* properties.

Atomicity means that a failure at any point leaves no partial effects. A
common way to get it is to work on a copy, as in
``new = dict(storage)``, and keep the copy only if every step succeeds.

Every Ethereum call is a transaction in this sense. A contract's *storage*
is its saved data, like a dict that persists between calls. A call
*reverts* when it fails or deliberately aborts:

- When execution reverts or runs out of gas, all of its storage writes are
  discarded.
- The gas spent is still paid, because the nodes did the work.

*Implementation:* :func:`blockchainkit.vm.systems.stack_machine.execute` runs
on a copy of storage and returns it only on success; ``REVERT`` aborts
deliberately.

*References:* J. Gray, *The transaction concept: virtues and limitations*,
Proc. 7th International Conference on Very Large Data Bases, 144–154 (1981).

.. minigallery:: ../../examples/vm/replication/plot_02_atomic_transactions.py

1994 -- Szabo's Smart Contracts
-------------------------------

Some agreements can be enforced by a machine instead of a court. A vending
machine sells to anyone who pays, and nobody can take the goods without
paying:

#. The buyer inserts coins.
#. The machine checks that the amount covers the price.
#. If it does, the machine releases the item and returns the change.
   Otherwise it returns the coins.

Nick Szabo coined *smart contract* for computer protocols that carry out
the terms of a contract. He gave the vending machine as their ancestor. He
argued that they could reduce the need for *trusted intermediaries*: the
banks, escrow agents and courts that parties rely on today to make sure
everyone keeps their promises.

Ethereum made the idea practical by putting contract code and state on a
blockchain. There every node runs the code, and anyone can check the
result.

*Implementation:* :func:`blockchainkit.vm.systems.programs.vending_machine`,
run with the ``arguments`` of
:func:`blockchainkit.vm.systems.stack_machine.execute`.

*References:* N. Szabo, *Smart contracts* (1994); N. Szabo, *Formalizing and
securing relationships on public networks*, First Monday 2(9) (1997). `DOI
<https://doi.org/10.5210/fm.v2i9.548>`__.

.. minigallery:: ../../examples/vm/contracts/plot_01_vending_machine.py

1995 -- Bytecode Verification
-----------------------------

Java programs are downloaded from strangers and run as *bytecode*: a list
of simple machine instructions, like the output of Python's ``dis`` module.
A malformed program could pop values that are not there and corrupt the
machine. Checking the stack before every instruction is slow.

James Gosling's design of the Java virtual machine checks downloaded
bytecode once, before running it. The check is a *data-flow analysis*: it
follows every path through the code and tracks what the stack looks like at
each instruction, without running the program on real values.

#. Start at the first instruction with an empty stack.
#. For each instruction, compute the stack height after it from the height
   before it.
#. Follow every possible next instruction, on both sides of each jump.
#. Where two paths meet, check that they agree on the stack's shape.
#. Reject the program if any instruction would pop more values than are
   present.

This has useful consequences:

- Because the check covers every path, verified code can run without
  run-time stack checks.
- Its maximum stack size is known in advance.

Rice's theorem is not contradicted. The verifier checks the *form* of the
code on every path, whether or not that path can ever run. That question
is decidable. The price is that it rejects some programs that would in fact
behave well.

The same idea of validating code once, at deployment, is behind Ethereum's
*EVM Object Format* (EOF) proposals, a planned container for contract code
that is checked when the contract is created. The implementation below is
an *abstract interpretation*: it runs the program on a summary of each value
(here, only how many values are on the stack) instead of on the values
themselves.

*Implementation:* :func:`blockchainkit.vm.systems.verifier.verify_bytecode`, an
abstract interpretation of stack heights only; the JVM verifier also infers the
type of every stack slot and local variable.

*References:* J. Gosling, *Java intermediate bytecodes*, ACM SIGPLAN Workshop
on Intermediate Representations, 111–118 (1995). `DOI
<https://doi.org/10.1145/202529.202541>`__.

.. minigallery:: ../../examples/vm/contracts/plot_02_bytecode_verification.py

2009 -- Bitcoin Script and Pay-to-Public-Key-Hash
-------------------------------------------------

How do you say who may spend a coin, when there is no bank to check?

Bitcoin's first release locked each coin with a tiny program in Script, a
stack language with no loops. To spend the coin, one supplies the inputs
that make the program succeed. Two ideas from cryptography do the work:

- A *hash function* is like Python's ``hash()``, but built so that nobody
  can find two inputs with the same output, or an input for a given output.
  Its output, the *hash*, works as a short fingerprint of any data.
  ``OP_HASH160`` computes a 160-bit hash.
- A *digital signature* uses a pair of keys. The owner keeps the *private
  key* secret and publishes the *public key*. Only the private key can
  produce a valid signature on a message. Anyone with the public key can
  check it.

The common lock, *pay-to-public-key-hash*, is
``OP_DUP OP_HASH160 <hash> OP_EQUALVERIFY OP_CHECKSIG``. It pays whoever
shows a public key with that hash and a valid signature by it. Spending
runs like this:

#. The spender pushes a signature and a public key onto the stack.
#. ``OP_DUP`` copies the key.
#. ``OP_HASH160`` hashes the copy.
#. ``<hash>`` pushes the hash written in the lock.
#. ``OP_EQUALVERIFY`` stops with failure unless the two hashes match.
#. ``OP_CHECKSIG`` checks the signature against the key. The spend is valid
   if it succeeds.

Without loops, execution time is bounded by script length, so Bitcoin needs
no gas.

Until 2010 the unlocking and locking scripts were joined end to end and run
as one program. That allowed an attack:

#. The attacker wrote an unlocking script ending in ``OP_TRUE OP_RETURN``.
#. ``OP_TRUE`` pushed a "true" value.
#. ``OP_RETURN`` then ended execution early with whatever was on the stack.
#. The program succeeded before the lock's checks ever ran.

The bug is listed as CVE-2010-5141. (A *CVE* number is an entry in the
public catalogue of security flaws.) The two scripts are now run
separately.

The implementation below differs from Bitcoin in a few ways it names.
*Big-endian* means the most significant byte comes first, as in
``int.from_bytes(b, "big")``. ``OP_HASH256`` applies the SHA-256 hash twice.
*Schnorr signatures* are one kind of digital signature. A *transaction
digest* is the hash of the spending transaction, which is the message
real Bitcoin signs.

*Implementation:* :func:`blockchainkit.vm.systems.script.verify_script`,
:func:`blockchainkit.vm.systems.script.p2pkh_locking` and
:func:`blockchainkit.vm.systems.script.p2pkh_unlocking` support a small opcode
subset on big-endian numbers, use ``OP_HASH256`` in place of ``OP_HASH160``,
and check this package's Schnorr signatures over an explicit message rather
than a transaction digest.

*References:* S. Nakamoto, Bitcoin v0.1 source code, ``script.cpp`` (2009);
`Bitcoin Script documentation
<https://developer.bitcoin.org/devguide/transactions.html>`__.

.. minigallery:: ../../examples/vm/script/plot_01_p2pkh.py

2014 -- Ethereum and Programmable Replicated State
--------------------------------------------------

Bitcoin's scripts can only decide whether a coin may be spent. Could a
blockchain run any program instead?

Ethereum's whitepaper describes a blockchain as a *state-transition
system*: a function ``apply(state, transaction)`` that returns the new
state. Its rules can include programmable contracts, so participants agree
on program results as well as payments. Two requirements follow:

- Replication requires deterministic execution.
- A gas budget stops any one program from consuming unlimited computation.

In symbols, one step looks like this:

.. math::

   (S,\mathrm{program},\mathrm{input},\mathrm{gas})\longrightarrow S'
   \quad\text{or an execution error leaving } S.

In words: running a program on state :math:`S` with some input and a gas
budget either produces a new state :math:`S'`, or fails and leaves
:math:`S` exactly as it was.

Words are 256 bits (32 bytes), wide enough for hashes and keys. Each word
holds a number from 0 to :math:`2^{256} - 1`.

*Implementation:* :func:`blockchainkit.vm.systems.stack_machine.execute` is a
256-bit stack machine with integer storage, branches, a stack bound, and an
instruction budget. It works on a copy of storage and returns a new state only
on success. Every instruction costs one gas unit by default, and there are no
memory, contract calls, logs or refunds: this is not the EVM.

*References:* V. Buterin, *A Next-Generation Smart Contract and Decentralized
Application Platform* (2014). `Original whitepaper maintained by Ethereum
<https://ethereum.org/en/whitepaper/>`__. The historical design is not a
specification of the present-day Ethereum network.

.. minigallery:: ../../examples/vm/ethereum/plot_01_gas.py

2015-2016 -- Hash Time-Locked Contracts
---------------------------------------

"Bob gets this money if he reveals the secret behind this hash; if he does
not by a deadline, Alice gets it back." Two script features make this
possible:

- A *hash lock*. A *preimage* of a hash :math:`h` is an input ``s`` with
  ``H(s) == h``. Nobody can work it out from :math:`h`, so revealing it
  proves you knew the secret.
- A *time lock*. Peter Todd's ``OP_CHECKLOCKTIMEVERIFY`` (BIP 65, activated
  in 2015) let a script refuse a spend before a given time. (A *BIP* is a
  Bitcoin Improvement Proposal, a numbered design document.)

Combined, they give the *hash time-locked contract* (HTLC). The money can
be spent in one of two ways:

- pay on revealing a preimage;
- or refund after a timeout.

A *payment channel* lets two people pay each other many times while
touching the blockchain only to open and close it. Poon and Dryja's
Lightning Network chains HTLCs that share one hash along a route of payment
channels. Each channel on the route is a *hop*. Say Alice pays Carol
through Bob:

#. Carol picks a secret ``s`` and gives Alice its hash ``H(s)``.
#. Alice locks money for Bob in an HTLC on ``H(s)`` with a timeout
   :math:`T_1`.
#. Bob locks the same amount for Carol in an HTLC on ``H(s)`` with an
   earlier timeout :math:`T_2 < T_1`.
#. Carol reveals ``s`` to claim Bob's payment.
#. Bob now knows ``s``, and uses it to claim Alice's payment.

Revealing the preimage at the last hop lets every earlier hop claim too.
Timeouts grow toward the sender (:math:`T_1 > T_2`). So an intermediary that
is paid out downstream with the preimage still has time to claim from
upstream before its own refund deadline passes.

Real Lightning has more machinery than this model:

- *relative timelocks*, which count a delay from the moment a payment was
  recorded rather than to a fixed time;
- *penalty transactions*, which let one party take all the channel's money
  if the other tries to cheat with an old balance.

*Implementation:* :func:`blockchainkit.vm.systems.script.htlc_locking` and the
``locktime`` argument of :func:`blockchainkit.vm.systems.script.verify_script`.
Lock times are compared as plain numbers; Lightning also uses relative
timelocks (``OP_CHECKSEQUENCEVERIFY``) and penalty transactions, which are not
modeled.

*References:* P. Todd, *BIP 65: OP_CHECKLOCKTIMEVERIFY* (2014). `Specification
<https://github.com/bitcoin/bips/blob/master/bip-0065.mediawiki>`__; J. Poon
and T. Dryja, *The Bitcoin Lightning Network: scalable off-chain instant
payments* (2016).

.. minigallery:: ../../examples/vm/script/plot_02_htlc.py

2016 -- The DAO and Reentrancy
------------------------------

The DAO (Decentralized Autonomous Organization) was a crowdfunded
investment contract holding about 14% of all ether. Its split function let
an investor withdraw their deposit. It did two things in the wrong order:

- it sent ether before zeroing the caller's balance;
- and sending ether to a contract runs that contract's code, its *fallback*
  function.

In June 2016 an attacker exploited this:

#. The attacker's contract called the split function.
#. The DAO checked the attacker's balance, then sent the ether.
#. Receiving the ether ran the attacker's fallback, which called the split
   function again, from inside the payment.
#. Because the balance had not yet been zeroed, every nested call passed
   the balance check and paid out the full deposit again.
#. The attacker repeated this and drained about 3.6 million ether.

Ethereum *hard-forked* to reverse the theft: nodes switched to new software
whose rules moved the stolen ether back. Nodes that refused kept the old
chain, which continues as Ethereum Classic.

*Reentrancy*, being called again before the first call has finished,
became the canonical smart-contract bug. It is avoided by the
*checks-effects-interactions* order:

#. Checks: verify the request (is the balance enough?).
#. Effects: update the contract's own state (set the balance to 0).
#. Interactions: only then call or pay other contracts.

*Implementation:* :func:`blockchainkit.vm.systems.reentrancy.drain_bank`, a
Python model of the call pattern with an attacker whose fallback re-enters, not
EVM execution; the DAO's real split function also involved token balances and a
waiting period.

*References:* N. Atzei, M. Bartoletti and T. Cimoli, *A survey of attacks on
Ethereum smart contracts (SoK)*, POST 2017, LNCS 10204, 164–186 (2017). `DOI
<https://doi.org/10.1007/978-3-662-54455-6_8>`__.

.. minigallery:: ../../examples/vm/ethereum/plot_03_reentrancy.py

2016 -- Gas Repricing after Denial-of-Service Attacks
-----------------------------------------------------

Gas is meant to reflect real work. If an operation costs little gas but a
lot of real work, an attacker can fill blocks with it and slow every node
down. This is a *denial-of-service* attack: overloading a service so that
honest users cannot use it.

In September 2016 this happened to Ethereum:

#. Attackers sent transactions that called underpriced, disk-heavy
   instructions over and over. One was ``EXTCODESIZE``, which reads the
   size of another contract's code from disk.
#. Each such call cost little gas, so a block could hold very many.
#. Every node had to do all those disk reads, and blocks took far longer to
   process.

EIP-150 raised the prices. (An *EIP* is an Ethereum Improvement Proposal.)
It took effect in the *Tangerine Whistle* fork, a coordinated rule upgrade
in October 2016:

- ``SLOAD`` (read a storage slot) from 50 to 200 gas;
- ``BALANCE`` (read an account's balance) from 20 to 400;
- ``EXTCODESIZE`` and ``CALL`` (call another contract) to 700.

Gas prices are security parameters. An attacker always picks the
instruction with the most work per unit of gas, so the cheapest instruction
relative to its real cost sets how much damage a block can do.

*Implementation:* the ``gas_costs`` schedule of
:func:`blockchainkit.vm.systems.stack_machine.execute`. The real-work costs in
the experiment are teaching estimates, not measurements of any Ethereum client.

*References:* V. Buterin, *EIP-150: Gas cost changes for IO-heavy operations*
(2016). `Specification <https://eips.ethereum.org/EIPS/eip-150>`__.

.. minigallery:: ../../examples/vm/ethereum/plot_02_gas_repricing.py

2018 -- Integer Overflow: BeautyChain
-------------------------------------

Machine integers wrap around like a car's odometer. An EVM word holds 256
bits, so arithmetic is done modulo :math:`2^{256}`: every result is reduced
as with ``% 2**256`` in Python. A result that is too big wraps round to a
small number. This is an *integer overflow*.

In April 2018 an attacker used this against the BeautyChain token (BEC):

#. The attacker called the token's ``batchTransfer`` with two recipients
   and ``value`` :math:`= 2^{255}` for each.
#. The contract computed the total as ``count * value``, which wrapped
   round to 0.
#. It checked that the sender held at least 0 tokens. That passed, even for
   a sender who had nothing.
#. It subtracted 0 from the sender.
#. It credited each recipient with :math:`2^{255}` tokens, :math:`2^{256}` in
   total, created from nothing.

The wrapped total in step 2 is:

.. math::

   2 \times 2^{255} \equiv 0 \pmod{2^{256}},

that is, ``(2 * 2**255) % 2**256 == 0`` in Python. The bug is listed as
CVE-2018-10299. Exchanges suspended the token.

*Checked arithmetic* detects the wrap and reverts instead. It came first
through the SafeMath library and, since version 0.8 of Solidity (the main
language for Ethereum contracts), by default.

- SafeMath's test is that dividing the product by one factor gives back the
  other.
- Here it fails, because :math:`0 / 2 \ne 2^{255}`.

*Implementation:* :func:`blockchainkit.vm.systems.programs.batch_transfer` is a
stack-machine program with storage slots as accounts, not the Solidity
contract; ``checked=True`` adds the SafeMath test ``amount / count == value``.

*References:* `CVE-2018-10299 <https://nvd.nist.gov/vuln/detail/CVE-2018-10299>`__
(2018).

.. minigallery:: ../../examples/vm/ethereum/plot_04_integer_overflow.py
