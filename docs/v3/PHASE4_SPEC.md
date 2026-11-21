# PHASE4_SPEC — SLOOS (S1·S3): 비슷한 가설의 사전 고정 시험

고정일 2026-11-21. 결과 변수 (수익률) 를 보기 전에 썼다. 공통 지시는 `../PHASE4_PROTOCOL.md`. 산출물은 `phase4/`.

## 0. 배경과 소재

게시 가설 ("대형 대출 태도 충격 분기 뒤 11개 섹터의 누적 초과수익") 은 3차에서 세 지역 모두 0/33 이었다 (`REPORT.md` §12). 그 설계는 분기 조사 한 계열 × 33개 셀이라 검정력이 낮다. 4차는 같은 조사 자료를 **단면이 넓은 설계** (은행별 대출 구성) 와 **단일 사전 고정 검정** (공표일 반응) 으로 다시 쓴다.

| 소재 | 위치 | 비고 |
|---|---|---|
| SLOOS 공표일 표 (1997년 이후 정확일) | `out/release_dates_US_SLOOS.csv` | 열 `release_date` (정확일), `approx_release_regular_practice` (1990–96 근사), `drtscilm` |
| ECB BLS·BoE CCS 공표일 표와 계열 | `out/release_dates_EZ_BLS.csv`, `out/release_dates_UK_CCS.csv`, `phase3/out/events_allq_{EZ,UK,US}.csv` | 3차가 쓴 것 그대로 |
| SLOOS 범주별 순긴축 계열 | FRED (`https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>`, 공개, 키 불필요). 저장소 캐시 `D:/vscode/sloos_sector_cross_section/data/cache/sloos_series_2026-05-05.parquet` 먼저 확인 | 확실한 ID: `DRTSCILM` (C&I 대·중견), `DRTSCIS` (C&I 소기업). 나머지 범주는 계열 제목으로 확인해 ID·제목·기간을 `FROZEN_PARAMS.json` 에 적는다. **ID 를 추측으로 쓰지 않는다** — 제목이 "Net Percentage of Domestic Banks Tightening Standards for …" 인지 확인 |
| 은행지주사 재무 (FR Y-9C, 2000-03 ~ 2025-12, 9,067개 지주사) | dump `bank_all.wrds_holding_bhck_1.csv.gz`, `…bhck_2…`, `…holding_other_1…` | 열이 1,000개 이상 — duckdb 로 필요한 열만. 항목 정의·유효 기간은 `bank_all.wrds_bank_reg_vars.csv.gz` |
| 은행–CRSP 연결 (rssd9001 ↔ permco, 유효 기간) | dump `bank_all.wrds_bank_crsp_link.csv.gz` | 1,213개 BHC 행, `dt_end` 최대 2024-09-30 |
| CRSP 일별·이름 이력, FF5+UMD | dump `crsp_a_stock.dsf_v2`, `dsenames`; `../X_sec_letter/phase3/cache/french_daily.parquet` | CRSP 는 2024-12 까지 |
| 유럽·영국 종목 패널 (STOXX 600 편입 이력 기준) | `phase3/out/panels/`, dump `comp_global_daily.g_secd.stoxx600_2003plus.csv.gz`, `g_company` (GICS) | S2 보조·S3 에만 |

## 1. S1 — 범주별 긴축 × 은행 대출 구성 → 은행주 단면 (주 검정 1)

- 가설: SLOOS 가 범주별로 보고하는 순긴축은 그 범주 대출의 향후 부실·수익 악화 신호다. 긴축이 큰 범주의 대출 비중이 높은 은행은 이후 수익률이 낮다.
- 범주 K (5개): CI (C&I: 대·중견과 소기업 계열의 평균), CRE (상업용 부동산: 그 시점에 있는 하위 계열의 평균), RRE (주택담보: 그 시점에 있는 하위 계열의 평균), CC (신용카드), OC (자동차·기타 소비자: 있는 계열의 평균). 범주에 계열이 없는 기간은 그 범주를 빼고 나머지 비중을 다시 1 로 맞춘다.
- 대출 비중 (Y-9C): CI = BHCK1763 + BHCK1764. CRE = 건설 (BHCKF158 + BHCKF159, 그 전은 BHDM1415) + 다가구 (BHDM1460) + 비주거 (BHCKF160 + BHCKF161, 그 전은 BHDM1480). RRE = BHDM1797 + BHDM5367 + BHDM5368. CC = BHCKB538. OC = BHCKB539 + BHCKK137 + BHCKK207 (K 항목 도입 전은 BHCKB539 + BHCK2011). 분모는 다섯 범주의 합. 항목 정의와 유효 기간을 `wrds_bank_reg_vars` 에서 확인하고, 대체가 필요하면 결과 변수 전에 `FROZEN_PARAMS.json` 에 적는다.
- 시점: 공표일 `r` 의 신호에는 `r` 보다 75일 이상 앞서 끝난 분기의 Y-9C 를 쓴다.
- 신호: `BT(i, r) = Σ_k share(i, k) × N(k, r)`, `N(k, r)` = 공표일 `r` 에 나온 범주 k 의 순긴축 (% 원값).
- 유니버스: 연결표로 `r` 에 유효한 BHC 의 CRSP 보통주 (shrcd 10/11, NYSE/AMEX/NASDAQ; 여러 종류면 시가총액이 큰 것), `r` 종가 ≥ $5, 시가총액 ≥ $100M.
- 포트폴리오: `r` 다음 거래일 종가에 BT 5분위. **LONG 최저 − SHORT 최고**, 동일가중, 다음 공표일의 다음 거래일 종가까지 보유.
- 통계량: 공표 간 보유 기간별 (약 분기) L/S 수익률의 시계열 평균과 t (Newey–West 1). **예상 부호 양.** 표본: 정확한 공표일이 있고 Y-9C 가 있는 2000년 이후 ~ CRSP 끝.
- 전·후반: 공표 연도 2000–2011 / 2012–2024.
- 함께 보고: 가치가중, 가격·시가총액 조건 없는 전체, 월별 달력 시간 FF5+UMD 절편, Fama–MacBeth (기간별 단면 회귀: 수익률 ~ 표준화 BT + log 시가총액 + 장부/시가 + 직전 12개월 수익률 + 3년 대출 증가율, 그리고 **범주 비중 자체를 통제에 넣은 판** — 비중의 고정된 프리미엄이 아니라 긴축의 시간 변동이 설명하는지), 다리별 평균 범주 비중, 기간별 종목 수, 비용 차감 (진입·청산 호가 스프레드 절반, 숏 차입료 연 1% 가정).

