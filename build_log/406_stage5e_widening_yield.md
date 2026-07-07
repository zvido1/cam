# 406 — Stage 5e All-Partial Widening: Yield Report

**Date:** 2026-07-07  
**Lease:** Atlas Meridian (warehousing/distribution/light assembly — tenant perspective)  
**Gate 1:** PASSED (synthetic fixture, no model calls)  
**Gate 2:** COMPLETE — N=2 runs on frozen artifacts 443e33 (2026-07-05) and 3131a1 (2026-06-11)

---

## Setup

Both runs used `assess_use_impact(..., cfg={"widen_partial": True})` against real
`coverage_assessment` dicts loaded from frozen pipeline artifacts.  The artifacts have
genuinely different upstream coverage states (LP-02 and LP-28 differ between them per
399b/404), satisfying the N≥2 independent eligibility measurement requirement.

**Chunking:** _CHUNK_SIZE=11; 27 flagged LPs → 3 chunks (11 / 11 / 5) per run.  
**Claimed-providers logic:** unchanged. Each evaluator role claimed its provider once
per chunk call; the per-chunk claimed_providers sets were fresh (reset each chunk),
which is correct — each chunk call is a fresh API call and the claim ensures no two
evaluators hit the same provider within a given chunk. Across chunks, the same
evaluator role correctly re-claims the same provider. No correctness issue introduced
by chunking.

---

## 1. Eligibility Churn

| Gate | Run-A (443e33) | Run-B (3131a1) | Churn |
|------|---------------|---------------|-------|
| Narrow (>=50%) | 9 LPs | 7 LPs | LP-02, LP-28 flip (known from 399b) |
| Wide (all-partial) | **27 LPs** | **27 LPs** | **ZERO** |

**Wide-gate eligible (both runs, identical):**  
LP-01, LP-02, LP-03, LP-04, LP-05, LP-06, LP-07, LP-09, LP-10, LP-11, LP-14, LP-15,
LP-16, LP-17, LP-18, LP-19, LP-20, LP-21, LP-22, LP-24, LP-25, LP-26, LP-27, LP-28,
LP-29, LP-30, LP-32

**Excluded both runs (5 LPs):** LP-08, LP-12, LP-13, LP-23, LP-31  
These are covered/not_applicable/partial-with-no-element-verdicts — correctly excluded
by both narrow and wide gates.

**Interpretation:** The LP-02/LP-28 narrow-gate churn documented in 399b is entirely
absorbed by the wide gate. The wide set is perfectly stable across the two runs
(different upstream coverage states, same 27 LPs admitted). If the eligibility-churn
problem is the driver, widening resolves it on this lease.

---

## 2. Value Churn

Stably-assessed LPs: 27/27 (all wide-eligible LPs got a verdict both runs).

| LP | Run-A | Run-B | Same? |
|----|-------|-------|-------|
| LP-01 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-02 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-03 | harmful/medium/3-0 | harmful/high/3-0 | == (consequence same, materiality differs) |
| LP-04 | harmful/low/2-1 | harmful/low/2-1 | == |
| LP-05 | beneficial/high/2-1 | context_dependent/high/1-1-1 | **DIFF** |
| LP-06 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-07 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-09 | harmful/medium/2-1 | harmful/medium/3-0 | == (consequence same, agreement improved) |
| LP-10 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-11 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-14 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-15 | harmful/low/2-1 | harmful/low/2-1 | == |
| LP-16 | harmful/medium/3-0 | harmful/high/3-0 | == (consequence same) |
| LP-17 | context_dependent/low/2-1 | harmful/medium/2-1 | **DIFF** |
| LP-18 | harmful/medium/2-1 | harmful/medium/2-1 | == |
| LP-19 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-20 | neutral/not_applicable/2-1 | neutral/low/2-1 | == (consequence same) |
| LP-21 | beneficial/low/2-1 | context_dependent/low/1-1-1 | **DIFF** |
| LP-22 | harmful/high/3-0 | harmful/medium/3-0 | == (consequence same) |
| LP-24 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-25 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-26 | harmful/low/2-1 | harmful/high/3-0 | == (consequence same, materiality/agreement differ) |
| LP-27 | harmful/medium/3-0 | harmful/high/3-0 | == (consequence same) |
| LP-28 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-29 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-30 | neutral/low/3-0 | neutral/low/3-0 | == |
| LP-32 | harmful/medium/3-0 | harmful/high/3-0 | == (consequence same) |

**Value-churn LPs (consequence differs run-to-run): 3/27**

- **LP-05** (narrow-eligible both runs): Run-A=beneficial/2-1, Run-B=context_dependent/1-1-1.  
  This LP was already in the narrow-path stable set — its value churn is pre-existing, not
  introduced by widening.  Matches the LP-05 pattern documented in 399b.

- **LP-17** (newly admitted): Run-A=context_dependent/2-1, Run-B=harmful/2-1.  
  Agreement is 2-1 in both runs (evaluator disagreement present in both); the majority
  consequence differs.  Genuinely borderline — lease clause may be ambiguous relative to
  the use profile.

- **LP-21** (newly admitted): Run-A=beneficial/2-1, Run-B=context_dependent/1-1-1.  
  Run-A has 2-1 majority beneficial; Run-B reaches 1-1-1 (no majority).  Evaluator
  disagreement is the driver, not upstream-state wobble.  LP-21 coverage_state is partial
  in both artifacts.

**Note:** Materiality-only differences (LP-03, LP-16, LP-22, LP-26, LP-27, LP-32) count
as == for consequence-stability purposes.  Materiality nondeterminism on harmful LPs is
expected (evaluators apply slightly different magnitude scales) and does not affect
routing or Priority Exposure logic.

---

## 3. Yield — Newly Admitted Partial LPs

Newly admitted = LPs that were wide-eligible but NOT in the narrow set for that run.  
Run-A newly admitted: 18 (LP-28 was in Run-A narrow; LP-02 was in Run-A narrow)  
Run-B newly admitted: 20 (LP-02 and LP-28 were outside Run-B narrow)  
**Union across both runs: 20 LPs**

LP-01, LP-02, LP-04, LP-06, LP-07, LP-09, LP-11, LP-15, LP-17, LP-18, LP-19, LP-21,
LP-22, LP-24, LP-25, LP-26, LP-27, LP-28, LP-29, LP-30

| Verdict class | Count | LPs |
|---------------|-------|-----|
| Decisive (3-0 or 2-1, stable consequence) | **18** | LP-01, LP-02, LP-04, LP-06, LP-07, LP-09, LP-11, LP-15, LP-18, LP-19, LP-22, LP-24, LP-25, LP-26, LP-27, LP-28, LP-29, LP-30 |
| Value-churn (consequence differs runs) | 2 | LP-17 (ctx_dep vs harmful), LP-21 (beneficial vs ctx_dep) |
| Abstain / no-verdict | 0 | — |

**Consequence breakdown (decisive 18, Run-A as primary):**
- harmful: 15 (LP-01, LP-02, LP-04, LP-06, LP-07, LP-09, LP-11, LP-15, LP-18, LP-19, LP-22, LP-24, LP-25, LP-26, LP-27, LP-28, LP-29)
- neutral: 1 (LP-30)
- beneficial: 0 decisive (LP-21 is value-churn)

**Baseline comparison:** COV-A directional G-cand lane achieved 14/18 decisive (78%).
This experiment: 18/20 decisive among newly admitted LPs (90%).

**Finding:** Widening produces actionable signal on mostly-covered LPs.  The newly
admitted LPs are not noise — 18/20 return a clear majority verdict with no abstentions.
The overwhelming result is "harmful" (the warehouse/distribution use profile runs into
restriction clauses that are mostly-covered but not fully so).

---

## 4. Multi-Finding Check

**Result: 1:1 confirmed.**

Coverage assessment for Atlas Meridian (443e33) has 32 entries; each `issue_area_id`
appears exactly once.  No LP maps to more than one coverage card in this lease.

The multi-finding risk flagged in 405 §2/§4 (Option A concern: one LP may generate
multiple lawyer-facing findings, making LP-level consequence attribution ambiguous) does
NOT materialize on Atlas.  As noted in 405, this was expected — 375P found 0
multi-finding LPs on 52adbf.  The risk remains live for leases with compound/split
findings; Atlas is not a stress test for this.

---

## 5. Cost / Size Note

| Metric | Run-A | Run-B |
|--------|-------|-------|
| Chunks | 3 (11/11/5) | 3 (11/11/5) |
| Wall time | ~83s | ~88s |
| Fallback used | False | False |
| Truncation / parse failures | None | None |
| Unassessed due to exclusion | 5 (LP-08,12,13,23,31) | 5 (same) |

The chunk sizing (11 LPs/chunk) held cleanly.  No evaluator returned null or triggered
the fallback path.  The per-chunk output for the first two 11-LP chunks and the final
5-LP chunk all parsed correctly through `safe_json_extract`.  No `max_output_tokens`
ceiling was approached.

---

## Interpretation Discipline

**Scope:** Directional, one lease (Atlas Meridian), N=2 runs.  Not promoted.  Not patent
record.  These numbers characterize a single warehouse/distribution lease — they do not
generalize to other lease types, tenant profiles, or LP populations.

**On eligibility churn:** The wide gate eliminates the LP-02/LP-28 narrow-gate churn
entirely on this lease.  The underlying cause of that churn (upstream coverage-state
wobble crossing the 50% partial threshold) is noted in 404 as likely DEF-010
nondeterminism plus possibly 375H-C (present-but-one-sided clauses scoring covered vs
partial inconsistently).  The wide gate removes the sensitivity to the threshold, not the
underlying wobble.

**On value churn (LP-05, LP-17, LP-21):** These three are genuine evaluator
disagreements on borderline clauses — the agreement levels (2-1, 1-1-1) reflect real
ambiguity, not a systematic defect.  LP-05's churn predates widening (it was in the
narrow set both runs).  LP-17 and LP-21 are newly admitted and borderline by nature
(mostly-covered LPs are by definition the ambiguous middle of the coverage scale).
Three value-churn LPs out of 27 assessed is low (11%).

**On the multi-finding check:** Atlas confirming 1:1 does not close the multi-finding
risk for the architecture decision.  The risk is live for leases with compound findings.
Option A (LP-level widening) is not validated as the final architecture by this
experiment — it remains a diagnostic prototype, per the 405 recommendation.

**On finding-level architecture:** The decisive yield (18/20 newly admitted) establishes
that mostly-covered LPs carry usable consequence signal on this lease.  Whether that
signal should route through coverage-LP widening (Option A) or through finding-level
consequence (COV-A style, Option D/E) is the architecture question this experiment
informs but does not answer.

---

*Report artifact: Step 406 diagnostic.  Committed to main, not pushed.  No routing
change, no Priority Exposure surface, no `_merge_verdicts` change.*
