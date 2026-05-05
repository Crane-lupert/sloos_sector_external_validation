"""SRF construction tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sloos_sector_external_validation.srf_construct import (
    FINANCIAL_SECTOR_CODE,
    _financial_gvkeys,
    _quarter_release_date,
    compute_daily_log_returns,
    quarterly_cross_sectional_skewness,
)


def test_financial_sector_constant():
    assert FINANCIAL_SECTOR_CODE == 40


def test_financial_gvkeys_filters_correctly():
    universe = pd.DataFrame(
        {
            "gvkey": ["1", "2", "3", "4"],
            "gsector": [40, 25, 40, None],
        }
    )
    keys = _financial_gvkeys(universe)
    assert set(keys) == {"1", "3"}


def test_quarter_release_date_buckets():
    # Daily date in Q1 (Jan-Mar) → release April 1
    assert _quarter_release_date(pd.Timestamp("2023-01-15")) == pd.Timestamp("2023-04-01")
    assert _quarter_release_date(pd.Timestamp("2023-03-31")) == pd.Timestamp("2023-04-01")
    # Q2 (Apr-Jun) → July 1
    assert _quarter_release_date(pd.Timestamp("2023-05-01")) == pd.Timestamp("2023-07-01")
    # Q4 (Oct-Dec) → next year January 1
    assert _quarter_release_date(pd.Timestamp("2023-12-15")) == pd.Timestamp("2024-01-01")


def test_compute_daily_log_returns_basic():
    df = pd.DataFrame(
        {
            "gvkey": ["1"] * 4,
            "datadate": pd.date_range("2023-01-02", periods=4, freq="B"),
            "prccd": [100.0, 101.0, 102.0, 99.0],
            "ajexdi": [1.0, 1.0, 1.0, 1.0],
        }
    )
    out = compute_daily_log_returns(df)
    assert len(out) == 3  # first row diff is NaN, drops
    expected_first = np.log(101.0 / 100.0)
    assert abs(out.iloc[0]["log_ret"] - expected_first) < 1e-9


def test_compute_daily_log_returns_drops_invalid_prices():
    df = pd.DataFrame(
        {
            "gvkey": ["1"] * 3,
            "datadate": pd.date_range("2023-01-02", periods=3, freq="B"),
            "prccd": [100.0, -1.0, 102.0],
            "ajexdi": [1.0, 1.0, 1.0],
        }
    )
    out = compute_daily_log_returns(df)
    # -1.0 is dropped, then 102 has no immediate predecessor in clean data
    assert (out["log_ret"].isfinite() if hasattr(out["log_ret"], "isfinite") else np.isfinite(out["log_ret"])).all()


def test_quarterly_skewness_meets_min_obs():
    # 5 firms × 6 days each = 30 obs (== threshold)
    rng = np.random.default_rng(0)
    rows = []
    for gv in range(5):
        for dt in pd.date_range("2023-01-02", periods=6, freq="B"):
            rows.append({"gvkey": str(gv), "datadate": dt, "log_ret": rng.normal(0, 0.02)})
    df = pd.DataFrame(rows)
    out = quarterly_cross_sectional_skewness(df)
    assert len(out) == 1
    assert out.iloc[0]["n_obs"] == 30


def test_quarterly_skewness_skips_thin_quarter():
    rows = [
        {"gvkey": "1", "datadate": pd.Timestamp("2023-01-02"), "log_ret": 0.01}
    ]
    df = pd.DataFrame(rows)
    out = quarterly_cross_sectional_skewness(df)
    assert out.empty


# Integration test on Day 6 snapshot
def test_real_srf_snapshot_present():
    cache = Path("data/cache")
    files = sorted(cache.glob("srf_*.parquet"))
    if not files:
        pytest.skip("no SRF snapshot")
    srf = pd.read_parquet(files[-1])
    assert {"quarter_release_date", "n_obs", "n_firms", "srf"} <= set(srf.columns)
    assert len(srf) >= 100, f"SRF too short: {len(srf)}"
    # Skewness should be bounded
    assert srf["srf"].abs().max() < 5.0
