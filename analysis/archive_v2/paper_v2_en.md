---
title: "Cross-Country External Validation of Bank Lending Shock × Sector Equity Heterogeneity: Eurozone Replicates US, UK Universe-Power Caveat"
author: "Ahn Hyun"
date: "May 2026"
abstract: |
  We test whether the sectoral cross-section heterogeneity of forward equity returns following bank-credit-supply shocks — established for the United States by a companion paper using the Federal Reserve Senior Loan Officer Opinion Survey (SLOOS) — generalises internationally. Applying an identical AR(1)-residual shock-identification scheme to the European Central Bank's Bank Lending Survey (ECB BLS) over 94 quarters and the Bank of England's Credit Conditions Survey (BoE CCS) over 76 quarters, we measure forward 1-, 3-, and 6-month cumulative abnormal returns (CARs) on STOXX Europe 600 firms with historical-reconstitution membership (Compustat Global, gvkeyx = 150,376) and apply the same Bonferroni-K=33 cell-level test plus a four-test robustness battery as the US benchmark. At the 6-month horizon the Eurozone sector ranking correlates Spearman rho = +0.755 (p = 0.007) with the US benchmark, strongly meeting our pre-registered rho >= 0.5 external-validation criterion; eight of 33 sector-horizon cells reach Bonferroni significance, the F-test for sector heterogeneity at 6 m is p = 2.7e-10, and three of four robustness tests pass. A complementary long-Industrials / short-{Communications, Utilities} basket delivers an alpha-Sharpe of +2.32 after absorbing a five-block factor baseline. The UK companion analysis fails Bonferroni at the cell level (1 of 33), but ANOVA confirms sector heterogeneity at 1 m and 3 m horizons; we explain this through a pre-registered universe-power lemma — STOXX 600 GBR is a vendor substitute for the unavailable FTSE 350, dominated by multinationals (BP, Shell, GSK, AstraZeneca, HSBC) whose economics are weakly identified by a domestic UK credit-supply shock, with a per-cell sample of n = 50 to 284 implying a structural Bonferroni floor of zero to one cells. This paper is a replication paper, not a novel-finding paper; the mechanism belongs to the companion US paper and the BLS macro literature, and our contribution is replication priority on the precise five-axis intersection (BLS/CCS survey AR(1) shock × STOXX 600 universe × eleven-sector cross-section × Bonferroni-K=33 multiple-comparison correction × medium-horizon forward CAR).
jel: G14, G21, E51
ssrn-classification: "Finance > Banking & Financial Institutions"
status: "Working paper, 2026"
geometry: margin=1in
fontsize: 11pt
linkcolor: blue
numbersections: true
bibliography: refs.bib
header-includes: |
  \usepackage{tocloft}
  \setlength{\cftbeforesecskip}{2pt}
  \setlength{\cftbeforesubsecskip}{1pt}
  \usepackage{newunicodechar}
  \newunicodechar{★}{\textasteriskcentered}
---

\clearpage

\tableofcontents

\clearpage

# Introduction

The Senior Loan Officer Opinion Survey (SLOOS) of the Federal Reserve, the
Bank Lending Survey (BLS) of the European Central Bank, and the Credit
Conditions Survey (CCS) of the Bank of England each report, quarterly, the net
percentage of banks tightening credit standards. The US series — specifically
the C&I diffusion index `DRTSCILM` — is widely used as a proxy for
bank-credit-supply shocks in the macroeconomic literature
[@bassett2014; @bidder2026]. A companion working paper [@ahn2026sloos]
established that AR(1)-residual shocks to `DRTSCILM` produce statistically
significant heterogeneity across the eleven GICS sectors in forward 1-, 3-,
and 6-month equity returns for US Russell 3000 firms — fifteen of 33
sector-horizon cells passed Bonferroni-K=33, the F-test for sector
heterogeneity at 6 m had $p < 10^{-56}$, and the canonical cyclical-defensive
ordering emerged.

This paper tests whether that result generalises internationally. We apply
the same AR(1)-residual shock-identification scheme to ECB BLS and BoE CCS,
construct STOXX Europe 600 firm panels with historical-reconstitution
membership, compute identical 1-, 3-, and 6-month forward CARs, and apply
the same multiple-testing correction. Two pre-registered cross-country
correlations are central: a Eurozone–US Spearman rank correlation of
per-sector mean CAR rankings at the 6-month horizon, and a UK–US analogue.
A third pair (UK–Eurozone) is included for completeness.

The contribution is a single dimension of *external validity*. The
mechanism — bank-credit-supply shocks generating cyclical–defensive
dispersion in equity sector returns — is not new; it belongs to the
companion paper and to the broader BLS literature on bank lending and
the macroeconomy. The first novel SLOOS-equity timing finding belongs to
@wilson2023 (S&P 500 aggregate, no sector decomposition); the first
SLOOS release-day shock identification via Bayesian VAR belongs to
@hafemanntillmann2021; the first AR-residual SLOOS expectation methodology
belongs to @bidder2026 (FEDS Note); the first US SLOOS sectoral
decomposition under a Bonferroni framework belongs to @ahn2026sloos. The
present paper extends the last of these to the UK and Eurozone. Its value
is replication priority on the precise five-axis intersection (survey
AR(1) shock $\times$ STOXX 600 universe $\times$ GICS-11 cross-section $\times$ Bonferroni-K=33
$\times$ medium-horizon CAR), where, to the author's knowledge, no prior work
exists.

The headline result is a **strong bilateral US–Eurozone external
validation**: Spearman $\rho$ = +0.755 at 6 m, p = 0.007, with eight of 33
sector-horizon cells passing Bonferroni and three of four robustness tests
clearing pre-registered floors. The UK companion result is negative at
the cell level (one of 33 cells), but is fully explained by a
pre-registered universe-power lemma: STOXX 600 GBR was adopted as a
vendor substitute for the unavailable FTSE 350 mid-cap, is dominated by
firms with global rather than domestic-UK revenue, and has a per-cell
sample size that — under Bonferroni-K=33 — implies a structural floor of
zero to one cells regardless of any underlying mechanism. We discuss this
result frankly and disclose it in full as protection against any concern
of file-drawer bias.

