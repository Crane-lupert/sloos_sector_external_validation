"""Layer D absorption test — synthetic + Day 8-9 snapshot integration."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sloos_sector_external_validation.layer_d import (
    DEFAULT_HORIZON_LABEL,
    DELTA_SHARPE_FLOOR,
    HORIZON_TD,
    annualize_per_event,
    compute_pre_event_ivol_proxy,
    compute_strategy_returns,
    select_long_short_sectors,
)


def test_lock_constants():
    assert HORIZON_TD == 126
    assert DEFAULT_HORIZON_LABEL == "6m"
    assert DELTA_SHARPE_FLOOR == 0.40


def test_select_long_short_sectors_picks_passing_signed():
    layer_a = pd.DataFrame(
        {
            "sector_code": [40, 35, 25, 45, 20],
            "horizon": ["6m"] * 5,
            "t_stat": [+5.0, -8.0, +3.5, -4.5, +1.5],
            "abs_t_passes_bonferroni": [True, True, True, True, False],
        }
    )
    long, short = select_long_short_sectors(layer_a, horizon="6m")
    assert sorted(long) == [25, 40]
    assert sorted(short) == [35, 45]


def test_select_long_short_sectors_horizon_filter():
    layer_a = pd.DataFrame(
        {
            "sector_code": [40, 40],
            "horizon": ["1m", "6m"],
            "t_stat": [+5.0, -5.0],
            "abs_t_passes_bonferroni": [True, True],
        }
    )
    long6, short6 = select_long_short_sectors(layer_a, horizon="6m")
    assert long6 == [] and short6 == [40]
    long1, short1 = select_long_short_sectors(layer_a, horizon="1m")
    assert long1 == [40] and short1 == []


def test_compute_strategy_returns_long_short_spread():
    panel = pd.DataFrame(
        {
            "event_date": pd.to_datetime(["2020-01-01"] * 4),
            "horizon": ["6m"] * 4,
            "sector": [40, 40, 35, 35],
            "log_ret": [0.10, 0.12, -0.05, -0.07],
        }
    )
    strat = compute_strategy_returns(panel, long_sectors=[40], short_sectors=[35], horizon="6m")
    assert len(strat) == 1
    # long mean = 0.11, short mean = -0.06, strat = 0.17
    assert abs(strat.iloc[0]["strategy_ret"] - 0.17) < 1e-9


def test_compute_strategy_returns_skips_event_with_empty_basket():
    panel = pd.DataFrame(
        {
            "event_date": pd.to_datetime(["2020-01-01"] * 2),
            "horizon": ["6m"] * 2,
            "sector": [40, 40],
            "log_ret": [0.10, 0.12],
        }
    )
    strat = compute_strategy_returns(panel, long_sectors=[40], short_sectors=[35], horizon="6m")
    # short_sectors=35 has no firms in panel → event skipped
    assert strat.empty


def test_compute_pre_event_ivol_proxy():
    idx = pd.date_range("2020-01-02", periods=100, freq="B")
    rng = np.random.default_rng(42)
    factors = pd.DataFrame(
        {"Mkt-RF": rng.normal(0.001, 0.01, size=100)},
        index=idx,
    )
    ivol = compute_pre_event_ivol_proxy(factors, idx[80], lookback_days=60)
    assert 0.005 < ivol < 0.020


def test_compute_pre_event_ivol_proxy_too_thin():
    idx = pd.date_range("2020-01-02", periods=10, freq="B")
    factors = pd.DataFrame({"Mkt-RF": [0.001] * 10}, index=idx)
    # Lookback 60 but only 9 days available pre-event → NaN
    ivol = compute_pre_event_ivol_proxy(factors, idx[5], lookback_days=60)
    assert np.isnan(ivol)


def test_annualize_per_event_scales():
    # 36 events over ~35 years → ~1 event/year → no scaling
    a = annualize_per_event(1.0, n_events=36, span_days=35 * 365)
    assert 0.95 < a < 1.05


def test_annualize_per_event_zero_span():
    a = annualize_per_event(1.0, n_events=2, span_days=0)
    assert np.isnan(a)


# Integration test on Day 8-9 snapshot
def test_real_layer_d_passes_phase1_floor():
    """Phase 1 §7 lock: Δ Sharpe ≥ 0.40."""
    from sloos_sector_external_validation.layer_d import run_layer_d

    cache = Path("data/cache")
    panel_files = sorted(cache.glob("sector_panel_*.parquet"))
    layer_a_files = sorted(cache.glob("layer_a_results_*.parquet"))
    factors_files = sorted(cache.glob("ff5_mom_daily_*.parquet"))
    srf_files = sorted(cache.glob("srf_*.parquet"))
    ecsi_files = sorted(cache.glob("ecsi_*.parquet"))

    if not (panel_files and layer_a_files and factors_files and srf_files and ecsi_files):
        pytest.skip("Day 8-9 snapshots not all available")

    panel = pd.read_parquet(panel_files[-1])
    layer_a = pd.read_parquet(layer_a_files[-1])
    factors = pd.read_parquet(factors_files[-1])
    srf = pd.read_parquet(srf_files[-1])
    ecsi = pd.read_parquet(ecsi_files[-1])

    result = run_layer_d(panel, layer_a, factors, srf, ecsi, horizon="6m", horizon_td=126)
    assert result.pass_phase1_floor, (
        f"Layer D FAIL: Δ Sharpe={result.delta_sharpe:.3f} < {DELTA_SHARPE_FLOOR} floor"
    )
    assert result.delta_sharpe >= DELTA_SHARPE_FLOOR, (
        f"Δ Sharpe {result.delta_sharpe:.3f} < {DELTA_SHARPE_FLOOR} floor"
    )
