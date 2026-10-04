"""Regenerate the README's per-subpackage teaser figures.

    python docs/make_readme_subpackage_figures.py              # all subpackages
    python docs/make_readme_subpackage_figures.py crypto vm    # just these

Writes docs/source/_static/images/readme_<subpackage>.png, three panels each,
at the same size as readme_hero.png (see make_readme_figure.py). README.md
embeds them by their raw.githubusercontent.com URLs so they also render on PyPI.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import blockchainkit as bk

OUT_DIR = Path(__file__).parent / "source" / "_static" / "images"
SIZE = (15, 4.6)


def crypto(axes):
    from blockchainkit.crypto.visualizers import plot_curve_points, plot_hamming_distances

    ax1, ax2, ax3 = axes
    plot_curve_points(bk.crypto.TOY_CURVE, ax=ax1)
    ax1.set_title("Scalar multiples on a toy elliptic curve")

    base = b"pay Bob 25"
    distances = []
    for i in range(2000):
        flipped = bytearray(base + i.to_bytes(4, "big"))
        flipped[i % 10] ^= 1 << (i % 8)
        distances.append(
            bk.crypto.hamming_distance(
                bk.crypto.sha256(base + i.to_bytes(4, "big")), bk.crypto.sha256(bytes(flipped))
            )
        )
    plot_hamming_distances(distances, ax=ax2)
    ax2.set_title("SHA-256 avalanche: one input bit flips half the output")

    bits = list(range(8, 33, 4))
    trials = [
        np.mean([bk.crypto.find_collision(b, prefix=bytes([s])).trials for s in range(5)])
        for b in bits
    ]
    ax3.semilogy(bits, trials, "o", label="measured")
    ax3.semilogy(
        bits, [np.sqrt(np.pi / 2 * 2.0**b) for b in bits], color="black", label="sqrt(pi/2 * 2^n)"
    )
    ax3.set(xlabel="digest bits n", ylabel="hashes until a collision")
    ax3.set_title("The birthday bound")
    ax3.legend()


def structures(axes):
    from blockchainkit.structures.visualizers import plot_block_tree, plot_merkle_tree

    ax1, ax2, ax3 = axes
    tree = bk.structures.MerkleTree([f"tx {i}".encode() for i in range(8)])
    plot_merkle_tree(tree, highlight=5, ax=ax1)
    ax1.set_title("A Merkle proof: three siblings for eight leaves")

    genesis = bk.consensus.mine(bk.structures.Block(difficulty=3)).block
    chain = bk.structures.Blockchain(genesis)
    parent, side = genesis, genesis
    for height in range(1, 5):
        parent = bk.consensus.mine(bk.structures.Block(parent.hash, (), height, height, 3)).block
        chain.add(parent)
        if height < 3:
            side = bk.consensus.mine(
                bk.structures.Block(side.hash, (), height, 10 + height, 3)
            ).block
            chain.add(side)
    plot_block_tree(chain, ax=ax2)
    ax2.set_title("A fork: the most work wins")

    size, items = 1000, np.arange(10, 401, 10)
    for k in (1, 3, 7):
        ax3.plot(
            items,
            [bk.structures.BloomFilter.false_positive_rate(size, k, int(n)) for n in items],
            label=f"{k} hashes",
        )
    ax3.set(xlabel="items in a 1000-bit filter", ylabel="false-positive rate")
    ax3.set_title("Bloom filters: compact, approximate membership")
    ax3.legend()


def consensus(axes):
    ax1, ax2, ax3 = axes
    for q in (0.1, 0.2, 0.3, 0.4):
        z = range(0, 31)
        ax1.semilogy(
            z,
            [max(bk.consensus.attacker_success_probability(q, k), 1e-12) for k in z],
            label=f"q = {q}",
        )
    ax1.set(xlabel="confirmations z", ylabel="attacker success", ylim=(1e-10, 1.5))
    ax1.set_title("Nakamoto's double-spend calculation")
    ax1.legend()

    alpha = np.linspace(0.01, 0.49, 49)
    for gamma in (0.0, 0.5, 1.0):
        ax2.plot(
            alpha,
            [bk.consensus.selfish_mining_revenue(a, gamma) for a in alpha],
            label=f"gamma = {gamma}",
        )
    ax2.plot(alpha, alpha, color="black", linestyle="--", label="honest share")
    ax2.set(xlabel="pool hashrate alpha", ylabel="pool's share of blocks")
    ax2.set_title("Selfish mining: majority is not enough")
    ax2.legend()

    hashrates = [1.0] * 3000 + [3.0] * 3000 + [0.5] * 3000
    run = bk.consensus.simulate_difficulty(hashrates, window=500, seed=2009)
    ax3.plot(np.convolve(run.block_times, np.ones(200) / 200, mode="valid"))
    ax3.axhline(600, color="black", linestyle="--")
    ax3.set(xlabel="block", ylabel="block time (s), moving average")
    ax3.set_title("Difficulty retargeting tracks the hashrate")


def network(axes):
    from blockchainkit.network.visualizers import plot_graph, plot_rumor_spread

    ax1, ax2, ax3 = axes
    plot_graph(bk.network.watts_strogatz(40, 4, 0.1, seed=3), ax=ax1)
    ax1.set_title("A small-world peer graph")

    runs = {
        mode: bk.network.spread_rumor(4096, mode=mode, seed=3)
        for mode in ("push", "pull", "push-pull")
    }
    plot_rumor_spread(runs, ax=ax2)
    ax2.set_title("Epidemic gossip: push, pull and push-pull")

    sizes = [64, 256, 1024, 4096]
    rng = np.random.default_rng(1)
    hops = []
    for n in sizes:
        ids = [int(i) for i in rng.choice(2**32, n, replace=False)]
        net = bk.network.KademliaNetwork(ids, bits=32, k=1, seed=1)
        sources = rng.choice(ids, 200)
        targets = rng.integers(0, 2**32, 200)
        hops.append(
            np.mean(
                [net.lookup(int(s), int(t)).hops for s, t in zip(sources, targets, strict=True)]
            )
        )
    ax3.semilogx(sizes, hops, "o-", base=2)
    ax3.set(xlabel="nodes", ylabel="mean lookup hops")
    ax3.set_title("Kademlia: logarithmic routing")


def vm(axes):
    from blockchainkit.vm.visualizers import plot_stack_height

    ax1, ax2, ax3 = axes
    n = 12
    left = "(" * (n - 2) + "1 + 2" + "".join(f") + {k}" for k in range(3, n + 1))
    right = "".join(f"{k} + (" for k in range(1, n)) + str(n) + ")" * (n - 1)
    for name, expression in (("left-nested", left), ("right-nested", right)):
        plot_stack_height(
            bk.vm.execute(bk.vm.compile_expression(expression), trace=True).trace,
            label=name,
            ax=ax1,
        )
    ax1.set_title("Reverse Polish evaluation on a stack")

    lengths = [
        run.steps
        for run in (bk.vm.run_turing_machine(r, max_steps=30) for r in bk.vm.enumerate_machines(2))
        if run.outcome == "halted"
    ]
    ax2.hist(lengths, bins=np.arange(0.5, 7.5), color="#7c3aed", edgecolor="white", log=True)
    ax2.set(xlabel="steps to halt", ylabel="two-state Turing machines")
    ax2.set_title("The busy beaver: S(2) = 6")

    ax3.bar(
        ["pay, then update", "update, then pay"],
        [
            bk.vm.drain_bank(10_000, 100).stolen,
            bk.vm.drain_bank(10_000, 100, checks_effects_interactions=True).stolen,
        ],
        color=["#dc2626", "#16a34a"],
    )
    ax3.set(ylabel="stolen from a 10,000 bank (deposit 100)")
    ax3.set_title("The DAO: reentrancy")


FIGURES = {
    "crypto": crypto,
    "structures": structures,
    "consensus": consensus,
    "network": network,
    "vm": vm,
}

if __name__ == "__main__":
    for name in sys.argv[1:] or FIGURES:
        fig, axes = plt.subplots(1, 3, figsize=SIZE, constrained_layout=True)
        FIGURES[name](axes)
        out = OUT_DIR / f"readme_{name}.png"
        fig.savefig(out, dpi=110)
        plt.close(fig)
        print(f"wrote {out}")