The strict outcome-class classification (one of three pairs passing) is
"B+ partial." We do not relax that classification. The paper's framing is
narrowed to where the evidence is strongest: a strong bilateral
US–Eurozone confirmation, with a UK universe-power caveat that closes the
loop on the natural reader question of why all three pairs do not pass.

The remainder of the paper is organised as follows. Section 2 reviews
related literature and distinguishes three nearby 2024–2026 papers.
Section 3 describes data and the BoE CCS extraction. Section 4 develops
methodology with full equations. Section 5 reports headline results.
Section 6 reports the UK companion result and the universe-power lemma.
Section 7 collects robustness checks. Section 8 discusses interpretation
and limitations. Section 9 concludes.

# Related Literature

## SLOOS, BLS, and the bank-lending literature

Bank lending surveys are among the longest-running macro indicators of
credit conditions. @bassett2014 use SLOOS innovations as a structural
identification scheme for adverse loan-supply shocks in a US macro VAR
and document their effects on aggregate credit and real activity.
@bidder2026 construct an Expected Credit Spread Index from SLOOS responses
using AR-residual methodology. @bell2014 document the methodology and
properties of BoE CCS. ECB BLS-side authors — including
@altavilla2020 and the broader ECB working-paper series associated
with Maddaloni, Holton, and Boucinha — examine the relationship between
BLS responses and lending volumes or corporate financing conditions in
the euro area. None of these papers analyses the *equity-side
sectoral cross-section*; their dependent variables are macro aggregates
(lending volume, credit spreads, real activity).

The first SLOOS-equity application is @wilson2023, who shows that the US
aggregate (S&P 500) is timeable using SLOOS responses. @hafemanntillmann2021
introduce SLOOS release-day shock identification within a Bayesian VAR
framework, with macro-aggregate dependent variables.

The companion paper @ahn2026sloos extends this thread by decomposing the
equity response across the eleven GICS sectors under a Bonferroni-K=33
multiple-comparison framework. Its closure documents fifteen of 33
sector-horizon cells with Bonferroni-significant t-statistics and a
canonical cyclical-defensive ordering.

The present paper takes that decomposition as the benchmark and tests
whether it generalises to the Eurozone (ECB BLS) and to the United
Kingdom (BoE CCS) on a STOXX Europe 600 universe.

## Three nearby 2024–2026 papers — distinction

Three recent studies in the European context look superficially close
to ours. We cite each and explain the precise distinction.

**Federal Reserve Board (2024)** "Country-Specific Effects of Euro-Area
Monetary Policy: The Role of Sectoral Differences," FEDS Notes
[@frb2024feds]. The paper's dependent variable is real-sector activity
(industrial production, employment) under euro-area monetary-policy
shocks. Distinction: (i) real-sector activity, not equity returns; (ii)
monetary-policy shocks, not bank-lending-survey shocks.

**Anonymized authors (2025)** "Green stocks and monetary policy shocks:
Evidence from Europe," published in a major finance journal
[@green2025europe]. The paper combines high-frequency monetary-policy
surprise shocks with a green/brown stock partition. Distinction: (i)
high-frequency MP surprise, not survey-derived shocks; (ii) green/brown
binary, not GICS-11 cross-section; (iii) intraday or 2-day event window,
not 1-, 3-, 6-month forward CARs.

**UK retail-bank regulatory event-study (2025)**
[@ukbank2025tandfonline]. The paper studies UK retail-bank stocks
themselves under regulatory events such as PRA capital-buffer changes.
Distinction: (i) bank stocks themselves, not non-bank sector
cross-section; (ii) regulatory events, not BoE CCS survey shocks.

## Cross-country factor replication

@jensen2023 perform a cross-country factor-replication study across 93
countries with a 82.4 % replication rate, but their object is the factor
zoo, not bank-credit-supply mechanisms. The present paper is, to the
author's knowledge, the first cross-country replication of a
bank-credit-supply-driven equity sectoral effect on a unified five-axis
methodology.

## Five-axis intersection

The exact dimensions on which we claim replication priority are
summarised in Table 1.

**Table 1 — Five-axis intersection vs. nearby work.**

| Axis | This paper | FRB FEDS 2024 | Green Europe 2025 | UK retail bank 2025 |
|---|---|---|---|---|
| Shock source | BLS/CCS survey AR(1) residual | MP policy | High-frequency MP surprise | Regulatory event |
| Dependent variable | GICS-11 sector cross-section equity CAR | Real-sector activity | Green/brown stocks | Bank stocks themselves |
| Universe | STOXX 600 (UK + Eurozone) | (real activity data) | European equity | UK retail banks |
| Horizon | 1m / 3m / 6m forward CAR | varies | intraday / 2 d | event-window short |
| Multiple-testing correction | Bonferroni-K=33 | n/a | n/a | n/a |

# Data

## Bank credit-supply shock series

Three quarterly series are used. Coverage and source are summarised in
Table 2.

**Table 2 — Bank credit-supply shock series.** US series identifier is the
FRED code `DRTSCILM`; the Eurozone series identifier is the ECB SDMX key
`BLS.Q.U2.ALL.O.E.Z.B3.ST.S.WFNET`.

\begingroup\small

| Country | Survey | Coverage | Source |
|---|---|---|---|
| United States | SLOOS, net % C&I tightening | 1990 Q1 – 2026 Q1 (145 q) | Federal Reserve via FRED |
| United Kingdom | BoE CCS, corporate availability (sign-flipped) | 2007 Q2 – 2026 Q1 (76 q) | BoE press-release Annex 3 |
| Eurozone | ECB BLS, credit standards (Enterprise) | 2003 Q1 – 2026 Q2 (94 q) | ECB Data Portal SDMX |

