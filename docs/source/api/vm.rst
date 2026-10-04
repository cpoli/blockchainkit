blockchainkit.vm
================

.. include:: /_generated/nav/vm.rst

.. automodule:: blockchainkit.vm
   :no-members:

A deterministic 256-bit stack machine and the languages, programs, and models built on it: assembly,
reverse Polish notation, bytecode verification, Turing machines, Bitcoin Script, contracts, and attacks.

Every public name below is re-exported by the subpackage: import it as
``bk.vm.<name>``. The plotting helpers are the exception: import them
explicitly from ``blockchainkit.vm.visualizers``, which loads Matplotlib.

Types and results
-----------------

.. automodule:: blockchainkit.vm.core.base
   :members:

Constructions and protocols
---------------------------

.. automodule:: blockchainkit.vm.systems.stack_machine
   :members:

.. automodule:: blockchainkit.vm.systems.assembler
   :members:

.. automodule:: blockchainkit.vm.systems.expressions
   :members:

.. automodule:: blockchainkit.vm.systems.verifier
   :members:

.. automodule:: blockchainkit.vm.systems.turing
   :members:

.. automodule:: blockchainkit.vm.systems.script
   :members:

.. automodule:: blockchainkit.vm.systems.programs
   :members:

.. automodule:: blockchainkit.vm.systems.reentrancy
   :members:

Plotting
--------

.. automodule:: blockchainkit.vm.visualizers.plots
   :members:
