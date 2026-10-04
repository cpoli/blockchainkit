Exercise solutions and explanations
===================================

Try the exercises before reading this page. These are worked answers, not
additional prerequisites. Each code block below is checked by Sphinx. They
use fresh local values rather than relying on notebook variables. All amounts
and keys are teaching fixtures. See :doc:`course` for the suggested order.

1. Public keys: recovering a tiny secret
----------------------------------------

.. doctest::

   >>> group = bk.crypto.DHGroup()
   >>> public = group.public(3)
   >>> [x for x in range(1, group.q) if group.public(x) == public]
   [3]

Enumeration works because the group is tiny. Increasing its size changes the
cost dramatically; the plot's appearance does not measure resistance to an
attack. Public exchange also needs authentication to prevent key substitution.

2. Secret sharing: forged shares
--------------------------------

.. doctest::

   >>> from random import Random
   >>> shares = bk.crypto.split_secret(42, 3, 5, randbelow=Random(7).randrange)
   >>> bk.crypto.recover_secret(shares[:3])
   42
   >>> altered = [(shares[0][0], (shares[0][1] + 1) % 2089), *shares[1:3]]
   >>> bk.crypto.recover_secret(altered) != 42
   True

Interpolation still produces an answer. Authenticating shares can detect
changes in transit; detecting a dealer's inconsistent shares requires a
verifiable sharing scheme with additional commitments or proofs.

3. Merkle proofs: position and size matter
------------------------------------------

.. doctest::

   >>> from dataclasses import replace
   >>> tree = bk.structures.MerkleTree([b"a", b"b", b"c"])
   >>> proof = tree.proof(1)
   >>> bk.structures.verify_proof(b"b", replace(proof, index=0), tree.root)
   False
   >>> bk.structures.verify_proof(b"b", replace(proof, leaf_count=4), tree.root)
   False

Neither a trusted root nor a valid proof checks a signature, a balance, or
agreement on the selected history. Follow the gallery's trace to see where
ordering and the leaf count enter the root calculation.

4. Blind signatures: removing the mask
--------------------------------------

.. doctest::

   >>> key = bk.crypto.rsa_keypair()
   >>> from math import gcd
   >>> gcd(61, key.n)
   61
   >>> try:
   ...     bk.crypto.rsa_blind(42, 61, key)
   ... except ValueError:
   ...     print("No invertible mask")
   No invertible mask

An inverse exists only when the factor and modulus are coprime. Blinding
changes what the signer can see; preventing repeated spending still requires
tracking spent tokens or another explicit double-spending mechanism.

5. Curves: group identities
---------------------------

.. doctest::

   >>> curve = bk.crypto.TOY_CURVE
   >>> g = curve.generator
   >>> bk.crypto.add(g, bk.crypto.multiply(-1, g, curve), curve) is None
   True
   >>> bk.crypto.multiply(7, g, curve) == bk.crypto.add(
   ...     bk.crypto.multiply(3, g, curve), bk.crypto.multiply(4, g, curve), curve)
   True

Coordinates are finite-field elements, hence isolated points. Double-and-add
branches on scalar bits and loops over their length; this implementation does
not provide constant-time handling of private values.

6. Schnorr: reused nonces
-------------------------

Subtracting s2 = k + c2*x from s1 = k + c1*x cancels k. Dividing by c1-c2
modulo the prime group order recovers x. Equal challenges give no invertible
difference and therefore do not permit this calculation.

.. doctest::

   >>> curve = bk.crypto.TOY_CURVE
   >>> public = bk.crypto.public_key(7, curve)
   >>> first = bk.crypto.sign(b"a", 7, nonce=3, curve=curve)
   >>> c1 = bk.crypto.challenge(b"a", first.commitment, public, curve)
   >>> messages = [str(i).encode() for i in range(100)]
   >>> message = next(m for m in messages if bk.crypto.challenge(m, first.commitment, public, curve) != c1)
   >>> second = bk.crypto.sign(message, 7, nonce=3, curve=curve)
   >>> c2 = bk.crypto.challenge(message, second.commitment, public, curve)
   >>> bk.crypto.recover_reused_nonce_key(first, second, c1, c2, curve.order)
   7

An honest-verifier transcript can be simulated by choosing challenge and
response first. That explains why showing a transcript differs from answering
a fresh challenge after committing. This is one specific proof relation;
it neither implements arbitrary proof circuits nor the BIP-340 encoding.

7. Hashes: a deliberately shortened digest
------------------------------------------

.. doctest::

   >>> seen = {}
   >>> for i in range(257):
   ...     short = bk.crypto.sha256(str(i).encode())[0]
   ...     if short in seen:
   ...         collision = (seen[short], i)
   ...         break
   ...     seen[short] = i
   >>> collision[0] != collision[1]
   True
   >>> bk.crypto.sha256(str(collision[0]).encode())[0] == bk.crypto.sha256(str(collision[1]).encode())[0]
   True

