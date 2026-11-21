# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Main-thread check of the SLOOS phase-4 pilot S1 (category tightening x bank loan mix -> bank stock cross-section).

A. Primary statistic recomputed from the agent's bank table with own quintile assignment.
B. Inputs rebuilt independently for random samples:
   B1 BT = sum_k share_k * N_k recomputed for every row from the release table,
   B2 loan shares recomputed from the raw FR Y-9C dump for a random sample of bank-quarters,
   B3 holding-period returns recomputed from the legacy CRSP daily file (dsf, not dsf_v2) for a random sample.
C. Interpretation checks - EXPLORATORY (post hoc), not used for the pass/fail verdict:
   what part of the long-short return comes from the survey's time variation and what part from a fixed
   loan-mix tilt (static CRE share).
Run: python s1_phase4_check.py
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
P4 = Path(V3WORK) / "phase4"
DUMP = WRDS_DUMP.rstrip("/")
CATS = ["CI", "CRE", "RRE", "CC", "OC"]
rng = np.random.default_rng(20261121)


def nw_t(x, lag=1):
    x = np.asarray(x, float)
    f = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lag, "use_correction": False})
    return f.params[0], f.tvalues[0]


def ls_series(df, col, n_q=5, long_low=True):
    """Equal-weighted quintile long-short per period on `col`; quintile = ceil(n_q * rank / n), ties by permno."""
    out = {}
    for p, g in df.groupby("period"):
        g = g.dropna(subset=[col, "R"]).sort_values([col, "permno"], kind="mergesort")
        n = len(g)
        if n < 2 * n_q:
            continue
        q = np.ceil(n_q * (np.arange(n) + 1) / n).astype(int)
        lo, hi = g.R.values[q == 1].mean(), g.R.values[q == n_q].mean()
        out[p] = (lo - hi) if long_low else (hi - lo)
    return pd.Series(out).sort_index() * 100


def report(name, s, years):
    m, t = nw_t(s.values)
    a = s[years.reindex(s.index) <= 2011]
    b = s[years.reindex(s.index) >= 2012]
    ma, ta = nw_t(a.values)
    mb, tb = nw_t(b.values)
    print(f"   {name:58s} n {len(s):3d} mean {m:+.3f}% t {t:+.2f} | 2000-11 {ma:+.3f} (t {ta:+.2f}) | 2012-24 {mb:+.3f} (t {tb:+.2f}) | share>0 {np.mean(s.values > 0):.2f}")
    return m, t


b = pd.read_parquet(P4 / "out" / "s1_bank_table.parquet")
N = pd.read_csv(P4 / "out" / "s1_N_by_release.csv", parse_dates=["fred_date", "release_date"])
main = b[b.screen].copy()
years = main.groupby("period").year.first()

# ---------------- A. primary ----------------
print("[A] primary statistic, own quintile assignment")
s_main = ls_series(main, "BT")
report("EW long lowest-BT minus short highest-BT (main universe)", s_main, years)
ag = pd.read_csv(P4 / "out" / "s1_ls_periods.csv").set_index("period").LS
print(f"   max abs difference vs agent per-period series: {np.abs(s_main - ag.reindex(s_main.index)).max():.2e}")
# exact small-sample critical value check
from scipy import stats
print(f"   Bonferroni-2 two-sided critical values: normal 2.24, t(df={len(s_main)-1}) {stats.t.ppf(1 - 0.05 / 4, len(s_main) - 1):.3f}")
print(f"   plain t (no HAC) {s_main.mean() / (s_main.std(ddof=1) / np.sqrt(len(s_main))):.2f}; NW lags 2/4: {nw_t(s_main.values, 2)[1]:.2f} / {nw_t(s_main.values, 4)[1]:.2f}")

