# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / step 12 - category net tightening N(k, fred_date) from the FRED cache (FROZEN_PARAMS fred_series.category_N),
mapped to the US release table. Output: out/s1_N_by_release.csv, cache/N_by_quarter.parquet. No returns."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import json
import pandas as pd
from p4lib import *

fz = json.load(open(P4 + "FROZEN_PARAMS.json"))
used = fz["fred_series"]["used"]
ser = {}
for u in used:
    d = pd.read_csv(C + f"fred/{u['id']}.csv", parse_dates=["date"]).set_index("date").value
    ser[u["id"]] = d
cat_of = {u["id"]: u["category"] for u in used}
A = pd.DataFrame(ser).sort_index()
rows = []
for k in CATS:
    ids = [i for i, c in cat_of.items() if c == k]
    A[f"N_{k}"] = A[ids].mean(axis=1, skipna=True)
    A[f"nser_{k}"] = A[ids].notna().sum(axis=1)
Q = A[[f"N_{k}" for k in CATS] + [f"nser_{k}" for k in CATS] + ["DRTSCILM"]].copy()
Q.index.name = "fred_date"
Q.to_parquet(C + "N_by_quarter.parquet")
rel = pd.read_csv(O1 + "release_dates_US_SLOOS.csv", parse_dates=["fred_date", "release_date", "approx_release_regular_practice"])
R = rel[["fred_date", "release_date", "approx_release_regular_practice", "drtscilm"]].merge(Q.reset_index(), on="fred_date", how="left")
print("DRTSCILM release table vs FRED now, max |diff|:", float((R.drtscilm - R.DRTSCILM).abs().max()))
R.to_csv(O + "s1_N_by_release.csv", index=False)
pd.set_option("display.width", 250)
print(R[R.fred_date.dt.month == 1][["fred_date", "release_date"] + [f"N_{k}" for k in CATS] + [f"nser_{k}" for k in CATS]].to_string(index=False))
print("series count by category and era:")
for era, lo, hi in [("2000-2007Q1", "2000-01-01", "2007-01-01"), ("2007Q2-2013Q3", "2007-04-01", "2013-07-01"),
                    ("2013Q4-2014Q4", "2013-10-01", "2014-10-01"), ("2015-2024", "2015-01-01", "2024-10-01")]:
    z = R[(R.fred_date >= lo) & (R.fred_date <= hi)]
    print(era, {k: sorted(z[f"nser_{k}"].unique().tolist()) for k in CATS})