## 2. S2 — 공표일 은행주 반응 (주 검정 2)

- 가설: 긴축이 직전 조사보다 커진 공표일에 은행주가 시장보다 덜 오른다.
- 사건: 정확한 공표일이 있는 SLOOS 공표 (1997 ~ CRSP 끝). 놀람 `s(r) = DRTSCILM(r) − DRTSCILM(직전 조사)` (%p).
- 은행 포트폴리오: S1 과 같은 유니버스 (연결표가 닿지 않는 2000년 이전은 CRSP SIC 6020–6029·6710–6712 보통주, 같은 가격·시가총액 조건) 동일가중. `AR` = 은행 포트폴리오 수익률 − CRSP 가치가중 시장 수익률, 공표일과 다음 거래일의 누적 `[0, +1]`.
- 통계량: `AR[0,+1]` 을 `s(r) / 10` 에 회귀한 기울기, White 표준오차 t. **예상 부호 음.**
- 전·후반: 1997–2010 / 2011–2024.
- 함께 보고: `[0]` 만, 가치가중, 시장 수익률 자체의 반응 (양측), AR(1) 확장 창 잔차로 정의한 놀람, 놀람 상·하위 3분위의 평균 AR.
- 보조 (보고만, 은행 식별이 Compustat Global 의 GICS 4010 으로 바로 되는 경우에만): 유로존 (BLS 공표일, 기업 대출 순긴축 변화) 과 영국 (CCS 공표일, 부호를 긴축이 양이 되게 맞춘 변화) 의 같은 회귀. 은행 = STOXX 600 편입 종목 중 GICS 4010, 기준 = 같은 지역 편입 종목 동일가중.

## 3. S3 — 실시간 시장 타이밍 (참조. 주 검정 아님)

선행연구가 이미 한 가설이다: Chava–Gallmeyer–Park (2015, JME 74:117–132) 은 SLOOS 긴축이 낮은 향후 주식 수익률을 예측한다고 보고했고, Wilson (2023, FRL 54:103733) 은 공표 뒤 1–2개월 수익률 예측과 최근 10년의 약화를 보고했다. 여기서는 공표일 기준 실시간 판을 2024년까지, 세 지역으로 계산해 **성립 여부만 기록**한다.

- 미국: 보유 기간 = 공표 다음 거래일 종가 ~ 다음 공표의 다음 거래일 종가. CRSP 가치가중 시장 초과수익을 `DRTSCILM(r)` 수준에 회귀 (기울기 t, NW 1). 구간: 1997–2024, 1990–2024 (근사 공표일 포함), 2015–2024 (CGP 게시 이후).
- 표본 외 R² (확장 창, 역사적 평균 대비, Campbell–Thompson) 와 타이밍 전략 (`DRTSCILM(r)` 이 그때까지의 확장 중앙값 이하면 주식, 초과면 T-bill) 의 Sharpe 대 매수 후 보유.
- 유로존 (2003–2024)·영국 (2007–2024): STOXX 600 편입 종목 가치가중 지역 수익률로 같은 계산 (무위험 수익률은 0 으로 두고 그렇게 표기).

## 4. 다중검정과 판정

주 검정은 둘이다: S1, S2 (미국). Bonferroni 양측 5% / 2 → **|t| ≥ 2.24**. 판정 등급은 `../PHASE4_PROTOCOL.md` §3. S3 과 유럽·영국 보조는 판정에 넣지 않고 보고만 한다.

통과하더라도 지위는 "사전 고정 pilot 통과" 다. 이 가설군 (SLOOS → 주식 수익률) 은 S1·S2·S3 저장소에서 이미 세 번 시도됐고, 4차의 후보는 그 실패를 본 뒤에 골랐다. 분기 자료라 새 표본 외 구간은 앞으로 쌓이는 분기뿐이다. 이 점을 보고서 D 에 적는다.
