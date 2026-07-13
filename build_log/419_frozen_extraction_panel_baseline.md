# 419 — Frozen-Extraction Panel Variance Baseline

**Date:** 2026-07-13
**Fixture:** atreca_eastjamie_southsf_lease.txt
**Frozen extraction:** lease_418c_run01 (payload_hash: ab80aafe9f7bce07c5c6113ceb5cd06d...)
**Panel:** post-414/416 (A=claude-sonnet-4-6 / B=gpt-5.5 / C=grok-4.3)
**N runs:** 10
**Total wall-clock:** 8295s (138.2 min)

---

## Run Inventory

| Run | Elapsed (s) |
|-----|-------------|
| 1 | 771.7 |
| 2 | 716.3 |
| 3 | 879.0 |
| 4 | 830.1 |
| 5 | 823.6 |
| 6 | 941.3 |
| 7 | 839.6 |
| 8 | 873.6 |
| 9 | 788.9 |
| 10 | 830.7 |

---

## Overall Variance Rate

- Total LPs measured: **32**
- Stable LPs (10/10 same coverage_state): **18**
- Unstable LPs (any run differs): **14**
- Frozen-input wobble rate: **43.8%** (14/32)

*(417 end-to-end wobble rate reference: 81.2% — included extraction variance)*

---

## LP Coverage-State Frequency Table

### Stable 10/10

18 LPs: LP-01, LP-02, LP-04, LP-06, LP-08, LP-11, LP-12, LP-13, LP-18, LP-19, LP-20, LP-21, LP-23, LP-24, LP-29, LP-30, LP-31, LP-32

### Boundary noise (8/2 or 9/1) — 8 LPs

**LP-03**: review_needed 9/10 | partial 1/10

**LP-05**: review_needed 9/10 | missing 1/10

**LP-07**: partial 8/10 | review_needed 2/10

**LP-09**: covered 8/10 | partial 2/10

**LP-10**: partial 8/10 | review_needed 2/10

**LP-16**: review_needed 8/10 | partial 2/10

**LP-25**: covered 9/10 | partial 1/10

**LP-28**: partial 9/10 | missing 1/10

### Directional preference (6/4 or 7/3) — 5 LPs

**LP-14**: missing 7/10 | partial 3/10

**LP-15**: partial 6/10 | covered 4/10

**LP-17**: partial 7/10 | review_needed 3/10

**LP-26**: partial 6/10 | review_needed 2/10 | covered 2/10

**LP-27**: partial 7/10 | review_needed 3/10

### Genuine split (≤5/10 modal) — 1 LPs

**LP-22**: partial 5/10 | review_needed 5/10

---

## Per-Role Flip Counts

A 'flip' = a role's verdict on an element differed from that role's modal verdict for that element across N runs.

| Role | Provider/Model | Total element flips | Share |
|------|----------------|--------------------:|------:|
| A | anthropic / claude-sonnet-4-6 | 43 | 21.7% |
| B | openai / gpt-5.5 | 58 | 29.3% |
| C | xai / grok-4.3 | 97 | 49.0% |

**Total element flips:** 198

---

## Fallback / Config-Integrity Audit

Fallback events: **0** across 10 runs.
No fallback events. 414 integrity confirmed.

---

## Answers to 419 Questions

**1. True panel variance (frozen input):** 43.8% wobble rate (14/32 LPs)

**2. How much of 417's 81.2% survives extraction freezing:** 43.8% residual vs 81.2% end-to-end.
   Extraction-driven variance: ~37.4pp of the original 81.2%.

**3. Is Role C still 43% of flips with frozen input?**
   Role C: 97 flips (49.0%)
   Role A: 43 flips (21.7%)
   Role B: 58 flips (29.3%)

**4. Are Roles A and C producing same-model temperature=0 variance?**
   Role A (claude-sonnet-4-6, temp=0): 43 flips.
   Role C (grok-4.3, temp=0): 97 flips.
   See LP table above for which elements.

**5. Residual pattern (boundary/hysteresis vs genuine disagreement):**
   Boundary noise (8/2 or 9/1): 8 LPs
   Directional (6/4 or 7/3): 5 LPs
   Genuine split (≤5/10): 1 LPs

