"""Sector panel build (Phase 0 Day 3).

For each shock event date and each R3000 firm with a primary common-stock
listing (iid='01') in Compustat sec_dprc, compute forward log returns at
{1m, 3m, 6m} horizons (21 / 63 / 126 trading days). Subtract cross-sectional
equal-weighted mean log return at each (event, horizon) to obtain CAR.

Output is a long DataFrame keyed (event_date, gvkey, horizon) with columns
needed by Phase 1 layer_a (Welch t-test on per-(sector, horizon) cells).

Conventions:
- t0 = first trading day with a valid adjusted price on or after the SLOOS
  release date. We use Compustat sec_dprc trading calendar (datadate
  effectively = exchange trading day). SLOOS release Monday → t0 typically
  same day or next.
- Adjusted price = prccd / ajexdi.fillna(1.0). ajexdi NaN means no
  adjustment recorded; default 1.0 leaves price unchanged.
- Market benchmark m_{e,h} = cross-sectional EQUAL-weighted mean log return
  across all firms with valid CAR for (event_date e, horizon h). For
  Phase 0 EDA this is sufficient; Phase 1 layer_a may swap to cap-weighted.
- CAR = firm_log_ret - m. By construction E[CAR] = 0 across all firms in a
  given (event, horizon) — the cross-sectional test is whether SECTOR mean
  deviates from zero.

Per-cell n audit:
- 11 sectors × 3 horizons = 33 unsigned cells
- Phase 0 §1.4 lock: n ≥ 50 per cell
- Plus 22 signed sub-cells (11 sectors × 2 signs) per horizon (66 total)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .preferred_universe import GICS_NAME
from .wrds_courier_adapter import query, resolve

logger = logging.getLogger(__name__)


HORIZONS_TD: dict[str, int] = {"1m": 21, "3m": 63, "6m": 126}
PRIMARY_IID = "01"


@dataclass
class PanelBuildStats:
    n_events: int
    n_event_slices_pulled: int
    n_rows_pulled: int
    n_panel_rows: int
    n_unique_firms: int


def _pull_bulk_prices(
    gvkeys: list[str],
    earliest_event: pd.Timestamp,
    horizon_td_max: int,
) -> pd.DataFrame:
    """Single bulk query for all (gvkey, datadate, prccd, ajexdi) in our universe.

    Each call to the courier scans a 6.4GB gzipped CSV (no index), so 36
    per-event queries took >15min. ONE query covering all events is ~30-60s.
    """
    start_buffer = earliest_event - pd.Timedelta(days=10)
    quoted = ",".join(f"'{g}'" for g in gvkeys)
    sql = f"""
        SELECT gvkey, datadate, prccd, ajexdi
        FROM {resolve('secd')}
        WHERE iid = '{PRIMARY_IID}'
          AND gvkey IN ({quoted})
          AND datadate >= DATE '{start_buffer.strftime('%Y-%m-%d')}'
          AND prccd IS NOT NULL
        ORDER BY gvkey, datadate
    """
    return query(sql)


def _per_firm_event_returns(
    firm_prices: pd.DataFrame,
    event_dates: pd.DatetimeIndex,
    horizons: dict[str, int],
) -> list[tuple]:
    """For one gvkey's full price series, compute log returns across all events × horizons.

    firm_prices: DataFrame sorted by datadate ascending, with adj_p column.
    Returns list of (event_date, horizon_label, horizon_td, t0_date, t1_date, t0_p, t1_p, log_ret) tuples.
    """
    if firm_prices.empty:
        return []
    dates_arr = firm_prices["datadate"].to_numpy()
    prices_arr = firm_prices["adj_p"].to_numpy()
    out: list[tuple] = []
    for evt in event_dates:
        # Find first trading day >= evt via searchsorted
        evt_np = np.datetime64(evt.to_datetime64(), "ns")
        i0 = int(np.searchsorted(dates_arr, evt_np, side="left"))
        if i0 >= len(dates_arr):
            continue
        t0_p = float(prices_arr[i0])
        if not np.isfinite(t0_p) or t0_p <= 0:
            continue
        t0_d = pd.Timestamp(dates_arr[i0])
        for h_label, h_td in horizons.items():
            i1 = i0 + h_td
            if i1 >= len(dates_arr):
                continue
            t1_p = float(prices_arr[i1])
            if not np.isfinite(t1_p) or t1_p <= 0:
                continue
            log_ret = float(np.log(t1_p / t0_p))
            if not np.isfinite(log_ret):
                continue
            t1_d = pd.Timestamp(dates_arr[i1])
            out.append((evt, h_label, h_td, t0_d, t1_d, t0_p, t1_p, log_ret))
    return out


def build_sector_panel(
    shocks: pd.DataFrame,
    universe: pd.DataFrame,
    horizons: dict[str, int] | None = None,
) -> tuple[pd.DataFrame, PanelBuildStats]:
    """End-to-end panel build via single bulk price pull + pandas event-loop.

    shocks: from `shock_construct.construct_shocks`. Index = release date,
            columns include is_event_start + shock_sign.
    universe: from `preferred_universe.build_universe`. Has gvkey + gsector.
    """
    horizons = horizons or HORIZONS_TD
    h_max = max(horizons.values())

    universe_clean = universe.dropna(subset=["gvkey", "gsector"]).copy()
    universe_clean["gsector"] = universe_clean["gsector"].astype(int)
    gvkey_to_sector = dict(
        zip(universe_clean["gvkey"].astype(str), universe_clean["gsector"].astype(int))
    )
    gvkeys = universe_clean["gvkey"].astype(str).unique().tolist()

    event_dates = shocks.index[shocks["is_event_start"].fillna(False)]
    sign_map = shocks.loc[event_dates, "shock_sign"].to_dict()

    if len(event_dates) == 0:
        return pd.DataFrame(), PanelBuildStats(0, 0, 0, 0, 0)

    earliest = pd.Timestamp(event_dates.min())

    logger.info("pulling bulk prices for %d gvkeys from %s onward...", len(gvkeys), earliest.date())
    bulk = _pull_bulk_prices(gvkeys, earliest, h_max)
    n_rows_pulled = int(len(bulk))
    logger.info("bulk pull complete: %d rows", n_rows_pulled)

    if bulk.empty:
        return pd.DataFrame(), PanelBuildStats(int(len(event_dates)), 1, 0, 0, 0)

    bulk["adj_p"] = bulk["prccd"] / bulk["ajexdi"].fillna(1.0).replace(0, np.nan)
    bulk = bulk.dropna(subset=["adj_p"])
    bulk = bulk[bulk["adj_p"] > 0]
    bulk = bulk.sort_values(["gvkey", "datadate"]).reset_index(drop=True)

    all_rows: list[dict] = []
    for gvkey, g in bulk.groupby("gvkey", sort=False):
        sector = gvkey_to_sector.get(str(gvkey))
        if sector is None:
            continue
        firm_results = _per_firm_event_returns(g, event_dates, horizons)
        for evt, h_label, h_td, t0_d, t1_d, t0_p, t1_p, log_ret in firm_results:
            all_rows.append(
                {
                    "event_date": evt,
                    "gvkey": str(gvkey),
                    "sector": sector,
                    "horizon": h_label,
                    "horizon_td": h_td,
                    "t0_date": t0_d,
                    "t1_date": t1_d,
                    "t0_p": t0_p,
                    "t1_p": t1_p,
                    "log_ret": log_ret,
                }
            )

    panel = pd.DataFrame(all_rows)
    if panel.empty:
        return panel, PanelBuildStats(int(len(event_dates)), 1, n_rows_pulled, 0, 0)

    market = panel.groupby(["event_date", "horizon"])["log_ret"].mean().rename("market_log_ret")
    panel = panel.merge(market.reset_index(), on=["event_date", "horizon"], how="left")
    panel["car"] = panel["log_ret"] - panel["market_log_ret"]
    panel["shock_sign"] = panel["event_date"].map(sign_map).astype(int)
    panel["sector_name"] = panel["sector"].map(GICS_NAME)

    stats = PanelBuildStats(
        n_events=int(len(event_dates)),
        n_event_slices_pulled=1,
        n_rows_pulled=n_rows_pulled,
        n_panel_rows=int(len(panel)),
        n_unique_firms=int(panel["gvkey"].nunique()),
    )
    return panel, stats


def per_cell_audit(panel: pd.DataFrame, n_min: int = 50) -> pd.DataFrame:
    """11×3 unsigned cells + 11×3×2 signed sub-cells: count + min(mean CAR, std).

    Returns DataFrame with columns: scope (unsigned/signed), sector_name,
    horizon, sign (or 'all'), n, mean_car_bp, std_car, t_stat, pass_n_min.
    """
    rows = []
    base = panel.dropna(subset=["car", "sector"]).copy()
    # Unsigned cells
    for (sec, horiz), g in base.groupby(["sector", "horizon"], sort=False):
        n = int(len(g))
        rows.append(
            {
                "scope": "unsigned",
                "sector_code": int(sec),
                "sector_name": GICS_NAME.get(int(sec), str(sec)),
                "horizon": horiz,
                "sign": "all",
                "n": n,
                "mean_car_bp": float(g["car"].mean() * 1e4),
                "std_car": float(g["car"].std()),
                "t_stat": float(g["car"].mean() / (g["car"].std() / np.sqrt(n))) if n > 1 else np.nan,
                "pass_n_min": n >= n_min,
            }
        )
    # Signed sub-cells
    for (sec, horiz, sgn), g in base.groupby(["sector", "horizon", "shock_sign"], sort=False):
        n = int(len(g))
        rows.append(
            {
                "scope": "signed",
                "sector_code": int(sec),
                "sector_name": GICS_NAME.get(int(sec), str(sec)),
                "horizon": horiz,
                "sign": "tighten" if int(sgn) == 1 else "ease",
                "n": n,
                "mean_car_bp": float(g["car"].mean() * 1e4),
                "std_car": float(g["car"].std()),
                "t_stat": float(g["car"].mean() / (g["car"].std() / np.sqrt(n))) if n > 1 else np.nan,
                "pass_n_min": n >= n_min,
            }
        )
    return pd.DataFrame(rows)


def panel_summary(panel: pd.DataFrame) -> dict[str, object]:
    """High-level statistics on the built panel."""
    if panel.empty:
        return {"n_panel_rows": 0}
    return {
        "n_panel_rows": int(len(panel)),
        "n_events": int(panel["event_date"].nunique()),
        "n_firms": int(panel["gvkey"].nunique()),
        "n_horizons": int(panel["horizon"].nunique()),
        "horizons": sorted(panel["horizon"].unique().tolist()),
        "events_min": str(panel["event_date"].min().date()),
        "events_max": str(panel["event_date"].max().date()),
        "n_sectors_present": int(panel["sector"].dropna().nunique()),
        "mean_abs_car_bp": float((panel["car"].abs().mean()) * 1e4),
        "median_abs_car_bp": float((panel["car"].abs().median()) * 1e4),
    }


def save_panel(panel: pd.DataFrame, out_dir: Path = Path("data/cache"), tag: str = "DRTSCILM_AR1") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    snap = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    out_path = out_dir / f"sector_panel_{tag}_{snap}.parquet"
    panel.to_parquet(out_path)
    return out_path


__all__ = [
    "HORIZONS_TD",
    "PanelBuildStats",
    "build_sector_panel",
    "panel_summary",
    "per_cell_audit",
    "save_panel",
]
