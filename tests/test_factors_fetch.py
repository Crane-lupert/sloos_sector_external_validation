"""Ken French factor fetcher tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sloos_sector_external_validation.factors_fetch import (
    KEN_FRENCH_URLS,
    _parse_french_csv,
    cumulative_factor_return,
)


def test_french_urls_present():
    assert "ff5_daily" in KEN_FRENCH_URLS
    assert "mom_daily" in KEN_FRENCH_URLS
    for url in KEN_FRENCH_URLS.values():
        assert url.startswith("https://")


def test_parse_french_csv_basic():
    text = (
        "Some metadata header\n"
        "More header\n"
        ",Mkt-RF,SMB,HML,RMW,CMA,RF\n"
        "20100104,0.50,0.10,-0.20,0.05,0.15,0.01\n"
        "20100105,-0.30,0.20,0.10,-0.05,-0.10,0.01\n"
        "\n"
        "20101231,1.50,0.30,-0.40,0.10,0.20,0.04\n"
    )
    df = _parse_french_csv(text)
    assert {"Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"} <= set(df.columns)
    # 2 daily rows before the blank
    assert len(df) == 2
    # Decimal conversion
    assert abs(df.iloc[0]["Mkt-RF"] - 0.005) < 1e-9


def test_cumulative_factor_return_sums():
    idx = pd.date_range("2020-01-02", periods=10, freq="B")
    factors = pd.DataFrame(
        {
            "Mkt-RF": [0.01] * 10,
            "Mom": [0.005] * 10,
        },
        index=idx,
    )
    cum = cumulative_factor_return(factors, start=idx[0], horizon_td=4)
    # 5 daily values summed (indices 0..4)
    assert abs(cum["Mkt-RF"] - 0.05) < 1e-9
    assert abs(cum["Mom"] - 0.025) < 1e-9


def test_cumulative_factor_return_oob():
    idx = pd.date_range("2020-01-02", periods=5, freq="B")
    factors = pd.DataFrame({"Mkt-RF": [0.01] * 5}, index=idx)
    cum = cumulative_factor_return(factors, start=idx[0], horizon_td=10)
    # horizon exceeds available days → NaN
    assert cum.isna().all()


# Integration test on Day 8 snapshot
def test_real_factors_snapshot_present():
    cache = Path("data/cache")
    files = sorted(cache.glob("ff5_mom_daily_*.parquet"))
    if not files:
        pytest.skip("no FF5+Mom snapshot")
    df = pd.read_parquet(files[-1])
    expected = {"Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF", "Mom"}
    assert expected <= set(df.columns)
    assert len(df) > 5000