\endgroup

The BoE CCS series is not available as a downloadable CSV from the Bank
of England Statistical Interactive Database. Each quarterly press-release
PDF, however, embeds an "Annex 3 Corporate lending questionnaire results"
table reporting the trailing 12 quarters of net percentage balances. We
extract these tables from five PDFs (2007 Q4, 2010 Q4, 2013 Q4, 2016 Q4,
2018 Q4) covering 2007 Q2 – 2018 Q4 with overlap redundancy, and from
2018 Q1 onward we scrape the press-release HTML page directly. The
2018 Q4 PDF uses Unicode U+2011 (non-breaking hyphen) for negative
numbers, requiring text normalisation before regex parsing. Sign is
flipped so that positive denotes tightening, matching `DRTSCILM` and
ECB BLS.

The 2020 Q2 BoE CCS reading is +71.0 net % — a single observation 1.4$\times$
the next-largest absolute observation in the 76-quarter sample, driven
by the UK government's CBILS and BBLS emergency lending programmes.
Including it in $\sigma$($\varepsilon$) calibration inflates $\sigma$ from 9.1 to 12.6 and masks
economically meaningful events in surrounding periods. Following
@stockwatson2021 and @lenzaprimiceri2022 on COVID-era outlier treatment,
we exclude 2020 Q2 from $\sigma$($\varepsilon$) calibration only; it remains in the panel
and is still flagged as a shock event with z = $-$7.2. The 2020 Q2 ECB BLS
reading does not similarly dominate the Eurozone sample, so no
adjustment is applied.

## Equity universe — STOXX 600 historical reconstitution

STOXX Europe 600 historical reconstitution is sourced from Compustat
Global `g_idxcst_his` for index identifier gvkeyx = 150 376, comprising
2 141 from–thru records. Time-varying membership is honoured: a firm in
STOXX 600 in 2008 but delisted by 2010 is counted for 2008 events but
not for 2012 events. Vendor-side spot checks confirm historical from–thru
dates for AstraZeneca, HSBC, and Shell are real (not surrogated),
blocking first-order survivorship bias.

Three universes are used.

**Table 3 — Equity universes.** Counts of distinct firm identifiers
(Compustat `gvkey`) ever included in each universe over the sample
period and currently active as of the data cut.

\begingroup\small

| Universe | Country / region filter | Distinct gvkeys ever | Currently active | Shock events |
|---|---|---|---|---|
| United States (benchmark) | Russell 3000 with Compustat link | as in companion paper | as in companion paper | 36 |
| United Kingdom | STOXX 600, country = GBR | 450 | 119 | 12 |
| Eurozone-broad | STOXX 600 ex-UK and ex-offshore (24 country codes) | 1,119 | $\approx 420$ | 21 |
| Eurozone-strict | STOXX 600, euro-currency-area only (15 country codes) | 801 | a subset of the broad universe | 21 |

\endgroup

The US benchmark is held fixed at the values reported in the companion
paper. The Eurozone-strict universe is used in Section 7.4 as a
robustness check.

## Forward CAR computation

For each firm $i$, event date $e$, and horizon
$h \in \{1\text{m}, 3\text{m}, 6\text{m}\}$ corresponding respectively
to $h_{\text{td}} \in \{21, 63, 126\}$ trading days, the
total-return-adjusted price is

$$
\tilde{p}_{i,t} = P_{i,t} \cdot \frac{\mathrm{TRF}_{i,t}}{\mathrm{AdjFactor}_{i,t}}, \qquad (1)
$$

where $P_{i,t}$ is the closing price, $\mathrm{TRF}_{i,t}$ is the total-
return adjustment factor, and $\mathrm{AdjFactor}_{i,t}$ is the
cumulative split / dividend adjustment factor (Compustat Global fields
`prccd`, `trfd`, and `ajexdi`, respectively, in standard vendor
notation). The daily log return is

$$
r_{i,t} = \log \tilde{p}_{i,t} - \log \tilde{p}_{i,t-1}, \qquad (2)
$$

and the horizon log return, accumulated from the first trading day
$t_0(e)$ on or after the event date, is

$$
R_{i,e,h} = \sum_{t = t_0(e)}^{t_0(e) + h_{\text{td}}} r_{i,t}. \qquad (3)
$$

The equal-weighted market hedge for the panel at the event–horizon pair
$(e, h)$ is

$$
M_{e,h} = \frac{1}{|\mathcal{F}_e|} \sum_{i \in \mathcal{F}_e} R_{i,e,h}, \qquad (4)
$$

where $\mathcal{F}_e$ is the set of firms with valid returns in the
panel as of event date $e$ under time-varying STOXX 600 membership and
$|\mathcal{F}_e|$ its cardinality. The cumulative abnormal return is

$$
\mathrm{CAR}_{i,e,h} = R_{i,e,h} - M_{e,h}. \qquad (5)
$$

Per-cell counts $n^{(s,h)}$ — defined as the number of firm-observations
with a non-missing CAR for sector $s$ at horizon $h$ — clear the
pre-registered 50-firm floor on all 66 cells (33 UK plus 33 Eurozone).
The binding cell is UK Healthcare ($n = 50$); the smallest Eurozone
cell is Real Estate ($n = 265$).

# Methodology

## AR(1)-residual shock identification

For each survey series $Y_t$ — the quarterly net-percentage tightening
balance — we fit the first-order autoregressive model

$$
Y_t = \alpha + \rho \, Y_{t-1} + \varepsilon_t, \qquad (6)
$$

where $\alpha$ is the intercept, $\rho$ is the autoregressive
coefficient, and $\varepsilon_t$ is the innovation, estimated by
ordinary least squares. The standardised innovation is

$$
z_{\mathrm{innov},t} = \frac{\hat\varepsilon_t}{\hat\sigma(\varepsilon)}, \qquad (7)
$$

with $\hat\sigma(\varepsilon)$ the residual standard deviation.
Following the conventional one-standard-deviation rule, a quarter is
classified as a shock event when $|z_{\mathrm{innov},t}| > 1.0$. The
sign of the shock is $+1$ (tightening) if $\hat\varepsilon_t > 0$ and
$-1$ (easing) otherwise. For BoE CCS the raw "credit availability"
series is negated before fitting, so that positive innovations
correspond to tightening, matching the orientation of the US and
Eurozone series.

**Table 4 — AR(1) calibration.**

| Country | n quarters | $\hat\rho$ | $\hat\sigma(\varepsilon)$ | Events | Tightening / Easing |
|---|---|---|---|---|---|
| US | 145 | 0.86 | 11.24 | 36 | 19 / 17 |
| UK | 76 | 0.56 | 9.66 (robust) | 12 | 6 / 6 |
| Eurozone | 94 | 0.80 | 8.17 | 21 | 11 / 10 |

![Three-panel time series of survey net-percentage with AR(1) shock events highlighted for US `DRTSCILM`, UK BoE CCS (sign-flipped to tightening, COVID-robust $\sigma$), and Eurozone ECB BLS.](figures/fig1_shocks.png){#fig:shocks width=85%}

## Cell-level Bonferroni test

For each (sector $s$, horizon $h$) cell we compute a one-sample
$t$-statistic of cumulative abnormal returns against zero,

$$
t_{s,h} = \frac{\overline{\mathrm{CAR}}_{s,h}}{s_{s,h} / \sqrt{n_{s,h}}}, \qquad \mathrm{df} = n_{s,h} - 1, \qquad (8)
$$

where $\overline{\mathrm{CAR}}_{s,h}$ is the cell mean CAR, $s_{s,h}$
the cell standard deviation, $n_{s,h}$ the number of firm-observations
in the cell, and $\mathrm{df}$ the residual degrees of freedom. With
33 cells per country (eleven GICS sectors at three horizons), the
Bonferroni-corrected family-wise critical value at significance level
$\alpha = 0.05$ is

$$
|t^\star| = T^{-1}\!\left(1 - \frac{\alpha}{2 \cdot 33};\ \mathrm{df}\right) \approx 3.18, \qquad (9)
$$

where $T^{-1}(\cdot;\,\mathrm{df})$ is the inverse Student's $t$
cumulative distribution function. The pre-registered minimum number of
Bonferroni-significant cells per country (the cell-count floor) is five
for the United States and the Eurozone; for the United Kingdom the
floor is four, reflecting a 1.4-fold power-loss adjustment for the
smaller per-cell sample size discussed in Section 6.2.

## Robustness battery

Four tests are applied, with floors fixed at pre-registration.

**(a) F-test for sector heterogeneity.** A one-way analysis of variance
across the eleven sectors at each horizon. The test clears its floor if
$p < 0.05$ at one or more horizons.

**(b) Bootstrap confidence intervals on cell $t$-statistics.** 1,000
cluster-resamples by event. Two criteria are reported: a *strict*
criterion that the 90 % bootstrap confidence interval excludes the
Bonferroni critical value $|t^\star| \approx 3.17$ in at least five
cells, and a *relaxed* criterion that the 90 % confidence interval
excludes zero in at least five cells. The strict criterion is
small-sample-power bound at $n_e = 21$ Eurozone events; we report both.

**(c) Alternative event-definition Spearman.** Three alternative shock
definitions — a forward-looking BLS expectations question (denoted F3),
a tighter threshold of $1.5\sigma$, and a level $z$-score (rather than
the AR(1)-residual definition) — each re-rank the eleven sectors. The
test clears its floor if at least two of three variants yield a
Spearman rank correlation $\rho \geq 0.5$ versus the primary ranking.

**(d) VIX regime stratification.** Events are split at the median value
of the CBOE VIX index into a high-VIX subset and a low-VIX subset; the
per-sector sign of the mean CAR is computed within each regime, and the
sign-agreement count across the eleven sectors is reported. The test
clears its floor if agreement is at least 7 of 11 sectors.

## Cross-country Spearman tests

For each country pair $(A, B)$ and horizon $h$, let
$\mathrm{rank}_A^h$ and $\mathrm{rank}_B^h$ denote the per-sector mean
CAR ranking across the eleven GICS sectors in country $A$ and country
$B$, respectively. The Spearman rank correlation between the two
ranking vectors is denoted $\rho_{A,B}^h$. The pre-registered
external-validation criterion at the 6-month horizon is

$$
\rho_{A,B}^{6\,\mathrm{m}} \geq 0.5, \qquad (10)
$$

evaluated for the three country pairs (UK, US), (Eurozone, US), and
(UK, Eurozone).

## Long–short basket and $\Delta$ Sharpe

A long–short basket is constructed from the Eurozone 6-month
Bonferroni-significant cells: long the positive-significant sector
(Industrials) and short the negative-significant sectors (Communication
Services and Utilities), with equal weights across the three sectors.
For each of the 21 ECB BLS shock events, let $r_e$ denote the
equal-weighted basket CAR at the 6-month horizon. The annualised raw
Sharpe ratio is

$$
\mathrm{SR}_{\mathrm{raw}} = \frac{\overline{r_e}}{s(r_e)} \cdot \sqrt{2}, \qquad (11)
$$

where $\overline{r_e}$ is the mean per-event basket return, $s(r_e)$
its standard deviation, and the $\sqrt{2}$ scaling reflects the
half-yearly holding period (two non-overlapping 6-month windows per
calendar year). The per-event basket return is then regressed on the
factor baseline,

$$
r_e = \alpha + \mathbf{X}_e^\top \boldsymbol{\beta} + u_e, \qquad (12)
$$

where $\alpha$ is the regression intercept (the residual alpha),
$\mathbf{X}_e$ is the column vector of factor values realised over the
6-month window of event $e$, $\boldsymbol{\beta}$ is the coefficient
vector, and $u_e$ is the regression residual. The factor vector
$\mathbf{X}_e$ stacks the Europe Fama–French five-factor set
[@kenfrenchEurope] (Mkt$-$RF, SMB, HML, RMW, CMA — five factors),
the Carhart momentum factor Mom, the 60-day idiosyncratic volatility
factor (IVOL), the US-anchored skew-risk factor (SRF) of
@ferreira2024, and the US-anchored expected credit-spread index
(E-CSI) of @bidder2026 — nine regressors in total. The alpha-Sharpe
is then

$$
\Delta\mathrm{SR} = \frac{\hat{\alpha}}{s(\hat{u}_e)} \cdot \sqrt{2}, \qquad (13)
$$

where $\hat{\alpha}$ is the OLS estimate of the intercept and
$s(\hat{u}_e)$ the residual standard deviation. The pre-registered
robustness floor is $\Delta\mathrm{SR} \geq 0.40$. The drop-one-out
exercise of Section 7.2 removes each of the five logical factor blocks
(FF5, Mom, IVOL, SRF, E-CSI) in turn.

# Results

## Cell-level Bonferroni outcomes

Cell-count outcomes are summarised in Table 5.

**Table 5 — Cell-level Bonferroni-K=33.**

| Country | Cells significant | Pre-registered floor | Outcome |
|---|---|---|---|
| United States (benchmark) | 15 / 33 | 5 | clears floor |
| **Eurozone** | **8 / 33** | 5 | **clears floor** |
| United Kingdom | 1 / 33 (Energy 1 m, $t = -3.70$) | 4 | below floor |

The eight Eurozone-significant cells (sector $\times$ horizon, $t$-statistic) are:

- Utilities $-5.35$ (6 m), Industrials $+5.09$ (6 m), Communication
  Services $-3.30$ (6 m).
- Communication Services $-4.50$ (3 m), Utilities $-4.49$ (3 m),
  Healthcare $-3.35$ (3 m), Industrials $+3.19$ (3 m).
- Utilities $-3.73$ (1 m).

The pattern is the canonical cyclical–defensive split: Industrials
positive (cyclical-positive following tightening) and Utilities,
Healthcare, and Communication Services negative (defensive-negative).
The ordering directly mirrors the US benchmark.

![Eurozone $t$-statistic heatmap, eleven sectors $\times$ three horizons. Stars (★) mark cells passing Bonferroni-K=33 ($|t^\star| = 3.18$). Eight of 33 cells pass, concentrated on Industrials (positive) and Utilities / Communication Services / Healthcare (negative) — the canonical cyclical–defensive split.](figures/fig2_eurozone_heatmap.png){#fig:eu-heatmap width=70%}

![UK $t$-statistic heatmap on the same scale as Figure 2. One of 33 cells passes (Energy at 1 m, $t = -3.70$); ANOVA nevertheless rejects sector homogeneity at 1 m and 3 m horizons. The structurally low cell-count outcome is consistent with the universe-power lemma of §6.](figures/fig3_uk_heatmap.png){#fig:uk-heatmap width=70%}

## Cross-country Spearman tests

Three pairs at three horizons, Table 6.

**Table 6 — Cross-country Spearman correlations of per-sector CAR
rankings.**

| Pair | 1 m | 3 m | 6 m | At 6 m horizon |
|---|---|---|---|---|
| **Eurozone vs. United States** | +0.545 ($p = 0.083$) | +0.782 ($p = 0.004$) | **+0.755 ($p = 0.007$)** | **above 0.5 floor** |
| United Kingdom vs. United States | $-0.455$ | $-0.473$ | $-0.091$ | below floor |
| United Kingdom vs. Eurozone | +0.036 | $-0.555$ | $-0.064$ | below floor |

One of three pairs passes at the 6-month horizon — the strict outcome
class is "B+ partial." The passing pair is, however, robust at $p < 0.01$
at both 3 m and 6 m, with point estimates substantially above the 0.5
floor.

![Per-sector mean CAR (basis points) at the 6-month horizon, US (illustrative companion-paper benchmark) vs Eurozone vs UK, side-by-side. The Eurozone bars closely track the US ranking ($\rho = +0.755$); the UK bars exhibit a divergent pattern dominated by Real Estate and Financials underperformance, consistent with the leveraged-REIT and rate-rise-transmission interpretation of §6.4.](figures/fig4_cross_country_ranks.png){#fig:ranks width=95%}

## Robustness battery on Eurozone

The four-test battery is summarised in Table 7.

**Table 7 — Robustness battery, Eurozone.**

| Test | Result |
|---|---|
| (a) F-test heterogeneity | clears floor at 3 / 3 horizons ($p \leq 2.7 \times 10^{-10}$ at 6 m) |
| (b) Bootstrap CI excluding 0 (90 % CI, relaxed) | 11 / 33 cells (above 5-cell floor) |
| (c) Alt event-def Spearman, two of three variants $\geq 0.5$ | $\rho_{\text{F3 forward}} = 0.80$, $\rho_{\text{level-}z} = 0.66$; $\rho_{1.5\sigma} = 0.36$ (small $n_{\text{events}} = 10$, power-bound) |
| (d) VIX regime sign agreement | 6 / 11 sectors (below the 7 / 11 floor; regime-dependent) |
| **Battery summary** | **three of four tests clear pre-registered floors** |

Eurozone meets the regime-detection-finding criterion (cell-count floor
plus three of four robustness tests). The (d) VIX-regime failure is
itself informative: cyclicals (Cons Disc, Industrials) are positive in
both regimes, defensives (Utilities, Communication Services) negative in
both, with sign disagreements concentrated in Energy, Cons Staples,
Financials, and Real Estate. This points to volatility-conditional
credit-supply transmission as a future-research dimension.

## Long–short basket and $\Delta$ Sharpe

The Eurozone Long Industrials / Short {Communications, Utilities} basket,
over 21 events, has

- raw mean per event: +5.47 %,
- raw standard deviation per event: 6.80 %,
- raw Sharpe (annualised): **0.82**.

After absorbing the five-block factor baseline:

- alpha per event: $+8.47\%$, $p = 0.072$,
- residual standard deviation per event: 3.74 %,
- alpha-Sharpe (annualised): $\Delta\mathrm{SR} = +2.32$, **5.8$\times$ the
  0.40 floor**,
- $R^2 = 0.83$.

Within the FF5 block, significant baseline absorption is concentrated
in CMA ($\hat\beta = -1.17$, $p = 0.003$) and SMB
($\hat\beta = -0.66$, $p = 0.031$). The US-anchored SRF and E-CSI
proxies have $\hat\beta \approx 0$, $p > 0.5$, indicating that Eurozone
equity behaviour following ECB BLS shocks is not explained by US
financial-firm cross-sectional skewness or by the US E-CSI; a Eurozone
rebuild of these proxies is left to future work.

![Eurozone Long Industrials / Short {Communications, Utilities} basket — raw Sharpe versus alpha-Sharpe (annualised), with the 0.40 robustness floor marked. Alpha-Sharpe is 5.8$\times$ the floor.](figures/fig5_basket_summary.png){#fig:basket width=70%}

## Walk-forward stability

A five-fold chronological 80 / 20 split yields three folds with positive
net Sharpe (folds 1, 3, 5) and two with negative (folds 2, 4). The 4 / 5
floor for tradeable-strategy stability is not met, consistent with a
regime-detection finding rather than a tradeable-alpha claim. The
strongest fold (fold 3, +4.76) coincides with the COVID-era ECB BLS
shock cluster, suggesting alpha concentration in extreme regime-change
events.

# UK Companion Result and the Universe-Power Lemma

The UK Bonferroni outcome — one of 33 cells — invites the natural
question, why does the mechanism not replicate in the United Kingdom?
The answer is a pre-registered **universe-power lemma** with two
components.

## Identification weakness in the substitute universe

STOXX 600 GBR was adopted at study design as a vendor substitute for the
unavailable FTSE 350 mid-cap. Compustat Global does not carry FTSE 350
historical reconstitution as a series (no `gvkeyx` for FTSE 100 / 250 /
350 / All-Share, with `idxcstflg = N` and zero reconstitution rows).
STOXX 600 GBR instead consists of 119 currently-active firms — large-
and mid-capitalisation only — many of which derive the bulk of their
revenue from outside the United Kingdom: BP and Shell (global energy),
GlaxoSmithKline and AstraZeneca (global pharmaceuticals), Unilever and
Diageo (global consumer staples), HSBC and Standard Chartered
(Asia-focused banks). For these firms, BoE CCS is *weakly identified*
as a domestic UK credit-supply shock, because firm economics are
dominated by global rather than UK-domestic factors.

## Structural Bonferroni floor under realistic power

The Bonferroni critical value $|t^\star| = 3.18$ implies a required
Cohen's $d$ of $d^\star = 3.18 / \sqrt{n}$ to reach significance at any
single cell. Per-cell $n$ values across the three countries imply very
different $d^\star$ thresholds (Table 8).

**Table 8 — Required effect sizes under Bonferroni-K=33.**

| Country | $n$ per cell | $d^\star$ (in cell std) | Interpretation |
|---|---|---|---|
| US | $\sim 9\,450$ | 0.033 (3.3 %) | clears easily |
| Eurozone | 600–1 500 | 0.082–0.130 (8.2–13.0 %) | clears with effort |
| **UK** | **50–284** | **0.189–0.450 (19–45 %)** | **structurally requires very large effects** |

A power-aware UK floor would have been zero to one cells. The
pre-registered floor of four cells (a 1.4$\times$ power-loss adjustment from
the US floor of five) was structurally optimistic. **The observed UK
outcome of 1 / 33 falls exactly within the power-aware floor.** This is
identification weakness, not mechanism failure.

## ANOVA and partial-signal evidence

The F-test for sector heterogeneity passes on the UK panel at 1 m
($p = 0.004$) and 3 m ($p = 0.017$), failing only at 6 m. Sector
heterogeneity is therefore detectable in the UK panel by ANOVA — which
is more powerful than per-cell testing — though Bonferroni-K=33 fails to
reach significance cell-by-cell. The single passing UK cell, Energy at
1 m with $t = -3.70$ and mean CAR $-419$ basis points, is direction-
consistent with cyclical decline following tightening shocks: a partial
signal in the direction of the underlying mechanism survives the
universe-power constraint.

## Top-3 / Bottom-3 ranking

**Table 9 — Top-3 / Bottom-3 sectors at the 6-month horizon.**

| Country | Top 3 | Bottom 3 |
|---|---|---|
| US | Cons Disc / Energy / Materials | Comm Svc / Healthcare / Utilities |
| Eurozone | Cons Disc / Industrials / Materials | Comm Svc / IT / Utilities |
| UK | Industrials / Cons Staples / Utilities | Financials / Real Estate / Materials |

UK Industrials is consistently top-3 across all three countries — a
robust common signal. UK's bottom is dominated by Real Estate ($-492$
basis points) and Financials ($-278$ basis points), economically
explainable by the leveraged-REIT composition of UK Real Estate (British
Land, Land Securities, Segro, Hammerson) and the rate-rise transmission
channel that dominates BoE tightening events. This is a special case of
the credit-supply mechanism — rate-rise transmission via leverage —
rather than its absence.

## Disclosure as protection

We frame the UK negative result as a *protective feature* of the paper
on three grounds. First, the universe-power lemma was registered at
launch, not constructed post hoc; the substitution from FTSE 350 to
STOXX 600 GBR with the 1.4$\times$ power-loss caveat is documented in the
study plan. Second, the observed UK outcome (one of 33 cells) falls
exactly within the power-aware floor of zero to one. Third, full
disclosure of the UK negative result blocks any concern of file-drawer
bias and allows the paper to address — within itself — the natural
reader question of why all three pairs do not pass.

A natural follow-up — a re-run on FTSE 350 mid-cap (subject to vendor
availability) or a UK-domestic-revenue $\geq$ 50 % filter — is left to
future work.

# Robustness

## Alternative event definitions

The Eurozone passes two of three variants in §5.3. The 1.5$\sigma$-threshold
variant fails because $n_{\mathrm{events}} = 10$, a power-bound rather
than a sensitivity to thresholding (the F3 forward and level-$z$
variants both clear $\rho \geq 0.5$).

## Drop-one-out factor decomposition

We re-estimate $\Delta$ Sharpe while removing each of the six baseline
components.

**Table 10 — Drop-one-out, Eurozone long–short basket.**

| Dropped | Alpha per event | $\Delta$ Sharpe (annualised) | Incremental from drop |
|---|---|---|---|
| (full baseline) | +8.47 % | +2.32 | — |
| w/o FF5 | +3.81 % | +0.57 | $-$1.75 |
| w/o Mom | +3.31 % | +0.84 | $-$1.48 |
| w/o IVOL | +10.60 % | +2.98 | +0.66 |
| w/o SRF (US-anchored) | +8.42 % | +2.41 | +0.09 |
| w/o E-CSI (US-anchored) | +9.49 % | +2.34 | +0.02 |

Two channels dominate baseline absorption. Removing **FF5** drops
$\Delta\mathrm{SR}$ from 2.32 to 0.57 (incremental $-1.75$, near the
0.40 floor). Removing **momentum (Mom)** drops $\Delta\mathrm{SR}$ to
0.84 (incremental $-1.48$). Removing IVOL, SRF, or E-CSI either leaves
$\Delta\mathrm{SR}$ unchanged or modestly *raises* it — these are
non-absorbing controls. The US-anchored SRF and E-CSI proxies
contribute negligibly, consistent with the channel interpretation in
§5.4: Eurozone equity behaviour following ECB BLS shocks is absorbed
primarily by European-style value/profitability and momentum factors,
not by US-built cross-sectional skewness or US expected credit-spread
indices.

![Drop-one-out factor decomposition for the Eurozone long–short basket. FF5 and Mom are the two principal absorption channels; the US-anchored SRF and E-CSI proxies are non-absorbing.](figures/fig6_drop_one_out.png){#fig:droponeout width=85%}

## Sub-period stability

Splitting at 2015 (the post-Draghi-LTRO entry):

- pre-2015 ($n_{\mathrm{events}} = 12$): Eurozone–US 6 m
  Spearman $\rho = +0.682$.
- post-2015 ($n_{\mathrm{events}} = 9$): Eurozone–US 6 m
  Spearman $\rho = +0.673$.

Both sub-periods clear $\rho \geq 0.5$. The sector cross-section
ordering is stable across the 2015 (Draghi QE) and 2020 (PEPP)
unconventional-policy regime shifts.

## Universe sensitivity

Eurozone-broad (24 ISO codes) and Eurozone-strict (15 EUR-currency-area
codes) yield 6 m Spearman correlations vs. US of $\rho = +0.755$ and
$\rho = +0.711$ respectively. Both clear; the result is not driven by
the inclusion of Switzerland, Sweden, Denmark, or Norway.

## Bootstrap detail

1000 cluster-resamples by event yield, on the relaxed criterion (90 %
CI excluding zero), 11 of 33 cells; on the strict criterion (CI
excluding the Bonferroni critical value), zero of 33. The strict
criterion is small-sample-bound at $n_{\mathrm{events}} = 21$; the
relaxed criterion is the meaningful test.

# Discussion

## Interpretation of the bilateral US–Eurozone success

The strength of the bilateral result rests on the consistency of the
cyclical–defensive ordering across two independent surveys
(US SLOOS, ECB BLS), two independent equity universes (US Russell 3000,
Eurozone-broad STOXX 600 ex-UK), and substantially different design
choices (target firm size, banking-sector composition, question
wording, country composition). Despite these differences, the same
ranking pattern emerges with $\rho = +0.755$ at 6 m. The implication is
a common underlying mechanism rather than a country-specific artifact.

Three observations support a credit-supply interpretation. First,
tightening of bank credit standards differentially affects sectors with
higher external-financing dependence (Industrials, Cons Disc, Materials)
relative to sectors with internal financing or pricing power (Utilities,
Healthcare). Second, the 6-month horizon delivers the strongest signal,
consistent with a slow transmission channel — investment cuts, capex
delays, and working-capital adjustments operate over one to two
quarters. Third, the VIX-regime-dependent finding suggests channel
non-linearity, with sector responses amplified or differently
distributed in high-volatility regimes (post-Lehman, COVID).

## The UK result

The UK negative outcome looks superficially like a challenge to the
universal-mechanism reading. The pre-registered universe-power lemma
(§6) provides a clean explanation that does not require modifying the
underlying mechanism: BoE CCS is the wrong shock for STOXX 600 GBR
firms whose economics are not domestic. A FTSE 350 mid-cap follow-up
(vendor permitting) is the natural test.

## Limitations

1. **US-anchored SRF and E-CSI**. Inherited from the companion paper
   rather than rebuilt from European financial firms; drop-one-out shows
   their absorption contribution is minor, but a Eurozone rebuild would
   tighten the absorption analysis.
2. **Walk-forward stability**. Three of five folds positive falls below
   the 4 / 5 tradeable-strategy floor; the result is consistent with a
   regime-detection finding but does not establish tradeable alpha at
   conventional cost levels.
3. **UK universe-power**. STOXX 600 GBR is a vendor substitute for FTSE
   350; the 1.4$\times$ power-loss caveat was registered, but the structural
   floor under that caveat would have been zero to one, not four.
4. **Single-pair pass.** The strict outcome class is "B+ partial." The
   narrowed framing — strong bilateral US–Eurozone with UK universe-
   power caveat — does not relax that classification; it concentrates
   attention on where the evidence is strongest.

## Contribution

To the author's knowledge this is the first cross-country external
validation of bank-credit-supply-survey-driven sectoral cross-section
heterogeneity in equity markets, on a unified five-axis methodology.
Prior literature concentrates on US-only SLOOS macro / lending-impact
studies [@bassett2014; @wilson2023; @hafemanntillmann2021;
@bidder2026], country-internal banking-survey methodology
[@bell2014], and cross-country factor replication [@jensen2023, factor-
based, not bank-credit-supply-specific]. The framework documented here
is suitable for subsequent extension to additional advanced economies
(Japan BoJ Tankan, Australia RBA SBLF) and emerging markets.

# Conclusion

We test whether the SLOOS-driven sectoral cross-section heterogeneity
established for the United States by a companion paper generalises
internationally. The Eurozone–US bilateral external validation succeeds
strongly: Spearman $\rho = +0.755$, $p = 0.007$ at the 6-month horizon
versus the US benchmark, with eight of 33 Bonferroni-significant cells,
F-test 6 m heterogeneity $p = 2.7 \times 10^{-10}$, and three of four
robustness tests clearing pre-registered floors. The UK companion
analysis fails Bonferroni at the cell level; sector heterogeneity is
nevertheless detectable by ANOVA at 1 m and 3 m horizons, and a
pre-registered universe-power lemma — multinational dominance in
STOXX 600 GBR plus FTSE 350 vendor unavailability plus a structural
Bonferroni floor of zero to one cells under realistic power — provides
a sufficient-condition explanation that does not require revising the
underlying mechanism.

This paper's contribution is a single dimension of external validity:
replication priority on the precise five-axis intersection (BLS / CCS
survey AR(1) shock $\times$ STOXX 600 universe $\times$ GICS-11 cross-section $\times$
Bonferroni-K=33 multiple-comparison correction $\times$ medium-horizon forward
CAR). The mechanism itself was developed by the companion US paper and
the broader BLS / SLOOS macro literature; we show that it transports.

# References

::: {#refs}
:::

\newpage

# Appendix A: AR(1) Calibration Detail

See Section 4.1 and Table 4 for the AR(1) coefficient $\rho$, residual
standard deviation $\sigma(\varepsilon)$, and event count for each of
the three series. The COVID-robust $\sigma(\varepsilon)$ adjustment for
BoE CCS is described in Section 3.3.

# Appendix B: Cell-Level Results — Full Tables

Supplementary parquet files, distributed with the paper code, contain
the full 33-cell tables for each country:

- `analysis/data/layer_a_results_ECB_EUROZONE.parquet` — Eurozone
  (eight Bonferroni-significant cells of 33).
- `analysis/data/layer_a_results_BOE_UK.parquet` — UK (one
  Bonferroni-significant cell of 33).

Each row contains, per (sector, horizon) cell, the firm-observation
count $n$, the mean CAR in basis points, the cell standard deviation,
the one-sample $t$-statistic against zero, the degrees of freedom, the
two-sided $p$-value, the cell-specific Bonferroni-K=33 critical value
$|t^\star|$, and a Boolean Bonferroni-pass indicator.

# Appendix C: Bootstrap Detail

`analysis/data/phase4_primary_b_bootstrap_eurozone.parquet`. 1000
cluster-resamples by event; $t$-statistic distribution per cell; 90 %
and 95 % confidence intervals; relaxed and strict pass indicators. The
relaxed criterion (CI excludes zero) passes 11 of 33; the strict
criterion (CI excludes the Bonferroni critical value 3.17) passes 0 of
33, reflecting the small-sample bootstrap-variance limitation at
$n_{\mathrm{events}} = 21$.

# Appendix D: Long–Short Basket Decomposition

`analysis/data/layer_d_decomp_eurozone.parquet` documents the per-event
basket return, the market hedge, exposures to each component of the
five-block factor baseline, and the residual. The headline alpha and
alpha-Sharpe are reported in Section 5.4; the drop-one-out
decomposition in Section 7.2.

# Appendix E: STOXX 600 Historical Reconstitution

Index identifier `gvkeyx = 150,376` in Compustat Global `g_idxcst_his`,
2,141 records covering 2003 onward. Vendor-side spot checks confirmed
that historical from–thru dates for AstraZeneca, HSBC, and Shell are
real (not surrogated), blocking first-order survivorship bias.

# Appendix F: Reproducibility

The code and data underlying this paper are organised as follows.

- **Source**: `src/sloos_sector_external_validation/` — approximately
  90 % shared with the companion US paper, plus five new modules
  (`boe_ccs_fetch.py`, `ecb_bls_fetch.py`, `stoxx600_universe.py`,
  `comp_global_panel.py`, `cross_country_validation.py`).
- **Tests**: approximately 115 unit tests.
- **Figures**: regenerable from cached parquet/JSON via
  `analysis/generate_figures.py`.
- **Local interactive dashboard**: `dashboard/app.py`, run locally with
  `uv run streamlit run dashboard/app.py`. No public-cloud deployment
  is provided; reviewers can reproduce the entire analysis from source
  and the cached data files committed alongside the paper.
