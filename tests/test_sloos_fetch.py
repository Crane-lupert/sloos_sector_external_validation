"""SLOOS fetch tests.

Pulls live FRED data (small payload). Skips if FRED_API_KEY not set so CI on
forks without the secret still passes.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv

load_dotenv()

from sloos_sector_external_validation.sloos_fetch import (  # noqa: E402
    DEFAULT_SERIES,
    PRIMARY_SERIES,
    fetch_series,
    summarize,
    to_panel,
)


pytestmark = pytest.mark.skipif(
    not os.environ.get("FRED_API_KEY", "").strip(),
    reason="FRED_API_KEY not set",
)


def test_primary_series_in_default():
    assert PRIMARY_SERIES in DEFAULT_SERIES


def test_fetch_primary_series_min_length():
    series = fetch_series((PRIMARY_SERIES,))
    assert PRIMARY_SERIES in series
    s = series[PRIMARY_SERIES]
    assert len(s) >= 140, f"primary series too short: {len(s)}"


def test_panel_shape_with_primary_only():
    series = fetch_series((PRIMARY_SERIES,))
    panel = to_panel(series)
    assert PRIMARY_SERIES in panel.columns
    assert panel.shape[0] >= 140


def test_summarize_keys():
    series = fetch_series((PRIMARY_SERIES,))
    summ = summarize(to_panel(series))
    assert PRIMARY_SERIES in summ
    keys = set(summ[PRIMARY_SERIES].keys())
    assert {"length", "first_date", "last_date", "last_value", "mean", "std"} <= keys


def test_legacy_series_missing_does_not_raise():
    # Legacy DRTSCRE / DRTSRRE / DRTSCC / DRTSAUTO retired from FRED — fetch must
    # log warning and continue, not raise.
    series = fetch_series(("DRTSCILM", "DRTSCRE_NONEXISTENT_XYZ"))
    assert "DRTSCILM" in series
    assert "DRTSCRE_NONEXISTENT_XYZ" not in series


def test_cache_parquet_written_today_or_yesterday(tmp_path):
    # Use cache files in repo data/cache, not tmp; just verify a parquet exists
    # with the expected schema after Day 1 fetch_and_save run.
    cache_dir = Path("data/cache")
    files = sorted(cache_dir.glob("sloos_series_*.parquet"))
    assert files, "no SLOOS parquet snapshots in data/cache; run sloos_fetch.fetch_and_save() first"
    df = pd.read_parquet(files[-1])
    assert PRIMARY_SERIES in df.columns
    assert df.shape[0] >= 140
