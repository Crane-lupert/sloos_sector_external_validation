"""E-CSI proxy — Bidder-Krane-Park 2026.02 reconstruction.

Layer D 5-component baseline component #5 (CLAUDE.md §1.6).

Methodology (Bidder, Krane, Park, "The Expected Composite Senior Loan
Officer Index," Fed working paper Feb 2026):
- E-CSI_t is constructed as the "expected SLOOS tightening" conditional on
  the current macro state.
- Their formal construction uses banks' loan-level data we don't have access
  to. We approximate via a linear-regression proxy:
      DRTSCILM_t = α + β · X_{t-1} + ε_t
  where X is a vector of macro state variables (unemployment, yield curve
  slope, GDP growth, VIX).
  E-CSI_t = fitted value α̂ + β̂ · X_{t-1} (the predictable component).

By construction the proxy is orthogonal to the SLOOS shock (which IS the
residual ε in our amended Phase 0 §1.1 lock — see audits/2026-05-05-
S1-day2-eod.md). This satisfies the F6-distinctness requirement: E-CSI as
a baseline component captures the part of SLOOS that is foreseeable from
macro state, while our shock captures the residual surprise.

FRED inputs:
- UNRATE   unemployment rate (monthly, quarterly = Q-end)
- T10Y3M   10y - 3mo Treasury spread (daily, quarterly mean)
- GDPC1    real GDP (quarterly), log QoQ growth
- VIXCLS   VIX close (daily, quarterly mean) — series exists from 1990 onward
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()
logger = logging.getLogger(__name__)


MACRO_SERIES: dict[str, str] = {
    "unrate": "UNRATE",
    "t10y3m": "T10Y3M",
    "gdpc1": "GDPC1",
    "vix": "VIXCLS",
}


def _get_fred() -> Fred:
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("FRED_API_KEY not set")
    return Fred(api_key=api_key)


def _fetch_series(fred: Fred, series_id: str) -> pd.Series:
    s = fred.get_series(series_id)
    s.index = pd.to_datetime(s.index)
    return s


def fetch_macro_panel(fred: Fred | None = None) -> pd.DataFrame:
    """Fetch raw FRED series and align to SLOOS-release quarterly schedule.

    Returns a DataFrame indexed by quarter_release_date with columns:
    unrate, t10y3m, gdpc1_log_growth, vix.

    Quarterly alignment: each macro variable's value AT THE END OF the
    quarter PRIOR to release is paired with the SLOOS release date.
    Example: 2023-04-01 release uses macro state as of 2023-03-31
    (= end of Q1 2023, the quarter the survey covers).
    """
    fred = fred or _get_fred()

    raw = {}
    for label, sid in MACRO_SERIES.items():
        try:
            raw[label] = _fetch_series(fred, sid)
        except Exception as exc:
            logger.warning("FRED %s fetch failed: %s", sid, exc)
            raw[label] = pd.Series(dtype=float)

    # Build quarterly index from 1990-Q1 to today
    today_naive = pd.Timestamp.utcnow().tz_localize(None).normalize()
    qs = pd.date_range("1990-04-01", today_naive, freq="QS-OCT")
    panel = pd.DataFrame(index=qs)
    panel.index.name = "quarter_release_date"

    # UNRATE monthly → take Q-end value (March, June, Sept, Dec) = month before release
    if not raw["unrate"].empty:
        unrate_m = raw["unrate"].resample("ME").last()
        # release = April 1 ⇒ macro = March 31 (= the previous month-end)
        unrate_q = unrate_m.reindex(qs - pd.offsets.MonthEnd(1), method="nearest")
        unrate_q.index = qs
        panel["unrate"] = unrate_q

    # T10Y3M daily → quarterly mean of preceding quarter
    if not raw["t10y3m"].empty:
        ser = raw["t10y3m"].copy()
        ser_q = ser.resample("QS-OCT").mean()
        panel["t10y3m"] = ser_q.reindex(qs)

    # GDPC1 quarterly → log QoQ growth, lagged by one quarter (so release sees prior-Q growth)
    if not raw["gdpc1"].empty:
        gdp = raw["gdpc1"].copy()
        gdp.index = pd.to_datetime(gdp.index)
        gdp_qs = gdp.resample("QS-OCT").mean()
        gdp_log_growth = np.log(gdp_qs / gdp_qs.shift(1))
        panel["gdpc1_log_growth"] = gdp_log_growth.reindex(qs)

    # VIX daily → quarterly mean
    if not raw["vix"].empty:
        vix = raw["vix"].copy()
        vix_q = vix.resample("QS-OCT").mean()
        panel["vix"] = vix_q.reindex(qs)

    return panel


def fit_ecsi_proxy(
    drtscilm: pd.Series,
    macro_panel: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, dict[str, float]]:
    """Fit DRTSCILM_t = α + β · X_{t-1} + ε. Return (E-CSI fitted, residual, model_stats).

    Lag X by 1 quarter (X_{t-1}) so E-CSI is conditioning on the macro state
    available BEFORE the SLOOS release. This is a predictive regression in
    the spirit of BKP 2026.
    """
    # Align on quarter_release_date
    df = pd.DataFrame({"y": drtscilm}).join(macro_panel)
    # Lag macro by 1 quarter (use prior-quarter macro to predict current SLOOS)
    for col in macro_panel.columns:
        df[col + "_lag1"] = df[col].shift(1)
    feature_cols = [col + "_lag1" for col in macro_panel.columns]
    df = df.dropna(subset=["y"] + feature_cols)
    if len(df) < 30:
        raise ValueError(f"too few aligned observations to fit E-CSI proxy: {len(df)}")

    X = sm.add_constant(df[feature_cols])
    y = df["y"]
    res = sm.OLS(y, X).fit()
    fitted = res.fittedvalues
    fitted.name = "ecsi"
    resid = res.resid
    resid.name = "ecsi_residual"

    stats = {
        "n_obs": int(res.nobs),
        "r_squared": float(res.rsquared),
        "adj_r_squared": float(res.rsquared_adj),
        "f_pvalue": float(res.f_pvalue),
        **{name: float(c) for name, c in res.params.items()},
        **{name + "_pvalue": float(p) for name, p in res.pvalues.items()},
    }
    return fitted, resid, stats


def build_ecsi(
    sloos_panel: pd.DataFrame,
    primary_series: str = "DRTSCILM",
    out_dir: Path = Path("data/cache"),
    save: bool = True,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """End-to-end E-CSI proxy: fetch macro, fit OLS, return panel of (E-CSI, residual)."""
    macro = fetch_macro_panel()
    drt = sloos_panel[primary_series]
    drt.index = pd.to_datetime(drt.index)
    fitted, resid, stats = fit_ecsi_proxy(drt, macro)
    out = pd.DataFrame({"ecsi": fitted, "ecsi_residual": resid}).join(macro)
    out.index.name = "quarter_release_date"
    if save:
        out_dir.mkdir(parents=True, exist_ok=True)
        snap = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
        out_path = out_dir / f"ecsi_{snap}.parquet"
        out.to_parquet(out_path)
    return out, stats


__all__ = [
    "MACRO_SERIES",
    "build_ecsi",
    "fetch_macro_panel",
    "fit_ecsi_proxy",
]
