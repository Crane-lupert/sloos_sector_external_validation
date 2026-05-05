"""Universe build tests — both pure-logic (no network) and integration (live).

The pure tests use synthetic in-memory frames. The integration tests hit
WRDS courier (instant) and require the Day 1 universe parquet snapshot.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sloos_sector_external_validation.preferred_universe import (
    GICS_NAME,
    union_r3000,
    universe_summary,
)


def _make_holdings(etf: str, tickers: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Ticker": tickers,
            "Asset Class": ["Equity"] * len(tickers),
            "_etf_source": etf,
            "_snapshot_date": "2026-05-05",
        }
    )


def test_gics_name_has_eleven_sectors():
    assert len(GICS_NAME) == 11


def test_gics_codes_are_canonical():
    expected = {10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60}
    assert set(GICS_NAME.keys()) == expected


def test_union_r3000_dedupes_tickers():
    iwb = _make_holdings("IWB", ["AAPL", "MSFT", "GOOGL"])
    iwm = _make_holdings("IWM", ["MSFT", "TSLA", "AMD"])  # MSFT overlap
    out = union_r3000({"IWB": iwb, "IWM": iwm})
    assert len(out) == 5
    assert sorted(out["ticker"].tolist()) == sorted(["AAPL", "MSFT", "GOOGL", "TSLA", "AMD"])


def test_union_r3000_drops_non_equity():
    df = pd.DataFrame(
        {
            "Ticker": ["AAPL", "USD", "FUT_XYZ"],
            "Asset Class": ["Equity", "Cash", "Futures"],
            "_etf_source": "IWB",
            "_snapshot_date": "2026-05-05",
        }
    )
    out = union_r3000({"IWB": df})
    assert out["ticker"].tolist() == ["AAPL"]


def test_union_r3000_uppercases_and_strips():
    df = pd.DataFrame(
        {
            "Ticker": ["  aapl ", "msft"],
            "Asset Class": ["Equity", "Equity"],
            "_etf_source": "IWB",
            "_snapshot_date": "2026-05-05",
        }
    )
    out = union_r3000({"IWB": df})
    assert sorted(out["ticker"].tolist()) == ["AAPL", "MSFT"]


def test_universe_summary_structure():
    universe = pd.DataFrame(
        {
            "ticker": ["AAPL", "JPM", "XOM"],
            "gvkey": ["1690", "2968", "5074"],
            "gsector": [45, 40, 10],
        }
    )
    s = universe_summary(universe)
    assert s["n_total"] == 3
    assert s["n_gvkey_resolved"] == 3
    assert s["gvkey_resolution_pct"] == 100.0
    assert s["per_sector_counts"]["Information Technology"] == 1
    assert s["per_sector_counts"]["Financials"] == 1
    assert s["per_sector_counts"]["Energy"] == 1


def test_universe_summary_handles_nan():
    universe = pd.DataFrame(
        {
            "ticker": ["AAPL", "UNKNOWN"],
            "gvkey": ["1690", None],
            "gsector": [45, None],
        }
    )
    s = universe_summary(universe)
    assert s["n_total"] == 2
    assert s["n_gvkey_resolved"] == 1
    assert s["gvkey_resolution_pct"] == 50.0


# Integration tests on Day 1 snapshot
def test_universe_snapshot_exists_and_resolves_well():
    cache_dir = Path("data/cache")
    files = sorted(cache_dir.glob("r3000_universe_*.parquet"))
    if not files:
        pytest.skip("no R3000 universe snapshot; run preferred_universe.build_universe() first")
    df = pd.read_parquet(files[-1])
    summary = universe_summary(df)
    assert summary["n_total"] >= 2500, f"universe too small: {summary['n_total']}"
    assert summary["gvkey_resolution_pct"] >= 90.0, f"gvkey resolution {summary['gvkey_resolution_pct']}% < 90%"


def test_universe_all_eleven_sectors_populated():
    cache_dir = Path("data/cache")
    files = sorted(cache_dir.glob("r3000_universe_*.parquet"))
    if not files:
        pytest.skip("no R3000 universe snapshot")
    df = pd.read_parquet(files[-1])
    s = universe_summary(df)
    for sector_name, count in s["per_sector_counts"].items():
        assert count >= 30, f"sector {sector_name} only {count} firms; floor=30"
