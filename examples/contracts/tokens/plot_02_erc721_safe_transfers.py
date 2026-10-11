r"""
ERC-721 non-fungible tokens and safe transfers (2018)
=====================================================

ERC-721, by William Entriken, Dieter Shirley, Jacob Evans and Nastassia
Sachs, gave each token an identity: a mapping from token ids to owners,

.. math::

   \mathrm{owner}: \mathrm{id} \mapsto \mathrm{address}, \qquad
   \mathrm{balance}(a) = |\{\mathrm{id} : \mathrm{owner}(\mathrm{id}) = a\}|,

so that collectibles, game items and deeds could be owned and traded like
coins. CryptoKitties had shown the demand in late 2017.

A token sent to a contract that has no code to move it is locked forever.
``safeTransferFrom`` therefore calls ``onERC721Received`` on a contract
recipient and reverts unless the recipient answers with the agreed value.
Here a plain ``transfer_from`` to a token contract strands an NFT, while
``safe_transfer_from`` refuses the same transfer and delivers to a vault
that knows how to hold and send tokens.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk

# %%
# Mint, then send to three kinds of recipient
# -------------------------------------------

world = bk.contracts.World()
nft = world.deploy("artist", bk.contracts.ERC721, name="kitties")
for token_id in range(1, 5):
    world.transact("artist", nft, "mint", "alice", token_id)
stranger = world.deploy("someone", bk.contracts.ERC20, 1, name="a token contract")
vault = world.deploy("alice", bk.contracts.NFTVault, name="vault")

attempts = {
    "transfer_from\nto token contract": ("transfer_from", stranger, 1),
    "safe_transfer_from\nto token contract": ("safe_transfer_from", stranger, 2),
    "safe_transfer_from\nto vault": ("safe_transfer_from", vault, 3),
    "safe_transfer_from\nto a person": ("safe_transfer_from", "bob", 4),
}
results = {}
for label, (function, to, token_id) in attempts.items():
    receipt = world.transact("alice", nft, function, "alice", to, token_id)
    owner = world.name(world.view(nft, "owner_of", token_id))
    results[label] = (receipt.success, owner)
    print(f"{label.replace(chr(10), ' '):40s} success={receipt.success} owner={owner}")

assert results["transfer_from\nto token contract"] == (True, "a token contract")
assert results["safe_transfer_from\nto token contract"] == (False, "alice")
assert world.transact("alice", vault, "send_token", nft, "carol", 3).success
assert world.view(nft, "owner_of", 3) == "carol"  # The vault can move what it holds.

fig, ax = plt.subplots(figsize=(9, 3.8))
colors = {"a token contract": "#dc2626", "alice": "#64748b", "vault": "#16a34a", "bob": "#16a34a"}
for row, (success, owner) in enumerate(results.values()):
    ax.barh(row, 1, color=colors[owner])
    verdict = (
        "delivered"
        if success and owner != "a token contract"
        else ("stuck forever" if success else "refused: stays with alice")
    )
    ax.text(0.03, row, f"{verdict} (owner: {owner})", va="center", color="white")
ax.set_yticks(range(len(results)), list(results))
ax.set(xticks=[], title="Where token ids 1-4 ended up")
ax.invert_yaxis()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# ``safe_transfer_from`` calls the recipient *after* updating ownership. The
# recipient's hook can call back into the NFT contract. Write a receiver
# whose ``on_erc721_received`` tries to transfer the token onward at once:
# does it work, and why is a callback in the middle of a transfer the same
# risk as the DAO's reentrancy?
