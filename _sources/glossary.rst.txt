Glossary
========

These definitions describe how terms are used in this course.

.. glossary::
   :sorted:

   Account
      An identifier associated with a balance and a payment sequence number.

   API
      The functions and classes a package offers to your Python programs.

   Block
      A batch of records with metadata, including a link to its predecessor.
      The first block is called the genesis block.

   Byte
      Eight bits. A bit is a single binary digit, either zero or one.

   Commitment
      A value published now that can later be checked against a revealed
      message. A cryptographic commitment aims to prevent changing the message
      while hiding it until it is revealed.

   Consensus
      Rules and a process for participants to agree on accepted updates.

   Deterministic
      Producing the same result from the same inputs under the same rules.

   Digital signature
      Evidence that a message was authorized using a particular private key,
      which others can check with the corresponding public key.

   Discrete logarithm
      Reversing a group exponentiation: recovering the secret exponent from
      the public result. Carefully chosen large groups make this difficult.

   Double spending
      Attempting conflicting payments using the same available funds.

   Encryption
      Transforming readable information into a form recoverable using a key.

   Finality
      An assurance that an accepted update will not be reversed, under a
      protocol's assumptions. This package provides no unconditional finality.

   Finite field
      A finite set with addition, subtraction, multiplication, and division
      by nonzero elements. Arithmetic modulo a prime is one example.

   Fork
      Competing continuations of a blockchain. Here this means a split in
      history, rather than a software upgrade.

   Gas
      A budget for program execution. This teaching VM charges one unit per
      instruction; these units are not money.

   Gossip
      Spreading an announcement by having peers pass it to neighbors.

   Group
      A set with a combining operation, an identity, and inverses, where
      regrouping operations does not change the result. Curve points form
      a group under a specially defined addition rule.

   Hash
   Digest
      A fixed-length fingerprint computed from data. Different inputs can
      share an output, but a secure hash makes finding such pairs difficult.

   Ledger
      Accounting state, such as balances, derived from accepted payments.

   Merkle tree
      A tree of hashes that summarizes a collection in a single root hash.
      A Merkle proof contains the information needed to check one item's
      membership without sending the entire collection.

   Modulo
      Arithmetic that keeps the remainder after division. For example,
      ``17 % 5`` is 2 in Python. The mathematical notation is “mod 5”.

   Nonce
      A value with a special one-use or changing role. An account nonce orders
      payments, a mining nonce is varied during a search, and a signing nonce
      must be secret and fresh. These are different requirements.

   Partition
      A break in connectivity that prevents some peers from communicating.

   Peer
      A participating computer, represented here by a simulated object.

   Prime
      An integer greater than one divisible only by itself and one.

   Private key
   Public key
      Related values: the private key is kept secret, while the public key
      can be shared to let others check signatures.

   Proof of stake
      A family of designs that gives participants influence based on stake.
      This package demonstrates only a weighted proposer lottery.

   Proof of work
      A result that is costly to find but cheap to check, used here as one
      ingredient in choosing between valid histories.

   Protocol
      The agreed rules for exchanging and interpreting information.

   Reorganization
      Switching the selected history to a competing branch and updating
      the corresponding ledger state.

   Replay
      Reusing an earlier message, for example trying to apply a payment twice.

   Salt
      Extra input to a hash. Its requirements depend on the application:
      in this course's commitment example it must remain secret until opening.

   Seed
      A starting value used to reproduce a sequence of simulated random choices.

   Serialization
      Turning structured data into bytes using a precise, repeatable format.

   State
      The current stored information, such as balances or program storage.

   Virtual machine
      A program that executes instructions according to specified rules.
      This one uses a stack: values are added and removed at one end.

   Zero knowledge
      A precise property of a proof protocol: the verifier gains no additional
      knowledge beyond the claim's validity, under stated assumptions.
