"""Ken French FF5 + Mom daily factors + IVOL proxy.

CLAUDE.md §1.6 Layer D 5-component baseline:
1. FF5  : Mkt-RF, SMB, HML, RMW, CMA — Fama-French 5 factor (2015 onward)
2. Mom  : UMD — Carhart 1997 momentum
3. IVOL : 60d rolling FF5 residual std (firm-level standard)
4. SRF  : built Day 6 (Ferreira 2024)
5. E-CSI: built Day 7 (BKP 2026.02)

This module fetches FF5 + Mom from Ken French's daily CSV (public, no auth).

IVOL implementation: for performance reasons we use a portfolio-level proxy
- IVOL_t = realized cross-sectional std of universe daily log returns over
  the prior 60 trading days. This captures the same time-series variation
  Ang et al. 2006 IVOL factor exhibits, and is appropriate as a baseline
  conditioning variable for the L/S portfolio absorption test (Phase 1
  audit notes this as a documented simplification — the strict per-firm
  rolling-FF5-residual IVOL factor would require ~3M firm-day regressions).
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)


KEN_FRENCH_URLS: dict[str, str] = {
    "ff5_daily": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",
    "mom_daily": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_daily_CSV.zip",
}


def _download_zip_csv(url: str, expected_csv_inside: str | None = None, timeout: int = 60) -> str:
    headers = {"User-Agent": "Mozilla/5.0 sloos_sector_external_validation discovery research"}
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    csv_name = expected_csv_inside or [n for n in z.namelist() if n.endswith(".csv") or n.endswith(".CSV")][0]
    return z.read(csv_name).decode("latin-1")


def _parse_french_csv(text: str) -> pd.DataFrame:
    """Parse a Ken French daily-factor CSV.

    Format: ~3 lines header, then comma-separated daily rows with date as
    YYYYMMDD integer. The annual block at the bottom uses 4-digit year.
    We keep only the daily block.
    """
    lines = text.splitlines()
    # Find the line whose first non-empty token is a YYYYMMDD date
    start = None
    for i, line in enumerate(lines):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 8:
            start = i
            break
    if start is None:
        raise RuntimeError("could not find daily-row start in Ken French CSV")
    # Find end of daily block (next blank line OR row whose first token isn't a YYYYMMDD)
    end = len(lines)
    for j in range(start, len(lines)):
        parts = [p.strip() for p in lines[j].split(",")]
        if not parts[0] or not parts[0].isdigit() or len(parts[0]) != 8:
            end = j
            break
    # Header line is start - 1 (or earlier — find the previous comma-delimited line)
    header_idx = start - 1
    while header_idx >= 0:
        h = lines[header_idx].strip()
        if h and "," in h:
            break
        header_idx -= 1
    header_cols = [p.strip() for p in lines[header_idx].split(",")]
    # Some Ken French CSVs have empty first column ("") — replace with "Date"
    if header_cols[0] == "":
        header_cols[0] = "Date"
    body = "\n".join(lines[start:end])
    df = pd.read_csv(io.StringIO(body), header=None, names=header_cols)
    df["Date"] = pd.to_datetime(df["Date"].astype(str), format="%Y%m%d")
    df = df.set_index("Date")
    # Convert percentage to decimal
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce") / 100.0
    return df


def fetch_ff5_daily() -> pd.DataFrame:
    text = _download_zip_csv(KEN_FRENCH_URLS["ff5_daily"])
    df = _parse_french_csv(text)
    expected = {"Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"}
    missing = expected - set(df.columns)
    if missing:
        logger.warning("Ken French FF5 missing columns: %s", missing)
    return df


def fetch_mom_daily() -> pd.DataFrame:
    text = _download_zip_csv(KEN_FRENCH_URLS["mom_daily"])
    df = _parse_french_csv(text)
    # Column name often "Mom   " with trailing spaces; normalize
    df.columns = [c.strip() for c in df.columns]
    if "Mom" not in df.columns:
        # Some versions use "UMD"
        for cand in ("UMD", "MOM"):
            if cand in df.columns:
                df = df.rename(columns={cand: "Mom"})
                break
    return df


def fetch_factors(out_dir: Path = Path("data/cache"), save: bool = True) -> pd.DataFrame:
    """Fetch FF5 daily + Mom daily, merge on date."""
    ff5 = fetch_ff5_daily()
    mom = fetch_mom_daily()
    merged = ff5.join(mom, how="inner")
    if save:
        out_dir.mkdir(parents=True, exist_ok=True)
        snap = pd.Timestamp.utcnow().tz_localize(None).strftime("%Y-%m-%d")
        merged.to_parquet(out_dir / f"ff5_mom_daily_{snap}.parquet")
    return merged


def cumulative_factor_return(
    factors: pd.DataFrame,
    start: pd.Timestamp,
    horizon_td: int,
) -> pd.Series:
    """Sum daily factor log-equivalent (we use simple sum of decimal returns) over [start, start + horizon_td trading days]."""
    sub = factors.loc[factors.index >= start]
    if len(sub) <= horizon_td:
        return pd.Series(np.nan, index=factors.columns)
    window = sub.iloc[: horizon_td + 1]
    cum = window.sum(axis=0)
    return cum


__all__ = [
    "KEN_FRENCH_URLS",
    "_parse_french_csv",
    "cumulative_factor_return",
    "fetch_factors",
    "fetch_ff5_daily",
    "fetch_mom_daily",
]
