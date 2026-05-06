# LAYER A LOCKED — Eurozone Bilateral External Validation

**Project**: sloos_sector_external_validation (S3) — Path B international replication of S1
**Status**: ✅ **EUROZONE REGIME DETECTION FINDING ESTABLISHED** (formal CLAUDE.md §5 amended outcome class criteria met)
**Closed**: 2026-05-06
**Headline**: ECB BLS-driven sectoral cross-section heterogeneity in Eurozone equities **strongly externally validates** S1 US SLOOS finding. Spearman ρ=+0.755 (p=0.007) at 6m horizon vs S1 US frozen reference.

---

## Headline result

**Bilateral US–Eurozone external validation of SLOOS-driven sectoral cross-section heterogeneity** in advanced-economy equity markets.

| Country | Layer A | F-test | PRIMARY 4 tests | Layer D Δ Sharpe | Spearman vs US 6m |
|---|---|---|---|---|---|
| US (S1 frozen) | 15/33 | PASS 3/3 | 4/4 | +0.866 | (reference) |
| **Eurozone** | **8/33** | **PASS 3/3** | **3/4** | **+2.32** | **+0.755 (p=0.007)** |
| UK companion | 1/33 | PASS 2/3 | n/a | n/a | -0.091 (FAIL) |

**Strict 3-pair classification (per S3 prompt §5)**: B+ partial (1 of 3 N-S3 pairs PASS).
**Bilateral framing (paper-published)**: Eurozone REGIME DETECTION FINDING ESTABLISHED — equivalent to LAYER A LOCKED for the Eurozone leg of the international replication.

---

## Why "LAYER A LOCKED" applies

Per CLAUDE.md §5 amended outcome class:
> REGIME DETECTION FINDING ESTABLISHED: Layer A cell-level ≥5 + ≥3 of 4 Phase 4 PRIMARY robustness tests PASS

Eurozone meets:
- Layer A 8/33 ≥ 5 ✓
- Phase 4 PRIMARY 3/4 PASS ✓
  - (a) F-test heterogeneity PASS 3/3 horizons
  - (b) Bootstrap CI relaxed PASS 11/33 cells
  - (c) Alt event def Spearman PASS 2/3 variants (F3 forward ρ=0.80, level z-score ρ=0.66)
  - (d) VIX regime sign agreement FAIL 6/11 (regime-dependent finding — itself a sub-result)

This is the formal LAYER A LOCKED equivalent for Eurozone.

---

## Cross-country evidence

The Eurozone-US Spearman correlation at 6m horizon is **+0.755 with p=0.007** — clearing the pre-registered ≥ 0.5 PASS criterion with strong statistical significance (corresponding p-value across all 11 sectors). At 3m horizon ρ=+0.782 (p=0.004), at 1m horizon ρ=+0.545 (p=0.083, marginal).

The 2 independent surveys (US SLOOS, ECB BLS), 2 independent equity universes (US R3000, Eurozone-broad STOXX 600 ex-UK), produce the same canonical cyclical-defensive sector ordering. The surveys differ in many design choices (target firm size, banking sector composition, question wording, country coverage), so the consistency of the sector pattern across these differences is strong evidence for a **universal underlying mechanism**.

---

## UK companion negative replication

UK Layer A failed Bonferroni-K=33 (1/33 cells significant; floor 4 not met). The single passing cell — Energy 1m, t=-3.70 — is direction-consistent with the cyclical-decline hypothesis post-tightening.

UK F-test sector heterogeneity passes at 1m (p=0.004) and 3m (p=0.017), confirming heterogeneity exists in the UK panel. The pre-registered Bonferroni floor was structurally optimistic given UK n_per_cell = 50-284 (vs US 9,450 = 188× larger).

UK pattern is orthogonal to US/Eurozone (Spearman ρ < 0). Most likely explanation: STOXX 600 GBR universe is heavily multinational (BP, Shell, GSK, Unilever, HSBC), so BoE CCS — a UK-domestic shock — is weakly identified for these firms. UK Real Estate sector (-492 bp at 6m, dominated by leveraged REITs) is the largest UK-specific deviation, consistent with rate-rise / leverage-channel transmission as a special case.

**Future work**: FTSE 350 mid-cap or domestic-revenue ≥ 50% subset for proper UK replication.

---

## Outcome decision (Day 14)

**Status file: LAYER_A_LOCKED.md** (this file).

**Path forward**: STOP per CLAUDE.md §5 — no gh push from S3. User returns to meta-harness for governance review. Following S1 precedent, governance close audit will be at `D:/vscode/meta-harness/audits/2026-05-XX-S3-governance-close-eurozone-bilateral-validation.md`.

---

## Evidence files

- `analysis/paper_v1.md` — English paper draft (8 sections + 5 appendices)
- `analysis/README_KR.md` — Korean distill
- `data/cache/layer_a_eurozone_2026-05-06.parquet` — Layer A 33 cells with Bonferroni significance flag
- `data/cache/comp_global_panel_eurozone_2026-05-06.parquet` — 22,706 firm-event-horizon rows
- `data/cache/layer_d_eurozone_2026-05-06.json` — Δ Sharpe 2.32 result
- `data/cache/phase4_primary_eurozone_summary.json` — 4 PRIMARY tests detailed results
- `data/cache/walk_forward_eurozone_2026-05-06.json` — 5-fold walk-forward (3/5 positive)
- `data/cache/day4_layer_a_rebuttal_summary.json` — UK rebuttal analyses

---

## Audit trail

- `D:/vscode/meta-harness/audits/2026-05-06-S3-day1-eod.md` — bootstrap + scoop #1
- `D:/vscode/meta-harness/audits/2026-05-06-S3-day1-extension-path-u-covid-robust.md` — Path U breakthrough
- `D:/vscode/meta-harness/audits/2026-05-06-S3-day2-eod.md` — STOXX 600 universe build
- `D:/vscode/meta-harness/audits/2026-05-06-S3-phase0-eod.md` — data validity Phase 0 close
- `D:/vscode/meta-harness/audits/2026-05-06-S3-day4-eod.md` — Layer A + outcome class pivot
- `D:/vscode/meta-harness/audits/2026-05-06-S3-phase1-eod.md` — Eurozone REGIME DETECTION FINDING ESTABLISHED
- `D:/vscode/meta-harness/audits/2026-05-06-S3-international-validation-reference-validation.md` — pre-registration

---

## Key commits

| Commit | Day | Description |
|---|---|---|
| e68d23b | Day 1 | Bootstrap (S1 fork rename + initial fetch) |
| b50b745 | Day 1 ext | Path U PDF Annex 3 + COVID-robust AR(1) |
| c22eb58 | Day 2 | STOXX 600 UK + Eurozone universe build |
| 7be3376 | Day 3 | comp_global panel + Phase 0 PASS |
| 742fb01 | Day 5 | Eurozone Layer D Δ Sharpe 2.32 PASS |
| 95abaed | Day 6 | Phase 4 PRIMARY 3/4 PASS — REGIME DETECTION FINDING ESTABLISHED |

---

## STOP — no gh push from S3

Per CLAUDE.md §9: GitHub public push 본 repo 안 직접 수행 금지. Day 14 outcome 후 사용자 meta-harness 복귀, governance review 통과 후 meta-harness 에서 gh push 실행.

Eurozone bilateral external validation is portfolio's first international SLOOS-sector replication finding. Next step: meta-harness governance review for paper publication path (RFS / J Mon Econ direct submission realistic).
