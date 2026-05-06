"""Compustat Global forward CAR panel build (Path B specific, S3).

Lifts S1's `crsp_panel.build_crsp_sector_panel` pattern for Compustat Global
data. The CRSP-vs-Compustat-Global vendor difference:

    CRSP                          | Compustat Global (g_secd)
    ----------------------------- | --------------------------
    permno                        | (gvkey, iid)  — listing-level identifier
    dsf.ret (delisting-adjusted)  | computed: log(adj_close_t / adj_close_t-1)
                                  | where adj_close = prccd * trfd / ajexdi

Adjustment factors:
    - `ajexdi`: cumulative split adjustment factor (price scale)
    - `trfd`: total return factor (folds dividends back into price for
      total-return time-series)
    - adj_close = prccd * trfd / ajexdi gives a continuous total-return-adjusted
      time-series suitable for log-return computation

Forward CAR (matching S1 convention):
    CAR_{i,e,h} = sum_{t=t0..t0+h_td}( log_ret_{i,t} ) - market_{e,h}
    where market_{e,h} = cross-sectional equal-weighted mean of log_ret over
    all firms at (e, h).

Horizons: 1m=21 trading days, 3m=63 td, 6m=126 td (matching S1 lock §1.3).

Per-country panel build:
    UK panel: filtered to UK universe (loc='GBR'), 12 BoE event dates
    Eurozone panel: filtered to Eurozone-broad universe, 21 ECB event dates

Currency note: CAR is computed in LOCAL currency per listing. Cross-country
Spearman comparisons (Phase 1 N-S3 tests) compare per-sector mean CAR
*ranks*, not raw values, so currency unit doesn't matter at the rank level.
USD-converted robustness deferred to Phase 2.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .preferred_universe import GICS_NAME

logger = logging.getLogger(__name__)


@dataclass
class CompGlobalPanelStats:
    n_listings_requested: int
    n_rows_pulled: int
    date_min: str
    date_max: str
    n_unique_listings_in_data: int
    n_panel_rows: int
    n_unique_firms_with_events: int


def _open_courier():
    courier_path = Path("e:/wrds-data-courier/src")
    if str(courier_path) not in sys.path:
        sys.path.insert(0, str(courier_path))
    from wrds_courier_client import open_db  # type: ignore[import-not-found]

    return open_db()


def pull_g_secd_for_listings(
    listings: list[tuple[str, str]],
    start_date: str = "2003-01-01",
) -> pd.DataFrame:
    """Bulk-fetch g_secd rows for given (gvkey, iid) listings.

    The (gvkey, iid) tuple identifies one share-class listing on one exchange.
    A multi-listed firm (e.g. Barclays primary GBP + secondary USD ADR) has
    multiple iid values and we only want the STOXX 600 constituent listing
    (the one that appears in g_idxcst_his with gvkeyx=150376).

    Returns columns: gvkey, iid, datadate, prccd, ajexdi, trfd, curcdd.
    """
    if not listings:
        raise ValueError("no listings provided")
    db = _open_courier()
    # Build (gvkey, iid) IN ((..., ...)) constraint via temporary table
    listing_df = pd.DataFrame(listings, columns=["gvkey", "iid"])
    db.register("listings_filter", listing_df)
    sql = f"""
        SELECT s.gvkey, s.iid, s.datadate, s.prccd, s.ajexdi, s.trfd, s.curcdd
        FROM comp_global_daily.g_secd s
        JOIN listings_filter f ON f.gvkey = s.gvkey AND f.iid = s.iid
        WHERE s.datadate >= DATE '{start_date}'
          AND s.prccd IS NOT NULL AND s.prccd > 0
          AND s.ajexdi IS NOT NULL AND s.ajexdi > 0
          AND s.trfd IS NOT NULL
        ORDER BY s.gvkey, s.iid, s.datadate
    """
    df = db.execute(sql).fetchdf()
    db.unregister("listings_filter")
    df["datadate"] = pd.to_datetime(df["datadate"])
    return df


def compute_daily_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Per (gvkey, iid), compute daily total-return log returns.

    adj_close = prccd * trfd / ajexdi
    log_ret_t = log(adj_close_t / adj_close_{t-1})
    """
    df = prices.copy()
    df["adj_close"] = df["prccd"] * df["trfd"] / df["ajexdi"]
    df = df[df["adj_close"] > 0].sort_values(["gvkey", "iid", "datadate"])
    df["adj_close_prev"] = df.groupby(["gvkey", "iid"])["adj_close"].shift(1)
    df["log_ret"] = np.log(df["adj_close"] / df["adj_close_prev"])
    df = df[df["log_ret"].notna() & np.isfinite(df["log_ret"])]
    # Drop pathological log-returns > 200% in one day (data error proxy)
    df = df[df["log_ret"].abs() < 1.5]
    return df[["gvkey", "iid", "datadate", "log_ret", "curcdd", "adj_close"]].reset_index(drop=True)


