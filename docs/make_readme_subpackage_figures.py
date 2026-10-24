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


def contracts(axes):
    from blockchainkit.contracts.visualizers import plot_symbolic_paths

    ax1, ax2, ax3 = axes
    program = """
require(amount <= balance)
if amount > 100:
    fee = 2
else:
    fee = 1
balance = balance - amount - fee
assert balance >= 0
"""
    plot_symbolic_paths(bk.contracts.symbolic_execute(program), ax=ax1)
    ax1.set_title("Symbolic execution: every path of a withdrawal")

    sizes = [100, 300, 500, 700, 900, 1_100]
    for lazy, color, label in (
        (False, "#dc2626", "clear every creditor"),
        (True, "#16a34a", "start a new round"),
    ):
        gas = []
        for n in sizes:
            world = bk.contracts.World(block_gas_limit=4_712_388)
            game = world.deploy("operator", bk.contracts.GovernMental, lazy)
            for index in range(n):
                world.fund(f"p{index}", 1)
                world.transact(f"p{index}", game, "invest", value=1)
            world.advance(seconds=43_200)
            gas.append(world.transact("anyone", game, "payout").gas_used)
        ax2.plot(sizes, gas, "o-", color=color, label=label)
    ax2.axhline(4_712_388, color="#64748b", linestyle="--", label="2016 block gas limit")
    ax2.set(xlabel="creditors", ylabel="payout gas")
    ax2.set_title("GovernMental: a loop outgrows the block")
    ax2.legend()

    paid = []
    for code in (bk.contracts.KingOfTheEther, bk.contracts.PullKingOfTheEther):
        world = bk.contracts.World()
        world.fund("bob", 10_000)
        throne = world.deploy("owner", code, 100)
        wallet = world.deploy("alice", bk.contracts.ContractWallet)
        world.fund(wallet, 1_000)
        world.transact("alice", wallet, "forward", throne, "claim_throne", 100)
        world.transact("bob", throne, "claim_throne", value=1_000)
        if code is bk.contracts.PullKingOfTheEther:
            world.transact("alice", wallet, "forward", throne, "withdraw", 0)
        paid.append(world.balance(wallet) - 900)
    ax3.bar(["unchecked send", "pull payment"], paid, color=["#dc2626", "#16a34a"])
    ax3.set(ylabel="ether reaching the deposed king (owed 990)")
    ax3.set_title("King of the Ether: push versus pull")


def economics(axes):
    from blockchainkit.economics.visualizers import plot_fee_market

    ax1, ax2, ax3 = axes
    target = 20 * 21_000
    run = bk.economics.simulate_fee_market(
        [20] * 40 + [45] * 40 + [20] * 40, gas_target=target, seed=7
    )
    plot_fee_market(run, gas_target=target, ax=ax1)
    ax1.set_title("EIP-1559: the base fee prices a demand surge")

    alphas = np.round(np.arange(0.05, 0.46, 0.05), 2)
    ax2.plot(alphas, alphas, "--", color="black", label="honest: share = alpha")
    for gamma, color in ((0.0, "#2563eb"), (0.5, "#16a34a")):
        best = [bk.economics.optimal_mining_revenue(a, gamma, max_lead=8) for a in alphas]
        ax2.plot(alphas, best, "o-", color=color, label=f"best response, gamma = {gamma}")
    ax2.set(xlabel="hashrate alpha", ylabel="share of the chain's blocks")
    ax2.set_title("Mining games: when honest mining is a best response")
    ax2.legend()

    tolerances = [10, 25, 50, 100, 200, 300, 500, 800]
    attacks = [
        bk.economics.sandwich_attack(10_000_000, 10_000_000, 100_000, slippage_bps=s)
        for s in tolerances
    ]
    percent = [s / 100 for s in tolerances]
    ax3.plot(percent, [a.profit for a in attacks], "o-", color="#dc2626", label="attacker profit")
    ax3.plot(percent, [a.victim_loss for a in attacks], "s-", color="#2563eb", label="victim loss")
    ax3.set(xlabel="victim's slippage tolerance (%)", ylabel="tokens")
    ax3.set_title("Sandwich attacks: a loose tolerance invites them")
    ax3.legend()


