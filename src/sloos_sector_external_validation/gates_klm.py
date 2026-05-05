"""Gate L (lookahead shift sweep) + Gate K (subperiod) + Gate M (net-of-cost).

CLAUDE.md §1.10, §1.11, §1.12 robustness checks for Phase 2.

Gate L (lookahead shift sweep):
- shift entry by Δ trading days, hold for original horizon
- Sweep Δ ∈ {1, original_horizon, 2×original_horizon}
- PASS: shifted_Sharpe / baseline_Sharpe ≥ 0.5 at the LARGEST shift
- Rationale: if the SLOOS-shock signal is real, modest entry delay should
  preserve most of the alpha. If Sharpe collapses immediately, the
  result is likely look-ahead bias.

Gate K (subperiod reproduction):
- Split events into 1990-2010 (pre-GFC + GFC) and 2010-2026 (post-GFC + COVID)
- PASS: min(period_Sharpe) / max(period_Sharpe) ≥ 0.5
- Plus: SVB cohort (>=2023-Q3) standalone Sharpe ≥ 0.5 × full-sample Sharpe

Gate M (net-of-cost):
- 6m hold × ~5bp roundtrip × turnover 0.5/yr = ~5bp/yr cost
- net_Sharpe = (raw_return - cost) / strategy_std × annualization_factor
- PASS: net_Sharpe ≥ 0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

from .layer_d import (
    DEFAULT_HORIZON_LABEL,
    HORIZON_TD,
    annualize_per_event,
    select_long_short_sectors,
)
from .wrds_courier_adapter import query, resolve

logger = logging.getLogger(__name__)


GATE_L_DECAY_FLOOR = 0.5
GATE_K_RATIO_FLOOR = 0.5
GATE_M_COST_BP_PER_YEAR = 5.0
SUBPERIOD_SPLIT = pd.Timestamp("2010-01-01")


@dataclass
class GateLResult:
    horizon: str
    baseline_sharpe: float
    shifted_sharpes: dict[int, float]  # shift_days -> sharpe
    decay_ratio_at_max_shift: float
    pass_floor: bool
    floor: float = GATE_L_DECAY_FLOOR


@dataclass
class GateKResult:
    horizon: str
    full_sharpe: float
    pre_2010_sharpe: float
    post_2010_sharpe: float
    pre_n: int
    post_n: int
    sub_sharpe_ratio: float
    svb_n: int
    svb_sharpe: float
    svb_to_full_ratio: float
    pass_subperiod: bool
    pass_svb: bool
    floor: float = GATE_K_RATIO_FLOOR


@dataclass
class GateMResult:
    horizon: str
    raw_return_per_year: float
    cost_per_year: float
    net_return_per_year: float
    raw_sharpe_ann: float
    net_sharpe_ann: float
    pass_floor: bool


def _shifted_strategy_returns(
    panel: pd.DataFrame,
    long_sectors: list[int],
    short_sectors: list[int],
    horizon_td: int,
    shift_td: int,
) -> pd.DataFrame:
    """Recompute strategy returns with entry shifted by `shift_td` trading days.

    Uses Compustat sec_dprc to fetch a fresh slice of prices at the shifted
    entry/exit dates. For each event date, t0_shifted = original_t0 + shift_td
    trading days.

    Implementation: query a per-firm price slice covering the shifted window;
    compute log returns at each event-firm-horizon.
    """
    # Reuse existing panel positions: identify (event, gvkey, sector, t0_date) tuples
    # Then for each tuple, find the price `shift_td` trading days after t0 and
    # `shift_td + horizon_td` trading days after t0. The original panel already
    # has t0_date; we need t0+shift price and t0+shift+horizon price.
    base = panel[panel["horizon_td"] == horizon_td].copy()
    if base.empty:
        return pd.DataFrame()

    # For each unique gvkey, query a window of prices covering all events
    # plus shift+horizon buffer on each side.
    earliest = base["t0_date"].min()
    latest = base["t0_date"].max() + pd.Timedelta(days=int((shift_td + horizon_td) * 1.6) + 5)

    gvkeys = base["gvkey"].astype(str).unique().tolist()
    quoted = ",".join(f"'{g}'" for g in gvkeys)
    sql = f"""
        SELECT gvkey, datadate, prccd, ajexdi
        FROM {resolve('secd')}
        WHERE iid = '01'
          AND gvkey IN ({quoted})
          AND datadate >= DATE '{earliest.strftime('%Y-%m-%d')}'
          AND datadate <= DATE '{latest.strftime('%Y-%m-%d')}'
          AND prccd IS NOT NULL
        ORDER BY gvkey, datadate
    """
    bulk = query(sql)
    if bulk.empty:
        return pd.DataFrame()
    bulk["adj_p"] = bulk["prccd"] / bulk["ajexdi"].fillna(1.0).replace(0, np.nan)
    bulk = bulk.dropna(subset=["adj_p"])
    bulk = bulk[bulk["adj_p"] > 0]
    bulk = bulk.sort_values(["gvkey", "datadate"]).reset_index(drop=True)

    # For each (event, gvkey), find shifted t0 and shifted t1 prices
    rows = []
    by_gvkey = {gv: g.reset_index(drop=True) for gv, g in bulk.groupby("gvkey", sort=False)}

    for _, row in base.iterrows():
        gv = str(row["gvkey"])
        firm = by_gvkey.get(gv)
        if firm is None or firm.empty:
            continue
        t0_orig = pd.Timestamp(row["t0_date"])
        # Find index of t0_orig in firm's series
        dates_arr = firm["datadate"].to_numpy()
        prices_arr = firm["adj_p"].to_numpy()
        t0_np = np.datetime64(t0_orig.to_datetime64(), "ns")
        i0 = int(np.searchsorted(dates_arr, t0_np, side="left"))
        if i0 >= len(dates_arr):
            continue
        i_shift = i0 + shift_td
        i_exit = i_shift + horizon_td
        if i_exit >= len(dates_arr):
            continue
        p_shift = float(prices_arr[i_shift])
        p_exit = float(prices_arr[i_exit])
        if not np.isfinite(p_shift) or p_shift <= 0 or not np.isfinite(p_exit) or p_exit <= 0:
            continue
        log_ret = float(np.log(p_exit / p_shift))
        if not np.isfinite(log_ret):
            continue
        rows.append(
            {
                "event_date": row["event_date"],
                "gvkey": gv,
                "sector": int(row["sector"]),
                "log_ret": log_ret,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Compute strategy returns per event
    strat_rows = []
    for evt, g in df.groupby("event_date"):
        long = g[g["sector"].isin(long_sectors)]
        short = g[g["sector"].isin(short_sectors)]
        if long.empty or short.empty:
            continue
        strat_rows.append(
            {
                "event_date": evt,
                "long_ret": float(long["log_ret"].mean()),
                "short_ret": float(short["log_ret"].mean()),
                "strategy_ret": float(long["log_ret"].mean() - short["log_ret"].mean()),
                "n_long": int(len(long)),
                "n_short": int(len(short)),
            }
        )
    return pd.DataFrame(strat_rows).sort_values("event_date").reset_index(drop=True)


def _per_event_sharpe_annualized(strat: pd.DataFrame) -> float:
    if strat.empty:
        return float("nan")
    n = len(strat)
    if n < 2:
        return float("nan")
    mean = float(strat["strategy_ret"].mean())
    std = float(strat["strategy_ret"].std(ddof=1))
    if std == 0:
        return float("nan")
    span = float((strat["event_date"].max() - strat["event_date"].min()).days)
    return annualize_per_event(mean / std, n, span)


def run_gate_l(
    panel: pd.DataFrame,
    layer_a_results: pd.DataFrame,
    horizon: str = DEFAULT_HORIZON_LABEL,
    horizon_td: int = HORIZON_TD,
) -> GateLResult:
    long_sec, short_sec = select_long_short_sectors(layer_a_results, horizon=horizon)
    # Baseline: shift_td = 0 (= the panel returns directly)
    base_strat = panel[(panel["horizon_td"] == horizon_td) & (panel["sector"].isin(long_sec + short_sec))].copy()
    base_rows = []
    for evt, g in base_strat.groupby("event_date"):
        long = g[g["sector"].isin(long_sec)]
        short = g[g["sector"].isin(short_sec)]
        if long.empty or short.empty:
            continue
        base_rows.append({"event_date": evt, "strategy_ret": float(long["log_ret"].mean() - short["log_ret"].mean())})
    base_strat_df = pd.DataFrame(base_rows).sort_values("event_date").reset_index(drop=True)
    baseline_sharpe = _per_event_sharpe_annualized(base_strat_df)

    shifted: dict[int, float] = {}
    shift_days = [1, horizon_td, 2 * horizon_td]
    for sd in shift_days:
        s = _shifted_strategy_returns(panel, long_sec, short_sec, horizon_td=horizon_td, shift_td=sd)
        shifted[sd] = _per_event_sharpe_annualized(s)

    max_shift = max(shift_days)
    decay = shifted[max_shift] / baseline_sharpe if (baseline_sharpe and not np.isnan(baseline_sharpe)) else float("nan")
    return GateLResult(
        horizon=horizon,
        baseline_sharpe=baseline_sharpe,
        shifted_sharpes=shifted,
        decay_ratio_at_max_shift=float(decay),
        pass_floor=bool(np.isfinite(decay) and decay >= GATE_L_DECAY_FLOOR),
    )


def run_gate_k(
    panel: pd.DataFrame,
    layer_a_results: pd.DataFrame,
    horizon: str = DEFAULT_HORIZON_LABEL,
    horizon_td: int = HORIZON_TD,
) -> GateKResult:
    long_sec, short_sec = select_long_short_sectors(layer_a_results, horizon=horizon)
    sub = panel[(panel["horizon"] == horizon) & (panel["sector"].isin(long_sec + short_sec))].copy()
    rows = []
    for evt, g in sub.groupby("event_date"):
        long = g[g["sector"].isin(long_sec)]
        short = g[g["sector"].isin(short_sec)]
        if long.empty or short.empty:
            continue
        rows.append({"event_date": evt, "strategy_ret": float(long["log_ret"].mean() - short["log_ret"].mean())})
    strat = pd.DataFrame(rows).sort_values("event_date").reset_index(drop=True)
    if strat.empty:
        raise RuntimeError("Gate K: no strategy returns")

    full_sharpe = _per_event_sharpe_annualized(strat)
    pre = strat[strat["event_date"] < SUBPERIOD_SPLIT]
    post = strat[strat["event_date"] >= SUBPERIOD_SPLIT]
    pre_sh = _per_event_sharpe_annualized(pre)
    post_sh = _per_event_sharpe_annualized(post)

    # Sub-period ratio: smaller / larger
    if any(np.isnan(x) for x in (pre_sh, post_sh)):
        sub_ratio = float("nan")
    else:
        denom = max(abs(pre_sh), abs(post_sh))
        sub_ratio = min(abs(pre_sh), abs(post_sh)) / denom if denom > 0 else float("nan")

    svb = strat[strat["event_date"] >= pd.Timestamp("2023-07-01")]
    svb_sh = _per_event_sharpe_annualized(svb) if len(svb) >= 2 else float("nan")
    svb_ratio = (svb_sh / full_sharpe) if (full_sharpe and not np.isnan(full_sharpe) and not np.isnan(svb_sh)) else float("nan")

    return GateKResult(
        horizon=horizon,
        full_sharpe=full_sharpe,
        pre_2010_sharpe=pre_sh,
        post_2010_sharpe=post_sh,
        pre_n=int(len(pre)),
        post_n=int(len(post)),
        sub_sharpe_ratio=float(sub_ratio),
        svb_n=int(len(svb)),
        svb_sharpe=float(svb_sh),
        svb_to_full_ratio=float(svb_ratio),
        pass_subperiod=bool(np.isfinite(sub_ratio) and sub_ratio >= GATE_K_RATIO_FLOOR),
        pass_svb=bool(np.isfinite(svb_ratio) and svb_ratio >= GATE_K_RATIO_FLOOR) if not np.isnan(svb_ratio) else False,
    )


def run_gate_m(
    panel: pd.DataFrame,
    layer_a_results: pd.DataFrame,
    horizon: str = DEFAULT_HORIZON_LABEL,
    horizon_td: int = HORIZON_TD,
    cost_bp_per_year: float = GATE_M_COST_BP_PER_YEAR,
) -> GateMResult:
    long_sec, short_sec = select_long_short_sectors(layer_a_results, horizon=horizon)
    sub = panel[(panel["horizon"] == horizon) & (panel["sector"].isin(long_sec + short_sec))].copy()
    rows = []
    for evt, g in sub.groupby("event_date"):
        long = g[g["sector"].isin(long_sec)]
        short = g[g["sector"].isin(short_sec)]
        if long.empty or short.empty:
            continue
        rows.append({"event_date": evt, "strategy_ret": float(long["log_ret"].mean() - short["log_ret"].mean())})
    strat = pd.DataFrame(rows).sort_values("event_date").reset_index(drop=True)
    raw_sharpe = _per_event_sharpe_annualized(strat)

    span_yr = float((strat["event_date"].max() - strat["event_date"].min()).days) / 365.25
    n = len(strat)
    raw_return_total = float(strat["strategy_ret"].sum())
    raw_return_per_year = raw_return_total / max(span_yr, 1e-9)
    cost_per_year = cost_bp_per_year / 1e4
    net_return_per_year = raw_return_per_year - cost_per_year

    std_per_event = float(strat["strategy_ret"].std(ddof=1))
    events_per_year = n / max(span_yr, 1e-9)
    net_mean_per_event = strat["strategy_ret"].mean() - (cost_per_year / events_per_year if events_per_year else 0.0)
    net_sharpe_per_event = net_mean_per_event / std_per_event if std_per_event else float("nan")
    net_sharpe_ann = net_sharpe_per_event * float(np.sqrt(events_per_year)) if events_per_year > 0 else float("nan")

    return GateMResult(
        horizon=horizon,
        raw_return_per_year=raw_return_per_year,
        cost_per_year=cost_per_year,
        net_return_per_year=net_return_per_year,
        raw_sharpe_ann=raw_sharpe,
        net_sharpe_ann=net_sharpe_ann,
        pass_floor=bool(np.isfinite(net_sharpe_ann) and net_sharpe_ann >= 0.0),
    )


__all__ = [
    "GATE_K_RATIO_FLOOR",
    "GATE_L_DECAY_FLOOR",
    "GATE_M_COST_BP_PER_YEAR",
    "GateKResult",
    "GateLResult",
    "GateMResult",
    "SUBPERIOD_SPLIT",
    "run_gate_k",
    "run_gate_l",
    "run_gate_m",
]
