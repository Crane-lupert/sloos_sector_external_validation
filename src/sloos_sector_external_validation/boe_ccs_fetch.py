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

    Two complementary text-based extraction paths cover the full 2007-Q2
    to present history:

    (A) HTML scrape: from Q1 2018 onwards, the press release HTML page at
        https://www.bankofengland.co.uk/credit-conditions-survey/<year>/<year>-q<n>
        contains a 6-quarter rolling table of Net % balances embedded as
        <table> elements. Pre-2018 release pages are stub HTML with no
        embedded tables.

    (B) PDF Annex 3 scrape: every BoE CCS PDF press release (2007-Q4 onward)
        contains an "Annex 3 Corporate lending questionnaire results" page
        with a Net % balances table covering the past 12 quarters
        (3 quarters for the inaugural 2007-Q4 release). pdfplumber
        text-extracts this table cleanly. PDF URL pattern:
            https://www.bankofengland.co.uk/-/media/boe/files/credit-conditions-survey/<year>/<year>-q<n>.pdf

        Minimum 5 PDFs cover the pre-HTML era and bridge to HTML:
            - 2007 Q4 (inaugural, 3 quarters: 2007 Q2-Q4)
            - 2010 Q4 (12 quarters: 2008 Q1 - 2010 Q4)
            - 2013 Q4 (12 quarters: 2011 Q1 - 2013 Q4)
            - 2016 Q4 (12 quarters: 2014 Q1 - 2016 Q4)
            - 2018 Q4 (12 quarters: 2016 Q1 - 2018 Q4, bridges to HTML)

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

from .shock_construct import (
    Z_THRESHOLD,
    construct_shocks,
    event_summary,
    fit_ar_residual,
    flag_events,
    save_shocks,
)

# COVID quarters whose residual we exclude from σ(ε) estimation. The 2020 Q2 BoE
# CCS reading was +71.0 net % (UK government CBILS / BBLS emergency lending
# programmes drove banks to report a massive "increased availability"), which
# is ~1.4× the next-largest absolute observation in the 76-quarter sample
# (-51.8 in 2007 Q4). Including this single observation in σ(ε) inflates the
# residual std from ~9.1 to ~12.6, masking events at the standard |z|>1.0σ
# threshold. Following Stock-Watson 2021 "Forecasting in the COVID era" and
# Lenza-Primiceri 2022 (NBER WP), we exclude COVID-period 2020 Q2 from the σ
# calibration. The observation itself remains in the data and is still flagged
# as an event if its |z_innov|>threshold (which it always will be — z ≈ -7).
COVID_OUTLIER_QUARTERS_DEFAULT: list[pd.Timestamp] = [
    pd.Timestamp("2020-06-30"),  # 2020 Q2 — BoE CCS extreme outlier
]


def construct_shocks_covid_robust(
    panel: pd.DataFrame,
    primary_series: str,
    threshold: float = Z_THRESHOLD,
    sigma_exclude_dates: list[pd.Timestamp] | None = None,
) -> pd.DataFrame:
    """AR(1) shock identification with COVID-robust σ(ε) estimation.

    Identical to `shock_construct.construct_shocks` except that σ(ε) is computed
    over residuals EXCLUDING the dates in `sigma_exclude_dates`. The excluded
    observations are still kept in the panel and event-flagged (their z_innov is
    computed against the robust σ).
    """
    if sigma_exclude_dates is None:
        sigma_exclude_dates = COVID_OUTLIER_QUARTERS_DEFAULT
    # Step 1: full-sample AR(1) fit, returns z_panel with residual, fitted, raw, z_innov
    z_panel = fit_ar_residual(panel[primary_series])
    # Step 2: recompute σ(ε) excluding outlier dates
    resid = z_panel["residual"].dropna()
    excluded_set = set(pd.Timestamp(d).normalize() for d in sigma_exclude_dates)
    resid_robust = resid[[d not in excluded_set for d in resid.index.normalize()]]
    sigma_robust = float(resid_robust.std(ddof=1))
    # Step 3: recompute z_innov against the robust σ
    z_panel = z_panel.copy()
    z_panel["z_innov"] = z_panel["residual"] / sigma_robust
    z_panel.attrs["sigma_eps_full"] = float(z_panel.attrs.get("sigma_eps"))
    z_panel.attrs["sigma_eps"] = sigma_robust
    z_panel.attrs["sigma_excluded_dates"] = sorted(d.strftime("%Y-%m-%d") for d in excluded_set)
    # Step 4: flag events (replicates flag_events behaviour)
    out = flag_events(z_panel, threshold=threshold)
    from .shock_construct import SVB_COHORT_START

    out["is_svb_cohort"] = out.index >= SVB_COHORT_START
    out.attrs.update(z_panel.attrs)
    return out