def channels(axes):
    from blockchainkit.channels.visualizers import plot_detection

    ax1, ax2, ax3 = axes
    plot_detection(range(1, 16), withheld=(0.25, 33 / 64), ax=ax1)
    ax1.set_title("Data-availability sampling catches withholding")

    hops = range(1, 21)
    staggered = [
        bk.channels.collateral_time([1] * n, bk.channels.htlc_expiries(n, delta=40)) for n in hops
    ]
    shared = [
        bk.channels.collateral_time([1] * n, bk.channels.sprites_expiries(n, delta=40))
        for n in hops
    ]
    ax2.plot(hops, staggered, "o-", color="#dc2626", label="Lightning: staggered expiries")
    ax2.plot(hops, shared, "s-", color="#16a34a", label="Sprites: one shared deadline")
    ax2.set(xlabel="hops in the route", ylabel="coins x blocks locked")
    ax2.set_title("Collateral locked by a multi-hop payment")
    ax2.legend()

    sizes = [1, 10, 30, 100, 300, 1_000, 3_000, 10_000]
    gas = [bk.channels.batch_gas(n, bytes_per_transaction=12, fixed_gas=300_000) / n for n in sizes]
    ax3.loglog(sizes, gas, "o-", color="#2563eb", label="zk-rollup")
    ax3.axhline(21_000, color="#dc2626", linestyle="--", label="transfer on chain")
    ax3.set(xlabel="transfers per batch", ylabel="gas per transfer")
    ax3.set_title("A rollup shares one proof across a batch")
    ax3.legend()


def proofs(axes):
    from blockchainkit.proofs.visualizers import plot_proof_sizes

    ax1, ax2, ax3 = axes
    prime = 97
    degrees = range(1, 25, 2)
    fooled = []
    for d in degrees:
        roots = bk.proofs.vanishing_polynomial(range(1, d + 1), prime)
        fooled.append(sum(bk.proofs.poly_eval(roots, x, prime) == 0 for x in range(prime)) / prime)
    ax1.plot(degrees, fooled, "o", color="#2563eb", label="points where f = 0")
    ax1.plot(degrees, [d / prime for d in degrees], color="#dc2626", label="bound d / |F|")
    ax1.set(xlabel="degree d", ylabel="chance a random test is fooled")
    ax1.set_title("Schwartz-Zippel over a field of 97 elements")
    ax1.legend()

    points = []
    for log_t in range(4, 11):
        t = 2**log_t
        points.append((t, bk.proofs.stark_prove(t).size))
    plot_proof_sizes(
        {"the trace (8 bytes a step)": [(t, 8 * t) for t, _ in points], "STARK proof": points},
        xlabel="steps of computation",
        ax=ax2,
    )
    ax2.set_title("STARKs: proof grows like log² T, the trace like T")

    bits = [2, 4, 8, 16, 32, 64]
    sizes = [sum(bk.proofs.range_proof(2**n - 1, 3, n).size) for n in bits]
    ax3.plot(bits, [4 * n for n in bits], "o-", color="#dc2626", label="a proof per bit")
    ax3.plot(bits, sizes, "o-", color="#2563eb", label="Bulletproofs")
    ax3.axhline(3, color="#16a34a", linestyle="--", label="Groth16 (trusted setup)")
    ax3.set_xscale("log", base=2)
    ax3.set(xlabel="range bits", ylabel="elements in the proof")
    ax3.set_title("Range proofs: setup-free, logarithmic")
    ax3.legend()


