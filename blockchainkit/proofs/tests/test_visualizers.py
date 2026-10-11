"""Smoke tests for blockchainkit.proofs.visualizers."""

import matplotlib.pyplot as plt
import pytest

from blockchainkit.proofs import PlonkCircuit, plonk_setup, trusted_setup
from blockchainkit.proofs.visualizers import (
    plot_copy_constraints,
    plot_field_polynomials,
    plot_proof_sizes,
)


def test_plot_field_polynomials_rings_the_agreements():
    ax = plot_field_polynomials({"f": [0, 1], "g": [0, 0, 1]}, 13)
    labels = [text.get_text() for text in ax.get_legend().get_texts()]
    assert "agree at 2 of 13 points" in labels
    _, given = plt.subplots()
    assert plot_field_polynomials({"f": [1]}, 7, ax=given) is given
    with pytest.raises(ValueError):
        plot_field_polynomials({}, 7)
    with pytest.raises(ValueError):
        plot_field_polynomials({"f": [1]}, 4001)


def test_plot_proof_sizes_uses_log_axes():
    ax = plot_proof_sizes({"a": [(2, 10), (4, 20)], "b": [(2, 5), (4, 5)]}, xlabel="n")
    assert len(ax.lines) == 2 and ax.get_xscale() == "log" and ax.get_xlabel() == "n"
    _, given = plt.subplots()
    assert plot_proof_sizes({"a": [(1, 1)]}, ax=given) is given
    with pytest.raises(ValueError):
        plot_proof_sizes({"a": []})


def test_plot_copy_constraints_joins_each_variable():
    circuit = PlonkCircuit()
    x = circuit.variable(3)
    circuit.assert_constant(circuit.mul(x, x), 9)
    key = plonk_setup(circuit, trusted_setup(8, 5))
    ax = plot_copy_constraints(key)
    assert "variables on 6 wire positions" in ax.get_title()
    _, given = plt.subplots()
    lone = PlonkCircuit()
    v = lone.variable(3)
    lone.mul(v, v)  # The product appears on one wire only.
    assert plot_copy_constraints(plonk_setup(lone, trusted_setup(8, 5)), ax=given) is given
