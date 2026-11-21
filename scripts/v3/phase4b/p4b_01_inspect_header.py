# v3 reference implementation - as run on 2026-11-21; absolute paths replaced by v3paths (see scripts/v3/README.md)
"""Phase 4B / Step 0 - inspect one Chicago Fed BHCF quarterly CSV (header + coverage of candidate loan items). No returns.
Usage: python -E -P p4b_01_inspect_header.py <path-to-bhcfYYMM.csv> [<more files> ...]
The downloaded file is treated as untrusted data: it is only parsed as CSV text."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from v3paths import V3WORK, WRDS_DUMP, REPO_CACHE
import re
import sys
import pandas as pd

CAND = ["RSSD9001", "RSSD9999", "RSSD9017", "RSSD9048", "RSSD9101", "RSSD9200", "RSSD9130", "RSSD9210",
        "BHCK2170", "BHCK2122", "BHCK2123", "BHCK2125", "BHCK3210", "BHCK3283",
        "BHCK1763", "BHCK1764", "BHCK1766", "BHCK1755", "BHCK1756",
        "BHCK1415", "BHDM1415", "BHCK1420", "BHDM1420", "BHCK1460", "BHDM1460", "BHCK1480", "BHDM1480",
        "BHCK1797", "BHDM1797", "BHCK5367", "BHDM5367", "BHCK5368", "BHDM5368", "BHCK1430", "BHDM1430",
        "BHCK1410", "BHDM1410", "BHCK1288", "BHCK1590", "BHDM1590",
        "BHCK1975", "BHCK2008", "BHCK2011", "BHCKB538", "BHCKB539", "BHCK2010", "BHCK1976", "BHCK1977", "BHCK2009",
        "BHDM1975", "BHDM2008", "BHDM2011", "BHFN1975", "BHCK1400", "BHDM1400", "BHFN1400"]

for path in sys.argv[1:]:
    with open(path, "r", encoding="latin-1") as f:
        header = f.readline().strip().split(",")
    hdr_u = [h.strip().upper() for h in header]
    print(f"== {path}")
    print(f"columns {len(hdr_u)}; duplicate names {len(hdr_u) - len(set(hdr_u))}; first 5 {hdr_u[:5]}")
    d = pd.read_csv(path, dtype=str, encoding="latin-1", low_memory=False)
    d.columns = [c.strip().upper() for c in d.columns]
    print("rows", len(d), "| rssd9999 values", d.RSSD9999.value_counts().to_dict())
    y9c = d["BHCK2170"].notna() if "BHCK2170" in d.columns else pd.Series(False, index=d.index)
    print("rows with BHCK2170 non-null (Y-9C filers):", int(y9c.sum()))
    for c in CAND:
        if c in d.columns:
            v = pd.to_numeric(d.loc[y9c, c], errors="coerce")
            print(f"  {c:9s} present | non-null among Y-9C {int(v.notna().sum()):5d} | >0 {int((v > 0).sum()):5d} | sum {v.sum():.3e}")
        else:
            print(f"  {c:9s} ABSENT")
    pref = {}
    for h in hdr_u:
        m = re.match(r"([A-Z]{4})", h)
        pref[m.group(1) if m else h] = pref.get(m.group(1) if m else h, 0) + 1
    print("column prefixes:", dict(sorted(pref.items(), key=lambda kv: -kv[1])))
    loan_like = [h for h in hdr_u if re.match(r"BH(CK|DM|FN)(1[3-9]\d\d|20\d\d|21\d\d|5367|5368|B53\d|F1\d\d|K1\d\d|K2\d\d)$", h)]
    print("loan-range items present:", loan_like)
