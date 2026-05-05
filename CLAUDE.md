# sloos_sector_external_validation (S3)

**Status**: 🚀 **LAUNCHING — Path B** (fork from S1 sloos_sector_cross_section close commit `4ce5c49`, 2026-05-06)
**Pod**: Macro/Credit international extension (S1 = US realized lending shock / S3 = UK + Eurozone realized lending shock cross-country external validation)
**Mission**: Cross-country external validation of S1's SLOOS sectoral decomposition. UK (BoE Credit Conditions Survey) + Eurozone (ECB Bank Lending Survey) × STOXX 600 universe → cross-country sector pattern Spearman ≥ 0.5 in 3 of 3 pairs (UK ↔ US ↔ Eurozone) → A+ external validation, portfolio 3rd LAYER A LOCKED, J Mon Econ / RFS direct submission realistic.
**Reference**: `D:/vscode/meta-harness/audits/2026-05-06-S3-international-validation-reference-validation.md` (Change Manifest §0 + Lock 14 + 4-cat × 12 abandon trigger + Phase 0/1/2 plan)

Hypothesis: BoE CCS C&I-equivalent / ECB BLS C&I-equivalent AR(1) residual shock event (`|z_innov|>1.0σ`) → forward {1m, 3m, 6m} 11-GICS sector cross-section CAR cyclical heterogeneity (S1 와 same direction). Cross-country Spearman ≥ 0.5 in 3 of 3 pairs (UK ↔ US (S1) / Eurozone ↔ US (S1) / UK ↔ Eurozone) → external validation strong.

## 1. 강제 규칙 (Path B locks)

1. **BoE CCS + ECB BLS shock identification (Phase 0 Day 1 검증 CRITICAL)** — BoE statistical interactive database CCS C&I net % tightening + ECB SDW BLS C&I net % tightening series fetch + AR(1) residual shock identification (BKP 2026.02 methodology, S1 inheritance). `|z_innov|>1.0σ` event. **시작 시점 ≥2015 → ABANDONED** (n_event<10) per country.
2. **Universe lock (Path B specific)** — STOXX 600 (gvkeyx=150376, real reconstitution AstraZeneca/HSBC/Shell verified) via `comp_global_daily.g_idxcst_his` × `g_company`:
   - **UK**: STOXX 600 GBR-filter, 116 currently-active firms (Bonferroni power 1.4× loss caveat, FTSE 350 vendor unavailable substitute)
   - **Eurozone**: STOXX 600 full minus UK + non-eurozone (USA/ZAF/HKG) = ~421+ active firms (DEU/FRA/CHE/SWE/ITA/NLD/ESP/DNK/FIN/NOR/BEL/IRL/AUT/PRT/LUX 등)
3. **Forward horizons + cell-level test (PRIMARY) lock** — {1m, 3m, 6m}. Bonferroni-K = 11 sectors × 3 horizons = **33** per country, critical t ≈ **3.17** (df-finite) 양측 α=0.05.
   - UK PASS floor: ≥4 cells (Bonferroni power 1.4× loss adjusted, S1 floor 5 ÷ 1.4)
   - Eurozone PASS floor: ≥5 cells (full power, S1 floor 동일)
   - US S1 reference: 15/33 (frozen at S1 commit `4ce5c49`)
4. **F1-1 minority-class n_min (S1 inheritance)** — per (country × sector × horizon) cell n_with_CAR ≥ **50**.
5. **6-component baseline lock (US-anchored, paper limitation)** — FF5 + Mom (Ken French US, per-country factor 부재) + IVOL (60d Mkt-RF) + SRF (Ferreira 2024 US financial firm subset) + E-CSI (BKP 2026.02 US Federal Reserve) + **6th: AR-residual UK CCS / Eurozone BLS shocks** (cross-validation per country).
6. **Cross-country PRIMARY (Path B specific, S3 extension)**:
   - **(N-S3-A)** UK ↔ US (S1) 6m sector Spearman ≥ 0.5
   - **(N-S3-B)** Eurozone ↔ US (S1) 6m sector Spearman ≥ 0.5
   - **(N-S3-C)** UK ↔ Eurozone 6m sector Spearman ≥ 0.5
7. **Gate N PRIMARY 3 per country (binding, S1 inheritance)** —
   - **(N-1)** Cell-level Bonferroni-K=33 ≥ floor (UK 4 / Eurozone 5)
   - **(N-2)** F-test sector heterogeneity p<0.05 in ≥1 horizon
   - **(N-3)** Alternative event def Spearman ≥ 0.5 (BoE CCS subcategory: secured / unsecured corporate / mortgage / ECB BLS per-country: DEU/FRA/ITA/ESP)
8. **Outcome class**:
   - 3 of 3 N-S3 + Gate N per-country PASS strict → **A+ external validation, portfolio 3rd LAYER A LOCKED** (J Mon Econ / RFS realistic)
   - 2 of 3 N-S3 → A 2-of-3 country (B+ Layer A LOCKED — international class)
   - 1 of 3 N-S3 → B+ partial
   - 0 of 3 → frozen-two-layer (Path B sub-mode)
9. **OOS in-sample/OOS split 부과 금지 (Gate N inheritance)** — thin-event-study class mathematical impossibility per country.
10. **5 lock amendment governance trail** — 모든 amendment 시 audit 의무 (S1 답습).
11. **Layer D Δ Sharpe (illustrative supplementary, Gate N binding 아님)** — 6-component baseline 흡수 후 per-country incremental Δ Sharpe. n thin-sample marginal stat power 한계.
12. **Walk-forward + Bootstrap + alt event def (illustrative supplementary)** — Phase 2 robustness 보고.
13. **g_idxcst_his real-ness verified** — courier 2026-05-05 23:40 response §g_idxcst_his_verification PASS (AstraZeneca/HSBC/Shell). 단 STOXX 600 universe 의 *time-varying from/thru* 검증 의무 — survivor bias 잔존 위험.

## 2. Phase plan (14d hard cap)

- **Phase 0 (Day 1-3)**: data + universe + shock + correlation + n audit
  - Day 1: BoE CCS + ECB BLS fetch + 시작 시점 검증 + AR(1) calibrate per country + scoop check #1
  - Day 2: STOXX 600 universe build (UK GBR-filter 116 + Eurozone full ~421) + per-cell n_min audit
  - Day 3: comp_global panel build (per country) + Phase 0 EOD
- **Phase 1 (Day 4-9)**: Layer A 3 panels (UK / Eurozone / US S1 reference) + 6-component baseline + Layer D + cross-country Spearman first
- **Phase 2 (Day 10-12)**: alt event def per country (BoE CCS subcategory / ECB BLS per-country) + Bootstrap + outcome class final
- **Day 13-14**: paper + bilingual README + STOP (no gh push)

## 3. Abandon criteria (4-cat × 12)

- **Data**: BoE/ECB 시작 시점 ≥2015 / events<10 per country / per-cell n<50 / universe coverage<90% / WRDS courier comp_global fail
- **Mechanism**: Layer A < floor (UK <4 / Eurozone <5) / F-test all horizons fail / cross-country Spearman 0/3 PASS / alt event def Spearman <0.5
- **Resource**: OpenRouter>$5 / Day 14 hard cap / attention 2 세션 저하
- **Product-market**: weekly scoop monitor (Day 1+7+11) / BoE/ECB direct follow-up paper

**Path B scoop risk 10-15%** (S2 의 50-70% 보다 낮음 — international replication 가 prior 부재 추정).

## 4. Skill invocation

- **karpathy-guidelines** (각 phase 진입 전): Think Before Coding / Simplicity First (S1 lift 우선) / Surgical Changes (90% inheritance) / Goal-Driven Execution (cross-country external validation)
- **drift-watchdog** (매 phase 시작): Hypothesis lock / scope / metrics
- **abandon-criteria** (매 phase 시작 + trigger 발화 시): 4-cat × 12 triggers loaded from §3

## 5. Lifted from S1 (90% framework)

`src/sloos_sector_external_validation/` 안:
- layer_a.py (Welch t + Bonferroni-K=33)
- layer_d.py (5-component absorption)
- phase4_tests.py (F-test / Bootstrap / Spearman)
- srf_construct.py (Ferreira 2024 US)
- ecsi_construct.py (BKP 2026.02 US)
- factors_fetch.py (Ken French FF5+Mom US)
- wrds_courier_adapter.py
- ~90 lifted tests

신규 module 5종 (S3 own contribution, V0 가 Phase 0 Day 1-3 작성):
- boe_ccs_fetch.py
- ecb_bls_fetch.py
- stoxx600_universe.py
- comp_global_panel.py
- cross_country_validation.py

Tests: 90 lifted + ~25 new = ~115 by Day 14.

## 6. Stop conditions / Resumability

매 step 후 atomic commit + manifest update:
- data/manifest_uk_events.json
- data/manifest_eurozone_events.json
- data/manifest_phase_status.json
- data/manifest_openrouter_spend.jsonl
- data/manifest_wrds_query_log.jsonl

stop trigger 발화 시 `audits/RESUMABLE.md` 작성.

## 7. Governance + STOP

- A+ external validation 시 → `LAYER_A_LOCKED.md` + paper draft + bilingual README + Streamlit MVP
- A 2-of-3 country / B+ partial → status file + paper draft (modest framing)
- frozen-two-layer (Path B sub-mode) → `FROZEN_TWO_LAYER.md` + post-mortem
- ABANDONED → `ABANDONED.md`
- **NO gh push from S3** — meta-harness governance review 후 사용자 명시 승인 별도 단계 (S1 답습)

## 8. Path A (S2) ABANDON 영향

S2 (sloos_forward_guidance_sector) ABANDONED-pre-Phase0 2026-05-06 (FRED expectation series 부재, commit `8285d4f`). Path A + Path B 결합 narrative 약화 단 Path B 자체 standalone J Mon Econ candidate. S1 single-finding motivation 충분.

## 9. Reference (meta-harness)

- launch reference validation: `D:/vscode/meta-harness/audits/2026-05-06-S3-international-validation-reference-validation.md`
- V0 overnight-start-prompt: `D:/vscode/meta-harness/audits/2026-05-06-S3-international-validation-overnight-start-prompt.md`
- cp + bootstrap instructions: `D:/vscode/meta-harness/audits/2026-05-06-S3-cp-bootstrap-instructions.md`
- portfolio-research-rules.md §3 row + §5 Gate N + abandon-criteria SKILL §S1 + §S2
- S1 close audit: `D:/vscode/meta-harness/audits/2026-05-05-S1-governance-close-layer-a-locked-event-study.md`
- S2 close audit: `D:/vscode/meta-harness/audits/2026-05-06-S2-bootstrap-blocked-close-abandoned.md`
- courier outbox response: `E:/wrds-data-courier/outbox/S1-pathB-international-equity-data-response-20260505-234029.json`
- S1 reference panel: `D:/vscode/sloos_sector_cross_section/data/cache/crsp_sector_panel_DRTSCILM_AR1_TIMEVAR_v2_2026-05-05.parquet` (frozen at S1 commit `4ce5c49`)
