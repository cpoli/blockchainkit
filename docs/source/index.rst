blockchainkit
=============

**Cryptography and blockchains, understood through experiments.**

Start with two people agreeing on a secret. Follow the ideas that make it
possible to prove knowledge, authenticate a payment, commit to a history,
compare competing histories, and execute a shared program. Each step links
an explanation to working Python, a figure, and an experiment you can change.

The :doc:`history` is the spine of this package. It traces the breakthroughs
and their limitations rather than treating a blockchain as an unexplained
collection of classes. Cryptography is central even though it is not in the
package name. The design follows physicskit's history-to-code teaching style.

**New to the topic?** Begin with :doc:`start_here`. It explains the ideas
using one imaginary payment, without assuming cryptography or finance knowledge.
Keep the :doc:`glossary` nearby; equations can wait until a second reading.

Follow :doc:`course` for a sequenced learning path with objectives, checkpoints,
and :doc:`solutions`. The capstone follows a payment through its entire lifecycle.

Choose a route
--------------

* **Learn the ideas:** read :doc:`history`, then work through the linked notebooks.
* **Build a chain:** follow :doc:`quickstart` and the end-to-end payment experiment.
* **Run simulations:** read :doc:`simulation` for assumptions and reproducibility.
* **Inspect the implementation:** browse :doc:`api` and :doc:`protocol`.

``import blockchainkit`` loads only the standard library. NumPy and Matplotlib
are installed with the package for each subpackage's plotting helpers in
``visualizers``; Sphinx builds the documentation and gallery.
This is a teaching and simulation package, not hardened cryptographic software
or a node compatible with an existing blockchain.

.. toctree::
   :maxdepth: 2

   start_here
   quickstart
   course
   solutions
   history
   gallery/index
   glossary
   simulation
   protocol
   api
   references
   contributing