def build_country_panel(
    shocks: pd.DataFrame,
    universe: pd.DataFrame,
    horizons: dict[str, int] | None = None,
    pad_days: int = 10,
) -> tuple[pd.DataFrame, CompGlobalPanelStats]:
    """Forward CAR panel for a single country (UK or Eurozone).

    Args:
        shocks: AR(1) shock identification DataFrame (output of construct_shocks).
                Index = quarter-end Timestamp; columns include is_event_start, shock_sign.
        universe: STOXX 600 universe rows for the target country (UK or Eurozone).
                  Columns: gvkey, iid, gsector, loc, conml, from_date, thru.
        horizons: dict like {'1m': 21, '3m': 63, '6m': 126} (trading days).

    Returns (panel_df, stats):
        panel_df columns: event_date, gvkey, iid, sector, sector_name, horizon,
                          horizon_td, t0_date, t1_date, log_ret, market_log_ret,
                          car, shock_sign, curcdd.
    """
    horizons = horizons or {"1m": 21, "3m": 63, "6m": 126}
    h_max = max(horizons.values())

    universe_clean = universe.dropna(subset=["gvkey", "iid", "gsector"]).copy()
    universe_clean["gsector"] = universe_clean["gsector"].astype(int)

    # Per-listing sector map. (gvkey, iid) → (gsector, conml, from_date, thru)
    listings = list(set(zip(universe_clean["gvkey"].astype(str), universe_clean["iid"].astype(str))))
    sector_map = {
        (str(r["gvkey"]), str(r["iid"])): int(r["gsector"])
        for _, r in universe_clean.iterrows()
    }
    membership_map = {
        (str(r["gvkey"]), str(r["iid"])): (
            pd.Timestamp(r["from_date"]),
            pd.Timestamp(r["thru"]) if pd.notna(r["thru"]) else None,
        )
        for _, r in universe_clean.iterrows()
    }

    event_dates = pd.DatetimeIndex(shocks.index[shocks["is_event_start"].fillna(False)])
    if event_dates.empty:
        raise ValueError("shocks DataFrame has no events flagged")
    sign_map = shocks.loc[event_dates, "shock_sign"].to_dict()

    earliest = pd.Timestamp(event_dates.min())
    start_date = (earliest - pd.Timedelta(days=pad_days)).strftime("%Y-%m-%d")
    logger.info("pulling g_secd for %d listings from %s onward...", len(listings), start_date)
    secd = pull_g_secd_for_listings(listings, start_date=start_date)
    n_rows = int(len(secd))
    logger.info("g_secd rows pulled: %d", n_rows)

    if secd.empty:
        raise RuntimeError("g_secd returned empty for universe + date filter")

    rets = compute_daily_log_returns(secd)
    rets = rets.sort_values(["gvkey", "iid", "datadate"]).reset_index(drop=True)
    n_unique_listings_in_data = int(rets[["gvkey", "iid"]].drop_duplicates().shape[0])

    rows: list[dict] = []
    for (gvkey, iid), g in rets.groupby(["gvkey", "iid"], sort=False):
        gv_str = str(gvkey)
        iid_str = str(iid)
        sector = sector_map.get((gv_str, iid_str))
        if sector is None:
            continue
        from_t, thru_t = membership_map.get((gv_str, iid_str), (None, None))
        dates_arr = g["datadate"].to_numpy()
        log_rets = g["log_ret"].to_numpy()
        curcdd_arr = g["curcdd"].to_numpy()
        for evt in event_dates:
            # Time-varying universe filter: firm must be a STOXX 600 member at event date
            if from_t is not None and evt < from_t:
                continue
            if thru_t is not None and evt > thru_t:
                continue
            evt_np = np.datetime64(evt.to_datetime64(), "ns")
            i0 = int(np.searchsorted(dates_arr, evt_np, side="left"))
            if i0 >= len(dates_arr):
                continue
            t0_d = pd.Timestamp(dates_arr[i0])
            curcdd_at_evt = curcdd_arr[i0]
            for h_label, h_td in horizons.items():
                i1 = i0 + h_td
                if i1 >= len(dates_arr):
                    continue
                cum = float(log_rets[i0 : i1 + 1].sum())
                if not np.isfinite(cum):
                    continue
                t1_d = pd.Timestamp(dates_arr[i1])
                rows.append(
                    {
                        "event_date": evt,
                        "gvkey": gv_str,
                        "iid": iid_str,
                        "sector": int(sector),
                        "horizon": h_label,
                        "horizon_td": h_td,
                        "t0_date": t0_d,
                        "t1_date": t1_d,
                        "log_ret": cum,
                        "curcdd": curcdd_at_evt,
                    }
                )

    panel = pd.DataFrame(rows)
    stats = CompGlobalPanelStats(
        n_listings_requested=len(listings),
        n_rows_pulled=n_rows,
        date_min=str(rets["datadate"].min().date()) if not rets.empty else "",
        date_max=str(rets["datadate"].max().date()) if not rets.empty else "",
        n_unique_listings_in_data=n_unique_listings_in_data,
        n_panel_rows=int(len(panel)),
        n_unique_firms_with_events=int(panel["gvkey"].nunique()) if not panel.empty else 0,
    )

    if panel.empty:
        return panel, stats

    # Cross-sectional equal-weighted market log-return per (event_date, horizon)
    market = panel.groupby(["event_date", "horizon"])["log_ret"].mean().rename("market_log_ret")
    panel = panel.merge(market.reset_index(), on=["event_date", "horizon"], how="left")
    panel["car"] = panel["log_ret"] - panel["market_log_ret"]
    panel["shock_sign"] = panel["event_date"].map(sign_map).astype(int)
    panel["sector_name"] = panel["sector"].map(GICS_NAME)

    return panel, stats


