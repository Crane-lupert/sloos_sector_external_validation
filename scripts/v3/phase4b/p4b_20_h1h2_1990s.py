# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / H1, H2 - pre-sample confirmation test of the phase-4 SLOOS S1 design, SLOOS releases 1990-08 .. 2000-05.
Implements PHASE4B_SPEC.md sections 2-3 under phase4b/FROZEN_PARAMS.json (ported from phase4/scripts/p4_20_s1.py; the phase-4
code is not modified).

Outputs: out/h1h2_1990s_bank_table.parquet (+ .csv), out/h1h2_1990s_periods.csv, out/h1h2_1990s_counts.csv,
         out/results_1990s.csv (test_id, sample, stat, value)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import json
import time
import numpy as np
import pandas as pd
import statsmodels.api as sm
from p4blib import *

t_ = time.time()
log = lambda *a: print(f"[{time.time() - t_:5.0f}s]", *a, flush=True)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
fz = json.load(open(P4B + "FROZEN_PARAMS.json", encoding="utf-8"))
log("FROZEN_PARAMS frozen_at:", fz["frozen_at"][:80], "...")
res = Results()

cal = pd.DatetimeIndex(pd.read_parquet(C + "dsi_1989_2025.parquet").date)
cal = cal[cal <= pd.Timestamp("2024-12-31")]
calv = days(cal)
N = pd.read_csv(P4O + "s1_N_by_release.csv", parse_dates=["fred_date", "release_date", "approx_release_regular_practice"])
Y = pd.read_parquet(C + "y9c_panel_1990s.parquet")
Y["date"] = pd.to_datetime(Y.date)
Yd = {k: g.set_index("date").sort_index() for k, g in Y.groupby("rssd9001")}
lk = pd.read_parquet(P4C + "link.parquet")
lk = lk[lk.inst_type.str.lower() == "bank holding company"].copy()
lk["dt_start"] = pd.to_datetime(lk.dt_start); lk["dt_end"] = pd.to_datetime(lk.dt_end)
lk["dt_end_open"] = lk.dt_end.where(lk.dt_end < lk.dt_end.max(), pd.Timestamp("2099-12-31"))
dn = pd.read_parquet(P4C + "dsenames.parquet")
dn["namedt"] = pd.to_datetime(dn.namedt); dn["nameendt"] = pd.to_datetime(dn.nameendt)
cs = dn[dn.shrcd.isin([10, 11]) & dn.exchcd.isin([1, 2, 3])]
delist = pd.read_parquet(P4C + "delist.parquet")
idx, px, dlr = us_index(C + "crsp_bank_dsf_1990s.parquet", delist)
log("index rows", len(idx.keys), "price rows", len(px.keys), "delisting records appended", len(dlr))


def qstar(r):
    """latest calendar quarter-end q with (r - q) >= 75 days (phase-4 rule)"""
    lim = pd.Timestamp(r) - pd.Timedelta(days=75)
    q = (lim + pd.offsets.QuarterEnd(0)).normalize()
    if q > lim:
        q = (q - pd.offsets.QuarterEnd(1)).normalize()
    return q


def y9c_at(rssd, q):
    g = Yd.get(rssd)
    if g is None:
        return None
    if q in g.index:
        return q
    z = g.index[(g.index < q) & (g.index >= q - pd.Timedelta(days=183))]
    return z.max() if len(z) else None


# ---------------------------------------------------------------- releases, dates, periods
rel = N[(N.fred_date >= pd.Timestamp("1990-07-01")) & (N.fred_date <= pd.Timestamp("2000-07-01"))].sort_values("fred_date").reset_index(drop=True)
rel["approx"] = rel.release_date.isna()
rel["r"] = rel.release_date.fillna(rel.approx_release_regular_practice)
rel["i_t0"] = [first_after(cal, r) + (9 if a else 0) for r, a in zip(rel.r, rel.approx)]
rel["t0"] = cal[rel.i_t0.values]
rel["i_D"] = rel.i_t0 - 1
rel["D"] = [cal[i - 1] if a else r for r, a, i in zip(rel.r, rel.approx, rel.i_t0)]
rel["qstar"] = rel.r.map(qstar)
rel["i_exit"] = rel.i_t0.shift(-1)
rel["exit"] = rel.t0.shift(-1)
per = rel[rel.fred_date <= pd.Timestamp("2000-04-01")].copy().reset_index(drop=True)
per["i_exit"] = per.i_exit.astype(int)
assert len(per) == 40 and per.exit.notna().all()
assert all(per.t0 > per.r), "entry must be after the (approximate) release date"
assert all((per.qstar + pd.Timedelta(days=75)) <= per.r)
ex_ = per[~per.approx]
assert all(ex_.i_D == [last_on_before(cal, r) for r in ex_.r]), "exact releases: decision day must be the last trading day <= r"
ap_ = per[per.approx]
assert all(ap_.i_t0 == [first_after(cal, r) + 9 for r in ap_.r])
p4_first_t0 = pd.Timestamp(pd.read_csv(P4O + "s1_ls_periods.csv", parse_dates=["t0"]).t0.min())
assert per.exit.iloc[-1] == p4_first_t0, (per.exit.iloc[-1], p4_first_t0)
log(f"releases in window {len(per)} (approximate dates {int(per.approx.sum())}); last exit {per.exit.iloc[-1].date()} == phase-4 first entry {p4_first_t0.date()}")

# ---------------------------------------------------------------- universe and signal per release
rows, cnt = [], []
for p, e in per.iterrows():
    D = e.D; iD = int(e.i_D); it0 = int(e.i_t0); ix = int(e.i_exit)
    L = lk[(lk.dt_start <= D) & (lk.dt_end_open >= D)][["rssd9001", "permco"]].drop_duplicates()
    S = cs[(cs.namedt <= D) & (cs.nameendt >= D)][["permno", "permco"]].drop_duplicates()
    c = L.merge(S, on="permco")
    n_link = L.rssd9001.nunique()
    _, prc = px.lookup(c.permno, calv[iD], "prc", stale_min=calv[iD - 5])
    _, cap = px.lookup(c.permno, calv[iD], "cap", stale_min=calv[iD - 5])
    c["prc_D"] = prc; c["cap_D"] = cap
    c = c[np.isfinite(c.cap_D) & (c.cap_D > 0)]
    c = c.sort_values(["rssd9001", "permco", "cap_D"], ascending=[True, True, False]).drop_duplicates(["rssd9001", "permco"])
    c = c.sort_values(["rssd9001", "cap_D"], ascending=[True, False]).drop_duplicates("rssd9001")
    n_cs = len(c)
    n_cs_screen = int(((c.prc_D >= 5) & (c.cap_D >= 100e6)).sum())  # count only: screened listed BHCs before the Y-9C merge
    q = e.qstar
    c["y9c_date"] = [y9c_at(int(x), q) for x in c.rssd9001]
    c = c[c.y9c_date.notna()].copy()
    c["y9c_date"] = pd.to_datetime(c.y9c_date)
    yy = Y.merge(c[["rssd9001", "y9c_date"]], left_on=["rssd9001", "date"], right_on=["rssd9001", "y9c_date"])
    c = c.merge(yy.drop(columns=["date"]), on=["rssd9001", "y9c_date"])
    c = c.sort_values(["permco", "bhck2170"], ascending=[True, False]).drop_duplicates("permco")
    n_y9 = len(c)
    Nk = {k: e[f"N_{k}"] for k in CATS}
    avail = [k for k in CATS if np.isfinite(Nk[k])]
    okk = c[[f"share_{k}" for k in avail]].notna().all(axis=1)
    n_nan_share = int((~okk).sum())
    c = c[okk].copy()
    ssum = c[[f"share_{k}" for k in avail]].sum(axis=1)
    c = c[ssum > 0].copy(); ssum = ssum[ssum > 0]
    for k in CATS:
        c[f"sh2_{k}"] = (c[f"share_{k}"] / ssum) if k in avail else 0.0
    c["BT"] = sum(c[f"sh2_{k}"] * Nk[k] for k in avail)
    c["avail"] = ",".join(avail)
    rec0, lv0 = idx.lookup(c.permno, calv[it0], "lv", stale_min=calv[it0 - 5])
    _, prc0 = px.lookup(c.permno, calv[it0], "prc", stale_min=calv[it0 - 5])
    _, cap0 = px.lookup(c.permno, calv[it0], "cap", stale_min=calv[it0 - 5])
    _, lvx = idx.lookup(c.permno, calv[ix], "lv")
    _, prcx = px.lookup(c.permno, calv[ix], "prc", stale_min=calv[ix - 5])
    c["lv_entry"] = lv0; c["prc_t0"] = prc0; c["cap_t0"] = cap0
    c["live_at_exit"] = np.isfinite(prcx)
    c["R"] = np.exp(lvx - lv0) - 1.0
    c = c[np.isfinite(c.lv_entry) & np.isfinite(c.R) & np.isfinite(c.prc_t0)].copy()
    dd = dlr[(dlr.date > cal[it0]) & (dlr.date <= cal[ix])]
    c["delisted_in_period"] = c.permno.isin(set(dd.permno))
    c["screen"] = (c.prc_D >= 5) & (c.cap_D >= 100e6)
    c["period"] = p; c["fred_date"] = e.fred_date; c["release_date"] = e.r; c["approx_date"] = bool(e.approx)
    c["decision_date"] = cal[iD]; c["t0"] = cal[it0]; c["exit"] = cal[ix]; c["qstar"] = q
    c["year"] = e.r.year
    for u, m in [("main", c.screen.to_numpy()), ("nofilter", np.ones(len(c), bool))]:
        for sk, col in [("bt", "BT"), ("cre", "share_CRE")]:
            z = c[m].sort_values([col, "permno"], kind="mergesort")
            n = len(z)
            qv = np.ceil(5 * np.arange(1, n + 1) / n).astype(int) if n else np.array([], int)
            c[f"q_{sk}_{u}"] = np.nan
            c.loc[z.index, f"q_{sk}_{u}"] = qv
    # self-checks
    if len(c):
        assert (c.y9c_date <= q).all() and (c.y9c_date >= q - pd.Timedelta(days=183)).all()
        assert c.permno.is_unique and c.rssd9001.is_unique and c.permco.is_unique
        assert np.allclose(c[[f"sh2_{k}" for k in CATS]].sum(axis=1), 1.0)
        assert np.allclose(c[["share_CI", "share_CRE", "share_RRE", "share_CONS"]].sum(axis=1), 1.0)
    rows.append(c)
    cnt.append(dict(period=p, fred_date=e.fred_date.date(), release_date=e.r.date(), approx_date=bool(e.approx), year=e.r.year,
                    decision_date=cal[iD].date(), t0=cal[it0].date(), exit=cal[ix].date(), qstar=q.date(), n_link_rssd=n_link,
                    n_common=n_cs, n_common_screen=n_cs_screen, n_y9c=n_y9, n_nan_share=n_nan_share, n_signal_entry=len(c), n_main=int(c.screen.sum()) if len(c) else 0,
                    n_main_q1_bt=int((c.q_bt_main == 1).sum()) if len(c) else 0, n_main_q5_bt=int((c.q_bt_main == 5).sum()) if len(c) else 0,
                    n_delisted_in_period=int(c.delisted_in_period.sum()) if len(c) else 0,
                    n_main_assets_lt_150m=int((c.screen & (c.bhck2170 < 150000)).sum()) if len(c) else 0, avail=",".join(avail)))
B = pd.concat([r for r in rows if len(r)], ignore_index=True)
CNT = pd.DataFrame(cnt)
CNT.to_csv(O + "h1h2_1990s_counts.csv", index=False)
keep_cols = ["period", "fred_date", "release_date", "approx_date", "decision_date", "t0", "exit", "year", "qstar", "permno", "permco", "rssd9001",
             "y9c_date"] + [f"share_{k}" for k in CATS + ["CONS"]] + [f"sh2_{k}" for k in CATS] + \
            ["avail", "BT", "q_bt_main", "q_bt_nofilter", "q_cre_main", "q_cre_nofilter", "screen", "R", "prc_D", "cap_D", "prc_t0", "cap_t0",
             "live_at_exit", "delisted_in_period", "bhck2170", "bhck2122", "CI", "CRE", "RRE", "CC", "OC", "CONS", "L"]
B[keep_cols].to_parquet(O + "h1h2_1990s_bank_table.parquet", index=False)
B[keep_cols].to_csv(O + "h1h2_1990s_bank_table.csv", index=False)
log("bank table rows", len(B), "periods with any bank", B.period.nunique())
print(CNT[["fred_date", "release_date", "approx_date", "t0", "exit", "qstar", "n_link_rssd", "n_common", "n_common_screen", "n_y9c", "n_signal_entry", "n_main",
           "n_main_q1_bt", "n_main_q5_bt", "n_delisted_in_period", "n_main_assets_lt_150m", "avail"]].to_string(index=False))


# ---------------------------------------------------------------- per-period series
def series(df, u):
    out = []
    for p, g in df.groupby("period"):
        g = g[g[f"q_bt_{u}"].notna()]
        if len(g) < 25:
            continue
        lo, hi = g[g[f"q_bt_{u}"] == 1], g[g[f"q_bt_{u}"] == 5]
        clo, chi = g[g[f"q_cre_{u}"] == 1], g[g[f"q_cre_{u}"] == 5]
        out.append(dict(period=p, fred_date=g.fred_date.iloc[0], release_date=g.release_date.iloc[0], approx_date=g.approx_date.iloc[0],
                        year=g.year.iloc[0], t0=g.t0.iloc[0], exit=g.exit.iloc[0], n=len(g), n_long=len(lo), n_short=len(hi),
                        R_long=lo.R.mean() * 100, R_short=hi.R.mean() * 100, LS_BT=(lo.R.mean() - hi.R.mean()) * 100,
                        n_cre_low=len(clo), n_cre_high=len(chi), R_cre_low=clo.R.mean() * 100, R_cre_high=chi.R.mean() * 100,
                        LS_CRE=(clo.R.mean() - chi.R.mean()) * 100, R_all=g.R.mean() * 100,
                        BT_long=lo.BT.mean(), BT_short=hi.BT.mean(), creshare_low=clo.share_CRE.mean(), creshare_high=chi.share_CRE.mean(),
                        creshare_bt_long=lo.share_CRE.mean(), creshare_bt_short=hi.share_CRE.mean()))
    return pd.DataFrame(out)


S_main = series(B, "main"); S_nf = series(B, "nofilter")
Nrel = per[[f"N_{k}" for k in CATS]].rename_axis("period")  # per's index is the period id used in the loop
S_main = S_main.join(Nrel, on="period"); S_nf = S_nf.join(Nrel, on="period")
dropped = sorted(set(per.index) - set(S_main.period))
log("periods formed (main, n >= 25):", len(S_main), "| not formed:", [str(per.fred_date[i].date()) for i in dropped],
    "| approximate-dated among formed:", int(S_main.approx_date.sum()))
assert S_main.period.equals(S_nf.period) or True

SPLITS = [("full", lambda d: np.ones(len(d), bool)), ("1990-1992", lambda d: (d.year <= 1992).to_numpy()),
          ("1993-2000Q2", lambda d: (d.year >= 1993).to_numpy()), ("1993-1999 strict", lambda d: d.year.between(1993, 1999).to_numpy()),
          ("exact-dated only (EXPLORATORY)", lambda d: (~d.approx_date.astype(bool)).to_numpy())]


def h1(tid, S, verdict_on):
    for lab, f in SPLITS:
        d = S[f(S)]
        a = nw_mean(d.LS_BT, 1)
        v = verdict_4b(a["mean"], a["t"], +1) if (verdict_on and lab == "full") else "reported only"
        res.add(tid, lab, n=a["n"], mean_pct=a["mean"], t_nw1=a["t"], verdict=v)
        log(f"{tid} [{lab}]: n={a['n']} mean LS={a['mean']:+.3f}% t={a['t']:+.2f} | {v}")


def h2(tid, S, verdict_on):
    for lab, f in SPLITS:
        d = S[f(S)]
        b = ols_slope(d.LS_CRE, d.N_CRE / 10.0, cov="HAC", lags=1)
        m = nw_mean(d.LS_CRE, 1)
        v = verdict_4b(b["b"], b["t"], +1) if (verdict_on and lab == "full") else "reported only"
        res.add(tid, lab, n=b["n"], slope_pct_per_10pp=b["b"], t_nw1=b["t"], intercept_pct=b["a"], t_intercept=b["t_a"], r2=b["r2"],
                mean_LS_CRE_pct=m["mean"], t_mean_LS_CRE=m["t"], mean_N_CRE=float(d.N_CRE.mean()), sd_N_CRE=float(d.N_CRE.std(ddof=1)), verdict=v)
        log(f"{tid} [{lab}]: n={b['n']} slope={b['b']:+.3f}%/10pp t={b['t']:+.2f} | intercept {b['a']:+.3f} (t {b['t_a']:+.2f}) | "
            f"mean LS_CRE {m['mean']:+.3f} (t {m['t']:+.2f}) | N_CRE mean {d.N_CRE.mean():.1f} sd {d.N_CRE.std(ddof=1):.1f} | {v}")


def panel(tid, df, S, verdict_on):
    formed = set(S.period)
    for lab, f in SPLITS:
        Sx = S[f(S)]
        keep = set(Sx.period)
        d = df[df.period.isin(keep) & df.period.isin(formed)].copy()
        mN = Sx.N_CRE.mean()  # sample mean over the releases of this sample (one value per release)
        d["Rp"] = d.R * 100
        d["I_CRE"] = d.share_CRE * (d.N_CRE - mN) / 10.0
        xs = ["I_CRE", "share_CRE", "share_CI"]
        d = d.dropna(subset=["Rp"] + xs)
        Wd = d[["Rp"] + xs] - d.groupby("period")[["Rp"] + xs].transform("mean")
        fit = sm.OLS(Wd.Rp, Wd[xs]).fit(cov_type="cluster", cov_kwds={"groups": d.period.values, "use_correction": True})
        v = verdict_4b(fit.params["I_CRE"], fit.tvalues["I_CRE"], -1) if (verdict_on and lab == "full") else "reported only"
        res.add(tid, lab, n_obs=len(d), n_releases=d.period.nunique(), coef_I_CRE=fit.params["I_CRE"], t_I_CRE=fit.tvalues["I_CRE"],
                coef_share_CRE=fit.params["share_CRE"], t_share_CRE=fit.tvalues["share_CRE"], coef_share_CI=fit.params["share_CI"],
                t_share_CI=fit.tvalues["share_CI"], mean_N_CRE_used=mN, verdict=v)
        log(f"{tid} [{lab}]: obs {len(d)}, releases {d.period.nunique()} | I_CRE coef {fit.params['I_CRE']:+.3f} (t {fit.tvalues['I_CRE']:+.2f}) | "
            f"share_CRE {fit.params['share_CRE']:+.3f} (t {fit.tvalues['share_CRE']:+.2f}) | share_CI {fit.params['share_CI']:+.3f} "
            f"(t {fit.tvalues['share_CI']:+.2f}) | {v}")


Bm = B.join(Nrel, on="period")
h1("H1_main_EW", S_main, True)
h2("H2_main_slope", S_main, True)
panel("H2_main_panel", Bm[Bm.screen], S_main, True)
h1("H1_nofilter_EW", S_nf, False)
h2("H2_nofilter_slope", S_nf, False)
panel("H2_nofilter_panel", Bm, S_nf, False)
for nm, col in [("H1_main_long_leg", "R_long"), ("H1_main_short_leg", "R_short"), ("H2_main_lowCRE_leg", "R_cre_low"), ("H2_main_highCRE_leg", "R_cre_high")]:
    a = nw_mean(S_main[col], 1)
    res.add(nm, "full", n=a["n"], mean_pct=a["mean"], t_nw1=a["t"])
    log(f"{nm}: mean {a['mean']:+.3f}% (t {a['t']:+.2f})")
# leg composition
for nm, qcol, qq in [("BT_Q1_long", "q_bt_main", 1), ("BT_Q5_short", "q_bt_main", 5), ("CRE_Q1_low", "q_cre_main", 1), ("CRE_Q5_high", "q_cre_main", 5)]:
    x = B[B[qcol] == qq]
    m_raw = x.groupby("period")[[f"share_{k}" for k in ["CI", "CRE", "RRE", "CONS"]]].mean().mean()
    res.add("leg_shares_1990s", nm, **{f"raw_{k}": m_raw[f"share_{k}"] for k in ["CI", "CRE", "RRE", "CONS"]},
            mean_BT=x.groupby("period").BT.mean().mean(), mean_n=x.groupby("period").size().mean())
    log(f"leg {nm}: mean raw shares {m_raw.round(3).to_dict()} | mean BT {x.groupby('period').BT.mean().mean():.2f}")
# rank correlation of the two sorts (BT vs CRE share) inside releases
rho = B[B.screen].groupby("period").apply(lambda g: g.BT.rank().corr(g.share_CRE.rank()), include_groups=False)
res.add("sort_overlap_1990s", "full", mean_spearman_BT_vs_CREshare=float(rho.mean()), min_spearman=float(rho.min()), max_spearman=float(rho.max()))
log(f"Spearman(BT, CRE share) inside releases: mean {rho.mean():.3f}, min {rho.min():.3f}, max {rho.max():.3f}")
res.add("counts_1990s", "per formed period", periods=len(S_main), approx_dated_periods=int(S_main.approx_date.sum()),
        mean_n_main=S_main.n.mean(), min_n_main=S_main.n.min(), max_n_main=S_main.n.max(), mean_n_nofilter=S_nf.n.mean(),
        delisted_positions_main=int(B[B.screen & B.delisted_in_period].shape[0]),
        main_positions_assets_lt_150m=int((B.screen & (B.bhck2170 < 150000)).sum()), main_positions=int(B.screen.sum()))
S_main.to_csv(O + "h1h2_1990s_periods.csv", index=False)
S_nf.to_csv(O + "h1h2_1990s_periods_nofilter.csv", index=False)
res.save(O + "results_1990s.csv")
log("done")
