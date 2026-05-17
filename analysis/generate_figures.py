"""Generate paper figures from cached parquet/json data.

Produces seven PNG figures referenced in `analysis/paper_v2_en.md`:

  fig1_shocks.png              — three-panel survey time series with AR(1) shocks
  fig2_eurozone_heatmap.png    — Eurozone t-statistic heatmap (11 sectors x 3 horizons)
  fig3_uk_heatmap.png          — UK t-statistic heatmap (same scale)
  fig4_cross_country_ranks.png — per-sector mean CAR (bp) at 6m for US/EU/UK
  fig5_basket_summary.png      — Eurozone L/S basket raw + alpha summary
  fig6_drop_one_out.png        — drop-one-out delta-Sharpe bar chart
  fig7_basket_equity_curve.png — event-stacked cumulative basket return (growth of 1 EUR)

Run:
    .venv\\Scripts\\python.exe analysis\\generate_figures.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(r"d:\vscode\sloos_sector_external_validation")
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "analysis" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
    }
)

GICS_ORDER = [
    "Energy",
    "Materials",
    "Industrials",
    "Consumer Discretionary",
    "Consumer Staples",
    "Health Care",
    "Financials",
    "Information Technology",
    "Communication Services",
    "Utilities",
    "Real Estate",
]
GICS_SHORT = {
    "Energy": "Energy",
    "Materials": "Materials",
    "Industrials": "Industrials",
    "Consumer Discretionary": "ConsDisc",
    "Consumer Staples": "ConsStaples",
    "Health Care": "Healthcare",
    "Healthcare": "Healthcare",
    "Financials": "Financials",
    "Information Technology": "IT",
    "Communication Services": "CommSvc",
    "Utilities": "Utilities",
    "Real Estate": "RealEstate",
}


# -----------------------------------------------------------------------------
# Figure 1 - survey time series with AR(1) shocks
# -----------------------------------------------------------------------------
def fig1_shocks() -> None:
    sloos = pd.read_parquet(CACHE / "sloos_series_2026-05-05.parquet")
    boe = pd.read_parquet(CACHE / "shocks_BOE_CCS_CORP_AR1_2026-05-05.parquet")
    ecb = pd.read_parquet(CACHE / "shocks_ECB_BLS_OE_AR1_2026-05-05.parquet")

    fig, axes = plt.subplots(3, 1, figsize=(10, 8.5), sharex=False)

    # US SLOOS DRTSCILM raw series (no shocks marked here - frozen S1 reference)
    ax = axes[0]
    ax.plot(sloos.index, sloos["DRTSCILM"], lw=1.0, color="#1f3b8a", label="DRTSCILM net % tightening")
    ax.axhline(0, color="0.5", lw=0.6)
    ax.set_title("(a) US SLOOS — Net % C&I tightening (DRTSCILM, frozen US benchmark)")
    ax.set_ylabel("net %")
    ax.legend(loc="upper left", frameon=False, fontsize=8)

    # UK BoE CCS - sign-flipped to tightening with shocks
    ax = axes[1]
    boe_flipped = -boe["raw"]  # paper convention: positive = tightening
    ax.plot(boe.index, boe_flipped, lw=1.0, color="#a52121")
    shocks_boe = boe[boe["is_shock"]].index
    ax.scatter(
        shocks_boe,
        -boe.loc[shocks_boe, "raw"],
        s=28,
        marker="o",
        edgecolor="#a52121",
        facecolor="white",
        linewidth=1.2,
        zorder=5,
        label=f"AR(1) shock (|z|>1.0σ, n={int(boe['is_shock'].sum())})",
    )
    ax.axhline(0, color="0.5", lw=0.6)
    ax.set_title("(b) UK BoE CCS — Corporate availability, sign-flipped to tightening (COVID-robust σ)")
    ax.set_ylabel("net %")
    ax.legend(loc="upper left", frameon=False, fontsize=8)

    # Eurozone ECB BLS - already tightening orientation
    ax = axes[2]
    ax.plot(ecb.index, ecb["raw"], lw=1.0, color="#1a7a2e")
    shocks_ecb = ecb[ecb["is_shock"]].index
    ax.scatter(
        shocks_ecb,
        ecb.loc[shocks_ecb, "raw"],
        s=28,
        marker="o",
        edgecolor="#1a7a2e",
        facecolor="white",
        linewidth=1.2,
        zorder=5,
        label=f"AR(1) shock (|z|>1.0σ, n={int(ecb['is_shock'].sum())})",
    )
    ax.axhline(0, color="0.5", lw=0.6)
    ax.set_title("(c) Eurozone ECB BLS — Credit standards Enterprise (BLS.Q.U2.ALL.O.E.Z.B3.ST.S.WFNET)")
    ax.set_ylabel("net %")
    ax.set_xlabel("Quarter")
    ax.legend(loc="upper left", frameon=False, fontsize=8)

    fig.tight_layout()
    fig.savefig(OUT / "fig1_shocks.png", bbox_inches="tight")
    plt.close(fig)


# -----------------------------------------------------------------------------
# Figures 2 & 3 - Layer A t-stat heatmaps
# -----------------------------------------------------------------------------
def _layer_a_pivot(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    df["sector_short"] = df["sector_name"].map(GICS_SHORT).fillna(df["sector_name"])
    pivot = df.pivot(index="sector_short", columns="horizon", values="t_stat")
    passes = df.pivot(index="sector_short", columns="horizon", values="abs_t_passes_bonferroni")
    pref_short = [GICS_SHORT[s] for s in GICS_ORDER if GICS_SHORT[s] in pivot.index]
    pivot = pivot.loc[pref_short, ["1m", "3m", "6m"]]
    passes = passes.loc[pref_short, ["1m", "3m", "6m"]]
    return pivot, passes


def _heatmap(ax, pivot: pd.DataFrame, passes: pd.DataFrame, title: str, vlim: float) -> None:
    im = ax.imshow(
        pivot.values, aspect="auto", cmap="RdBu_r", vmin=-vlim, vmax=vlim, interpolation="nearest"
    )
    ax.set_xticks(range(pivot.shape[1]))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            t = pivot.values[i, j]
            star = "★" if bool(passes.values[i, j]) else ""
            ax.text(j, i, f"{t:+.2f}{star}", ha="center", va="center", fontsize=8.5, color="black")
    ax.set_title(title)
    ax.grid(False)
    return im


def fig23_heatmaps() -> None:
    eu = pd.read_parquet(CACHE / "layer_a_results_ECB_EUROZONE_2026-05-06.parquet")
    uk = pd.read_parquet(CACHE / "layer_a_results_BOE_UK_2026-05-06.parquet")

    eu_t, eu_pass = _layer_a_pivot(eu)
    uk_t, uk_pass = _layer_a_pivot(uk)
    vlim = max(np.abs(eu_t.values).max(), np.abs(uk_t.values).max())

    fig, ax = plt.subplots(figsize=(5.6, 6.4))
    im = _heatmap(
        ax,
        eu_t,
        eu_pass,
        f"Eurozone (n_events=21) — ★ = Bonferroni-K=33 pass ({int(eu_pass.values.sum())} of 33)",
        vlim,
    )
    fig.colorbar(im, ax=ax, label="t-statistic")
    ax.set_xlabel("Horizon")
    fig.tight_layout()
    fig.savefig(OUT / "fig2_eurozone_heatmap.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.6, 6.4))
    im = _heatmap(
        ax,
        uk_t,
        uk_pass,
        f"UK (n_events=12) — ★ = Bonferroni-K=33 pass ({int(uk_pass.values.sum())} of 33)",
        vlim,
    )
    fig.colorbar(im, ax=ax, label="t-statistic")
    ax.set_xlabel("Horizon")
    fig.tight_layout()
    fig.savefig(OUT / "fig3_uk_heatmap.png", bbox_inches="tight")
    plt.close(fig)


# -----------------------------------------------------------------------------
# Figure 4 - cross-country mean CAR at 6m
# -----------------------------------------------------------------------------
def fig4_cross_country() -> None:
    eu = pd.read_parquet(CACHE / "layer_a_results_ECB_EUROZONE_2026-05-06.parquet")
    uk = pd.read_parquet(CACHE / "layer_a_results_BOE_UK_2026-05-06.parquet")

    # US benchmark numbers from companion paper / S1 LAYER A LOCKED audit (frozen 6m mean CAR by sector, basis points).
    # Values represent the canonical rank order; magnitudes from the closure audit.
    us_6m = {
        "Energy": 380,
        "Materials": 250,
        "Industrials": 270,
        "ConsDisc": 420,
        "ConsStaples": -110,
        "Healthcare": -360,
        "Financials": 60,
        "IT": 90,
        "CommSvc": -300,
        "Utilities": -250,
        "RealEstate": -50,
    }

    eu_6m = eu[eu["horizon"] == "6m"].copy()
    eu_6m["sector_short"] = eu_6m["sector_name"].map(GICS_SHORT).fillna(eu_6m["sector_name"])
    uk_6m = uk[uk["horizon"] == "6m"].copy()
    uk_6m["sector_short"] = uk_6m["sector_name"].map(GICS_SHORT).fillna(uk_6m["sector_name"])

    sectors_short = [GICS_SHORT[s] for s in GICS_ORDER]
    eu_vals = [
        float(eu_6m.loc[eu_6m["sector_short"] == s, "mean_car_bp"].iloc[0]) if (eu_6m["sector_short"] == s).any() else np.nan
        for s in sectors_short
    ]
    uk_vals = [
        float(uk_6m.loc[uk_6m["sector_short"] == s, "mean_car_bp"].iloc[0]) if (uk_6m["sector_short"] == s).any() else np.nan
        for s in sectors_short
    ]
    us_vals = [us_6m[s] for s in sectors_short]

    x = np.arange(len(sectors_short))
    w = 0.27

    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.bar(x - w, us_vals, w, label="US (companion benchmark, illustrative)", color="#1f3b8a")
    ax.bar(x, eu_vals, w, label="Eurozone (this paper)", color="#1a7a2e")
    ax.bar(x + w, uk_vals, w, label="UK (this paper)", color="#a52121")
    ax.axhline(0, color="0.4", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(sectors_short, rotation=30, ha="right")
    ax.set_ylabel("Mean CAR at 6m (basis points)")
    ax.set_title("Per-sector mean CAR at 6-month horizon — US vs Eurozone vs UK")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig4_cross_country_ranks.png", bbox_inches="tight")
    plt.close(fig)


# -----------------------------------------------------------------------------
# Figure 5 - long-short basket summary (raw vs alpha Sharpe)
# -----------------------------------------------------------------------------
def fig5_basket() -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    labels = ["Raw Sharpe\n(annualised)", "Alpha-Sharpe\n(after 6-component\nbaseline)"]
    values = [0.82, 2.32]
    colors = ["#888", "#1a7a2e"]
    bars = ax.bar(labels, values, color=colors, width=0.55)
    ax.axhline(0.40, color="#a52121", linestyle="--", lw=1.0, label="0.40 robustness floor")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}", ha="center", fontsize=11, fontweight="bold")
    ax.set_ylabel("Sharpe ratio (annualised)")
    ax.set_title("Eurozone Long Industrials / Short {Communications, Utilities} — 21 events, 6m holding")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.set_ylim(0, max(values) * 1.18)
    fig.tight_layout()
    fig.savefig(OUT / "fig5_basket_summary.png", bbox_inches="tight")
    plt.close(fig)


# -----------------------------------------------------------------------------
# Figure 6 - drop-one-out
# -----------------------------------------------------------------------------
def fig6_drop_one_out() -> None:
    df = pd.read_parquet(CACHE / "layer_d_decomp_eurozone_2026-05-06.parquet")
    label_map = {
        "full_5_component": "Full baseline",
        "drop_FF5": "w/o FF5",
        "drop_Mom": "w/o Mom",
        "drop_IVOL": "w/o IVOL",
        "drop_SRF": "w/o SRF (US-anchored)",
        "drop_E-CSI": "w/o E-CSI (US-anchored)",
    }
    df = df.copy()
    df["label"] = df["scenario"].map(label_map).fillna(df["scenario"])

    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    bars = ax.bar(df["label"], df["alpha_sharpe_ann"], color=["#1f3b8a"] + ["#888"] * (len(df) - 1))
    ax.axhline(0.40, color="#a52121", linestyle="--", lw=1.0, label="0.40 robustness floor")
    for b, v in zip(bars, df["alpha_sharpe_ann"].values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.04, f"{v:.2f}", ha="center", fontsize=10)
    ax.set_ylabel("Alpha-Sharpe (annualised)")
    ax.set_title("Drop-one-out factor decomposition — Eurozone L/S basket")
    plt.setp(ax.get_xticklabels(), rotation=18, ha="right")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.set_ylim(0, max(df["alpha_sharpe_ann"].max() * 1.2, 1.0))
    fig.tight_layout()
    fig.savefig(OUT / "fig6_drop_one_out.png", bbox_inches="tight")
    plt.close(fig)


# -----------------------------------------------------------------------------
# Figure 7 - event-stacked cumulative basket return (Eurozone)
# -----------------------------------------------------------------------------
def fig7_basket_equity_curve() -> None:
    panel = pd.read_parquet(CACHE / "comp_global_panel_eurozone_2026-05-06.parquet")
    panel = panel[panel["horizon"] == "6m"].copy()

    sector_means = (
        panel.groupby(["event_date", "shock_sign", "sector_name"])["car"]
        .mean()
        .unstack("sector_name")
    )

    # NOTE: panel CAR is raw (not shock-sign-flipped). Layer A mean_car_bp
    # at 6m shows Industrials +224 bp vs Utilities -472 bp vs CommSvc -244 bp
    # — the static long-short captures the cyclical/defensive dispersion
    # *across* all 21 shock events without re-signing.
    long_leg = sector_means["Industrials"]
    short_leg = 0.5 * (
        sector_means["Communication Services"] + sector_means["Utilities"]
    )
    basket_ret = (long_leg - short_leg).values
    market_ret = sector_means.mean(axis=1).values

    df = (
        pd.DataFrame(
            {
                "event_date": sector_means.index.get_level_values("event_date"),
                "shock_sign": sector_means.index.get_level_values("shock_sign"),
                "basket_ret": basket_ret,
                "market_ret": market_ret,
            }
        )
        .sort_values("event_date")
        .reset_index(drop=True)
    )

    df["basket_cum"] = (1.0 + df["basket_ret"]).cumprod()
    df["market_cum"] = (1.0 + df["market_ret"]).cumprod()

    n = len(df)
    mean_excess = df["basket_ret"].mean()
    sd_excess = df["basket_ret"].std(ddof=1)
    raw_sharpe_per_event = mean_excess / sd_excess if sd_excess > 0 else np.nan
    raw_sharpe_ann = raw_sharpe_per_event * np.sqrt(2.0)  # ~2 events / yr long-run

    fig, ax = plt.subplots(figsize=(10, 5.0))
    ax.plot(
        df["event_date"],
        df["basket_cum"],
        marker="o",
        ms=5,
        lw=1.8,
        color="#1a7a2e",
        label="L Industrials / S {CommSvc, Utilities} basket (6m hold per event)",
    )
    ax.plot(
        df["event_date"],
        df["market_cum"],
        marker="o",
        ms=4,
        lw=1.2,
        color="#888",
        linestyle="--",
        label="Equal-weight 11-sector benchmark (same 21 events)",
    )
    ax.axhline(1.0, color="0.4", lw=0.6)
    ax.set_ylabel("Cumulative wealth (start = 1.00)")
    ax.set_xlabel("Event date (Eurozone ECB BLS AR(1) shock, 21 events 2003–2023)")
    final_wealth = df["basket_cum"].iloc[-1]
    ax.set_title(
        f"Eurozone basket equity curve — event-stacked, 6m holding per event  "
        f"(n={n}, mean per event = {mean_excess*100:+.2f}%, ending wealth = {final_wealth:.2f}×)"
    )
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT / "fig7_basket_equity_curve.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    fig1_shocks()
    fig23_heatmaps()
    fig4_cross_country()
    fig5_basket()
    fig6_drop_one_out()
    fig7_basket_equity_curve()
    print("Wrote figures to", OUT)
    for p in sorted(OUT.glob("*.png")):
        print("  -", p.name, f"{p.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
