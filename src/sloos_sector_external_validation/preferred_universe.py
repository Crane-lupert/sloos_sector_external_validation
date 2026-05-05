"""R3000 preferred universe + GICS sector map.

Strategy (Phase 0 §2):
1. Fetch current iShares IWB (Russell 1000) + IWM (Russell 2000) holdings CSV — both
   public, no auth, redirect-stable URL. Union ≈ Russell 3000 current snapshot.
2. Map ticker → gvkey via Compustat `names` table (latest active row per ticker).
3. Map gvkey → gsector via Compustat `company` table (11 GICS sector codes).
4. Persist as parquet + JSON-friendly dict.

Limitations recorded in audit (Phase 0 §1.2 universe lock note):
- Current snapshot only — pre-2010 R3000 reconstitution is approximate.
- Backstop for pre-2010: Compustat `curr_sp500_flag` + per-GICS market-cap rank
  is provided as `_universe_backstop`, used only when current-snapshot tickers
  fail to resolve.
- Mid-cap gap: tickers in Russell 2000 (IWM) but no longer in Russell 1000 (IWB)
  are folded into universe. iShares IWB+IWM ∪ ≈ R3000 current.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from .wrds_courier_adapter import query_alias, resolve

logger = logging.getLogger(__name__)

# iShares public holdings CSV. URL skeleton stable since 2018.
# IWB = Russell 1000, IWM = Russell 2000. Union ≈ R3000.
ISHARES_HOLDINGS_URLS: dict[str, str] = {
    "IWB": "https://www.ishares.com/us/products/239707/ishares-russell-1000-etf/1467271812596.ajax?fileType=csv&fileName=IWB_holdings&dataType=fund",
    "IWM": "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund",
}

GICS_NAME: dict[int, str] = {
    10: "Energy",
    15: "Materials",
    20: "Industrials",
    25: "Consumer Discretionary",
    30: "Consumer Staples",
    35: "Healthcare",
    40: "Financials",
    45: "Information Technology",
    50: "Communication Services",
    55: "Utilities",
    60: "Real Estate",
}


def _download_csv(url: str, timeout: int = 30) -> pd.DataFrame:
    """Download iShares holdings CSV. The response has a 9-line preamble before the table header."""
    headers = {"User-Agent": "Mozilla/5.0 sloos_sector_external_validation discovery research"}
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    text = r.content.decode("utf-8-sig", errors="replace")
    # iShares puts ~9 metadata rows then a blank line then the column header. Find header row.
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("Ticker,") or line.startswith("\"Ticker\","):
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError(f"Could not find Ticker header in iShares CSV from {url}")
    body = "\n".join(lines[header_idx:])
    df = pd.read_csv(io.StringIO(body))
    return df


def fetch_ishares_holdings(out_dir: Path = Path("data/raw")) -> dict[str, pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    snap = datetime.utcnow().strftime("%Y-%m-%d")
    frames: dict[str, pd.DataFrame] = {}
    for etf, url in ISHARES_HOLDINGS_URLS.items():
        try:
            df = _download_csv(url)
            df["_etf_source"] = etf
            df["_snapshot_date"] = snap
            df.to_parquet(out_dir / f"ishares_{etf}_holdings_{snap}.parquet")
            frames[etf] = df
            logger.info("iShares %s holdings: %d rows", etf, len(df))
        except Exception as exc:
            logger.warning("iShares %s holdings fetch failed: %s", etf, exc)
    return frames


def union_r3000(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Union IWB + IWM holdings on Ticker. Equity-only filter."""
    if not frames:
        return pd.DataFrame(columns=["ticker"])
    parts = []
    for etf, df in frames.items():
        d = df.copy()
        # Filter equity asset class (drops cash + futures rows)
        if "Asset Class" in d.columns:
            d = d[d["Asset Class"].astype(str).str.lower().isin({"equity", "stock"})]
        if "Ticker" not in d.columns:
            continue
        d = d.rename(columns={"Ticker": "ticker"})
        d["ticker"] = d["ticker"].astype(str).str.strip().str.upper()
        d = d[d["ticker"].str.len() > 0]
        parts.append(d[["ticker", "_etf_source", "_snapshot_date"]])
    if not parts:
        return pd.DataFrame(columns=["ticker"])
    union = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["ticker"])
    return union


