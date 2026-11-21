"""Figures for the revised SLOOS paper (v3). Static PNGs for a PDF; the plotted values are in tables/series_*.csv.

Palette: categorical slots 1-2 of the reference palette (#2a78d6 blue, #eb6834 orange), validated with
validate_palette.js (--mode light --pairs all: all checks pass). Identity never rests on colour alone: the two
samples in Figure 1b also differ by marker shape and carry a legend. Text uses ink tokens, not series colours.
Run: python make_figures.py
"""
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
S = Path(os.environ.get("SLOOS_V3_WORK", str(HERE.parents[1] / "data" / "v3_work")))   # working directory with phase4/ and phase4b/
T = HERE / "tables"
F = HERE / "figures"
F.mkdir(exist_ok=True)
SURF, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
C1, C2 = "#2a78d6", "#eb6834"
plt.rcParams.update({"font.size": 8, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.linewidth": 0.6, "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "xtick.major.size": 0, "ytick.major.size": 0})


def style(ax):
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


# ---------------- Figure 1: the survey series and what follows it
N = pd.read_csv(S / "phase4" / "out" / "s1_N_by_release.csv", parse_dates=["fred_date"])
N = N.dropna(subset=["N_CRE"])
ts = pd.read_csv(T / "series_cre_spread.csv", parse_dates=["release"])
fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 3.1), gridspec_kw={"width_ratios": [1.05, 1]})
a.plot(N.fred_date, N.N_CRE, color=C1, linewidth=1.6)
a.axhline(0, color=MUTED, linewidth=0.6)
style(a)
a.set_title("a. Net share of banks tightening CRE lending standards", loc="left", fontsize=8.5, color=INK)
a.set_ylabel("Net percentage of banks (SLOOS)")
for lab, d, dx, dy, ha in [("1990-91", "1990-10-01", 7, 3, "left"), ("2008-09", "2008-10-01", 0, 6, "center"), ("2020", "2020-07-01", -3, 6, "right"), ("2023", "2023-04-01", 5, 5, "left")]:
    r = N.iloc[(N.fred_date - pd.Timestamp(d)).abs().argsort()[:1]]
    a.annotate(lab, (r.fred_date.iloc[0], r.N_CRE.iloc[0]), xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=7.5, color=INK2)
a.set_ylim(-35, 100)
a.xaxis.set_major_locator(matplotlib.dates.YearLocator(8))
a.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))

pre, main = ts[ts["sample"] == "1991-2000"], ts[ts["sample"] == "2000-2024"]
b.axhline(0, color=MUTED, linewidth=0.6)
b.scatter(main.N_CRE, main.spread, s=26, color=C1, marker="o", edgecolor=SURF, linewidth=0.9, label="2000-2024 (95 releases)", zorder=3)
b.scatter(pre.N_CRE, pre.spread, s=26, color=C2, marker="s", edgecolor=SURF, linewidth=0.9, label="1991-2000, pre-sample (38)", zorder=3)
fit = sm.OLS(ts.spread, sm.add_constant(ts.N_CRE)).fit()
xx = np.linspace(ts.N_CRE.min(), ts.N_CRE.max(), 50)
b.plot(xx, fit.params.iloc[0] + fit.params.iloc[1] * xx, color=INK2, linewidth=1.4, zorder=2)
b.set_ylim(-13.5, 25.5)
b.text(0.98, 0.025, f"pooled fit: {fit.params.iloc[1] * 10:+.2f} pp per 10 pp of tightening", transform=b.transAxes, ha="right", va="bottom", fontsize=7.5, color=INK2)
style(b)
b.set_title("b. Return spread, low-CRE minus high-CRE banks", loc="left", fontsize=8.5, color=INK)
b.set_xlabel("Net CRE tightening just released (%)")
b.set_ylabel("Return spread until the next release (%)")
leg = b.legend(loc="upper left", frameon=False, fontsize=7.5, handletextpad=0.3, borderaxespad=0.2)
for t_ in leg.get_texts():
    t_.set_color(INK2)
for yv in (2009, 1991):
    d = ts[ts.year == yv]
    r = d.loc[d.spread.idxmax()]
    b.annotate(str(yv), (r.N_CRE, r.spread), xytext=(5, 2), textcoords="offset points", fontsize=7.5, color=INK2)
fig.tight_layout(w_pad=2.0)
fig.savefig(F / "fig1_cre_tightening_and_spread.png", dpi=300)
plt.close(fig)

# ---------------- Figure 2: the pre-specified long-short through time
q = pd.read_csv(T / "series_exposure_quintiles.csv")
rel = pd.read_csv(T / "releases.csv", parse_dates=["release"])
q = q.merge(rel[["pid", "release"]], on="pid").sort_values("release")
p25 = pd.read_csv(T / "T6b_record_2025.csv", parse_dates=["t0"])
dates = list(q.release) + list(p25.t0)
ls = list(q.LS) + list(p25.LS_BT)
cum = (np.cumprod(1 + np.array(ls) / 100) - 1) * 100
fig, ax = plt.subplots(figsize=(7.2, 2.9))
ax.plot(dates, cum, color=C1, linewidth=1.6)
ax.axhline(0, color=MUTED, linewidth=0.6)
style(ax)
ymax = cum.max()
for d, lab in [(pd.Timestamp("2000-08-28"), "pre-specified test\n2000-2024"), (pd.Timestamp("2024-11-13"), "record\n2025")]:
    ax.axvline(d, color=MUTED, linewidth=0.6)
ax.text(pd.Timestamp("1995-10-01"), ymax * 0.93, "pre-sample confirmation\n1991-2000", ha="center", va="top", fontsize=7.5, color=INK2)
ax.text(pd.Timestamp("2012-06-01"), ymax * 0.93, "pre-specified test\n2000-2024", ha="center", va="top", fontsize=7.5, color=INK2)
ax.text(pd.Timestamp("2025-01-15"), ymax * 0.18, "2025", ha="left", va="top", fontsize=7.5, color=INK2)
ax.annotate(f"{cum[-1]:.0f}%", (dates[-1], cum[-1]), xytext=(-4, 5), textcoords="offset points", ha="right", fontsize=7.5, color=INK2)
ax.set_title("Cumulative return of the exposure long-short (low minus high exposure to tightening), before costs", loc="left", fontsize=8.5, color=INK)
ax.set_ylabel("Cumulative return (%)")
fig.tight_layout()
fig.savefig(F / "fig2_cumulative_long_short.png", dpi=300)
plt.close(fig)
print("figures written:", [p.name for p in sorted(F.glob("*.png"))], "| final cumulative", round(float(cum[-1]), 1), "| n periods", len(ls))
