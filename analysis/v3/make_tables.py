"""Tables for the revised SLOOS paper (v3): loan-officer surveys and the cross-section of bank stock returns.

Inputs (read-only): phase4/ (2000-2024, pre-specified test S1), phase4b/ (1991-2000 pre-sample confirmation, 2025 record),
the FR Y-9C files in the WRDS dump (credit losses for the mechanism test M1, PHASE4C_SPEC.md).
Outputs: paper_v3/tables/*.csv and a printed summary. Definitions follow PHASE4_SPEC.md / PHASE4B_SPEC.md / PHASE4C_SPEC.md.
Run: python make_tables.py
"""
import os
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
S = Path(os.environ.get("SLOOS_V3_WORK", str(HERE.parents[1] / "data" / "v3_work")))   # working directory with phase4/ and phase4b/
OUT = HERE / "tables"
OUT.mkdir(exist_ok=True)
DUMP = os.environ.get("WRDS_DUMP_DIR", str(HERE.parents[1] / "data" / "wrds_dump")).replace("\\", "/").rstrip("/")
CATS = ["CI", "CRE", "RRE", "CC", "OC"]


def nw_mean(x, lag=1):
    x = np.asarray(x, float)
    f = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return f.params[0], f.tvalues[0]


def ts_reg(y, X, lag=1):
    f = sm.OLS(np.asarray(y, float), sm.add_constant(np.asarray(X, float))).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return f


def quintile(g, col):
    g = g.dropna(subset=[col, "R"]).sort_values([col, "permno"], kind="mergesort")
    n = len(g)
    return g.assign(q=np.ceil(5 * (np.arange(n) + 1) / n).astype(int))


# ---------------------------------------------------------------- data
b00 = pd.read_parquet(S / "phase4" / "out" / "s1_bank_table.parquet")
b00 = b00[b00.screen & b00.R.notna()].copy()
N = pd.read_csv(S / "phase4" / "out" / "s1_N_by_release.csv", parse_dates=["fred_date", "release_date"])
Nrel = N.dropna(subset=["release_date"]).set_index("release_date")[[f"N_{k}" for k in CATS]]
b00 = b00.merge(Nrel, left_on="release_date", right_index=True, how="left")
b00["sample"] = "2000-2024"
b90 = pd.read_parquet(S / "phase4b" / "out" / "h1h2_1990s_bank_table.parquet")
b90 = b90[b90.screen.astype(bool) & b90.R.notna()].copy()
p90 = pd.read_csv(S / "phase4b" / "out" / "h1h2_1990s_periods.csv")
b90 = b90.merge(p90[["period"] + [f"N_{k}" for k in CATS]], on="period", how="left")
b90["sample"] = "1991-2000"
b90["release_key"] = pd.to_datetime(b90.t0)          # entry date identifies the release (1990-96 release dates are approximate)
b00["release_key"] = pd.to_datetime(b00.t0)
for d in (b00, b90):
    d["share_CONSUMER"] = d[["share_CC", "share_OC"]].sum(axis=1, min_count=1)
if "share_CONS" in b90:
    b90["share_CONSUMER"] = b90.share_CONSUMER.fillna(b90.share_CONS)
keep = ["sample", "release_key", "year", "permno", "rssd9001", "y9c_date", "share_CI", "share_CRE", "share_RRE", "share_CONSUMER",
        "BT", "R", "cap_t0", "N_CI", "N_CRE", "N_RRE", "N_CC", "N_OC"]
P = pd.concat([b90[keep], b00[keep + ["share_CC", "share_OC", "logcap", "bm", "mom12"]]], ignore_index=True)
rk = {d: i for i, d in enumerate(sorted(P.release_key.unique()))}
P["pid"] = P.release_key.map(rk)
P["Rp"] = P.R * 100
rel = P.groupby("pid").agg(sample=("sample", "first"), release=("release_key", "first"), year=("year", "first"),
                           N_CRE=("N_CRE", "first"), N_CI=("N_CI", "first"), n=("permno", "size")).reset_index()
print(f"releases: pre-sample {int((rel['sample'] == '1991-2000').sum())}, main {int((rel['sample'] == '2000-2024').sum())}; bank-release obs {len(P)}")

