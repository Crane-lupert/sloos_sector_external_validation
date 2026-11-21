# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Main-thread addendum to the SLOOS phase-4 pilot S1 - EXPLORATORY (post hoc), not used for the verdict.

Why: the spec asked for a Fama-MacBeth regression "with the loan shares as controls" to tell a fixed loan-mix
premium from the time variation of the survey. Inside one release, BT = sum_k share_k * N_k is an exact linear
function of the shares (the N_k are common to all banks), so a period-by-period regression cannot identify the
BT coefficient - the reported FM-B coefficient is a collinearity artefact (spec design error by the main thread).
The question is identified only ACROSS releases. This script asks it properly:

 1. collinearity check of the FM-B design
 2. pooled panel: return ~ release fixed effects + loan shares (constant coefficients) + BT ; clustered by release
 3. the same with one interaction per category: share_k x (N_k at release - average N_k)
 4. time series: does the return of the static CRE tilt depend on the CRE tightening just released?
 5. influence of single releases (leave-one-year-out) on the primary long-short mean
Run: python s1_phase4_addendum.py
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
P4 = Path(V3WORK) / "phase4"
CATS = ["CI", "CRE", "RRE", "CC", "OC"]

b = pd.read_parquet(P4 / "out" / "s1_bank_table.parquet")
N = pd.read_csv(P4 / "out" / "s1_N_by_release.csv", parse_dates=["fred_date", "release_date"])
Nr = N.dropna(subset=["release_date"]).set_index("release_date")[[f"N_{k}" for k in CATS]]
m = b[b.screen & b.R.notna() & b.BT.notna()].copy()
m["Rp"] = m.R * 100
m = m.merge(Nr, left_on="release_date", right_index=True, how="left")
m["zBT"] = m.groupby("period").BT.transform(lambda s: (s - s.mean()) / s.std(ddof=0))
print(f"main universe rows {len(m)}, releases {m.period.nunique()}")

# ---- 1. collinearity of the period-by-period design
r2, rank_def = [], 0
for p, g in m.groupby("period"):
    X = sm.add_constant(g[["share_CI", "share_CRE", "share_CC", "share_OC"]])
    r2.append(sm.OLS(g.zBT, X).fit().rsquared)
    rank_def += int(np.linalg.matrix_rank(np.column_stack([X.values, g.zBT.values]), tol=1e-8) < X.shape[1] + 1)
r2 = np.array(r2)
print(f"[1] zBT explained by the four raw shares inside a release: R2 = 1 (to 1e-10) in {int((r2 > 1 - 1e-10).sum())} of {len(r2)} releases; "
      f"design matrix rank-deficient in {rank_def} releases; remaining releases min R2 {r2[r2 <= 1 - 1e-10].min() if (r2 <= 1 - 1e-10).any() else float('nan'):.4f}")


def within(df, cols):
    return df[cols] - df.groupby("period")[cols].transform("mean")


def panel(y, xcols, df, label):
    d = df.dropna(subset=[y] + xcols).copy()
    W = within(d, [y] + xcols)
    f = sm.OLS(W[y], W[xcols]).fit(cov_type="cluster", cov_kwds={"groups": d.period.values, "use_correction": True})
    print(f"   {label}: n {len(d)}, releases {d.period.nunique()}")
    for c in xcols:
        if c.startswith("zBT") or c.startswith("I_") or c == "BT":
            print(f"      {c:10s} coef {f.params[c]:+.4f}  t {f.tvalues[c]:+.2f}")
    return f, d


# ---- 2. pooled panel with constant share coefficients
print("[2] pooled panel, release fixed effects, standard errors clustered by release (coef of zBT in % per one cross-sectional sd)")
sh = ["share_CI", "share_CRE", "share_CC", "share_OC"]
panel("Rp", ["zBT"], m, "no share controls")
f2, d2 = panel("Rp", ["zBT"] + sh, m, "with loan shares (constant coefficients)")
panel("Rp", ["zBT"] + sh + ["logcap", "bm", "mom12"], m, "with loan shares + size, book-to-market, momentum")
for lab, a, bq in [("2000-2011", 2000, 2011), ("2012-2024", 2012, 2024)]:
    panel("Rp", ["zBT"] + sh, m[(m.year >= a) & (m.year <= bq)], f"with loan shares, {lab}")
panel("Rp", ["zBT"] + sh, m[~m.year.isin([2008, 2009])], "with loan shares, excluding releases in 2008-2009")

# ---- 3. one interaction per category (deviation of tightening from its own average)
print("[3] interactions share_k x (N_k - average N_k); expected sign negative; coef in % per (share 1.0 x 10pp)")
mean_full = Nr.loc[sorted(m.release_date.unique())].mean()
for k in CATS:
    m[f"I_{k}"] = m[f"share_{k}"] * (m[f"N_{k}"] - mean_full[f"N_{k}"]).fillna(0) / 10.0
panel("Rp", [f"I_{k}" for k in CATS] + sh, m, "five interactions + loan shares")
panel("Rp", ["I_CRE"] + sh, m, "CRE interaction only + loan shares")

# ---- 4. time series of the static CRE tilt
print("[4] time series: return of (low CRE share quintile - high CRE share quintile) on the CRE tightening released (per 10pp)")
rows = []
for p, g in m.groupby("period"):
    g = g.sort_values(["share_CRE", "permno"], kind="mergesort")
    n = len(g)
    q = np.ceil(5 * (np.arange(n) + 1) / n).astype(int)
    rows.append((p, g.year.iloc[0], g.Rp.values[q == 1].mean() - g.Rp.values[q == 5].mean(), g.N_CRE.iloc[0], g.N_CI.iloc[0]))
ts = pd.DataFrame(rows, columns=["period", "year", "ls_cre", "N_CRE", "N_CI"]).set_index("period")
for lab, d in [("all releases", ts), ("excluding 2008-2009", ts[~ts.year.isin([2008, 2009])]), ("2012-2024", ts[ts.year >= 2012])]:
    f = sm.OLS(d.ls_cre, sm.add_constant(d.N_CRE / 10.0)).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
    print(f"   {lab:22s}: n {len(d)}, slope {f.params.iloc[1]:+.3f}% per 10pp (t {f.tvalues.iloc[1]:+.2f}), intercept {f.params.iloc[0]:+.3f}% (t {f.tvalues.iloc[0]:+.2f})")
hi = ts[ts.N_CRE > ts.N_CRE.median()]
lo = ts[ts.N_CRE <= ts.N_CRE.median()]
print(f"   CRE tightening above its median: mean {hi.ls_cre.mean():+.3f}% (n {len(hi)}); at or below: {lo.ls_cre.mean():+.3f}% (n {len(lo)})")

# ---- 5. leave-one-year-out on the primary long-short series
ls = pd.read_csv(P4 / "out" / "s1_ls_periods.csv")
tt = []
for y in sorted(ls.year.unique()):
    x = ls[ls.year != y].LS.values
    f = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
    tt.append((y, f.params[0], f.tvalues[0]))
tt = pd.DataFrame(tt, columns=["year_dropped", "mean", "t"])
print(f"[5] leave-one-year-out, primary long-short: t range {tt.t.min():.2f} .. {tt.t.max():.2f}; lowest when dropping {int(tt.loc[tt.t.idxmin(), 'year_dropped'])} "
      f"(mean {tt.loc[tt.t.idxmin(), 'mean']:+.3f}%); years whose removal puts t below 2.24: {tt[tt.t < 2.24].year_dropped.astype(int).tolist()}")
