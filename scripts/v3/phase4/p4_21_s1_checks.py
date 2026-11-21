# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / S1 implementation self-checks (not tests; nothing here enters results.csv):
duplicates, manual Newey-West t, timing assertions, signal composition, per-period series, recompute L/S from the bank table."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from p4lib import *

pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
B = pd.read_parquet(O + "s1_bank_table.parquet")
P = pd.read_csv(O + "s1_ls_periods.csv", parse_dates=["release_date", "t0", "exit"])
# 1 duplicates
print("dup (period, permno):", int(B.duplicated(["period", "permno"]).sum()), "dup (period, permco):", int(B.duplicated(["period", "permco"]).sum()),
      "dup (period, rssd):", int(B.duplicated(["period", "rssd9001"]).sum()))
# 2 timing
print("min (release - y9c_date) days:", int((B.release_date - B.y9c_date).dt.days.min()), "| all t0 > release:", bool((B.t0 > B.release_date).all()),
      "| exit > t0:", bool((B.exit > B.t0).all()), "| contiguous periods:", bool((P.t0.iloc[1:].values == P.exit.iloc[:-1].values).all()))
print("y9c lag distribution (days):", (B.release_date - B.y9c_date).dt.days.describe().round(0).to_dict())
# 3 recompute EW L/S from the bank table
m = B[B.screen]
rc = m.groupby("period").apply(lambda g: (g[g.q_main == 1].R.mean() - g[g.q_main == 5].R.mean()) * 100)
print("recomputed EW L/S vs stored, max |diff|:", float((rc.values - P.set_index("period").LS.reindex(rc.index).values).__abs__().max()))
# 4 manual NW(1) t (Bartlett, lag 1) with and without n/(n-1)
x = P.LS.to_numpy(); n = len(x); e = x - x.mean()
g0 = (e @ e) / n; g1 = (e[1:] @ e[:-1]) / n
S = g0 + 2 * (1 - 1 / 2) * g1
print(f"manual NW1 t: no correction {x.mean() / np.sqrt(S / n):.3f}, with n/(n-1) {x.mean() / np.sqrt(S / n * n / (n - 1)):.3f}; plain t {x.mean() / (x.std(ddof=1) / np.sqrt(n)):.3f}; "
      f"lag-1 autocorr {np.corrcoef(x[1:], x[:-1])[0, 1]:.3f}")
# 5 per-period series
print(P[["period", "release_date", "n", "n_long", "n_short", "R_long", "R_short", "LS", "LS_VW", "LS_nofilter", "LS_net_turnover"]].round(2).to_string(index=False))
print("LS quantiles:", P.LS.quantile([0, .05, .25, .5, .75, .95, 1]).round(2).to_dict(), "share of periods > 0:", round(float((P.LS > 0).mean()), 3))
# 6 BT composition: rank correlation of BT with the raw CRE share per period
rk = m.groupby("period").apply(lambda g: g[["BT", "share_CRE"]].corr(method="spearman").iloc[0, 1])
print("per-period Spearman(BT, raw CRE share): median", round(float(rk.median()), 3), "min", round(float(rk.min()), 3), "max", round(float(rk.max()), 3))
for k in CATS:
    rk = m.groupby("period").apply(lambda g: g[["BT", f"share_{k}"]].corr(method="spearman").iloc[0, 1])
    print(f"  median Spearman(BT, share_{k}) = {rk.median():+.3f}")
# 7 stability of quintile membership between consecutive periods
s = m[m.q_main.isin([1, 5])][["period", "permno", "q_main"]]
for qq in [1, 5]:
    a = s[s.q_main == qq]
    stay = []
    for p in sorted(a.period.unique())[1:]:
        cur = set(a[a.period == p].permno); prv = set(a[a.period == p - 1].permno)
        stay.append(len(cur & prv) / max(len(cur), 1))
    print(f"quintile {qq}: share of names also in the same quintile last period, mean {np.mean(stay):.3f}")
