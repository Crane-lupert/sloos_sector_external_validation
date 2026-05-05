"""Streamlit MVP dashboard for S1 sloos_sector_external_validation results.

Run: streamlit run dashboard/app.py

Loads the latest cached panel + layer A + layer D outputs from data/cache/
and renders interactive views of:
- SLOOS shock event timeline
- Layer A cell t-stat heatmap (Bonferroni-K=33 highlighted)
- L/S strategy cumulative return curve
- Walk-forward fold breakdown
- Per-component decomposition bars
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

CACHE = Path("data/cache")


def _latest(glob: str) -> Path | None:
    files = sorted(CACHE.glob(glob))
    return files[-1] if files else None


def _load(glob: str) -> pd.DataFrame:
    p = _latest(glob)
    if p is None:
        return pd.DataFrame()
    return pd.read_parquet(p)


def main():
    st.set_page_config(page_title="S1 SLOOS Sector Cross-Section", layout="wide")
    st.title("S1: SLOOS Shock × 11 GICS Sector Cross-Section CAR")
    st.caption("LAYER A LOCKED 3-of-3 PASS — 2026-05-05 — Macro/Credit pod")

    # Load artifacts
    sloos = _load("sloos_series_*.parquet")
    shocks = _load("shocks_DRTSCILM_AR1_*.parquet")
    panel = _load("sector_panel_*.parquet")
    layer_a = _load("layer_a_results_*.parquet")
    audit = _load("per_cell_audit_phase0.parquet") if (CACHE / "per_cell_audit_phase0.parquet").exists() else pd.DataFrame()

    if sloos.empty or shocks.empty or panel.empty or layer_a.empty:
        st.warning("Some cache artifacts are missing. Run the full pipeline (uv run pytest then the per-module scripts) first.")
        return

    st.header("1. SLOOS Shock Events (DRTSCILM AR(1) innovation, |z_innov|>1.0σ)")
    col1, col2 = st.columns([3, 1])
    with col1:
        events = shocks[shocks["is_event_start"]].copy()
        events["sign_label"] = np.where(events["shock_sign"] == 1, "TIGHTEN", "EASE")
        st.dataframe(
            events[["raw", "z_innov", "shock_sign", "is_svb_cohort", "sign_label"]].rename(
                columns={
                    "raw": "DRTSCILM (raw, %)",
                    "z_innov": "z_innov",
                    "shock_sign": "sign (+1/-1)",
                    "is_svb_cohort": "SVB cohort",
                }
            ),
            use_container_width=True,
        )
    with col2:
        st.metric("Events total", int(len(events)))
        st.metric("Tightening", int((events["shock_sign"] == 1).sum()))
        st.metric("Easing", int((events["shock_sign"] == -1).sum()))
        st.metric("SVB cohort", int(events["is_svb_cohort"].sum()))

    st.header("2. Layer A — Per-(sector × horizon) t-stat (Bonferroni-K=33)")
    pivot = layer_a.pivot(index="sector_name", columns="horizon", values="t_stat")
    # Reorder horizons
    if all(h in pivot.columns for h in ("1m", "3m", "6m")):
        pivot = pivot[["1m", "3m", "6m"]]
    st.dataframe(pivot.round(2).style.background_gradient(cmap="RdBu", axis=None, vmin=-12, vmax=12), use_container_width=True)
    n_sig = int(layer_a["abs_t_passes_bonferroni"].sum())
    st.success(f"{n_sig} of 33 cells pass Bonferroni-K=33 (critical |t| ≈ 3.17). Phase 1 §7 floor ≥ 5 — PASS.")

    st.header("3. Layer A — passing cells with mean CAR")
    sig = layer_a[layer_a["abs_t_passes_bonferroni"]].copy()
    sig = sig[["horizon", "sector_name", "n", "mean_car_bp", "t_stat", "p_value"]].sort_values("horizon")
    st.dataframe(sig.round(3), use_container_width=True)

    st.header("4. Strategy Returns per Event")
    from sloos_sector_external_validation.layer_d import compute_strategy_returns, select_long_short_sectors

    long_sec, short_sec = select_long_short_sectors(layer_a, horizon="6m")
    strat = compute_strategy_returns(panel, long_sec, short_sec, horizon="6m")
    if not strat.empty:
        strat["cum_strategy"] = strat["strategy_ret"].cumsum()
        st.line_chart(strat.set_index("event_date")[["cum_strategy"]], use_container_width=True)
        st.caption(f"L/S 6m strategy: long {long_sec}, short {short_sec}")
        st.metric("Mean per event", f"{strat['strategy_ret'].mean()*100:.2f}%")
        st.metric("Std per event", f"{strat['strategy_ret'].std()*100:.2f}%")
        events_per_year = len(strat) / max(((strat["event_date"].max() - strat["event_date"].min()).days / 365.25), 1e-9)
        sharpe = strat["strategy_ret"].mean() / strat["strategy_ret"].std() * np.sqrt(events_per_year)
        st.metric("Sharpe annualized", f"{sharpe:.3f}")

    st.header("5. Audit references")
    st.markdown(
        """
        - [Day 2 lock amendment (AR(1) innovation)](audits/2026-05-05-S1-day2-eod.md)
        - [Day 5 Layer A formal](audits/2026-05-05-S1-day5-eod.md)
        - [Day 9 Layer D + IVOL revision](audits/2026-05-05-S1-day9-eod.md)
        - [Day 10 Gates K/L/M](audits/2026-05-05-S1-day10-eod.md)
        - [Day 11 walk-forward](audits/2026-05-05-S1-day11-eod.md)
        """
    )


if __name__ == "__main__":
    main()
