blockchainkit.fraud
===================

.. include:: /_generated/nav/fraud.rst

.. automodule:: blockchainkit.fraud
   :no-members:

How people are defrauded on and around blockchains, and how to tell:
Ponzi schemes and their payout patterns, Benford's law, proofs of reserves,
liabilities and solvency, custodians that lose or lend their customers'
coins, scam contracts whose source deceives the reader, price manipulation
and pump-and-dumps, wash trading, approval phishing, and address poisoning.

Every public name below is re-exported by the subpackage: import it as
``bk.fraud.<name>``. The plotting helpers are the exception: import them
explicitly from ``blockchainkit.fraud.visualizers``, which loads
Matplotlib.

Results
-------

.. automodule:: blockchainkit.fraud.core.base
   :members:

Ponzi schemes and fabricated figures
------------------------------------

.. automodule:: blockchainkit.fraud.systems.ponzi
   :members:

.. automodule:: blockchainkit.fraud.systems.benford
   :members:

Reserves, liabilities and custodians
------------------------------------

.. automodule:: blockchainkit.fraud.utils.merkle_sum
   :members:

.. automodule:: blockchainkit.fraud.systems.reserves
   :members:

.. automodule:: blockchainkit.fraud.systems.provisions
   :members:

.. automodule:: blockchainkit.fraud.systems.custody
   :members:

Scam contracts
--------------

.. automodule:: blockchainkit.fraud.systems.verification
   :members:

.. automodule:: blockchainkit.fraud.systems.token_sales
   :members:

.. automodule:: blockchainkit.fraud.systems.honeypots
   :members:

.. automodule:: blockchainkit.fraud.systems.rug_pulls
   :members:

Manipulation
------------

.. automodule:: blockchainkit.fraud.systems.manipulation
   :members:

.. automodule:: blockchainkit.fraud.systems.wash_trading
   :members:

Phishing
--------

.. automodule:: blockchainkit.fraud.systems.phishing
   :members:

.. automodule:: blockchainkit.fraud.systems.poisoning
   :members:

Plotting
--------

.. automodule:: blockchainkit.fraud.visualizers.plots
   :members:
