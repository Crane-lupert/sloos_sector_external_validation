# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / S3 - real-time market timing with the SLOOS level (reference only, not in the verdict). Implements FROZEN_PARAMS S3.
Outputs: out/s3_periods_{US_a,US_b,EZ,EZ_broad,UK}.csv, out/results_s3.csv"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import time
import numpy as np
import pandas as pd
import statsmodels.api as sm
from p4lib import *

t_ = time.time()
log = lambda *a: print(f"[{time.time() - t_:5.0f}s]", *a, flush=True)
pd.set_option("display.width", 250)
res = Results()


def oos(ret, x, years, eval_mask, min_train=20):
    """expanding-window OOS R2 (plain and CT-restricted) on period arrays; training = all earlier periods."""
    e_m, e_h, e_ct = [], [], []
    for p in range(len(ret)):
        if not eval_mask[p] or p < min_train:
            continue
        X = sm.add_constant(x[:p]); b = np.linalg.lstsq(X, ret[:p], rcond=None)[0]
        f = b[0] + b[1] * x[p]; hm = ret[:p].mean()
        fct = hm if b[1] > 0 else max(f, 0.0)
        e_m.append(ret[p] - f); e_h.append(ret[p] - hm); e_ct.append(ret[p] - fct)
    e_m, e_h, e_ct = map(np.asarray, (e_m, e_h, e_ct))
    return dict(n_oos=len(e_m), r2_os=float(1 - (e_m ** 2).sum() / (e_h ** 2).sum()) if len(e_m) else np.nan,
                r2_os_ct=float(1 - (e_ct ** 2).sum() / (e_h ** 2).sum()) if len(e_m) else np.nan)


def sharpe(d):
    d = np.asarray(d, float)
    return float(d.mean() / d.std(ddof=1) * np.sqrt(252)), float(d.mean() * 252 * 100)


# ================================================================ US
cal = us_calendar()
dsi = pd.read_parquet(C + "dsi.parquet"); dsi["date"] = pd.to_datetime(dsi.date)
ff = pd.read_parquet(C + "ff5umd_daily.parquet"); ff["date"] = pd.to_datetime(ff.date)
D = dsi.merge(ff[["date", "rf"]], on="date", how="left")
log("US days without rf:", int(D.rf.isna().sum()))
D["rf"] = D.rf.fillna(0.0)
D = D.set_index("date")
Q = pd.read_parquet(C + "N_by_quarter.parquet"); y = Q.DRTSCILM.dropna(); y.index = pd.DatetimeIndex(y.index)
rel = pd.read_csv(O1 + "release_dates_US_SLOOS.csv", parse_dates=["fred_date", "release_date", "approx_release_regular_practice"])


def us_periods(R):
    R = R.sort_values("R").reset_index(drop=True)
    R["i0"] = R.R.map(lambda d: first_after(cal, d))
    R["i1"] = list(R.i0.iloc[1:]) + [-1]
    R = R[(R.i1 > 0) & (R.i1 < len(cal))].copy()
    R = R[cal[R.i1.values] <= US_END].reset_index(drop=True)
    rows, daily = [], []
    for _, e in R.iterrows():
        dd = D.iloc[int(e.i0) + 1: int(e.i1) + 1]
        med = float(y[y.index <= e.fred_date].median())
        x = float(y.loc[e.fred_date])
        inmkt = x <= med
        rows.append(dict(fred_date=e.fred_date.date(), R=e.R.date(), year=e.R.year, t0=cal[int(e.i0)].date(), exit=cal[int(e.i1)].date(),
                         ndays=len(dd), drtscilm=x, exp_median=med, in_equity=inmkt,
                         ex_ret=(np.prod(1 + dd.vwretd) - np.prod(1 + dd.rf)) * 100))
        daily.append(pd.DataFrame({"date": dd.index, "bh_ex": (dd.vwretd - dd.rf).values,
                                   "strat_ex": ((dd.vwretd if inmkt else dd.rf) - dd.rf).values, "year": e.R.year}))
    return pd.DataFrame(rows), daily