# ---------------------------------------------------------------- T1 summary
rows = []
for s, g in P.groupby("sample"):
    r = rel[rel["sample"] == s]
    rows.append(dict(sample=s, releases=len(r), first=str(r.release.min().date()), last=str(r.release.max().date()), banks_per_release=round(g.groupby("pid").size().mean(), 1),
                     banks_min=int(g.groupby("pid").size().min()), banks_max=int(g.groupby("pid").size().max()), distinct_banks=g.rssd9001.nunique(),
                     share_CI=g.share_CI.mean(), share_CRE=g.share_CRE.mean(), share_RRE=g.share_RRE.mean(), share_consumer=g.share_CONSUMER.mean(),
                     cre_p10=g.share_CRE.quantile(.1), cre_p90=g.share_CRE.quantile(.9), mktcap_median_musd=g.cap_t0.median() / 1e6,
                     N_CRE_mean=r.N_CRE.mean(), N_CRE_sd=r.N_CRE.std(), N_CRE_min=r.N_CRE.min(), N_CRE_max=r.N_CRE.max(), N_CI_mean=r.N_CI.mean(), N_CI_sd=r.N_CI.std()))
T1 = pd.DataFrame(rows)
T1.to_csv(OUT / "T1_summary.csv", index=False)
print("\n[T1]\n", T1.round(3).T.to_string())

# ---------------------------------------------------------------- T2 pre-specified exposure sort
Q = pd.concat([quintile(g, "BT") for _, g in P.groupby("pid")])
qm = Q.groupby(["pid", "q"]).Rp.mean().unstack("q")
qm["LS"] = qm[1] - qm[5]
qm = qm.join(rel.set_index("pid")[["sample", "year"]])


def t2row(label, d):
    out = dict(sample=label, n=len(d))
    for q in range(1, 6):
        out[f"Q{q}"] = d[q].mean()
    m, t = nw_mean(d.LS.values)
    out.update(LS=m, t=t, share_pos=float((d.LS > 0).mean()))
    return out


T2 = pd.DataFrame([t2row("2000-2024 (pre-specified test)", qm[qm["sample"] == "2000-2024"]),
                   t2row("  2000-2011", qm[(qm["sample"] == "2000-2024") & (qm.year <= 2011)]),
                   t2row("  2012-2024", qm[(qm["sample"] == "2000-2024") & (qm.year >= 2012)]),
                   t2row("1991-2000 (pre-sample)", qm[qm["sample"] == "1991-2000"]),
                   t2row("1991-2024 (pooled)", qm)])
T2.to_csv(OUT / "T2_exposure_sort.csv", index=False)
print("\n[T2] mean return per release-to-release period, % (Q1 = lowest exposure to tightening)\n", T2.round(3).to_string(index=False))

# ---------------------------------------------------------------- T3 CRE channel, time series
C = pd.concat([quintile(g, "share_CRE") for _, g in P.groupby("pid")])
cm = C.groupby(["pid", "q"]).Rp.mean().unstack("q")
ts = pd.DataFrame({"spread": cm[1] - cm[5]}).join(rel.set_index("pid"))
ts["x"] = ts.N_CRE / 10
ts["spread_lag"] = ts.spread.shift(1)
ts["x_lag"] = ts.x.shift(1)
ts.to_csv(OUT / "series_cre_spread.csv")
rows = []


def t3(label, d, cols):
    f = ts_reg(d.spread, d[cols])
    r = dict(spec=label, n=len(d), r2=f.rsquared, intercept=f.params[0], t_intercept=f.tvalues[0])
    for i, c in enumerate(cols):
        r[f"b_{c}"] = f.params[i + 1]
        r[f"t_{c}"] = f.tvalues[i + 1]
    rows.append(r)


main, pre = ts[ts["sample"] == "2000-2024"], ts[ts["sample"] == "1991-2000"]
t3("(1) 2000-2024, discovery", main, ["x"])
t3("(2) 1991-2000, pre-specified confirmation", pre, ["x"])
t3("(3) 1991-2024 pooled", ts, ["x"])
t3("(4) pooled, excl. 1991-92 and 2008-09", ts[~ts.year.isin([1991, 1992, 2008, 2009])], ["x"])
t3("(5) pooled, controlling for the previous spread", ts.dropna(subset=["spread_lag"]), ["x", "spread_lag"])
t3("(6) pooled, tightening of the previous survey", ts.dropna(subset=["x_lag"]), ["x_lag"])
t3("(7) 2012-2024", main[main.year >= 2012], ["x"])
T3 = pd.DataFrame(rows)
T3.to_csv(OUT / "T3_cre_timeseries.csv", index=False)
print("\n[T3] spread (low-CRE minus high-CRE quintile, % per period) on released net CRE tightening (per 10pp)\n", T3.round(3).to_string(index=False))
hi = ts[ts.N_CRE > ts.N_CRE.median()]
lo = ts[ts.N_CRE <= ts.N_CRE.median()]
print(f"     descriptive split at the pooled median of N_CRE ({ts.N_CRE.median():.1f}): above {hi.spread.mean():+.2f}% (n {len(hi)}), at or below {lo.spread.mean():+.2f}% (n {len(lo)})")


# ---------------------------------------------------------------- T4 bank-level panel
def panel(df, xcols, keep_show, label, cluster2=None):
    d = df.dropna(subset=["Rp"] + xcols).copy()
    W = d[["Rp"] + xcols] - d.groupby("pid")[["Rp"] + xcols].transform("mean")
    f = sm.OLS(W.Rp, W[xcols]).fit(cov_type="cluster", cov_kwds={"groups": d.pid.values, "use_correction": True})
    r = dict(spec=label, obs=len(d), releases=d.pid.nunique())
    for c in keep_show:
        r[f"b_{c}"] = f.params[c]
        r[f"t_{c}"] = f.tvalues[c]
    return r


for k in CATS:
    P[f"I_{k}"] = np.nan
m00 = P["sample"] == "2000-2024"
for k in CATS:
    mu00 = P.loc[m00].groupby("pid")[f"N_{k}"].first().mean()
    sh = {"CI": "share_CI", "CRE": "share_CRE", "RRE": "share_RRE", "CC": "share_CC", "OC": "share_OC"}[k]
    P.loc[m00, f"I_{k}"] = P.loc[m00, sh] * (P.loc[m00, f"N_{k}"] - mu00).fillna(0) / 10
m90 = P["sample"] == "1991-2000"
for k in ("CI", "CRE"):
    mu90 = P.loc[m90].groupby("pid")[f"N_{k}"].first().mean()
    P.loc[m90, f"I_{k}"] = P.loc[m90, f"share_{k}"] * (P.loc[m90, f"N_{k}"] - mu90) / 10
rows = []
sh4 = ["share_CI", "share_CRE", "share_CC", "share_OC"]
sh3 = ["share_CI", "share_CRE", "share_CONSUMER"]
rows.append(panel(P[m00], ["I_CI", "I_CRE", "I_RRE", "I_CC", "I_OC"] + sh4, ["I_CI", "I_CRE", "I_RRE", "I_CC", "I_OC"], "(1) 2000-2024, five categories"))
rows.append(panel(P[m00], ["I_CI", "I_CRE"] + sh4 + ["logcap", "bm", "mom12"], ["I_CI", "I_CRE"], "(2) 2000-2024, CRE and C&I + size, B/M, momentum"))
rows.append(panel(P[m90], ["I_CI", "I_CRE"] + sh3, ["I_CI", "I_CRE"], "(3) 1991-2000, CRE and C&I"))
rows.append(panel(P, ["I_CI", "I_CRE"] + sh3, ["I_CI", "I_CRE"], "(4) 1991-2024 pooled, CRE and C&I"))
rows.append(panel(P[~P.year.isin([1991, 1992, 2008, 2009])], ["I_CI", "I_CRE"] + sh3, ["I_CI", "I_CRE"], "(5) pooled, excl. 1991-92 and 2008-09"))
T4 = pd.DataFrame(rows)
T4.to_csv(OUT / "T4_panel.csv", index=False)
print("\n[T4] bank-level panel, release fixed effects, clustered by release; coefficient = % per (loan share 1.0 x 10pp tightening above its mean)\n", T4.round(3).to_string(index=False))

# ---------------------------------------------------------------- T5 mechanism M1 (PHASE4C_SPEC)
con = duckdb.connect()
con.execute("SET memory_limit='6GB'")
ids = b00[["rssd9001"]].drop_duplicates().assign(rssd9001=lambda d: d.rssd9001.astype(int).astype(str))
con.register("ids", ids)
a = con.execute(f"""SELECT t.rssd9001, t.rssd9999 d, max(TRY_CAST(t.bhck4635 AS DOUBLE)) co FROM read_csv('{DUMP}/bank_all.wrds_holding_bhck_1.csv.gz', all_varchar=true, header=true, ignore_errors=true) t
                    JOIN ids ON ids.rssd9001 = t.rssd9001 GROUP BY 1, 2""").df()
c2 = con.execute(f"""SELECT t.rssd9001, t.rssd9999 d, max(TRY_CAST(t.bhck4605 AS DOUBLE)) rec, max(TRY_CAST(t.bhck4230 AS DOUBLE)) prov, max(TRY_CAST(t.bhck2122 AS DOUBLE)) loans
                     FROM read_csv('{DUMP}/bank_all.wrds_holding_bhck_2.csv.gz', all_varchar=true, header=true, ignore_errors=true) t
                     JOIN ids ON ids.rssd9001 = t.rssd9001 GROUP BY 1, 2""").df()
y = a.merge(c2, on=["rssd9001", "d"], how="outer")
y["d"] = pd.to_datetime(y.d)
y["rssd9001"] = y.rssd9001.astype(int)
y = y.sort_values(["rssd9001", "d"])
y["nco_ytd"] = y.co - y.rec
y["yr"] = y.d.dt.year
for v in ("nco_ytd", "prov"):
    prev = y.groupby(["rssd9001", "yr"])[v].shift(1)
    gap_ok = (y.d - y.groupby(["rssd9001", "yr"]).d.shift(1)).dt.days.between(85, 95)
    y[v + "_q"] = np.where(y.d.dt.quarter == 1, y[v], np.where(gap_ok, y[v] - prev, np.nan))
flows = y.set_index(["rssd9001", "d"])[["nco_ytd_q", "prov_q"]]
qends = pd.DatetimeIndex(sorted(y.d.unique()))
M = b00[["period", "release_date", "year", "rssd9001", "y9c_date", "share_CI", "share_CRE", "share_CC", "share_OC", "N_CRE", "bhck2122"]].copy()
M["rssd9001"] = M.rssd9001.astype(int)
M["release_date"] = pd.to_datetime(M.release_date)
nxt = {r: list(qends[qends > r][:4]) for r in M.release_date.unique()}
vals = {k: [] for k in ("nco4", "prov4")}
for rid, r in zip(M.rssd9001.values, M.release_date.values):
    qs = nxt[pd.Timestamp(r)]
    if len(qs) < 4 or qs[-1] > pd.Timestamp("2024-12-31"):
        vals["nco4"].append(np.nan); vals["prov4"].append(np.nan); continue
    try:
        f4 = flows.loc[[(rid, q) for q in qs]]
        vals["nco4"].append(f4.nco_ytd_q.sum(min_count=4)); vals["prov4"].append(f4.prov_q.sum(min_count=4))
    except KeyError:
        vals["nco4"].append(np.nan); vals["prov4"].append(np.nan)
M["nco4"] = np.array(vals["nco4"]) / M.bhck2122 * 100
M["prov4"] = np.array(vals["prov4"]) / M.bhck2122 * 100
M = M.dropna(subset=["nco4", "prov4"])
for v in ("nco4", "prov4"):
    lo_, hi_ = M[v].quantile([.005, .995])
    M[v] = M[v].clip(lo_, hi_)
M["I_CRE"] = M.share_CRE * (M.N_CRE - M.groupby("period").N_CRE.first().mean()) / 10


def twoway(df, yv, xcols, show, fe_bank=False):
    d = df.dropna(subset=[yv] + xcols).copy()
    cols = [yv] + xcols
    W = d[cols] - d.groupby("period")[cols].transform("mean")
    if fe_bank:
        for _ in range(8):
            W = W - W.groupby(d.rssd9001.values)[cols].transform("mean")
            W = W - W.groupby(d.period.values)[cols].transform("mean")
    X, Y = W[xcols].values, W[yv].values
    beta = np.linalg.lstsq(X, Y, rcond=None)[0]
    u = Y - X @ beta
    XtXi = np.linalg.inv(X.T @ X)

    def meat(g):
        Sg = pd.DataFrame(X * u[:, None]).groupby(g).sum().values
        G = len(Sg)
        return (G / (G - 1)) * Sg.T @ Sg
    g1, g2 = d.period.values, d.rssd9001.values
    g12 = pd.factorize(pd.Series(g1).astype(str) + "_" + pd.Series(g2).astype(str))[0]
    V = XtXi @ (meat(g1) + meat(g2) - meat(g12)) @ XtXi
    se = np.sqrt(np.diag(V))
    i = xcols.index(show)
    return dict(obs=len(d), releases=d.period.nunique(), banks=d.rssd9001.nunique(), b=beta[i], t=beta[i] / se[i], mean_y=d[yv].mean())


rows = []
for yv, lab in [("nco4", "net charge-offs, next 4 quarters / loans (%)"), ("prov4", "loan-loss provisions, next 4 quarters / loans (%)")]:
    rows.append(dict(outcome=lab, spec="release FE + loan shares", **twoway(M, yv, ["I_CRE", "share_CI", "share_CRE", "share_CC", "share_OC"], "I_CRE")))
    rows.append(dict(outcome=lab, spec="release FE + bank FE + loan shares", **twoway(M, yv, ["I_CRE", "share_CI", "share_CRE", "share_CC", "share_OC"], "I_CRE", fe_bank=True)))
