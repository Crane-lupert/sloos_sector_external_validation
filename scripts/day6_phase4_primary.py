"""Day 6 — Phase 4 PRIMARY 4 tests on Eurozone CAR panel.

(a) F-test sector heterogeneity (already done Day 4)
(b) Bootstrap CI on cell t-stats (1000 event-resample iters)
(c) Alt event def Spearman: ECB BLS DE/FR/IT/ES vs aggregate
(d) VIX-regime stratification
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as st


def load_env():
    env_text = Path(".env").read_text()
    for line in env_text.splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip("\"").strip("'")


def main() -> None:
    load_env()
    eu_panel = pd.read_parquet("data/cache/comp_global_panel_eurozone_2026-05-06.parquet")
    GICS = {10: "Energy", 15: "Mat", 20: "Indus", 25: "CDisc", 30: "CSta",
            35: "Health", 40: "Fin", 45: "IT", 50: "Comm", 55: "Util", 60: "RE"}

    # ============ PRIMARY (b): Bootstrap CI on cell t-stats ============
    print("=" * 70)
    print("PRIMARY (b): Bootstrap CI on cell t-stats")
    print("=" * 70)
    rng = np.random.default_rng(42)
    n_iter = 1000
    event_dates = sorted(eu_panel["event_date"].unique())
    n_events = len(event_dates)
    boot_results = []

    for (sector, horizon), g_full in eu_panel.dropna(subset=["car"]).groupby(["sector", "horizon"]):
        t_stats_boot = []
        for it in range(n_iter):
            sampled = rng.choice(event_dates, size=n_events, replace=True)
            sub = g_full[g_full["event_date"].isin(sampled)]
            v = sub["car"].values
            if len(v) < 10:
                continue
            m = np.mean(v); s = np.std(v, ddof=1)
            if s == 0:
                continue
            t_stats_boot.append(m / (s / np.sqrt(len(v))))
        if len(t_stats_boot) < 50:
            continue
        t_arr = np.array(t_stats_boot)
        ci_lo = float(np.percentile(t_arr, 5))
        ci_hi = float(np.percentile(t_arr, 95))
        t_mean = float(np.mean(t_arr))
        crit = 3.17
        boot_pass = (ci_lo > crit) or (ci_hi < -crit)
        boot_results.append({"sector": int(sector), "horizon": horizon, "t_mean_boot": t_mean,
                             "ci_5": ci_lo, "ci_95": ci_hi, "pass_b": bool(boot_pass)})

    bdf = pd.DataFrame(boot_results)
    n_pass_b = int(bdf["pass_b"].sum())
    print(f"Cells passing bootstrap (90% CI excludes Bonferroni critical): {n_pass_b}/33")
    sig_b = bdf[bdf["pass_b"]].sort_values("t_mean_boot", key=abs, ascending=False)
    for _, r in sig_b.iterrows():
        name = GICS.get(r["sector"], str(r["sector"]))
        print(f"  {name:6s} {r['horizon']:3s}  t_mean={r['t_mean_boot']:+6.2f}  90%CI=[{r['ci_5']:+6.2f}, {r['ci_95']:+6.2f}]")
    bdf.to_parquet("data/cache/phase4_primary_b_bootstrap_eurozone_2026-05-06.parquet")

    # ============ PRIMARY (c): Alt event def — DE/FR/IT/ES vs aggregate ============
    print()
    print("=" * 70)
    print("PRIMARY (c): Alt event def Spearman (DE/FR/IT/ES per-country vs U2 aggregate)")
    print("=" * 70)
    from sloos_sector_external_validation import ecb_bls_fetch
    from sloos_sector_external_validation.shock_construct import construct_shocks

    primary_shocks, _ = ecb_bls_fetch.fetch_and_construct_shocks(threshold=1.0)

    def sector_mean(panel, ev, h="6m"):
        sub = panel[panel["event_date"].isin(ev) & (panel["horizon"] == h) & panel["car"].notna()]
        return sub.groupby("sector")["car"].mean()

    primary_events = primary_shocks.index[primary_shocks["is_event_start"].fillna(False)]
    primary_pattern = sector_mean(eu_panel, primary_events, "6m")
    print(f"Aggregate primary events: n={len(primary_events)}")

    per_country = ecb_bls_fetch.fetch_ecb_bls_per_country()
    results_c = {}
    for ctry, series in per_country.items():
        panel_c = ecb_bls_fetch.to_panel(series)
        shocks_c = construct_shocks(panel_c, primary_series=series.name, threshold=1.0)
        events_c = shocks_c.index[shocks_c["is_event_start"].fillna(False)]
        if len(events_c) < 5:
            print(f"  {ctry}: only {len(events_c)} events, skipped")
            continue
        pattern_c = sector_mean(eu_panel, events_c, "6m")
        common = primary_pattern.index.intersection(pattern_c.index)
        rho, p = st.spearmanr(primary_pattern.loc[common].values, pattern_c.loc[common].values)
        verdict = "PASS" if rho >= 0.5 else "FAIL"
        print(f"  {ctry}: events={len(events_c):2d}  Spearman rho={rho:+.3f}  p={p:.3f}  [{verdict}]")
        results_c[ctry] = {"n_events": int(len(events_c)), "spearman_rho": float(rho), "p_value": float(p),
                           "pass_05": bool(rho >= 0.5)}
    n_country_pass = sum(r["pass_05"] for r in results_c.values())
    print(f"\nPASS PRIMARY (c)? n_country_pass >= 3: {n_country_pass >= 3} ({n_country_pass}/4)")

    # ============ PRIMARY (d): VIX regime stratification ============
    print()
    print("=" * 70)
    print("PRIMARY (d): VIX-regime stratification (high vs low VIX events)")
    print("=" * 70)
    from fredapi import Fred
    fred = Fred(api_key=os.environ["FRED_API_KEY"])
    vix = fred.get_series("VIXCLS")
    vix.index = pd.to_datetime(vix.index)
    vix_median = float(vix.median())
    print(f"VIX median (full sample): {vix_median:.2f}")

    event_vix = []
    for e in event_dates:
        sub = vix.loc[vix.index <= e].tail(1)
        if not sub.empty:
            event_vix.append({"event_date": e, "vix": float(sub.iloc[0])})
    vix_df = pd.DataFrame(event_vix)
    high_events = vix_df[vix_df["vix"] >= vix_median]["event_date"].tolist()
    low_events = vix_df[vix_df["vix"] < vix_median]["event_date"].tolist()
    print(f"High-VIX events: {len(high_events)}, Low-VIX events: {len(low_events)}")

    high_pat = sector_mean(eu_panel, high_events, "6m")
    low_pat = sector_mean(eu_panel, low_events, "6m")

    print()
    print(f"{'Sector':6s}  {'high_VIX':>10s}  {'low_VIX':>10s}  status")
    sign_agree = 0
    for sec in sorted(set(high_pat.index) | set(low_pat.index)):
        name = GICS.get(sec, str(sec))
        h = high_pat.get(sec, np.nan)
        l = low_pat.get(sec, np.nan)
        if not (np.isnan(h) or np.isnan(l)):
            if np.sign(h) == np.sign(l):
                sign_agree += 1
                status = "AGREE"
            else:
                status = "DISAGREE"
        else:
            status = "N/A"
        h_str = f"{h*1e4:+8.1f}" if not np.isnan(h) else "  NA"
        l_str = f"{l*1e4:+8.1f}" if not np.isnan(l) else "  NA"
        print(f"  {name:4s}  {h_str}  {l_str}  {status}")
    print(f"\nSign agreement: {sign_agree}/11 sectors")
    print(f"PASS PRIMARY (d)? sign_agree >= 7: {sign_agree >= 7}")

    common = high_pat.index.intersection(low_pat.index)
    rho_d, p_d = (np.nan, np.nan)
    if len(common) >= 5:
        rho_d, p_d = st.spearmanr(high_pat.loc[common].values, low_pat.loc[common].values)
        print(f"Spearman (high vs low VIX regime): rho={rho_d:+.3f}  p={p_d:.3f}")

    # ============ Summary ============
    summary = {
        "date": "2026-05-06",
        "phase4_primary_a_f_test": "PASS 3/3 horizons (Day 4)",
        "phase4_primary_b_bootstrap": {"n_cells_pass": int(n_pass_b), "floor": 5,
                                        "pass": bool(n_pass_b >= 5)},
        "phase4_primary_c_alt_event_def": {"per_country": results_c,
                                            "n_country_pass": int(n_country_pass),
                                            "floor": 3, "pass": bool(n_country_pass >= 3)},
        "phase4_primary_d_vix_regime": {"sign_agreement": int(sign_agree), "floor": 7,
                                         "pass": bool(sign_agree >= 7),
                                         "spearman_rho": float(rho_d) if not np.isnan(rho_d) else None,
                                         "spearman_p": float(p_d) if not np.isnan(p_d) else None}
    }
    n_primary_pass = sum([True,
                          summary["phase4_primary_b_bootstrap"]["pass"],
                          summary["phase4_primary_c_alt_event_def"]["pass"],
                          summary["phase4_primary_d_vix_regime"]["pass"]])
    summary["n_primary_pass"] = n_primary_pass
    summary["regime_detection_finding_established"] = bool(n_primary_pass >= 3)
    Path("data/cache/phase4_primary_eurozone_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )

    print()
    print("=" * 70)
    print("PHASE 4 PRIMARY 4-TEST EUROZONE SUMMARY")
    print("=" * 70)
    print(f"  (a) F-test:          PASS 3/3 horizons (Day 4)")
    print(f"  (b) Bootstrap:       {'PASS' if n_pass_b >= 5 else 'FAIL'}  ({n_pass_b}/33, floor 5)")
    print(f"  (c) Alt event def:   {'PASS' if n_country_pass >= 3 else 'FAIL'}  ({n_country_pass}/4 countries)")
    print(f"  (d) VIX regime:      {'PASS' if sign_agree >= 7 else 'FAIL'}  ({sign_agree}/11 sectors)")
    print(f"\n  PRIMARY tests PASSED: {n_primary_pass}/4")
    print(f"  Regime detection finding established (>=3/4): {n_primary_pass >= 3}")


if __name__ == "__main__":
    main()
