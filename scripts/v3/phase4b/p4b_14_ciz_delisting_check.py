# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / Step 0 - CIZ (dsf_v2) delisting layout vs stkdelists, and the dsf_v2 trading calendar vs dsi. No portfolio returns.
Output: logs/p4b_14_ciz_delisting_check.log"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import pandas as pd

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
C = V3WORK + "phase4b/cache/"
v = pd.read_parquet(C + "crsp_bank_dsfv2_2024_25.parquet")
v["date"] = pd.to_datetime(v.date)
sd = pd.read_parquet(C + "stkdelists.parquet")
sd["permno"] = sd.permno.astype(int); sd["delistingdt"] = pd.to_datetime(sd.delistingdt, errors="coerce")
sd["delret"] = pd.to_numeric(sd.delret, errors="coerce")
y = v[v.dlydelflg == "Y"].copy()
print("dsf_v2 rows with dlydelflg=Y:", len(y), "dates", y.date.min().date(), "..", y.date.max().date())
m = y.merge(sd[["permno", "delistingdt", "delret", "delactiontype", "delpaymenttype", "delretmisstype"]], on="permno", how="left")
m["days_after_delistingdt"] = (m.date - m.delistingdt).dt.days
m["ret_eq_delret"] = (m.ret - m.delret).abs() < 1e-6
print(m[["permno", "date", "ret", "prc", "dlyretmissflg", "dlyprcflg", "delistingdt", "days_after_delistingdt", "delret", "delactiontype",
         "delpaymenttype", "ret_eq_delret"]].to_string(index=False))
print("dlyret == delret:", int(m.ret_eq_delret.sum()), "of", len(m), "| delisting row is the permno's last record:",
      int(y.set_index(["permno", "date"]).index.isin(v.sort_values(["permno", "date"]).groupby("permno").tail(1).set_index(["permno", "date"]).index).sum()))
dsi = pd.read_parquet(C + "dsi_1989_2025.parquet"); dsi["date"] = pd.to_datetime(dsi.date)
cnt = v.groupby("date").size(); calv2 = cnt[cnt >= 100].index
ov = set(dsi[(dsi.date >= "2024-06-03") & (dsi.date <= "2024-12-31")].date)
mine = set(calv2[(calv2 >= "2024-06-03") & (calv2 <= "2024-12-31")])
print("calendar 2024-06-03..2024-12-31: dsi", len(ov), "dsf_v2 (>=100 records)", len(mine), "identical", ov == mine,
      "| dsf_v2 trading days in 2025:", int(((calv2 >= "2025-01-01") & (calv2 <= "2025-12-31")).sum()))
