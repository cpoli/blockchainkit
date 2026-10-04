"""
Hash time-locked contracts: pay for a secret, or get a refund (2015-2016)
=========================================================================

A hash time-locked contract (HTLC) pays the recipient if they reveal the
preimage of a hash before a deadline, and otherwise lets the sender take
the money back. Peter Todd's ``OP_CHECKLOCKTIMEVERIFY`` (BIP 65, 2015) made
the deadline enforceable in Script, and Poon and Dryja's Lightning Network
(2016) chains HTLCs with the same hash across many channels, so a payment
either completes along the whole route or nowhere.

What to look for
----------------

Bob can claim at any time with the secret, never with a guess. Alice's
refund fails before the deadline and succeeds from it on. Revealing the
secret to claim on one hop is exactly what lets the previous hop claim too.

The history behind this experiment: :doc:`/history/vm_breakthroughs`.
"""

# %%
# Alice pays Bob for the secret behind a hash
# -------------------------------------------
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.crypto import public_key, sha256, sign

alice, bob = public_key(7), public_key(5)
secret = b"invoice 42 preimage"
lock = bk.vm.htlc_locking(sha256(secret), recipient=bob, refund=alice, timeout=500)
tx = b"spend the HTLC output"
claim = (bk.vm.encode_signature(sign(tx, 5, nonce=3)), secret, "OP_TRUE")
guess = (bk.vm.encode_signature(sign(tx, 5, nonce=3)), b"invoice 41", "OP_TRUE")
refund = (bk.vm.encode_signature(sign(tx, 7, nonce=4)), "OP_FALSE")
assert bk.vm.verify_script(claim, lock, message=tx, locktime=10).valid
print(bk.vm.verify_script(guess, lock, message=tx).error)

heights = list(range(480, 521, 4))
refundable = [bk.vm.verify_script(refund, lock, message=tx, locktime=h).valid for h in heights]
claimable = [bk.vm.verify_script(claim, lock, message=tx, locktime=h).valid for h in heights]
assert refundable == [h >= 500 for h in heights] and all(claimable)

# %%
# A two-hop route with one secret
# -------------------------------
# Alice pays Carol through Bob: Alice -> Bob locked until 600, Bob -> Carol
# until 500. Carol claims with the secret, and Bob reuses it before 600.
carol = public_key(11)
hop_bob_carol = bk.vm.htlc_locking(sha256(secret), recipient=carol, refund=bob, timeout=500)
hop_alice_bob = bk.vm.htlc_locking(sha256(secret), recipient=bob, refund=alice, timeout=600)
carol_claim = (bk.vm.encode_signature(sign(tx, 11, nonce=6)), secret, "OP_TRUE")
assert bk.vm.verify_script(carol_claim, hop_bob_carol, message=tx, locktime=450).valid
revealed = carol_claim[1]  # Now public on chain.
bob_claim = (bk.vm.encode_signature(sign(tx, 5, nonce=8)), revealed, "OP_TRUE")
assert bk.vm.verify_script(bob_claim, hop_alice_bob, message=tx, locktime=460).valid

fig, ax = plt.subplots(figsize=(7, 3))
ax.step(heights, claimable, where="post", label="Bob claims with the secret")
ax.step(heights, [0.95 * r for r in refundable], where="post", label="Alice's refund")
ax.axvline(500, color="black", linestyle="--")
ax.set(
    xlabel="block height (lock time)",
    yticks=[0, 1],
    yticklabels=["invalid", "valid"],
    title="HTLC paths",
)
ax.legend(loc="center left")
fig.tight_layout()

# %%
# Exercise
# --------
# Why must the earlier hop (Alice -> Bob) have the *later* timeout? Swap the
# timeouts and describe how Bob could lose money.
