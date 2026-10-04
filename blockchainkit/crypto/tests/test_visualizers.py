"""Smoke tests for blockchainkit.crypto.visualizers."""

import matplotlib.axes
import pytest

import blockchainkit as bk
from blockchainkit.crypto.visualizers import plot_curve_points, plot_hamming_distances


def test_plot_curve_points_draws_every_point_and_labels_the_subgroup():
    curve = bk.crypto.TOY_CURVE
    ax = plot_curve_points(curve)
    assert isinstance(ax, matplotlib.axes.Axes)
    assert len(ax.collections[0].get_offsets()) == curve.order - 1
    assert len(ax.texts) == curve.order - 1
    assert "19 points" in ax.get_title()
    assert not plot_curve_points(curve, label_multiples=False).texts


def test_plot_hamming_distances_overlays_the_binomial():
    message = b"avalanche"
    base = bk.crypto.sha256(message)
    distances = [
        bk.crypto.hamming_distance(
            base, bk.crypto.sha256(bytes([message[0] ^ (1 << bit)]) + message[1:])
        )
        for bit in range(8)
    ]
    ax = plot_hamming_distances(distances)
    assert isinstance(ax, matplotlib.axes.Axes)
    assert ax.lines[0].get_ydata().sum() == pytest.approx(1, abs=0.01)
