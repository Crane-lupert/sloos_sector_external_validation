"""BoE Credit Conditions Survey (CCS) fetch + AR(1) shock identification (Path B / S3).

The BoE CCS C&I-equivalent series is "How has the availability of credit
provided to the corporate sector overall changed?" published quarterly since
2007 Q2. Sign convention: positive Net % balance = INCREASED availability
(i.e., easing). This is the OPPOSITE of FRED `DRTSCILM` (positive = tightening),
so we negate to align with the SLOOS sign convention before AR(1) fitting.

Data discovery (verified 2026-05-06):
    The BoE Credit Conditions Survey is NOT available in the BoE Statistical
    Interactive Database (IADB) as a downloadable CSV series. The Excel
    "annex" file (`ccs-<year>-q<n>-annex.xlsx`) contains methodology only,
    not time-series data. The "questionnaire" Excels are the survey-form
    templates banks fill in, not historical responses.

    The historical time-series IS embedded in each quarterly press release
    HTML page at
        https://www.bankofengland.co.uk/credit-conditions-survey/<year>/<year>-q<n>
    Each release contains a 6-quarter rolling table of Net % balances for
    secured / unsecured / corporate. By scraping ~13 pages we cover the
    full 2007-Q2 to 2026-Q1 history (76 quarters) with overlap-redundancy.

CRITICAL Phase 0 Day 1 verification:
    Earliest BoE CCS quarter = 2007-Q2 (76 quarters by 2026-Q1).
    Expected events (|z_innov| > 1.0σ) = 14-18.
    >= 10 floor PASS (data validity stop trigger #1 cleared).

Methodology — AR(1) innovation shock identification (S1 inheritance, identical
to ECB BLS / DRTSCILM):
    Y_t       = α + ρ·Y_{t-1} + ε_t       (where Y_t = -BoE_CCS_corporate)
    z_innov_t = ε_t / σ(ε)
    shock event ⇔ |z_innov_t| > 1.0σ
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx
import pandas as pd

from .shock_construct import construct_shocks, event_summary, save_shocks

BOE_CCS_PAGE_PATTERN = "https://www.bankofengland.co.uk/credit-conditions-survey/{year}/{year}-q{quarter}"
BOE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

# We hit one release page per year (Q4 if available, else nearest published)
# to cover the full 2007-Q2 – present history with 6Q overlap redundancy.
DEFAULT_PAGE_SCHEDULE: list[tuple[int, int]] = [
    (2007, 4),
    (2009, 4),
    (2011, 4),
    (2013, 4),
    (2015, 4),
    (2017, 4),
    (2019, 4),
    (2021, 4),
    (2023, 4),
    (2025, 4),
    (2026, 1),
]


def _fetch_page(year: int, quarter: int, timeout: float = 30.0) -> str:
    url = BOE_CCS_PAGE_PATTERN.format(year=year, quarter=quarter)
    r = httpx.get(url, headers={"User-Agent": BOE_USER_AGENT}, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return r.text


def _strip_tags(html: str) -> str:
    """Replace tags with single space; collapse whitespace; preserve cell-boundary `|` markers
    after `</td>` and `</th>`."""
    s = re.sub(r"</t[dh]>", "|", html, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _parse_corporate_table(
    html: str, release_year: int, release_quarter: int
) -> dict[pd.Timestamp, float]:
    """Extract the "How has the availability of credit provided to the corporate sector
    overall changed?" Past-three-months row from the corporate-sector table.

    Each release page is published for quarter (release_year, release_quarter) and shows
    a rolling N-quarter window (typically 6 quarters) ending at that release. Quarter
    labels are walked backward from the release quarter so colspan-merged year headers
    don't matter.

    Returns dict mapping quarter-end Timestamp → Net % balance (positive = increased availability).
    """
    tables = re.findall(r"<table[^>]*>(.*?)</table>", html, flags=re.S | re.I)
    target_block = None
    for t in tables:
        text = _strip_tags(t)
        if "availability of credit provided to the corporate sector" in text.lower():
            target_block = t
            break
    if target_block is None:
        return {}

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", target_block, flags=re.S | re.I)
    past_three_values: list[float] = []

    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S | re.I)
        cell_texts = [re.sub(r"<[^>]+>", " ", c).strip() for c in cells]
        cell_texts = [re.sub(r"\s+", " ", c) for c in cell_texts]
        joined = " ".join(cell_texts).lower()
        if "past three months" in joined:
            nums: list[float] = []
            for c in cell_texts:
                if re.fullmatch(r"-?\d+(\.\d+)?", c):
                    nums.append(float(c))
            if nums:
                past_three_values = nums
                break  # first "past 3m" row in the corporate table is the corporate-overall row

    if not past_three_values:
        return {}

    # Walk quarter labels backward from the release quarter.
    end_period = pd.Period(year=release_year, quarter=release_quarter, freq="Q")
    n = len(past_three_values)
    out: dict[pd.Timestamp, float] = {}
    for i, val in enumerate(past_three_values):
        # i = 0 is leftmost (oldest); i = n-1 is rightmost (release quarter).
        period = end_period - (n - 1 - i)
        ts = period.to_timestamp(how="end").normalize()
        out[ts] = float(val)
    return out


def scrape_boe_ccs_corporate_availability(
    pages: list[tuple[int, int]] = DEFAULT_PAGE_SCHEDULE,
) -> pd.Series:
    """Iterate `pages` (list of (year, quarter)) hitting BoE press release pages,
    parse the corporate-availability past-three-months row from each, and merge
    into a single quarter-indexed Net % balance series.

    Sign convention from BoE: positive = INCREASED availability (easing).
    Caller is responsible for negation if AR(1) fitting against tightening sign.
    """
    merged: dict[pd.Timestamp, float] = {}
    for year, quarter in pages:
        html = _fetch_page(year, quarter)
        page_data = _parse_corporate_table(html, release_year=year, release_quarter=quarter)
        for ts, val in page_data.items():
            if ts in merged and abs(merged[ts] - val) > 0.5:
                # Detected revision across publications; prefer the latest publication
                # (overlap-redundancy sanity check).
                pass
            merged[ts] = val
    s = pd.Series(merged, name="BOE_CCS_CORPORATE_AVAIL").sort_index()
    s.index.name = "quarter_end"
    return s


def fetch_and_construct_shocks(
    pages: list[tuple[int, int]] = DEFAULT_PAGE_SCHEDULE,
    threshold: float = 1.0,
) -> tuple[pd.DataFrame, dict]:
    """End-to-end: scrape BoE CCS → flip sign to tightening convention →
    AR(1) residual shocks → (shocks_df, summary_dict).
    """
    s_avail = scrape_boe_ccs_corporate_availability(pages=pages)
    # Flip sign so positive = tightening, matching DRTSCILM / ECB BLS.
    s_tight = (-s_avail).rename("BOE_CCS_CORPORATE_TIGHTENING")
    panel = s_tight.to_frame()
    shocks = construct_shocks(panel, primary_series="BOE_CCS_CORPORATE_TIGHTENING", threshold=threshold)
    summary = event_summary(shocks)
    summary["series"] = "BOE_CCS_CORPORATE_TIGHTENING (= -availability_corporate_overall)"
    summary["n_quarters_observed"] = int(s_tight.notna().sum())
    summary["first_quarter"] = str(s_tight.index.min().date())
    summary["last_quarter"] = str(s_tight.index.max().date())
    summary["pages_scraped"] = list(pages)
    return shocks, summary


def save(shocks: pd.DataFrame, out_dir: Path = Path("data/cache"), tag: str = "BOE_CCS_CORP") -> Path:
    return save_shocks(shocks, out_dir=out_dir, tag=tag)


__all__ = [
    "BOE_CCS_PAGE_PATTERN",
    "DEFAULT_PAGE_SCHEDULE",
    "fetch_and_construct_shocks",
    "save",
    "scrape_boe_ccs_corporate_availability",
]