def n_with_car_audit(panel: pd.DataFrame, floor: int = 50) -> pd.DataFrame:
    """Per-(sector × horizon) count of firm-events with non-null CAR.

    Returns DataFrame with columns: sector, sector_name, horizon, n_with_car,
    floor_passed.
    """
    if panel.empty:
        return pd.DataFrame(columns=["sector", "sector_name", "horizon", "n_with_car", "floor_passed"])
    grp = panel.dropna(subset=["car"]).groupby(["sector", "horizon"])
    n = grp.size().rename("n_with_car").reset_index()
    n["sector_name"] = n["sector"].map(GICS_NAME)
    n["floor_passed"] = n["n_with_car"] >= floor
    return n.sort_values(["sector", "horizon"]).reset_index(drop=True)


def save_country_panel(
    panel: pd.DataFrame,
    country_label: str,
    out_dir: Path = Path("data/cache"),
    snap: str | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if snap is None:
        snap = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    out_path = out_dir / f"comp_global_panel_{country_label}_{snap}.parquet"
    panel.to_parquet(out_path)
    return out_path


__all__ = [
    "CompGlobalPanelStats",
    "build_country_panel",
    "compute_daily_log_returns",
    "n_with_car_audit",
    "pull_g_secd_for_listings",
    "save_country_panel",
]