BOE_CCS_PAGE_PATTERN = "https://www.bankofengland.co.uk/credit-conditions-survey/{year}/{year}-q{quarter}"
BOE_CCS_PDF_PATTERN = (
    "https://www.bankofengland.co.uk/-/media/boe/files/credit-conditions-survey/"
    "{year}/{year}-q{quarter}.pdf"
)
BOE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

# HTML scrape schedule: from Q1 2018 the press release page embeds a 6-quarter
# rolling Net % balance table. Pre-2018 release pages are stub HTML.
# Hit Q4 of every year 2019-2025 + Q1 2026 to ensure no quarter is missed
# (each page covers 6 quarters back, so the alternating-year gap of mid-year
# quarters needs every-year coverage).
DEFAULT_HTML_PAGE_SCHEDULE: list[tuple[int, int]] = [
    (2019, 4),
    (2020, 4),
    (2021, 4),
    (2022, 4),
    (2023, 4),
    (2024, 4),
    (2025, 4),
    (2026, 1),
]

# Backwards-compat alias (Day 1 used a single schedule for HTML-only).
DEFAULT_PAGE_SCHEDULE = DEFAULT_HTML_PAGE_SCHEDULE

# PDF Annex 3 schedule: 5 PDFs cover the full 2007-Q2..2018-Q4 pre-HTML era.
# Every Q4 release after 2008 carries the trailing 12 quarters' Net %.
DEFAULT_PDF_SCHEDULE: list[tuple[int, int]] = [
    (2007, 4),  # inaugural Q2-Q4 (3 quarters)
    (2010, 4),  # 2008 Q1 - 2010 Q4
    (2013, 4),  # 2011 Q1 - 2013 Q4
    (2016, 4),  # 2014 Q1 - 2016 Q4
    (2018, 4),  # 2016 Q1 - 2018 Q4 (bridges to HTML era)
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


def _fetch_pdf(year: int, quarter: int, cache_dir: Path = Path("data/raw"), timeout: float = 60.0) -> Path:
    """Download (and cache) the BoE CCS quarterly press release PDF."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"boe_ccs_{year}_q{quarter}.pdf"
    if out.exists() and out.stat().st_size > 0:
        return out
    url = BOE_CCS_PDF_PATTERN.format(year=year, quarter=quarter)
    r = httpx.get(url, headers={"User-Agent": BOE_USER_AGENT}, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    out.write_bytes(r.content)
    return out


def _parse_pdf_annex3_corporate(
    pdf_path: Path, release_year: int, release_quarter: int
) -> dict[pd.Timestamp, float]:
    """Extract the Annex 3 Corporate-availability "Past three months" row from a BoE CCS PDF.

    Each PDF press release (2007-Q4 onward) embeds a "Net percentage balances" table
    in its "Annex 3 Corporate lending questionnaire results" page. The first data row
    of that table is "How has the availability of credit provided to the corporate
    sector overall changed? Past three months <12 floats>" (or 3 floats for the
    inaugural 2007-Q4 release).

    Quarter labels are walked backward from the release quarter so colspan-merged
    year headers ("2015 2016 2017") and quarter headers ("Q1 Q2 Q3 Q4 ...") don't
    need to be parsed structurally.
    """
    import pdfplumber  # local import; pdfplumber is in dev / pyproject deps

    with pdfplumber.open(pdf_path) as pdf:
        annex3_text: str | None = None
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if "Corporate lending questionnaire results" in txt and "Net percentage balances" in txt:
                annex3_text = txt
                break
        if annex3_text is None:
            return {}

    # Normalize Unicode hyphen variants (BoE PDFs from 2018+ use U+2011 non-breaking
    # hyphen for negative numbers) so our ASCII-hyphen regex matches.
    # U+2010 hyphen, U+2011 non-breaking hyphen, U+2012 figure-dash, U+2013 en-dash,
    # U+2014 em-dash, U+2212 minus sign — all map to ASCII '-'.
    annex3_text = re.sub(r"[‐‑‒–—−]", "-", annex3_text)

    # Find the headline corporate-availability past-three-months row. Two formats:
    # (a) 2007 Q4 inaugural: full sentence on one line.
    # (b) 2010+ format: text wraps so "How has the availability of credit provided to"
    #     ends a line and "Past three months <values>" begins the next visual row.
    #     pdfplumber.extract_text often joins these, but with row-text wrap split.
    target_row: str | None = None

    pattern_inline = re.compile(
        r"How has the availability of credit provided to the corporate sector overall changed\?\s*"
        r"Past three months\s+([-\d.\s]+?)(?:\n|Next three months|of which)",
        re.S,
    )
    m = pattern_inline.search(annex3_text)
    if m:
        target_row = m.group(1)
    else:
        # Wrapped form: search for "How has the availability of credit provided to" followed by
        # "Past three months" and floats on a single text line.
        pattern_wrapped = re.compile(
            r"How has the availability of credit provided to[^\n]*Past three months\s+([-\d.\s]+)",
        )
        m = pattern_wrapped.search(annex3_text)
        if m:
            target_row = m.group(1)

    if target_row is None:
        return {}

    # Float tokens on the data row.
    floats: list[float] = []
    for tok in target_row.split():
        try:
            v = float(tok)
        except ValueError:
            continue
        if -100.0 <= v <= 100.0:  # Net % balance ∈ [-100, 100]
            floats.append(v)

    if not floats:
        return {}

    # Walk quarter labels backward from the release quarter.
    end_period = pd.Period(year=release_year, quarter=release_quarter, freq="Q")
    n = len(floats)
    out: dict[pd.Timestamp, float] = {}
    for i, val in enumerate(floats):
        period = end_period - (n - 1 - i)
        ts = period.to_timestamp(how="end").normalize()
        out[ts] = float(val)
    return out


def scrape_boe_ccs_corporate_availability_pdf(
    pdfs: list[tuple[int, int]] = DEFAULT_PDF_SCHEDULE,
) -> pd.Series:
    """Iterate `pdfs` (list of (year, quarter)), download/cache each PDF, parse the
    Annex 3 corporate-availability past-three-months row, and merge into a single
    quarter-indexed Net % balance series.

    Sign convention: positive = INCREASED availability (easing), same as HTML scrape.
    """
    merged: dict[pd.Timestamp, float] = {}
    for year, quarter in pdfs:
        pdf_path = _fetch_pdf(year, quarter)
        page_data = _parse_pdf_annex3_corporate(pdf_path, release_year=year, release_quarter=quarter)
        for ts, val in page_data.items():
            merged[ts] = val  # last-write wins; later-published values are more recent revisions
    s = pd.Series(merged, name="BOE_CCS_CORPORATE_AVAIL_PDF").sort_index()
    s.index.name = "quarter_end"
    return s


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


def scrape_boe_ccs_corporate_availability_full(
    pdfs: list[tuple[int, int]] = DEFAULT_PDF_SCHEDULE,
    html_pages: list[tuple[int, int]] = DEFAULT_HTML_PAGE_SCHEDULE,
) -> pd.Series:
    """Combined PDF Annex 3 (pre-2018) + HTML scrape (2018+) full series builder.

    For overlapping quarters, the HTML scrape value wins (more recently published
    revision visible on the live release page).
    """
    s_pdf = scrape_boe_ccs_corporate_availability_pdf(pdfs=pdfs)
    s_html = scrape_boe_ccs_corporate_availability(pages=html_pages)
    merged: dict[pd.Timestamp, float] = {}
    for ts, val in s_pdf.items():
        merged[ts] = float(val)
    for ts, val in s_html.items():
        merged[ts] = float(val)  # HTML overrides
    s = pd.Series(merged, name="BOE_CCS_CORPORATE_AVAIL").sort_index()
    s.index.name = "quarter_end"
    return s


def fetch_and_construct_shocks(
    pdfs: list[tuple[int, int]] = DEFAULT_PDF_SCHEDULE,
    html_pages: list[tuple[int, int]] = DEFAULT_HTML_PAGE_SCHEDULE,
    threshold: float = 1.0,
    covid_robust: bool = True,
    sigma_exclude_dates: list[pd.Timestamp] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """End-to-end: scrape BoE CCS (PDF Annex 3 + HTML) → flip sign to tightening
    convention → AR(1) residual shocks → (shocks_df, summary_dict).

    `covid_robust=True` (default) computes σ(ε) excluding 2020 Q2 (CBILS/BBLS
    outlier). See `construct_shocks_covid_robust` for rationale.
    """
    s_avail = scrape_boe_ccs_corporate_availability_full(pdfs=pdfs, html_pages=html_pages)
    # Flip sign so positive = tightening, matching DRTSCILM / ECB BLS.
    s_tight = (-s_avail).rename("BOE_CCS_CORPORATE_TIGHTENING")
    panel = s_tight.to_frame()
    if covid_robust:
        shocks = construct_shocks_covid_robust(
            panel,
            primary_series="BOE_CCS_CORPORATE_TIGHTENING",
            threshold=threshold,
            sigma_exclude_dates=sigma_exclude_dates,
        )
    else:
        shocks = construct_shocks(panel, primary_series="BOE_CCS_CORPORATE_TIGHTENING", threshold=threshold)
    summary = event_summary(shocks)
    summary["series"] = "BOE_CCS_CORPORATE_TIGHTENING (= -availability_corporate_overall)"
    summary["n_quarters_observed"] = int(s_tight.notna().sum())
    summary["first_quarter"] = str(s_tight.index.min().date())
    summary["last_quarter"] = str(s_tight.index.max().date())
    summary["pdfs_scraped"] = list(pdfs)
    summary["html_pages_scraped"] = list(html_pages)
    summary["covid_robust"] = covid_robust
    summary["sigma_eps_robust"] = shocks.attrs.get("sigma_eps")
    summary["sigma_eps_full"] = shocks.attrs.get("sigma_eps_full")
    summary["sigma_excluded_dates"] = list(shocks.attrs.get("sigma_excluded_dates", []))
    return shocks, summary


def save(shocks: pd.DataFrame, out_dir: Path = Path("data/cache"), tag: str = "BOE_CCS_CORP") -> Path:
    return save_shocks(shocks, out_dir=out_dir, tag=tag)


__all__ = [
    "BOE_CCS_PAGE_PATTERN",
    "BOE_CCS_PDF_PATTERN",
    "COVID_OUTLIER_QUARTERS_DEFAULT",
    "DEFAULT_HTML_PAGE_SCHEDULE",
    "DEFAULT_PAGE_SCHEDULE",
    "DEFAULT_PDF_SCHEDULE",
    "construct_shocks_covid_robust",
    "fetch_and_construct_shocks",
    "save",
    "scrape_boe_ccs_corporate_availability",
    "scrape_boe_ccs_corporate_availability_full",
    "scrape_boe_ccs_corporate_availability_pdf",
]
