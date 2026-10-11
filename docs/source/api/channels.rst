blockchainkit.channels
======================

.. include:: /_generated/nav/channels.rst

.. automodule:: blockchainkit.channels
   :no-members:

How a blockchain scales beyond what every node can verify, and how chains
connect: Reed-Solomon codes and data-availability sampling; payment
channels from Spilman's to Lightning and eltoo, state channels and
watchtowers; multi-hop routing and balance probing; atomic swaps, a
light-client relay and two bridge exploits; Plasma, sharding, and zk and
optimistic rollups.

Every public name below is re-exported by the subpackage: import it as
``bk.channels.<name>``. The plotting helpers are the exception: import them
explicitly from ``blockchainkit.channels.visualizers``, which loads
Matplotlib.

Results
-------

.. automodule:: blockchainkit.channels.core.base
   :members:

Erasure codes and data availability
-----------------------------------

.. automodule:: blockchainkit.channels.systems.reed_solomon
   :members:

.. automodule:: blockchainkit.channels.systems.data_availability
   :members:

Payment and state channels
--------------------------

.. automodule:: blockchainkit.channels.systems.micropayment
   :members:

.. automodule:: blockchainkit.channels.systems.duplex
   :members:

.. automodule:: blockchainkit.channels.systems.lightning
   :members:

.. automodule:: blockchainkit.channels.systems.state_channels
   :members:

.. automodule:: blockchainkit.channels.systems.eltoo
   :members:

.. automodule:: blockchainkit.channels.systems.watchtowers
   :members:

Channel networks
----------------

.. automodule:: blockchainkit.channels.systems.routing
   :members:

.. automodule:: blockchainkit.channels.systems.probing
   :members:

Interoperability
----------------

.. automodule:: blockchainkit.channels.systems.swaps
   :members:

.. automodule:: blockchainkit.channels.systems.relay
   :members:

.. automodule:: blockchainkit.channels.systems.bridges
   :members:

Scaling the chain
-----------------

.. automodule:: blockchainkit.channels.systems.plasma
   :members:

.. automodule:: blockchainkit.channels.systems.sharding
   :members:

.. automodule:: blockchainkit.channels.systems.rollups
   :members:

Plotting
--------

.. automodule:: blockchainkit.channels.visualizers.plots
   :members:
