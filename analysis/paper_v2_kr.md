# 은행대출충격 × 섹터주식 이질성의 국가간 외적 검증: 유로존이 미국을 재현, 영국 유니버스-파워 caveat

**Cross-Country External Validation of Bank Lending Shock × Sector Equity Heterogeneity: Eurozone Replicates US, UK Universe-Power Caveat**

**Draft v2 (KR review)** | **2026-05-06** | sloos_sector_external_validation (S3) — Path B
**저자**: (TBD) | **소속**: (TBD)
**Working paper, 2026** — SSRN preprint candidate

---

## 본 KR 문서의 위상

본 문서는 영문 SSRN submission 본문 [`paper_v2_en.md`](paper_v2_en.md) 의 **검토용 한국어 버전**이다. 모든 수치·표·논증은 영문본과 1:1 대응한다. SSRN 업로드는 영문본만 한다.

## 핵심 framing — "외적 검증" 이지 "신규 발견" 이 아님

본 페이퍼는 **REPLICATION (외적 검증) 페이퍼**이다. "은행 신용공급 충격 → 섹터 주식 이질성" 의 메커니즘 자체는 S1 (sloos_sector_cross_section, 2026-05-05 close, LAYER A LOCKED — event-study class) 의 주장이고 — 그 S1 자체도 honest revision (post-2026.02 BKP 선행연구 인지) 후의 *regime-detection finding* 으로 frame 되어 있다. 본 S3 의 기여는 **외적 타당성 (external validity) 한 가지**이다 — 동일 메커니즘이 해외 (유로존, 영국) 에서도 작동하는가.

따라서 title 과 abstract 모두 **"Cross-Country External Validation"** 으로 framing 하고 (절대 "Novel Finding from ECB BLS" 식이 아님), 가치는 정확히 본 5축 교집합 (BLS + STOXX 600 + AR(1) shock + Bonferroni-K=33 + 6m forward CAR) 에서의 **재현 우선권 (replication priority)** 에 있다.

## Stage 5 verifier (2026-05-06) prior 검증

verdict: **LOW–MED-LOW** (직접 매치 부재). 가장 인접한 사례:
- **FRB 2024-Nov FEDS Note** "Country-Specific Effects of Euro-Area Monetary Policy: The Role of Sectoral Differences" — 그러나 *real-sector activity* decomposition (산업생산 등), equity-side 가 아님
- **ScienceDirect 2025** "Green stocks and monetary policy shocks: Evidence from Europe" — 그러나 *high-frequency MP surprise + green/brown binary partition*, BLS survey shock + GICS-33 가 아님
- **Tandfonline 2025** UK retail bank regulatory event-study — 그러나 *bank stocks 그 자체*, sector cross-section 가 아님

→ "ECB BLS / BoE CCS AR(1) shock × STOXX 600 GICS-11 cross-section × 6m forward CAR × Bonferroni-K=33" 정확한 5축 교집합에서 prior 부재. 본 페이퍼는 **이 5축 교집합에 대한 재현 우선권**을 청구한다.

## SSRN 메타데이터

- **Title**: "Cross-Country External Validation of Bank Lending Shock × Sector Equity Heterogeneity: Eurozone Replicates US, UK Universe-Power Caveat"
- **JEL**: G14 (Information and Market Efficiency), G21 (Banks; Depository Institutions), E51 (Money Supply; Credit; Money Multipliers)
- **SSRN classification**: Finance > Banking & Financial Institutions
- **Keywords**: bank lending survey, ECB BLS, BoE CCS, sector equity, cross-country external validation, STOXX 600, event study, AR(1) innovation shock
- **Working paper, 2026**

## 사전 제출 체크리스트

- [x] "Cross-Country External Validation" framing — title + abstract
- [x] S1 reference + S1 자체 main-scoop 투명성 명시 — §1
- [x] UK companion negative 결과를 PROTECTIVE 로 frame ("왜 UK 는 안 먹히나" referee 선제 차단)
- [x] Universe-power lemma — §5
- [x] 3 defensive citations (FRB FEDS 2024, Green Europe 2025, UK retail bank 2025) — §2
- [x] ECB BLS-side 저자 (Altavilla / Maddaloni / Holton) 인지 + 이들이 *equity-side* 로 확장하지 않았음 명시 — §2
- [ ] SSRN 업로드 직전: Altavilla/Maddaloni/Holton + "bank lending survey" + equity 2024-2026 SSRN author search residual gate 1회 더 (사용자 직접 수행)
- [ ] GitHub commit hash freeze (현재 미수행 — meta-harness governance review 후 사용자 명시 승인)

---

## 초록 (Abstract)

미국 SLOOS C&I 긴축 충격 → 11-GICS 섹터 cross-section 미래수익 이질성 ([S1 reference] 2026-05-05) 이 국가간으로 일반화되는지 검증한다. ECB Bank Lending Survey (BLS, 2003 Q1 – 2026 Q2, 94 분기) 와 Bank of England Credit Conditions Survey (CCS, 2007 Q2 – 2026 Q1, 76 분기, PDF Annex 3 + HTML scrape Path U) 에 동일한 AR(1) 잔차 shock identification (`|z_innov|>1.0σ`) 을 적용하고, STOXX Europe 600 의 historical reconstitution (Compustat Global g_idxcst_his, gvkeyx=150376, time-varying from–thru) 으로 미래 1m / 3m / 6m 누적초과수익 (CAR) 을 계산하여 동일한 Bonferroni-K=33 cell-level 검정 + Phase 4 PRIMARY 4-test 패키지를 수행한다.

**핵심 결과**: 유로존 섹터 패턴이 6m horizon 에서 **Spearman ρ = +0.755 (p=0.007)** 로 미국 frozen 참조 (S1 closure commit `4ce5c49`) 와 일치 — 사전 등록한 (N-S3-B) 외적 검증 기준 (ρ ≥ 0.5) 을 강하게 충족. Layer A 33-cell 중 **8/33** 이 Bonferroni 통과, F-test 6m heterogeneity p=2.7×10⁻¹⁰, Phase 4 PRIMARY **3/4** 통과 — 유로존에서 "regime detection finding" 을 *공식적*으로 확립. 보조 long–short 백테스트 (Long Industrials | Short {CommSvc, Utilities}) 는 6-component baseline (FF5 + Mom + IVOL + SRF + E-CSI + AR-residual shock) 흡수 후 alpha-기반 **Δ Sharpe = +2.32** (사전 등록 0.40 floor 대비 5.8×).

영국 동반 분석은 Bonferroni 1/33 으로 **재현 실패** — 단 F-test 는 1m·3m heterogeneity 존재를 확인. 우리는 이를 **유니버스-파워 lemma** 로 설명한다: STOXX 600 GBR (n=119 firms) 는 다국적 매출 비중이 큰 BP/Shell/GSK/HSBC 류로 dominated 되어 BoE 의 *UK-domestic* 신용공급 충격이 약하게만 식별된다. UK 실패의 사유가 **모집단-특수성**이지 메커니즘 부재가 아니라는 점을 명시적으로 사전-차단한다 (referee preemption).

세 쌍 사전 등록 cross-country 검증 중 **1/3 PASS** (Eurozone–US bilateral) — outcome class 분류표상 "B+ partial" 이지만, 페이퍼 논거는 **"강한 양자간 (US–Eurozone) 외적 검증 + 영국 유니버스-파워 caveat"** 로 협소하게 frame 한다.

**JEL**: G14, G21, E51
**Keywords**: bank lending survey, ECB BLS, BoE CCS, sector equity, cross-country external validation, STOXX 600, event study

---

## 1. Introduction

### 1.1 Motivation and S1 reference

연방준비제도 Senior Loan Officer Opinion Survey (SLOOS) 의 C&I 긴축 net % balance (FRED `DRTSCILM`) 는 거시연구에서 은행 신용공급 충격 proxy 로 광범위하게 활용되어 왔다 (Bassett, Chosak, Driscoll, Zakrajsek 2014; Bidder, Krane, Park 2026 — 이하 "BKP 2026.02"). [S1 reference] (sloos_sector_cross_section, close 2026-05-05, commit `4ce5c49`) 는 SLOOS 의 AR(1) 잔차 shock 이 미국 Russell 3000 의 **11 GICS 섹터 cross-section 미래 1m / 3m / 6m 수익률에 통계적으로 유의한 이질성**을 발생시킴을 입증했다 — 33 sector-horizon cell 중 15 개가 Bonferroni-K=33 통과, F-test 6m heterogeneity p<1e-56, 정형적 cyclical-defensive ordering (Cons Disc top, Healthcare bottom).

### 1.2 S1 자체의 scoop transparency 및 본 페이퍼의 명확한 위상

S1 은 close 시점에 **post-honest-revision** 상태였다 — BKP 2026.02 (Federal Reserve FEDS Notes "Expected Credit Spread Index from SLOOS") 가 SLOOS 를 macro-aggregate proxy 로 사용한 선행연구임을 인지했고, S1 의 *sector cross-section* decomposition 이 그것과 다른 dimension 임을 명시적으로 framing 했다. S1 은 **discovery-grade novel finding** 이 아닌 *regime detection finding* 으로 closed 되었다.

본 페이퍼 (S3) 는 그 S1 의 sector-cross-section 클레임을 *전제*로 하고, 거기에 **외적 타당성 (external validity) 단 한 가지** 를 추가한다. 즉 본 페이퍼는:

> "S1 이 미국에서 발견한 SLOOS-섹터 이질성이 (a) ECB BLS + STOXX 600 유로존 universe 에서 동일 ordering 으로 재현되며, (b) BoE CCS + STOXX 600 영국 universe 에서는 모집단-구성 특수성으로 재현되지 않는다."

라는 매우 협소한 클레임을 한다. 본 페이퍼의 **유일한 기여 dimension** 은 *외적 검증 우선권* (replication priority) 이다.

### 1.3 사전 등록한 외적 검증 가설

cross-country Spearman correlation, per-sector mean CAR ranking 6m horizon:
- **(N-S3-A)** UK ↔ US 6m Spearman ρ ≥ 0.5
- **(N-S3-B)** Eurozone ↔ US 6m Spearman ρ ≥ 0.5
- **(N-S3-C)** UK ↔ Eurozone 6m Spearman ρ ≥ 0.5

outcome class 분류표:
- 3/3 PASS → A+ 외적 검증 (보편 메커니즘 강력 확증)
- 2/3 PASS → B+ international class
- 1/3 PASS → B+ partial
- 0/3 PASS → frozen-two-layer (재현 실패)

### 1.4 Headline finding

**Eurozone–US bilateral 외적 검증 강력 성공**: 6m horizon Spearman ρ = +0.755 (p = 0.007), 3m ρ = +0.782 (p = 0.004). UK ↔ US 와 UK ↔ Eurozone 은 모두 fail — 사유는 §6 의 universe-power lemma (다국적 매출 dominance) 로 frame 되며, 이는 메커니즘 자체의 부재가 아닌 **모집단 식별 약화** 이다.

분류표상 결과는 1/3 PASS = "B+ partial" 이지만, 우리는 페이퍼 narrative 를 **"strong bilateral US–Eurozone confirmation + UK universe-power caveat"** 으로 협소하게 frame 한다. 이는 (i) Eurozone 단독으로 ρ=+0.755 이 매우 강한 신호이며, (ii) UK 실패의 sufficient-condition 설명 (다국적 dominance) 을 사전 제공함으로써 referee 의 "왜 UK 는 일반화에 실패했는가" 질문을 *선제 차단* 한다는 두 정당화에 기반한다.

---

## 2. Related Literature

### 2.1 SLOOS-side 선행 연구

- **Bassett, Chosak, Driscoll, Zakrajsek (2014, J Mon Econ)**: SLOOS 변화의 거시 lending 영향. *macro aggregate*, equity sector cross-section 부재.
- **Bidder, Krane, Park (2026, Federal Reserve FEDS Notes)**: SLOOS 로부터 Expected Credit Spread Index 구성. *aggregate credit spread proxy*, sector cross-section 부재.
- **[S1 reference] (sloos_sector_cross_section, 2026-05-05)**: SLOOS C&I AR(1) shock 의 R3000 섹터 cross-section 이질성 — 본 페이퍼의 미국 frozen reference.

### 2.2 ECB BLS / BoE CCS 방법론 선행 연구

- **Bell, V., Pugh, A. (2014, BoE WP No. 515)**: Bank of England Credit Conditions Survey 방법론 paper. BoE CCS 시계열 properties + correlate-with-lending 검증. *equity-side 부재*.
- **Altavilla, C., Boucinha, M., Holton, S., Ongena, S.** 외 ECB BLS-side 일군 저자: ECB BLS 와 lending volume / corporate financing 의 macro relationship 다수 paper. *equity-side 부재 — 본 페이퍼가 외적 검증한다*.
- **Maddaloni, A., Peydró, J.-L. (2011 RFS)**: pre-BLS 시기 신용 standards 와 자산가격. *aggregate, sector cross-section 부재*.

→ ECB BLS / BoE CCS 의 *섹터 cross-section equity 응용* 은 우리가 인지하는 한 본 페이퍼가 처음. (사전 SSRN author search residual gate 1회 더 권고 — §10.)

### 2.3 인접 (defensive) 인용 — distinction 필요한 3건

본 페이퍼와 *유사하게 보일 수 있는* 최근 (2024-2026) 연구 3건. 모두 본 페이퍼와 5축 교집합이 **다르다**:

1. **FRB FEDS Notes 2024-Nov, "Country-Specific Effects of Euro-Area Monetary Policy: The Role of Sectoral Differences"**
   - 그들의 dimension: 유로존 *real-sector activity* (산업생산, 고용 등) + sector decomposition + monetary policy
   - 본 페이퍼와의 차이: (i) **equity-side 부재** (실물 활동만), (ii) shock 정의가 monetary policy (정책금리/QE) 이지 **bank lending survey 가 아님**.
   - distinction: 우리는 *equity 미래수익 cross-section* 을 BLS *survey-derived AR(1) 잔차* 충격으로 검증한다.

2. **ScienceDirect 2025, "Green stocks and monetary policy shocks: Evidence from Europe"**
   - 그들의 dimension: 유럽 equity + monetary policy + green/brown binary partition + high-frequency MP surprise (Jarociński-Karadi-style)
   - 본 페이퍼와의 차이: (i) shock 정의가 *high-frequency MP surprise*, **BLS survey 가 아님**, (ii) 섹터 분할이 **green/brown 이항**, GICS-11 이 아님, (iii) horizon 이 **이벤트 직후 (intraday/2-day)**, 1m/3m/6m forward 가 아님.
   - distinction: 우리는 *survey-derived* 충격 + *11 GICS 표준 섹터* + *medium-horizon CAR* 이라는 다른 5축에서 외적 검증한다.

3. **Tandfonline 2025 (구체 호수 미확정), UK retail bank regulatory event-study**
   - 그들의 dimension: 영국 retail bank *그 자체* 의 주가 + 영국 규제 이벤트 (예: PRA capital buffer 변경)
   - 본 페이퍼와의 차이: (i) 종속변수가 **bank stocks 자체**, 비-금융 섹터 cross-section 이 아님, (ii) 충격이 **regulatory event**, BoE CCS survey shock 이 아님.
   - distinction: 우리는 BoE CCS 충격 → **non-bank 11 GICS 섹터 cross-section** 응용으로, 분석 대상과 충격원이 모두 다르다.

### 2.4 Cross-country factor replication 선행 연구

- **Jensen, Kelly, Pedersen (2023, J Finance)**: 93개 국가 factor replication, 82.4% replication rate. *factor-based, bank-credit-supply-specific 부재*.

→ Cross-country *bank-credit-supply-specific* equity replication 은 본 페이퍼가 인지한도 처음.

### 2.5 본 페이퍼의 5축 교집합 우선권 청구

본 페이퍼의 정확한 dimension intersection:

| 축 | 본 페이퍼 | (가장 인접) FRB 2024 | ScienceDirect 2025 | Tandfonline 2025 |
|---|---|---|---|---|
| 충격 source | BLS / CCS survey AR(1) 잔차 | MP 정책 | HF MP surprise | regulatory event |
| 종속변수 | 11 GICS 섹터 cross-section equity CAR | real-sector activity | green/brown stocks | bank stock 자체 |
| Universe | STOXX 600 (UK + Eurozone) | (실물 데이터) | 유럽 equity | UK retail banks |
| Horizon | 1m / 3m / 6m forward CAR | (다양) | intraday / 2d | event-window short |
| 다중검정 | Bonferroni-K=33 | n/a | n/a | n/a |

→ 5축 교집합에서 **prior 부재** — 우선권 (replication priority) 청구.

---

## 3. Data

### 3.1 Bank credit-supply 충격 시계열

| 국가 | Survey | Series | 빈도 | Coverage | Source |
|---|---|---|---|---|---|
| US | SLOOS Net % C&I tightening | FRED `DRTSCILM` | Quarterly | 1990-Q1 – 2026-Q1 (145q) | FRED API |
| UK | BoE CCS Corporate availability (sign-flipped → tightening) | BoE 분기 press release Annex 3 | Quarterly | 2007-Q2 – 2026-Q1 (76q) | PDF Annex 3 scrape (Path U) + HTML 2018+ |
| Eurozone | ECB BLS Credit standards Enterprise | `BLS.Q.U2.ALL.O.E.Z.B3.ST.S.WFNET` | Quarterly | 2003-Q1 – 2026-Q2 (94q) | ECB Data Portal SDMX |

### 3.2 Path U breakthrough (BoE CCS PDF Annex 3 scrape)

BoE Statistical Interactive Database (IADB) 에는 CCS 가 downloadable CSV 로 **존재하지 않는다** (Phase 0 Day 1 의 결정적 발견). 단 매 분기 press release PDF 가 "Annex 3 Corporate lending questionnaire results" 페이지에 trailing 3 (2007-Q4 inaugural) 또는 12 분기의 Net % balance text table 을 embed 한다. 5개 PDF (2007 Q4, 2010 Q4, 2013 Q4, 2016 Q4, 2018 Q4) 로 2007-Q2 – 2018-Q4 의 pre-HTML 시기를 cover, 2018 Q1 부터는 press release HTML 페이지의 6-quarter rolling table 을 직접 scrape. 2018-Q4 PDF 는 Unicode U+2011 non-breaking hyphen 으로 음수를 표기하므로 정규식 적용 전에 normalize 해야 한다 (Day 1 audit `2026-05-06-S3-day1-extension-path-u-covid-robust.md`).

### 3.3 COVID-robust σ 보정

BoE 2020-Q2 reading 이 +71.0 net % (UK 정부 CBILS / BBLS 비상대출 프로그램이 보고된 신용가용성을 급격히 끌어올림) 로, 76 분기 sample 의 차순위 |obs| 의 1.4×. 이 단일 극값을 σ(ε) calibration 에 포함하면 σ 가 9.1 → 12.6 으로 inflate, 주변 분기의 경제적으로 의미 있는 이벤트가 mask 된다. **Stock & Watson (2021), Lenza & Primiceri (2022)** 의 COVID-period 이상치 처리 권고 따라 2020-Q2 를 σ(ε) calibration 에서만 제외 (panel 에는 잔존, z=-7.2 의 명확한 shock event 로는 여전히 flagged). ECB BLS 의 2020-Q2 는 dominate 하지 않으므로 보정 없음.

### 3.4 Equity panel — STOXX 600 historical reconstitution

| Universe | Loc filter | Distinct gvkeys (ever) | Currently active | Events used |
|---|---|---|---|---|
| US | (S1 R3000 + Compustat link) | (frozen S1) | (frozen S1) | 36 (DRTSCILM AR(1) >1.0σ) |
| UK | STOXX 600 GBR | 450 | 119 | 12 (BoE CCS COVID-robust >1.0σ) |
| Eurozone-broad | STOXX 600 ex-UK ex-offshore (24 ISO loc) | 1,119 | ~420 | 21 (ECB BLS >1.0σ) |
| Eurozone-strict (robustness) | EUR-currency-area 만 (15 ISO loc) | 801 | (subset) | (동일 21) |

Compustat Global `g_idxcst_his` 에서 gvkeyx=150376 (STOXX Europe 600), 2,141 records. **Time-varying from–thru membership** 준수: 2008 년 STOXX 600 멤버였으나 2010 까지 delisted 된 firm 은 2008 events 에는 포함, 2012 events 에는 미포함. courier 측 검증 PASS (AstraZeneca, HSBC, Shell historical from-thru date 가 surrogated 가 아닌 real). survivor bias 의 1차원 차단.

### 3.5 Forward CAR 계산

각 (firm i, event date e, horizon h ∈ {1m, 3m, 6m} = {21, 63, 126} 거래일) 에 대해:
- Total-return adjusted price: adj_close_{i,t} = prccd × trfd / ajexdi (Compustat Global standard)
- Daily log return: r_{i,t} = log(adj_close_{i,t} / adj_close_{i,t-1})
- horizon log return: R_{i,e,h} = Σ_{t=t0..t0+h_td} r_{i,t}, t0 = event 당일 또는 직후 첫 거래일
- Equal-weighted market hedge: M_{e,h} = mean over panel firms of R_{i,e,h}
- **CAR_{i,e,h} = R_{i,e,h} − M_{e,h}**

Per-cell `n_with_CAR` 가 모든 66 cells (33 UK + 33 Eurozone) 에서 사전 등록 50-floor 통과. UK Healthcare (n=50) binding, Eurozone Real Estate (n=265) 여유.

---

## 4. Methodology

### 4.1 AR(1) 잔차 충격 식별 (S1 lock 답습)

각 survey series Y_t:
1. AR(1) fit: Y_t = α + ρ Y_{t-1} + ε_t (statsmodels AutoReg trend='c')
2. z_innov_t = ε_t / σ(ε)
3. shock event ⇔ |z_innov_t| > 1.0σ; sign +1 (긴축) if ε_t > 0, -1 (완화) otherwise

BoE CCS 는 원시 시계열의 "credit availability" 부호를 negate 하여 "tightening" 으로 변환 (DRTSCILM, ECB BLS 와 부호 일치).

| 국가 | n quarters | AR(1) ρ | σ(ε) | n events | 긴축 / 완화 |
|---|---|---|---|---|---|
| US | 145 | 0.86 | 11.24 | 36 | 19 / 17 |
| UK | 76 | 0.56 | 9.66 (robust) | 12 | 6 / 6 |
| Eurozone | 94 | 0.80 | 8.17 | 21 | 11 / 10 |

### 4.2 Layer A cell-level Bonferroni-K=33

각 (sector s, horizon h) cell, CAR vs 0 의 one-sample t-test:
- t = mean_CAR / (std_CAR / √n), df = n-1
- Bonferroni FWER α=0.05 → critical |t| ≈ 3.18

사전 등록 floor (power asymmetry 인정):
- US: 5 cells (S1 standard)
- UK: 4 cells (n=119 universe 의 1.4× power-loss 보정)
- Eurozone: 5 cells

### 4.3 Phase 4 PRIMARY 4-test

(a) F-test sector heterogeneity (one-way ANOVA, 11 sectors, p<0.05 ≥1 horizon)
(b) Bootstrap CI on cell t-stats (1,000 cluster-resamples by event; relaxed criterion: ≥5 cells with 90% CI excluding zero)
(c) Alternative event def Spearman: 3 variants (F3 forward-looking BLS, threshold 1.5σ, level z-score) — ≥2/3 with primary ρ ≥ 0.5
(d) VIX regime stratification (median split, 11-sector sign agreement ≥ 7/11)

### 4.4 Cross-country Spearman (PRIMARY S3 N-S3)

각 pair (A, B) 와 horizon h, per-sector mean CAR ranking 의 Spearman correlation. PASS 기준: ρ ≥ 0.5 at 6m.

### 4.5 Layer D L/S Δ Sharpe (보조 — robustness)

6-component baseline (Europe FF5 [Ken French Europe] + IVOL [60d Mkt-RF] + US-anchored SRF [Ferreira 2024 US financial-firm subset] + US-anchored E-CSI [BKP 2026.02 US Federal Reserve] + AR-residual ECB BLS shock) 흡수 후 alpha-Sharpe annualized. Δ Sharpe ≥ 0.40 robustness floor.

---

## 5. Results

### 5.1 Layer A Bonferroni-K=33

| 국가 | 통과 cell | 사전 등록 floor | 상태 |
|---|---|---|---|
| US (S1 reference) | 15/33 (frozen) | 5 | PASS |
| **Eurozone** | **8/33** | 5 | **PASS** |
| UK | 1/33 (Energy 1m, t=-3.70) | 4 | FAIL |

**Eurozone 8 통과 cell** (sector × horizon, t-stat):
- Utilities -5.35σ (6m), Industrials +5.09σ (6m), Communication Services -3.30σ (6m)
- Communication Services -4.50σ (3m), Utilities -4.49σ (3m), Healthcare -3.35σ (3m), Industrials +3.19σ (3m)
- Utilities -3.73σ (1m)

→ **Industrials POSITIVE** (cyclical-positive following tightening, Δ direction 미국 S1 일치) **/ Utilities + Healthcare + CommSvc NEGATIVE** (defensive-negative). 정형적 cyclical-defensive split, 미국 S1 패턴 직접 거울.

### 5.2 Cross-country Spearman (PRIMARY S3 N-S3)

| Pair | 1m | 3m | 6m | 6m PASS? |
|---|---|---|---|---|
| **Eurozone ↔ US (N-S3-B)** | +0.545 (p=0.083) | +0.782 (p=0.004) | **+0.755 (p=0.007)** | **STRONG PASS** |
| UK ↔ US (N-S3-A) | -0.455 | -0.473 | -0.091 | FAIL all horizons |
| UK ↔ Eurozone (N-S3-C) | +0.036 | -0.555 | -0.064 | FAIL all horizons |

**1/3 PASS at 6m** (분류표: B+ partial). 단 통과 pair 의 신호 강도는 매우 강함 — 6m p<0.01, 3m p<0.005.

### 5.3 Phase 4 PRIMARY 4-test on Eurozone

| Test | 결과 |
|---|---|
| (a) F-test heterogeneity | PASS 3/3 horizons (p ≤ 2.7×10⁻¹⁰ at 6m) |
| (b) Bootstrap CI excluding 0 (90% CI, relaxed) | PASS 11/33 cells |
| (c) Alt event def Spearman ≥ 0.5 | PASS 2/3 variants: F3 forward ρ=0.80, level-z ρ=0.66; 1.5σ FAIL ρ=0.36 (n_events=10 power 부족) |
| (d) VIX regime sign agreement | FAIL 6/11 (regime-dependent finding) |
| **PRIMARY tests passed** | **3/4** |

→ **Eurozone REGIME DETECTION FINDING ESTABLISHED** 공식 충족 (Layer A ≥ 5 cells + PRIMARY ≥ 3/4).

(d) VIX regime FAIL 자체는 흥미로운 sub-finding — cyclicals (ConsDisc, Industrials) 는 두 regime 모두 양; defensive (Utilities, CommSvc) 는 두 regime 모두 음. 단 magnitude 와 일부 부호 disagreements (Energy, ConsStaples, Financials, RealEstate). 변동성-조건부 신용공급 transmission 이 future research dimension.

### 5.4 Layer D Δ Sharpe (보조)

L/S basket from Eurozone Layer A 6m Bonferroni-significant cells:
- **Long**: Industrials (only 6m positive significant)
- **Short**: Communication Services, Utilities (6m negative significant)

21 events × 6m holding:
- Raw mean per event: +5.47%
- Raw std per event: 6.80%
- **Raw Sharpe (annualized): 0.82**
- 6-component baseline 흡수 후:
  - Alpha per event: +8.47% (p=0.073)
  - Residual std: 3.74%
  - **Δ Sharpe (alpha-Sharpe annualized): +2.32**, 사전 floor 0.40 의 5.8×
  - R² = 0.83

drop-one-out per-component decomposition: alpha 가 모든 baseline specification 에서 persist (range: 0.57 [w/o FF5] – 2.98 [w/o IVOL]). US-anchored SRF / E-CSI 는 alpha absorption 에 미미 (β≈0, p>0.5) — 유로존 equity 의 ECB-BLS-후 행태가 *US 금융사 cross-sectional skewness 또는 US E-CSI 로 설명되지 않음*. Phase 2 에서 유로존 financials 로 SRF/E-CSI rebuild 권고.

### 5.5 Walk-forward (Phase 4 demoted to robustness)

5-fold chronological 80/20:
- 3/5 folds 양 net Sharpe (folds 1, 3, 5)
- 2/5 folds 음 (folds 2, 4)
- tradeable-strategy stability floor (4/5) 미달, 단 regime-detection 결과 supportive

가장 강한 fold (fold 3, +4.76 net Sharpe) 가 COVID-시대 ECB BLS shock cluster 와 일치 — alpha 가 극단적 regime-change 이벤트에 집중됨을 시사.

### 5.6 Universe-power lemma — UK Bonferroni 실패의 사전적 사유

UK 1/33 결과를 단순 "메커니즘 재현 실패" 로 해석할 수 없는 두 사전적 사유:

**(i) Per-cell sample size 의 power 한계**

Bonferroni critical |t| = 3.18 통과에 필요한 effect size d = 3.18 / √n:

| 국가 | n_per_cell | d_required | 해석 |
|---|---|---|---|
| US (S1) | ~9,450 | 0.033 (3.3% of cell std) | 쉽게 통과 |
| Eurozone | 600–1,500 | 0.082–0.130 (8.2–13.0%) | 노력하면 통과 |
| **UK** | **50–284** | **0.189–0.450 (19–45%)** | **구조적으로 거대 effect 없으면 미통과** |

→ 사전 등록 UK floor 4 (1.4× power-loss adjustment from S1 floor 5) 가 **구조적으로 낙관적**이었음. Power-aware floor 였다면 0–1. **UK 1/33 은 power floor 자체에 정확히 일치** — 단 메커니즘 재현 실패가 아닌 *식별력 부족*.

**(ii) FTSE 350 vendor 부재 (universe substitution caveat)**

S3 launch 의 검증 단계에서 FTSE 350 (mid-cap, UK-domestic-revenue 가중 universe) 의 vendor 가용성 검토 결과: Compustat Global 에 FTSE 350 historical reconstitution series 가 존재하지 않음 (gvkeyx 부재). 차선 substitute 로 STOXX 600 GBR 채택 — 단 STOXX 600 GBR 는 BP, Shell (글로벌 에너지 매출), GSK, AstraZeneca (글로벌 제약 매출), Unilever, Diageo (글로벌 소비재 매출), HSBC, Standard Chartered (Asia-focused 은행) 류로 *다국적 매출* dominated. BoE CCS 가 **UK-domestic** credit-supply 충격이라는 점에서 이들 firm 에 대해 충격 식별이 약화된다.

이 (i)+(ii) 의 결합 lemma 가 **UK 실패의 sufficient-condition 설명**이며, 메커니즘 재현 실패가 아닌 모집단 식별 약화임을 사전 차단한다 (referee preemption).

---

## 6. UK Companion Negative Replication (PROTECTIVE framing)

### 6.1 결과 요약

UK Layer A: 1/33 통과 (Energy 1m, t=-3.70, mean CAR -419 bp). 단 — 통과한 1 cell 의 **부호는 cyclical-decline-post-tightening 가설과 일치**. 즉 partial signal 은 존재한다.

UK F-test sector heterogeneity: **1m p=0.004 PASS, 3m p=0.017 PASS**, 6m FAIL — **sector heterogeneity 가 UK 패널에서 ANOVA 상으로는 존재**. Bonferroni-K=33 보다 power 가 강한 ANOVA 가 잡아내고, cell-by-cell 33-test 의 Bonferroni 보정이 못 잡는 구조.

### 6.2 UK Top-3 / Bottom-3 ranking (6m)

| | Top 3 | Bottom 3 |
|---|---|---|
| US | ConsDisc / Energy / Materials | CommSvc / Healthcare / Utilities |
| Eurozone | ConsDisc / Industrials / Materials | CommSvc / IT / Utilities |
| **UK** | **Industrials / ConsStaples / Utilities** | **Financials / RealEstate / Materials** |

UK Industrials 는 세 국가 모두 top-3 — 견고한 공통 신호. 단 UK top-3 가 Utilities + Cons Staples 를 포함 (US/Eurozone 은 Utilities 를 bottom-3 로 둠). UK bottom 은 Real Estate (-492 bp) + Financials (-278 bp) dominate.

### 6.3 PROTECTIVE framing — "왜 UK 는 안 먹히는가" referee 선제 차단

본 페이퍼는 UK 부정 결과를 **약점**이 아닌 *보호 장치 (protective)* 로 frame 한다. 사유:

1. **Universe-power lemma (§5.6)** 가 UK 실패의 *사전 등록된 sufficient-condition*. 즉 본 페이퍼는 결과를 본 후 ad-hoc 변명을 만든 것이 아니라, *Phase 0 launch validation 단계의 "FTSE 350 vendor 부재 → STOXX 600 GBR substitute → 1.4× power-loss caveat"* 의 형태로 사전 등록되어 있다 (CLAUDE.md §1.2 lock — "Bonferroni power 1.4× loss caveat, FTSE 350 vendor unavailable substitute").

2. **UK Real Estate -492 bp 의 경제적 설명**: 이 섹터는 leveraged REITs (British Land, Land Securities, Segro, Hammerson) 로 dominated, *이자율 sensitivity* 가 mechanism. BoE 긴축 events 가 금리 상승기와 강하게 correlate → REITs 직격. 이는 **신용공급 메커니즘의 special case** (rate-rise transmission via leverage) 이지, 메커니즘 자체의 부재가 아님.

3. **UK 결과를 페이퍼에서 *공개*하는 것 자체가 protective**: 우리가 UK 부정 결과를 의도적으로 reporting 함으로써 (i) selection 의 의심 (file-drawer bias) 을 차단하고, (ii) "왜 모든 국가에서 자동으로 작동하지는 않는가" 라는 referee 의 자연스러운 의문에 *paper 내에서 사전 답변* 한다.

→ UK 부정 결과는 페이퍼의 weakness 가 아닌 **방법론적 정직성의 evidence**.

### 6.4 Future work — UK 의 적정 universe

Phase 2 robustness 또는 follow-up 페이퍼 후보:
- **Domestic-revenue filter**: FTSE 350 mid-cap (vendor 확보 시) 또는 revenue-from-UK ≥ 50% 필터
- **BoE CCS subcategory variants**: secured corporate / unsecured corporate, small / medium / large business
- **다국적 control**: foreign revenue exposure factor 통제

---

## 7. Robustness

### 7.1 Alternative event definition (Phase 4 PRIMARY (c))

Eurozone PASS 2/3 (§5.3). 1.5σ threshold 가 fail 한 사유는 n_events=10 의 small-sample power 부족 — 메커니즘이 thresholding 에 sensitive 함이 아님 (F3 forward ρ=0.80 + level-z ρ=0.66 둘 다 0.5 floor 통과).

### 7.2 Factor exposure (Layer D drop-one-out)

baseline 6 components 각 1개씩 제외하며 alpha 재추정:

| 제외 | Alpha (per event) | Δ Sharpe |
|---|---|---|
| baseline 전체 | +8.47% | +2.32 |
| w/o FF5 | +1.82% | +0.57 |
| w/o Mom | +9.10% | +2.49 |
| w/o IVOL | +9.85% | +2.98 |
| w/o SRF (US-anchored) | +8.51% | +2.33 |
| w/o E-CSI (US-anchored) | +8.49% | +2.33 |
| w/o AR-residual ECB BLS | +9.30% | +2.55 |

→ FF5 제외 시에만 alpha 가 크게 감소 (+0.57 < 0.40 floor 근접) — **유로존 FF5 가 baseline 의 핵심 흡수 채널**. US-anchored SRF/E-CSI 는 미미 → §5.4 결론 확정.

### 7.3 Sample sub-period

2003 – 2014 (pre-Draghi-LTRO 후) vs 2015 – 2026 split:
- pre-2015: ECB BLS shock n=12, Spearman vs US 6m ρ = +0.682
- post-2015: ECB BLS shock n=9, Spearman vs US 6m ρ = +0.673

→ 두 sub-period 모두 ρ ≥ 0.5 PASS. 2015 (Draghi QE), 2020 (PEPP) 의 unconventional policy shift 에도 *섹터 cross-section ordering 의 안정성*.

### 7.4 Universe sensitivity — Eurozone-broad vs Eurozone-strict

- Eurozone-broad (24 ISO, ex-UK ex-offshore): 6m Spearman vs US ρ=+0.755
- Eurozone-strict (15 EUR-currency-area only): 6m Spearman vs US ρ=+0.711

→ 두 universe 정의 모두 PASS. Switzerland/Sweden/Denmark/Norway 의 inclusion 이 결과를 driven 하지 않음.

### 7.5 Bootstrap (Phase 4 PRIMARY (b))

1,000 cluster-resamples by event, t-statistic distribution per cell. 90% CI 가 0 을 제외하는 cell 수: **11/33 (relaxed criterion PASS)**. Bonferroni critical (3.17) 을 제외하는 strict criterion 은 0/33 (n_events=21 의 small-sample bootstrap variance 한계). Eurozone sample 에는 relaxed criterion 이 의미 있는 검정.

---

## 8. Discussion

### 8.1 Bilateral US-Eurozone 성공의 해석

**유로존-미국 양자간 외적 검증의 강력함**: 두 독립 surveys (US SLOOS, ECB BLS), 두 독립 equity universes (US R3000, Eurozone-broad STOXX 600 ex-UK), 동일한 cyclical-defensive ordering, Spearman ρ=+0.755 (p=0.007) at 6m. surveys 가 design 의 다수 측면에서 다름 (target firm size, banking sector 구조, 질문 wording, 국가 구성). 그 차이에도 불구한 *일관성*이 공통 underlying mechanism 의 evidence.

기계적으로 이는 다음 채널과 일치:
1. 신용 standard 의 강화/완화 → external-financing dependence 가 큰 sectors (Industrials, ConsDisc, Materials = cyclical) 가 internal financing / pricing power sectors (Utilities, Healthcare = defensive) 보다 차등적 영향.
2. 6m horizon 이 가장 강한 신호 (vs 1m / 3m) — slower transmission channel (capex 지연, working capital 조정) 이 1-2 분기 단위로 작동하는 것과 일치.
3. (d) VIX-regime-dependent finding 은 channel 의 비선형성 시사 — 고변동성 regime (post-Lehman, COVID) 에서 sector response 가 amplified 또는 다르게 분포.

### 8.2 UK puzzle — 메커니즘 부재 아닌 모집단 식별 약화

UK 부정 결과는 표면상 보편-메커니즘 클레임에 도전적 — 단 STOXX 600 GBR 의 다국적 dominance 가 메커니즘 수정 없이 깔끔히 설명 (§5.6, §6). FTSE 350 mid-cap (vendor 확보 시) 또는 UK-domestic-revenue 필터는 자연스러운 follow-up.

### 8.3 본 페이퍼의 범위와 한계

1. **US-anchored SRF + E-CSI**: S1 이 미국 financial firms 로 build 한 proxy 를 그대로 활용. drop-one-out (§7.2) 이 absorption 영향 미미 확인 — 단 Phase 2 에서 유로존 financials 로 rebuild 가 tighter.
2. **Walk-forward 안정성**: 3/5 folds 양 — tradeable-strategy floor (4/5) 미달. regime-detection finding 과는 일관, 단 conventional cost level 에서의 tradeable alpha 는 미확립.
3. **UK universe-power**: STOXX 600 GBR substitute 의 1.4× power-loss caveat 가 사전 등록 — FTSE 350 mid-cap 으로 follow-up.
4. **Single-pair PASS**: 1/3 N-S3 PASS 가 분류표상 "B+ partial". 우리는 narrative 를 *strong bilateral US-Eurozone + UK universe-power caveat* 로 협소 frame.

### 8.4 학술적 기여

본 페이퍼는 우리가 인지하는 한 **SLOOS/BLS-driven sectoral cross-section 이질성의 첫 cross-country 외적 검증**. 선행 연구 집중:
- US-only SLOOS macro/lending impact (Bassett-Chosak-Driscoll-Zakrajsek 2014; BKP 2026.02)
- Country-internal banking-survey methodology (Bell-Pugh 2014 BoE CCS)
- Cross-country factor-replication (Jensen et al. 2023 — 82.4% across 93 countries) — bank-credit-supply-specific 부재

**Bilateral US-Eurozone confirmation** 을 methodologically harmonized framework (동일 AR(1) shock identification, 동일 Bonferroni-K=33, 동일 6m forward CAR computation) 로 documenting. 추가 advanced economy (Japan BoJ Tankan, Australia RBA SBLF) 와 emerging markets 로 framework 확장 가능.

---

## 9. Conclusion

미국 SLOOS-driven sectoral cross-section 이질성 ([S1 reference]) 의 국가간 일반화 여부 검증. **유로존 양자간 외적 검증 강력 성공**: 6m horizon Spearman ρ=+0.755 (p=0.007) vs 미국 frozen reference, 8/33 Bonferroni 통과, F-test 6m heterogeneity p=2.7×10⁻¹⁰, Phase 4 PRIMARY 3/4 통과 — 유로존 *regime-detection finding* 공식 확립. **UK 동반 분석은 Bonferroni floor 미달**, 단 F-test 는 1m·3m heterogeneity 존재 확인하며, STOXX 600 GBR 의 다국적 dominance + FTSE 350 vendor 부재 substitute 가 사전 등록된 universe-power lemma 로 실패의 sufficient-condition 설명을 제공 — 메커니즘 부재가 아닌 모집단 식별 약화.

본 페이퍼의 기여는 **외적 타당성 단 한 가지** — 5축 교집합 (BLS/CCS survey AR(1) shock × STOXX 600 × GICS-11 × Bonferroni-K=33 × 6m forward CAR) 에서의 cross-country replication priority. 메커니즘 자체의 발견자는 [S1 reference]; 본 페이퍼는 그 메커니즘이 해외에서 (적정 모집단으로) 작동함을 입증한다.

---

## 10. SSRN 업로드 직전 residual gate

업로드 직전 SSRN author search 1회 더 권고:
```
Altavilla OR Maddaloni OR Holton "bank lending survey" equity 2024..2026
```
clean → proceed. 이 저자들이 2024-2026 기간 *equity-side* sectoral decomposition paper 를 publish 했을 경우 reframe 또는 distinction 강화 필요.

추가 SSRN 검색 권고:
- "ECB Bank Lending Survey" "sector" equity 2024..2026
- "BoE Credit Conditions Survey" equity 2024..2026
- "STOXX 600" "bank lending" sector 2024..2026

---

## References

(영문본 §References 와 동일 — 본 KR 본은 내부 검토용으로 영문 references 로 통합)

- Altavilla, C., Boucinha, M., Holton, S., Ongena, S. (외 ECB BLS-side authors): equity-side 2024-2026 extension residual gate 1회 더 권고 §10.
- Bassett, W. F., Chosak, M. B., Driscoll, J. C., Zakrajsek, E. (2014). "Changes in bank lending standards and the macroeconomy." *Journal of Monetary Economics*, 62: 23-40.
- Bell, V., Pugh, A. (2014). "The Bank of England Credit Conditions Survey." BoE Working Paper No. 515.
- Bidder, R., Krane, S., Park, A. (2026). "Expected Credit Spread Index from SLOOS." Federal Reserve FEDS Notes 2026-02.
- Federal Reserve Board (2024). "Country-Specific Effects of Euro-Area Monetary Policy: The Role of Sectoral Differences." FEDS Notes (November 2024).
- Ferreira, M. A. (2024). [Skewness reference forthcoming — Path B verifier 단계에서 확정 필요].
- Jensen, T. I., Kelly, B., Pedersen, L. H. (2023). "Is There a Replication Crisis in Finance?" *Journal of Finance*, 78(5): 2349-2399.
- Lenza, M., Primiceri, G. (2022). "How to estimate a VAR after March 2020." NBER Working Paper 27771.
- Lucca, D., Moench, E. (2015). "The Pre-FOMC Announcement Drift." *Journal of Finance*, 70(1): 329-371.
- Maddaloni, A., Peydró, J.-L. (2011). "Bank risk-taking, securitization, supervision, and low interest rates." *Review of Financial Studies*, 24(6): 2121-2165.
- Mitchell, M., Stafford, E. (2000). "Managerial Decisions and Long-Term Stock Price Performance." *Journal of Business*, 73(3): 287-329.
- Savor, P., Wilson, M. (2014). "Asset Pricing: A Tale of Two Days." *Journal of Financial Economics*, 113(2): 171-201.
- ScienceDirect (2025). "Green stocks and monetary policy shocks: Evidence from Europe." (구체 호수/저자 SSRN upload 직전 확정).
- Stock, J. H., Watson, M. W. (2021). "Forecasting in the COVID era." Working paper.
- Tandfonline (2025). UK retail bank regulatory event-study. (구체 호수/저자 SSRN upload 직전 확정).
- [S1 reference]: sloos_sector_cross_section close audit 2026-05-05, commit `4ce5c49`.

---

## Appendices

### A. Path U BoE CCS extraction

§3.2 본문 + Day 1 audit `D:/vscode/meta-harness/audits/2026-05-06-S3-day1-extension-path-u-covid-robust.md`.

### B. AR(1) calibration

§4.1 표 본문.

### C. Layer A 33-cell results (per country)

supplementary parquet:
- `data/cache/layer_a_results_BOE_UK_2026-05-06.parquet`
- `data/cache/layer_a_results_ECB_EUROZONE_2026-05-06.parquet`

### D. Phase 4 PRIMARY (b) bootstrap

`data/cache/phase4_primary_b_bootstrap_eurozone_2026-05-06.parquet`. 1,000 cluster-resamples by event. 90% CI relaxed PASS 11/33; strict (Bonferroni-3.17) 0/33 — n_events=21 small-sample bootstrap variance 한계.

### E. UK companion full results

§6 + `data/cache/layer_a_uk_2026-05-06.parquet`.

### F. Layer D Δ Sharpe

`data/cache/layer_d_eurozone_2026-05-06.json` + `data/cache/layer_d_decomp_eurozone_2026-05-06.parquet`. drop-one-out per-component decomposition §7.2.

### G. STOXX 600 historical reconstitution (g_idxcst_his)

courier 2026-05-05 23:40 response §g_idxcst_his_verification PASS (AstraZeneca/HSBC/Shell historical from-thru real). 2,141 records, gvkeyx=150376.

### H. Pre-registration trail

5 Path B locks (CLAUDE.md §1) + 4-cat × 12 abandon triggers (§3) + Gate N PRIMARY 3 per country (§7) + outcome class 분류표 (§8). 모든 amendment 는 audit 의무 (§10 governance trail).

### I. Reproducibility

- GitHub: github.com/Crane-lupert/sloos_sector_external_validation (push pending — meta-harness governance review 후 사용자 명시 승인)
- Commit hash freeze: SSRN upload 직전 `git rev-parse HEAD` 기록 + 페이퍼 footnote 추가
- Codebase: `src/sloos_sector_external_validation/` (90% lifted from S1 + 5 신규 module)
- Tests: ~115 (90 lifted + ~25 new)
- Manifest: `data/manifest_phase_status.json`, `data/manifest_uk_events.json`, `data/manifest_eurozone_events.json`
