# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / section 4 - post-sample record 2024-11 .. 2025 (record only, no test), FROZEN_PARAMS.json post_sample_2025.
Phase-4 S1 construction (p4_20_s1.py) with the period limit lifted; dsf_v2 (CIZ) daily data; last link / last name kept.
Also the data-path check: the last phase-4 period (release 2024-08-05) recomputed from dsf_v2 vs phase4/out/s1_ls_periods.csv.

Outputs: out/post2025_periods.csv, out/post2025_bank_table.parquet (+ .csv), out/post2025_datapath_check.csv, out/results_2025.csv
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import json
import numpy as np
import pandas as pd
from p4blib import *

pd.set_option("display.width", 250)
fz = json.load(open(P4B + "FROZEN_PARAMS.json", encoding="utf-8"))
res = Results()
v = pd.read_parquet(C + "crsp_bank_dsfv2_2024_25.parquet", columns=["date"])
cnt = pd.to_datetime(v.date).value_counts()
cal = pd.DatetimeIndex(sorted(cnt[cnt >= 100].index)); calv = days(cal)
print("calendar", cal.min().date(), "..", cal.max().date(), len(cal), "days")
N = pd.read_csv(P4O + "s1_N_by_release.csv", parse_dates=["fred_date", "release_date"])
Y = pd.read_parquet(P4C + "y9c_panel.parquet"); Y["date"] = pd.to_datetime(Y.date)
Yd = {k: g.set_index("date").sort_index() for k, g in Y.groupby("rssd9001")}
lk = pd.read_parquet(P4C + "link.parquet")
lk = lk[lk.inst_type.str.lower() == "bank holding company"].copy()
lk["dt_start"] = pd.to_datetime(lk.dt_start); lk["dt_end"] = pd.to_datetime(lk.dt_end)
lk["dt_end_open"] = lk.dt_end.where(lk.dt_end < lk.dt_end.max(), pd.Timestamp("2099-12-31"))
dn = pd.read_parquet(P4C + "dsenames.parquet")
dn["namedt"] = pd.to_datetime(dn.namedt); dn["nameendt"] = pd.to_datetime(dn.nameendt)
mx = dn.nameendt.max()
dn["nameendt_open"] = dn.nameendt.where(dn.nameendt < mx, pd.Timestamp("2099-12-31"))
print("dsenames nameendt max", mx.date(), "-> spells ending there treated as open-ended:", int((dn.nameendt == mx).sum()))
cs = dn[dn.shrcd.isin([10, 11]) & dn.exchcd.isin([1, 2, 3])]
empty = pd.DataFrame({"permno": pd.Series(dtype=int), "dlstdt": pd.Series(dtype="datetime64[ns]"), "dlstcd": pd.Series(dtype=float),
                      "dlret": pd.Series(dtype=float), "exchcd": pd.Series(dtype=float)})
idx, px, _ = us_index(C + "crsp_bank_dsfv2_2024_25.parquet", empty)
dv = pd.read_parquet(C + "crsp_bank_dsfv2_2024_25.parquet", columns=["permno", "date", "dlydelflg"])
dv["date"] = pd.to_datetime(dv.date)
deln = dv[dv.dlydelflg == "Y"]
sn = pd.read_parquet(C + "stocknames_v2.parquet")
sn["permno"] = sn.permno.astype(int); sn["namedt"] = pd.to_datetime(sn.namedt, errors="coerce"); sn["nameenddt"] = pd.to_datetime(sn.nameenddt, errors="coerce")


def qstar(r):
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


rel = N[N.release_date.notna() & (N.release_date >= "2024-08-05")].sort_values("release_date").reset_index(drop=True)
rel["i_t0"] = [first_after(cal, r) for r in rel.release_date]
rel = rel[rel.i_t0 < len(cal)].reset_index(drop=True)
rel["t0"] = cal[rel.i_t0.values]
rel["i_exit"] = rel.i_t0.shift(-1); rel["exit"] = rel.t0.shift(-1)
per = rel[rel.exit.notna()].copy().reset_index(drop=True)
per["i_exit"] = per.i_exit.astype(int)
per["qstar"] = per.release_date.map(qstar)
print(per[["fred_date", "release_date", "t0", "exit", "qstar"]].to_string(index=False))

rows, out = [], []
for p, e in per.iterrows():
    r = e.release_date; ir = last_on_before(cal, r); it0 = int(e.i_t0); ix = int(e.i_exit)
    L = lk[(lk.dt_start <= r) & (lk.dt_end_open >= r)][["rssd9001", "permco"]].drop_duplicates()
    S = cs[(cs.namedt <= r) & (cs.nameendt_open >= r)][["permno", "permco"]].drop_duplicates()
    c = L.merge(S, on="permco")
    _, prc = px.lookup(c.permno, calv[ir], "prc", stale_min=calv[ir - 5])
    _, cap = px.lookup(c.permno, calv[ir], "cap", stale_min=calv[ir - 5])
    c["prc_r"] = prc; c["cap_r"] = cap
    c = c[np.isfinite(c.cap_r) & (c.cap_r > 0)]
    c = c.sort_values(["rssd9001", "permco", "cap_r"], ascending=[True, True, False]).drop_duplicates(["rssd9001", "permco"])
    c = c.sort_values(["rssd9001", "cap_r"], ascending=[True, False]).drop_duplicates("rssd9001")
    q = e.qstar
    c["y9c_date"] = [y9c_at(int(x), q) for x in c.rssd9001]
    c = c[c.y9c_date.notna()].copy(); c["y9c_date"] = pd.to_datetime(c.y9c_date)
    yy = Y.merge(c[["rssd9001", "y9c_date"]], left_on=["rssd9001", "date"], right_on=["rssd9001", "y9c_date"])
    c = c.merge(yy.drop(columns=["date"]), on=["rssd9001", "y9c_date"])
    c = c.sort_values(["permco", "bhck2170"], ascending=[True, False]).drop_duplicates("permco")
    Nk = {k: e[f"N_{k}"] for k in CATS}
    avail = [k for k in CATS if np.isfinite(Nk[k])]
    ssum = c[[f"share_{k}" for k in avail]].sum(axis=1)
    c = c[ssum > 0].copy(); ssum = ssum[ssum > 0]
    for k in CATS:
        c[f"sh2_{k}"] = (c[f"share_{k}"] / ssum) if k in avail else 0.0
    c["BT"] = sum(c[f"sh2_{k}"] * Nk[k] for k in avail)
    _, lv0 = idx.lookup(c.permno, calv[it0], "lv", stale_min=calv[it0 - 5])
    _, prc0 = px.lookup(c.permno, calv[it0], "prc", stale_min=calv[it0 - 5])
    _, lvx = idx.lookup(c.permno, calv[ix], "lv")
    c["R"] = np.exp(lvx - lv0) - 1.0; c["lv_entry"] = lv0; c["prc_t0"] = prc0
    c = c[np.isfinite(c.lv_entry) & np.isfinite(c.R) & np.isfinite(c.prc_t0)].copy()
    c["delisted_in_period"] = c.permno.isin(set(deln[(deln.date > cal[it0]) & (deln.date <= cal[ix])].permno))
    c["screen"] = (c.prc_r >= 5) & (c.cap_r >= 100e6)
    c["period"] = p; c["release_date"] = r; c["fred_date"] = e.fred_date; c["t0"] = cal[it0]; c["exit"] = cal[ix]; c["qstar"] = q
    for u, m in [("main", c.screen.to_numpy()), ("nofilter", np.ones(len(c), bool))]:
        for sk, col in [("bt", "BT"), ("cre", "share_CRE")]:
            z = c[m].sort_values([col, "permno"], kind="mergesort")
            n = len(z)
            c[f"q_{sk}_{u}"] = np.nan
            c.loc[z.index, f"q_{sk}_{u}"] = np.ceil(5 * np.arange(1, n + 1) / n).astype(int)
    assert (c.y9c_date <= q).all() and c.permno.is_unique
    # CIZ name check (reported only)
    snr = sn[(sn.namedt <= r) & (sn.nameenddt >= r)].drop_duplicates("permno").set_index("permno")
    j = snr.reindex(c.permno)
    ciz_ok = ((j.securitytype == "EQTY") & (j.securitysubtype == "COM") & (j.sharetype == "NS") & (j.usincflg == "Y") & j.primaryexch.isin(["N", "A", "Q"])).to_numpy()
    c["ciz_common_ok"] = ciz_ok
    rows.append(c)
    for u in ["main", "nofilter"]:
        g = c if u == "nofilter" else c[c.screen]
        lo, hi = g[g[f"q_bt_{u}"] == 1], g[g[f"q_bt_{u}"] == 5]
        clo, chi = g[g[f"q_cre_{u}"] == 1], g[g[f"q_cre_{u}"] == 5]
        out.append(dict(universe=u, period=p, fred_date=e.fred_date.date(), release_date=r.date(), t0=cal[it0].date(), exit=cal[ix].date(),
                        qstar=q.date(), n=len(g), n_long=len(lo), n_short=len(hi), R_long=lo.R.mean() * 100, R_short=hi.R.mean() * 100,
                        LS_BT=(lo.R.mean() - hi.R.mean()) * 100, R_cre_low=clo.R.mean() * 100, R_cre_high=chi.R.mean() * 100,
                        LS_CRE=(clo.R.mean() - chi.R.mean()) * 100, N_CRE=Nk["CRE"], N_CI=Nk["CI"], N_RRE=Nk["RRE"], N_CC=Nk["CC"], N_OC=Nk["OC"],
                        creshare_low=clo.share_CRE.mean(), creshare_high=chi.share_CRE.mean(), R_all=g.R.mean() * 100,
                        n_delisted=int(g.delisted_in_period.sum()), n_ciz_name_mismatch=int((~g.ciz_common_ok).sum())))
P = pd.DataFrame(out)
Bt = pd.concat(rows, ignore_index=True)
keep = ["period", "fred_date", "release_date", "t0", "exit", "qstar", "permno", "permco", "rssd9001", "y9c_date"] + [f"share_{k}" for k in CATS] + \
       [f"sh2_{k}" for k in CATS] + ["BT", "q_bt_main", "q_bt_nofilter", "q_cre_main", "q_cre_nofilter", "screen", "R", "prc_r", "cap_r", "prc_t0",
                                     "delisted_in_period", "ciz_common_ok", "bhck2170"]
Bt[keep].to_parquet(O + "post2025_bank_table.parquet", index=False)
Bt[keep].to_csv(O + "post2025_bank_table.csv", index=False)

# data-path check on the last phase-4 period
p4 = pd.read_csv(P4O + "s1_ls_periods.csv", parse_dates=["release_date"])
p4l = p4[p4.release_date == pd.Timestamp("2024-08-05")].iloc[0]
mine = P[(P.universe == "main") & (P.release_date == pd.Timestamp("2024-08-05").date())].iloc[0]
chk = pd.DataFrame([dict(item=k, phase4_legacy_dsf=float(p4l[a]), phase4b_dsf_v2=float(mine[b]), diff=float(mine[b]) - float(p4l[a]))
                    for k, a, b in [("n", "n", "n"), ("n_long", "n_long", "n_long"), ("n_short", "n_short", "n_short"), ("R_long", "R_long", "R_long"),
                                    ("R_short", "R_short", "R_short"), ("LS", "LS", "LS_BT")]])
chk.to_csv(O + "post2025_datapath_check.csv", index=False)
print("\n[data-path check] release 2024-08-05 (last phase-4 period), legacy dsf (phase 4) vs dsf_v2 (this script):")
print(chk.round(4).to_string(index=False))

rec = P[P.release_date >= pd.Timestamp("2024-11-12").date()].copy()
rec.to_csv(O + "post2025_periods.csv", index=False)
print("\n[post-sample record, %] (no test; H1 = LS_BT expected > 0; H2 = LS_CRE with N_CRE)")
print(rec[["universe", "release_date", "t0", "exit", "qstar", "n", "n_long", "n_short", "LS_BT", "R_long", "R_short", "LS_CRE", "R_cre_low", "R_cre_high",
           "N_CRE", "N_CI", "n_delisted", "n_ciz_name_mismatch"]].round(3).to_string(index=False))
for u in ["main", "nofilter"]:
    z = rec[rec.universe == u]
    res.add("POST2025_H1", u, n_periods=len(z), mean_LS_BT=z.LS_BT.mean(), n_positive=int((z.LS_BT > 0).sum()),
            **{f"LS_BT_{d}": v for d, v in zip(z.release_date.astype(str), z.LS_BT)})
    res.add("POST2025_H2", u, n_periods=len(z), mean_LS_CRE=z.LS_CRE.mean(),
            **{f"LS_CRE_{d}": v for d, v in zip(z.release_date.astype(str), z.LS_CRE)},
            **{f"N_CRE_{d}": v for d, v in zip(z.release_date.astype(str), z.N_CRE)})
res.add("POST2025_datapath_check", "2024-08-05", **{f"diff_{a}": b for a, b in zip(chk.item, chk["diff"])})
res.save(O + "results_2025.csv")
print("saved")
