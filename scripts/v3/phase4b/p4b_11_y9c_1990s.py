# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / step 11 - FR Y-9C loan-mix panel 1990-2000 from the Chicago Fed BHCF extract (FROZEN_PARAMS.json y9c_1990s rules),
plus the overlap check against the phase-4 dump panel for the report dates 2000-03-31 and 2000-06-30. No returns.

Input : cache/bhcf_items.parquet (p4b_10), phase4/cache/y9c_panel.parquet (read-only, dump-based phase-4 panel)
Output: cache/y9c_panel_1990s.parquet (rssd9001, date, CI, CRE, RRE, CC, OC, CONS, L, share_*, bhck2170, bhck2122, book),
        out/y9c_overlap_check_2000.csv (per rssd x date: Chicago Fed vs dump values)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import numpy as np
import pandas as pd

W = V3WORK + ""
P4B = W + "phase4b/"
pd.set_option("display.width", 250)

X = pd.read_parquet(P4B + "cache/bhcf_items.parquet")
X["date"] = pd.to_datetime(X.rssd9999)
print("extract rows", len(X), "dates", X.date.min().date(), "..", X.date.max().date())
Y = X[X.bhck2170 > 0].copy()
print("Y-9C filer rows (bhck2170 > 0):", len(Y))
pre = Y.date < pd.Timestamp("1990-09-30")
print("rows dated before 1990-09-30 (no real-estate breakdown in the Y-9C; not usable):", int(pre.sum()),
      Y.loc[pre].groupby("date").size().to_dict())
Y = Y[~pre].copy()
assert not Y.duplicated(["rssd9001", "date"]).any(), "duplicate (rssd9001, date)"


def pick(a, b):
    """BHDM item, else the BHCK item of the same code (consolidated) when the BHDM item is missing."""
    return Y[a].where(Y[a].notna(), Y[b])


comp = {
    "CI_1763": Y.bhck1763, "CI_1764": Y.bhck1764, "CI_1766": Y.bhck1766,
    "con": pick("bhdm1415", "bhck1415"), "mf": pick("bhdm1460", "bhck1460"), "nr": pick("bhdm1480", "bhck1480"),
    "h1797": pick("bhdm1797", "bhck1797"), "h1798": pick("bhdm1798", "bhck1798"),
    "h5367": pick("bhdm5367", "bhck5367"), "h5368": pick("bhdm5368", "bhck5368"),
    "cc2008": Y.bhck2008, "oc2011": Y.bhck2011, "cons1975": Y.bhck1975,
}
fallback_used = {k: int((Y[a].isna() & Y[b].notna()).sum()) for k, (a, b) in
                 {"con": ("bhdm1415", "bhck1415"), "mf": ("bhdm1460", "bhck1460"), "nr": ("bhdm1480", "bhck1480"),
                  "h1797": ("bhdm1797", "bhck1797"), "h1798": ("bhdm1798", "bhck1798"), "h5367": ("bhdm5367", "bhck5367"),
                  "h5368": ("bhdm5368", "bhck5368")}.items()}
print("BHCK fallback used (BHDM missing, BHCK present):", fallback_used)
early = Y.date <= pd.Timestamp("1990-12-31")  # 1990-09-30, 1990-12-31: 1-4 family closed-end = 1798; no CC / OC split
need = {"con", "mf", "nr", "h1797"} | ({"h1798"}) | {"h5367", "h5368", "cc2008", "oc2011", "cons1975"}
neg = {k: int((v < 0).sum()) for k, v in comp.items()}
print("negative values set to 0:", {k: v for k, v in neg.items() if v})
V = {k: v.clip(lower=0) for k, v in comp.items()}
# missing counts, era-specific (only the items that the era uses)
miss = {}
for k in ["con", "mf", "nr", "h1797"]:
    miss[k] = int(V[k].isna().sum())
miss["h1798 (1990Q3-Q4)"] = int(V["h1798"][early].isna().sum())
for k in ["h5367", "h5368", "cc2008", "oc2011"]:
    miss[f"{k} (1991Q1+)"] = int(V[k][~early].isna().sum())
miss["cons1975 (1990Q3-Q4)"] = int(V["cons1975"][early].isna().sum())
miss["CI (1763 and 1766 both missing)"] = int((V["CI_1763"].isna() & V["CI_1766"].isna()).sum())
print("missing components set to 0 (counts):", {k: v for k, v in miss.items() if v})

ci = np.where(V["CI_1763"].notna(), V["CI_1763"] + V["CI_1764"].fillna(0), V["CI_1766"])
ci = np.nan_to_num(ci, nan=0.0)
cre = V["con"].fillna(0) + V["mf"].fillna(0) + V["nr"].fillna(0)
rre = V["h1797"].fillna(0) + np.where(early, V["h1798"].fillna(0), V["h5367"].fillna(0) + V["h5368"].fillna(0))
cc = np.where(early, np.nan, V["cc2008"].fillna(0))
oc = np.where(early, np.nan, V["oc2011"].fillna(0))
cons = np.where(early, V["cons1975"].fillna(0), np.nan_to_num(cc) + np.nan_to_num(oc))
out = pd.DataFrame({"rssd9001": Y.rssd9001.astype("int64").values, "date": Y.date.values, "CI": ci, "CRE": cre.values,
                    "RRE": np.asarray(rre, float), "CC": cc, "OC": oc, "CONS": cons})
out["L"] = out.CI + out.CRE + out.RRE + out.CONS
out["bhck2170"] = Y.bhck2170.values
out["bhck2122"] = Y.bhck2122.values
out["book"] = (Y.bhck3210 - Y.bhck3283.fillna(0)).values
out["cc_oc_split"] = ~early.values
n0 = len(out)
out = out[out.L > 0].copy()
print("rows with five-category total L > 0:", len(out), "of", n0)
for k in ["CI", "CRE", "RRE", "CC", "OC", "CONS"]:
    out[f"share_{k}"] = out[k] / out.L
s = out[["share_CI", "share_CRE", "share_RRE", "share_CONS"]].sum(axis=1)
assert np.allclose(s, 1.0, atol=1e-9)
s2 = out.loc[out.cc_oc_split, ["share_CI", "share_CRE", "share_RRE", "share_CC", "share_OC"]].sum(axis=1)
assert np.allclose(s2, 1.0, atol=1e-9)
print("share sums: max |1 - sum| (4 groups)", float((s - 1).abs().max()), "| (5 categories, 1991Q1+)", float((s2 - 1).abs().max()))
print("mean shares by year (all Y-9C filers):\n", out.groupby(out.date.dt.year)[["share_CI", "share_CRE", "share_RRE", "share_CC", "share_OC", "share_CONS"]]
      .mean().round(3).to_string())
print("filers per report date:", out.groupby("date").size().to_dict())
# persistence of the CRE share between consecutive quarters (for the 75-day timing discussion)
o = out.sort_values(["rssd9001", "date"]).copy()
o["prev_date"] = o.groupby("rssd9001").date.shift(); o["prev_cre"] = o.groupby("rssd9001").share_CRE.shift()
oo = o[(o.date - o.prev_date).dt.days.between(85, 95)]
print("CRE share, consecutive quarters: corr", round(float(oo.share_CRE.corr(oo.prev_cre)), 4), "| Spearman",
      round(float(oo.share_CRE.rank().corr(oo.prev_cre.rank())), 4), "| median |change|", round(float((oo.share_CRE - oo.prev_cre).abs().median()), 4),
      "n", len(oo))
out.to_parquet(P4B + "cache/y9c_panel_1990s.parquet", index=False)
print("saved cache/y9c_panel_1990s.parquet", len(out))

# ---------------- overlap check vs the phase-4 dump panel (2000-03-31, 2000-06-30)
D = pd.read_parquet(W + "phase4/cache/y9c_panel.parquet")
D["date"] = pd.to_datetime(D.date)
rows = []
for dt in [pd.Timestamp("2000-03-31"), pd.Timestamp("2000-06-30")]:
    a = out[out.date == dt].set_index("rssd9001")
    b = D[D.date == dt].set_index("rssd9001")
    common = a.index.intersection(b.index)
    print(f"\n[overlap {dt.date()}] Chicago Fed filers {len(a)}, dump filers {len(b)}, common {len(common)}, only CF {len(a.index.difference(b.index))}, "
          f"only dump {len(b.index.difference(a.index))}")
    for k in ["CI", "CRE", "RRE", "CC", "OC", "L", "bhck2170", "bhck2122"]:
        diff = (a.loc[common, k] - b.loc[common, k]).abs()
        print(f"   {k:8s}: identical (|diff| <= 0.5 $000) {float((diff <= 0.5).mean()):.4f}, max |diff| {float(diff.max()):.1f}")
    for k in ["CI", "CRE", "RRE", "CC", "OC"]:
        diff = (a.loc[common, f"share_{k}"] - b.loc[common, f"share_{k}"]).abs()
        print(f"   share_{k:4s}: max |diff| {float(diff.max()):.2e}, share with |diff| < 1e-9 {float((diff < 1e-9).mean()):.4f}")
    z = pd.DataFrame({"rssd9001": common, "date": dt})
    for k in ["CI", "CRE", "RRE", "CC", "OC", "L", "share_CRE", "share_CI", "bhck2170"]:
        z[f"{k}_cf"] = a.loc[common, k].values; z[f"{k}_dump"] = b.loc[common, k].values
    rows.append(z)
pd.concat(rows).to_csv(P4B + "out/y9c_overlap_check_2000.csv", index=False)
print("saved out/y9c_overlap_check_2000.csv")
