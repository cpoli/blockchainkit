r"""
Grigg's Ricardian contracts: a bond whose terms are its name (1996)
===================================================================

Ian Grigg designed the Ricardian contract to issue bonds and currencies on
the Ricardo payment system. One document is both a legal contract a person
can read and a set of parameters a program can parse. The issuer signs it,
and its hash becomes the instrument's identifier:

.. math::

   \mathrm{id} = H(\mathrm{prose} \,\|\, \mathrm{parameters}).

Every payment cites the identifier, so there is never a question which
terms a payment was made under. Change one word of the prose and the hash,
and so the instrument, changes. Here a token is issued under a signed bond:
the supply comes from the same document the holder reads, payments citing
the terms go through, and payments citing an edited version are refused.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Write, sign and issue
# ---------------------

ISSUER_KEY = 7  # A fixed teaching key: never use such a key for real money.
terms = (
    "The issuer will pay the holder of each of the {supply} units a coupon of "
    "{coupon}% a year until {maturity}, then redeem it at par."
)
bond = bk.contracts.ricardian_contract(
    terms, {"supply": 1_000, "coupon": 5, "maturity": "2030-12-31"}, ISSUER_KEY
)
print(bond.rendered)
print("identifier", bond.identifier[:16], "...", "signed:", bk.contracts.verify_ricardian(bond))
assert bk.contracts.verify_ricardian(bond)

world = bk.contracts.World()
token = world.deploy(
    "issuer", bk.contracts.RicardianToken, bond.identifier, bond.parameters["supply"]
)
assert world.view(token, "total_supply") == 1_000
paid = world.transact("issuer", token, "transfer_under", bond.identifier, "holder", 10)
assert paid.success

# %%
# One word changes the instrument
# -------------------------------

edited = terms.replace("will pay", "may pay")
edited_id = bk.contracts.ricardian_digest(edited, bond.parameters).hex()
refused = world.transact("issuer", token, "transfer_under", edited_id, "holder", 10)
print("payment under edited terms:", refused.error)
assert refused.error == "payment cites different terms"
assert world.view(token, "balance_of", "holder") == 10

# A digest that does not match its prose fails verification.
tampered = type(bond)(edited, bond.parameters, bond.issuer, bond.signature, bond.digest)
assert not bk.contracts.verify_ricardian(tampered)

words = terms.split()
changed_bits = []
for index in range(len(words)):
    variant = " ".join(words[:index] + [words[index] + "s"] + words[index + 1 :])
    digest = bk.contracts.ricardian_digest(variant, bond.parameters)
    changed_bits.append(bk.crypto.hamming_distance(digest, bond.digest))
assert min(changed_bits) > 90

fig, ax = plt.subplots(figsize=(8, 3.5))
ax.bar(range(len(words)), changed_bits, color="#2563eb")
ax.axhline(128, color="#dc2626", linestyle="--", label="half of 256 bits")
ax.set(
    xlabel="word edited (an 's' appended)",
    ylabel="identifier bits changed",
    title="Any edit to the prose renames the instrument",
)
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# The parameters are hashed with the prose. Show that changing only the
# coupon, without touching the text, also changes the identifier. Why must
# the parameters be inside the signed document rather than stored only in
# the token contract?