# ---------------- B1. BT recomputation ----------------
print("[B1] BT recomputed from renormalised shares and the release table")
Nr = N.dropna(subset=["release_date"]).set_index("release_date")[[f"N_{k}" for k in CATS]]
chk = b.merge(Nr, left_on="release_date", right_index=True, how="left")
bt2 = sum(chk[f"sh2_{k}"].fillna(0) * chk[f"N_{k}"].fillna(0) for k in CATS)
print(f"   rows {len(chk)}, max |BT - recomputed| {np.abs(chk.BT - bt2).max():.2e}; share sums min/max {chk[[f'sh2_{k}' for k in CATS]].sum(axis=1).min():.6f}/{chk[[f'sh2_{k}' for k in CATS]].sum(axis=1).max():.6f}")
print("   releases with RRE missing in N:", int(Nr.loc[sorted(b.release_date.unique())].N_RRE.isna().sum()), "of", b.release_date.nunique())

# ---------------- B2. shares from raw Y-9C ----------------
print("[B2] loan shares recomputed from the raw FR Y-9C files (random sample of bank-quarters)")
keys = b[["rssd9001", "y9c_date"]].drop_duplicates().sample(400, random_state=7)
keys["rssd9001"] = keys.rssd9001.astype(int).astype(str)
keys["d"] = pd.to_datetime(keys.y9c_date).dt.strftime("%Y-%m-%d")
con = duckdb.connect()
con.execute("SET memory_limit='6GB'")
con.register("k", keys[["rssd9001", "d"]])
cols = {
    "bank_all.wrds_holding_bhck_1": ["bhck1763", "bhck1764", "bhck1766", "bhckf158", "bhckf159", "bhckf160", "bhckf161", "bhckb538", "bhckb539", "bhckk137", "bhckk207", "bhck2011", "bhck2008"],
    "bank_all.wrds_holding_other_1": ["bhdm1415", "bhdm1460", "bhdm1480", "bhdm1797", "bhdm5367", "bhdm5368"],
}
raw = None
for f, cc in cols.items():
    hdr = con.execute(f"SELECT * FROM read_csv('{DUMP}/{f}.csv.gz', all_varchar=true, header=true, ignore_errors=true) LIMIT 0").df().columns
    cc = [c for c in cc if c in hdr]
    sel = ", ".join(f"max(TRY_CAST(t.{c} AS DOUBLE)) AS {c}" for c in cc)
    d = con.execute(f"""SELECT t.rssd9001, t.rssd9999 AS d, {sel}
                        FROM read_csv('{DUMP}/{f}.csv.gz', all_varchar=true, header=true, ignore_errors=true) t
                        JOIN k ON k.rssd9001 = t.rssd9001 AND k.d = t.rssd9999 GROUP BY 1, 2""").df()
    raw = d if raw is None else raw.merge(d, on=["rssd9001", "d"], how="outer")
z = raw.fillna(np.nan)
g = lambda c: z[c] if c in z else pd.Series(np.nan, index=z.index)
ci = (g("bhck1763").fillna(0) + g("bhck1764").fillna(0)).where(g("bhck1763").notna() | g("bhck1764").notna(), g("bhck1766"))
cons = (g("bhckf158").fillna(0) + g("bhckf159").fillna(0)).where(g("bhckf158").notna() | g("bhckf159").notna(), g("bhdm1415"))
nonres = (g("bhckf160").fillna(0) + g("bhckf161").fillna(0)).where(g("bhckf160").notna() | g("bhckf161").notna(), g("bhdm1480"))
cre = cons.fillna(0) + g("bhdm1460").fillna(0) + nonres.fillna(0)
rre = g("bhdm1797").fillna(0) + g("bhdm5367").fillna(0) + g("bhdm5368").fillna(0)
cc_ = g("bhckb538").where(g("bhckb538").notna(), g("bhck2008"))
oc_new = g("bhckb539").fillna(0) + g("bhckk137").fillna(0) + g("bhckk207").fillna(0)
oc_old = g("bhckb539").fillna(0) + g("bhck2011").fillna(0)
oc = oc_new.where(g("bhckk137").notna() | g("bhckk207").notna(), oc_old)
oc = oc.where(g("bhckb539").notna() | g("bhckk137").notna(), g("bhck2011"))
tot = ci.fillna(0) + cre + rre + cc_.fillna(0) + oc.fillna(0)
mine = pd.DataFrame({"rssd9001": z.rssd9001.astype(int), "y9c_date": pd.to_datetime(z.d), "m_CI": ci.fillna(0) / tot, "m_CRE": cre / tot,
                     "m_RRE": rre / tot, "m_CC": cc_.fillna(0) / tot, "m_OC": oc.fillna(0) / tot})
ref = b.drop_duplicates(["rssd9001", "y9c_date"])[["rssd9001", "y9c_date"] + [f"share_{k}" for k in CATS]]
ref["rssd9001"] = ref.rssd9001.astype(int)
cmp_ = mine.merge(ref, on=["rssd9001", "y9c_date"])
for k in CATS:
    dif = (cmp_[f"m_{k}"] - cmp_[f"share_{k}"]).abs()
    print(f"   {k:3s}: n {len(cmp_)}, exact (<1e-6) {np.mean(dif < 1e-6):.3f}, within 0.01 {np.mean(dif < 0.01):.3f}, max diff {dif.max():.4f}")

# ---------------- B3. returns from the legacy CRSP daily file ----------------
print("[B3] holding-period returns recomputed from legacy crsp_a_stock.dsf (random sample, no delisting in period)")
smp = main[(~main.delisted_in_period) & main.R.notna()].sample(300, random_state=11)[["permno", "t0", "exit", "R"]].copy()
smp["permno"] = smp.permno.astype(int)
smp["t0s"] = pd.to_datetime(smp.t0).dt.strftime("%Y-%m-%d")
smp["exs"] = pd.to_datetime(smp["exit"]).dt.strftime("%Y-%m-%d")
con.register("s", smp[["permno", "t0s", "exs"]])
r = con.execute(f"""
  SELECT s.permno, s.t0s, s.exs, exp(sum(ln(1 + TRY_CAST(d.ret AS DOUBLE)))) - 1 AS R2, count(*) AS nd, sum(CASE WHEN TRY_CAST(d.ret AS DOUBLE) IS NULL THEN 1 ELSE 0 END) AS nmiss
  FROM read_csv('{DUMP}/crsp_a_stock.dsf.csv.gz', all_varchar=true, header=true, ignore_errors=true) d
  JOIN s ON TRY_CAST(d.permno AS INTEGER) = s.permno AND d.date > s.t0s AND d.date <= s.exs
  GROUP BY 1, 2, 3""").df()
m = smp.merge(r, on=["permno", "t0s", "exs"], how="left")
dif = (m.R - m.R2).abs()
print(f"   matched {int(m.R2.notna().sum())}/300; |diff| < 1e-4: {np.mean(dif[m.R2.notna()] < 1e-4):.3f}; max diff {dif.max():.5f}; rows with a missing daily return {int((m.nmiss > 0).sum())}")

