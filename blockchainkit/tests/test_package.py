"""Package-level smoke tests: blockchainkit imports cleanly and every declared
subpackage re-exports a consistent public API."""

import importlib

import pytest

import blockchainkit as bk

SUBPACKAGES = ["crypto", "structures", "consensus", "network", "vm"]


def test_top_level_import_exposes_declared_names():
    for name in bk.__all__:
        assert hasattr(bk, name), f"blockchainkit.{name} listed in __all__ but not importable"


def test_version_is_a_dotted_string():
    assert isinstance(bk.__version__, str)
    assert bk.__version__.count(".") == 2


@pytest.mark.parametrize("subpackage", SUBPACKAGES)
def test_subpackage_all_resolves(subpackage):
    module = getattr(bk, subpackage)
    for name in module.__all__:
        assert hasattr(module, name), f"blockchainkit.{subpackage}.{name} is not importable"


@pytest.mark.parametrize("subpackage", SUBPACKAGES)
@pytest.mark.parametrize("layer", ["core", "systems"])
def test_every_layer_name_is_reexported_by_its_subpackage(subpackage, layer):
    module = getattr(bk, subpackage)
    inner = importlib.import_module(f"blockchainkit.{subpackage}.{layer}")
    missing = set(inner.__all__) - set(module.__all__)
    assert not missing, f"blockchainkit.{subpackage} does not re-export {sorted(missing)}"


def test_constants_match_their_documented_values():
    assert bk.constants.UINT64_LIMIT == 2**64
    assert bk.constants.WORD_MODULUS == 2**256
    assert bk.constants.DEFAULT_CHAIN_ID == "blockchainkit-demo"
    prefixes = {
        bk.constants.MERKLE_LEAF_PREFIX,
        bk.constants.MERKLE_NODE_PREFIX,
        bk.constants.MERKLE_ROOT_PREFIX,
    }
    assert len(prefixes) == 3
