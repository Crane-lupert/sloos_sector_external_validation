"""Paths for the v3 scripts. Set the environment variables to point at your own copies.

SLOOS_V3_WORK   working directory that holds phase4/, phase4b/, out/ (intermediate tables; not in the repo)
WRDS_DUMP_DIR   directory with the WRDS extracts as <schema>.<table>.csv.gz (licensed data; not in the repo)
"""
import os
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
V3WORK = os.environ.get("SLOOS_V3_WORK", str(_REPO / "data" / "v3_work")).replace("\\", "/").rstrip("/") + "/"
WRDS_DUMP = os.environ.get("WRDS_DUMP_DIR", str(_REPO / "data" / "wrds_dump")).replace("\\", "/").rstrip("/") + "/"
REPO_CACHE = str(_REPO / "data" / "cache").replace("\\", "/") + "/"
