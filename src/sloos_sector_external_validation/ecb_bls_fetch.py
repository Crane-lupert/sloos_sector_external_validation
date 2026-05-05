"""ECB Bank Lending Survey (BLS) fetch + AR(1) shock identification (Path B / S3).

Fetches the eurozone-aggregate Net % balance for changes in credit standards
applied for the approval of loans to Enterprises (B3 = backward 3 months).
The series is the eurozone analog of FRED `DRTSCILM` (Net % C&I tightening
Large/Middle-Market) used in S1.

Endpoint (verified 2026-05-06): ECB Data Portal SDMX REST API
    https://data-api.ecb.europa.eu/service/data/BLS/<key>?format=text/csv

Series key (verified 2026-05-06):
    BLS.Q.U2.ALL.O.E.Z.B3.ST.S.WFNET
    - Q       = quarterly
    - U2      = euro area, changing composition
    - ALL     = all banks
    - O       = Overall (loan type)
    - E       = Enterprise counterpart
    - Z       = motivation N/A
    - B3      = Backward looking three months (the realized quarter)
    - ST      = effect domain: credit standards
    - S       = market role: loan supply
    - WFNET   = weighted net percentage (tightened minus eased)

Sign convention: positive = tightening (matches DRTSCILM convention).

Methodology — AR(1) innovation shock identification (S1 inheritance):
    Y_t       = α + ρ·Y_{t-1} + ε_t
    z_innov_t = ε_t / σ(ε)
    shock event ⇔ |z_innov_t| > 1.0σ      (Bidder-Krane-Park 2026.02 standard)

This module reuses `shock_construct.construct_shocks` (lifted from S1) for
AR(1) fitting and event identification. Path B uses identical methodology to
make cross-country Spearman validation interpretable.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pandas as pd

from .shock_construct import construct_shocks, event_summary, save_shocks

ECB_BLS_API_BASE = "https://data-api.ecb.europa.eu/service/data"

# Eurozone aggregate, credit standards, enterprises, B3 backward-3-months.
ECB_BLS_KEY_OE_BACKWARD = "Q.U2.ALL.O.E.Z.B3.ST.S.WFNET"
ECB_BLS_DATAFLOW = "BLS"

# Per-country SDMX dim REF_AREA codes (for alt event-def Spearman robustness).
# DE / FR / IT / ES are the 4 largest eurozone economies.
ECB_BLS_PER_COUNTRY_KEYS = {
    "DE": "Q.DE.ALL.O.E.Z.B3.ST.S.WFNET",
    "FR": "Q.FR.ALL.O.E.Z.B3.ST.S.WFNET",
    "IT": "Q.IT.ALL.O.E.Z.B3.ST.S.WFNET",
    "ES": "Q.ES.ALL.O.E.Z.B3.ST.S.WFNET",
}


def _fetch_csv(series_key: str, dataflow: str = ECB_BLS_DATAFLOW, timeout: float = 60.0) -> pd.DataFrame:
    """Fetch one BLS series from ECB Data Portal SDMX endpoint as a CSV-row DataFrame."""
    url = f"{ECB_BLS_API_BASE}/{dataflow}/{series_key}"
    headers = {"Accept": "text/csv", "User-Agent": "sloos-sector-external-validation/0.0.1"}
    r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    from io import StringIO

    return pd.read_csv(StringIO(r.text))


def _quarter_period_to_timestamp(period: str) -> pd.Timestamp:
    """Convert ECB quarter code '2003-Q1' to a quarter-end timestamp '2003-03-31'."""
    return pd.Period(period, freq="Q").to_timestamp(how="end").normalize()


def fetch_ecb_bls_series(
    series_key: str = ECB_BLS_KEY_OE_BACKWARD,
    column_name: str = "ECB_BLS_OE_WFNET",
) -> pd.Series:
    """Return the BLS quarterly series indexed by quarter-end Timestamp.

    Default fetches the eurozone-aggregate "Overall - Enterprise - B3 backward"
    credit-standards Net % series (the canonical SLOOS DRTSCILM analog).
    """
    raw = _fetch_csv(series_key)
    if "TIME_PERIOD" not in raw.columns or "OBS_VALUE" not in raw.columns:
        raise ValueError(f"Unexpected BLS schema; columns={list(raw.columns)}")
    s = pd.Series(
        raw["OBS_VALUE"].astype(float).values,
        index=[_quarter_period_to_timestamp(p) for p in raw["TIME_PERIOD"]],
        name=column_name,
    ).sort_index()
    s.index.name = "quarter_end"
    return s


def fetch_ecb_bls_per_country() -> dict[str, pd.Series]:
    """Fetch DE/FR/IT/ES variants for alternative event def Spearman robustness."""
    out: dict[str, pd.Series] = {}
    for ctry, key in ECB_BLS_PER_COUNTRY_KEYS.items():
        out[ctry] = fetch_ecb_bls_series(series_key=key, column_name=f"ECB_BLS_{ctry}_OE_WFNET")
    return out


def to_panel(series: pd.Series) -> pd.DataFrame:
    """Wrap a series as a 1-column panel for `construct_shocks(panel, primary_series=...)`."""
    return series.to_frame()


def fetch_and_construct_shocks(
    series_key: str = ECB_BLS_KEY_OE_BACKWARD,
    column_name: str = "ECB_BLS_OE_WFNET",
    threshold: float = 1.0,
) -> tuple[pd.DataFrame, dict]:
    """End-to-end: fetch BLS → AR(1) residual shocks → (shocks_df, summary_dict)."""
    s = fetch_ecb_bls_series(series_key=series_key, column_name=column_name)
    panel = to_panel(s)
    shocks = construct_shocks(panel, primary_series=column_name, threshold=threshold)
    summary = event_summary(shocks)
    summary["series_key"] = series_key
    summary["n_quarters_observed"] = int(s.notna().sum())
    summary["first_quarter"] = str(s.index.min().date())
    summary["last_quarter"] = str(s.index.max().date())
    return shocks, summary


def save(shocks: pd.DataFrame, out_dir: Path = Path("data/cache"), tag: str = "ECB_BLS_OE") -> Path:
    """Persist with same naming convention as S1 `shock_construct.save_shocks`."""
    return save_shocks(shocks, out_dir=out_dir, tag=tag)


__all__ = [
    "ECB_BLS_API_BASE",
    "ECB_BLS_KEY_OE_BACKWARD",
    "ECB_BLS_PER_COUNTRY_KEYS",
    "fetch_and_construct_shocks",
    "fetch_ecb_bls_per_country",
    "fetch_ecb_bls_series",
    "save",
    "to_panel",
]
