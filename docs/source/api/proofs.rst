blockchainkit.proofs
====================

.. include:: /_generated/nav/proofs.rst

.. automodule:: blockchainkit.proofs
   :no-members:

How a prover convinces a verifier that a computation is correct, cheaply
and without revealing its secrets: polynomial identity testing and
sum-check, interactive proofs and PCPs, Merkle-committed arguments, KZG
commitments, circuits and QAPs, Groth16 and PLONK with their trusted setups,
private payments, and the transparent systems Bulletproofs, FRI, STARKs and
Halo.

Every public name below is re-exported by the subpackage: import it as
``bk.proofs.<name>``. The plotting helpers are the exception: import them
explicitly from ``blockchainkit.proofs.visualizers``, which loads
Matplotlib.

Results
-------

.. automodule:: blockchainkit.proofs.core.base
   :members:

Fields, polynomials and transcripts
-----------------------------------

.. automodule:: blockchainkit.proofs.utils.polynomials
   :members:

.. automodule:: blockchainkit.proofs.utils.transcript
   :members:

.. automodule:: blockchainkit.proofs.utils.groups
   :members:

Interactive proofs
------------------

.. automodule:: blockchainkit.proofs.systems.identity
   :members:

.. automodule:: blockchainkit.proofs.systems.sumcheck
   :members:

.. automodule:: blockchainkit.proofs.systems.ip_pspace
   :members:

PCPs and arguments
------------------

.. automodule:: blockchainkit.proofs.systems.pcp
   :members:

.. automodule:: blockchainkit.proofs.systems.kilian
   :members:

Pairings and polynomial commitments
-----------------------------------

.. automodule:: blockchainkit.proofs.systems.pairing
   :members:

.. automodule:: blockchainkit.proofs.systems.kzg
   :members:

.. automodule:: blockchainkit.proofs.systems.ceremony
   :members:

Circuits and SNARKs
-------------------

.. automodule:: blockchainkit.proofs.systems.circuits
   :members:

.. automodule:: blockchainkit.proofs.systems.qap
   :members:

.. automodule:: blockchainkit.proofs.systems.groth16
   :members:

.. automodule:: blockchainkit.proofs.systems.plonk
   :members:

.. automodule:: blockchainkit.proofs.systems.zerocash
   :members:

Transparent proofs
------------------

.. automodule:: blockchainkit.proofs.systems.bulletproofs
   :members:

.. automodule:: blockchainkit.proofs.systems.fri
   :members:

.. automodule:: blockchainkit.proofs.systems.stark
   :members:

.. automodule:: blockchainkit.proofs.systems.halo
   :members:

Plotting
--------

.. automodule:: blockchainkit.proofs.visualizers.plots
   :members:
