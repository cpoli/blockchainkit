blockchainkit.vm
================

.. include:: /_generated/nav/vm.rst

.. automodule:: blockchainkit.vm
   :no-members:

A deterministic 256-bit stack machine with storage, gas limits, step traces, and atomic failure.

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

Plotting
--------

.. automodule:: blockchainkit.vm.visualizers.plots
   :members:
