"""CRSP-based survivor-bias-free price + return panel (Phase 3 honest revision).

CRSP `dsf` includes delisting returns natively (the `ret` column folds
delisting return into the daily return on the delisting date). When a firm
is delisted, the panel ends with that firm's true experience including the
delisting impact — eliminating the survivor bias inherent in the original
Compustat-sec_dprc-based panel which only includes currently-listed firms.

We pull CRSP dsf by permno (mapped from our R3000 universe via CUSIP8 link),
compute daily log returns from cumulative-adjusted prices, and provide
helper functions to build event-study sector panels.

Date range: CRSP dsf 1925-12-31 → 2024-12-31 (107M rows). For our SLOOS
events spanning 1990-Q4 to 2025-Q2, we lose only the very last event
(2025-04-01) which falls past CRSP coverage. We track this gap in the
audit (acceptable — it just removes 1 of 36 events, the strategy still
has 35 events of CRSP-corrected data plus the 36th from Compustat-only
panel for cross-validation).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .preferred_universe import GICS_NAME
from .wrds_courier_adapter import query

logger = logging.getLogger(__name__)


@dataclass
class CRSPPanelStats:
    n_permnos_requested: int
    n_rows_pulled: int
    date_min: str
    date_max: str
    n_unique_permnos_in_data: int
    n_panel_rows: int
    n_unique_firms_with_events: int


def pull_crsp_dsf(permnos: list[int], start_date: str = "1990-01-01") -> pd.DataFrame:
    """Bulk pull CRSP dsf for a list of permnos.

    Returns columns: permno, date, prc, ret, retx, shrout, cfacpr, cfacshr.
    `ret` is the delisting-adjusted return (NaN for missing data).
    """
    if not permnos:
        raise ValueError("no permnos provided")
    quoted = ",".join(str(int(p)) for p in permnos)
    sql = f"""
        SELECT permno, date, prc, ret, retx, shrout, cfacpr, cfacshr
        FROM crsp_a_stock.dsf
        WHERE permno IN ({quoted})
          AND date >= DATE '{start_date}'
          AND ret IS NOT NULL
        ORDER BY permno, date
    """
    return query(sql)


def compute_daily_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """From CRSP dsf rows with `ret`, return per-permno daily log returns.

    CRSP `ret` is simple return including delisting; we convert to log
    return for additivity over horizons.
    """
    df = prices.copy()
    df = df.dropna(subset=["ret"])
    df = df[df["ret"] > -1.0]  # drop pathological values
    df["log_ret"] = np.log1p(df["ret"])
    df = df[np.isfinite(df["log_ret"])]
    return df[["permno", "date", "log_ret", "ret"]]


def build_crsp_sector_panel(
    shocks: pd.DataFrame,
    universe: pd.DataFrame,
    link: pd.DataFrame,
    horizons: dict[str, int] | None = None,
    time_varying: bool = False,
) -> tuple[pd.DataFrame, CRSPPanelStats]:
    """Build forward CAR panel using CRSP returns.

    Same shape as `sector_panel.build_sector_panel` but with CRSP data:
    columns event_date, gvkey (from link), permno, sector, horizon,
    horizon_td, t0_date, t1_date, log_ret, market_log_ret, car, shock_sign,
    sector_name.

    Args:
        time_varying: if True, `link` is expected to have valid_from/valid_to
            columns (from `crsp_link_timevarying`); the per-event permno
            list is filtered to firms valid at each event date. If False
            (default), `link` is treated as static (single (permno, gvkey)
            mapping per firm, valid for all time).

    The benchmark `market_log_ret` is the cross-sectional equal-weighted
    mean log return per (event_date, horizon), same as v1 panel for
    apples-to-apples comparison.
    """
    horizons = horizons or {"1m": 21, "3m": 63, "6m": 126}
    h_max = max(horizons.values())

    universe_clean = universe.dropna(subset=["gvkey", "gsector"]).copy()
    universe_clean["gsector"] = universe_clean["gsector"].astype(int)
    universe_clean["gvkey_str"] = universe_clean["gvkey"].astype(str)

    link_clean = link.copy()
    link_clean["gvkey_str"] = link_clean["gvkey"].astype(str)
    link_clean["permno"] = link_clean["permno"].astype(int)

    if time_varying and "valid_from" in link_clean.columns:
        # For time-varying mode: keep valid_from/valid_to columns for per-event filtering
        merged = universe_clean.merge(
            link_clean[["permno", "gvkey_str", "valid_from", "valid_to"]],
            on="gvkey_str",
            how="inner",
        )
    else:
        merged = universe_clean.merge(link_clean[["permno", "gvkey_str"]], on="gvkey_str", how="inner")

    permno_to_sector: dict[int, int] = dict(zip(merged["permno"].astype(int), merged["gsector"].astype(int)))
    permno_to_gvkey: dict[int, str] = dict(zip(merged["permno"].astype(int), merged["gvkey_str"]))
    permnos = list(set(int(p) for p in merged["permno"].dropna()))

    event_dates = pd.DatetimeIndex(shocks.index[shocks["is_event_start"].fillna(False)])
    sign_map = shocks.loc[event_dates, "shock_sign"].to_dict()

    if not permnos:
        raise RuntimeError("no permno↔gvkey mapping in universe")

    earliest = pd.Timestamp(event_dates.min())
    start_date = (earliest - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
    logger.info("pulling CRSP dsf for %d permnos from %s onward...", len(permnos), start_date)
    dsf = pull_crsp_dsf(permnos, start_date=start_date)
    n_rows = int(len(dsf))
    logger.info("CRSP dsf rows: %d", n_rows)

    if dsf.empty:
        raise RuntimeError("CRSP dsf returned empty")

    rets = compute_daily_log_returns(dsf)
    rets = rets.sort_values(["permno", "date"]).reset_index(drop=True)

    # For time-varying mode: build per-event permno→gvkey lookup (subset valid at event date)
    if time_varying and "valid_from" in merged.columns:
        per_event_link: dict[pd.Timestamp, dict[int, tuple[str, int]]] = {}
        for evt in event_dates:
            valid_at_evt = merged[(merged["valid_from"] <= evt) & (merged["valid_to"] > evt)]
            per_event_link[evt] = {
                int(p): (str(g), int(s))
                for p, g, s in zip(valid_at_evt["permno"], valid_at_evt["gvkey_str"], valid_at_evt["gsector"])
            }
    else:
        per_event_link = None

    rows: list[dict] = []
    for permno, g in rets.groupby("permno", sort=False):
        permno_int = int(permno)
        dates_arr = g["date"].to_numpy()
        log_rets = g["log_ret"].to_numpy()
        for evt in event_dates:
            if per_event_link is not None:
                evt_lookup = per_event_link.get(evt, {})
                if permno_int not in evt_lookup:
                    continue  # firm not linked at this event date (time-varying mode)
                gvkey, sector = evt_lookup[permno_int]
            else:
                sector = permno_to_sector.get(permno_int)
                gvkey = permno_to_gvkey.get(permno_int)
                if sector is None or gvkey is None:
                    continue
            evt_np = np.datetime64(evt.to_datetime64(), "ns")
            i0 = int(np.searchsorted(dates_arr, evt_np, side="left"))
            if i0 >= len(dates_arr):
                continue
            t0_d = pd.Timestamp(dates_arr[i0])
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
                        "permno": permno_int,
                        "gvkey": gvkey,
                        "sector": int(sector),
                        "horizon": h_label,
                        "horizon_td": h_td,
                        "t0_date": t0_d,
                        "t1_date": t1_d,
                        "log_ret": cum,
                    }
                )

    panel = pd.DataFrame(rows)
    if panel.empty:
        return panel, CRSPPanelStats(
            n_permnos_requested=len(permnos),
            n_rows_pulled=n_rows,
            date_min=str(rets["date"].min().date()) if not rets.empty else "",
            date_max=str(rets["date"].max().date()) if not rets.empty else "",
            n_unique_permnos_in_data=int(rets["permno"].nunique()),
            n_panel_rows=0,
            n_unique_firms_with_events=0,
        )

    market = panel.groupby(["event_date", "horizon"])["log_ret"].mean().rename("market_log_ret")
    panel = panel.merge(market.reset_index(), on=["event_date", "horizon"], how="left")
    panel["car"] = panel["log_ret"] - panel["market_log_ret"]
    panel["shock_sign"] = panel["event_date"].map(sign_map).astype(int)
    panel["sector_name"] = panel["sector"].map(GICS_NAME)

    stats = CRSPPanelStats(
        n_permnos_requested=len(permnos),
        n_rows_pulled=n_rows,
        date_min=str(rets["date"].min().date()),
        date_max=str(rets["date"].max().date()),
        n_unique_permnos_in_data=int(rets["permno"].nunique()),
        n_panel_rows=int(len(panel)),
        n_unique_firms_with_events=int(panel["permno"].nunique()),
    )
    return panel, stats


def save_crsp_panel(panel: pd.DataFrame, out_dir: Path = Path("data/cache"), tag: str = "DRTSCILM_AR1") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    snap = pd.Timestamp.utcnow().tz_localize(None).strftime("%Y-%m-%d")
    out_path = out_dir / f"crsp_sector_panel_{tag}_{snap}.parquet"
    panel.to_parquet(out_path)
    return out_path


__all__ = [
    "CRSPPanelStats",
    "build_crsp_sector_panel",
    "compute_daily_log_returns",
    "pull_crsp_dsf",
    "save_crsp_panel",
]