T5 = pd.DataFrame(rows)
T5.to_csv(OUT / "T5_mechanism.csv", index=False)
print("\n[T5] mechanism M1: coefficient on CRE share x (net CRE tightening - mean)/10; two-way clustered (release, bank)\n", T5.round(4).to_string(index=False))
print(f"     interpretation: for a bank with CRE share {M.share_CRE.quantile(.9):.2f} (p90) vs {M.share_CRE.quantile(.1):.2f} (p10), a 10pp higher reading changes the outcome by b x {M.share_CRE.quantile(.9) - M.share_CRE.quantile(.1):.2f}")

# ---------------------------------------------------------------- T6 implementation
ag = pd.read_csv(S / "phase4" / "out" / "s1_ls_periods.csv")
rows = []
for lab, col in [("equal-weighted (pre-specified)", "LS"), ("value-weighted", "LS_VW"), ("no price / size filter", "LS_nofilter"),
                 ("net of costs, turnover-based", "LS_net_turnover"), ("net of costs, full round trip each period", "LS_net_fullrt")]:
    m_, t_ = nw_mean(ag[col].values)
    rows.append(dict(sample="2000-2024", version=lab, n=len(ag), mean=m_, t=t_))
x = ag[~ag.year.isin([2008, 2009])].LS.values
rows.append(dict(sample="2000-2024", version="equal-weighted, excluding releases in 2008-2009", n=len(x), mean=nw_mean(x)[0], t=nw_mean(x)[1]))
loo = [nw_mean(ag[ag.year != yv].LS.values)[1] for yv in sorted(ag.year.unique())]
rows.append(dict(sample="2000-2024", version=f"leave-one-year-out t range", n=len(ag), mean=np.nan, t=np.nan, note=f"{min(loo):.2f} to {max(loo):.2f}"))
# pre-sample value-weighted
vw = []
for pid, g in Q[Q.pid.isin(rel[rel["sample"] == "1991-2000"].pid)].groupby("pid"):
    w = lambda h: np.average(h.Rp, weights=h.cap_t0) if h.cap_t0.notna().all() and h.cap_t0.sum() > 0 else np.nan
    vw.append(w(g[g.q == 1]) - w(g[g.q == 5]))
vw = np.array(vw)
rows.append(dict(sample="1991-2000", version="equal-weighted", n=int((qm["sample"] == "1991-2000").sum()), mean=nw_mean(qm[qm["sample"] == "1991-2000"].LS.values)[0], t=nw_mean(qm[qm["sample"] == "1991-2000"].LS.values)[1]))
rows.append(dict(sample="1991-2000", version="value-weighted", n=int(np.isfinite(vw).sum()), mean=nw_mean(vw[np.isfinite(vw)])[0], t=nw_mean(vw[np.isfinite(vw)])[1]))
pool = qm.LS.values
rows.append(dict(sample="1991-2024", version="equal-weighted, pooled", n=len(pool), mean=nw_mean(pool)[0], t=nw_mean(pool)[1]))
T6 = pd.DataFrame(rows)
T6.to_csv(OUT / "T6_implementation.csv", index=False)
print("\n[T6] exposure long-short, % per period\n", T6.round(3).to_string(index=False))
ann = (1 + qm.LS / 100).prod() ** (1 / ((rel.release.max() - rel.release.min()).days / 365.25)) - 1
print(f"     pooled equal-weighted long-short: compound {ann * 100:.2f}% per year before costs over {((rel.release.max() - rel.release.min()).days / 365.25):.1f} years; "
      f"per-period sd {qm.LS.std():.2f}%, annualised Sharpe approx {qm.LS.mean() / qm.LS.std() * np.sqrt(len(qm) / ((rel.release.max() - rel.release.min()).days / 365.25)):.2f}")
p25 = pd.read_csv(S / "phase4b" / "out" / "post2025_periods.csv")
p25 = p25[p25.universe == "main"][["release_date", "t0", "exit", "n", "LS_BT", "LS_CRE", "N_CRE"]]
p25.to_csv(OUT / "T6b_record_2025.csv", index=False)
print("\n[T6b] post-sample record (no test)\n", p25.round(2).to_string(index=False))
qm.to_csv(OUT / "series_exposure_quintiles.csv")
rel.to_csv(OUT / "releases.csv", index=False)
