# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / S2 - release-day bank-stock reaction to the SLOOS C&I tightening surprise (primary test 2, US) + EZ / UK auxiliary.
Implements FROZEN_PARAMS S2. Outputs: out/s2_events.csv, out/s2_events_alt_link.csv, out/s2_events_{EZ,EZ_broad,UK}.csv,
out/results_s2.csv"""
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

# ================================================================ US
cal = us_calendar(); calv = days(cal)
dsi = pd.read_parquet(C + "dsi.parquet"); dsi["date"] = pd.to_datetime(dsi.date); mkt = dsi.set_index("date").vwretd
Q = pd.read_parquet(C + "N_by_quarter.parquet")
y = Q.DRTSCILM.dropna(); y.index = pd.DatetimeIndex(y.index)
rel = pd.read_csv(O1 + "release_dates_US_SLOOS.csv", parse_dates=["fred_date", "release_date"])
ev = rel[rel.release_date.notna() & (rel.release_date.dt.year >= 1997) & (rel.release_date <= US_END)].copy()
lk = pd.read_parquet(C + "link.parquet")
lk = lk[lk.inst_type.str.lower() == "bank holding company"].copy()
lk["dt_start"] = pd.to_datetime(lk.dt_start); lk["dt_end"] = pd.to_datetime(lk.dt_end)
lk["dt_end_open"] = lk.dt_end.where(lk.dt_end < lk.dt_end.max(), pd.Timestamp("2099-12-31"))
dn = pd.read_parquet(C + "dsenames.parquet")
dn["namedt"] = pd.to_datetime(dn.namedt); dn["nameendt"] = pd.to_datetime(dn.nameendt)
cs = dn[dn.shrcd.isin([10, 11]) & dn.exchcd.isin([1, 2, 3])]
idx, px, dlr = us_index()
dlr["date"] = pd.to_datetime(dlr.date)
log("events (exact date, 1997-2024):", len(ev))


def members(r, ipre, rule):
    """bank permnos for release r; screen at close of cal[ipre]. rule: 'link' or 'sic'."""
    S = cs[(cs.namedt <= r) & (cs.nameendt >= r)]
    if rule == "link":
        L = lk[(lk.dt_start <= r) & (lk.dt_end_open >= r)][["rssd9001", "permco"]].drop_duplicates()
        c = L.merge(S[["permno", "permco"]].drop_duplicates(), on="permco")
    else:
        c = S[S.siccd.between(6020, 6029) | S.siccd.between(6710, 6712)][["permno", "permco"]].drop_duplicates()
        c["rssd9001"] = -1
    _, prc = px.lookup(c.permno, calv[ipre], "prc", stale_min=calv[ipre - 5])
    _, cap = px.lookup(c.permno, calv[ipre], "cap", stale_min=calv[ipre - 5])
    c = c.assign(prc=prc, cap=cap)
    c = c[np.isfinite(c.cap) & (c.cap > 0)]
    c = c.sort_values(["permco", "cap"], ascending=[True, False]).drop_duplicates("permco")
    if rule == "link":
        c = c.sort_values(["rssd9001", "cap"], ascending=[True, False]).drop_duplicates("rssd9001")
    c = c[(c.prc >= 5) & (c.cap >= 100e6)]
    return c


def day_ret(perm, i):
    """member returns on calendar day i (dsf row that day, or a delisting record dated in (cal[i-1], cal[i]])."""
    has = px.has_exact(perm, calv[i])
    dd = dlr[(dlr.date > cal[i - 1]) & (dlr.date <= cal[i])]
    has = has | np.isin(perm, dd.permno.to_numpy())
    _, a = idx.lookup(perm, calv[i], "lv")
    _, b = idx.lookup(perm, calv[i - 1], "lv")
    r = np.exp(a - b) - 1
    return np.where(has & np.isfinite(r), r, np.nan)


def us_events(rule_fn):
    out = []
    for _, e in ev.iterrows():
        r = e.release_date
        i0 = first_on_after(cal, r); i1 = i0 + 1
        if i1 >= len(cal):
            continue
        rule = rule_fn(r)
        m = members(r, i0 - 1, rule)
        perm = m.permno.to_numpy(); w = m.cap.to_numpy()
        rr = {}
        for lab, i in [("0", i0), ("1", i1)]:
            x = day_ret(perm, i)
            ok = np.isfinite(x)
            rr[f"ew{lab}"] = float(np.mean(x[ok])) if ok.any() else np.nan
            rr[f"vw{lab}"] = float(np.sum(w[ok] * x[ok]) / np.sum(w[ok])) if ok.any() else np.nan
            rr[f"n{lab}"] = int(ok.sum())
            rr[f"mkt{lab}"] = float(mkt.loc[cal[i]])
        q = e.fred_date
        qp = (q - pd.DateOffset(months=3))
        s = float(y.loc[q] - y.loc[qp])
        hist = y[y.index < q]
        Xh = sm.add_constant(hist.shift(1).dropna().to_numpy()); yh = hist.iloc[1:].to_numpy()
        b = np.linalg.lstsq(Xh, yh, rcond=None)[0]
        u = float(y.loc[q] - (b[0] + b[1] * y.loc[qp]))
        out.append(dict(fred_date=q.date(), release_date=r.date(), year=r.year, day0=cal[i0].date(), day1=cal[i1].date(), rule=rule,
                        n_members=len(m), drtscilm=float(y.loc[q]), s=s, u_ar1=u, ar1_a=b[0], ar1_rho=b[1], n_hist=len(yh), **rr))
    E = pd.DataFrame(out)
    for k in ["ew", "vw"]:
        E[f"AR0_{k}"] = (E[f"{k}0"] - E.mkt0) * 100
        E[f"AR1_{k}"] = (E[f"{k}1"] - E.mkt1) * 100
        E[f"CAR_{k}"] = E[f"AR0_{k}"] + E[f"AR1_{k}"]
    E["MKT01"] = (E.mkt0 + E.mkt1) * 100
    return E


def reg(tid, sample, E, ycol, xcol, sign=-1, verdict_on=False, halves=((1997, 2010), (2011, 2024))):
    a = ols_slope(E[ycol], E[xcol] / 10.0, cov="HC0")
    hs = []
    for lo, hi in halves:
        z = E[(E.year >= lo) & (E.year <= hi)]
        h = ols_slope(z[ycol], z[xcol] / 10.0, cov="HC0"); hs.append(h)
    v = verdict(a["t"], [h["b"] for h in hs], sign=sign) if verdict_on else "reported only"
    res.add(tid, sample, n=a["n"], slope_pct_per10pp=a["b"], t_white=a["t"], intercept=a["a"], r2=a["r2"],
            crit_exact_df=float(st.t.ppf(1 - 0.0125, a["n"] - 2)), verdict=v)
    for (lo, hi), h in zip(halves, hs):
        res.add(tid, f"{lo}-{hi}", n=h["n"], slope_pct_per10pp=h["b"], t_white=h["t"])
    log(f"{tid} [{sample}]: n={a['n']} slope={a['b']:+.3f}%/10pp t={a['t']:+.2f} | " +
        " | ".join(f"{lo}-{hi}: {h['b']:+.3f} (t {h['t']:+.2f}, n {h['n']})" for (lo, hi), h in zip(halves, hs)) + f" | verdict: {v}")
    return a


E = us_events(lambda r: "sic" if r < pd.Timestamp("2000-01-01") else "link")
E.to_csv(O + "s2_events.csv", index=False)
log("US events", len(E), "members per event: median", float(E.n_members.median()), "min", int(E.n_members.min()),
    "| SIC-rule events", int((E.rule == "sic").sum()))
print(E.groupby(E.year // 5 * 5)[["n_members", "n0", "n1"]].mean().round(1).to_string())
reg("S2_main_EW_CAR01", "1997-2024", E, "CAR_ew", "s", verdict_on=True)
reg("S2_day0_EW", "1997-2024", E, "AR0_ew", "s")
reg("S2_VW_CAR01", "1997-2024", E, "CAR_vw", "s")
reg("S2_market_01", "1997-2024", E, "MKT01", "s", sign=+1)
reg("S2_ar1_surprise_EW_CAR01", "1997-2024", E, "CAR_ew", "u_ar1")
# terciles
o = E.sort_values(["s", "release_date"]).reset_index(drop=True)
o["terc"] = pd.qcut(np.arange(len(o)), 3, labels=[1, 2, 3]).astype(int)
lo_ = o[o.terc == 1].CAR_ew; hi_ = o[o.terc == 3].CAR_ew
tw = st.ttest_ind(hi_, lo_, equal_var=False)
res.add("S2_terciles_EW_CAR01", "1997-2024", n_bottom=len(lo_), mean_bottom=lo_.mean(), t_bottom=lo_.mean() / (lo_.std(ddof=1) / np.sqrt(len(lo_))),
        s_range_bottom=f"{o[o.terc == 1].s.min():.1f}..{o[o.terc == 1].s.max():.1f}", n_top=len(hi_), mean_top=hi_.mean(),
        t_top=hi_.mean() / (hi_.std(ddof=1) / np.sqrt(len(hi_))), s_range_top=f"{o[o.terc == 3].s.min():.1f}..{o[o.terc == 3].s.max():.1f}",
        diff_top_minus_bottom=hi_.mean() - lo_.mean(), t_welch=tw.statistic)
log(f"terciles: bottom (s {o[o.terc == 1].s.min():.1f}..{o[o.terc == 1].s.max():.1f}) mean CAR {lo_.mean():+.3f}% | top "
    f"(s {o[o.terc == 3].s.min():.1f}..{o[o.terc == 3].s.max():.1f}) {hi_.mean():+.3f}% | diff {hi_.mean() - lo_.mean():+.3f} Welch t {tw.statistic:+.2f}")
E.to_csv(O + "s2_events.csv", index=False)
# second reading: link-table universe in all years
E2 = us_events(lambda r: "link")
E2.to_csv(O + "s2_events_alt_link.csv", index=False)
reg("S2_alt_link_all_years_EW_CAR01", "1997-2024", E2, "CAR_ew", "s")
log("alt-link: pre-2000 members median", float(E2[E2.year < 2000].n_members.median()), "vs SIC rule", float(E[E.year < 2000].n_members.median()))
del idx, px

# ================================================================ EZ / UK auxiliary
con = connect()
q = con.execute(f"""
WITH s AS (SELECT l.fid, CAST(g.datadate AS DATE) date, g.prccd * g.trfd / g.ajexdi adj
           FROM '{O1}g_secd_stoxx600_min.parquet' g JOIN '{O3}eu_listing_ids.parquet' l ON g.gvkey = l.gvkey AND g.iid = l.iid
           WHERE g.prccd > 0 AND g.ajexdi > 0 AND g.trfd IS NOT NULL AND g.datadate <= DATE '2026-05-01'),
s2 AS (SELECT fid, date, ln(adj / lag(adj) OVER (PARTITION BY fid ORDER BY date)) lr FROM s WHERE adj > 0),
s3 AS (SELECT * FROM s2 WHERE lr IS NOT NULL AND isfinite(lr) AND abs(lr) < 1.5)
SELECT fid, date_diff('day', DATE '1970-01-01', date) d, SUM(lr) OVER (PARTITION BY fid ORDER BY date ROWS UNBOUNDED PRECEDING) lv FROM s3""").fetchnumpy()
keys = q["fid"].astype(np.int64) * MULT + q["d"].astype(np.int64)
o_ = np.argsort(keys, kind="stable"); keys = keys[o_]; lv = q["lv"].astype(float)[o_]
keep = np.concatenate([[True], np.diff(keys) > 0])
eidx = Keyed.__new__(Keyed); eidx.keys = keys[keep]; eidx.cols = {"lv": lv[keep]}
log("EU index rows", len(eidx.keys), "duplicates dropped", int((~keep).sum()))
lid = pd.read_parquet(O3 + "eu_listing_ids.parquet")
comp = pd.read_parquet(C + "eu_company.parquet")


def eu_universe(path, euro_only):
    u = pd.read_parquet(path).dropna(subset=["gvkey", "iid"]).copy()
    u["gvkey"] = u.gvkey.astype(str); u["iid"] = u.iid.astype(str)
    u = u.merge(lid, on=["gvkey", "iid"], how="inner").merge(comp[["gvkey", "ggroup", "loc"]].rename(columns={"loc": "gloc"}), on="gvkey", how="left")
    u["from_date"] = pd.to_datetime(u.from_date); u["thru"] = pd.to_datetime(u.thru)
    u["bank"] = u.ggroup == "4010"
    if euro_only:
        u = u[u.gloc.isin(EURO)]
    return u


def eu_events(reg_, upath, euro_only, relfile, col, y0, y1):
    calr = eu_calendar(reg_); calrv = days(calr)
    u = eu_universe(upath, euro_only)
    rr = pd.read_csv(O1 + relfile, parse_dates=["release_date"])
    rr = rr.reset_index(drop=True)
    rr["d"] = rr[col] - rr[col].shift(1)
    rr = rr[rr.release_date.notna() & (rr.release_date.dt.year >= y0) & (rr.release_date.dt.year <= y1)]
    out = []
    for _, e in rr.iterrows():
        r = e.release_date
        m = u[(u.from_date <= r) & (u.thru.isna() | (u.thru >= r))].drop_duplicates("fid")
        i0 = first_on_after(calr, r)
        if i0 + 1 >= len(calr):
            continue
        rec = {}
        for lab, i in [("0", i0), ("1", i0 + 1)]:
            fid = m.fid.to_numpy()
            has = eidx.has_exact(fid, calrv[i])
            _, a = eidx.lookup(fid, calrv[i], "lv")
            _, b = eidx.lookup(fid, calrv[i - 1], "lv", stale_min=calrv[i - 6])
            x = np.where(has, np.exp(a - b) - 1, np.nan)
            ok = np.isfinite(x); bk = ok & m.bank.to_numpy()
            rec[f"all{lab}"] = float(np.mean(x[ok])) if ok.any() else np.nan
            rec[f"bank{lab}"] = float(np.mean(x[bk])) if bk.any() else np.nan
            rec[f"nall{lab}"] = int(ok.sum()); rec[f"nbank{lab}"] = int(bk.sum())
        out.append(dict(release_date=r.date(), year=r.year, day0=calr[i0].date(), level=e[col], s=e.d, n_members=len(m),
                        n_banks=int(m.bank.sum()), **rec))
    E = pd.DataFrame(out)
    E["CAR_ew"] = ((E.bank0 - E.all0) + (E.bank1 - E.all1)) * 100
    return E


for tid, reg_, upath, eo, relf, col, y0, y1 in [
        ("S2_aux_EZ", "EZ", S3C + "stoxx600_eurozone_universe_2026-05-06.parquet", True, "release_dates_EZ_BLS.csv", "wfnet", 2003, 2024),
        ("S2_aux_EZ_broad", "EZ", S3C + "stoxx600_eurozone_universe_2026-05-06.parquet", False, "release_dates_EZ_BLS.csv", "wfnet", 2003, 2024),
        ("S2_aux_UK", "UK", S3C + "stoxx600_uk_universe_2026-05-06.parquet", False, "release_dates_UK_CCS.csv", "neg_availability", 2007, 2024)]:
    Ee = eu_events(reg_, upath, eo, relf, col, y0, y1)
    Ee.to_csv(O + f"s2_events_{tid.replace('S2_aux_', '')}.csv", index=False)
    log(tid, "events", len(Ee), "banks per event median", float(Ee.n_banks.median()), "members median", float(Ee.n_members.median()),
        "| events with missing s:", int(Ee.s.isna().sum()))
    reg(tid, f"{y0}-{y1}", Ee.dropna(subset=["s", "CAR_ew"]), "CAR_ew", "s", halves=())  # spec: same regression, full sample only
res.save(O + "results_s2.csv")
log("done")
