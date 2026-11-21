# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / step 11 - Y-9C panel under FROZEN_PARAMS (duplicates rule, item substitutions, shares, controls).
Output: cache/y9c_panel.parquet (rssd9001, date, CI, CRE, RRE, CC, OC, L, share_*, bhck2170, bhck2122, book). No returns."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from p4lib import *

DUMP = WRDS_DUMP + ""
con = connect()
FILES = {
    "bhck_1": ("bank_all.wrds_holding_bhck_1.csv.gz", ["bhck1763", "bhck1764", "bhck1766", "bhckf158", "bhckf159", "bhckf160", "bhckf161",
                                                         "bhckb538", "bhckb539", "bhckk137", "bhckk207", "bhck2011", "bhck2008", "bhck1975"],
               "COALESCE(TRY_CAST(bhck1763 AS DOUBLE), TRY_CAST(bhck1766 AS DOUBLE))"),
    "bhck_2": ("bank_all.wrds_holding_bhck_2.csv.gz", ["bhck2170", "bhck2122", "bhck3210", "bhck3283"], "TRY_CAST(bhck2170 AS DOUBLE)"),
    "other_1": ("bank_all.wrds_holding_other_1.csv.gz", ["bhdm1797", "bhdm5367", "bhdm5368", "bhdm1460", "bhdm1480", "bhdm1415"],
                "TRY_CAST(bhdm1797 AS DOUBLE)"),
}
parts = []
for k, (f, its, keyexpr) in FILES.items():
    sql = ", ".join(f"TRY_CAST({c} AS DOUBLE) {c}" for c in its)
    d = con.execute(f"""SELECT CAST(rssd9001 AS BIGINT) rssd9001, CAST(CAST(rssd9999 AS DATE) AS VARCHAR) rssd9999, wrdsdownloaddate,
        ({keyexpr}) IS NOT NULL AS haskey, {sql} FROM read_csv('{DUMP}{f}', header=true, all_varchar=true)""").fetchdf()
    d = d.sort_values(["rssd9001", "rssd9999", "haskey", "wrdsdownloaddate"], ascending=[True, True, False, True])
    dupmask = d.duplicated(["rssd9001", "rssd9999"], keep=False)
    dd = d[dupmask]
    differ = dd.groupby(["rssd9001", "rssd9999"])[its].nunique(dropna=True).gt(1).any(axis=1)
    keep = d.drop_duplicates(["rssd9001", "rssd9999"], keep="first")
    print(f"{k}: rows {len(d)}, keys {len(keep)}, duplicated keys {dd[['rssd9001','rssd9999']].drop_duplicates().shape[0]}, "
          f"keys whose duplicate rows differ in any used item {int(differ.sum())}", flush=True)
    parts.append(keep.drop(columns=["wrdsdownloaddate", "haskey"]).set_index(["rssd9001", "rssd9999"]))
Y = pd.concat(parts, axis=1, join="outer").reset_index()
Y["date"] = pd.to_datetime(Y.rssd9999)
print("rows", len(Y), "filers", Y.rssd9001.nunique(), Y.date.min(), Y.date.max())

use = (Y.bhck2170 > 0)
Y = Y[use].copy()
print("usable filer rows (bhck2170 > 0):", len(Y), "filers", Y.rssd9001.nunique())
comp_cols = ["bhck1763", "bhck1764", "bhck1766", "bhckf158", "bhckf159", "bhckf160", "bhckf161", "bhckb538", "bhckb539", "bhckk137",
             "bhckk207", "bhck2011", "bhck2008", "bhdm1797", "bhdm5367", "bhdm5368", "bhdm1460", "bhdm1480", "bhdm1415"]
neg = {c: int((Y[c] < 0).sum()) for c in comp_cols}
print("negative component values set to 0:", {c: v for c, v in neg.items() if v})
V = {c: Y[c].clip(lower=0) for c in comp_cols}
d = Y.date
# CI
ci = np.where(V["bhck1763"].notna(), V["bhck1763"] + V["bhck1764"].fillna(0), V["bhck1766"])
# CRE
has_f_con = V["bhckf158"].notna() | V["bhckf159"].notna()
con_ = np.where(has_f_con, V["bhckf158"].fillna(0) + V["bhckf159"].fillna(0), V["bhdm1415"])
has_f_nr = V["bhckf160"].notna() | V["bhckf161"].notna()
nonres = np.where(has_f_nr, V["bhckf160"].fillna(0) + V["bhckf161"].fillna(0), V["bhdm1480"])
mf = V["bhdm1460"]
# RRE
rre_parts = [V["bhdm1797"], V["bhdm5367"], V["bhdm5368"]]
# CC / OC
pre01 = d < pd.Timestamp("2001-03-31")
post11 = d >= pd.Timestamp("2011-03-31")
cc = np.where(pre01, V["bhck2008"], V["bhckb538"])
oc = np.where(pre01, V["bhck2011"],
              np.where(post11, V["bhckb539"].fillna(0) + V["bhckk137"].fillna(0) + V["bhckk207"].fillna(0),
                       V["bhckb539"].fillna(0) + V["bhck2011"].fillna(0)))
raw = pd.DataFrame({"CI": ci, "CRE_con": con_, "CRE_mf": mf.to_numpy(), "CRE_nr": nonres,
                    "RRE_1797": rre_parts[0].to_numpy(), "RRE_5367": rre_parts[1].to_numpy(), "RRE_5368": rre_parts[2].to_numpy(),
                    "CC": cc, "OC": oc}, index=Y.index)
miss = raw.isna().sum()
print("missing components set to 0 (counts):", miss[miss > 0].to_dict())
raw = raw.fillna(0.0)
out = pd.DataFrame({"rssd9001": Y.rssd9001.values, "date": Y.date.values})
out["CI"] = raw.CI.values
out["CRE"] = (raw.CRE_con + raw.CRE_mf + raw.CRE_nr).values
out["RRE"] = (raw.RRE_1797 + raw.RRE_5367 + raw.RRE_5368).values
out["CC"] = raw.CC.values
out["OC"] = raw.OC.values
out["L"] = out[CATS].sum(axis=1)
out["bhck2170"] = Y.bhck2170.values
out["bhck2122"] = Y.bhck2122.values
out["book"] = (Y.bhck3210 - Y.bhck3283.fillna(0)).values
out["any_missing_component"] = (Y[comp_cols].isna().sum(axis=1) > 0).values
out = out[out.L > 0].copy()
for k in CATS:
    out[f"share_{k}"] = out[k] / out.L
s = out[[f"share_{k}" for k in CATS]].sum(axis=1)
assert np.allclose(s, 1.0, atol=1e-9), "shares do not sum to 1"
print("rows with L > 0:", len(out), "share sum max |1-sum|:", float((s - 1).abs().max()))
print("mean shares by year:\n", out.groupby(out.date.dt.year)[[f"share_{k}" for k in CATS]].mean().round(3).to_string())
print("filers per quarter (Dec):", out[out.date.dt.month == 12].groupby("date").size().to_dict())
out.to_parquet(C + "y9c_panel.parquet", index=False)
print("saved", C + "y9c_panel.parquet")
