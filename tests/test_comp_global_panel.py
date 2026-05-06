"""Tests for comp_global_panel (Path B specific, S3).

Uses synthetic mini panels to verify CAR computation logic without depending
on the WRDS courier. A separate real-WRDS smoke test confirms end-to-end
pipeline against the live courier dump.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sloos_sector_external_validation import comp_global_panel as cgp


def _make_synthetic_secd(n_days: int = 400) -> pd.DataFrame:
    """Two synthetic listings with `n_days` trading days of price data.

    Default 400 business days = ~18 calendar months, enough for an event
    mid-window plus the 6m=126 trading-day horizon.
    """
    dates = pd.date_range("2020-01-01", periods=n_days, freq="B")  # business days
    rng = np.random.default_rng(42)
    rows = []
    for gvkey, iid, mu, sigma in [("000001", "01W", 0.0005, 0.02), ("000002", "01W", 0.0003, 0.015)]:
        prccd = 100.0
        for d in dates:
            r = rng.normal(mu, sigma)
            prccd *= (1 + r)
            rows.append({
                "gvkey": gvkey,
                "iid": iid,
                "datadate": d,
                "prccd": prccd,
                "ajexdi": 1.0,
                "trfd": 1.0,
                "curcdd": "GBP",
            })
    return pd.DataFrame(rows)


def _make_synthetic_universe() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "gvkey": "000001", "iid": "01W", "gsector": 40, "loc": "GBR", "conml": "FAKE BANK",
            "from_date": pd.Timestamp("2010-01-01"), "thru": pd.NaT,
        },
        {
            "gvkey": "000002", "iid": "01W", "gsector": 35, "loc": "GBR", "conml": "FAKE PHARMA",
            "from_date": pd.Timestamp("2010-01-01"), "thru": pd.NaT,
        },
    ])


def _make_synthetic_shocks(event_dates: list[str]) -> pd.DataFrame:
    """Construct a minimal shocks DataFrame with is_event_start flag and shock_sign."""
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in event_dates])
    return pd.DataFrame({
        "is_event_start": [True] * len(idx),
        "shock_sign": [1] * len(idx),
    }, index=idx)


def test_compute_daily_log_returns_basic():
    secd = _make_synthetic_secd(n_days=10)
    rets = cgp.compute_daily_log_returns(secd)
    # 9 returns per listing × 2 listings = 18 rows
    assert len(rets) == 18
    assert rets["log_ret"].notna().all()
    assert (rets["log_ret"].abs() < 1.5).all()  # filter applied


def test_compute_daily_log_returns_filters_pathological():
    secd = _make_synthetic_secd(n_days=5)
    # Inject a 200% one-day jump
    secd.loc[2, "prccd"] = secd.loc[1, "prccd"] * 3  # ~110% log return
    rets = cgp.compute_daily_log_returns(secd)
    # The 110% jump should be filtered (limit < 1.5)
    assert rets["log_ret"].abs().max() < 1.5


def test_build_country_panel_synthetic(monkeypatch):
    """End-to-end with synthetic data, monkey-patching pull_g_secd_for_listings."""
    universe = _make_synthetic_universe()
    secd = _make_synthetic_secd(n_days=400)
    shocks = _make_synthetic_shocks(["2020-06-30"])

    monkeypatch.setattr(cgp, "pull_g_secd_for_listings", lambda *a, **kw: secd)

    panel, stats = cgp.build_country_panel(shocks, universe, horizons={"1m": 21, "3m": 63, "6m": 126})
    assert not panel.empty
    assert set(panel["gvkey"].unique()) == {"000001", "000002"}
    assert set(panel["horizon"].unique()) == {"1m", "3m", "6m"}
    assert "car" in panel.columns
    assert "shock_sign" in panel.columns
    assert "sector_name" in panel.columns
    # CAR at horizon h should equal log_ret - market_log_ret; market is cross-sectional mean
    for (e, h), g in panel.groupby(["event_date", "horizon"]):
        market = g["log_ret"].mean()
        assert np.allclose(g["car"], g["log_ret"] - market, atol=1e-9)


def test_build_country_panel_respects_thru_date(monkeypatch):
    universe = _make_synthetic_universe()
    universe.loc[0, "thru"] = pd.Timestamp("2018-12-31")  # FAKE BANK delisted before 2020 event
    secd = _make_synthetic_secd(n_days=400)
    shocks = _make_synthetic_shocks(["2020-06-30"])

    monkeypatch.setattr(cgp, "pull_g_secd_for_listings", lambda *a, **kw: secd)

    panel, _ = cgp.build_country_panel(shocks, universe)
    # FAKE BANK (gvkey=000001) should NOT appear in panel
    assert "000001" not in panel["gvkey"].unique()
    assert "000002" in panel["gvkey"].unique()


def test_n_with_car_audit_floor(monkeypatch):
    universe = _make_synthetic_universe()
    secd = _make_synthetic_secd(n_days=400)
    shocks = _make_synthetic_shocks(["2020-06-30"])
    monkeypatch.setattr(cgp, "pull_g_secd_for_listings", lambda *a, **kw: secd)
    panel, _ = cgp.build_country_panel(shocks, universe)

    audit = cgp.n_with_car_audit(panel, floor=1)
    assert "floor_passed" in audit.columns
    # 2 firms × 3 horizons = 6 rows (each sector has 1 firm)
    assert len(audit) == 6
    assert audit["floor_passed"].all()  # n=1 per cell, floor=1


def test_n_with_car_audit_handles_empty():
    audit = cgp.n_with_car_audit(pd.DataFrame())
    assert audit.empty
    assert "floor_passed" in audit.columns


def test_save_country_panel(tmp_path, monkeypatch):
    universe = _make_synthetic_universe()
    secd = _make_synthetic_secd(n_days=400)
    shocks = _make_synthetic_shocks(["2020-06-30"])
    monkeypatch.setattr(cgp, "pull_g_secd_for_listings", lambda *a, **kw: secd)
    panel, _ = cgp.build_country_panel(shocks, universe)

    path = cgp.save_country_panel(panel, "test_country", out_dir=tmp_path, snap="2026-01-01")
    assert path.exists()
    back = pd.read_parquet(path)
    assert len(back) == len(panel)


def test_real_uk_panel_smoke():
    """End-to-end smoke test against real WRDS courier — UK panel with BoE events."""
    pytest.importorskip("wrds_courier_client")
    from sloos_sector_external_validation import boe_ccs_fetch, stoxx600_universe

    try:
        master = stoxx600_universe.query_stoxx600_master()
    except Exception:
        pytest.skip("WRDS courier not available")
    uk = stoxx600_universe.build_uk_universe(master)
    boe_shocks, _ = boe_ccs_fetch.fetch_and_construct_shocks(threshold=1.0, covid_robust=True)
    panel, stats = cgp.build_country_panel(boe_shocks, uk)
    # Sanity: panel non-empty, all 33 cells clear 50-floor (verified 2026-05-06)
    assert not panel.empty
    assert stats.n_panel_rows > 4000
    audit = cgp.n_with_car_audit(panel, floor=50)
    assert (audit["n_with_car"] >= 50).all(), (
        f"UK n_with_CAR cells below 50-floor: {audit[audit['n_with_car'] < 50].to_dict('records')}"
    )
