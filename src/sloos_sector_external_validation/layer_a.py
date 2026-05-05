"""Layer A — per-(sector × horizon) cross-section t-test on shock-event CARs.

Phase 1 §1.3 lock: K = 11 sectors × 3 horizons = 33 hypotheses. Bonferroni
correction at family-wise α=0.05 → per-test α'=0.05/33=0.00152 → critical
|t| at df→∞ ≈ 3.18 (CLAUDE.md notes 3.04 as approximation; we compute the
exact critical from the cell-specific df).

Test specification (per cell):
    H_0: μ_CAR = 0 vs H_1: μ_CAR ≠ 0
Statistic: one-sample t = mean_CAR / (std_CAR / sqrt(n)), df = n-1.
The "Welch" label in CLAUDE.md §1.5 is a one-sample-with-unbiased-variance
formulation (no group comparison; Welch-Satterthwaite df not needed).

PASS condition (Phase 1 §7 hard-kill): ≥5 cells significant at family-wise
α=0.05 after Bonferroni-K=33 correction.

Sign-stratified extension (CLAUDE.md §6 lever 4): also report per-cell
t-test on tightening-only and easing-only sub-samples (66 hypotheses if
treated independently — but we keep K=33 for the headline lock and report
sign-stratified as descriptive).
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as st

from .preferred_universe import GICS_NAME

logger = logging.getLogger(__name__)


K_BONFERRONI = 33  # 11 sectors × 3 horizons
ALPHA = 0.05


def _one_sample_ttest(values: np.ndarray) -> tuple[float, float, int]:
    """Return (t_stat, p_two_sided, df) for H_0: mean=0."""
    n = int(len(values))
    if n < 2:
        return (np.nan, np.nan, max(n - 1, 0))
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    if std == 0 or not np.isfinite(std):
        return (np.nan, np.nan, n - 1)
    t = mean / (std / np.sqrt(n))
    df = n - 1
    p = 2.0 * (1.0 - st.t.cdf(abs(t), df=df))
    return (float(t), float(p), df)


def _bonferroni_critical_t(df: int, k: int = K_BONFERRONI, alpha: float = ALPHA) -> float:
    """Two-sided Bonferroni-corrected critical |t| for family of size k at alpha."""
    alpha_per_test = alpha / k
    return float(st.t.ppf(1.0 - alpha_per_test / 2.0, df=df))


def run_layer_a(
    panel: pd.DataFrame,
    k: int = K_BONFERRONI,
    alpha: float = ALPHA,
) -> pd.DataFrame:
    """Compute per-cell t-test + Bonferroni significance flags.

    Returns DataFrame with columns:
    sector_code, sector_name, horizon, n, mean_car_bp, std_car, t_stat,
    df, p_value, critical_t_bonferroni, abs_t_passes_bonferroni.
    """
    base = panel.dropna(subset=["car", "sector"]).copy()
    rows = []
    for (sector, horizon), g in base.groupby(["sector", "horizon"], sort=False):
        values = g["car"].to_numpy()
        t, p, df = _one_sample_ttest(values)
        crit = _bonferroni_critical_t(df=df, k=k, alpha=alpha) if df >= 1 else np.nan
        passes = bool(np.isfinite(t) and np.isfinite(crit) and abs(t) >= crit)
        rows.append(
            {
                "sector_code": int(sector),
                "sector_name": GICS_NAME.get(int(sector), str(sector)),
                "horizon": horizon,
                "n": int(len(values)),
                "mean_car_bp": float(np.mean(values) * 1e4) if len(values) else np.nan,
                "std_car": float(np.std(values, ddof=1)) if len(values) > 1 else np.nan,
                "t_stat": t,
                "df": df,
                "p_value": p,
                "critical_t_bonferroni": crit,
                "abs_t_passes_bonferroni": passes,
            }
        )
    return pd.DataFrame(rows).sort_values(["horizon", "sector_code"]).reset_index(drop=True)


def run_layer_a_signed(
    panel: pd.DataFrame,
    k: int = K_BONFERRONI,
    alpha: float = ALPHA,
) -> pd.DataFrame:
    """Sign-stratified version: 66 sub-cells, descriptive only."""
    base = panel.dropna(subset=["car", "sector"]).copy()
    rows = []
    for (sector, horizon, sgn), g in base.groupby(["sector", "horizon", "shock_sign"], sort=False):
        values = g["car"].to_numpy()
        t, p, df = _one_sample_ttest(values)
        crit = _bonferroni_critical_t(df=df, k=k, alpha=alpha) if df >= 1 else np.nan
        passes = bool(np.isfinite(t) and np.isfinite(crit) and abs(t) >= crit)
        rows.append(
            {
                "sector_code": int(sector),
                "sector_name": GICS_NAME.get(int(sector), str(sector)),
                "horizon": horizon,
                "sign": "tighten" if int(sgn) == 1 else "ease",
                "n": int(len(values)),
                "mean_car_bp": float(np.mean(values) * 1e4) if len(values) else np.nan,
                "t_stat": t,
                "df": df,
                "p_value": p,
                "critical_t_bonferroni": crit,
                "abs_t_passes_bonferroni": passes,
            }
        )
    return pd.DataFrame(rows).sort_values(["horizon", "sector_code", "sign"]).reset_index(drop=True)


def layer_a_summary(results: pd.DataFrame, threshold_pass: int = 5) -> dict[str, object]:
    """Phase 1 PASS/FAIL gate per CLAUDE.md §7."""
    n_cells = int(len(results))
    n_pass = int(results["abs_t_passes_bonferroni"].sum())
    by_horizon = results.groupby("horizon")["abs_t_passes_bonferroni"].sum().astype(int).to_dict()
    by_sector = results.groupby("sector_name")["abs_t_passes_bonferroni"].sum().astype(int).to_dict()
    pass_phase1 = n_pass >= threshold_pass
    return {
        "n_cells": n_cells,
        "n_pass_bonferroni": n_pass,
        "pass_phase1_floor_5": pass_phase1,
        "phase1_floor": threshold_pass,
        "passing_by_horizon": by_horizon,
        "passing_by_sector": by_sector,
        "max_abs_t": float(results["t_stat"].abs().max()),
        "min_p_value": float(results["p_value"].min()),
    }


def save_layer_a(
    results: pd.DataFrame,
    out_dir: Path = Path("data/cache"),
    tag: str = "DRTSCILM_AR1",
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    snap = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    out_path = out_dir / f"layer_a_results_{tag}_{snap}.parquet"
    results.to_parquet(out_path)
    return out_path


__all__ = [
    "ALPHA",
    "K_BONFERRONI",
    "layer_a_summary",
    "run_layer_a",
    "run_layer_a_signed",
    "save_layer_a",
]