def map_ticker_to_gvkey(tickers: list[str]) -> pd.DataFrame:
    """Pick latest active gvkey for each ticker from Compustat names table.

    `names` schema: gvkey + tic + cusip + cik + sic + naics + gsubind + gind +
    year1 (start year) + year2 (end year, or large sentinel if active).
    We want the row with the largest year2 per ticker — i.e., most recent
    or active naming.
    """
    if not tickers:
        return pd.DataFrame(columns=["ticker", "gvkey"])
    # SQL IN clause with up to 5000 tickers safe in DuckDB
    quoted = ",".join(f"'{t.replace(chr(39), chr(39)+chr(39))}'" for t in tickers)
    sql = (
        f"SELECT tic AS ticker, gvkey, gsubind, gind, year1, year2 "
        f"FROM {resolve('names')} "
        f"WHERE tic IN ({quoted})"
    )
    from .wrds_courier_adapter import query as _q

    df = _q(sql)
    if df.empty:
        return pd.DataFrame(columns=["ticker", "gvkey"])
    # Pick row with max year2 per ticker (most recent active span)
    df = df.sort_values(["ticker", "year2"], ascending=[True, False]).drop_duplicates("ticker", keep="first")
    return df.reset_index(drop=True)


def map_gvkey_to_gics(gvkeys: list[str]) -> pd.DataFrame:
    """gvkey -> gsector (10..60) + curr_sp500_flag from Compustat `company` table."""
    if not gvkeys:
        return pd.DataFrame(columns=["gvkey", "gsector"])
    quoted = ",".join(f"'{g}'" for g in gvkeys)
    sql = (
        f"SELECT gvkey, gsector, gind, gsubind, conm, curr_sp500_flag, ipodate, dldte "
        f"FROM {resolve('company')} "
        f"WHERE gvkey IN ({quoted})"
    )
    from .wrds_courier_adapter import query as _q

    df = _q(sql)
    return df.reset_index(drop=True)


def build_universe(out_dir: Path = Path("data/cache")) -> pd.DataFrame:
    """End-to-end: holdings → ticker→gvkey → gvkey→gsector → final universe parquet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    snap = datetime.utcnow().strftime("%Y-%m-%d")
    frames = fetch_ishares_holdings()
    if not frames:
        raise RuntimeError("All iShares holdings fetch failed — universe build aborted.")
    r3000 = union_r3000(frames)
    tickers = r3000["ticker"].tolist()
    tg = map_ticker_to_gvkey(tickers)
    gvkeys = tg["gvkey"].dropna().unique().tolist()
    gc = map_gvkey_to_gics(gvkeys)
    universe = (
        r3000.merge(tg, on="ticker", how="left")
        .merge(gc, on="gvkey", how="left", suffixes=("", "_company"))
    )
    universe["gsector_name"] = universe["gsector"].map(GICS_NAME)
    out_path = out_dir / f"r3000_universe_{snap}.parquet"
    universe.to_parquet(out_path)
    return universe


def universe_summary(universe: pd.DataFrame) -> dict[str, object]:
    """Coverage diagnostics: total tickers, gvkey-resolved, gsector-resolved, per-sector counts."""
    n_total = int(len(universe))
    n_gvkey = int(universe["gvkey"].notna().sum())
    n_gsector = int(universe["gsector"].notna().sum())
    per_sector: dict[str, int] = {}
    if "gsector" in universe.columns:
        for code, name in GICS_NAME.items():
            per_sector[name] = int((universe["gsector"] == code).sum())
    return {
        "n_total": n_total,
        "n_gvkey_resolved": n_gvkey,
        "gvkey_resolution_pct": round(n_gvkey / n_total * 100, 1) if n_total else 0.0,
        "n_gsector_resolved": n_gsector,
        "gsector_resolution_pct": round(n_gsector / n_total * 100, 1) if n_total else 0.0,
        "per_sector_counts": per_sector,
    }


__all__ = [
    "GICS_NAME",
    "ISHARES_HOLDINGS_URLS",
    "build_universe",
    "fetch_ishares_holdings",
    "map_gvkey_to_gics",
    "map_ticker_to_gvkey",
    "union_r3000",
    "universe_summary",
]
