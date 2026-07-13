# 417 — Post-416 Stage 5 Baseline Measurement

**Date:** 2026-07-12
**Fixture:** atreca_eastjamie_southsf_lease.txt (same as Steps 407/411)
**Panel:** post-414/416 frozen stack (A=claude-sonnet-4-6 / B=gpt-5.5 / C=grok-4.3)
**N runs:** 10
**Total wall-clock:** 18117s (302.0 min)
**Config:** widen_partial=False (production default / narrow gate)

---

## Run Inventory

| Run | Run ID | Wall-clock (s) |
|-----|--------|----------------|
| 1 | lease_417_atreca_run01 | 1235.8 |
| 2 | lease_417_atreca_run02 | 1290.4 |
| 3 | lease_417_atreca_run03 | 1370.2 |
| 4 | lease_417_atreca_run04 | 1677.0 |
| 5 | lease_417_atreca_run05 | 3387.1 |
| 6 | lease_417_atreca_run06 | 1721.4 |
| 7 | lease_417_atreca_run07 | 3417.3 |
| 8 | lease_417_atreca_run08 | 1315.5 |
| 9 | lease_417_atreca_run09 | 1333.0 |
| 10 | lease_417_atreca_run10 | 1369.2 |

---

## Overall Variance Rate

- Total LPs measured: **32**
- LPs with any coverage_state change across 10 runs: **26**
- Overall wobble rate: **81.2%** (26/32)

*(Pre-416 reference: ~31% from Step 411 N=2 Atreca pair)*

---

## LP Coverage-State Frequency Table

All 32 LPs. Frequency = count/N=10 runs.

### Stable 10/10

6 LPs: LP-04, LP-12, LP-20, LP-21, LP-23, LP-31

### Boundary noise (8/2 or 9/1)

9 LPs:

**LP-02**: partial 8/10 | missing 2/10

**LP-06**: covered 8/10 | missing 2/10

**LP-08**: covered 8/10 | missing 2/10

**LP-13**: partial 8/10 | missing 2/10

**LP-16**: broken_xref 8/10 | missing 2/10

**LP-18**: covered 8/10 | missing 2/10

**LP-19**: covered_unfavorable 8/10 | missing 2/10

**LP-28**: review_needed 8/10 | missing 2/10

**LP-30**: partial 8/10 | missing 2/10


### Directional preference (7/3 or 6/4)

12 LPs:

**LP-01**: partial 6/10 | covered 2/10 | missing 2/10

**LP-03**: review_needed 6/10 | partial 2/10 | missing 2/10

**LP-07**: partial 6/10 | review_needed 2/10 | missing 2/10

**LP-09**: broken_xref 7/10 | missing 2/10 | partial 1/10

**LP-11**: partial 7/10 | missing 2/10 | review_needed 1/10

**LP-14**: review_needed 6/10 | missing 2/10 | partial 2/10

**LP-15**: covered 6/10 | missing 2/10 | partial 1/10 | review_needed 1/10

**LP-17**: partial 7/10 | missing 3/10

**LP-24**: partial 6/10 | review_needed 2/10 | missing 2/10

**LP-25**: covered 7/10 | missing 2/10 | review_needed 1/10

**LP-29**: partial 7/10 | review_needed 2/10 | covered 1/10

**LP-32**: covered_unfavorable 7/10 | missing 2/10 | review_needed 1/10


### Genuine split (≤5/10 modal state)

5 LPs:

**LP-05**: review_needed 5/10 | missing 3/10 | partial 2/10

**LP-10**: partial 4/10 | covered_unfavorable 2/10 | missing 2/10 | review_needed 2/10

**LP-22**: review_needed 4/10 | partial 4/10 | missing 2/10

**LP-26**: partial 5/10 | review_needed 3/10 | missing 2/10

**LP-27**: review_needed 5/10 | missing 4/10 | partial 1/10


### Element churn with stable final state

0 LPs where element-level verdicts flipped but coverage_state held 10/10:
none

---

## Per-Role Raw Verdict Flip Table

A 'flip' = a role's verdict on an element differed from that role's own modal verdict for that element across N runs.

| Role | Provider/Model | Config | Total element flips | LPs with any flip |
|------|----------------|--------|--------------------|--------------------|
| A | anthropic / claude-sonnet-4-6 | temperature=0 | 49 | 15 |
| B | openai / gpt-5.5 | temperature=1 (provider default; model rejects temp=0) | 63 | 15 |
| C | xai / grok-4.3 | temperature=0 | 86 | 20 |

**Share of total flips by role:**

- Role A: 49 flips (25%)
- Role B: 63 flips (32%)
- Role C: 86 flips (43%)

**LPs each role flipped on:**

- Role A: ['LP-01', 'LP-02', 'LP-03', 'LP-05', 'LP-06', 'LP-07', 'LP-11', 'LP-14', 'LP-15', 'LP-17', 'LP-22', 'LP-24', 'LP-25', 'LP-26', 'LP-27']
- Role B: ['LP-01', 'LP-02', 'LP-05', 'LP-10', 'LP-11', 'LP-15', 'LP-17', 'LP-18', 'LP-19', 'LP-22', 'LP-26', 'LP-27', 'LP-28', 'LP-29', 'LP-32']
- Role C: ['LP-01', 'LP-03', 'LP-05', 'LP-06', 'LP-07', 'LP-10', 'LP-11', 'LP-13', 'LP-15', 'LP-17', 'LP-18', 'LP-19', 'LP-22', 'LP-24', 'LP-25', 'LP-27', 'LP-28', 'LP-29', 'LP-30', 'LP-32']

---

## Fallback / Config-Integrity Audit

Fallback events: **none** across 10 runs × 32 LPs. 414 integrity confirmed.

Config-integrity assertion: `_check_generation_integrity()` fires on every evaluator call.
Any FatalProviderError would have aborted the run — no aborts observed.
Role B primary (gpt-5.5) temperature: TEMPERATURE_ONLY_DEFAULT_MODELS exception fires every call (expected).

---

## Decision Standard Answers

**1. Post-414/416 irreducible wobble rate:** 81.2% (26/32 LPs showed any coverage_state variance across N=10)

**2. Comparison to pre-416 ~31% (Step 411 N=2):** +50.2% change.

**3. Boundary vs genuine split:** 9 LPs are 8/2 or 9/1 type (boundary noise); 5 are 5/5 or worse (genuine disagreement).

**4. Role B primary disproportionate?** Role B accounted for 63/198 total element flips (32%).
   Role A (temperature=0): 49 flips. Role C (temperature=0): 86 flips.
   → Role B is NOT disproportionate. Roles A/C also produce meaningful temperature=0 variance. Shadow diagnostic is less decisive.

**5. Temperature=0 same-model variance (Role A + C):** 135 flips from Roles A and C combined.

**6. Stabilization framing:** boundary/hysteresis (most churn is 9/1 or 8/2 type boundary noise)

---

*Step 417 baseline. N=10. Frozen panel post-414/416. No push.*