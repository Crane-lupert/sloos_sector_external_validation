# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / step 40 - out/results.csv (test_id, sample, stat, value) = results_1990s + exploratory_1990s (marked) + results_2025."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import pandas as pd

O = V3WORK + "phase4b/out/"
a = pd.read_csv(O + "results_1990s.csv")
e = pd.read_csv(O + "exploratory_1990s.csv"); e["test_id"] = "EXPLORATORY_post_hoc:" + e.test_id
b = pd.read_csv(O + "results_2025.csv")
r = pd.concat([a, e, b], ignore_index=True)
r.to_csv(O + "results.csv", index=False)
key = r[r.stat.isin(["n", "mean_pct", "slope_pct_per_10pp", "t_nw1", "coef_I_CRE", "t_I_CRE", "verdict"]) &
        r.test_id.isin(["H1_main_EW", "H2_main_slope", "H2_main_panel"])]
pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200)
print(key.to_string(index=False))
print("rows", len(r), "->", O + "results.csv")
