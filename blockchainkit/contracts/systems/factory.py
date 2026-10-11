"""CREATE2 and counterfactual addresses (EIP-1014, 2019).

``CREATE`` derives a new contract's address from the deployer and its nonce,
so the address depends on everything the deployer did before. ``CREATE2``
derives it from the deployer, a chosen salt and the hash of the creation
code alone:

    address = H(0xff || deployer || salt || H(init_code))[12:]

The address is therefore known, and can receive funds, before the contract
exists: it is *counterfactual*. State channels and smart-contract wallets
rely on this: a wallet is deployed only when it is first needed, by
whoever pays for it, at the address its owner has already been using.
"""

from blockchainkit.contracts.systems.world import Contract, create2_address


class Forwarder(Contract):
    """A minimal wallet that sends everything it holds to its owner."""

    layout = ("owner",)

    def constructor(self, owner: str) -> None:
        self.write("owner", owner)

    def receive(self) -> None:
        pass

    def sweep(self) -> int:
        """Send the whole balance to the owner; anyone may call it."""
        amount = self.ether_balance()
        self.call(self.read("owner"), None, value=amount)
        return amount


class Factory(Contract):
    """Deploys :class:`Forwarder` wallets with CREATE2."""

    layout = ()

    def predict(self, salt: int, owner: str) -> str:
        """The address :meth:`deploy` will use for ``salt`` and ``owner``."""
        return create2_address(self.address, salt, Forwarder, owner)

    def deploy(self, salt: int, owner: str) -> str:
        """Deploy a forwarder for ``owner`` at its predicted address."""
        return self.create(Forwarder, owner, salt=salt)
