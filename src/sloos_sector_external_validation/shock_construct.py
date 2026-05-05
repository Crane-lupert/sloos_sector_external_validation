"""SLOOS shock event construction (Phase 0 §1.1 lock — amended 2026-05-05 Day 2).

LOCK §1.1 (amended): primary DRTSCILM full-sample AR(1) fit → residual ε_t →
z_innov = ε_t / σ(ε). Shock event = quarter where |z_innov| > 1.0σ. Sign:
+1 (tightening) if ε_t > 0, -1 (easing) if ε_t < 0. No first-quarter cluster
filter — AR(1)-residual is approximately white noise so consecutive shocks
are by construction rare.

Why AR(1) innovation (vs original level z-score with rolling 40q σ):
- DRTSCILM has 3 regime spikes (early-2000s / GFC / COVID+post-COVID) and is
  highly persistent (ρ ≈ 0.86 in AR(1) fit). Level z-score under-counts
  events because consecutive elevated quarters are correlated.
- AR(1) residual differences out the persistence. The remaining innovation
  is the "news" content of each SLOOS release.
- This matches Bidder-Krane-Park 2026.02 E-CSI methodology and Bassett 2014
  SLOOS-shock identification.

Why 1.0σ (not 1.5σ): AR-innovation standard threshold per Bassett 2014 /
Bidder-Krane-Park 2026.02. Original 1.5σ in lock spec was paired with the
level-z formulation, a different statistical universe. At 1.0σ on AR(1)
residuals, ~17% of post-fit quarters fire as shocks (vs ~13% expected under
N(0,1)) — reasonable shock frequency.

SVB cohort sub-sample (CLAUDE.md §6 lever 3, §7 amended floor ≥1) =
events with release date >= 2023-07-01.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

Z_THRESHOLD = 1.0
SVB_COHORT_START = pd.Timestamp("2023-07-01")
AR_ORDER = 1


def fit_ar_residual(
    series: pd.Series,
    order: int = AR_ORDER,
) -> pd.DataFrame:
    """Fit AR(`order`) on `series`, return panel with raw / fitted / residual / z_innov.

    Uses statsmodels AutoReg with `trend='c'` (constant). For order=1 we estimate:
        DRTSCILM_t = α + ρ * DRTSCILM_{t-1} + ε_t
    Then z_innov_t = ε_t / σ(ε_residual_sample).

    Index is preserved from input. The first `order` rows have NaN residual
    (AR pre-history), which is correct.
    """
    s = series.dropna().astype(float).copy()
    if len(s) < 2 * order + 10:
        raise ValueError(f"series too short for AR({order}): {len(s)} obs")

    model = sm.tsa.AutoReg(s, lags=order, trend="c", old_names=False)
    res = model.fit()
    fitted = res.fittedvalues  # starts at index `order`
    resid = res.resid  # same index as fitted
    sigma_eps = float(resid.std(ddof=1))

    out = pd.DataFrame(
        {
            "raw": s,
            "fitted": np.nan,
            "residual": np.nan,
            "z_innov": np.nan,
        }
    )
    out.loc[fitted.index, "fitted"] = fitted.values
    out.loc[resid.index, "residual"] = resid.values
    out["z_innov"] = out["residual"] / sigma_eps
    out.attrs["ar_order"] = order
    out.attrs["ar_alpha"] = float(res.params.iloc[0])
    out.attrs["ar_rho"] = float(res.params.iloc[1]) if order >= 1 else None
    out.attrs["sigma_eps"] = sigma_eps
    return out


def flag_events(
    z_panel: pd.DataFrame,
    threshold: float = Z_THRESHOLD,
) -> pd.DataFrame:
    """Add abs_z_above / shock_sign / is_shock / is_event_start columns.

    Under AR(1)-innovation lock, every |z_innov| > threshold quarter is
    independently a shock event — no cluster-deduplication.
    """
    df = z_panel.copy()
    abs_z = df["z_innov"].abs()
    above = (abs_z > threshold).fillna(False)
    df["abs_z_above"] = above.astype("Int64")

    z_filled = df["z_innov"].fillna(0.0).to_numpy()
    sign = np.zeros(len(df), dtype=int)
    sign[(z_filled > 0) & above.to_numpy()] = 1
    sign[(z_filled < 0) & above.to_numpy()] = -1
    df["shock_sign"] = sign
    df["is_shock"] = above
    df["is_event_start"] = above  # alias for downstream API compatibility
    return df


def construct_shocks(
    sloos_panel: pd.DataFrame,
    primary_series: str = "DRTSCILM",
    order: int = AR_ORDER,
    threshold: float = Z_THRESHOLD,
) -> pd.DataFrame:
    """End-to-end: panel -> AR(order)-residual z_innov -> events.

    Returns DataFrame indexed by quarter_release_date with columns:
    raw, fitted, residual, z_innov, abs_z_above, shock_sign, is_shock,
    is_event_start, is_svb_cohort.
    """
    if primary_series not in sloos_panel.columns:
        raise KeyError(f"Primary series {primary_series!r} not in panel columns {list(sloos_panel.columns)}")
    z_panel = fit_ar_residual(sloos_panel[primary_series], order=order)
    out = flag_events(z_panel, threshold=threshold)
    out["is_svb_cohort"] = out.index >= SVB_COHORT_START
    out.attrs.update(z_panel.attrs)
    return out


def event_dates(shocks: pd.DataFrame) -> pd.DatetimeIndex:
    """Just the timestamps of shock events."""
    return shocks.index[shocks["is_event_start"].fillna(False)]


def event_summary(shocks: pd.DataFrame) -> dict[str, object]:
    """Counts by sign, decade, and SVB cohort split."""
    e = shocks[shocks["is_event_start"].fillna(False)].copy()
    n_total = int(len(e))
    n_tight = int((e["shock_sign"] == 1).sum())
    n_ease = int((e["shock_sign"] == -1).sum())
    e["decade"] = (e.index.year // 10) * 10
    by_decade = {int(k): int(v) for k, v in e.groupby("decade").size().to_dict().items()}
    n_svb = int(e["is_svb_cohort"].sum())
    return {
        "n_events_total": n_total,
        "n_events_tightening": n_tight,
        "n_events_easing": n_ease,
        "events_by_decade": by_decade,
        "n_svb_cohort": n_svb,
        "n_pre_svb": n_total - n_svb,
        "first_event": str(e.index.min().date()) if n_total else None,
        "last_event": str(e.index.max().date()) if n_total else None,
        "ar_alpha": shocks.attrs.get("ar_alpha"),
        "ar_rho": shocks.attrs.get("ar_rho"),
        "sigma_eps": shocks.attrs.get("sigma_eps"),
    }


def save_shocks(shocks: pd.DataFrame, out_dir: Path = Path("data/cache"), tag: str = "DRTSCILM") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    snap = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    out_path = out_dir / f"shocks_{tag}_AR{AR_ORDER}_{snap}.parquet"
    shocks.to_parquet(out_path)
    return out_path


__all__ = [
    "AR_ORDER",
    "SVB_COHORT_START",
    "Z_THRESHOLD",
    "construct_shocks",
    "event_dates",
    "event_summary",
    "fit_ar_residual",
    "flag_events",
    "save_shocks",
]
