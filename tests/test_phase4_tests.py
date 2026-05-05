"""Unit tests for Phase 4 PRIMARY robustness tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sloos_sector_external_validation.phase4_tests import (
    run_test_a_ftest,
    run_test_b_bootstrap,
    run_test_d_vix_regime,
)


# ============================================================
# Test A — F-test sector heterogeneity
# ============================================================

def _make_synthetic_panel(n_events: int = 30, n_sectors: int = 11, with_signal: bool = True):
    """Make a synthetic panel with optional sector heterogeneity signal."""
    rng = np.random.default_rng(42)
    rows = []
    sector_offsets = rng.normal(0, 0.05, size=n_sectors) if with_signal else np.zeros(n_sectors)
    for evt_idx in range(n_events):
        evt = pd.Timestamp("2000-01-01") + pd.Timedelta(days=90 * evt_idx)
        for s_idx, sector in enumerate(range(10, 65, 5)[:n_sectors]):
            n_firms = rng.integers(50, 300)
            for h in ("1m", "3m", "6m"):
                cars = rng.normal(sector_offsets[s_idx], 0.10, size=n_firms)
                for car in cars:
                    rows.append(
                        {
                            "event_date": evt,
                            "sector": sector,
                            "horizon": h,
                            "car": float(car),
                            "shock_sign": int(rng.choice([-1, 1])),
                        }
                    )
    return pd.DataFrame(rows)


def test_run_test_a_ftest_with_signal_passes():
    panel = _make_synthetic_panel(n_events=30, n_sectors=11, with_signal=True)
    res = run_test_a_ftest(panel)
    assert len(res) == 3  # 3 horizons
    assert res["pass_at_05"].any()


def test_run_test_a_ftest_no_signal_fails():
    panel = _make_synthetic_panel(n_events=30, n_sectors=11, with_signal=False)
    res = run_test_a_ftest(panel)
    # All sectors have same mean (=0) → F-test should NOT reject H_0 systematically
    assert len(res) == 3
    assert int(res["pass_at_05"].sum()) <= 1  # type-I error allowed at 1/3 horizons


def test_run_test_a_ftest_shape_and_columns():
    panel = _make_synthetic_panel(n_events=12, n_sectors=11)
    res = run_test_a_ftest(panel)
    expected = {"horizon", "f_stat", "p_value", "df_between", "df_within", "n_sectors", "pass_at_05"}
    assert expected <= set(res.columns)


# ============================================================
# Test B — Bootstrap
# ============================================================

def test_run_test_b_bootstrap_runs_and_returns_expected_shape():
    panel = _make_synthetic_panel(n_events=12, n_sectors=11, with_signal=True)
    res = run_test_b_bootstrap(panel, n_iterations=50, seed=42)
    # 11 sectors × 3 horizons = 33 rows max
    assert len(res) <= 33
    assert "share_pass_bonferroni" in res.columns
    assert "ci_lower_pass_bonferroni" in res.columns


def test_run_test_b_bootstrap_share_in_unit_interval():
    panel = _make_synthetic_panel(n_events=15, n_sectors=11, with_signal=True)
    res = run_test_b_bootstrap(panel, n_iterations=30, seed=42)
    assert (res["share_pass_bonferroni"] >= 0).all()
    assert (res["share_pass_bonferroni"] <= 1).all()


def test_run_test_b_bootstrap_q05_le_q95():
    panel = _make_synthetic_panel(n_events=15, n_sectors=11, with_signal=True)
    res = run_test_b_bootstrap(panel, n_iterations=30, seed=42)
    assert (res["abs_t_q05"] <= res["abs_t_q95"]).all()


# ============================================================
# Test D — VIX-regime
# ============================================================

def test_run_test_d_vix_regime_basic():
    panel = _make_synthetic_panel(n_events=12, n_sectors=11)
    # Synthetic VIX: half events high, half low
    vix_series = pd.Series(
        [30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0],
        index=panel["event_date"].drop_duplicates().sort_values().tolist(),
    )
    ecsi = pd.DataFrame({"vix": vix_series})
    ecsi.index.name = "quarter_release_date"
    out = run_test_d_vix_regime(panel, ecsi, vix_threshold_high=25, vix_threshold_low=20)
    assert "n_events_high_vix" in out
    assert "n_events_low_vix" in out
    assert out["n_events_high_vix"] == 6
    assert out["n_events_low_vix"] == 6


def test_run_test_d_vix_regime_pass_logic():
    panel = _make_synthetic_panel(n_events=12, n_sectors=11)
    vix_series = pd.Series(
        [30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0],
        index=panel["event_date"].drop_duplicates().sort_values().tolist(),
    )
    ecsi = pd.DataFrame({"vix": vix_series})
    ecsi.index.name = "quarter_release_date"
    out = run_test_d_vix_regime(panel, ecsi, vix_threshold_high=25, vix_threshold_low=20)
    # pass field should be a bool
    assert isinstance(out["pass"], bool)


# ============================================================
# Integration tests on Phase 4 cached results
# ============================================================

def test_phase4_test_a_csv_present_and_passes():
    f = Path("data/cache/phase4_test_a_ftest.csv")
    if not f.exists():
        pytest.skip("Phase 4 test A CSV not generated yet")
    df = pd.read_csv(f)
    assert df["pass_at_05"].any(), "F-test should pass at >=1 horizon"


def test_phase4_test_c_csv_present_and_strong():
    f = Path("data/cache/phase4_test_c_drtscis_corr.csv")
    if not f.exists():
        pytest.skip("Phase 4 test C CSV not generated yet")
    df = pd.read_csv(f)
    # Phase 4 lock criterion: Spearman >= 0.5 at >=1 horizon
    assert (df["spearman_rho"] >= 0.5).any()


def test_phase4_test_b_csv_robust_cells_present():
    f = Path("data/cache/phase4_test_b_bootstrap.csv")
    if not f.exists():
        pytest.skip("Phase 4 test B CSV not generated yet")
    df = pd.read_csv(f)
    # Refined criterion: >=5 cells with share_pass >= 0.70
    n_robust = int((df["share_pass_bonferroni"] >= 0.70).sum())
    assert n_robust >= 5, f"Only {n_robust} cells with bootstrap share_pass>=0.70"
