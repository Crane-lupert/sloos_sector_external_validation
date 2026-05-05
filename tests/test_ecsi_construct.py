"""E-CSI proxy tests."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sloos_sector_external_validation.ecsi_construct import (
    MACRO_SERIES,
    fit_ecsi_proxy,
)


def test_macro_series_keys():
    assert {"unrate", "t10y3m", "gdpc1", "vix"} == set(MACRO_SERIES.keys())


def test_fit_ecsi_proxy_synthetic():
    rng = np.random.default_rng(42)
    n = 100
    idx = pd.date_range("2000-04-01", periods=n, freq="QS-OCT")
    macro = pd.DataFrame(
        {
            "x1": rng.normal(0, 1, size=n),
            "x2": rng.normal(0, 1, size=n),
        },
        index=idx,
    )
    # y_t = 0.5 + 2 * x1_{t-1} - 1 * x2_{t-1} + noise
    x1_lag = macro["x1"].shift(1).fillna(0).to_numpy()
    x2_lag = macro["x2"].shift(1).fillna(0).to_numpy()
    y_arr = 0.5 + 2.0 * x1_lag - 1.0 * x2_lag + rng.normal(0, 0.1, size=n)
    y = pd.Series(y_arr, index=idx)
    fitted, resid, stats = fit_ecsi_proxy(y, macro)
    # Coefficients should be close to (0.5, 2, -1)
    assert abs(stats["const"] - 0.5) < 0.2
    assert abs(stats["x1_lag1"] - 2.0) < 0.2
    assert abs(stats["x2_lag1"] + 1.0) < 0.2
    assert stats["r_squared"] > 0.95


def test_fit_ecsi_proxy_orthogonality():
    """Fitted values must be orthogonal to residuals (OLS property)."""
    rng = np.random.default_rng(7)
    n = 80
    idx = pd.date_range("2000-04-01", periods=n, freq="QS-OCT")
    macro = pd.DataFrame({"x1": rng.normal(0, 1, size=n)}, index=idx)
    y = pd.Series(rng.normal(0, 1, size=n), index=idx)
    fitted, resid, _ = fit_ecsi_proxy(y, macro)
    aligned = pd.concat([fitted, resid], axis=1).dropna()
    corr = float(np.corrcoef(aligned.iloc[:, 0], aligned.iloc[:, 1])[0, 1])
    assert abs(corr) < 1e-8


def test_fit_ecsi_proxy_too_short_raises():
    n = 20
    idx = pd.date_range("2000-04-01", periods=n, freq="QS-OCT")
    macro = pd.DataFrame({"x1": np.zeros(n)}, index=idx)
    y = pd.Series(np.zeros(n), index=idx)
    with pytest.raises(ValueError):
        fit_ecsi_proxy(y, macro)


# Integration test on Day 7 snapshot
@pytest.mark.skipif(
    not os.environ.get("FRED_API_KEY", "").strip(),
    reason="FRED_API_KEY not set",
)
def test_real_ecsi_snapshot_present():
    cache = Path("data/cache")
    files = sorted(cache.glob("ecsi_*.parquet"))
    if not files:
        pytest.skip("no E-CSI snapshot")
    ecsi = pd.read_parquet(files[-1])
    assert "ecsi" in ecsi.columns
    assert "ecsi_residual" in ecsi.columns
    # R² should be substantial
    aligned = ecsi.dropna(subset=["ecsi", "ecsi_residual"])
    corr = float(np.corrcoef(aligned["ecsi"], aligned["ecsi_residual"])[0, 1])
    assert abs(corr) < 1e-6, f"orthogonality broken: corr={corr}"
