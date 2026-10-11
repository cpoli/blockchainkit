"""Smoke tests for blockchainkit.contracts.visualizers."""

import matplotlib.pyplot as plt
import pytest

from blockchainkit.contracts import ERC20, Receipt, World, symbolic_execute
from blockchainkit.contracts.visualizers import (
    plot_call_tree,
    plot_storage,
    plot_symbolic_paths,
)


def _receipt():
    world = World()
    token = world.deploy("alice", ERC20, 10)
    return world, world.transact("alice", token, "transfer", "bob", 20)


def test_plot_call_tree_marks_reverts():
    world, receipt = _receipt()
    ax = plot_call_tree(receipt, names=world.name)
    assert "reverted" in ax.get_title() and "insufficient balance" in ax.texts[0].get_text()
    _, given = plt.subplots()
    assert plot_call_tree(receipt, ax=given) is given
    with pytest.raises(ValueError, match="no calls"):
        plot_call_tree(Receipt(True, None, None, 0, (), ()))


def test_plot_call_tree_shows_nested_and_delegated_calls():
    from blockchainkit.contracts import BoxV1, EIP1967Proxy

    world = World()
    proxy = world.deploy("dev", EIP1967Proxy, world.deploy("dev", BoxV1))
    world.fund("dev", 5)
    receipt = world.transact("alice", proxy, "initialize")
    ax = plot_call_tree(receipt)
    assert "storage of" in ax.texts[1].get_text() and "succeeded" in ax.get_title()
    paid = World()
    paid.fund("a", 5)
    payment = paid.transact("a", "b", value=5)
    assert "receive {value: 5}" in plot_call_tree(payment).texts[0].get_text()


def test_plot_symbolic_paths_draws_one_marker_per_leaf():
    result = symbolic_execute("require(x > 1)\nif x > 5:\n    y = 1\nassert y == 1")
    ax = plot_symbolic_paths(result)
    assert len([text for text in ax.texts]) == len(result.paths)
    assert "x" in ax.get_title()
    _, given = plt.subplots()
    assert plot_symbolic_paths(symbolic_execute("y = 1"), ax=given) is given
    with pytest.raises(ValueError, match="no paths"):
        plot_symbolic_paths(type(result)((), (), True))


def test_plot_storage_names_slots():
    ax = plot_storage({0: "0x" + "ab" * 20, 1: 7}, fields={0: "implementation"})
    cells = {cell.get_text().get_text() for cell in ax.tables[0].get_celld().values()}
    assert "implementation" in cells and "7" in cells
    _, given = plt.subplots()
    assert plot_storage({}, ax=given, title="empty") is given
    assert given.texts[0].get_text() == "empty"
