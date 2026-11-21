# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / step 21 - implementation self-checks of p4b_20 (independent re-derivations; no new specifications).

 1. per-period LS_BT / LS_CRE rebuilt from the bank table with an independent quintile assignment (pandas rank, not the
    p4b_20 sort) -> max |diff| vs out/h1h2_1990s_periods.csv
 2. H1 mean / t and H2 slope / t re-derived with a hand-written Newey-West (Bartlett, 1 lag) estimator; both the plain
    and the n/(n-k) small-sample scaled variance are printed next to the statsmodels value
 3. holding returns of 40 random bank-periods re-compounded directly from the raw dsf extract (ret, missing -> 0) and
    delisting records -> max |diff|
 4. timing: entry strictly after the (approximate) release; approximate releases enter exactly 10 trading days after the
    approximate date; every report used is dated <= q* and q* + 75 days <= release date; link validity at the decision date
 5. legs: quintile sizes, weights sum to 1 (EW), no duplicate banks
Run: python -E -P p4b_21_checks.py   (output -> logs/p4b_21_checks.log)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import sys
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from p4blib import *

rng = np.random.default_rng(20261121)
B = pd.read_parquet(O + "h1h2_1990s_bank_table.parquet")
S = pd.read_csv(O + "h1h2_1990s_periods.csv", parse_dates=["release_date", "t0", "exit", "fred_date"])
for c in ["release_date", "t0", "exit", "decision_date", "qstar", "y9c_date", "fred_date"]:
    B[c] = pd.to_datetime(B[c])

# 1. independent quintiles
rows = []
for p, g in B[B.screen].groupby("period"):
    g = g.copy()
    n = len(g)
    for col, nm in [("BT", "bt"), ("share_CRE", "cre")]:
        rk = g[[col, "permno"]].apply(tuple, axis=1).rank(method="first")
        g[f"q_{nm}"] = np.ceil(5 * rk / n).astype(int)
    rows.append(dict(period=p, LS_BT=(g[g.q_bt == 1].R.mean() - g[g.q_bt == 5].R.mean()) * 100,
                     LS_CRE=(g[g.q_cre == 1].R.mean() - g[g.q_cre == 5].R.mean()) * 100,
                     same_q_bt=bool((g.q_bt == g.q_bt_main).all()), same_q_cre=bool((g.q_cre == g.q_cre_main).all())))
I = pd.DataFrame(rows).merge(S[["period", "LS_BT", "LS_CRE"]], on="period", suffixes=("_indep", ""))
print("[1] periods", len(I), "| max |LS_BT diff|", float((I.LS_BT_indep - I.LS_BT).abs().max()), "| max |LS_CRE diff|",
      float((I.LS_CRE_indep - I.LS_CRE).abs().max()), "| identical quintiles BT / CRE in all periods:", bool(I.same_q_bt.all()), bool(I.same_q_cre.all()))


# 2. hand-written Newey-West
def nw_by_hand(y, X, L=1):
    y = np.asarray(y, float); X = np.asarray(X, float)
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    u = y - X @ b
    Z = X * u[:, None]
    Sm = Z.T @ Z
    for l in range(1, L + 1):
        w = 1 - l / (L + 1)
        G = Z[l:].T @ Z[:-l]
        Sm += w * (G + G.T)
    V = XtX_inv @ Sm @ XtX_inv
    return b, np.sqrt(np.diag(V)), np.sqrt(np.diag(V * n / (n - k)))


b, se, se_c = nw_by_hand(S.LS_BT.values, np.ones((len(S), 1)))
sm1 = sm.OLS(S.LS_BT.values, np.ones(len(S))).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
print(f"[2] H1 mean {b[0]:+.4f}: t by hand {b[0] / se[0]:+.4f} (no df scaling) / {b[0] / se_c[0]:+.4f} (n/(n-k)); statsmodels {sm1.tvalues[0]:+.4f}")
X = np.column_stack([np.ones(len(S)), S.N_CRE.values / 10])
b, se, se_c = nw_by_hand(S.LS_CRE.values, X)
sm2 = sm.OLS(S.LS_CRE.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
print(f"[2] H2 slope {b[1]:+.4f}: t by hand {b[1] / se[1]:+.4f} (no df scaling) / {b[1] / se_c[1]:+.4f} (n/(n-k)); statsmodels {sm2.tvalues[1]:+.4f}; "
      f"plain OLS t {sm.OLS(S.LS_CRE.values, X).fit().tvalues[1]:+.4f}")

# 3. holding returns from the raw extract
d = pd.read_parquet(C + "crsp_bank_dsf_1990s.parquet", columns=["permno", "date", "ret"])
d["date"] = pd.to_datetime(d.date)
dl = pd.read_parquet(P4C + "delist.parquet")
smp = B[B.screen].sample(40, random_state=7)
diffs = []
for _, r in smp.iterrows():
    x = d[(d.permno == r.permno) & (d.date > r.t0) & (d.date <= r.exit)].sort_values("date")
    rr = x.ret.fillna(0).clip(lower=-1).values
    R = np.prod(1 + np.where(rr < -1, 0, rr)) - 1
    z = dl[(dl.permno == r.permno) & (dl.dlstcd >= 200)]
    if len(z):
        dd = pd.Timestamp(z.dlstdt.iloc[-1])
        lastd = d[d.permno == r.permno].date.max()
        when = max(dd, lastd + pd.Timedelta(days=1))
        if r.t0 < when <= r.exit:
            dr = z.dlret.iloc[-1]
            if not np.isfinite(dr):
                dr = (-0.55 if z.exchcd.iloc[-1] == 3 else -0.30) if 500 <= z.dlstcd.iloc[-1] <= 599 else 0.0
            R = (1 + R) * (1 + dr) - 1
    diffs.append(abs(R - r.R))
print(f"[3] 40 random main-universe bank-periods: max |R(recompounded) - R(table)| = {max(diffs):.2e}; delisted among them: "
      f"{int(smp.delisted_in_period.sum())}; delisted positions in the main universe overall: {int(B[B.screen].delisted_in_period.sum())}")
# 3b. all delisted main-universe positions (delisting return compounded once, cash afterwards)
dd_ = B[B.screen & B.delisted_in_period]
diffs, nmiss, codes = [], 0, []
for _, r in dd_.iterrows():
    x = d[(d.permno == r.permno) & (d.date > r.t0) & (d.date <= r.exit)].sort_values("date")
    rr = x.ret.fillna(0).values
    R = np.prod(1 + np.where(rr < -1, 0, rr)) - 1
    z = dl[(dl.permno == r.permno) & (dl.dlstcd >= 200)].sort_values("dlstdt")
    dr = z.dlret.iloc[-1]
    codes.append(int(z.dlstcd.iloc[-1]))
    if not np.isfinite(dr):
        nmiss += 1
        dr = (-0.55 if z.exchcd.iloc[-1] == 3 else -0.30) if 500 <= z.dlstcd.iloc[-1] <= 599 else 0.0
    R = (1 + R) * (1 + max(dr, -0.9999)) - 1
    diffs.append(abs(R - r.R))
cc = pd.Series(codes).floordiv(100).mul(100).value_counts().to_dict()
print(f"[3b] all {len(dd_)} delisted main-universe positions: max |R(recompounded incl. delisting return) - R(table)| = {max(diffs):.2e}; "
      f"missing dlret substituted {nmiss}; delisting code families {cc}")

# 4. timing
cal = pd.DatetimeIndex(pd.read_parquet(C + "dsi_1989_2025.parquet").date)
P = B.drop_duplicates("period")
ok_entry = (P.t0 > P.release_date).all()
ap = P[P.approx_date]
k10 = [int(np.searchsorted(cal.values, np.datetime64(t), side="left") - np.searchsorted(cal.values, np.datetime64(r), side="right")) + 1
       for t, r in zip(ap.t0, ap.release_date)]
print(f"[4] entry strictly after release in all {len(P)} periods: {bool(ok_entry)}; approximate releases ({len(ap)}): trading-day position of the entry after "
      f"the approximate date = {sorted(set(k10))}; report date <= q*: {bool((B.y9c_date <= B.qstar).all())}; q* + 75d <= release: "
      f"{bool(((P.qstar + pd.Timedelta(days=75)) <= P.release_date).all())}; report age at release (days) min {int((P.release_date - P.qstar).dt.days.min())} max {int((P.release_date - P.qstar).dt.days.max())}; "
      f"banks on the fallback (older) report: {int((B.y9c_date < B.qstar).sum())} of {len(B)}")
lk = pd.read_parquet(P4C + "link.parquet")
lk = lk[lk.inst_type.str.lower() == "bank holding company"].copy()
lk["dt_start"] = pd.to_datetime(lk.dt_start); lk["dt_end"] = pd.to_datetime(lk.dt_end)
m = B.merge(lk, on=["rssd9001", "permco"], how="left")
m["D"] = np.where(m.approx_date, m.decision_date, m.release_date)
m["valid"] = (m.dt_start <= m.D) & (m.dt_end >= m.D)
print(f"[4] link valid at the decision date for every bank-release: {bool(m.groupby(['period', 'permno']).valid.any().all())}")

# 5. legs
z = B[B.screen].groupby("period").agg(n=("permno", "size"), q1=("q_bt_main", lambda s: int((s == 1).sum())), q5=("q_bt_main", lambda s: int((s == 5).sum())),
                                      c1=("q_cre_main", lambda s: int((s == 1).sum())), c5=("q_cre_main", lambda s: int((s == 5).sum())),
                                      dup=("permno", lambda s: int(s.duplicated().sum())))
print(f"[5] main-universe n per period min {z.n.min()} max {z.n.max()}; BT legs Q1 {z.q1.min()}-{z.q1.max()}, Q5 {z.q5.min()}-{z.q5.max()}; "
      f"CRE legs low {z.c1.min()}-{z.c1.max()}, high {z.c5.min()}-{z.c5.max()}; duplicate permnos {int(z.dup.sum())}")
print(f"[5] raw shares sum to 1 (CI+CRE+RRE+CONS): {bool(np.allclose(B[['share_CI', 'share_CRE', 'share_RRE', 'share_CONS']].sum(axis=1), 1))}; "
      f"renormalised shares sum to 1: {bool(np.allclose(B[[f'sh2_{k}' for k in CATS]].sum(axis=1), 1))}; banks with a 1990Q3/Q4 report (no CC/OC split): "
      f"{int(B.share_CC.isna().sum())} rows, all at releases before 1996: {bool((B[B.share_CC.isna()].fred_date < '1996-01-01').all())}")
