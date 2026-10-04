Breakthroughs in Replicated Execution
=====================================

.. include:: /_generated/nav/vm.rst

When every node must reach the same state, every node must run the same
program and get the same result, within bounded resources. This chronology
traces the ideas behind :mod:`blockchainkit.vm`.

All snippets use the package's conventional import: ``import blockchainkit as bk``.

.. contents:: Timeline
   :local:
   :depth: 1

2014 — Ethereum and programmable replicated state
-------------------------------------------------

**In plain language.** Participants can agree on program results as well as payments if
they all execute the same rules. A work budget stops one program from consuming
unlimited computation.

**Reading the experiment.** S is the state before execution and S prime is the state
afterward. In this experiment, a successful program returns updated storage; an error
leaves the original storage untouched. This small virtual machine is separate from the
payment ledger, rather than an Ethereum implementation.

Ethereum's whitepaper describes a blockchain as a state-transition system
whose rules can include programmable contracts. Replication
requires deterministic execution, while bounded execution cost limits the
resources an individual program can demand.

.. math::

   (S,\mathrm{program},\mathrm{input})\longrightarrow S'
   \quad\text{or an execution error}.

**Implementation:** :func:`blockchainkit.vm.systems.stack_machine.execute` provides a
256-bit stack machine, integer storage, branches, a stack bound, and an
instruction budget. It works on a storage copy and returns a new state only
after success; errors leave the caller's state unchanged.

**Experiment:** :doc:`/api/gallery/vm/stack_machine/plot_01_execution` compares successful execution,
out-of-gas failure, and a bounded infinite loop. Costs are one unit per
instruction, not an EVM gas schedule. The VM is independent of the transfer-only
ledger: connecting arbitrary contract transactions would require a further
consensus specification.

*References:* V. Buterin, *A Next-Generation Smart Contract and Decentralized
Application Platform* (2014). `Original whitepaper maintained by Ethereum
<https://ethereum.org/en/whitepaper/>`__. The historical design is not a
specification of the present-day Ethereum network.

.. minigallery:: ../../examples/vm/stack_machine/plot_01_execution.py
