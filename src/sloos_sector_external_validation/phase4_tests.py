"""Phase 4 PRIMARY robustness tests for event-study regime-detection framework.

CLAUDE.md §1 amended 2026-05-05 Phase 4. Four tests:

(a) F-test sector heterogeneity per horizon  (`run_test_a_ftest`)
(b) Block bootstrap on cell t-stats           (`run_test_b_bootstrap`)
(c) Alternative event definition via DRTSCIS  (`run_test_c_alt_event_def`)
(d) VIX-regime stratification                  (`run_test_d_vix_regime`)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as st

from .layer_a import K_BONFERRONI, _bonferroni_critical_t, run_layer_a
from .preferred_universe import GICS_NAME

logger = logging.getLogger(__name__)


# ============================================================
# Test (a) — F-test sector heterogeneity
# ============================================================

@dataclass
class FTestResult:
    horizon: str
    f_stat: float
    p_value: float
    df_between: int
    df_within: int
    n_sectors: int
    pass_at_05: bool


def run_test_a_ftest(panel: pd.DataFrame) -> pd.DataFrame:
    """One-way ANOVA across sectors per horizon.

    H_0: all 11 sectors have equal mean CAR at horizon h.
    PASS condition: p<0.05 at ≥1 horizon.
    """
    rows = []
    for horizon in panel["horizon"].unique():
        sub = panel[panel["horizon"] == horizon].dropna(subset=["car", "sector"])
        groups = [g["car"].values for _, g in sub.groupby("sector") if len(g) >= 2]
        if len(groups) < 2:
            continue
        f, p = st.f_oneway(*groups)
        n_sectors = len(groups)
        n_total = sum(len(g) for g in groups)
        rows.append(
            FTestResult(
                horizon=str(horizon),
                f_stat=float(f),
                p_value=float(p),
                df_between=n_sectors - 1,
                df_within=n_total - n_sectors,
                n_sectors=n_sectors,
                pass_at_05=bool(p < 0.05),
            )
        )
    return pd.DataFrame([r.__dict__ for r in rows])


# ============================================================
# Test (b) — Block bootstrap on cell t-stats
# ============================================================

def run_test_b_bootstrap(
    panel: pd.DataFrame,
    n_iterations: int = 1000,
    seed: int = 42,
) -> pd.DataFrame:
    """Event-level resample bootstrap on cell t-statistics.

    For each iteration:
      1. Resample EVENTS with replacement (block-bootstrap at event level
         to preserve within-event firm correlation).
      2. Compute cell-level t-stats on the resampled panel.
    Returns 90% CI on each cell t-stat + share of iterations where
    |t| > Bonferroni critical 3.17.

    PASS condition: ≥5 cells with 90% CI lower-bound (in |t| sense) > 3.17.
    """
    rng = np.random.default_rng(seed)
    base = panel.dropna(subset=["car", "sector"]).copy()
    events = sorted(base["event_date"].unique())
    n_events = len(events)

    # Sector × horizon cells
    sector_horizons = sorted(set(zip(base["sector"], base["horizon"])))
    n_cells = len(sector_horizons)
    boot_t = {(int(s), str(h)): np.empty(n_iterations) for s, h in sector_horizons}

    # Pre-index events for fast lookup
    event_groups = {evt: base[base["event_date"] == evt] for evt in events}

    for it in range(n_iterations):
        idx = rng.integers(0, n_events, size=n_events)
        sampled_events = [events[i] for i in idx]
        sampled = pd.concat([event_groups[e] for e in sampled_events], ignore_index=True)
        for (sec, h), tarr in boot_t.items():
            cell = sampled[(sampled["sector"] == sec) & (sampled["horizon"] == h)]
            if len(cell) < 2:
                tarr[it] = np.nan
                continue
            mean = cell["car"].mean()
            sd = cell["car"].std(ddof=1)
            if not np.isfinite(sd) or sd == 0:
                tarr[it] = np.nan
                continue
            tarr[it] = mean / (sd / np.sqrt(len(cell)))

    rows = []
    crit = _bonferroni_critical_t(df=10_000, k=K_BONFERRONI, alpha=0.05)
    for (sec, h), tarr in boot_t.items():
        ts = tarr[np.isfinite(tarr)]
        if len(ts) == 0:
            continue
        abs_ts = np.abs(ts)
        rows.append(
            {
                "sector_code": sec,
                "sector_name": GICS_NAME.get(int(sec), str(sec)),
                "horizon": h,
                "n_iter": int(len(ts)),
                "t_mean": float(np.mean(ts)),
                "t_q05": float(np.quantile(ts, 0.05)),
                "t_q95": float(np.quantile(ts, 0.95)),
                "abs_t_q05": float(np.quantile(abs_ts, 0.05)),
                "abs_t_q95": float(np.quantile(abs_ts, 0.95)),
                "share_pass_bonferroni": float(np.mean(abs_ts > crit)),
                "ci_lower_pass_bonferroni": bool(np.quantile(abs_ts, 0.05) > crit),
            }
        )
    return pd.DataFrame(rows)


# ============================================================
# Test (d) — VIX-regime stratification
# ============================================================

def run_test_d_vix_regime(
    panel: pd.DataFrame,
    ecsi_panel: pd.DataFrame,
    vix_threshold_high: float = 25.0,
    vix_threshold_low: float = 20.0,
) -> dict:
    """Split events by VIX at release date; compute cell-level t-stats per regime.

    PASS condition: sign agreement ≥7/11 sectors at 6m horizon between
    high-VIX and low-VIX regimes (i.e., the qualitative pattern persists
    across regimes).
    """
    base = panel.dropna(subset=["car", "sector"]).copy()
    base["event_date"] = pd.to_datetime(base["event_date"])

    # Map event_date → VIX from ecsi_panel
    ecsi = ecsi_panel.copy()
    ecsi.index = pd.to_datetime(ecsi.index)
    if "vix" not in ecsi.columns:
        raise ValueError("ecsi_panel must have 'vix' column")
    vix_at_event = ecsi["vix"].to_dict()

    base["vix_at_event"] = base["event_date"].map(vix_at_event)
    base = base.dropna(subset=["vix_at_event"])

    high_panel = base[base["vix_at_event"] > vix_threshold_high].copy()
    low_panel = base[base["vix_at_event"] < vix_threshold_low].copy()
    mid_panel = base[(base["vix_at_event"] >= vix_threshold_low) & (base["vix_at_event"] <= vix_threshold_high)].copy()

    high_layer_a = run_layer_a(high_panel) if len(high_panel) > 0 else pd.DataFrame()
    low_layer_a = run_layer_a(low_panel) if len(low_panel) > 0 else pd.DataFrame()

    # Sign-agreement analysis at 6m
    if not high_layer_a.empty and not low_layer_a.empty:
        h6 = high_layer_a[high_layer_a["horizon"] == "6m"][["sector_code", "t_stat"]].rename(columns={"t_stat": "t_high"})
        l6 = low_layer_a[low_layer_a["horizon"] == "6m"][["sector_code", "t_stat"]].rename(columns={"t_stat": "t_low"})
        merged = h6.merge(l6, on="sector_code", how="inner")
        merged["sign_agree"] = (np.sign(merged["t_high"]) == np.sign(merged["t_low"]))
        sign_agree_count = int(merged["sign_agree"].sum())
        sign_agree_pct = sign_agree_count / len(merged) * 100 if len(merged) else 0.0
        spearman_corr = float(merged[["t_high", "t_low"]].corr(method="spearman").iloc[0, 1]) if len(merged) > 2 else float("nan")
    else:
        merged = pd.DataFrame()
        sign_agree_count = 0
        spearman_corr = float("nan")

    return {
        "n_events_high_vix": int(high_panel["event_date"].nunique()),
        "n_events_mid_vix": int(mid_panel["event_date"].nunique()),
        "n_events_low_vix": int(low_panel["event_date"].nunique()),
        "vix_threshold_high": vix_threshold_high,
        "vix_threshold_low": vix_threshold_low,
        "high_layer_a": high_layer_a,
        "low_layer_a": low_layer_a,
        "merged_6m": merged,
        "sign_agree_6m_count": sign_agree_count,
        "sign_agree_6m_total": int(len(merged)),
        "spearman_corr_6m": spearman_corr,
        "pass": bool(sign_agree_count >= 7),
    }


__all__ = [
    "FTestResult",
    "run_test_a_ftest",
    "run_test_b_bootstrap",
    "run_test_d_vix_regime",
]
