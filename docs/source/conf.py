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
    "Blockchain": "blockchainkit.structures.systems.chain.Blockchain",
    "MerkleTree": "blockchainkit.structures.systems.merkle.MerkleTree",
    "MerkleTrace": "blockchainkit.structures.core.base.MerkleTrace",
    "ProofStep": "blockchainkit.structures.core.base.ProofStep",
    "Delivery": "blockchainkit.network.core.base.Delivery",
    "ExecutionResult": "blockchainkit.vm.core.base.ExecutionResult",
    "TraceStep": "blockchainkit.vm.core.base.TraceStep",
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
    ("py:class", "blockchainkit.crypto.core.base.Point"),
    ("py:class", "Point"),
    ("py:class", "blockchainkit.vm.core.base.Instruction"),
    ("py:class", "Instruction"),
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
        "blurb": "Deterministic discrete-event gossip with latency, partitions, "
        "and duplicate suppression.",
    },
    {
        "name": "vm",
        "category": "Execution",
        "blurb": "A deterministic 256-bit stack machine with storage, gas limits, "
        "step traces, and atomic failure.",
    },
]

for _s in SUBPACKAGES:
    _s.setdefault("history_doc", f"{_s['name']}_breakthroughs")
    _s["examples_doc"] = f"api/gallery/{_s['name']}/index"
del _s

_CATEGORY_ORDER = ["Cryptography", "Ledgers", "Agreement", "Execution"]
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
html_title = "blockchainkit"
html_theme_options = {
    "github_url": "https://github.com/cpoli/blockchainkit",
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "show_toc_level": 2,
    "navigation_with_keys": True,
    "navigation_depth": 2,
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
