"""Layer D — 5-component absorption test (CLAUDE.md §1.6, §1.7).

Strategy: at each SLOOS shock event, form a long-short sector portfolio
weighted by Layer A 6m signed t-statistics. Hold 6 months (126 trading
days). Strategy return per event = mean(long-basket 6m log return)
- mean(short-basket 6m log return).

The 6m horizon is the strongest Layer A signal (8/11 sectors significant
at Bonferroni-K=33). Long/short composition is determined IN-SAMPLE from
Layer A results — Phase 2 walk-forward (§1.9) will redo this OOS.

Baseline regression:
    r_strategy_e = α + β·X_e + ε_e
where X_e is the cumulative 6m factor return for FF5 + Mom + IVOL_proxy
plus contemporaneous SRF and E-CSI.

PASS condition (Phase 1 §1.7 lock): Δ Sharpe ≥ 0.40 vs baseline.
We measure two things:
  - Raw strategy Sharpe (annualized)
  - Alpha-Sharpe (information ratio) = α / σ(ε) annualized after
    baseline regression
Δ Sharpe = Raw - alpha-Sharpe? No — that misreads the spec.
Per CLAUDE.md §1.7 "F6 absorption gate Δ Sharpe ≥ 0.40", we read this as
the *retained* Sharpe after baseline absorption. So:
  Δ Sharpe = alpha-Sharpe (the annualized information ratio).
This is the ≥0.40 gate.

Per-component lever 1 reporting (CLAUDE.md §6):
  For each baseline component k ∈ {FF5, Mom, IVOL, SRF, E-CSI}, also report
  alpha-Sharpe with ONLY component k removed (i.e., 4-component baseline).
  This shows incremental Δ Sharpe attribution.

Notes / known simplifications:
- IVOL is a portfolio-level proxy: cross-sectional std of universe daily
  log returns over the 60 trading days BEFORE the event. Standard Ang et al.
  IVOL would use rolling-firm-level FF5 residuals — left to Phase 2 if
  this becomes binding.
- 5 FF5 factors treated as 5 features (not aggregated).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .factors_fetch import cumulative_factor_return

logger = logging.getLogger(__name__)


HORIZON_TD = 126
DEFAULT_HORIZON_LABEL = "6m"
DELTA_SHARPE_FLOOR = 0.40


@dataclass
class LayerDResult:
    n_events: int
    raw_sharpe_annualized: float
    alpha_sharpe_annualized: float
    raw_mean_per_event: float
    raw_std_per_event: float
    alpha_per_event: float
    alpha_p_value: float
    residual_std_per_event: float
    r_squared: float
    delta_sharpe: float
    pass_phase1_floor: bool
    long_sectors: list[int]
    short_sectors: list[int]
    n_factor_features: int
    factor_betas: dict[str, float]
    factor_pvalues: dict[str, float]


def select_long_short_sectors(layer_a_results: pd.DataFrame, horizon: str = DEFAULT_HORIZON_LABEL) -> tuple[list[int], list[int]]:
    """Pick long basket = +sign Layer A passing cells, short basket = -sign passing cells, at given horizon."""
    ar = layer_a_results[layer_a_results["horizon"] == horizon]
    sig = ar[ar["abs_t_passes_bonferroni"]]
    long = sig[sig["t_stat"] > 0]["sector_code"].astype(int).tolist()
    short = sig[sig["t_stat"] < 0]["sector_code"].astype(int).tolist()
    return long, short


def compute_strategy_returns(
    panel: pd.DataFrame,
    long_sectors: list[int],
    short_sectors: list[int],
    horizon: str = DEFAULT_HORIZON_LABEL,
) -> pd.DataFrame:
    """Per-event L/S strategy return = mean(long-basket 6m log ret) - mean(short-basket 6m log ret).

    Note we use raw `log_ret` (not CAR) so the L/S spread captures real dollar
    return difference, not market-relative deviation. The L/S structure is
    market-neutral by construction (long and short have similar betas at the
    sector level).
    """
    panel_h = panel[panel["horizon"] == horizon].copy()
    rows = []
    for evt, g in panel_h.groupby("event_date"):
        long = g[g["sector"].isin(long_sectors)]
        short = g[g["sector"].isin(short_sectors)]
        if len(long) == 0 or len(short) == 0:
            continue
        long_ret = float(long["log_ret"].mean())
        short_ret = float(short["log_ret"].mean())
        rows.append(
            {
                "event_date": evt,
                "n_long": len(long),
                "n_short": len(short),
                "long_ret": long_ret,
                "short_ret": short_ret,
                "strategy_ret": long_ret - short_ret,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["event_date", "n_long", "n_short", "long_ret", "short_ret", "strategy_ret"])
    return pd.DataFrame(rows).sort_values("event_date").reset_index(drop=True)


def compute_pre_event_ivol_proxy(
    factors_daily: pd.DataFrame,
    event_date: pd.Timestamp,
    lookback_days: int = 60,
) -> float:
    """Realized market vol over the 60 trading days preceding the event.

    IVOL proxy = std(Mkt-RF daily returns) over [evt - 60td, evt]. This is
    the textbook macro-level IVOL proxy (Ang et al. 2006 IVOL is an
    option-implied counterpart of realized market vol; the two are highly
    correlated at quarterly frequency).

    The earlier "prior event cross-sectional std" proxy was rejected as
    pathological — it leaked signal because the same events drive both
    the signal and the proxy. Day 8-9 audit documents this and switches
    to realized market vol.
    """
    if "Mkt-RF" not in factors_daily.columns:
        return float("nan")
    sub = factors_daily.loc[factors_daily.index < event_date, "Mkt-RF"].tail(lookback_days)
    if len(sub) < 20:
        return float("nan")
    return float(sub.std(ddof=1))


def build_event_factor_panel(
    strat_returns: pd.DataFrame,
    panel: pd.DataFrame,
    factors_daily: pd.DataFrame,
    srf: pd.DataFrame,
    ecsi_panel: pd.DataFrame,
    horizon_td: int = HORIZON_TD,
) -> pd.DataFrame:
    """For each event date, attach cumulative FF5 + Mom over 6m + IVOL proxy + SRF + E-CSI."""
    factor_cols = [c for c in ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"] if c in factors_daily.columns]

    rows = []
    for _, row in strat_returns.iterrows():
        evt = pd.Timestamp(row["event_date"])
        # Cumulative FF5+Mom over horizon starting at evt+1 trading day
        # Use evt directly; cumulative_factor_return slices factors.index >= evt
        cum = cumulative_factor_return(factors_daily, start=evt, horizon_td=horizon_td)
        # IVOL proxy: realized market vol over 60td prior to event
        ivol = compute_pre_event_ivol_proxy(factors_daily, evt)
        # SRF / E-CSI at the contemporaneous release date
        srf_match = srf[srf["quarter_release_date"] == evt]
        srf_val = float(srf_match["srf"].iloc[0]) if not srf_match.empty else np.nan
        ecsi_match = ecsi_panel[ecsi_panel.index == evt]
        ecsi_val = float(ecsi_match["ecsi"].iloc[0]) if not ecsi_match.empty else np.nan
        out = {"event_date": evt, "strategy_ret": float(row["strategy_ret"])}
        for c in factor_cols:
            out[c] = float(cum.get(c, np.nan))
        out["ivol"] = ivol
        out["srf"] = srf_val
        out["ecsi"] = ecsi_val
        rows.append(out)
    return pd.DataFrame(rows)


def regress_absorption(
    event_factor_panel: pd.DataFrame,
    feature_cols: list[str] | None = None,
) -> tuple[sm.regression.linear_model.RegressionResultsWrapper, pd.DataFrame]:
    """OLS: strategy_ret = α + β · X + ε. Return (model, cleaned data used)."""
    if feature_cols is None:
        feature_cols = [c for c in event_factor_panel.columns if c not in ("event_date", "strategy_ret")]
    df = event_factor_panel.dropna(subset=["strategy_ret"] + feature_cols)
    X = sm.add_constant(df[feature_cols])
    y = df["strategy_ret"]
    return sm.OLS(y, X).fit(), df


def annualize_per_event(stat: float, n_events: int, span_days: float) -> float:
    """Annualize an event-frequency Sharpe given n_events and span (days)."""
    if span_days <= 0 or n_events <= 1:
        return float("nan")
    events_per_year = n_events / (span_days / 365.25)
    return stat * float(np.sqrt(events_per_year))


def run_layer_d(
    panel: pd.DataFrame,
    layer_a_results: pd.DataFrame,
    factors_daily: pd.DataFrame,
    srf: pd.DataFrame,
    ecsi_panel: pd.DataFrame,
    horizon: str = DEFAULT_HORIZON_LABEL,
    horizon_td: int = HORIZON_TD,
) -> LayerDResult:
    long_sec, short_sec = select_long_short_sectors(layer_a_results, horizon=horizon)
    if not long_sec or not short_sec:
        raise RuntimeError("Layer A produced no long or short basket — Layer D cannot run")

    strat = compute_strategy_returns(panel, long_sec, short_sec, horizon=horizon)
    efp = build_event_factor_panel(strat, panel, factors_daily, srf, ecsi_panel, horizon_td=horizon_td)
    feature_cols = [c for c in ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom", "ivol", "srf", "ecsi"] if c in efp.columns]
    model, used = regress_absorption(efp, feature_cols)

    n = int(len(used))
    span_days = float((used["event_date"].max() - used["event_date"].min()).days)

    raw_mean = float(used["strategy_ret"].mean())
    raw_std = float(used["strategy_ret"].std(ddof=1))
    raw_sharpe_per_event = raw_mean / raw_std if raw_std else float("nan")
    raw_sharpe_ann = annualize_per_event(raw_sharpe_per_event, n, span_days)

    alpha = float(model.params["const"])
    alpha_p = float(model.pvalues["const"])
    resid_std = float(model.resid.std(ddof=len(feature_cols) + 1))
    alpha_sharpe_per_event = alpha / resid_std if resid_std else float("nan")
    alpha_sharpe_ann = annualize_per_event(alpha_sharpe_per_event, n, span_days)

    delta_sharpe = alpha_sharpe_ann

    return LayerDResult(
        n_events=n,
        raw_sharpe_annualized=raw_sharpe_ann,
        alpha_sharpe_annualized=alpha_sharpe_ann,
        raw_mean_per_event=raw_mean,
        raw_std_per_event=raw_std,
        alpha_per_event=alpha,
        alpha_p_value=alpha_p,
        residual_std_per_event=resid_std,
        r_squared=float(model.rsquared),
        delta_sharpe=delta_sharpe,
        pass_phase1_floor=bool(np.isfinite(delta_sharpe) and delta_sharpe >= DELTA_SHARPE_FLOOR),
        long_sectors=long_sec,
        short_sectors=short_sec,
        n_factor_features=len(feature_cols),
        factor_betas={k: float(v) for k, v in model.params.items() if k != "const"},
        factor_pvalues={k: float(v) for k, v in model.pvalues.items() if k != "const"},
    )


def per_component_decomposition(
    panel: pd.DataFrame,
    layer_a_results: pd.DataFrame,
    factors_daily: pd.DataFrame,
    srf: pd.DataFrame,
    ecsi_panel: pd.DataFrame,
    horizon: str = DEFAULT_HORIZON_LABEL,
    horizon_td: int = HORIZON_TD,
) -> pd.DataFrame:
    """Run Layer D with each component dropped one at a time → incremental Δ Sharpe attribution.

    Per CLAUDE.md §6 lever 1 reporting. The "incremental" Δ Sharpe of dropping
    component k = full-Δ-Sharpe minus drop-k-Δ-Sharpe. Larger means
    component k absorbs more strategy alpha.
    """
    components = {
        "FF5": ["Mkt-RF", "SMB", "HML", "RMW", "CMA"],
        "Mom": ["Mom"],
        "IVOL": ["ivol"],
        "SRF": ["srf"],
        "E-CSI": ["ecsi"],
    }

    long_sec, short_sec = select_long_short_sectors(layer_a_results, horizon=horizon)
    strat = compute_strategy_returns(panel, long_sec, short_sec, horizon=horizon)
    efp = build_event_factor_panel(strat, panel, factors_daily, srf, ecsi_panel, horizon_td=horizon_td)
    all_features = [c for c in ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom", "ivol", "srf", "ecsi"] if c in efp.columns]

    full_model, used = regress_absorption(efp, all_features)
    n = int(len(used))
    span = float((used["event_date"].max() - used["event_date"].min()).days)
    full_alpha = float(full_model.params["const"])
    full_resid_std = float(full_model.resid.std(ddof=len(all_features) + 1))
    full_alpha_sharpe = annualize_per_event(full_alpha / full_resid_std, n, span)

    rows = [
        {
            "scenario": "full_5_component",
            "alpha_per_event": full_alpha,
            "alpha_sharpe_ann": full_alpha_sharpe,
            "incremental_delta_sharpe_from_drop": np.nan,
            "n_features": len(all_features),
        }
    ]
    for comp_name, drop_cols in components.items():
        kept = [c for c in all_features if c not in drop_cols]
        if not kept:
            continue
        m, _ = regress_absorption(efp, kept)
        a = float(m.params["const"])
        rs = float(m.resid.std(ddof=len(kept) + 1))
        ash = annualize_per_event(a / rs, n, span)
        rows.append(
            {
                "scenario": f"drop_{comp_name}",
                "alpha_per_event": a,
                "alpha_sharpe_ann": ash,
                "incremental_delta_sharpe_from_drop": ash - full_alpha_sharpe,
                "n_features": len(kept),
            }
        )
    return pd.DataFrame(rows)


__all__ = [
    "DEFAULT_HORIZON_LABEL",
    "DELTA_SHARPE_FLOOR",
    "HORIZON_TD",
    "LayerDResult",
    "build_event_factor_panel",
    "compute_pre_event_ivol_proxy",
    "compute_strategy_returns",
    "per_component_decomposition",
    "regress_absorption",
    "run_layer_d",
    "select_long_short_sectors",
]