A = rel[rel.release_date.notna() & (rel.release_date.dt.year >= 1997)].rename(columns={"release_date": "R"})[["fred_date", "R"]]
Bv = rel.assign(R=rel.release_date.fillna(rel.approx_release_regular_practice))
Bv = Bv[Bv.R.notna() & (Bv.fred_date >= pd.Timestamp("1990-04-01"))][["fred_date", "R"]]
PA, dA = us_periods(A); PB, dB = us_periods(Bv)
PA.to_csv(O + "s3_periods_US_a.csv", index=False); PB.to_csv(O + "s3_periods_US_b.csv", index=False)
for tag, P, dl_, mask, lab in [("a", PA, dA, np.ones(len(PA), bool), "1997-2024"), ("b", PB, dB, np.ones(len(PB), bool), "1990-2024"),
                               ("c", PA, dA, (PA.year >= 2015).to_numpy(), "2015-2024")]:
    Z = P[mask]
    rg = ols_slope(Z.ex_ret, Z.drtscilm, cov="HAC", lags=1)
    if tag == "c":
        oo = oos(PA.ex_ret.to_numpy(), PA.drtscilm.to_numpy(), PA.year.to_numpy(), mask, min_train=20)
    else:
        oo = oos(P.ex_ret.to_numpy(), P.drtscilm.to_numpy(), P.year.to_numpy(), mask, min_train=20)
    dd = pd.concat([d for d, m in zip(dl_, mask) if m], ignore_index=True)
    sh_s, mu_s = sharpe(dd.strat_ex); sh_b, mu_b = sharpe(dd.bh_ex)
    res.add("S3_US", lab, n_periods=rg["n"], slope_pct_per_pp=rg["b"], t_nw1=rg["t"], r2=rg["r2"], **oo, sharpe_timing=sh_s, sharpe_bh=sh_b,
            ann_ex_timing_pct=mu_s, ann_ex_bh_pct=mu_b, share_in_equity=float(Z.in_equity.mean()))
    log(f"S3 US {lab}: n={rg['n']} slope {rg['b']:+.4f}%/pp t {rg['t']:+.2f} | R2_OS {oo['r2_os']:+.4f} (CT {oo['r2_os_ct']:+.4f}, n_oos {oo['n_oos']}) | "
        f"Sharpe timing {sh_s:.3f} vs B&H {sh_b:.3f} | in equity {Z.in_equity.mean():.2f}")

# ================================================================ EU
con = connect()
q = con.execute(f"""
WITH s AS (SELECT l.fid, CAST(g.datadate AS DATE) date, g.prccd * g.trfd / g.ajexdi adj
           FROM '{O1}g_secd_stoxx600_min.parquet' g JOIN '{O3}eu_listing_ids.parquet' l ON g.gvkey = l.gvkey AND g.iid = l.iid
           WHERE g.prccd > 0 AND g.ajexdi > 0 AND g.trfd IS NOT NULL AND g.datadate <= DATE '2026-05-01'),
s2 AS (SELECT fid, date, ln(adj / lag(adj) OVER (PARTITION BY fid ORDER BY date)) lr FROM s WHERE adj > 0),
s3 AS (SELECT * FROM s2 WHERE lr IS NOT NULL AND isfinite(lr) AND abs(lr) < 1.5)
SELECT fid, date_diff('day', DATE '1970-01-01', date) d, SUM(lr) OVER (PARTITION BY fid ORDER BY date ROWS UNBOUNDED PRECEDING) lv FROM s3""").fetchnumpy()
keys = q["fid"].astype(np.int64) * MULT + q["d"].astype(np.int64)
o_ = np.argsort(keys, kind="stable"); keys = keys[o_]; lvv = q["lv"].astype(float)[o_]
eidx = Keyed.__new__(Keyed); eidx.keys = keys; eidx.cols = {"lv": lvv}
lid = pd.read_parquet(O3 + "eu_listing_ids.parquet")
comp = pd.read_parquet(C + "eu_company.parquet")
cap = pd.read_parquet(C + "eu_cap_formation.parquet")
cap = cap.merge(lid, on=["gvkey", "iid"], how="inner")
cap["datadate"] = pd.to_datetime(cap.datadate)
fx = pd.read_parquet(C + "eu_fx_formation.parquet"); fx["datadate"] = pd.to_datetime(fx.datadate)
fx = fx[fx.fromcurd == "GBP"]
log("EU cap rows", len(cap), "| UK-GBP prccd median", float(cap[cap.curcdd == "GBP"].prccd.median()),
    "| GBP->GBP rate rows", int((fx.tocurd == "GBP").sum()))


def eu_run(tag, reg_, upath, euro_only, relfile, col, y0, y1, ccy):
    calr = eu_calendar(reg_); calrv = days(calr)
    u = pd.read_parquet(upath).dropna(subset=["gvkey", "iid"]).copy()
    u["gvkey"] = u.gvkey.astype(str); u["iid"] = u.iid.astype(str)
    u = u.merge(lid, on=["gvkey", "iid"]).merge(comp[["gvkey", "loc"]].rename(columns={"loc": "gloc"}), on="gvkey", how="left")
    u["from_date"] = pd.to_datetime(u.from_date); u["thru"] = pd.to_datetime(u.thru)
    if euro_only:
        u = u[u.gloc.isin(EURO)]
    tab = pd.read_csv(O1 + relfile, parse_dates=["release_date"]).reset_index(drop=True)
    tab["exp_median"] = tab[col].expanding().median()
    R = tab[tab.release_date.notna() & (tab.release_date.dt.year >= y0) & (tab.release_date.dt.year <= y1)].reset_index(drop=True)
    R["i0"] = R.release_date.map(lambda d: first_after(calr, d))
    R["i1"] = list(R.i0.iloc[1:]) + [-1]
    R = R[(R.i1 > 0) & (R.i1 < len(calr))].copy()
    R = R[calr[R.i1.values] <= US_END].reset_index(drop=True)
    rows, daily = [], []
    for _, e in R.iterrows():
        r = e.release_date; i0 = int(e.i0); i1 = int(e.i1)
        m = u[(u.from_date <= r) & (u.thru.isna() | (u.thru >= r))].drop_duplicates("fid")
        fid = m.fid.to_numpy()
        _, lv0 = eidx.lookup(fid, calrv[i0], "lv", stale_min=calrv[i0 - 5])
        f0 = calr[i0]
        cp = cap[(cap.fid.isin(fid)) & (cap.datadate <= f0) & (cap.datadate >= f0 - pd.Timedelta(days=10)) & cap.cshoc.notna() & (cap.prccd > 0)]
        cp = cp.sort_values(["fid", "datadate"]).drop_duplicates("fid", keep="last")
        rt = fx[fx.datadate <= f0].sort_values("datadate").groupby("tocurd").exratd.last()
        rt.loc["GBP"] = 1.0
        conv = cp.curcdd.map(rt)
        val_gbp = cp.prccd * cp.cshoc / conv
        val = val_gbp * (rt.get("EUR", np.nan) if ccy == "EUR" else 1.0)
        wmap = pd.Series(val.values, index=cp.fid.values)
        w = wmap.reindex(fid).to_numpy()
        ok = np.isfinite(lv0) & np.isfinite(w) & (w > 0)
        fidk, lv0k, wk = fid[ok], lv0[ok], w[ok] / w[ok].sum()
        dd = calr[i0 + 1: i1 + 1]
        ids = np.repeat(fidk, len(dd)); dn_ = np.tile(days(dd), len(fidk))
        _, lv = eidx.lookup(ids, dn_, "lv")
        rel_ = np.exp(lv.reshape(len(fidk), len(dd)) - lv0k[:, None])
        V = (wk[:, None] * rel_).sum(axis=0)
        Vp = np.concatenate([[1.0], V[:-1]])
        dr = V / Vp - 1
        inm = bool(e[col] <= e.exp_median)
        rows.append(dict(release_date=r.date(), year=r.year, t0=calr[i0].date(), exit=calr[i1].date(), level=e[col], exp_median=e.exp_median,
                         in_market=inm, n_members=len(m), n_weighted=int(ok.sum()), ret=(V[-1] - 1) * 100,
                         cap_cov=float(ok.mean())))
        daily.append(pd.DataFrame({"date": dd, "bh": dr, "strat": dr if inm else np.zeros(len(dr))}))
    P = pd.DataFrame(rows)
    P.to_csv(O + f"s3_periods_{tag}.csv", index=False)
    rg = ols_slope(P.ret, P.level, cov="HAC", lags=1)
    oo = oos(P.ret.to_numpy(), P.level.to_numpy(), P.year.to_numpy(), np.ones(len(P), bool), min_train=20)
    dd = pd.concat(daily, ignore_index=True)
    sh_s, mu_s = sharpe(dd.strat); sh_b, mu_b = sharpe(dd.bh)
    res.add(f"S3_{tag}", f"{y0}-{y1}", n_periods=rg["n"], slope_pct_per_pp=rg["b"], t_nw1=rg["t"], r2=rg["r2"], **oo, sharpe_timing_rf0=sh_s,
            sharpe_bh_rf0=sh_b, ann_timing_pct=mu_s, ann_bh_pct=mu_b, share_in_market=float(P.in_market.mean()),
            median_members=float(P.n_members.median()), median_cap_coverage=float(P.cap_cov.median()))
    log(f"S3 {tag} {y0}-{y1}: n={rg['n']} slope {rg['b']:+.4f}%/pp t {rg['t']:+.2f} | R2_OS {oo['r2_os']:+.4f} (CT {oo['r2_os_ct']:+.4f}, "
        f"n_oos {oo['n_oos']}) | Sharpe timing {sh_s:.3f} vs B&H {sh_b:.3f} (RF=0) | members {P.n_members.median():.0f}, cap coverage "
        f"{P.cap_cov.median():.3f}")


eu_run("EZ", "EZ", S3C + "stoxx600_eurozone_universe_2026-05-06.parquet", True, "release_dates_EZ_BLS.csv", "wfnet", 2003, 2024, "EUR")
eu_run("EZ_broad", "EZ", S3C + "stoxx600_eurozone_universe_2026-05-06.parquet", False, "release_dates_EZ_BLS.csv", "wfnet", 2003, 2024, "EUR")
eu_run("UK", "UK", S3C + "stoxx600_uk_universe_2026-05-06.parquet", False, "release_dates_UK_CCS.csv", "neg_availability", 2007, 2024, "GBP")
res.save(O + "results_s3.csv")
log("done")
