"""SLOOS series fetcher — FRED API.

Primary: DRTSCILM = Net % of domestic banks tightening C&I lending standards
to large and middle-market firms. CLAUDE.md §2.

Robust series fetched alongside for sensitivity check (Phase 0 §1.6 escape
mechanism — none of these is the locked shock; primary remains DRTSCILM).

Series intended (some may be discontinued in FRED — fetch defensively):
- DRTSCILM   primary (C&I, Large/Middle-Market)            1990.Q2+
- DRTSCIS    C&I, Small firms                              1990.Q2+
- DRTSCRE    Commercial Real Estate (legacy aggregate)     pre-2013 only
- DRTSRRE    Residential Real Estate (legacy aggregate)    pre-2013 only
- DRTSCC     Credit Card (legacy)                          variable
- DRTSAUTO   Auto loans (legacy)                           variable

If a legacy series is unavailable, we record null length and continue.
The robust check uses whichever subset is actually available; the locked
primary shock is unaffected.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_SERIES: tuple[str, ...] = (
    "DRTSCILM",
    "DRTSCIS",
    "DRTSCRE",
    "DRTSRRE",
    "DRTSCC",
    "DRTSAUTO",
)

PRIMARY_SERIES = "DRTSCILM"


def _get_fred_client() -> Fred:
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY not set. Put it in .env or OS env. "
            "Free key from https://fred.stlouisfed.org/docs/api/api_key.html."
        )
    return Fred(api_key=api_key)


def fetch_series(
    series_ids: tuple[str, ...] = DEFAULT_SERIES,
    fred: Fred | None = None,
) -> dict[str, pd.Series]:
    """Fetch each FRED series. Missing series logged and skipped, not raised."""
    fred = fred or _get_fred_client()
    out: dict[str, pd.Series] = {}
    for sid in series_ids:
        try:
            s = fred.get_series(sid)
            if s is None or len(s) == 0:
                logger.warning("FRED series %s returned empty; skipping", sid)
                continue
            s.name = sid
            out[sid] = s
        except Exception as exc:  # FRED 400 for retired series
            logger.warning("FRED series %s fetch failed: %s", sid, exc)
    return out


def to_panel(series_dict: dict[str, pd.Series]) -> pd.DataFrame:
    """Wide panel: index = quarter-end date, columns = series_id, values = net %."""
    if not series_dict:
        return pd.DataFrame()
    df = pd.concat(series_dict.values(), axis=1)
    df.columns = list(series_dict.keys())
    df.index.name = "quarter_release_date"
    return df.sort_index()


def save_panel(panel: pd.DataFrame, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(out_path)
    return out_path


def fetch_and_save(
    out_dir: Path = Path("data/cache"),
    series_ids: tuple[str, ...] = DEFAULT_SERIES,
    snapshot_date: str | None = None,
) -> tuple[pd.DataFrame, Path]:
    """End-to-end: fetch all series, build wide panel, write parquet snapshot."""
    snap = snapshot_date or datetime.utcnow().strftime("%Y-%m-%d")
    series_dict = fetch_series(series_ids)
    panel = to_panel(series_dict)
    if PRIMARY_SERIES not in panel.columns:
        raise RuntimeError(
            f"Primary series {PRIMARY_SERIES} missing — Phase 0 #1 lock violated. "
            "Cannot continue without primary shock series."
        )
    out_path = out_dir / f"sloos_series_{snap}.parquet"
    save_panel(panel, out_path)
    return panel, out_path


def summarize(panel: pd.DataFrame) -> dict[str, dict[str, object]]:
    """Per-series length + first/last release date + last value."""
    summary: dict[str, dict[str, object]] = {}
    for col in panel.columns:
        s = panel[col].dropna()
        if len(s) == 0:
            summary[col] = {"length": 0}
            continue
        summary[col] = {
            "length": int(len(s)),
            "first_date": str(s.index[0].date()),
            "last_date": str(s.index[-1].date()),
            "last_value": float(s.iloc[-1]),
            "mean": float(s.mean()),
            "std": float(s.std()),
        }
    return summary


__all__ = [
    "DEFAULT_SERIES",
    "PRIMARY_SERIES",
    "fetch_and_save",
    "fetch_series",
    "save_panel",
    "summarize",
    "to_panel",
]
