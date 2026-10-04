blockchainkit.network
=====================

.. include:: /_generated/nav/network.rst

.. automodule:: blockchainkit.network
   :no-members:

Peer graphs, logical clocks, gossip and reliable broadcast, replication under partitions, Kademlia
and its attacks, block relay, forks, and transaction privacy.

Every public name below is re-exported by the subpackage: import it as
``bk.network.<name>``. The plotting helpers are the exception: import them
explicitly from ``blockchainkit.network.visualizers``, which loads Matplotlib.

Types and results
-----------------

.. automodule:: blockchainkit.network.core.base
   :members:

Constructions and protocols
---------------------------

.. automodule:: blockchainkit.network.systems.gossip
   :members:

.. automodule:: blockchainkit.network.systems.topology
   :members:

.. automodule:: blockchainkit.network.systems.clocks
   :members:

.. automodule:: blockchainkit.network.systems.epidemics
   :members:

.. automodule:: blockchainkit.network.systems.broadcast
   :members:

.. automodule:: blockchainkit.network.systems.replication
   :members:

.. automodule:: blockchainkit.network.systems.kademlia
   :members:

.. automodule:: blockchainkit.network.systems.addresses
   :members:

.. automodule:: blockchainkit.network.systems.relay
   :members:

.. automodule:: blockchainkit.network.systems.propagation
   :members:

.. automodule:: blockchainkit.network.systems.privacy
   :members:

Plotting
--------

.. automodule:: blockchainkit.network.visualizers.plots
   :members:
