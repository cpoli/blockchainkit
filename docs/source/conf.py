"""Sphinx configuration: history, executable gallery, API, and mathematics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import blockchainkit  # noqa: E402

project = "blockchainkit"
author = "Charles Poli"
copyright = "2026, Charles Poli"
release = blockchainkit.__version__
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",
    "sphinx.ext.doctest",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinx_gallery.gen_gallery",
]
html_theme = "pydata_sphinx_theme"
html_title = "blockchainkit — ideas you can execute"
html_theme_options = {
    "navigation_depth": 3,
    "show_toc_level": 2,
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
}
html_static_path = ["_static"]
html_css_files = ["custom.css"]
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_ivar = True
napoleon_preprocess_types = True
napoleon_type_aliases = {
    "iterable": "collections.abc.Iterable",
    "mapping": "collections.abc.Mapping",
    "callable": "collections.abc.Callable",
    "Mapping": "collections.abc.Mapping",
    "Curve": "blockchainkit.crypto.systems.curves.Curve",
    "SchnorrSignature": "blockchainkit.crypto.core.base.SchnorrSignature",
    "Transaction": "blockchainkit.structures.systems.transaction.Transaction",
    "Block": "blockchainkit.structures.systems.block.Block",
    "Ledger": "blockchainkit.structures.systems.ledger.Ledger",
    "ExecutionResult": "blockchainkit.vm.core.base.ExecutionResult",
}
autodoc_typehints = "description"
autodoc_member_order = "bysource"
nitpicky = True
# Built-in typing and standard library targets have no intersphinx dependency,
# keeping documentation builds offline after installing the toolchain.
nitpick_ignore = [
    ("py:class", "collections.abc.Iterable"),
    ("py:class", "collections.abc.Mapping"),
    ("py:class", "collections.abc.Callable"),
    ("py:class", "collections.abc.Sequence"),
    ("py:class", "blockchainkit.crypto.core.base.Point"),
    ("py:class", "blockchainkit.vm.core.base.Instruction"),
]
exclude_patterns = ["gallery/*.ipynb"]
sphinx_gallery_conf = {
    "examples_dirs": "../../examples",
    "gallery_dirs": "gallery",
    "filename_pattern": r"/plot_",
    "download_all_examples": True,
    "abort_on_example_error": True,
    "run_stale_examples": True,
    "remove_config_comments": True,
    "image_scrapers": ("matplotlib",),
    "matplotlib_animations": False,
    "capture_repr": (),
    "within_subsection_order": "FileNameSortKey",
}
doctest_global_setup = "import blockchainkit as bk"
