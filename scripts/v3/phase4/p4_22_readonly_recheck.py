# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 - read-only recheck (writes nothing): recompute the two primary statistics from the saved per-period / per-event
tables and from an independent second pass over the bank table, and compare with out/results.csv."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from p4lib import *

R = pd.read_csv(O + "results.csv")
get = lambda t, s, k: float(R[(R.test_id == t) & (R["sample"] == s) & (R.stat == k)].value.iloc[0])
# S1: from the bank table (independent of s1_ls_periods.csv)
B = pd.read_parquet(O + "s1_bank_table.parquet")
m = B[B.screen]
ls = []
for p, g in m.groupby("period"):
    z = g.sort_values(["BT", "permno"]); n = len(z)
    q = np.ceil(5 * np.arange(1, n + 1) / n)
    ls.append((z.R.values[q == 1].mean() - z.R.values[q == 5].mean()) * 100)
ls = np.array(ls)
fit = sm.OLS(ls, np.ones(len(ls))).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
print(f"S1 main EW: recomputed mean {ls.mean():.6f} t {fit.tvalues[0]:.6f} | stored {get('S1_main_EW', '2000-2024', 'mean_pct'):.6f} "
      f"t {get('S1_main_EW', '2000-2024', 't_nw1'):.6f}")
# S2: from the event table
E = pd.read_csv(O + "s2_events.csv")
f2 = sm.OLS(E.CAR_ew, sm.add_constant(E.s / 10)).fit(cov_type="HC0")
car = ((E.ew0 - E.mkt0) + (E.ew1 - E.mkt1)) * 100
print(f"S2 main EW: recomputed slope {f2.params.iloc[1]:.6f} t {f2.tvalues.iloc[1]:.6f} | stored {get('S2_main_EW_CAR01', '1997-2024', 'slope_pct_per10pp'):.6f} "
      f"t {get('S2_main_EW_CAR01', '1997-2024', 't_white'):.6f} | CAR column consistent: {np.allclose(car, E.CAR_ew)}")
# surprise check against FRED cache
Q = pd.read_parquet(C + "N_by_quarter.parquet"); y = Q.DRTSCILM
E["fd"] = pd.to_datetime(E.fred_date)
s_chk = [y.loc[d] - y.loc[d - pd.DateOffset(months=3)] for d in E.fd]
print("S2 surprise recomputed from FRED cache, max |diff|:", float(np.max(np.abs(np.array(s_chk) - E.s.values))))
