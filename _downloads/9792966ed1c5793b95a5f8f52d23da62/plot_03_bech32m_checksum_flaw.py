r"""
Bech32m and the insertion flaw in Bech32 (BIP350, 2020)
=======================================================

In 2019 it was found that Bech32 has a blind spot: when a string ends in
``p``, inserting or deleting ``q`` characters just before that ``p`` leaves
the checksum valid. ``q`` is the value 0, and ``p`` is 1, the constant the
checksum must leave, so the extra zeros multiply the polynomial by powers
of x without changing its remainder. Witness version 0 survives, because
its programs must be 20 or 32 bytes, but Taproot's version 1 and later
allow other lengths. Pieter Wuille's Bech32m changes only the constant,

.. math::

   \mathrm{polymod}(\dots) = \texttt{0x2bc830a3},

and is required from witness version 1 on.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# A string ending in p
# --------------------


def ending_in_p(encoding):
    for n in range(1_000):
        data = [n % 32, n // 32 % 32, 7, 3, 1]
        text = bk.wallets.bech32_encode("bc", data, encoding)
        if text.endswith("p"):
            return text
    raise ValueError("no string found")


def accepts(text):
    try:
        bk.wallets.bech32_decode(text)
    except ValueError:
        return False
    return True


original = ending_in_p("bech32")
print("original:", original)
inserted = {}
for encoding in ("bech32", "bech32m"):
    text = ending_in_p(encoding)
    inserted[encoding] = [accepts(text[:-1] + "q" * k + "p") for k in range(1, 9)]
    print(f"{encoding:8} with 1..8 q's inserted:", inserted[encoding])
assert all(inserted["bech32"]) and not any(inserted["bech32m"])

# %%
# Why version 0 was safe
# ----------------------

program = bytes(20)
v0 = bk.wallets.segwit_encode("bc", 0, program)
assert bk.wallets.segwit_decode("bc", v0).program == program
taproot = bk.wallets.segwit_encode("bc", 1, bytes(32))
print("version 0:", v0)
print("version 1:", taproot, bk.wallets.bech32_decode(taproot).encoding)

fig, ax = plt.subplots(figsize=(6, 4))
k = list(range(1, 9))
ax.plot(k, inserted["bech32"], "o-", color="#dc2626", label="Bech32")
ax.plot(k, inserted["bech32m"], "o-", color="#2563eb", label="Bech32m")
ax.set(
    xlabel="q characters inserted before the final p",
    ylabel="accepted",
    yticks=[0, 1],
    yticklabels=["no", "yes"],
)
ax.set_title("A new constant closes the insertion hole")
ax.legend()
fig.tight_layout()
plt.show()

# %%
# Exercise
# --------
# Does deleting a ``q`` before a final ``p`` fool Bech32 too? Find a string
# ending in ``qp`` and try.
# A worked solution is in :doc:`/exercises/wallets`.
