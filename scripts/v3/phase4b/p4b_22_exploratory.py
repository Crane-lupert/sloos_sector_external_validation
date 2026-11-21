# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / step 22 - EXPLORATORY (post hoc) diagnostics of the 1990s H1 / H2 results. NOT used for the verdict.
Added after the p4b_20 results were seen (recorded in FROZEN_PARAMS.json deviations NOTE-2). No frozen parameter is changed.

 E1  leave-one-year-out (release year) range of the H1 mean t and the H2 slope t, and which single years move t below 1.96
 E2  H2 slope with the PREVIOUS survey's N_CRE (released one quarter earlier, certainly public at every entry) - addresses the
     risk that an approximate (1990-96) release date + 10 trading days was still before the actual release
 E3  per-period table (descriptive) of N_CRE, LS_CRE, LS_BT
Output: logs/p4b_22_exploratory.log, out/exploratory_1990s.csv
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from p4blib import *

pd.set_option("display.width", 250)
res = Results()
S = pd.read_csv(O + "h1h2_1990s_periods.csv", parse_dates=["fred_date", "release_date", "t0", "exit"])
N = pd.read_csv(P4O + "s1_N_by_release.csv", parse_dates=["fred_date"]).set_index("fred_date")
S["N_CRE_prev"] = [N.N_CRE.shift(1).loc[f] for f in S.fred_date]

# E1
rows = []
for y in sorted(S.year.unique()):
    d = S[S.year != y]
    a = nw_mean(d.LS_BT, 1); b = ols_slope(d.LS_CRE, d.N_CRE / 10, cov="HAC", lags=1)
    rows.append(dict(year_dropped=y, n=len(d), H1_mean=a["mean"], H1_t=a["t"], H2_slope=b["b"], H2_t=b["t"]))
L = pd.DataFrame(rows)
print("E1 leave-one-year-out (EXPLORATORY):")
print(L.round(3).to_string(index=False))
print(f"   H1 t range {L.H1_t.min():+.2f} .. {L.H1_t.max():+.2f}; H2 slope t range {L.H2_t.min():+.2f} .. {L.H2_t.max():+.2f}; "
      f"years whose removal puts the H2 t below 1.96: {L[L.H2_t < 1.96].year_dropped.tolist()}")
res.add("EXPL_LOYO_H1", "1990s", t_min=L.H1_t.min(), t_max=L.H1_t.max())
res.add("EXPL_LOYO_H2", "1990s", t_min=L.H2_t.min(), t_max=L.H2_t.max(), slope_min=L.H2_slope.min(), slope_max=L.H2_slope.max(),
        years_below_196=";".join(str(v) for v in L[L.H2_t < 1.96].year_dropped))
for lab, d in [("excluding 1991-1992 releases", S[S.year >= 1993]), ("excluding 1991 releases", S[S.year != 1991])]:
    b = ols_slope(d.LS_CRE, d.N_CRE / 10, cov="HAC", lags=1)
    print(f"   H2 slope {lab}: {b['b']:+.3f} (t {b['t']:+.2f}, n {b['n']})")

# E2
for lab, d in [("full", S), ("1993-2000Q2", S[S.year >= 1993])]:
    b = ols_slope(d.LS_CRE, d.N_CRE_prev / 10, cov="HAC", lags=1)
    print(f"E2 H2 slope on the previous survey's N_CRE [{lab}] (EXPLORATORY): {b['b']:+.3f}%/10pp (t {b['t']:+.2f}, n {b['n']})")
    res.add("EXPL_H2_prevN", lab, n=b["n"], slope=b["b"], t_nw1=b["t"])
print(f"   corr(N_CRE, previous N_CRE) over the 38 periods: {S.N_CRE.corr(S.N_CRE_prev):.3f}")

# E3
print("\nE3 per-period series (main universe, %):")
print(S[["fred_date", "release_date", "approx_date", "t0", "exit", "n", "N_CI", "N_CRE", "N_CRE_prev", "LS_BT", "LS_CRE", "R_cre_low", "R_cre_high", "R_all"]]
      .round(2).to_string(index=False))
res.save(O + "exploratory_1990s.csv")
