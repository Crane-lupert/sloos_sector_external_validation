# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4 / step 02 - Step 0 inspection of the bank dump files (no returns are read).

(1) wrds_bank_reg_vars: definitions and validity dates of the Y-9C items named in PHASE4_SPEC S1 (+ controls)
(2) header check: which file holds each item
(3) wrds_bank_crsp_link: columns, inst_type counts, date ranges, multiplicity
(4) Y-9C item coverage by year (share of filer-quarters with a non-null value), all filers and linked filers
Writes logs only (stdout) and cache/y9c_items.parquet (rssd9001, rssd9999, items; Y-9C values only).
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import duckdb
import pandas as pd

DUMP = WRDS_DUMP + ""
P4 = V3WORK + "phase4/"
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 120); pd.set_option("display.max_rows", 500)
con = duckdb.connect()
con.execute("SET threads=4"); con.execute("SET memory_limit='6GB'"); con.execute(f"SET temp_directory='{P4}tmp'")

ITEMS = ["bhck1763", "bhck1764", "bhck1766", "bhckf158", "bhckf159", "bhckf160", "bhckf161", "bhck1410", "bhck1975",
         "bhckb538", "bhckb539", "bhckk137", "bhckk207", "bhck2011", "bhck4635", "bhck4340",
         "bhck2122", "bhck2170", "bhck3210", "bhck4230", "bhck4605",
         "bhdm1797", "bhdm5367", "bhdm5368", "bhdm1460", "bhdm1480", "bhdm1415", "bhdm1420", "bhdm1410", "bhdm1766", "bhdm1975"]
EXTRA = ["bhck3283", "bhdmf158", "bhdmf159", "bhdmf160", "bhdmf161", "bhdmb538", "bhdmb539", "bhdmk137", "bhdmk207", "bhdm2011",
         "bhckf164", "bhckf165", "bhckb987", "bhckb989", "bhck2165", "bhck1590", "bhck2107", "bhck1288", "bhck2081"]

# (1) definitions
rv = con.execute(f"SELECT * FROM read_csv('{DUMP}bank_all.wrds_bank_reg_vars.csv.gz', header=true, all_varchar=true)").fetchdf()
print("reg_vars columns:", rv.columns.tolist(), "rows", len(rv))
rv["vn"] = rv.variable_name.str.lower()
sel = rv[rv.vn.isin(ITEMS + EXTRA)].sort_values(["vn", "start_date"])
keep = [c for c in ["vn", "item_name", "start_date", "end_date", "table"] if c in sel.columns]
print(sel[keep].to_string(index=False))

# (2) headers
files = {"bhck_1": "bank_all.wrds_holding_bhck_1.csv.gz", "bhck_2": "bank_all.wrds_holding_bhck_2.csv.gz",
         "other_1": "bank_all.wrds_holding_other_1.csv.gz"}
where = {}
for k, f in files.items():
    cols = con.execute(f"SELECT * FROM read_csv('{DUMP}{f}', header=true, all_varchar=true) LIMIT 1").fetchdf().columns
    cl = [c.lower() for c in cols]
    print(k, "ncols", len(cl), "first cols", cl[:6])
    for it in ITEMS + EXTRA:
        if it in cl:
            where.setdefault(it, []).append(k)
print("item -> file:", {it: where.get(it) for it in ITEMS + EXTRA})

# (3) link table
lk = con.execute(f"SELECT * FROM read_csv('{DUMP}bank_all.wrds_bank_crsp_link.csv.gz', header=true, all_varchar=true)").fetchdf()
print("link columns", lk.columns.tolist(), "rows", len(lk))
print(lk.inst_type.value_counts().to_string())
for c in ["dt_start", "dt_end"]:
    lk[c] = pd.to_datetime(lk[c])
print("dt_start range", lk.dt_start.min(), lk.dt_start.max(), "dt_end range", lk.dt_end.min(), lk.dt_end.max())
print("dt_start by year (count):", lk.dt_start.dt.year.value_counts().sort_index().to_dict())
print("rows with dt_end == max:", int((lk.dt_end == lk.dt_end.max()).sum()))
print("rssd with >1 rows:", int((lk.groupby("rssd9001").size() > 1).sum()), "permco with >1 rssd:", int((lk.groupby("permco").rssd9001.nunique() > 1).sum()))
print(lk.head(8).to_string())

# (4) Y-9C items -> cache, coverage
parts = []
for k, f in files.items():
    its = [it for it in ITEMS + EXTRA if k in where.get(it, [])]
    if not its:
        continue
    sql = ", ".join(f"TRY_CAST({it} AS DOUBLE) AS {it}" for it in its)
    d = con.execute(f"SELECT CAST(rssd9001 AS BIGINT) rssd9001, CAST(rssd9999 AS VARCHAR) rssd9999, {sql} "
                    f"FROM read_csv('{DUMP}{f}', header=true, all_varchar=true)").fetchdf()
    print(k, "rows", len(d), "distinct (rssd, date)", len(d[["rssd9001", "rssd9999"]].drop_duplicates()))
    parts.append(d.drop_duplicates(["rssd9001", "rssd9999"]).set_index(["rssd9001", "rssd9999"]))
Y = pd.concat(parts, axis=1).reset_index()
print("rssd9999 samples:", Y.rssd9999.head(3).tolist())
Y["date"] = pd.to_datetime(Y.rssd9999.str[:10].str.replace("-", ""), format="%Y%m%d", errors="coerce")
print("unparsed dates:", int(Y.date.isna().sum()), "range", Y.date.min(), Y.date.max(), "rows", len(Y), "filers", Y.rssd9001.nunique())
Y.to_parquet(P4 + "cache/y9c_items.parquet", index=False)
Y["year"] = Y.date.dt.year
linked = set(lk.rssd9001.astype("int64"))
for lab, Z in [("ALL FILERS", Y), ("LINKED FILERS", Y[Y.rssd9001.isin(linked)])]:
    cov = Z.groupby("year")[[c for c in ITEMS + EXTRA if c in Z.columns]].apply(lambda g: g.notna().mean()).round(2)
    cov.insert(0, "n", Z.groupby("year").size())
    print(f"\n== coverage (share non-null), {lab}")
    print(cov.T.to_string())
# per-quarter filer counts (linked) to see reporting-threshold changes
q = Y[Y.rssd9001.isin(linked)].groupby("date").size()
print("\nlinked filers per quarter (selected):", q[q.index.month == 12].to_dict())
qa = Y.groupby("date").size()
print("all filers per quarter (Dec):", qa[qa.index.month == 12].to_dict())
