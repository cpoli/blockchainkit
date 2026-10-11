r"""
BTC Relay: a Bitcoin light client in an Ethereum contract (2016)
================================================================

An Ethereum contract cannot see Bitcoin. BTC Relay let it check Bitcoin
payments the way a light client does: relayers submit block headers, the
contract checks that each links to a stored one and meets its proof-of-work
target, and it follows the chain with the most work. A contract can then
verify that a transaction is in a block of that chain under ``c``
confirmations, with a Merkle proof against the header's root. Each header
adds expected work

.. math::

   W = \sum_{\text{headers}} 2^{\text{difficulty}},

and the relay trusts whichever chain has the most of it, so it is exactly
as safe as the work an attacker cannot match.
"""

# %%
import matplotlib.pyplot as plt

import blockchainkit as bk
from blockchainkit.contracts import World
from blockchainkit.structures import MerkleTree

# %%
# Relaying headers and verifying a payment
# ----------------------------------------

world = World()
genesis = bk.channels.mine_header(None, [b"genesis"])
relay = world.deploy("deployer", bk.channels.BTCRelay, genesis, 8, name="BTC Relay")

payment = b"alice pays bob 0.5 BTC"
payloads = [b"coinbase 1", payment, b"carol pays dave"]
headers, gas = [bk.channels.mine_header(genesis, payloads, timestamp=1)], []
for i in range(5):
    headers.append(bk.channels.mine_header(headers[-1], [f"coinbase {i + 2}".encode()]))
proof = MerkleTree(payloads).proof(1)
honest_confirmations = []
for header in headers:
    gas.append(world.transact("relayer", relay, "store_header", header).gas_used)
    honest_confirmations.append(world.view(relay, "confirmations", headers[0].hash))
assert world.view(relay, "verify_transaction", payment, headers[0].hash, proof, 6)
print("gas per header:", gas[0])

# %%
# Cheap headers are refused, heavier forks win
# --------------------------------------------
# A fork mined at difficulty 2 costs almost nothing and is rejected. A fork
# at full difficulty that outgrows the honest chain replaces it, and the
# payment loses its confirmations.

cheap = bk.channels.mine_header(genesis, [b"double spend"], difficulty=2)
assert world.transact("attacker", relay, "store_header", cheap).error == "difficulty too low"
fork = [bk.channels.mine_header(genesis, [b"double spend"], timestamp=2)]
attack_confirmations = []
for i in range(7):
    world.transact("attacker", relay, "store_header", fork[-1])
    attack_confirmations.append(world.view(relay, "confirmations", headers[0].hash))
    fork.append(bk.channels.mine_header(fork[-1], [f"attacker {i}".encode()]))
assert attack_confirmations[-1] == 0
assert not world.view(relay, "verify_transaction", payment, headers[0].hash, proof, 1)

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(range(1, 7), honest_confirmations, "o-", color="#16a34a", label="honest headers")
ax.plot(range(7, 14), attack_confirmations, "s-", color="#dc2626", label="attacker's fork")
ax.set(xlabel="headers submitted", ylabel="confirmations of Alice's payment")
ax.set_title("The relay follows the most work, whoever mined it")
ax.legend()
fig.tight_layout()

plt.show()

# %%
# Exercise
# --------
# A contract releasing ether against a relayed Bitcoin payment asks for
# ``c`` confirmations. If an attacker has a fraction ``q`` of Bitcoin's
# hashrate, use :func:`~blockchainkit.consensus.systems.catch_up.attacker_success_probability`
# to choose ``c`` for a payment worth 100 block rewards.
