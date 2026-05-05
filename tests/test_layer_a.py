"""Layer A tests — Welch t-test + Bonferroni-K=33."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sloos_sector_external_validation.layer_a import (
    ALPHA,
    K_BONFERRONI,
    _bonferroni_critical_t,
    _one_sample_ttest,
    layer_a_summary,
    run_layer_a,
)


def test_lock_constants():
    assert K_BONFERRONI == 33
    assert ALPHA == 0.05


def test_one_sample_ttest_recovers_known_mean():
    # Synthetic: mean=0.01, std=0.05, n=400 → t = 0.01 / (0.05/sqrt(400)) = 4.0
    rng = np.random.default_rng(42)
    x = rng.normal(0.01, 0.05, size=400)
    t, p, df = _one_sample_ttest(x)
    assert df == 399
    # Allow tolerance because of finite-sample noise
    assert 3.0 < abs(t) < 5.5
    assert p < 0.001


def test_one_sample_ttest_zero_mean_high_p():
    rng = np.random.default_rng(1)
    x = rng.normal(0.0, 0.05, size=400)
    t, p, df = _one_sample_ttest(x)
    assert df == 399
    # p should NOT be tiny (we expect p > 0.05 most of the time, but allow some randomness)
    assert p > 0.001


def test_one_sample_ttest_handles_n1():
    t, p, df = _one_sample_ttest(np.array([0.5]))
    assert np.isnan(t) and np.isnan(p)


def test_one_sample_ttest_handles_zero_std():
    t, p, df = _one_sample_ttest(np.array([0.5, 0.5, 0.5]))
    assert np.isnan(t) and np.isnan(p)


def test_bonferroni_critical_t_increases_with_k():
    # K=10 should require larger critical t than K=1
    crit_k1 = _bonferroni_critical_t(df=1000, k=1, alpha=0.05)
    crit_k10 = _bonferroni_critical_t(df=1000, k=10, alpha=0.05)
    crit_k33 = _bonferroni_critical_t(df=1000, k=33, alpha=0.05)
    assert crit_k1 < crit_k10 < crit_k33


def test_bonferroni_critical_t_close_to_3_18_at_k33():
    # At df=infty, K=33, alpha=0.05 two-sided: critical |t| ≈ 3.176
    crit = _bonferroni_critical_t(df=10_000, k=33, alpha=0.05)
    assert 3.10 < crit < 3.25


def test_run_layer_a_synthetic_panel():
    # Synthetic: 11 sectors × 3 horizons. Sector 40 has clear signal at 6m.
    rng = np.random.default_rng(7)
    parts = []
    for sector in (10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60):
        for horizon in ("1m", "3m", "6m"):
            n = 500
            mu = 0.01 if (sector == 40 and horizon == "6m") else 0.0
            car = rng.normal(mu, 0.05, size=n)
            parts.append(
                pd.DataFrame(
                    {
                        "sector": sector,
                        "horizon": horizon,
                        "car": car,
                        "shock_sign": rng.choice([-1, 1], size=n),
                    }
                )
            )
    panel = pd.concat(parts, ignore_index=True)
    res = run_layer_a(panel)
    assert len(res) == 33
    # Sector 40 × 6m should pass — it has 1% mean signal vs std 5%, n=500 → t ≈ 4.5
    target = res[(res["sector_code"] == 40) & (res["horizon"] == "6m")].iloc[0]
    assert abs(target["t_stat"]) > 3.0
    assert bool(target["abs_t_passes_bonferroni"])


def test_layer_a_summary_pass_threshold():
    res = pd.DataFrame(
        {
            "sector_code": [40, 35, 25, 45, 20, 10],
            "sector_name": ["Financials", "Healthcare", "ConsDisc", "IT", "Industrials", "Energy"],
            "horizon": ["1m"] * 6,
            "n": [100] * 6,
            "mean_car_bp": [0.0] * 6,
            "std_car": [0.0] * 6,
            "t_stat": [3.5, -3.5, 3.5, 3.5, 3.5, 0.5],
            "df": [99] * 6,
            "p_value": [0.001] * 5 + [0.6],
            "critical_t_bonferroni": [3.18] * 6,
            "abs_t_passes_bonferroni": [True, True, True, True, True, False],
        }
    )
    summ = layer_a_summary(res, threshold_pass=5)
    assert summ["n_cells"] == 6
    assert summ["n_pass_bonferroni"] == 5
    assert summ["pass_phase1_floor_5"] is True


def test_layer_a_summary_fails_below_threshold():
    res = pd.DataFrame(
        {
            "sector_code": [40, 35, 25],
            "sector_name": ["A", "B", "C"],
            "horizon": ["1m", "3m", "6m"],
            "n": [100, 100, 100],
            "mean_car_bp": [0.0, 0.0, 0.0],
            "std_car": [0.0, 0.0, 0.0],
            "t_stat": [3.5, 3.5, 1.0],
            "df": [99, 99, 99],
            "p_value": [0.001, 0.001, 0.3],
            "critical_t_bonferroni": [3.18, 3.18, 3.18],
            "abs_t_passes_bonferroni": [True, True, False],
        }
    )
    summ = layer_a_summary(res, threshold_pass=5)
    assert summ["n_pass_bonferroni"] == 2
    assert summ["pass_phase1_floor_5"] is False


# Integration test on Day 4 snapshot
def test_real_panel_layer_a_passes_phase1_floor():
    cache = Path("data/cache")
    files = sorted(cache.glob("sector_panel_*.parquet"))
    if not files:
        pytest.skip("no panel snapshot")
    panel = pd.read_parquet(files[-1])
    res = run_layer_a(panel)
    summ = layer_a_summary(res, threshold_pass=5)
    assert summ["pass_phase1_floor_5"], (
        f"Layer A FAIL: {summ['n_pass_bonferroni']} / 33 cells significant, need ≥5"
    )
    assert summ["n_pass_bonferroni"] >= 10, f"weak signal: only {summ['n_pass_bonferroni']} sig"