---

## Interpretation

**The panel has substantial residual variance at fixed input.** 43.8% of LPs (14/32) show coverage-state changes across N=10 runs on byte-identical inputs. This is not negligible. The 418c finding — that extraction non-determinism explains the 417 variance — was incomplete. Extraction variance explains 12 of the 26 unstable LPs from 417 (46% by LP count, ~37pp of the 81.2% wobble rate). The remaining 14 LPs show true panel-level stochasticity that persists even when all three evaluators receive the same text every time.

**Corrected attribution for 417.** The 418c report tentatively concluded that "43% Role C element flip share previously attributed to model stochasticity is substantially (possibly predominantly) driven by variable extraction input." Step 419 refutes this. With frozen extraction, Role C's share rises to 49% (97/198 flips) rather than falling. Extraction freezing eliminated the 12 LPs whose instability was input-driven; on the 14 that remain, Role C is still the dominant contributor. The 417 figure (43%) was an underestimate of Role C's true panel-level variance share, not an overestimate. The 418c interpretation was premature — it killed the stochasticity hypothesis for LP-07 specifically (where the extraction difference was decisive) but the hypothesis is confirmed for the broader panel.

**Role C vs Role A at temperature=0.** Both roles are configured at temperature=0 and receive identical inputs. Role A (claude-sonnet-4-6) produces 43 element flips (21.7%); Role C (grok-4.3) produces 97 flips (49.0%) — 2.26× more. This is genuine intrinsic stochasticity: grok-4.3 is not deterministic at temperature=0 in this context. For comparison, Role B (gpt-5.5, running at its default temperature, nominally ~1.0) produces only 58 flips (29.3%). Role B at its default temperature produces fewer flips than Role C at temperature=0.

**Instability pattern is predominantly hysteresis, not fundamental disagreement.**
- Boundary noise (8/2 or 9/1): 8 LPs (57%) — the modal state is correct 80-90% of the time; the flip is a rare excursion.
- Directional preference (6/4 or 7/3): 5 LPs (36%) — a correct state exists, but the panel finds it only 60-70% of the time.
- Genuine split (5/5): 1 LP (7%) — LP-22 (`non_disturbance_source_is_binding`), a perfect coin-flip between `partial` and `review_needed`.

The boundary-noise category is the least clinically significant; the directional misses and the genuine split are the primary concerns for output reliability.

**LP-22 is the most vulnerable.** It cannot be resolved by extraction stabilization (the input is already frozen and it still splits 5/5). The merge logic currently picks one of two adjacent states at random. This LP will produce inconsistent results in production absent an evaluator-level fix.

**The two variance sources are separable.** Extraction variance (Gemini Stage 1) affected 12 LPs in 417; freezing extraction stabilized them completely. Panel variance (model stochasticity) affects 14 LPs; their instability persists even with frozen input. These are independent mechanisms with independent remediation paths. Extraction stabilization (caching or deterministic re-use of Stage 1 output) would eliminate the 12 extraction-driven LPs but leave the 14 panel-driven LPs unchanged.

**Revised decomposition of 417's 81.2%.**
- 12/32 LPs (37.5%) = extraction-driven only — stable with fixed input.
- 14/32 LPs (43.8%) = panel-driven — persist with fixed input.
- 6/32 LPs (18.8%) = were stable in both 417 and 419 (LP-04, LP-12, LP-20, LP-21, LP-23, LP-31).

(Note: 12 + 14 + 6 = 32. The 14 panel-driven LPs may have had additional extraction variance on top in 417, but their instability doesn't require it.)

**Annotation for 417 report.** The 417 number (81.2%) remains accurate as a description of end-to-end pipeline variance (extraction + evaluation combined). It should not be retroactively relabeled as "evaluator instability." The correct reading is: 81.2% of LPs are unstable in a full pipeline run; of that, approximately 37pp is attributable to Gemini extraction non-determinism and approximately 44pp to panel-level stochasticity.

---

*Step 419 baseline. N=10 frozen-input runs. No push.*