# ---------------- C. interpretation (EXPLORATORY, post hoc) ----------------
print("[C] EXPLORATORY (post hoc) - where does the long-short return come from? Not used for the verdict.")
rel = sorted(main.release_date.unique())
Nx = Nr.loc[rel].copy()
exp_mean = Nx.expanding().mean().shift(1)            # real-time mean of each category before the release
full_mean = Nx.mean()
mm = main.merge(exp_mean.add_prefix("E_"), left_on="release_date", right_index=True, how="left")
mm["BT_static_full"] = sum(mm[f"sh2_{k}"].fillna(0) * (full_mean[f"N_{k}"] if mm[f"sh2_{k}"].notna().any() else 0) for k in CATS)
mm["BT_static_rt"] = sum(mm[f"sh2_{k}"].fillna(0) * mm[f"E_N_{k}"].fillna(0) for k in CATS)
mm["BT_dev_rt"] = mm.BT - mm.BT_static_rt
cross = Nx.sub(Nx.mean(axis=1), axis=0)             # category tightening relative to the cross-category average at that release
mm = mm.merge(cross.add_prefix("X_"), left_on="release_date", right_index=True, how="left")
mm["BT_rel"] = sum(mm[f"sh2_{k}"].fillna(0) * mm[f"X_N_{k}"].fillna(0) for k in CATS)
report("C1 static tilt: sort on CRE share only (long low CRE)", ls_series(mm, "share_CRE"), years)
report("C2 static tilt: shares x full-sample mean tightening", ls_series(mm, "BT_static_full"), years)
s_dev = ls_series(mm[mm.release_date >= rel[8]], "BT_dev_rt")
report("C3 timing part: BT minus shares x real-time mean tightening", s_dev, years)
# C4: BT quintile long-short inside CRE-share terciles (tercile-neutral)
parts = []
for p, g_ in mm.groupby("period"):
    g_ = g_.dropna(subset=["BT", "R"]).copy()
    g_["ter"] = pd.qcut(g_.share_CRE.rank(method="first"), 3, labels=False)
    v = []
    for _, h in g_.groupby("ter"):
        h = h.sort_values(["BT", "permno"], kind="mergesort")
        n = len(h)
        if n < 10:
            continue
        q = np.ceil(5 * (np.arange(n) + 1) / n).astype(int)
        v.append(h.R.values[q == 1].mean() - h.R.values[q == 5].mean())
    if v:
        parts.append((p, np.mean(v) * 100))
s_ter = pd.Series(dict(parts)).sort_index()
report("C4 BT quintile long-short within CRE-share terciles", s_ter, years)
# C5: residual of BT on the five shares, period by period
res = []
for p, g_ in mm.groupby("period"):
    g_ = g_.dropna(subset=["BT", "R"]).copy()
    Xs = sm.add_constant(g_[["share_CI", "share_CRE", "share_CC", "share_OC"]].fillna(0))
    g_["BT_res"] = sm.OLS(g_.BT, Xs).fit().resid
    res.append(g_[["period", "permno", "BT_res", "R"]])
s_res = ls_series(pd.concat(res), "BT_res")
report("C5 BT residual on raw shares (period-by-period)", s_res, years)
print(f"      (C5 residual variance share: BT explained by raw shares, median R2 over periods = "
      f"{np.median([sm.OLS(g_.dropna(subset=['BT']).BT, sm.add_constant(g_.dropna(subset=['BT'])[['share_CI','share_CRE','share_CC','share_OC']].fillna(0))).fit().rsquared for _, g_ in mm.groupby('period')]):.3f})")
# C6: influence of the crisis
yrs = years.reindex(s_main.index)
x = s_main[~yrs.isin([2008, 2009])]
print(f"   C6 primary excluding releases in 2008-2009: n {len(x)}, mean {x.mean():+.3f}%, t {nw_t(x.values)[1]:+.2f}")
top3 = s_main.sort_values(ascending=False).head(3)
x = s_main.drop(top3.index)
print(f"   C7 primary excluding its three largest periods ({', '.join(str(years[i]) for i in top3.index)}): mean {x.mean():+.3f}%, t {nw_t(x.values)[1]:+.2f}")
# C8: correlation of the primary long-short series with the static CRE tilt series
s_cre = ls_series(mm, "share_CRE")
print(f"   C8 correlation between primary long-short and static CRE-share long-short: {np.corrcoef(s_main, s_cre.reindex(s_main.index))[0, 1]:.3f}")
al = sm.OLS(s_main.values, sm.add_constant(s_cre.reindex(s_main.index).values)).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
print(f"      primary on static CRE tilt: beta {al.params[1]:.2f}, intercept {al.params[0]:+.3f}% (t {al.tvalues[0]:+.2f})")
