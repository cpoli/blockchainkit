r"""Balance probing in Lightning (Herrera-Joancomartí et al., 2019).

A channel announces its capacity but keeps secret how it is split, which
hides how much each party has paid the other. Herrera-Joancomartí and
co-authors showed the split leaks to anyone with a channel. The prober
sends a payment through the target channel to its far end with a random
payment hash that nobody can claim. If the hop cannot forward the amount,
the error comes back from it, ``temporary_channel_failure``; if it can, the
payment reaches the recipient and fails there, ``unknown_payment_hash``.
Either way no money moves and the prober pays nothing, and a binary search
pins the balance down in

.. math::

   \lceil \log_2 (C + 1) \rceil

probes for a channel of capacity :math:`C`.
"""

from blockchainkit.channels.core.base import ProbeResult
from blockchainkit.channels.systems.routing import ChannelNetwork


def probe_balance(network: ChannelNetwork, prober: int, u: int, v: int) -> ProbeResult:
    """Find ``u``'s balance toward ``v`` by sending unclaimable payments ``prober -> u -> v``.

    Parameters
    ----------
    network : ChannelNetwork
        The prober must have a channel with ``u``, with enough balance on its side.
    prober, u, v : int
        Nodes; ``u`` and ``v`` share the target channel.

    Returns
    -------
    ProbeResult
        Narrowed to a single value unless the prober's own channel runs out first.

    Examples
    --------
    >>> from blockchainkit.channels import ChannelNetwork, probe_balance
    >>> from blockchainkit.network import Graph
    >>> graph = Graph(3, [(0, 1), (1, 2)])
    >>> network = ChannelNetwork(graph, {(0, 1): 5_000, (1, 0): 0, (1, 2): 618, (2, 1): 382})
    >>> probe_balance(network, 0, 1, 2)
    ProbeResult(low=618, high=618, probes=10)
    """
    low, high, probes = 0, network.capacity(u, v), 0
    while low < high:
        amount = (low + high + 1) // 2
        attempt = network.send(network.route((prober, u, v), amount), known_hash=False)
        probes += 1
        if attempt.failed_at == (u, v):
            high = amount - 1
        elif attempt.error == "unknown_payment_hash":
            low = amount
        else:  # The prober's own channel could not carry the probe.
            break
    return ProbeResult(low, high, probes)
