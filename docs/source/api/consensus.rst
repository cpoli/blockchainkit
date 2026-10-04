blockchainkit.consensus
=======================

.. include:: /_generated/nav/consensus.rst

.. automodule:: blockchainkit.consensus
   :no-members:

Proof-of-work search and its expected cost, catch-up probabilities, and stake-weighted proposer selection.

Every public name below is re-exported by the subpackage: import it as
``bk.consensus.<name>``. The plotting helpers are the exception: import them
explicitly from ``blockchainkit.consensus.visualizers``, which loads Matplotlib.

Types and results
-----------------

.. automodule:: blockchainkit.consensus.core.base
   :members:

Constructions and protocols
---------------------------

.. automodule:: blockchainkit.consensus.systems.pow
   :members:

.. automodule:: blockchainkit.consensus.systems.catch_up
   :members:

.. automodule:: blockchainkit.consensus.systems.pos
   :members:

Plotting
--------

.. automodule:: blockchainkit.consensus.visualizers.plots
   :members:
