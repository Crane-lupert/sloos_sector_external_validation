"""SRF — Skewness of Returns of Financial firms (Ferreira 2024 reconstruction).

Layer D 5-component baseline component #4 (CLAUDE.md §1.6).

Methodology (Ferreira, "Cross-Sectional Financial Conditions, Business
Cycles and the Lending Channel," J Monetary Economics 2024):
- Universe: financial firms (GICS sector 40 = Financials).
- For each firm i and trading day t, compute log return r_{i,t} = log(p_t / p_{t-1}).
- For each quarter q, pool all daily firm-day returns within q, then compute
  cross-sectional skewness γ̂_q.
- SRF_q is the quarterly time series of these cross-sectional skewness values.

Interpretation: when the cross-section of financial firms' returns is left-
skewed (a few firms see large negative returns), the financial sector is
under stress → predicts lending tightening and macro downturn.

Output: quarterly time series indexed by quarter-end date, aligned to
SLOOS release calendar (quarterly start dates 1990-04-01 …).
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .preferred_universe import GICS_NAME
from .wrds_courier_adapter import query, resolve

logger = logging.getLogger(__name__)


FINANCIAL_SECTOR_CODE = 40
PRIMARY_IID = "01"


def _financial_gvkeys(universe: pd.DataFrame) -> list[str]:
    """Return gvkeys whose GICS sector == 40 (Financials) from the universe."""
    fin = universe[(universe["gsector"] == FINANCIAL_SECTOR_CODE) & universe["gvkey"].notna()]
    return fin["gvkey"].astype(str).unique().tolist()


def _pull_financial_prices(gvkeys: list[str], start_date: str = "1990-01-01") -> pd.DataFrame:
    """Bulk pull daily prices for Financial-sector firms."""
    if not gvkeys:
        raise ValueError("no financial gvkeys provided")
    quoted = ",".join(f"'{g}'" for g in gvkeys)
    sql = f"""
        SELECT gvkey, datadate, prccd, ajexdi
        FROM {resolve('secd')}
        WHERE iid = '{PRIMARY_IID}'
          AND gvkey IN ({quoted})
          AND datadate >= DATE '{start_date}'
          AND prccd IS NOT NULL
        ORDER BY gvkey, datadate
    """
    return query(sql)


def compute_daily_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Per-gvkey daily log returns from adjusted price."""
    df = prices.copy()
    df["adj_p"] = df["prccd"] / df["ajexdi"].fillna(1.0).replace(0, np.nan)
    df = df.dropna(subset=["adj_p"])
    df = df[df["adj_p"] > 0]
    df = df.sort_values(["gvkey", "datadate"]).reset_index(drop=True)
    df["log_p"] = np.log(df["adj_p"])
    df["log_ret"] = df.groupby("gvkey", sort=False)["log_p"].diff()
    df = df.dropna(subset=["log_ret"])
    # Drop infinities (split / spinoff residuals)
    df = df[np.isfinite(df["log_ret"])]
    return df[["gvkey", "datadate", "log_ret"]]


def quarterly_cross_sectional_skewness(
    returns: pd.DataFrame,
    winsorize: float | None = 0.005,
) -> pd.DataFrame:
    """Compute SRF: cross-sectional skewness of pooled firm-day returns per quarter.

    Pool all (firm, day) returns inside a quarter, then compute γ̂ via the
    standard Fisher-Pearson moment estimator (scipy.stats.skew unbiased=False
    matches Ferreira's reporting convention).

    Optional winsorize trims the top/bottom (winsorize) fraction of each
    quarter's pooled returns to limit extreme leverage of single-firm
    tail events.
    """
    from scipy.stats import skew

    if returns.empty:
        return pd.DataFrame(columns=["quarter_release_date", "n_obs", "n_firms", "srf"])

    df = returns.copy()
    df["quarter_release_date"] = df["datadate"].apply(_quarter_release_date)

    rows = []
    for qrd, g in df.groupby("quarter_release_date"):
        ret_arr = g["log_ret"].to_numpy()
        if winsorize is not None and 0.0 < winsorize < 0.5:
            lo = np.quantile(ret_arr, winsorize)
            hi = np.quantile(ret_arr, 1.0 - winsorize)
            ret_arr = np.clip(ret_arr, lo, hi)
        if len(ret_arr) < 30:
            continue
        skew_val = float(skew(ret_arr, bias=True))
        rows.append(
            {
                "quarter_release_date": qrd,
                "n_obs": int(len(ret_arr)),
                "n_firms": int(g["gvkey"].nunique()),
                "srf": skew_val,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["quarter_release_date", "n_obs", "n_firms", "srf"])
    out = pd.DataFrame(rows).sort_values("quarter_release_date").reset_index(drop=True)
    out["quarter_release_date"] = pd.to_datetime(out["quarter_release_date"])
    return out


def _quarter_release_date(d: pd.Timestamp | np.datetime64) -> pd.Timestamp:
    """Map a daily date to the SLOOS release-quarter index (Q1=Apr-1, Q2=Jul-1, etc.).

    SLOOS releases the senior loan officer survey roughly:
    - Late Jan (covers Q4 prior year) → maps to release_date 2023-01-01 in FRED
    - Late April (covers Q1) → 2023-04-01
    - Late July (covers Q2) → 2023-07-01
    - Late Oct (covers Q3) → 2023-10-01

    We bucket daily returns by the SLOOS-release quarter they fall into:
    daily date in [Jan 1, Apr 1) → release 2023-04-01 (covers Q1 returns,
    released after Q1 closes). Conservatively: bucket date d to the
    NEXT quarter-start after d (i.e., the release date that observed those
    daily returns).
    """
    ts = pd.Timestamp(d)
    year, month = ts.year, ts.month
    if month in (1, 2, 3):
        return pd.Timestamp(year, 4, 1)
    if month in (4, 5, 6):
        return pd.Timestamp(year, 7, 1)
    if month in (7, 8, 9):
        return pd.Timestamp(year, 10, 1)
    return pd.Timestamp(year + 1, 1, 1)


def build_srf(
    universe: pd.DataFrame,
    out_dir: Path = Path("data/cache"),
    save: bool = True,
) -> pd.DataFrame:
    """End-to-end SRF construction."""
    gvkeys = _financial_gvkeys(universe)
    if not gvkeys:
        raise RuntimeError("no Financials gvkeys in universe — universe build broken?")
    logger.info("pulling financials prices for %d gvkeys...", len(gvkeys))
    prices = _pull_financial_prices(gvkeys)
    logger.info("financials price rows: %d", len(prices))
    rets = compute_daily_log_returns(prices)
    logger.info("daily log returns: %d rows from %d firms", len(rets), rets["gvkey"].nunique())
    srf = quarterly_cross_sectional_skewness(rets)
    logger.info("SRF quarters: %d (first %s, last %s)",
                len(srf), srf["quarter_release_date"].min(), srf["quarter_release_date"].max())
    if save and not srf.empty:
        out_dir.mkdir(parents=True, exist_ok=True)
        snap = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
        out_path = out_dir / f"srf_{snap}.parquet"
        srf.to_parquet(out_path)
    return srf


__all__ = [
    "FINANCIAL_SECTOR_CODE",
    "build_srf",
    "compute_daily_log_returns",
    "quarterly_cross_sectional_skewness",
]
