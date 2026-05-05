"""Sector panel tests — synthetic + Day 3 snapshot integration."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sloos_sector_external_validation.sector_panel import (
    HORIZONS_TD,
    PRIMARY_IID,
    _per_firm_event_returns,
    panel_summary,
    per_cell_audit,
)


def test_horizons_td_constants():
    assert HORIZONS_TD == {"1m": 21, "3m": 63, "6m": 126}


def test_primary_iid_constant():
    assert PRIMARY_IID == "01"


def test_per_firm_event_returns_basic():
    # 200 trading days of synthetic prices, 1 event at index 50
    dates = pd.date_range("2010-01-01", periods=200, freq="B")
    prices = np.linspace(100.0, 200.0, 200)
    df = pd.DataFrame({"datadate": dates, "adj_p": prices})
    event = pd.DatetimeIndex([dates[50]])
    out = _per_firm_event_returns(df, event, {"1m": 21, "3m": 63})
    assert len(out) == 2
    # 1m return: log(prices[71]/prices[50])
    expected_1m = np.log(prices[71] / prices[50])
    expected_3m = np.log(prices[113] / prices[50])
    assert abs(out[0][7] - expected_1m) < 1e-9
    assert abs(out[1][7] - expected_3m) < 1e-9


def test_per_firm_event_returns_truncation():
    # Event near series end — 6m horizon should be skipped
    dates = pd.date_range("2010-01-01", periods=100, freq="B")
    prices = np.linspace(100.0, 200.0, 100)
    df = pd.DataFrame({"datadate": dates, "adj_p": prices})
    event = pd.DatetimeIndex([dates[80]])
    out = _per_firm_event_returns(df, event, {"1m": 21, "3m": 63, "6m": 126})
    horizons = [h for _, h, *_ in out]
    # 1m: 80+21=101 (>=100, OOB) — skipped
    # 3m: 80+63=143 OOB skipped
    # 6m: OOB skipped
    assert "1m" not in horizons
    assert "3m" not in horizons
    assert "6m" not in horizons


def test_per_firm_event_returns_empty_after_event():
    dates = pd.date_range("2010-01-01", periods=20, freq="B")
    df = pd.DataFrame({"datadate": dates, "adj_p": np.full(20, 100.0)})
    event = pd.DatetimeIndex([pd.Timestamp("2020-01-01")])  # after data ends
    out = _per_firm_event_returns(df, event, {"1m": 21})
    assert out == []


def test_per_firm_event_returns_invalid_price_skipped():
    dates = pd.date_range("2010-01-01", periods=200, freq="B")
    prices = np.full(200, 100.0)
    prices[50] = -1.0  # invalid t0
    df = pd.DataFrame({"datadate": dates, "adj_p": prices})
    event = pd.DatetimeIndex([dates[50]])
    out = _per_firm_event_returns(df, event, {"1m": 21})
    assert out == []


# Integration tests on Day 3 snapshot
def test_panel_summary_meets_phase0_floors():
    cache = Path("data/cache")
    files = sorted(cache.glob("sector_panel_*.parquet"))
    if not files:
        pytest.skip("no Day 3 sector_panel snapshot available")
    panel = pd.read_parquet(files[-1])
    summary = panel_summary(panel)
    assert summary["n_events"] >= 30, f"events {summary['n_events']} < 30"
    assert summary["n_sectors_present"] == 11, f"sectors present {summary['n_sectors_present']} != 11"
    assert summary["n_horizons"] == 3, f"horizons {summary['n_horizons']} != 3"


def test_per_cell_n_min_floor():
    cache = Path("data/cache")
    files = sorted(cache.glob("sector_panel_*.parquet"))
    if not files:
        pytest.skip("no Day 3 sector_panel snapshot available")
    panel = pd.read_parquet(files[-1])
    audit = per_cell_audit(panel, n_min=50)
    unsigned = audit[audit["scope"] == "unsigned"]
    assert len(unsigned) == 33, f"expected 33 unsigned cells, got {len(unsigned)}"
    assert int(unsigned["pass_n_min"].sum()) == 33, f"unsigned cells passing: {unsigned['pass_n_min'].sum()} / 33"


def test_layer_a_preview_meets_floor():
    """At least 5 unsigned cells should already pass Bonferroni-K=33 critical t=3.04."""
    cache = Path("data/cache")
    files = sorted(cache.glob("sector_panel_*.parquet"))
    if not files:
        pytest.skip("no Day 3 sector_panel snapshot available")
    panel = pd.read_parquet(files[-1])
    audit = per_cell_audit(panel, n_min=50)
    unsigned = audit[audit["scope"] == "unsigned"]
    n_significant = int((unsigned["t_stat"].abs() >= 3.04).sum())
    assert n_significant >= 5, f"Phase 1 §7 floor: only {n_significant} cells at |t|>=3.04, need >=5"


def test_mean_abs_car_above_cost_wall_floor():
    """CLAUDE.md §7 floor: EDA mean |sector CAR| ≥ 20bp at all horizons."""
    cache = Path("data/cache")
    files = sorted(cache.glob("sector_panel_*.parquet"))
    if not files:
        pytest.skip("no Day 3 sector_panel snapshot available")
    panel = pd.read_parquet(files[-1])
    audit = per_cell_audit(panel, n_min=50)
    unsigned = audit[audit["scope"] == "unsigned"]
    by_horizon = unsigned.groupby("horizon")["mean_car_bp"].apply(lambda s: s.abs().mean())
    for h, val in by_horizon.items():
        assert val >= 20.0, f"horizon {h} mean |sector CAR| {val:.1f}bp < 20bp floor"
