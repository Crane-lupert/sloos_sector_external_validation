# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / step 50 - merge results_s1/s2/s3 into out/results.csv (test_id, sample, stat, value), parquet copies of the
primary-test series, and a compact summary print for the report."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import os
import pandas as pd
from p4lib import *

parts = [pd.read_csv(O + f) for f in ["results_s1.csv", "results_s2.csv", "results_s3.csv"]]
R = pd.concat(parts, ignore_index=True)
R.to_csv(O + "results.csv", index=False)
pd.read_csv(O + "s1_ls_periods.csv").to_parquet(O + "s1_ls_periods.parquet", index=False)
pd.read_csv(O + "s2_events.csv").to_parquet(O + "s2_events.parquet", index=False)
pd.read_csv(O + "s1_ls_monthly.csv").astype({"ym": str}).to_parquet(O + "s1_ls_monthly.parquet", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400); pd.set_option("display.max_colwidth", 60)
W_ = R.pivot_table(index=["test_id", "sample"], columns="stat", values="value", aggfunc="first")
cols = [c for c in ["n", "n_periods", "mean_pct", "slope_pct_per10pp", "slope_pct_per_pp", "t_nw1", "t_white", "crit_exact_df", "r2_os",
                    "r2_os_ct", "sharpe_timing", "sharpe_bh", "sharpe_timing_rf0", "sharpe_bh_rf0", "verdict"] if c in W_.columns]
print(W_[cols].to_string())
tot = 0
for root, _, files in os.walk(P4):
    for f in files:
        tot += os.path.getsize(os.path.join(root, f))
print(f"phase4 total size: {tot / 1e6:.1f} MB")
