blockchainkit.wallets
=====================

.. include:: /_generated/nav/wallets.rst

.. automodule:: blockchainkit.wallets
   :no-members:

Keys as users actually hold them: check digits and the error-detecting
codes behind Base58Check, Bech32 and Bech32m addresses; PBKDF2 and scrypt,
and the brain wallets that used neither; BIP32 key trees, BIP39 seed
phrases and BIP44 paths; and shared control, from P2SH multisig and
threshold ECDSA to social recovery and ERC-4337 accounts.

Every public name below is re-exported by the subpackage: import it as
``bk.wallets.<name>``. The utilities and the plotting helpers are the
exceptions: import them from ``blockchainkit.wallets.utils`` and
``blockchainkit.wallets.visualizers``, which loads Matplotlib.

Results
-------

.. automodule:: blockchainkit.wallets.core.base
   :members:

Error-detecting codes
---------------------

.. automodule:: blockchainkit.wallets.utils.galois
   :members:

.. automodule:: blockchainkit.wallets.systems.bch
   :members:

.. automodule:: blockchainkit.wallets.systems.check_digits
   :members:

Addresses
---------

.. automodule:: blockchainkit.wallets.utils.ripemd160
   :members:

.. automodule:: blockchainkit.wallets.utils.keys
   :members:

.. automodule:: blockchainkit.wallets.systems.base58
   :members:

.. automodule:: blockchainkit.wallets.systems.bech32
   :members:

Key stretching
--------------

.. automodule:: blockchainkit.wallets.systems.stretching
   :members:

.. automodule:: blockchainkit.wallets.systems.scrypt
   :members:

.. automodule:: blockchainkit.wallets.systems.brainwallets
   :members:

Key derivation
--------------

.. automodule:: blockchainkit.wallets.systems.hd
   :members:

.. automodule:: blockchainkit.wallets.systems.mnemonics
   :members:

.. automodule:: blockchainkit.wallets.systems.paths
   :members:

Shared control
--------------

.. automodule:: blockchainkit.wallets.systems.p2sh
   :members:

.. automodule:: blockchainkit.wallets.systems.ecdsa
   :members:

.. automodule:: blockchainkit.wallets.systems.threshold
   :members:

.. automodule:: blockchainkit.wallets.systems.social_recovery
   :members:

.. automodule:: blockchainkit.wallets.systems.account_abstraction
   :members:

Plotting
--------

.. automodule:: blockchainkit.wallets.visualizers.plots
   :members:
