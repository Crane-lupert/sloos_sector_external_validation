# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / step 04 - Step 0 inspection of the remaining inputs (headers, ranges, duplicates). No outcome statistics."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import os
import duckdb
import numpy as np
import pandas as pd

DUMP = WRDS_DUMP + ""
W = V3WORK + ""
P4 = W + "phase4/"
S3C = REPO_CACHE
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 100); pd.set_option("display.max_rows", 200)
con = duckdb.connect(); con.execute("SET threads=4"); con.execute("SET memory_limit='6GB'"); con.execute(f"SET temp_directory='{P4}tmp'")


def hdr(f):
    return con.execute(f"SELECT * FROM read_csv('{DUMP}{f}', header=true, all_varchar=true) LIMIT 2").fetchdf()


# other_1 / bhck_2 duplicates
for f, its in [("bank_all.wrds_holding_other_1.csv.gz", ["bhdm1797", "bhdm5367", "bhdm1460", "bhdm1415"]),
               ("bank_all.wrds_holding_bhck_2.csv.gz", ["bhck2170", "bhck2122", "bhck3210"])]:
    sql = ", ".join(f"TRY_CAST({c} AS DOUBLE) {c}" for c in its)
    d = con.execute(f"SELECT CAST(rssd9001 AS BIGINT) rssd9001, CAST(rssd9999 AS VARCHAR) rssd9999, wrdsdownloaddate, {sql} "
                    f"FROM read_csv('{DUMP}{f}', header=true, all_varchar=true)").fetchdf()
    dup = d[d.duplicated(["rssd9001", "rssd9999"], keep=False)]
    k = dup.groupby(["rssd9001", "rssd9999"])
    print(f, "rows", len(d), "dup rows", len(dup), "dup keys", k.ngroups)
    print("  dup keys by date (top):", dup.rssd9999.value_counts().head(8).to_dict())
    print("  download dates among dups:", dup.wrdsdownloaddate.value_counts().head(6).to_dict())
    nn = k[its[0]].apply(lambda x: x.notna().sum())
    print(f"  non-null {its[0]} per dup key:", nn.value_counts().to_dict())
    print(f"  keys with >1 distinct non-null {its[0]}:", int((k[its[0]].nunique(dropna=True) > 1).sum()))

# CRSP legacy files
for f in ["crsp_a_stock.dsf.csv.gz", "crsp_a_stock.dsenames.csv.gz", "crsp_a_stock.dsedelist.csv.gz", "crsp_a_stock.dsi.csv.gz"]:
    print(f, hdr(f).columns.tolist())
p1 = W + "out/crsp_dsf_pit_min.parquet"
print("phase-1 dsf extract:", con.execute(f"SELECT min(date), max(date), count(*), count(distinct permno) FROM '{p1}'").fetchone(),
      con.execute(f"SELECT * FROM '{p1}' LIMIT 1").fetchdf().columns.tolist())
print("dsi range:", con.execute(f"SELECT min(date), max(date) FROM read_csv('{DUMP}crsp_a_stock.dsi.csv.gz', header=true, all_varchar=true) "
                                f"WHERE TRY_CAST(vwretd AS DOUBLE) IS NOT NULL").fetchone())
dn = con.execute(f"SELECT * FROM read_csv('{DUMP}crsp_a_stock.dsenames.csv.gz', header=true, all_varchar=true)").fetchdf()
print("dsenames rows", len(dn), "nameendt max", dn.nameendt.max(), "siccd sample", dn.siccd.dropna().head(3).tolist())
sic = pd.to_numeric(dn.siccd, errors="coerce")
banksic = dn[sic.between(6020, 6029) | sic.between(6710, 6712)]
print("dsenames rows with bank SIC:", len(banksic), "permnos", banksic.permno.nunique(), "permcos", banksic.permco.nunique())
lk = con.execute(f"SELECT * FROM read_csv('{DUMP}bank_all.wrds_bank_crsp_link.csv.gz', header=true, all_varchar=true)").fetchdf()
lp = set(lk.permco.astype(int))
dpc = dn[pd.to_numeric(dn.permco, errors="coerce").isin(lp)]
print("dsenames permnos for linked permcos:", dpc.permno.nunique(), "of permcos", len(lp), "matched permcos", dpc.permco.nunique())
print("union bank permnos:", len(set(dpc.permno) | set(banksic.permno)))
s2 = pd.to_numeric(dpc.siccd, errors="coerce")
print("SIC of linked permco name rows (top):", s2.value_counts().head(12).to_dict())

# FF monthly files
for f in ["ff_all.fivefactors_monthly.csv.gz", "ff_all.factors_monthly.csv.gz", "ff_all.fivefactors_daily.csv.gz", "ff_all.factors_daily.csv.gz"]:
    h = con.execute(f"SELECT * FROM read_csv('{DUMP}{f}', header=true, all_varchar=true)").fetchdf()
    print(f, h.columns.tolist(), len(h), h.iloc[0].tolist(), h.iloc[-1].tolist())

# EU / UK inputs
for f in [W + "out/g_secd_stoxx600_min.parquet", S3C + "stoxx600_eurozone_universe_2026-05-06.parquet", S3C + "stoxx600_uk_universe_2026-05-06.parquet",
          W + "phase3/out/eu_listing_ids.parquet"]:
    x = pd.read_parquet(f)
    print(os.path.basename(f), x.shape, x.columns.tolist())
    print(x.head(2).to_string())
print([f for f in os.listdir(S3C)])
gc = hdr("comp_global_daily.g_company.csv.gz")
print("g_company cols:", gc.columns.tolist())
gs = hdr("comp_global_daily.g_secd.stoxx600_2003plus.csv.gz")
print("g_secd stoxx cols:", gs.columns.tolist())
print([f for f in os.listdir(DUMP) if f.startswith("comp_global_daily")])
for reg in ["EZ_BLS", "UK_CCS"]:
    r = pd.read_csv(W + f"out/release_dates_{reg}.csv")
    print(reg, r.shape, r.columns.tolist()); print(r.head(3).to_string()); print(r.tail(2).to_string())
for reg in ["EZ", "UK", "US"]:
    e = pd.read_csv(W + f"phase3/out/events_allq_{reg}.csv")
    print("events_allq", reg, e.shape, e.columns.tolist()); print(e.head(2).to_string())