There are only 256 possible first bytes, so 257 distinct inputs guarantee a
collision. Under uniform hashing the first collision typically takes on the
order of the square root of 256 trials, not 256. This tests an 8-bit truncation,
not a collision in the full 256-bit hash. Guessable unsalted bids can be tried
one by one; a secret unpredictable salt prevents that simple lookup.

8. Mining: average versus typical cost
--------------------------------------

.. doctest::

   >>> from statistics import mean, median
   >>> attempts = [bk.consensus.mine(bk.structures.Block(difficulty=4, timestamp=i)).attempts for i in range(100)]
   >>> mean(attempts) >= 1 and median(attempts) >= 1
   True
   >>> bk.consensus.expected_trials(4)
   16

Compare the sample mean and median yourself; they need not coincide or equal
16. Under the independent uniform-hash model the geometric distribution has
a long right tail, so the mean exceeds the population median. More trials
improve estimation without guaranteeing monotonic convergence. Keep timeouts
in your analysis rather than discarding slow searches. The catch-up helper
models an infinite horizon and excludes network delays.

9. Gossip: redundant routes and broken links
--------------------------------------------

.. doctest::

   >>> net = bk.network.SimulatedNetwork(["a", "b", "c"], seed=7)
   >>> for left, right in [("a", "b"), ("b", "c"), ("c", "a")]:
   ...     net.connect(left, right, latency=(2, 4))
   >>> net.broadcast("a", b"news")
   >>> net.disconnect("a", "b")
   >>> _ = net.run()
   >>> sorted(d.recipient for d in net.deliveries)
   ['a', 'b', 'c']

The direct in-flight message to b is dropped, but the route through c remains.
Each peer accepts the payload once. Recreate the same graph and operations
with seed 7 to reproduce times; changing the seed can change delays, but need
not change every result. A disconnected peer with no alternate route cannot
receive the message until a later explicit retransmission.

10 and 13. Reorganization, reinclusion, and conflict
----------------------------------------------------

The lifecycle notebook checks actual reinclusion in a new mined block. Here
we isolate its accounting rule: a displaced payment is eligible against a
state that has not spent its nonce; after applying it, replay fails.

.. doctest::

   >>> public = bk.crypto.public_key(7)
   >>> alice = bk.structures.address(public)
   >>> bob = bk.structures.address(bk.crypto.public_key(11))
   >>> initial = bk.structures.Ledger({alice: 100})
   >>> payment = bk.structures.Transaction(public, bob, 25, 0).signed(7, signing_nonce=17)
   >>> paid = initial.apply([payment])
   >>> paid.balances[bob]
   25
   >>> try:
   ...     paid.apply([payment])
   ... except ValueError as error:
   ...     print("nonce" in str(error))
   True
   >>> replace(payment, chain_id="another-network").is_valid()
   False
   >>> conflict = bk.structures.Transaction(public, bob, 100, 0).signed(7, signing_nonce=19)
   >>> competing_state = initial.apply([conflict])
   >>> try:
   ...     competing_state.apply([payment])
   ... except ValueError as error:
   ...     print("nonce" in str(error))
   True

The conflict consumed the same account nonce and all funds. The original
payment must not return to the eligible queue even though its signature still
verifies. Changing a chain ID changes the signed message. A newly signed
payment for that other chain still fails this ledger's chain-ID check.

11. Stake: splitting names does not create weight
-------------------------------------------------

.. doctest::

   >>> stakes = {"alice": 10, "bob": 30, **{f"carol-{i}": 6 for i in range(10)}}
   >>> sum(weight for name, weight in stakes.items() if name.startswith("carol-")) / sum(stakes.values())
   0.6

The aggregate expected probability stays 60%; finite samples fluctuate. A
selected proposer can still propose conflicting blocks. Voting and selection
rules must resolve that conflict. A known seed makes future selections
predictable; allowing someone to choose among seeds also permits bias.

12. Execution: branch outcomes and failure
------------------------------------------

.. doctest::

   >>> def comparison(left, right):
   ...     return [("PUSH", left), ("PUSH", right), ("EQ", None), ("JZ", 7),
   ...             ("PUSH", 10), ("STORE", 0), ("STOP", None),
   ...             ("PUSH", 20), ("STORE", 0), ("STOP", None)]
   >>> bk.vm.execute(comparison(3, 3)).storage[0]
   10
   >>> bk.vm.execute(comparison(3, 4)).storage[0]
   20
   >>> bk.vm.execute([("PUSH", 0), ("PUSH", 1), ("SUB", None)]).stack == (2**256 - 1,)
   True
   >>> try:
   ...     bk.vm.execute([("ADD", None)])
   ... except bk.vm.VMError:
   ...     print("Stack underflow rejected")
   Stack underflow rejected

The rightmost stack item is the top. Intermediate storage is working state;
a failure before successful completion leaves the caller's input unchanged.
``execute(..., trace=True)`` records the state after every executed
instruction, following jumps, so the same trace works for branches and loops.
