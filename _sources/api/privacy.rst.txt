blockchainkit.privacy
=====================

.. include:: /_generated/nav/privacy.rst

.. automodule:: blockchainkit.privacy
   :no-members:

Anonymity and confidentiality on public ledgers: what a ledger reveals,
measured by anonymity sets, address clustering and ring tracing, and the
techniques that hide senders, receivers and amounts, from mix-nets and
ring signatures to confidential transactions, Mimblewimble and a mixer
contract.

Every public name below is re-exported by the subpackage: import it as
``bk.privacy.<name>``. The plotting helpers are the exception: import them
explicitly from ``blockchainkit.privacy.visualizers``, which loads
Matplotlib.

Results
-------

.. automodule:: blockchainkit.privacy.core.base
   :members:

Anonymous networks and anonymity sets
-------------------------------------

.. automodule:: blockchainkit.privacy.systems.mixnets
   :members:

.. automodule:: blockchainkit.privacy.systems.onion
   :members:

.. automodule:: blockchainkit.privacy.systems.anonymity
   :members:

Ring signatures and stealth addresses
-------------------------------------

.. automodule:: blockchainkit.privacy.systems.ring_signatures
   :members:

.. automodule:: blockchainkit.privacy.systems.linkable
   :members:

.. automodule:: blockchainkit.privacy.systems.stealth
   :members:

Tracing a ledger
----------------

.. automodule:: blockchainkit.privacy.systems.clustering
   :members:

.. automodule:: blockchainkit.privacy.systems.traceability
   :members:

Mixing coins
------------

.. automodule:: blockchainkit.privacy.systems.coinjoin
   :members:

.. automodule:: blockchainkit.privacy.systems.tumblebit
   :members:

.. automodule:: blockchainkit.privacy.systems.tornado
   :members:

Hidden coins and amounts
------------------------

.. automodule:: blockchainkit.privacy.systems.zerocoin
   :members:

.. automodule:: blockchainkit.privacy.systems.confidential
   :members:

.. automodule:: blockchainkit.privacy.systems.ringct
   :members:

.. automodule:: blockchainkit.privacy.systems.mimblewimble
   :members:

Group helpers
-------------

.. automodule:: blockchainkit.privacy.utils.groups
   :members:

Plotting
--------

.. automodule:: blockchainkit.privacy.visualizers.plots
   :members:
