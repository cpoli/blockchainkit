"""Sphinx configuration for blockchainkit."""

import re
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _release():
    """Installed distribution version, falling back to blockchainkit/__init__.py.

    The metadata lookup only succeeds when blockchainkit is installed, so a
    docs build from a fresh clone would otherwise die with PackageNotFoundError.
    """
    try:
        return _dist_version("blockchainkit")
    except PackageNotFoundError:
        init = Path(__file__).resolve().parents[2] / "blockchainkit" / "__init__.py"
        return re.search(r'^__version__\s*=\s*"([^"]+)"', init.read_text(), re.M).group(1)


project = "blockchainkit"
author = "Charles Poli"
copyright = "2026, Charles Poli"
release = _release()
del _release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # NumPy-style docstrings
    "sphinx.ext.mathjax",
    "sphinx.ext.doctest",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_gallery.gen_gallery",
    "sphinx_design",
    "jupyterlite_sphinx",
    "sphinx_sitemap",
    "sphinxext.opengraph",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "api/gallery/**/*.ipynb"]

napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_ivar = True
napoleon_preprocess_types = True
napoleon_type_aliases = {
    "iterable": "collections.abc.Iterable",
    "sequence": "collections.abc.Sequence",
    "mapping": "collections.abc.Mapping",
    "callable": "collections.abc.Callable",
    "collection": "collections.abc.Collection",
    "Mapping": "collections.abc.Mapping",
    "Curve": "blockchainkit.crypto.systems.curves.Curve",
    "DHGroup": "blockchainkit.crypto.systems.asymmetric.DHGroup",
    "RSAKeyPair": "blockchainkit.crypto.systems.asymmetric.RSAKeyPair",
    "DiscreteLogResult": "blockchainkit.crypto.core.base.DiscreteLogResult",
    "CollisionResult": "blockchainkit.crypto.core.base.CollisionResult",
    "PuzzleSolution": "blockchainkit.crypto.core.base.PuzzleSolution",
    "LamportKeyPair": "blockchainkit.crypto.core.base.LamportKeyPair",
    "FeldmanShares": "blockchainkit.crypto.core.base.FeldmanShares",
    "SchnorrSignature": "blockchainkit.crypto.core.base.SchnorrSignature",
    "Transaction": "blockchainkit.structures.systems.transaction.Transaction",
    "Block": "blockchainkit.structures.systems.block.Block",
    "Ledger": "blockchainkit.structures.systems.ledger.Ledger",
    "BlockHeader": "blockchainkit.structures.systems.block.BlockHeader",
    "UTXOSet": "blockchainkit.structures.systems.utxo.UTXOSet",
    "UTXOTransaction": "blockchainkit.structures.systems.utxo.UTXOTransaction",
    "OutPoint": "blockchainkit.structures.core.base.OutPoint",
    "Coin": "blockchainkit.structures.core.base.Coin",
    "SparseMerkleTree": "blockchainkit.structures.systems.sparse_merkle.SparseMerkleTree",
    "SparseMerkleProof": "blockchainkit.structures.core.base.SparseMerkleProof",
    "MerkleMountainRange": "blockchainkit.structures.systems.mmr.MerkleMountainRange",
    "MMRProof": "blockchainkit.structures.core.base.MMRProof",
    "Blockchain": "blockchainkit.structures.systems.chain.Blockchain",
    "MerkleTree": "blockchainkit.structures.systems.merkle.MerkleTree",
    "MerkleTrace": "blockchainkit.structures.core.base.MerkleTrace",
    "ProofStep": "blockchainkit.structures.core.base.ProofStep",
    "Delivery": "blockchainkit.network.core.base.Delivery",
    "RumorRun": "blockchainkit.network.core.base.RumorRun",
    "BroadcastResult": "blockchainkit.network.core.base.BroadcastResult",
    "Operation": "blockchainkit.network.core.base.Operation",
    "LookupResult": "blockchainkit.network.core.base.LookupResult",
    "RelayCost": "blockchainkit.network.core.base.RelayCost",
    "CompactBlockResult": "blockchainkit.network.core.base.CompactBlockResult",
    "Graph": "blockchainkit.network.systems.topology.Graph",
    "ConsensusRun": "blockchainkit.consensus.core.base.ConsensusRun",
    "DifficultyRun": "blockchainkit.consensus.core.base.DifficultyRun",
    "GeneralsResult": "blockchainkit.consensus.core.base.GeneralsResult",
    "MiningResult": "blockchainkit.consensus.core.base.MiningResult",
    "Offense": "blockchainkit.consensus.core.base.Offense",
    "PBFTResult": "blockchainkit.consensus.core.base.PBFTResult",
    "SelfishMiningResult": "blockchainkit.consensus.core.base.SelfishMiningResult",
    "SquareRootResult": "blockchainkit.consensus.core.base.SquareRootResult",
    "ViewChangeRun": "blockchainkit.consensus.core.base.ViewChangeRun",
    "ExecutionResult": "blockchainkit.vm.core.base.ExecutionResult",
    "TraceStep": "blockchainkit.vm.core.base.TraceStep",
    "VerificationResult": "blockchainkit.vm.core.base.VerificationResult",
    "TuringRun": "blockchainkit.vm.core.base.TuringRun",
    "BusyBeaverResult": "blockchainkit.vm.core.base.BusyBeaverResult",
    "ScriptResult": "blockchainkit.vm.core.base.ScriptResult",
    "ReentrancyResult": "blockchainkit.vm.core.base.ReentrancyResult",
    "CallRecord": "blockchainkit.contracts.core.base.CallRecord",
    "Event": "blockchainkit.contracts.core.base.Event",
    "Receipt": "blockchainkit.contracts.core.base.Receipt",
    "TripleResult": "blockchainkit.contracts.core.base.TripleResult",
    "SymbolicPath": "blockchainkit.contracts.core.base.SymbolicPath",
    "SymbolicResult": "blockchainkit.contracts.core.base.SymbolicResult",
    "FuzzCall": "blockchainkit.contracts.core.base.FuzzCall",
    "FuzzResult": "blockchainkit.contracts.core.base.FuzzResult",
    "RicardianContract": "blockchainkit.contracts.core.base.RicardianContract",
    "Contract": "blockchainkit.contracts.systems.world.Contract",
    "World": "blockchainkit.contracts.systems.world.World",
    "AuctionResult": "blockchainkit.economics.core.base.AuctionResult",
    "OracleRound": "blockchainkit.economics.core.base.OracleRound",
    "AttackIncentive": "blockchainkit.economics.core.base.AttackIncentive",
    "PendingTransaction": "blockchainkit.economics.core.base.PendingTransaction",
    "FeeMarketRun": "blockchainkit.economics.core.base.FeeMarketRun",
    "GasAuction": "blockchainkit.economics.core.base.GasAuction",
    "SandwichResult": "blockchainkit.economics.core.base.SandwichResult",
    "PBSRun": "blockchainkit.economics.core.base.PBSRun",
    "Settlement": "blockchainkit.channels.core.base.Settlement",
    "SwapOutcome": "blockchainkit.channels.core.base.SwapOutcome",
    "Commitment": "blockchainkit.channels.core.base.Commitment",
    "Route": "blockchainkit.channels.core.base.Route",
    "PaymentAttempt": "blockchainkit.channels.core.base.PaymentAttempt",
    "ProbeResult": "blockchainkit.channels.core.base.ProbeResult",
    "CoinTransfer": "blockchainkit.channels.core.base.CoinTransfer",
    "InclusionProof": "blockchainkit.channels.core.base.InclusionProof",
    "PlasmaExit": "blockchainkit.channels.core.base.PlasmaExit",
    "AtomixResult": "blockchainkit.channels.core.base.AtomixResult",
    "Transfer": "blockchainkit.channels.core.base.Transfer",
    "ValidityProof": "blockchainkit.channels.core.base.ValidityProof",
    "FraudProof": "blockchainkit.channels.core.base.FraudProof",
    "ErasureCodedData": "blockchainkit.channels.core.base.ErasureCodedData",
    "EncodingFraudProof": "blockchainkit.channels.core.base.EncodingFraudProof",
    "SamplingResult": "blockchainkit.channels.core.base.SamplingResult",
    "AppointmentReceipt": "blockchainkit.channels.core.base.AppointmentReceipt",
    "ChannelNetwork": "blockchainkit.channels.systems.routing.ChannelNetwork",
    "MerkleProof": "blockchainkit.structures.core.base.MerkleProof",
    "LightningChannel": "blockchainkit.channels.systems.lightning.LightningChannel",
    "IdentityTest": "blockchainkit.proofs.core.base.IdentityTest",
    "CNF": "blockchainkit.proofs.core.base.CNF",
    "SumcheckRun": "blockchainkit.proofs.core.base.SumcheckRun",
    "QBF": "blockchainkit.proofs.core.base.QBF",
    "TQBFRound": "blockchainkit.proofs.core.base.TQBFRound",
    "TQBFRun": "blockchainkit.proofs.core.base.TQBFRun",
    "QuadraticSystem": "blockchainkit.proofs.core.base.QuadraticSystem",
    "HadamardProof": "blockchainkit.proofs.core.base.HadamardProof",
    "PCPRun": "blockchainkit.proofs.core.base.PCPRun",
    "KilianRun": "blockchainkit.proofs.core.base.KilianRun",
    "Opening": "blockchainkit.proofs.core.base.Opening",
    "CSProof": "blockchainkit.proofs.core.base.CSProof",
    "SRS": "blockchainkit.proofs.core.base.SRS",
    "KZGOpening": "blockchainkit.proofs.core.base.KZGOpening",
    "Contribution": "blockchainkit.proofs.core.base.Contribution",
    "R1CS": "blockchainkit.proofs.core.base.R1CS",
    "QAP": "blockchainkit.proofs.core.base.QAP",
    "QAPDivision": "blockchainkit.proofs.core.base.QAPDivision",
    "Groth16Trapdoor": "blockchainkit.proofs.core.base.Groth16Trapdoor",
    "VerifyingKey": "blockchainkit.proofs.core.base.VerifyingKey",
    "ProvingKey": "blockchainkit.proofs.core.base.ProvingKey",
    "Groth16Proof": "blockchainkit.proofs.core.base.Groth16Proof",
    "Note": "blockchainkit.proofs.core.base.Note",
    "SpendTransaction": "blockchainkit.proofs.core.base.SpendTransaction",
    "PlonkKey": "blockchainkit.proofs.core.base.PlonkKey",
    "PlonkProof": "blockchainkit.proofs.core.base.PlonkProof",
    "RangeProof": "blockchainkit.proofs.core.base.RangeProof",
    "IPAOpening": "blockchainkit.proofs.core.base.IPAOpening",
    "HaloAccumulator": "blockchainkit.proofs.core.base.HaloAccumulator",
    "AccumulationProof": "blockchainkit.proofs.core.base.AccumulationProof",
    "FRILayerOpening": "blockchainkit.proofs.core.base.FRILayerOpening",
    "FRIQuery": "blockchainkit.proofs.core.base.FRIQuery",
    "FRIProof": "blockchainkit.proofs.core.base.FRIProof",
    "TraceOpening": "blockchainkit.proofs.core.base.TraceOpening",
    "StarkProof": "blockchainkit.proofs.core.base.StarkProof",
    "Transcript": "blockchainkit.proofs.utils.transcript.Transcript",
    "Wire": "blockchainkit.proofs.systems.circuits.Wire",
    "Circuit": "blockchainkit.proofs.systems.circuits.Circuit",
    "PlonkCircuit": "blockchainkit.proofs.systems.plonk.PlonkCircuit",
    "ShieldedPool": "blockchainkit.proofs.systems.zerocash.ShieldedPool",
    "PonziRun": "blockchainkit.fraud.core.base.PonziRun",
    "Flow": "blockchainkit.fraud.core.base.Flow",
    "PonziFeatures": "blockchainkit.fraud.core.base.PonziFeatures",
    "BenfordTest": "blockchainkit.fraud.core.base.BenfordTest",
    "SumProofStep": "blockchainkit.fraud.core.base.SumProofStep",
    "SumProof": "blockchainkit.fraud.core.base.SumProof",
    "AuditResult": "blockchainkit.fraud.core.base.AuditResult",
    "BitRangeProof": "blockchainkit.fraud.core.base.BitRangeProof",
    "SolvencyProof": "blockchainkit.fraud.core.base.SolvencyProof",
    "MarketRun": "blockchainkit.fraud.core.base.MarketRun",
    "PumpRun": "blockchainkit.fraud.core.base.PumpRun",
    "Trade": "blockchainkit.fraud.core.base.Trade",
    "TradeHistory": "blockchainkit.fraud.core.base.TradeHistory",
    "WashReport": "blockchainkit.fraud.core.base.WashReport",
    "LookalikeAddress": "blockchainkit.fraud.core.base.LookalikeAddress",
    "MerkleSumTree": "blockchainkit.fraud.utils.merkle_sum.MerkleSumTree",
    "MixRun": "blockchainkit.privacy.core.base.MixRun",
    "FlowObservation": "blockchainkit.privacy.core.base.FlowObservation",
    "RingSignature": "blockchainkit.privacy.core.base.RingSignature",
    "LinkableRingSignature": "blockchainkit.privacy.core.base.LinkableRingSignature",
    "TransactionRecord": "blockchainkit.privacy.core.base.TransactionRecord",
    "PaymentHistory": "blockchainkit.privacy.core.base.PaymentHistory",
    "ClusterScore": "blockchainkit.privacy.core.base.ClusterScore",
    "StealthKeys": "blockchainkit.privacy.core.base.StealthKeys",
    "StealthOutput": "blockchainkit.privacy.core.base.StealthOutput",
    "CoinJoinRound": "blockchainkit.privacy.core.base.CoinJoinRound",
    "ZerocoinSpend": "blockchainkit.privacy.core.base.ZerocoinSpend",
    "RingRangeProof": "blockchainkit.privacy.core.base.RingRangeProof",
    "ConfidentialOutput": "blockchainkit.privacy.core.base.ConfidentialOutput",
    "RingCTTransaction": "blockchainkit.privacy.core.base.RingCTTransaction",
    "Kernel": "blockchainkit.privacy.core.base.Kernel",
    "MimblewimbleTransaction": "blockchainkit.privacy.core.base.MimblewimbleTransaction",
    "PuzzlePromise": "blockchainkit.privacy.core.base.PuzzlePromise",
    "TumblerRun": "blockchainkit.privacy.core.base.TumblerRun",
    "RingInput": "blockchainkit.privacy.core.base.RingInput",
    "TraceReport": "blockchainkit.privacy.core.base.TraceReport",
    "MixerReport": "blockchainkit.privacy.core.base.MixerReport",
    "Withdrawal": "blockchainkit.privacy.core.base.Withdrawal",
    "MixNode": "blockchainkit.privacy.systems.mixnets.MixNode",
    "BCHDecoding": "blockchainkit.wallets.core.base.BCHDecoding",
    "DetectionRates": "blockchainkit.wallets.core.base.DetectionRates",
    "CrackResult": "blockchainkit.wallets.core.base.CrackResult",
    "RomixCost": "blockchainkit.wallets.core.base.RomixCost",
    "ExtendedKey": "blockchainkit.wallets.core.base.ExtendedKey",
    "AccountScan": "blockchainkit.wallets.core.base.AccountScan",
    "BrainDrain": "blockchainkit.wallets.core.base.BrainDrain",
    "Bech32Decoding": "blockchainkit.wallets.core.base.Bech32Decoding",
    "WitnessProgram": "blockchainkit.wallets.core.base.WitnessProgram",
    "EcdsaSignature": "blockchainkit.wallets.core.base.EcdsaSignature",
    "KeyShares": "blockchainkit.wallets.core.base.KeyShares",
    "ThresholdSigning": "blockchainkit.wallets.core.base.ThresholdSigning",
    "RecoveryRisk": "blockchainkit.wallets.core.base.RecoveryRisk",
    "UserOperation": "blockchainkit.wallets.core.base.UserOperation",
    "GaloisField": "blockchainkit.wallets.utils.galois.GaloisField",
}

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
autodoc_typehints = "description"
autodoc_member_order = "bysource"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
}

# Every cross-reference must resolve: a broken link is a build error.
nitpicky = True
# sphinx_gallery_conf holds a function, so Sphinx cannot cache the config.
suppress_warnings = ["config.cache"]
nitpick_ignore = [
    # Type aliases are documented as module attributes, not classes.
    ("py:class", "blockchainkit.channels.utils.scripts.PublicKey"),
    ("py:class", "blockchainkit.channels.systems.bridges.Approval"),
    ("py:class", "blockchainkit.proofs.core.base.Polynomial"),
    ("py:class", "Polynomial"),
    ("py:class", "blockchainkit.proofs.core.base.Row"),
    ("py:class", "Row"),
    ("py:class", "blockchainkit.proofs.systems.pairing.GTElement"),
    ("py:class", "GTElement"),
    ("py:class", "blockchainkit.proofs.systems.pcp.Oracle"),
    ("py:class", "Oracle"),
    ("py:class", "blockchainkit.proofs.utils.transcript.Message"),
    ("py:class", "Message"),
    ("py:class", "blockchainkit.crypto.core.base.Point"),
    ("py:class", "Point"),
    ("py:class", "blockchainkit.network.systems.clocks.Event"),
    ("py:class", "Event"),
    ("py:class", "blockchainkit.vm.core.base.Instruction"),
    ("py:class", "Instruction"),
    ("py:class", "blockchainkit.vm.systems.script.ScriptItem"),
    ("py:class", "ScriptItem"),
    ("py:class", "blockchainkit.vm.systems.turing.Rule"),
    ("py:class", "Rule"),
    ("py:class", "blockchainkit.contracts.core.base.Expr"),
    ("py:class", "Expr"),
    ("py:class", "blockchainkit.contracts.utils.expressions.Statement"),
    ("py:class", "Statement"),
    ("py:class", "blockchainkit.contracts.systems.wallets.Approval"),
    ("py:class", "Approval"),
    ("py:class", "blockchainkit.contracts.systems.wallets.PublicKey"),
    ("py:class", "PublicKey"),
    ("py:class", "blockchainkit.contracts.systems.design_by_contract.F"),
    ("py:class", "blockchainkit.wallets.utils.keys.PublicKey"),
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Single source of truth for the subpackages. Every card grid (homepage,
# api/index, examples/index, history/index, and the per-subpackage hub pages)
# and the cross-link strip atop each api/history page is generated from this
# table by _generate_subpackage_docs() below, ported from mathematicskit.
SUBPACKAGES = [
    {
        "name": "crypto",
        "category": "Cryptography",
        "blurb": "Hashing and commitments, Diffie-Hellman and RSA, blind signatures, "
        "secret sharing, elliptic curves, and Schnorr proofs and signatures.",
    },
    {
        "name": "structures",
        "category": "Ledgers",
        "blurb": "Merkle trees and proofs, signed transfers, blocks, ledger state, "
        "and cumulative-work fork selection.",
    },
    {
        "name": "consensus",
        "category": "Agreement",
        "blurb": "Proof-of-work search and its expected cost, catch-up probabilities, "
        "and stake-weighted proposer selection.",
    },
    {
        "name": "network",
        "category": "Agreement",
        "blurb": "Peer graphs, logical clocks, gossip and reliable broadcast, "
        "Kademlia and its attacks, block relay, forks, and transaction privacy.",
    },
    {
        "name": "vm",
        "category": "Execution",
        "blurb": "A deterministic 256-bit stack machine with gas and atomic failure, "
        "Turing machines, Bitcoin Script, and smart contracts and their attacks.",
    },
    {
        "name": "contracts",
        "category": "Execution",
        "blurb": "A world-state model of contracts calling contracts: token standards, "
        "wallets, proxies and their famous failures, with Hoare logic, symbolic "
        "execution and fuzzing.",
    },
    {
        "name": "economics",
        "category": "Economics",
        "blurb": "Incentives, fees and markets: auctions, block rewards and mining games, "
        "EIP-1559, stablecoins and market makers, and the value of transaction ordering.",
    },
    {
        "name": "channels",
        "category": "Scaling",
        "blurb": "Layer 2 and interoperability: payment channels from Spilman to Lightning "
        "and eltoo, atomic swaps and bridges, Plasma, sharding, rollups, and "
        "data-availability sampling.",
    },
    {
        "name": "proofs",
        "category": "Cryptography",
        "blurb": "Zero-knowledge and succinct proofs: sum-check and PCPs, KZG, Groth16 and "
        "PLONK with their trusted setups, Zerocash, and transparent Bulletproofs, FRI, "
        "STARKs and Halo.",
    },
    {
        "name": "fraud",
        "category": "Economics",
        "blurb": "Ponzi schemes, Benford's law, proofs of reserves and solvency, honeypots "
        "and rug pulls, pump-and-dumps, wash trading, and phishing.",
    },
    {
        "name": "privacy",
        "category": "Cryptography",
        "blurb": "Anonymity on public ledgers: mix-nets and Tor, ring signatures and stealth "
        "addresses, address clustering, CoinJoin and mixers, and hidden amounts from "
        "confidential transactions to Mimblewimble.",
    },
    {
        "name": "wallets",
        "category": "Ledgers",
        "blurb": "Keys as users hold them: check digits, Base58Check and Bech32 addresses, "
        "PBKDF2 and scrypt, brain wallets, HD keys and seed phrases, multisig and threshold "
        "ECDSA, social recovery, and ERC-4337 accounts.",
    },
]

for _s in SUBPACKAGES:
    _s.setdefault("history_doc", f"{_s['name']}_breakthroughs")
    _s["examples_doc"] = f"api/gallery/{_s['name']}/index"
del _s

_CATEGORY_ORDER = ["Cryptography", "Ledgers", "Agreement", "Execution", "Economics", "Scaling"]
_GALLERY_SUBPACKAGES = [s["name"] for s in SUBPACKAGES]


def _jupyterlite_install_cell(notebook_content, notebook_filename):
    """Prepend a ``%pip install`` cell so the Pyodide kernel fetches blockchainkit from PyPI."""
    notebook_content["cells"].insert(
        0,
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ["%pip install blockchainkit"],
        },
    )


sphinx_gallery_conf = {
    "examples_dirs": [f"../../examples/{name}" for name in _GALLERY_SUBPACKAGES],
    "gallery_dirs": [f"api/gallery/{name}" for name in _GALLERY_SUBPACKAGES],
    "filename_pattern": r"/plot_",
    "download_all_examples": True,
    "within_subsection_order": "FileNameSortKey",
    "remove_config_comments": True,
    "abort_on_example_error": True,
    "image_scrapers": ("matplotlib",),
    "capture_repr": (),
    # Lets ".. minigallery::" (used throughout docs/source/history/) resolve.
    "backreferences_dir": "gen_modules/backreferences",
    "doc_module": ("blockchainkit",),
    # "Launch JupyterLite" button: runs the notebook in the browser on
    # Pyodide, with no server. blockchainkit is pure Python, so it runs there
    # unchanged once it is on PyPI.
    "jupyterlite": {
        "use_jupyter_lab": True,
        "notebook_modification_function": _jupyterlite_install_cell,
    },
}

doctest_global_setup = "import blockchainkit as bk"

html_theme = "pydata_sphinx_theme"

# Search-engine metadata: sphinx-sitemap writes sitemap.xml with absolute
# URLs from html_baseurl, and sphinxext-opengraph adds a <meta
# name="description"> plus og:* link-preview tags from each page's text.
# html_baseurl also gives every page a <link rel="canonical">.
html_baseurl = "https://cpoli.github.io/blockchainkit/"
sitemap_url_scheme = "{link}"
sitemap_excludes = [
    "search.html",
    "genindex.html",
    "py-modindex.html",
    "*sg_execution_times.html",
    "_modules/*",
    # Include-only fragments (card grids, nav strips), not standalone pages.
    "_generated/grid_*",
    "_generated/vars.html",
    "_generated/nav/*",
]
ogp_site_url = html_baseurl
ogp_site_name = project
ogp_image = html_baseurl + "_static/images/blockchainkit_logo.png"
ogp_social_cards = {"enable": False}
html_title = "blockchainkit"
html_logo = "_static/images/blockchainkit_logo_transparent.png"
html_theme_options = {
    "github_url": "https://github.com/cpoli/blockchainkit",
    "icon_links": [
        {
            "name": "Charles Poli",
            "url": "https://cpoli.github.io/",
            "icon": "fa-solid fa-user",
            "type": "fontawesome",
        },
    ],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "show_toc_level": 2,
    "navigation_with_keys": True,
    "navigation_depth": 2,
    "logo": {
        "alt_text": "blockchainkit logo",
    },
}
html_static_path = ["_static"]
html_css_files = ["custom.css"]


def _card(link, blurb, link_title):
    """One sphinx-design grid-item-card, indented for a ``.. grid::`` block."""
    return (
        f"   .. grid-item-card:: {link_title}\n"
        f"      :link: {link}\n"
        "      :link-type: doc\n\n"
        f"      {blurb}\n\n"
    )


def _grid(cards):
    return ".. grid:: 1 2 3 3\n   :gutter: 2\n\n" + "".join(cards)


def _grouped_grid(link_fn):
    """A ``.. grid::`` per category, each preceded by a rubric heading."""
    parts = []
    for category in _CATEGORY_ORDER:
        members = [s for s in SUBPACKAGES if s["category"] == category]
        if not members:
            continue
        parts.append(f".. rubric:: {category}\n\n")
        parts.append(
            _grid([_card(link_fn(s), s["blurb"], f"blockchainkit.{s['name']}") for s in members])
        )
        parts.append("\n")
    return "".join(parts)


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _generate_subpackage_docs(app):
    """Generate the card grids, per-subpackage hub pages, and cross-link strips.

    Runs at "builder-inited", before Sphinx reads any source file that
    includes them. Everything lands under _generated/ (gitignored), since it
    is entirely derived from SUBPACKAGES.
    """
    out = Path(app.srcdir) / "_generated"
    _write(out / "vars.rst", f".. |num_subpackages| replace:: {len(SUBPACKAGES)}\n")
    _write(out / "grid_api.rst", _grouped_grid(lambda s: f"/api/{s['name']}"))
    _write(out / "grid_examples.rst", _grouped_grid(lambda s: f"/{s['examples_doc']}"))
    _write(out / "grid_history.rst", _grouped_grid(lambda s: f"/history/{s['history_doc']}"))
    _write(out / "grid_hub.rst", _grouped_grid(lambda s: f"/_generated/subpackages/{s['name']}"))

    for s in SUBPACKAGES:
        name = s["name"]
        title = f"blockchainkit.{name}"
        cards = _grid(
            [
                _card(
                    f"/history/{s['history_doc']}",
                    "The breakthroughs behind this subpackage, linked to the implementation.",
                    "History",
                ),
                _card(f"/{s['examples_doc']}", "The runnable example gallery.", "Examples"),
                _card(f"/api/{name}", "Every public class and function.", "API reference"),
            ]
        )
        _write(
            out / "subpackages" / f"{name}.rst",
            f"{title}\n{'=' * len(title)}\n\n{s['blurb']}\n\n{cards}",
        )

        links = [
            f":doc:`blockchainkit.{name} hub </_generated/subpackages/{name}>`",
            f":doc:`History </history/{s['history_doc']}>`",
            f":doc:`Examples </{s['examples_doc']}>`",
            f":doc:`API reference </api/{name}>`",
        ]
        _write(
            out / "nav" / f"{name}.rst", f".. container:: subpkg-nav\n\n   {' · '.join(links)}\n"
        )


def setup(app):
    app.connect("builder-inited", _generate_subpackage_docs)
