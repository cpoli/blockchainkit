"""Test-session setup: force Matplotlib's non-interactive Agg backend before
anything imports pyplot, so the visualizer tests run headlessly, and close
every figure after each test so the suite doesn't accumulate open figures."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _close_all_figures():
    yield
    plt.close("all")
