---
title: "Loan-Officer Surveys and the Cross-Section of Bank Stock Returns: Evidence from Commercial Real Estate Lending Standards, 1991–2024"
author: "Ahn Hyun"
date: "November 2026 (draft v3 — replaces the May 2026 version)"
abstract: |
  The Federal Reserve's Senior Loan Officer Opinion Survey reports, loan category by loan category, the net share of banks tightening lending standards. I ask whether these public readings predict which bank stocks do worse. Weighting each category's reading by a bank holding company's loan mix (FR Y-9C) gives a bank-level exposure to tightening. In a test specified before returns were computed, banks in the lowest exposure quintile outperform banks in the highest by 1.19% per quarter between survey releases over 2000–2024 (t = 2.42; 95 releases, about 230 listed bank holding companies per release). The spread comes from commercial real estate (CRE): when the survey shows net CRE tightening 10 percentage points higher, banks with little CRE lending outperform CRE-heavy banks by 0.93 percentage points over the following quarter (t = 4.0; 1991–2024, 133 releases). That pattern was found after the first test, so I test it on a non-overlapping earlier sample, 1991–2000, with a specification fixed before those data were assembled; it is confirmed (t = 2.2). A static sort on CRE share is not significant (0.49% per quarter, t = 0.76) — the information is in the survey's variation over time. The effect is concentrated in the two CRE downturns, is absent in value-weighted portfolios, and is not statistically significant after trading costs.
jel: G12, G14, G21, E51
ssrn-classification: "Finance > Banking & Financial Institutions"
status: "Working paper, 2026"
geometry: margin=1in
fontsize: 11pt
linkcolor: blue
numbersections: true
bibliography: refs_v3.bib
---

# Introduction

Every quarter the Federal Reserve asks the senior loan officers of large banks whether they tightened or eased their lending standards, and publishes the answers by loan category: commercial and industrial (C&I) loans, commercial real estate (CRE), residential mortgages, credit cards and other consumer loans. The headline series — the net percentage of banks tightening standards — is a standard measure of credit supply in macroeconomics [@lown2006; @bassett2014], and it has been shown to forecast the return on the aggregate stock market [@chava2015; @wilson2023].

This paper asks a cross-sectional question that those studies do not: when the survey says that standards are tightening in one loan category, do the stocks of banks that hold a lot of that category subsequently do worse than the stocks of banks that hold little of it? The survey is public, the loan mix of every bank holding company is public (FR Y-9C), and the question can be asked at each release date using only information available on that date.

The answer is yes, and the result is specific.

1. **A pre-specified exposure sort earns a spread.** I weight each category's net tightening by the bank's loan share in that category, sort listed bank holding companies into quintiles at each survey release, and hold until the next release. Over 2000–2024 the lowest-exposure quintile outperforms the highest by 1.19% per holding period (about one quarter), with a Newey–West *t*-statistic of 2.42. The portfolio rule, the sample, the test statistic and the threshold were written down before any return was computed (Section 3.5 explains what that statement does and does not establish).
2. **The spread comes from commercial real estate, and from the survey's variation over time.** A static sort on CRE share alone earns 0.49% per period (*t* = 0.76). What predicts returns is the interaction: after a release with net CRE tightening 10 percentage points higher, low-CRE banks outperform high-CRE banks by 0.93 percentage points over the next holding period (*t* = 4.0 over 1991–2024).
3. **The CRE pattern is confirmed out of sample.** I found the CRE pattern by decomposing the first result, so the 2000–2024 sample cannot confirm it. The CRE survey series and the bank–CRSP link both start before 2000, while the bank financial data I had used start in 2000. I therefore wrote a second specification, then collected 1990–2000 FR Y-9C filings from the Federal Reserve Bank of Chicago, and ran the test on the 38 releases of 1991–2000. The slope is 0.85 percentage points per 10 points of tightening (*t* = 2.22), close to the 2000–2024 estimate of 0.95.

The limits are equally specific. Both samples owe much of their statistical strength to a CRE downturn (1991–92 and 2008–09); excluding both, the pooled slope is 0.51 (*t* = 2.4). The exposure spread is carried by smaller banks: it is 0.19% per period (*t* = 0.24) in value-weighted portfolios and 0.61% (*t* = 1.24) after quoted spreads and an assumed borrowing fee. I therefore present the result as evidence that bank stocks are slow to reflect a public, loan-category-specific credit signal, not as a profitable trading strategy.

**Contribution.** To my knowledge this is the first test of whether public lending-standards survey readings predict the *cross-section* of bank stock returns through banks' loan mix. Prior work relates the survey to aggregate returns [@chava2015; @wilson2023], relates confidential bank-level survey responses to banks' cost of capital with lending standards as the outcome [@kovner2022], or relates CRE exposure to bank stock returns year by year or in an event window without any survey variable [@faria2024; @pandolfo2024]. Section 2 gives the details.

**Relation to the earlier version.** This paper replaces the May 2026 version posted under the same SSRN identifier, which studied sector-level equity returns after survey shocks in the United States, the euro area and the United Kingdom. When event dates are set to the public release dates, universes are point-in-time, and each survey event is treated as one observation, those sector-level results are not distinguishable from zero in any of the three regions (Appendix C). The present paper keeps the survey data and the release-date tables of that project and asks a different question with a wider cross-section.

# Related Literature

**Lending-standards surveys.** @lown2006 show that shocks to the survey's standards series account for much of the variation in business loans and output. @bassett2014 purge bank-level responses of demand and macro factors to obtain a credit-supply indicator; recent Federal Reserve notes extend that approach [@baylor2024; @baylor2026]. These papers are about lending and real activity, not about stock returns.

**The survey and stock returns.** @chava2015 find that a tightening of standards predicts lower aggregate US stock returns at a business-cycle frequency. @wilson2023 reports that the standards question predicts quarterly S&P 500 returns after its release and that the relation is weaker in the last decade of his sample. Both are time-series results for the market as a whole. @hafemann2021 use the change in corporate bond spreads on the survey's release days as an instrument for lending-standards shocks in a macroeconomic model. Appendix B reports my own release-dated version for three regions: the aggregate relation is not significant in 1997–2024 and has the opposite sign in 2015–2024. The cross-sectional result of this paper is therefore not a restatement of the aggregate one.

**Bank-level survey responses.** @kovner2022 use the confidential bank-level responses and show that when a bank's CAPM cost of capital rises, the bank tightens its C&I standards. The survey response is their dependent variable; they do not predict stock returns and do not use loan mix.

**CRE exposure and bank stocks.** CRE concentration predicts bank failure [@cole2012]. @faria2024 regress annual bank holding company returns on lagged CRE exposure year by year over 2001–2023 and find a significantly negative coefficient in 2007–08 and in 2023 and little in between; @pandolfo2024 relate abnormal returns in a February 2024 window to CRE concentration. Neither uses a survey or any other measure of CRE credit conditions to say *when* CRE exposure should matter. @jiang2023 and @hinzen2025 study the solvency consequences of CRE distress, not returns.

**Predictability in the cross-section of bank stocks.** Bank stock returns are predictable from balance-sheet variables in ways that look like underreaction [@cooper2003], fast loan growth is followed by poor returns [@fahlenbrach2018], bank size carries a premium unrelated to standard factors [@gandhi2015], and aggregate credit expansions precede low bank equity returns [@baron2017]. The mechanism proposed here — a public signal about one line of business that reaches the prices of exposed firms with a delay — is of the kind documented for customer–supplier links by @cohen2008. Whether such a pattern survives its publication is an open question for any predictor [@mclean2016]; Section 6 returns to this.

# Data and Design

## Survey readings and release dates

The survey series are the Federal Reserve's "net percentage of domestic banks tightening standards" by loan category, taken from FRED. Net percentage is the share of banks that tightened minus the share that eased over the past three months. I group the series into five categories (Appendix A lists the series identifiers): C&I (large and middle-market firms, small firms), CRE (one series through 2013Q3; construction and land development, nonfarm nonresidential and multifamily afterwards), residential mortgages (from 2007Q2), credit cards (from 1996Q1) and other consumer loans (from 1996Q1). When a category has several series at a date, I average them. When a category has no series, it is dropped and the remaining loan shares are rescaled to sum to one.

The survey is released several weeks after it is taken. I use the Federal Reserve's release date for each survey from 1997 on. For 1990–1996 the exact release dates are not in the Federal Reserve's online archive; I use an approximate date built from the typical lag in 1997–2001 and enter positions ten trading days after it, so that no position is opened before the release (in 1997–2024 the same rule never precedes the true release).

## Bank loan mix

Loan shares come from the consolidated financial statements of bank holding companies (FR Y-9C): C&I loans; CRE loans (construction and land development, multifamily, nonfarm nonresidential); residential real-estate loans (closed-end 1–4 family and home-equity lines); credit cards; other consumer loans. Shares are taken over the sum of the five categories. For 2000–2024 the filings are from the WRDS Bank Regulatory database; for 1990–2000 they are the quarterly files published by the Federal Reserve Bank of Chicago. In the two quarters where the sources overlap (2000Q1, 2000Q2) every share is identical across the two. At a release date I use the filing for the most recent quarter that ended at least 75 days earlier.

## Stocks

Bank holding companies are matched to CRSP with the PERMCO–RSSD link distributed with the WRDS Bank Regulatory database. The universe at each release is every linked holding company with a Y-9C filing, common shares on NYSE, AMEX or NASDAQ, a closing price of at least \$5 and a market capitalisation of at least \$100 million on the release date. Returns include delisting returns.

**Table 1. Samples.**

| | 1991–2000 (pre-sample) | 2000–2024 (main) |
|---|---:|---:|
| Survey releases | 38 | 95 |
| First / last entry date | 1991-02-25 / 2000-05-22 | 2000-08-28 / 2024-08-06 |
| Banks per release, mean (min–max) | 221 (154–298) | 233 (157–329) |
| Distinct bank holding companies | 465 | 655 |
| Mean loan share: C&I / CRE / residential / consumer | 0.24 / 0.25 / 0.33 / 0.18 | 0.20 / 0.44 / 0.27 / 0.08 |
| CRE share, 10th–90th percentile | 0.12–0.40 | 0.19–0.68 |
| Median market capitalisation (\$ million) | 385 | 575 |
| Net CRE tightening across releases, mean (s.d.; min, max) | 6.1 (13.2; −11.3, 46.4) | 19.1 (27.6; −23.6, 87.0) |

## Exposure and portfolios

For bank $i$ at release $r$,

$$BT_{i,r} = \sum_k s_{i,k}\, N_{k,r},$$

where $s_{i,k}$ is the bank's loan share in category $k$ and $N_{k,r}$ is the net percentage of banks tightening standards in category $k$ reported at release $r$. Banks are sorted into quintiles on $BT$ at the close of the first trading day after the release, and equal-weighted quintile portfolios are held until the close of the first trading day after the next release (about one quarter). The test statistic is the time-series mean of the return of the lowest-exposure quintile minus the highest, with a Newey–West standard error with one lag [@newey1987].

## Order of the tests and what "pre-specified" means here {#sec:order}

The tests were run in this order.

1. **Exposure sort, 2000–2024.** The definition of $BT$, the universe filters, the quintile sort, the holding period, the statistic and the decision rule (|*t*| ≥ 2.24, a Bonferroni threshold for two tests, and the same sign in 2000–2011 and 2012–2024) were written down before any return was computed. The second test in that family, a release-day reaction of bank stocks, did not pass (Appendix B).
2. **Decomposition, 2000–2024 (after seeing the result of 1).** I asked which category and which source of variation produced the spread. This is where the CRE pattern was found. Nothing in this step is a confirmatory test.
3. **CRE test, 1991–2000.** Because step 2 is post hoc, I wrote a second specification — the slope of the low-CRE minus high-CRE return spread on the released net CRE tightening, expected sign positive, confirmed if |*t*| ≥ 1.96 — and only then collected the 1990–2000 bank filings and computed returns for that period.
4. **Record for 2025.** Four releases after the main sample are reported without a test.

The specification documents and the execution logs are in the replication package. They carry file timestamps, not a public registration, so "pre-specified" should be read as the author's statement about the order of work, supported by those files. The decision rules are stated in advance so that a reader can check each result against them.

# Results

## The exposure sort

**Table 2. Returns of exposure quintiles between survey releases (% per holding period).** Q1 = lowest exposure to tightening. Equal-weighted. *t*-statistics use Newey–West standard errors with one lag.

| Sample | Releases | Q1 | Q2 | Q3 | Q4 | Q5 | Q1 − Q5 | *t* | Share of periods > 0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **2000–2024 (pre-specified test)** | 95 | 3.64 | 2.81 | 3.16 | 2.74 | 2.44 | **1.19** | **2.42** | 0.61 |
| 2000–2011 | 45 | 2.78 | 1.56 | 1.82 | 1.47 | 1.16 | 1.62 | 1.98 | 0.64 |
| 2012–2024 | 50 | 4.41 | 3.93 | 4.38 | 3.88 | 3.60 | 0.81 | 1.44 | 0.58 |
| 1991–2000 (pre-sample) | 38 | 5.94 | 5.45 | 5.42 | 5.28 | 5.41 | 0.53 | 0.90 | 0.61 |
| 1991–2024 (pooled) | 133 | 4.30 | 3.56 | 3.81 | 3.47 | 3.29 | 1.00 | 2.56 | 0.61 |

Over 2000–2024 the spread is 1.19% per holding period with a *t*-statistic of 2.42, above the threshold of 2.24, and it is positive in both halves of the sample. The pre-specified test therefore passes. In monthly calendar time the same portfolio has a five-factor-plus-momentum alpha [@fama2015; @carhart1997] of 0.38% per month (*t* = 2.41).

The spread has the same sign in the pre-sample (0.53%, *t* = 0.90) and averages 1.37% over the four releases of 2025 (three of four positive; Section 5.3). Over the 133 releases of 1991–2024 it averages 1.00% (*t* = 2.56). The figure below shows the cumulative return.

The pass is not comfortable. The *t*-statistic is 2.32 with two lags and 2.15 with four. Dropping any one of 2004, 2008, 2009 or 2013 takes it below 2.24 (the range over all leave-one-year-out samples is 1.95 to 2.97), and without the releases of 2008–2009 the spread is 0.58% (*t* = 1.45). The next section shows where the spread comes from, which is also what makes those years matter.

![Cumulative return of the exposure long-short (lowest minus highest exposure quintile), equal-weighted, before costs. Values in `v3/tables/series_exposure_quintiles.csv`.](figures_v3/fig2_cumulative_long_short.png)

## Where the spread comes from: CRE tightening, not CRE share

Within one release, $BT$ is a linear combination of a bank's loan shares, with the survey readings as weights that are common to all banks. The exposure sort is therefore a sort on loan mix whose weights change from release to release. Two things could produce a spread: a fixed premium on some loan mix, or the changing weights.

A fixed premium does not. Sorting on CRE share alone at every release — always long low-CRE banks, short high-CRE banks — earns 0.49% per period over 2000–2024 (*t* = 0.76). Sorting on loan shares weighted by the *average* reading of each category earns the same.

The changing weights do. Table 3 regresses the return spread between the lowest and highest CRE-share quintiles on the net CRE tightening just released.

**Table 3. Low-CRE minus high-CRE return spread on released net CRE tightening.** Dependent variable: return of the lowest CRE-share quintile minus the highest, between releases (%). Regressor: net percentage of banks tightening CRE standards, divided by 10. Newey–West *t*-statistics (one lag) in parentheses.

| | Sample | Releases | Slope | Intercept | $R^2$ |
|---|---|---:|---:|---:|---:|
| (1) | 2000–2024 (where the pattern was found) | 95 | 0.95 (3.90) | −1.33 (−3.19) | 0.23 |
| **(2)** | **1991–2000 (specified before the data were collected)** | **38** | **0.85 (2.22)** | −0.85 (−1.61) | 0.11 |
| (3) | 1991–2024 pooled | 133 | 0.93 (4.02) | −1.17 (−3.58) | 0.22 |
| (4) | Pooled, excluding 1991–92 and 2008–09 | 117 | 0.51 (2.36) | −0.88 (−2.79) | 0.08 |
| (5) | Pooled, adding the previous period's spread (coefficient 0.10, *t* = 1.28) | 132 | 0.82 (3.63) | −1.08 (−3.44) | 0.22 |
| (6) | Pooled, using the previous survey's reading instead | 132 | 0.85 (3.66) | −1.12 (−3.29) | 0.19 |
| (7) | 2012–2024 | 50 | 0.66 (2.44) | −0.74 (−1.35) | 0.14 |

In the pooled sample, a reading 10 points higher is followed by a spread 0.93 percentage points larger. The negative intercept means that when CRE standards are not tightening, CRE-heavy banks outperform: after releases with net CRE tightening above its median (8.9), low-CRE banks beat high-CRE banks by 1.90% on average; after releases at or below the median, they trail by 1.37%. The static CRE sort earns little because it averages the two states.

Row (2) is the confirmatory test. In 1991–2000 the slope is 0.85 (*t* = 2.22), which meets the criterion set in advance. The bank-level companion statistic specified with it — returns on release fixed effects, the CRE and C&I shares, and CRE share interacted with the reading — is −2.22 (*t* = −2.12). Table 4 adds the C&I interaction and gives −2.14 (*t* = −2.09) in 1991–2000 against −2.06 (*t* = −4.71) in 2000–2024.

Two further points. The reading adds information beyond the past relative performance of CRE-heavy banks (row 5). And the previous survey's reading predicts almost as well as the current one (row 6): net CRE tightening is a slow-moving state variable, with a first-order autocorrelation of 0.89, so the effect is better described as continued underperformance of CRE-heavy banks while a tightening phase lasts than as a reaction to one release. A consequence is that the approximate release dates of 1990–1996 are not driving the pre-sample result.

![Left: net percentage of domestic banks tightening standards on CRE loans (average of the CRE series of the survey). Right: return of the lowest minus the highest CRE-share quintile until the next release, against the reading just released; squares are the 1991–2000 pre-sample. Values in `v3/tables/series_cre_spread.csv`.](figures_v3/fig1_cre_tightening_and_spread.png)

**Table 4. Bank-level panel.** Dependent variable: bank stock return between releases (%). All regressions include release fixed effects and the loan shares themselves. Interactions are loan share × (net tightening of that category minus its sample mean) / 10. Standard errors clustered by release.

| | Sample | Bank-releases | CRE interaction | C&I interaction | Other categories |
|---|---|---:|---:|---:|---|
| (1) | 2000–2024, five categories | 22,117 | −2.06 (−4.71) | −1.20 (−2.16) | residential 0.54 (0.73); cards −0.08 (−0.06); other consumer −0.43 (−0.40) |
| (2) | 2000–2024, with size, book-to-market, momentum | 21,575 | −2.31 (−5.51) | −1.41 (−2.97) | |
| (3) | 1991–2000 | 8,389 | −2.14 (−2.09) | 0.43 (0.49) | |
| (4) | 1991–2024 pooled | 30,506 | −2.11 (−5.07) | −1.13 (−2.49) | |
| (5) | Pooled, excluding 1991–92 and 2008–09 | 27,590 | −1.47 (−3.68) | −0.98 (−1.88) | |

The CRE interaction is stable across samples. To read its size: for a bank with a CRE share of 0.68 (the 90th percentile in 2000–2024) against one with 0.19 (the 10th), a reading 10 points above average lowers the next-period return by about 1.0 percentage point. The C&I interaction has the expected sign in 2000–2024 but not in 1991–2000; I do not interpret it. The residential and consumer categories show nothing.

## Do the losses follow?

If tightening signals deteriorating loans, the credit losses of exposed banks should rise afterwards. I specified one test before looking at loss data: net charge-offs over the four quarters after a release, scaled by loans, on release fixed effects, loan shares, and CRE share interacted with the CRE reading; standard errors clustered by release and by bank [@cameron2011]; expected sign positive; "consistent" if |*t*| ≥ 1.96.

**Table 5. Credit losses over the next four quarters, 2000–2024.** Coefficient on CRE share × (net CRE tightening minus its mean) / 10. 20,361 bank-releases, 580 banks, 93 releases.

| Outcome (% of loans) | Mean | Release FE + loan shares | Adding bank FE |
|---|---:|---:|---:|
| **Net charge-offs (pre-specified)** | 0.42 | **0.048 (1.49)** | 0.059 (2.00) |
| Loan-loss provisions | 0.54 | 0.070 (1.77) | 0.081 (2.16) |

The coefficient is positive in all four versions, but the pre-specified one does not reach 1.96, so by the rule set in advance the mechanism is not established. The magnitudes are also small: moving from the 10th to the 90th percentile of CRE share, a reading 10 points higher raises four-quarter net charge-offs by about 0.02% of loans. Losses on CRE loans typically arrive later than four quarters and are recognised slowly, so this horizon may be too short; I leave that to future work rather than search over horizons here.

# Implementation

## Weighting and costs

**Table 6. The exposure long-short under alternative implementations (% per holding period).**

| Sample | Version | Releases | Mean | *t* |
|---|---|---:|---:|---:|
| 2000–2024 | Equal-weighted (pre-specified) | 95 | 1.19 | 2.42 |
| 2000–2024 | Value-weighted | 95 | 0.19 | 0.24 |
| 2000–2024 | No price or size filter | 95 | 1.60 | 2.74 |
| 2000–2024 | Net of costs, turnover-based | 95 | 0.61 | 1.24 |
| 2000–2024 | Net of costs, full round trip every period | 95 | 0.11 | 0.23 |
| 2000–2024 | Excluding releases in 2008–2009 | 87 | 0.58 | 1.45 |
| 1991–2000 | Equal-weighted | 38 | 0.53 | 0.90 |
| 1991–2000 | Value-weighted | 38 | 1.47 | 1.72 |
| 1991–2024 | Equal-weighted, pooled | 133 | 1.00 | 2.56 |

Costs are half the quoted closing spread at entry and exit (median half-spread 0.08%) and a borrowing fee of 1% a year on the short leg, which is an assumption; one-way turnover is 0.60 to 0.67 per period. After costs the spread is 0.61% per period (*t* = 1.24). In value-weighted portfolios it is 0.19% in 2000–2024: the high-exposure quintile is CRE-heavy, CRE-heavy banks are smaller, and the largest banks hold little CRE. Over 1991–2024 the equal-weighted long-short compounds at 3.7% a year before costs, with an annualised Sharpe ratio of about 0.5.

## What the result is

The evidence supports a statement about prices: the relative returns of CRE-heavy and CRE-light bank stocks over the next quarter are predictable from a public survey reading. It does not support a statement about profits: the predictability sits in small banks and does not clear costs with statistical confidence.

## The 2025 releases

Four releases after the main sample have complete holding periods in the available return data. No test is possible with four observations; they are reported for the record.

| Release | Holding period | Banks | Exposure long-short (%) | Low-CRE minus high-CRE (%) | Net CRE tightening |
|---|---|---:|---:|---:|---:|
| 2024-11-12 | 2024-11-13 – 2025-02-04 | 193 | 2.89 | 5.31 | 17.0 |
| 2025-02-03 | 2025-02-04 – 2025-05-13 | 192 | 1.82 | 0.64 | 6.9 |
| 2025-05-12 | 2025-05-13 – 2025-08-05 | 190 | 1.03 | 5.73 | 7.9 |
| 2025-08-04 | 2025-08-05 – 2025-11-04 | 190 | −0.24 | 0.91 | 8.7 |

# Discussion

**Why would prices be slow?** The survey reading is a single number about the banking system. Turning it into a statement about one bank requires that bank's loan mix, which sits in a regulatory filing. The combination is cheap to compute but, as far as I can find, is not a standard input to bank-stock analysis, and the banks most exposed are small and thinly followed. This is the setting in which information about one line of business has been found to reach related stocks with a delay [@cohen2008].

**Two episodes.** In both samples the largest spreads come from a CRE downturn: 1991–92 and 2008–09. Without them the pooled slope is 0.51 (*t* = 2.36; Table 3) and the bank-level interaction is −1.47 (*t* = −3.68; Table 4), so the pattern is present in ordinary times at about half the size. A reader who believes that only crises matter should take the smaller estimates.

**After publication.** Predictors tend to weaken once they are published [@mclean2016], and the aggregate survey–return relation shows that pattern in release-dated data (Appendix B). The cross-sectional relation here is still present in 2012–2024 (slope 0.66, *t* = 2.44) and in the four releases of 2025, but it has no track record after its own publication.

**Limits.** (i) The CRE pattern in 2000–2024 was found after the first test; its confirmation rests on the 38 releases of 1991–2000, of which 25 use approximate release dates. (ii) Pre-specification is documented by the author's files, not by a public registry. (iii) The FR Y-9C reporting threshold rose in 2006, 2015 and 2018, so the cross-section shrinks and tilts toward larger banks over time. (iv) Before 2007 there is no residential-mortgage series that meets the series definition, and before 1996 no consumer series, so in the early years exposure is computed over the available categories only. (v) The borrowing fee is assumed. (vi) The mechanism test on credit losses is not conclusive.

# Conclusion

Public lending-standards survey readings, combined with public loan-mix data, predict the relative returns of bank stocks over the following quarter. A sort on exposure to tightening that was specified in advance earns 1.19% per quarter in 2000–2024 before costs. The source is commercial real estate: the survey's CRE reading determines whether CRE-heavy banks will lag or lead, and this relation, found in 2000–2024, is confirmed in a separately specified test on 1991–2000. The effect is concentrated in smaller banks and in CRE downturns and does not survive trading costs with statistical confidence. The same approach — a category-level public signal crossed with firm-level exposure — could be applied to the euro-area and UK lending surveys where bank-level loan mix is available.

# References {.unnumbered}

::: {#refs}
:::

# Appendix A: Series and Variable Definitions {.unnumbered}

**Survey series (FRED identifiers).** C&I: `DRTSCILM`, `DRTSCIS`. CRE: `DRTSCREL` (1990Q3–2013Q3); `SUBLPDRCSC`, `SUBLPDRCSN`, `SUBLPDRCSM` (from 2013Q4). Residential: `DRTSPM`, `DRTSNT`, `DRTSSP` (2007Q2–2014Q4); `SUBLPDHMSENQ`, `SUBLPDHMSGNQ`, `SUBLPDHMSQNQ`, `SUBLPDHMSJNQ`, `SUBLPDHMSKNQ`, `SUBLPDHMSMNQ`, `DRTSSP` and the home-equity series `SUBLPDCLHSNQ` (from 2015Q1; home-equity from 2008Q1). Credit cards: `DRTSCLCC` (from 1996Q1). Other consumer: `DRTSCOCL` (1996Q1–2011Q1); `STDSAUTO`, `STDSOTHCONS` (from 2011Q2). Only series titled "Net Percentage of Domestic Banks Tightening Standards for …" are used; a pre-2007 mortgage series with a different title is excluded.

**FR Y-9C items.** C&I: BHCK1763 + BHCK1764 (BHCK1766 where only the total is reported). CRE: construction (BHCKF158 + BHCKF159; BHDM1415 before 2007) + multifamily (BHDM1460) + nonfarm nonresidential (BHCKF160 + BHCKF161; BHDM1480 before 2007). Residential: BHDM1797 + BHDM5367 + BHDM5368. Credit cards: BHCKB538 (BHCK2008 before 2001). Other consumer: BHCKB539 + BHCKK137 + BHCKK207 (BHCK2011 before 2011). Net charge-offs: BHCK4635 − BHCK4605; provisions: BHCK4230; total loans: BHCK2122. Income-statement items are year-to-date and are differenced to quarterly flows.

**Sources.** FRED (survey series); Federal Reserve Board, Senior Loan Officer Opinion Survey release pages (release dates); Federal Reserve Bank of Chicago, Holding Company Data (FR Y-9C, 1990–2000); WRDS Bank Regulatory (FR Y-9C from 2000; PERMCO–RSSD link); CRSP (returns); Kenneth French's data library (factors).

# Appendix B: Other Tests Specified in Advance {.unnumbered}

Two further tests were specified together with the exposure sort. Neither passes; they are reported so that the family of tests is complete.

**Release-day reaction (second test of the family, threshold |*t*| ≥ 2.24).** The two-day abnormal return of an equal-weighted portfolio of bank stocks around each release (bank portfolio minus the CRSP value-weighted market) is regressed on the change in the C&I reading from the previous survey. Over 109 releases in 1997–2024 the slope is −0.31% per 10 points (*t* = −1.06), positive in 1997–2010 and negative in 2011–2024.

**Aggregate market timing (reference; already studied by @chava2015 and @wilson2023).** The excess return of the value-weighted market between releases is regressed on the C&I reading. United States, 1997–2024: slope −0.054 (*t* = −1.24), out-of-sample $R^2$ −5.0%; 2015–2024: +0.087 (*t* = +1.88). Euro area, 2003–2024: −0.060 (*t* = −0.80). United Kingdom, 2007–2024: −0.135 (*t* = −1.84).

# Appendix C: The Sector-Level Results of the Earlier Version {.unnumbered}

The May 2026 version reported that sector-level cumulative abnormal returns after large survey shocks were significant in several sector-horizon cells in the United States and the euro area. Three corrections change that result: (i) event dates are moved to the public release dates of each survey (the earlier dates were the first day of the survey quarter in the United States and the last day in the euro area); (ii) the stock universes are point-in-time rather than current index constituents; (iii) all firms that share an event are treated as one observation. With these corrections and a signed shock, no sector-horizon cell passes a Bonferroni threshold in the United States, the euro area or the United Kingdom (0 of 33 in each), and a real-time strategy that selects sectors from past events earns a Sharpe ratio of −0.12 in the euro area and 0.07 in the United States. The cross-regional rank correlation of sector responses, reported as 0.63 to 0.85, is 0.54 with a bootstrap interval that includes zero.

# Appendix D: Replication {.unnumbered}

The replication package contains the specification documents (`PHASE4_SPEC.md`, `PHASE4B_SPEC.md`, `PHASE4C_SPEC.md`), the scripts and logs of each step, the bank-release tables for both samples, and the scripts that produce every table and figure of this paper (`make_tables.py`, `make_figures.py`). Independent recomputations of the main statistics from the raw filings and from a second CRSP file are included: loan shares for 400 (2000–2024) and 300 (1991–2000) randomly drawn bank-quarters and holding-period returns for 300 and 200 randomly drawn positions match exactly.
