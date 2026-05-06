"""Tests for stoxx600_universe (Path B specific, S3).

Unit tests use synthetic master panels so they don't depend on the WRDS courier.
A separate "real" snapshot test verifies the courier query produces sensible
counts.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sloos_sector_external_validation import stoxx600_universe as su


def _make_synthetic_master() -> pd.DataFrame:
    """Build a 6-firm synthetic STOXX 600 master panel covering 2010-2025."""
    rows = [
        # gvkey, iid, from_date, thru, conml, gsector, loc, costat, ipodate, dldte
        ("000001", "01W", "2010-01-01", None, "UK BIG ENERGY PLC", 10, "GBR", "A", "1990-01-01", None),
        ("000002", "01W", "2010-01-01", None, "UK FINANCIALS LTD", 40, "GBR", "A", "2000-01-01", None),
        ("000003", "01W", "2008-01-01", "2018-06-30", "UK FALLEN FIRM", 35, "GBR", "I", None, "2018-06-30"),
        ("000004", "01W", "2010-01-01", None, "DEUTSCHE BIG INDUSTRIAL", 20, "DEU", "A", None, None),
        ("000005", "01W", "2014-04-01", None, "FRENCH NEW IT", 45, "FRA", "A", "2014-04-01", None),
        ("000006", "01W", "2008-01-01", None, "USA OFFSHORE EXCLUDED", 40, "USA", "A", None, None),
    ]
    df = pd.DataFrame(rows, columns=[
        "gvkey", "iid", "from_date", "thru", "conml", "gsector", "loc", "costat", "ipodate", "dldte",
    ])
    df["from_date"] = pd.to_datetime(df["from_date"])
    df["thru"] = pd.to_datetime(df["thru"])
    df["ipodate"] = pd.to_datetime(df["ipodate"])
    df["dldte"] = pd.to_datetime(df["dldte"])
    return df


def test_build_uk_universe_filters_to_gbr():
    master = _make_synthetic_master()
    uk = su.build_uk_universe(master)
    assert set(uk["loc"]) == {"GBR"}
    assert uk["gvkey"].nunique() == 3
    assert "USA OFFSHORE EXCLUDED" not in uk["conml"].values


def test_build_eurozone_excludes_uk_and_offshore():
    master = _make_synthetic_master()
    eu = su.build_eurozone_universe(master)
    assert "GBR" not in set(eu["loc"])
    assert "USA" not in set(eu["loc"])
    assert eu["gvkey"].nunique() == 2  # DEU + FRA


def test_build_eurozone_strict_excludes_non_eur_currency():
    master = _make_synthetic_master()
    eu_strict = su.build_eurozone_universe(master, strict=True)
    # FRA + DEU both eurozone-strict
    assert set(eu_strict["loc"]) == {"DEU", "FRA"}


def test_firms_active_at_respects_from_thru():
    master = _make_synthetic_master()
    uk = su.build_uk_universe(master)
    # 2015-06-30: UK FALLEN FIRM still active
    active_2015 = su.firms_active_at(uk, pd.Timestamp("2015-06-30"))
    assert "000003" in active_2015["gvkey"].values
    # 2020-01-01: UK FALLEN FIRM was delisted 2018-06-30, must NOT be in active set
    active_2020 = su.firms_active_at(uk, pd.Timestamp("2020-01-01"))
    assert "000003" not in active_2020["gvkey"].values


def test_firms_active_at_pre_inception_excluded():
    master = _make_synthetic_master()
    eu = su.build_eurozone_universe(master)
    # FRENCH NEW IT joined 2014-04-01; pre-inception 2013-12-31 must NOT include it
    active_2013 = su.firms_active_at(eu, pd.Timestamp("2013-12-31"))
    assert "000005" not in active_2013["gvkey"].values


def test_per_sector_n_audit_pivots_sector_x_event():
    master = _make_synthetic_master()
    uk = su.build_uk_universe(master)
    events = pd.DatetimeIndex([pd.Timestamp("2015-06-30"), pd.Timestamp("2022-03-31")])
    audit = su.per_sector_n_audit(uk, events)
    assert "distinct_total" in audit.columns
    assert "sector_name" in audit.columns
    # Healthcare (gsector=35) had 1 firm in 2015 (000003) but 0 in 2022 (delisted 2018)
    assert audit.loc[35, "distinct_total"] == 1


def test_expected_per_cell_n_sums_over_events():
    master = _make_synthetic_master()
    uk = su.build_uk_universe(master)
    events = pd.DatetimeIndex([pd.Timestamp("2015-06-30"), pd.Timestamp("2022-03-31")])
    cells = su.expected_per_cell_n(uk, events)
    # gsector=10 (Energy): 000001 active in BOTH events → 1 + 1 = 2
    assert cells.loc[10, "horizon_1m"] == 2
    # gsector=35 (Healthcare): 000003 active 2015 only → 1 + 0 = 1
    assert cells.loc[35, "horizon_1m"] == 1
    assert cells.loc[10, "horizon_1m"] == cells.loc[10, "horizon_6m"]  # n same across horizons


def test_save_universes_writes_parquets(tmp_path):
    master = _make_synthetic_master()
    uk = su.build_uk_universe(master)
    eu = su.build_eurozone_universe(master)
    paths = su.save_universes(uk, eu, out_dir=tmp_path, snap="2026-01-01")
    assert paths["uk"].exists()
    assert paths["eurozone"].exists()
    assert paths["uk"].read_bytes()  # non-empty
    # Round-trip
    uk_back = pd.read_parquet(paths["uk"])
    assert uk_back["gvkey"].nunique() == 3


def test_eurozone_broad_loc_list_disjoint_from_uk():
    assert su.UK_LOC not in su.EUROZONE_BROAD_LOCS
    assert su.UK_LOC not in su.EUROZONE_STRICT_LOCS


def test_eurozone_strict_subset_of_broad():
    assert set(su.EUROZONE_STRICT_LOCS).issubset(set(su.EUROZONE_BROAD_LOCS))


def test_real_courier_master_panel_size():
    """Smoke test against real WRDS courier — verify ~1,600 distinct gvkeys ever in STOXX 600.

    Marked separately because it depends on the courier connection.
    """
    pytest.importorskip("wrds_courier_client")
    try:
        master = su.query_stoxx600_master()
    except Exception:
        pytest.skip("WRDS courier not available")
    assert master["gvkey"].nunique() > 1500, (
        f"expected > 1500 distinct gvkeys in STOXX 600 history, got {master['gvkey'].nunique()}"
    )
    # UK should be largest single-country contributor
    by_loc = master.groupby("loc")["gvkey"].nunique().sort_values(ascending=False)
    assert by_loc.index[0] == "GBR"


def test_real_uk_currently_active_around_120():
    """Smoke: UK currently-active should be ~119 (verified 2026-05-06)."""
    try:
        master = su.query_stoxx600_master()
    except Exception:
        pytest.skip("WRDS courier not available")
    uk = su.build_uk_universe(master)
    today = pd.Timestamp.today().normalize()
    active = su.firms_active_at(uk, today)
    n = active["gvkey"].nunique()
    assert 100 <= n <= 140, f"UK currently-active should be ~119, got {n}"
