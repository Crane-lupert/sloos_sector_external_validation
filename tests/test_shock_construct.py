"""Shock construction tests (Phase 0 §1.1 amended lock — AR(1) innovation)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sloos_sector_external_validation.shock_construct import (
    AR_ORDER,
    SVB_COHORT_START,
    Z_THRESHOLD,
    construct_shocks,
    event_dates,
    event_summary,
    fit_ar_residual,
    flag_events,
)


@pytest.fixture
def synthetic_panel():
    """Synthetic AR(1) DRTSCILM-like series with known structure for unit tests."""
    rng = np.random.default_rng(42)
    n = 145
    rho = 0.85
    sigma = 10.0
    eps = rng.normal(0, sigma, size=n)
    s = np.zeros(n)
    s[0] = 0.0
    for t in range(1, n):
        s[t] = 0.5 + rho * s[t - 1] + eps[t]
    idx = pd.date_range("1990-04-01", periods=n, freq="QS-OCT")
    return pd.DataFrame({"DRTSCILM": s}, index=idx)


def test_lock_constants_match_amendment():
    # Phase 0 §1.1 amended: AR(1), threshold 1.0σ
    assert AR_ORDER == 1
    assert Z_THRESHOLD == 1.0


def test_svb_cohort_start_is_2023_q3():
    assert SVB_COHORT_START == pd.Timestamp("2023-07-01")


def test_fit_ar_residual_recovers_rho_within_tolerance(synthetic_panel):
    # Should recover the synthetic rho=0.85 within ±0.05
    z = fit_ar_residual(synthetic_panel["DRTSCILM"], order=1)
    assert abs(z.attrs["ar_rho"] - 0.85) < 0.10
    assert z.attrs["ar_order"] == 1


def test_fit_ar_residual_first_obs_has_nan_residual(synthetic_panel):
    z = fit_ar_residual(synthetic_panel["DRTSCILM"], order=1)
    # AR(1) needs lag-1, so first obs has no residual
    assert pd.isna(z["residual"].iloc[0])
    assert z["residual"].iloc[1:].notna().all()


def test_flag_events_threshold_applied():
    # Direct test: |z|>1.0 should fire
    df = pd.DataFrame(
        {
            "raw": [10.0, 20.0, 30.0, 40.0, 5.0],
            "fitted": [9.5, 19.5, 29.5, 39.5, 4.5],
            "residual": [0.5, 0.5, 12.0, -15.0, 0.5],
            "z_innov": [0.05, 0.05, 1.2, -1.5, 0.05],
        }
    )
    out = flag_events(df, threshold=1.0)
    assert out["is_shock"].tolist() == [False, False, True, True, False]
    assert out["shock_sign"].tolist() == [0, 0, 1, -1, 0]


def test_construct_shocks_end_to_end(synthetic_panel):
    shocks = construct_shocks(synthetic_panel)
    # Required columns
    for col in ("raw", "fitted", "residual", "z_innov", "is_shock", "shock_sign", "is_event_start", "is_svb_cohort"):
        assert col in shocks.columns
    # AR attrs preserved
    assert "ar_rho" in shocks.attrs
    # Synthetic events should be present (~16% of obs at threshold 1.0σ)
    n_events = int(shocks["is_event_start"].sum())
    assert 10 <= n_events <= 50, f"n_events={n_events} outside expected band 10-50"


def test_event_summary_keys(synthetic_panel):
    shocks = construct_shocks(synthetic_panel)
    summ = event_summary(shocks)
    expected = {
        "n_events_total",
        "n_events_tightening",
        "n_events_easing",
        "events_by_decade",
        "n_svb_cohort",
        "n_pre_svb",
        "first_event",
        "last_event",
        "ar_alpha",
        "ar_rho",
        "sigma_eps",
    }
    assert expected <= set(summ.keys())


def test_event_summary_signs_sum_to_total(synthetic_panel):
    shocks = construct_shocks(synthetic_panel)
    summ = event_summary(shocks)
    assert summ["n_events_tightening"] + summ["n_events_easing"] == summ["n_events_total"]


def test_event_summary_svb_split_consistent(synthetic_panel):
    shocks = construct_shocks(synthetic_panel)
    summ = event_summary(shocks)
    assert summ["n_pre_svb"] + summ["n_svb_cohort"] == summ["n_events_total"]


def test_construct_shocks_missing_primary_raises():
    panel = pd.DataFrame({"OTHER": [1, 2, 3]})
    with pytest.raises(KeyError):
        construct_shocks(panel)


# Integration test on real Day 2 snapshot
def test_real_drtscilm_events_meet_amended_floor():
    cache_dir = Path("data/cache")
    files = sorted(cache_dir.glob("sloos_series_*.parquet"))
    if not files:
        pytest.skip("no SLOOS parquet snapshot available")
    panel = pd.read_parquet(files[-1])
    if "DRTSCILM" not in panel.columns:
        pytest.skip("DRTSCILM not in panel")
    shocks = construct_shocks(panel)
    summ = event_summary(shocks)
    # Phase 0 §7 amended floor: events ≥ 30, SVB cohort ≥ 1
    assert summ["n_events_total"] >= 30, f"events={summ['n_events_total']} < 30 floor"
    assert summ["n_svb_cohort"] >= 1, f"SVB cohort={summ['n_svb_cohort']} < 1 floor"


def test_real_drtscilm_ar_rho_high_persistence():
    cache_dir = Path("data/cache")
    files = sorted(cache_dir.glob("sloos_series_*.parquet"))
    if not files:
        pytest.skip("no SLOOS parquet snapshot available")
    panel = pd.read_parquet(files[-1])
    if "DRTSCILM" not in panel.columns:
        pytest.skip("DRTSCILM not in panel")
    shocks = construct_shocks(panel)
    # Expected ρ ≈ 0.86 — high persistence is the reason we use AR(1) innovation,
    # not level z-score. If ρ ever drops below 0.5, lock §1.1 amendment rationale
    # weakens and should be re-audited.
    assert shocks.attrs["ar_rho"] > 0.5, f"AR(1) ρ={shocks.attrs['ar_rho']:.3f} < 0.5"
    assert shocks.attrs["ar_rho"] < 1.0, f"AR(1) ρ={shocks.attrs['ar_rho']:.3f} >= 1.0 (non-stationary)"