def fraud(axes):
    import random

    from blockchainkit.fraud.visualizers import plot_benford, plot_ponzi, plot_price_spikes

    ax1, ax2, ax3 = axes
    deposits = [min(100 * 1.6**t, 2_000) for t in range(15)]
    plot_ponzi(bk.fraud.simulate_ponzi(deposits, promised_return=0.5), ax=ax1)
    ax1.set_title("Ponzi's scheme: new money pays old, until it cannot")

    rng = random.Random(1938)
    invented = bk.fraud.benford_test(rng.uniform(100, 9_999) for _ in range(3_000))
    plot_benford(invented, ax=ax2, label="invented amounts")
    ax2.set_title("Benford's law: invented figures stand out")

    run = bk.fraud.simulate_pump_and_dump(seed=1)
    plot_price_spikes(run.prices, bk.fraud.detect_pumps(run.prices, run.volumes), ax=ax3)
    ax3.set(xlabel="hour", ylabel="price (BTC)")
    ax3.set_title("A pump-and-dump, flagged by its spike")


def privacy(axes):
    import random

    from blockchainkit.privacy.visualizers import (
        plot_anonymity_sets,
        plot_cluster_sizes,
        plot_ring_positions,
    )

    ax1, ax2, ax3 = axes
    history = bk.privacy.simulate_payments(150, 1_500, reuse=0.9, seed=13)
    plot_cluster_sizes(bk.privacy.cluster_addresses(history.transactions), ax=ax1, label="inputs")
    plot_cluster_sizes(
        bk.privacy.cluster_addresses(history.transactions, change=True), ax=ax1, label="and change"
    )
    ax1.set_title("Clustering Bitcoin addresses by owner")

    rings = bk.privacy.simulate_rings(5_000, 1_000, ring_size=5, seed=7)
    plot_ring_positions(rings, ax=ax2)
    ax2.set_title("Monero's uniform decoys: the newest is real")

    rng = random.Random(3)
    deposits = [(f"user{i}", rng.randrange(0, 200)) for i in range(40)]
    withdrawals = sorted(
        ((f"fresh{i}", b + rng.randrange(1, 60)) for i, (_, b) in enumerate(deposits)),
        key=lambda w: w[1],
    )
    plot_anonymity_sets(bk.privacy.mixer_report(deposits, withdrawals).anonymity_sets, ax=ax3)
    ax3.set_title("A mixer's anonymity set per withdrawal")


def wallets(axes):
    from blockchainkit.wallets.visualizers import (
        plot_detection_rates,
        plot_memory_tradeoff,
        plot_recovery_risk,
    )

    ax1, ax2, ax3 = axes
    rates = [bk.wallets.detection_rates(s, 3) for s in ("sum", "luhn", "verhoeff")]
    plot_detection_rates(rates, ax=ax1)
    ax1.set_title("Check digits: only Verhoeff's catches every swap")

    block = bk.wallets.pbkdf2(b"password", b"NaCl", 1, 128)
    costs = [bk.wallets.romix(block, 128, keep_every=k)[1] for k in (1, 2, 4, 8, 16, 32, 64, 128)]
    plot_memory_tradeoff(costs, ax=ax2)
    ax2.set_title("scrypt: saving memory costs time")

    plot_recovery_risk(5, lost=0.1, corrupt=0.05, ax=ax3)
    ax3.set_title("Social recovery: 5 guardians against one seed phrase")


FIGURES = {
    "crypto": crypto,
    "structures": structures,
    "consensus": consensus,
    "network": network,
    "vm": vm,
    "contracts": contracts,
    "economics": economics,
    "channels": channels,
    "proofs": proofs,
    "fraud": fraud,
    "privacy": privacy,
    "wallets": wallets,
}

if __name__ == "__main__":
    for name in sys.argv[1:] or FIGURES:
        fig, axes = plt.subplots(1, 3, figsize=SIZE, constrained_layout=True)
        FIGURES[name](axes)
        out = OUT_DIR / f"readme_{name}.png"
        fig.savefig(out, dpi=110)
        plt.close(fig)
        print(f"wrote {out}")
