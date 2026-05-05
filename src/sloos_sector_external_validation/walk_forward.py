"""Walk-forward 5-fold chronological 80/20 split (CLAUDE.md §1.9).

For each fold k ∈ {1, 2, 3, 4, 5}:
  - Train events = chronological first k/5 of all events
  - Test events  = chronological events [k/5, (k+1)/5)

Re-fit Layer A on train events to derive long/short sector baskets, then
apply those baskets to test events and compute test-period Sharpe.

PASS condition (Phase 1 §7): ≥ 4/5 folds with positive net-cost Sharpe.

Net-cost adjustment per fold: subtract 5bp/yr × span_years from the
cumulative test-period return (consistent with Gate M cost rate).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .layer_a import run_layer_a
from .layer_d import (
    DEFAULT_HORIZON_LABEL,
    annualize_per_event,
    compute_strategy_returns,
    select_long_short_sectors,
)

logger = logging.getLogger(__name__)


N_FOLDS = 5
GATE_M_COST_BP_PER_YEAR = 5.0
WALK_FORWARD_FLOOR = 4  # ≥4/5 folds PASS


@dataclass
class FoldResult:
    fold: int
    n_train_events: int
    n_test_events: int
    train_long: list[int]
    train_short: list[int]
    train_layer_a_passing: int
    test_sharpe_ann: float
    test_net_sharpe_ann: float
    test_mean_per_event: float
    test_std_per_event: float
    pass_fold: bool


@dataclass
class WalkForwardResult:
    n_folds_total: int
    n_folds_pass: int
    folds: list[FoldResult]
    pass_phase2_floor: bool
    floor: int = WALK_FORWARD_FLOOR


def _split_chronological(event_dates: list[pd.Timestamp], n_folds: int = N_FOLDS) -> list[tuple[list[int], list[int]]]:
    """Return list of (train_idx, test_idx) for each fold (sklearn TimeSeriesSplit semantics).

    For n_folds=5 and T=36, boundaries are [T/6, 2T/6, ..., 6T/6]. This gives
    5 expanding-window splits where each test fold has ~T/6 events:
      fold 1: train [0..T/6], test [T/6..2T/6]
      fold 5: train [0..5T/6], test [5T/6..T]
    """
    T = len(event_dates)
    if T < n_folds + 1:
        raise ValueError(f"need >= {n_folds + 1} events, got {T}")
    n_segments = n_folds + 1
    boundaries = [int(round(T * k / n_segments)) for k in range(n_segments + 1)]
    out = []
    for k in range(1, n_folds + 1):
        train_idx = list(range(0, boundaries[k]))
        test_idx = list(range(boundaries[k], boundaries[k + 1]))
        if train_idx and test_idx:
            out.append((train_idx, test_idx))
    return out


def _per_event_strategy_in_test(panel: pd.DataFrame, long_sectors: list[int], short_sectors: list[int], horizon: str = DEFAULT_HORIZON_LABEL) -> pd.DataFrame:
    """Apply L/S baskets (from train) to compute test-event strategy returns."""
    return compute_strategy_returns(panel, long_sectors, short_sectors, horizon=horizon)


def run_walk_forward(
    panel: pd.DataFrame,
    horizon: str = DEFAULT_HORIZON_LABEL,
    cost_bp_per_year: float = GATE_M_COST_BP_PER_YEAR,
) -> WalkForwardResult:
    """5-fold chronological walk-forward."""
    panel_h = panel[panel["horizon"] == horizon].copy()
    event_dates_sorted = sorted(panel_h["event_date"].unique())

    splits = _split_chronological(event_dates_sorted)
    folds: list[FoldResult] = []
    for fold_i, (train_idx, test_idx) in enumerate(splits, start=1):
        train_events = [event_dates_sorted[i] for i in train_idx]
        test_events = [event_dates_sorted[i] for i in test_idx]

        train_panel = panel_h[panel_h["event_date"].isin(train_events)].copy()
        test_panel = panel_h[panel_h["event_date"].isin(test_events)].copy()

        if train_panel.empty or test_panel.empty:
            folds.append(
                FoldResult(
                    fold=fold_i,
                    n_train_events=len(train_events),
                    n_test_events=len(test_events),
                    train_long=[],
                    train_short=[],
                    train_layer_a_passing=0,
                    test_sharpe_ann=float("nan"),
                    test_net_sharpe_ann=float("nan"),
                    test_mean_per_event=float("nan"),
                    test_std_per_event=float("nan"),
                    pass_fold=False,
                )
            )
            continue

        train_layer_a = run_layer_a(train_panel)
        train_layer_a_h = train_layer_a[train_layer_a["horizon"] == horizon].copy()
        # Use Bonferroni-K=33 critical from training-fold sample size
        n_pass = int(train_layer_a_h["abs_t_passes_bonferroni"].sum())

        long_sec, short_sec = select_long_short_sectors(train_layer_a, horizon=horizon)

        # Edge case: train has no significant cell on one side. Fall back to top-2/bottom-2 by |t|.
        if not long_sec or not short_sec:
            ranked = train_layer_a_h.sort_values("t_stat")
            short_sec = ranked.head(2)["sector_code"].astype(int).tolist()
            long_sec = ranked.tail(2)["sector_code"].astype(int).tolist()
            logger.info("fold %d: empty Bonferroni-pass basket on one side; falling back to top-2/bot-2 by t", fold_i)

        test_strat = _per_event_strategy_in_test(test_panel, long_sec, short_sec, horizon=horizon)
        if test_strat.empty:
            folds.append(
                FoldResult(
                    fold=fold_i,
                    n_train_events=len(train_events),
                    n_test_events=len(test_events),
                    train_long=long_sec,
                    train_short=short_sec,
                    train_layer_a_passing=n_pass,
                    test_sharpe_ann=float("nan"),
                    test_net_sharpe_ann=float("nan"),
                    test_mean_per_event=float("nan"),
                    test_std_per_event=float("nan"),
                    pass_fold=False,
                )
            )
            continue

        n = len(test_strat)
        span = float((test_strat["event_date"].max() - test_strat["event_date"].min()).days)
        # If span is 0 (single event), can't annualize meaningfully — use raw mean as Sharpe proxy
        mean = float(test_strat["strategy_ret"].mean())
        std = float(test_strat["strategy_ret"].std(ddof=1)) if n > 1 else float("nan")
        sharpe_per_event = mean / std if std and np.isfinite(std) and std > 0 else float("nan")
        sharpe_ann = annualize_per_event(sharpe_per_event, n, span) if span > 0 else sharpe_per_event

        # Net-cost: subtract cost/yr × proportion of year held
        events_per_year = n / max(span / 365.25, 1e-9) if span > 0 else 1.0
        cost_per_event = (cost_bp_per_year / 1e4) / events_per_year if events_per_year > 0 else 0.0
        net_mean = mean - cost_per_event
        net_sharpe_per_event = net_mean / std if std and np.isfinite(std) and std > 0 else float("nan")
        net_sharpe_ann = annualize_per_event(net_sharpe_per_event, n, span) if span > 0 else net_sharpe_per_event

        passes = bool(np.isfinite(net_sharpe_ann) and net_sharpe_ann > 0.0)

        folds.append(
            FoldResult(
                fold=fold_i,
                n_train_events=len(train_events),
                n_test_events=len(test_events),
                train_long=long_sec,
                train_short=short_sec,
                train_layer_a_passing=n_pass,
                test_sharpe_ann=float(sharpe_ann),
                test_net_sharpe_ann=float(net_sharpe_ann),
                test_mean_per_event=float(mean),
                test_std_per_event=float(std),
                pass_fold=passes,
            )
        )

    n_pass = sum(int(f.pass_fold) for f in folds)
    return WalkForwardResult(
        n_folds_total=len(folds),
        n_folds_pass=n_pass,
        folds=folds,
        pass_phase2_floor=bool(n_pass >= WALK_FORWARD_FLOOR),
    )


__all__ = [
    "FoldResult",
    "GATE_M_COST_BP_PER_YEAR",
    "N_FOLDS",
    "WALK_FORWARD_FLOOR",
    "WalkForwardResult",
    "_split_chronological",
    "run_walk_forward",
]
