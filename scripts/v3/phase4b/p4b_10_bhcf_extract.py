# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / step 10 - Step 0 item coverage of the Chicago Fed BHCF quarterly CSVs + extraction of the needed columns.
No returns are read or computed here.

Usage : python -E -P p4b_10_bhcf_extract.py <raw-dir>        (raw-dir holds bhcfYYMM.csv, treated as untrusted CSV text)
Writes: cache/bhcf_items.parquet  (one row per file row; needed columns only, numeric; rssd9001, rssd9999 as date)
        stdout -> logs/p4b_10_bhcf_extract.log (per-quarter coverage, identities, reporting threshold, duplicates)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

P4B = V3WORK + "phase4b/"
KEEP = ["RSSD9001", "RSSD9999", "RSSD9048", "BHCK2170", "BHCK2122", "BHCK3210", "BHCK3283",
        "BHCK1763", "BHCK1764", "BHCK1766",
        "BHDM1410", "BHCK1410",
        "BHDM1415", "BHCK1415", "BHDM1420", "BHCK1420", "BHDM1460", "BHCK1460", "BHDM1480", "BHCK1480",
        "BHDM1797", "BHCK1797", "BHDM1798", "BHCK1798", "BHDM5367", "BHCK5367", "BHDM5368", "BHCK5368",
        "BHCK1975", "BHDM1975", "BHCK2008", "BHCK2011", "BHCKB538", "BHCKB539"]
pd.set_option("display.width", 250)

raw = sys.argv[1]
files = sorted(glob.glob(os.path.join(raw, "bhcf[0-9][0-9][0-9][0-9].csv")),
               key=lambda p: (int(os.path.basename(p)[4:6]) + (1900 if int(os.path.basename(p)[4:6]) >= 50 else 2000),
                              os.path.basename(p)[6:8]))
print("files:", len(files), [os.path.basename(f) for f in files])
parts, cov = [], []
for path in files:
    yymm = os.path.basename(path)[4:8]
    d = pd.read_csv(path, dtype=str, encoding="latin-1", low_memory=False)
    d.columns = [c.strip().upper() for c in d.columns]
    present = [c for c in KEEP if c in d.columns]
    x = d[present].copy()
    for c in KEEP:
        if c not in x.columns:
            x[c] = np.nan
    for c in KEEP:
        if c not in ("RSSD9999",):
            x[c] = pd.to_numeric(x[c], errors="coerce")
    x["RSSD9999"] = pd.to_datetime(x.RSSD9999.astype(str).str.strip(), format="%Y%m%d", errors="coerce")
    x["src_file"] = os.path.basename(path)
    rd = x.RSSD9999.dropna().unique()
    y = x[x.BHCK2170.notna()]
    dup = int(y.RSSD9001.duplicated().sum())
    row = dict(file=yymm, report_dates=",".join(str(pd.Timestamp(v).date()) for v in rd), rows=len(x), y9c_filers=len(y),
               dup_rssd_y9c=dup, n_cols_file=d.shape[1])
    for c in ["BHCK1763", "BHCK1766", "BHDM1415", "BHDM1460", "BHDM1480", "BHCK1415", "BHDM1797", "BHDM1798", "BHDM5367", "BHDM5368",
              "BHCK1975", "BHCK2008", "BHCK2011", "BHCK2122", "BHCK3210"]:
        row[c] = int(y[c].notna().sum())
    a = y.BHCK2170
    row["assets_min_k"] = float(a.min()); row["assets_p01_k"] = float(a.quantile(0.01)); row["n_assets_lt_150m"] = int((a < 150000).sum())
    # identities
    re_parts = ["BHDM1415", "BHDM1420", "BHDM1460", "BHDM1480", "BHDM1797", "BHDM1798", "BHDM5367", "BHDM5368"]
    s = y[re_parts].fillna(0).sum(axis=1); t = y.BHDM1410
    ok = t.notna() & (t > 0) & y.BHDM1415.notna()
    row["re_identity_share"] = round(float(((s - t).abs() <= 1)[ok].mean()), 4) if ok.any() else np.nan
    ci = y.BHCK1763 + y.BHCK1764.fillna(0); ok2 = y.BHCK1763.notna() & y.BHCK1766.notna()
    row["ci_identity_share"] = round(float(((ci - y.BHCK1766).abs() <= 1)[ok2].mean()), 4) if ok2.any() else np.nan
    ok3 = y.BHCK2008.notna() & y.BHCK2011.notna() & y.BHCK1975.notna()
    row["cons_identity_share"] = round(float(((y.BHCK2008 + y.BHCK2011 - y.BHCK1975).abs() <= 1)[ok3].mean()), 4) if ok3.any() else np.nan
    both = y.BHCK1415.notna() & y.BHDM1415.notna()
    row["bhck_eq_bhdm_1415_share"] = round(float((y.BHCK1415 == y.BHDM1415)[both].mean()), 4) if both.any() else np.nan
    cov.append(row)
    parts.append(x)
    print(f"{yymm}: rows {len(x)}, Y-9C filers {len(y)}, report dates {row['report_dates']}, dup rssd among Y-9C {dup}", flush=True)
B = pd.concat(parts, ignore_index=True)
B.columns = [c.lower() for c in B.columns]
B = B.rename(columns={"rssd9999": "rssd9999"})
os.makedirs(P4B + "cache", exist_ok=True)
B.to_parquet(P4B + "cache/bhcf_items.parquet", index=False)
C = pd.DataFrame(cov)
C.to_csv(P4B + "logs/p4b_10_bhcf_coverage.csv", index=False)
print(C.to_string(index=False))
print("saved", P4B + "cache/bhcf_items.parquet", len(B), "rows;", P4B + "logs/p4b_10_bhcf_coverage.csv")
