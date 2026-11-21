# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / S1 - category tightening x bank loan mix -> bank-stock cross-section (primary test 1). Implements FROZEN_PARAMS S1.

Outputs: out/s1_bank_table.parquet, out/s1_ls_periods.csv, out/s1_ls_monthly.csv, out/s1_counts.csv, out/s1_fm_coefs.csv,
         out/results_s1.csv (test_id, sample, stat, value)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import time
import numpy as np
import pandas as pd
import statsmodels.api as sm
import scipy.stats as st
from p4lib import *

t_ = time.time()
log = lambda *a: print(f"[{time.time() - t_:5.0f}s]", *a, flush=True)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
res = Results()

cal = us_calendar(); calv = days(cal)
N = pd.read_csv(O + "s1_N_by_release.csv", parse_dates=["fred_date", "release_date"])
Y = pd.read_parquet(C + "y9c_panel.parquet")
Y["date"] = pd.to_datetime(Y.date)
Yd = {k: g.set_index("date").sort_index() for k, g in Y.groupby("rssd9001")}
lk = pd.read_parquet(C + "link.parquet")
lk = lk[lk.inst_type.str.lower() == "bank holding company"].copy()
lk["dt_start"] = pd.to_datetime(lk.dt_start); lk["dt_end"] = pd.to_datetime(lk.dt_end)
lk["dt_end_open"] = lk.dt_end.where(lk.dt_end < lk.dt_end.max(), pd.Timestamp("2099-12-31"))
dn = pd.read_parquet(C + "dsenames.parquet")
dn["namedt"] = pd.to_datetime(dn.namedt); dn["nameendt"] = pd.to_datetime(dn.nameendt)
cs = dn[dn.shrcd.isin([10, 11]) & dn.exchcd.isin([1, 2, 3])]
idx, px, dlr = us_index()
log("index rows", len(idx.keys), "price rows", len(px.keys), "delisting records", len(dlr))


def qstar(r):
    """latest calendar quarter-end q with (r - q) >= 75 days"""
    lim = pd.Timestamp(r) - pd.Timedelta(days=75)
    q = (lim + pd.offsets.QuarterEnd(0)).normalize()
    if q > lim:
        q = (q - pd.offsets.QuarterEnd(1)).normalize()
    return q


# ---------------------------------------------------------------- releases and periods
rel = N[N.release_date.notna()].sort_values("release_date").reset_index(drop=True)
rel["qstar"] = rel.release_date.map(qstar)
rel = rel[(rel.qstar >= pd.Timestamp("2000-03-31")) & (rel.release_date <= US_END)].reset_index(drop=True)
rel["i_t0"] = rel.release_date.map(lambda d: first_after(cal, d))
rel["t0"] = cal[rel.i_t0.values]
rel["exit"] = list(rel.t0.iloc[1:]) + [pd.NaT]
rel["i_exit"] = list(rel.i_t0.iloc[1:]) + [-1]
per = rel[rel.exit.notna() & (rel.exit <= US_END)].reset_index(drop=True)
log("S1 rebalance releases", len(rel), "complete periods", len(per), per.release_date.min().date(), "..", per.release_date.max().date(),
    "| skipped (no exact date) quarters between rebalances:",
    int(((per.fred_date.shift(-1) - per.fred_date).dt.days > 100).sum()))
assert all((per.qstar + pd.Timedelta(days=75)) <= per.release_date)
assert all(per.t0 > per.release_date)


# ---------------------------------------------------------------- universe and signal per release
def y9c_at(rssd, q):
    g = Yd.get(rssd)
    if g is None:
        return None
    if q in g.index:
        return q
    z = g.index[(g.index < q) & (g.index >= q - pd.Timedelta(days=183))]
    return z.max() if len(z) else None


rows, cnt = [], []
for p, e in per.iterrows():
    r = e.release_date; ir = last_on_before(cal, r); it0 = int(e.i_t0); ix = int(e.i_exit)
    L = lk[(lk.dt_start <= r) & (lk.dt_end_open >= r)][["rssd9001", "permco"]].drop_duplicates()
    S = cs[(cs.namedt <= r) & (cs.nameendt >= r)][["permno", "permco"]].drop_duplicates()
    c = L.merge(S, on="permco")
    n_link = L.rssd9001.nunique()
    _, prc = px.lookup(c.permno, calv[ir], "prc", stale_min=calv[ir - 5])
    _, cap = px.lookup(c.permno, calv[ir], "cap", stale_min=calv[ir - 5])
    c["prc_r"] = prc; c["cap_r"] = cap
    c = c[np.isfinite(c.cap_r) & (c.cap_r > 0)]
    c = c.sort_values(["rssd9001", "permco", "cap_r"], ascending=[True, True, False]).drop_duplicates(["rssd9001", "permco"])
    c = c.sort_values(["rssd9001", "cap_r"], ascending=[True, False]).drop_duplicates("rssd9001")
    n_cs = len(c)
    q = e.qstar
    c["y9c_date"] = [y9c_at(int(x), q) for x in c.rssd9001]
    c = c[c.y9c_date.notna()].copy()
    c["y9c_date"] = pd.to_datetime(c.y9c_date)
    yy = Y.merge(c[["rssd9001", "y9c_date"]], left_on=["rssd9001", "date"], right_on=["rssd9001", "y9c_date"])
    c = c.merge(yy.drop(columns=["date"]), on=["rssd9001", "y9c_date"])
    c = c.sort_values(["permco", "bhck2170"], ascending=[True, False]).drop_duplicates("permco")
    n_y9 = len(c)
    # signal
    Nk = {k: e[f"N_{k}"] for k in CATS}
    avail = [k for k in CATS if np.isfinite(Nk[k])]
    ssum = c[[f"share_{k}" for k in avail]].sum(axis=1)
    c = c[ssum > 0].copy(); ssum = ssum[ssum > 0]
    for k in CATS:
        c[f"sh2_{k}"] = (c[f"share_{k}"] / ssum) if k in avail else 0.0
    c["BT"] = sum(c[f"sh2_{k}"] * Nk[k] for k in avail)
    c["avail"] = ",".join(avail)
    # entry / exit
    rec0, lv0 = idx.lookup(c.permno, calv[it0], "lv", stale_min=calv[it0 - 5])
    _, prc0 = px.lookup(c.permno, calv[it0], "prc", stale_min=calv[it0 - 5])
    _, cap0 = px.lookup(c.permno, calv[it0], "cap", stale_min=calv[it0 - 5])
    _, bid0 = px.lookup(c.permno, calv[it0], "bid", stale_min=calv[it0 - 5])
    _, ask0 = px.lookup(c.permno, calv[it0], "ask", stale_min=calv[it0 - 5])
    _, lvx = idx.lookup(c.permno, calv[ix], "lv")
    recx_p, prcx = px.lookup(c.permno, calv[ix], "prc", stale_min=calv[ix - 5])
    _, bidx = px.lookup(c.permno, calv[ix], "bid", stale_min=calv[ix - 5])
    _, askx = px.lookup(c.permno, calv[ix], "ask", stale_min=calv[ix - 5])
    i12 = it0 - 252
    _, lvm = idx.lookup(c.permno, calv[i12], "lv", stale_min=calv[i12 - 5]) if i12 - 5 >= 0 else (None, np.full(len(c), np.nan))
    c["lv_entry"] = lv0; c["prc_t0"] = prc0; c["cap_t0"] = cap0
    c["hs_entry"] = half_spread(bid0, ask0); c["hs_exit"] = half_spread(bidx, askx)
    c["live_at_exit"] = np.isfinite(prcx)
    c["R"] = np.exp(lvx - lv0) - 1.0
    c["mom12"] = np.exp(lv0 - lvm) - 1.0
    c = c[np.isfinite(c.lv_entry) & np.isfinite(c.R) & np.isfinite(c.prc_t0)].copy()
    # delisting inside the period
    dd = dlr[(dlr.date > cal[it0]) & (dlr.date <= cal[ix])]
    c["delisted_in_period"] = c.permno.isin(set(dd.permno))
    # loan growth 12 quarters
    lg = []
    for rs, qd, l0 in zip(c.rssd9001, c.y9c_date, c.bhck2122):
        g = Yd.get(int(rs)); q12 = (qd - pd.offsets.QuarterEnd(12)).normalize()
        v = g.bhck2122.get(q12, np.nan) if g is not None else np.nan
        lg.append(np.log(l0 / v) if (np.isfinite(v) and v > 0 and l0 > 0) else np.nan)
    c["loan_g3"] = lg
    c["bm"] = np.where(c.book > 0, c.book * 1000.0 / c.cap_t0, np.nan)
    c["logcap"] = np.log(c.cap_t0 / 1e6)
    c["screen"] = (c.prc_r >= 5) & (c.cap_r >= 100e6)
    c["period"] = p; c["release_date"] = r; c["fred_date"] = e.fred_date; c["t0"] = cal[it0]; c["exit"] = cal[ix]
    c["year"] = r.year
    for u, m in [("main", c.screen), ("nofilter", np.ones(len(c), bool))]:
        z = c[m].sort_values(["BT", "permno"])
        n = len(z)
        qv = np.ceil(5 * np.arange(1, n + 1) / n).astype(int) if n else np.array([], int)
        c.loc[z.index, f"q_{u}"] = qv
    rows.append(c)
    cnt.append(dict(period=p, release_date=r.date(), year=r.year, qstar=q.date(), n_link_rssd=n_link, n_common=n_cs, n_y9c=n_y9,
                    n_signal_entry=len(c), n_main=int(c.screen.sum()), n_main_q1=int((c.q_main == 1).sum()), n_main_q5=int((c.q_main == 5).sum()),
                    n_delisted_in_period=int(c.delisted_in_period.sum()), avail=",".join(avail)))
B = pd.concat(rows, ignore_index=True)
CNT = pd.DataFrame(cnt)
CNT.to_csv(O + "s1_counts.csv", index=False)
keep_cols = ["period", "release_date", "fred_date", "t0", "exit", "year", "permno", "permco", "rssd9001", "y9c_date"] + \
            [f"share_{k}" for k in CATS] + [f"sh2_{k}" for k in CATS] + \
            ["avail", "BT", "q_main", "q_nofilter", "screen", "R", "prc_r", "cap_r", "prc_t0", "cap_t0", "hs_entry", "hs_exit", "live_at_exit",
             "delisted_in_period", "logcap", "bm", "mom12", "loan_g3", "bhck2170", "bhck2122", "book"]
B[keep_cols].to_parquet(O + "s1_bank_table.parquet", index=False)
log("bank table rows", len(B), "periods", B.period.nunique())
print(CNT.groupby("year")[["n_link_rssd", "n_common", "n_y9c", "n_signal_entry", "n_main", "n_main_q1", "n_main_q5", "n_delisted_in_period"]]
      .mean().round(1).to_string())
small = CNT[CNT.n_main < 25]
log("periods with n_main < 25 (dropped):", len(small))
assert np.allclose(B[[f"share_{k}" for k in CATS]].sum(axis=1), 1.0)
assert np.allclose(B[[f"sh2_{k}" for k in CATS]].sum(axis=1), 1.0)


# ---------------------------------------------------------------- L/S per period
def legs(df, qcol, w=None):
    out = []
    for p, g in df.groupby("period"):
        g = g[g[qcol].notna()]
        if len(g) < 25:
            continue
        lo = g[g[qcol] == 1]; hi = g[g[qcol] == 5]
        if w is None:
            rl, rh = lo.R.mean(), hi.R.mean()
        else:
            rl = np.average(lo.R, weights=lo[w]); rh = np.average(hi.R, weights=hi[w])
        out.append(dict(period=p, release_date=g.release_date.iloc[0], year=g.year.iloc[0], t0=g.t0.iloc[0], exit=g.exit.iloc[0],
                        n=len(g), n_long=len(lo), n_short=len(hi), R_long=rl * 100, R_short=rh * 100, LS=(rl - rh) * 100,
                        R_all=(g.R.mean() * 100)))
    return pd.DataFrame(out)


EW = legs(B, "q_main"); VW = legs(B[B.cap_t0 > 0], "q_main", w="cap_t0"); NF = legs(B, "q_nofilter")


def report(tid, d, col="LS", sign=+1, verdict_on=True):
    a = nw_mean(d[col], 1)
    h1 = nw_mean(d.loc[d.year <= 2011, col], 1); h2 = nw_mean(d.loc[d.year >= 2012, col], 1)
    v = verdict(a["t"], [h1["mean"], h2["mean"]], sign=sign) if verdict_on else "reported only"
    crit_exact = float(st.t.ppf(1 - 0.0125, a["n"] - 1))
    res.add(tid, "2000-2024", n=a["n"], mean_pct=a["mean"], t_nw1=a["t"], crit_exact_df=crit_exact, verdict=v)
    res.add(tid, "2000-2011", n=h1["n"], mean_pct=h1["mean"], t_nw1=h1["t"])
    res.add(tid, "2012-2024", n=h2["n"], mean_pct=h2["mean"], t_nw1=h2["t"])
    log(f"{tid}: n={a['n']} mean={a['mean']:+.3f}% t={a['t']:+.2f} | 2000-11 {h1['mean']:+.3f} (t {h1['t']:+.2f}, n {h1['n']}) | "
        f"2012-24 {h2['mean']:+.3f} (t {h2['t']:+.2f}, n {h2['n']}) | verdict: {v}")
    return a


report("S1_main_EW", EW)
report("S1_VW", VW, verdict_on=False)
report("S1_nofilter_EW", NF, verdict_on=False)
for nm, d in [("S1_main_EW_long_leg", EW.assign(LS=EW.R_long)), ("S1_main_EW_short_leg", EW.assign(LS=EW.R_short))]:
    report(nm, d, verdict_on=False)

# ---------------------------------------------------------------- costs (main EW)
cost_rows = []
prev = {}
mainB = B[B.q_main.isin([1, 5])].copy()
plist = sorted(EW.period)
for j, p in enumerate(plist):
    g = mainB[mainB.period == p]
    row = dict(period=p)
    for leg, qq in [("L", 1), ("S", 5)]:
        x = g[g.q_main == qq].copy()
        n = len(x)
        hs_in = fill_hs(x.hs_entry.to_numpy())
        w_new = pd.Series(1.0 / n, index=x.permno.values)
        hsd = pd.Series(hs_in, index=x.permno.values)
        old = prev.get(leg)
        if old is None:
            to_cost = float((w_new * hsd).sum()); turn = 1.0
        else:
            wo = old["w_drift_live"]  # live names at the rebalance close (index = permno)
            allp = w_new.index.union(wo.index)
            dw = (w_new.reindex(allp).fillna(0) - wo.reindex(allp).fillna(0)).abs()
            hs_all = hsd.reindex(allp)
            hs_all = hs_all.fillna(pd.Series(old["hs_exit"], index=wo.index).reindex(allp))
            hs_all = hs_all.fillna(np.nanmedian(hs_all) if np.isfinite(hs_all).any() else 0.0025)
            to_cost = float((dw * hs_all).sum()); turn = float(dw.sum())
        # drifted weights at this period's exit
        wd = (1.0 / n) * (1 + x.R.to_numpy()) / (1 + x.R.mean())
        live = x.live_at_exit.to_numpy()
        hs_out = fill_hs(x.hs_exit.to_numpy())
        prev[leg] = dict(w_drift_live=pd.Series(wd[live], index=x.permno.values[live]), hs_exit=hs_out[live])
        full_rt = float(np.mean(hs_in) + np.sum(wd[live] * hs_out[live]))
        row[f"to_cost_{leg}"] = to_cost * 100; row[f"turnover_{leg}"] = turn; row[f"fullrt_cost_{leg}"] = full_rt * 100
        if j == len(plist) - 1:
            row[f"to_cost_{leg}"] += float(np.sum(wd[live] * hs_out[live])) * 100
    e = EW[EW.period == p].iloc[0]
    row["borrow_S"] = 1.0 * (pd.Timestamp(e.exit) - pd.Timestamp(e.t0)).days / 365.0  # 1%/yr in % units
    cost_rows.append(row)
CO = pd.DataFrame(cost_rows)
EW = EW.merge(CO, on="period")
EW["LS_net_turnover"] = EW.LS - EW.to_cost_L - EW.to_cost_S - EW.borrow_S
EW["LS_net_fullrt"] = EW.LS - EW.fullrt_cost_L - EW.fullrt_cost_S - EW.borrow_S
report("S1_main_EW_net_turnover", EW, col="LS_net_turnover", verdict_on=False)
report("S1_main_EW_net_fullroundtrip", EW, col="LS_net_fullrt", verdict_on=False)
log("mean costs per period (%): turnover L/S", round(EW.to_cost_L.mean(), 3), round(EW.to_cost_S.mean(), 3), "full rt L/S",
    round(EW.fullrt_cost_L.mean(), 3), round(EW.fullrt_cost_S.mean(), 3), "borrow", round(EW.borrow_S.mean(), 3),
    "mean one-way turnover L/S", round(EW.turnover_L.iloc[1:].mean(), 3), round(EW.turnover_S.iloc[1:].mean(), 3))
res.add("S1_costs", "2000-2024", to_cost_L_pct=EW.to_cost_L.mean(), to_cost_S_pct=EW.to_cost_S.mean(), fullrt_cost_L_pct=EW.fullrt_cost_L.mean(),
        fullrt_cost_S_pct=EW.fullrt_cost_S.mean(), borrow_pct=EW.borrow_S.mean(), turnover_L=EW.turnover_L.iloc[1:].mean(),
        turnover_S=EW.turnover_S.iloc[1:].mean(), median_hs_entry_pct=float(np.nanmedian(mainB.hs_entry) * 100),
        share_valid_quote_entry=float(np.isfinite(mainB.hs_entry).mean()))
out = EW.merge(VW[["period", "LS", "R_long", "R_short"]].rename(columns={"LS": "LS_VW", "R_long": "R_long_VW", "R_short": "R_short_VW"}),
               on="period", how="left").merge(NF[["period", "LS", "n"]].rename(columns={"LS": "LS_nofilter", "n": "n_nofilter"}), on="period", how="left")
out.to_csv(O + "s1_ls_periods.csv", index=False)

# ---------------------------------------------------------------- monthly calendar time (main EW), FF5 + UMD
dl_rows = []
for p in plist:
    g = mainB[mainB.period == p]; e = EW[EW.period == p].iloc[0]
    it0 = first_on_after(cal, e.t0); ix = first_on_after(cal, e.exit)
    dd = cal[it0 + 1: ix + 1]
    for leg, qq in [("L", 1), ("S", 5)]:
        x = g[g.q_main == qq]
        ids = np.repeat(x.permno.to_numpy(), len(dd)); dn_ = np.tile(days(dd), len(x))
        _, lv = idx.lookup(ids, dn_, "lv")
        rel_ = np.exp(lv.reshape(len(x), len(dd)) - x.lv_entry.to_numpy()[:, None]) if "lv_entry" in x else None
        if rel_ is None:
            raise RuntimeError("lv_entry missing")
        V = np.nanmean(rel_, axis=0)
        Vp = np.concatenate([[1.0], V[:-1]])
        dl_rows.append(pd.DataFrame({"date": dd, "leg": leg, "r": V / Vp - 1, "period": p}))
DLY = pd.concat(dl_rows, ignore_index=True)
DL = DLY.pivot_table(index="date", columns="leg", values="r")
DL["ym"] = DL.index.to_period("M")
M = DL.groupby("ym").agg(L=("L", lambda v: np.prod(1 + v) - 1), S=("S", lambda v: np.prod(1 + v) - 1), ndays=("L", "size"))
M["LS"] = (M.L - M.S) * 100
ff = pd.read_parquet(C + "ff5umd_monthly.parquet"); ff["ym"] = pd.to_datetime(ff.date).dt.to_period("M")
M = M.reset_index().merge(ff, on="ym", how="left")
M.to_csv(O + "s1_ls_monthly.csv", index=False)
X = sm.add_constant(M[["mktrf", "smb", "hml", "rmw", "cma", "umd"]] * 100)
mm = sm.OLS(M.LS, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
log(f"S1 monthly calendar-time (n={len(M)} months {M.ym.min()}..{M.ym.max()}): mean LS {M.LS.mean():+.3f}%/mo, FF5+UMD alpha "
    f"{mm.params['const']:+.3f}%/mo t {mm.tvalues['const']:+.2f} (NW6); betas {mm.params.drop('const').round(3).to_dict()}")
ann_sh = M.LS.mean() / M.LS.std(ddof=1) * np.sqrt(12)
res.add("S1_calendar_monthly_FF6", "2000-2024", n_months=len(M), mean_ls_pct_month=M.LS.mean(), sharpe_ann=ann_sh,
        alpha_pct_month=mm.params["const"], t_alpha_nw6=mm.tvalues["const"], r2=mm.rsquared,
        **{f"beta_{k}": mm.params[k] for k in ["mktrf", "smb", "hml", "rmw", "cma", "umd"]})
chk = DLY.groupby(["period", "leg"]).r.apply(lambda v: np.prod(1 + v) - 1).unstack()
chk = chk.join(EW.set_index("period")[["R_long", "R_short"]])
log("check: daily-chained leg return vs period leg return, max |diff| (pp):",
    float(max((chk.L * 100 - chk.R_long).abs().max(), (chk.S * 100 - chk.R_short).abs().max())))

# ---------------------------------------------------------------- Fama-MacBeth
def winsor(s):
    lo, hi = s.quantile(0.01), s.quantile(0.99)
    return s.clip(lo, hi)


fm_rows = {"A": [], "B": []}
mb = B[B.screen].copy()
for p, g in mb.groupby("period"):
    g = g.copy()
    g["zBT"] = (g.BT - g.BT.mean()) / g.BT.std(ddof=1) if g.BT.std(ddof=1) > 0 else np.nan
    for v in ["bm", "mom12", "loan_g3"]:
        g[v] = winsor(g[v])
    for ver, xs in [("A", ["zBT", "logcap", "bm", "mom12", "loan_g3"]),
                    ("B", ["zBT", "logcap", "bm", "mom12", "loan_g3", "share_CI", "share_CRE", "share_CC", "share_OC"])]:
        z = g[["R"] + xs].replace([np.inf, -np.inf], np.nan).dropna()
        if len(z) < 30:
            continue
        m = sm.OLS(z.R * 100, sm.add_constant(z[xs])).fit()
        d = m.params.to_dict(); d.update(period=p, n=len(z), year=int(g.year.iloc[0]))
        fm_rows[ver].append(d)
fm_all = []
for ver in ["A", "B"]:
    F = pd.DataFrame(fm_rows[ver])
    F["version"] = ver
    fm_all.append(F)
    for v in [c for c in F.columns if c not in ("period", "n", "year", "version", "const")]:
        a = nw_mean(F[v], 1)
        h1 = nw_mean(F.loc[F.year <= 2011, v], 1); h2 = nw_mean(F.loc[F.year >= 2012, v], 1)
        res.add(f"S1_FM_{ver}", v, n_periods=a["n"], coef=a["mean"], t_nw1=a["t"], coef_2000_2011=h1["mean"], t_2000_2011=h1["t"],
                coef_2012_2024=h2["mean"], t_2012_2024=h2["t"], avg_n=F.n.mean())
        if v == "zBT":
            log(f"FM version {ver}: zBT coef {a['mean']:+.3f}%/sd t {a['t']:+.2f} (periods {a['n']}, avg n {F.n.mean():.0f}) | "
                f"2000-11 {h1['mean']:+.3f} (t {h1['t']:+.2f}) | 2012-24 {h2['mean']:+.3f} (t {h2['t']:+.2f})")
pd.concat(fm_all, ignore_index=True).to_csv(O + "s1_fm_coefs.csv", index=False)

# ---------------------------------------------------------------- leg shares, counts
for leg, qq in [("long_Q1", 1), ("short_Q5", 5)]:
    x = B[B.q_main == qq]
    m_raw = x.groupby("period")[[f"share_{k}" for k in CATS]].mean().mean()
    m_ren = x.groupby("period")[[f"sh2_{k}" for k in CATS]].mean().mean()
    res.add("S1_leg_shares", leg, **{f"raw_{k}": m_raw[f"share_{k}"] for k in CATS}, **{f"renorm_{k}": m_ren[f"sh2_{k}"] for k in CATS},
            mean_BT=x.groupby("period").BT.mean().mean())
    log(f"leg {leg}: raw shares {m_raw.round(3).to_dict()} | mean BT {x.groupby('period').BT.mean().mean():.2f}")
res.add("S1_counts", "per period", mean_n_main=CNT.n_main.mean(), min_n_main=CNT.n_main.min(), max_n_main=CNT.n_main.max(),
        mean_n_q1=CNT.n_main_q1.mean(), mean_n_q5=CNT.n_main_q5.mean(), periods=len(CNT),
        delisted_positions_main=int(B[B.screen & B.delisted_in_period].shape[0]))
for era, lo, hi in [("2000-2005", 2000, 2005), ("2006-2014", 2006, 2014), ("2015-2018", 2015, 2018), ("2019-2024", 2019, 2024)]:
    z = CNT[(CNT.year >= lo) & (CNT.year <= hi)]
    res.add("S1_counts", era, mean_n_y9c=z.n_y9c.mean(), mean_n_main=z.n_main.mean(), mean_n_nofilter=z.n_signal_entry.mean())
res.save(O + "results_s1.csv")
log("done")
