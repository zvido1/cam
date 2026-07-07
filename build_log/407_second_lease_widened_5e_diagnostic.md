# 407 — Second-Lease Widened Stage 5e Transfer Test

**Date:** 2026-07-07  
**Fixture:** Atreca, Inc. — 450 East Jamie Court, South San Francisco, CA  
**EDGAR exhibit:** EX-10.18 (accession 0001104659-19-041460)  
**Property type:** Lab/office (CA jurisdiction)  
**Work scope:** Populated (Exhibit C = Landlord's Work — private offices per attached plan)  
**Full pipeline runs:** N=2, each ~23 min, no push, no routing change  
**Based on:** 406 widening (`8b9ed5d`), 405 design (`9341b9a`)

---

## 1. Executive Summary

The widened Stage 5e gate transfers cleanly to a second lease of a different property type.
Atreca EX-10.18 (lab/office) produced 19/32 wide-eligible LPs across two independent full
pipeline runs, identical both runs (zero eligibility churn). Consequence verdicts were stable
across all 19 assessed LPs (zero value churn), and 8/8 newly-admitted partial LPs returned
decisive verdicts (100%, all harmful except LP-30 neutral). No truncation, no fallback, no
parse errors.

The multi-finding-per-LP stress check produced the first real finding of this diagnostic arc:
on Atreca EX-10.18, LP-01, LP-11, and LP-27 each appear in multiple Stage 7 compound findings
(CRX-01 through CRX-06) representing cross-provision risk patterns. These 6 compound findings
are marked `not_assessed` in the Stage 5e-F finding-level consequence layer — a per-LP
`use_impact` verdict for LP-01 (harmful) does not capture, and cannot capture, the compound
risk that LP-01 + LP-11 + LP-27 together form. This is NOT the coverage-card 1:1 question
(which remains confirmed 1:1) — it is the finding-level consequence gap that 405 §4 identified
as the live risk for Option A, and this lease tests it.

---

## 2. Fixture Chosen and Rationale

**Chosen:** `atreca_eastjamie_southsf_lease.txt` — Atreca, Inc. EX-10.18, 450 East Jamie
Court, South San Francisco, CA. Effective 2019-07-17. Landlord: ARE-East Jamie Court, LLC
(Alexandria Real Estate Equities). CA governing law.

**Why EX-10.18:**
- Full executed lease (not a work letter exhibit or partial document) — runnable through Mode C.
- Property type: lab/office — vs Atlas Meridian's warehouse/industrial — a genuine cross-type
  transfer test.
- Work scope: populated (Landlord constructs private offices per Exhibit C plan) — tests
  LP-10 (Alterations & Improvements) and related TI provisions specifically.
- Named in the record (CAM_Current_State.md) as the sharper of the Atreca pair for the
  landlord-work contrast; the EX-10.19 companion (to-be-constructed shell) is also in the
  corpus but uses a Work Letter / TI Allowance structure rather than direct Landlord's Work.
- CA jurisdiction — same jurisdiction family as Atlas (CA-governed) but different city and
  landlord structure.

**BOKF rejected:** BOKF Oklahoma Tower is a work letter exhibit with `[INTENTIONALLY DELETED]`
TI schedules — not a full executed lease and not a valid Mode C input for a widening
comparison.

---

## 3. Eligibility Yield vs Atlas 406

| Metric | Atlas 406 | Atreca 407 |
|--------|-----------|------------|
| Total LPs in scope | 32 | 32 |
| Narrow eligible (Run-A) | 9 | 12 |
| Narrow eligible (Run-B) | 7 | 12 |
| Wide eligible (Run-A) | 27 | 19 |
| Wide eligible (Run-B) | 27 | 19 |
| Wide gate churn | 0 | 0 |
| Newly admitted (union) | 20 | 8 |
| Excluded (wide gate) | 5 | 13 |

**Wide-eligible set (both runs, identical):**  
LP-01, LP-02, LP-03, LP-05, LP-07, LP-10, LP-11, LP-13, LP-14, LP-17, LP-20, LP-21, LP-22,
LP-24, LP-26, LP-27, LP-28, LP-29, LP-30

**Narrow-eligible (Run-A):** LP-01, LP-03, LP-05, LP-10, LP-14, LP-17, LP-20, LP-21, LP-22,
LP-26, LP-27, LP-28 — 12 LPs  
**Narrow-eligible (Run-B):** LP-01, LP-02, LP-03, LP-05, LP-14, LP-17, LP-20, LP-21, LP-22,
LP-26, LP-27, LP-28 — 12 LPs  
**Narrow churn (Run-A vs Run-B):** LP-10 in Run-A only (partial in A, different state in B);
LP-02 in Run-B only (review_needed in B, partial in A). Wide gate absorbs both.

**Excluded both runs (13 LPs):**  
LP-04, LP-06, LP-08, LP-09, LP-12, LP-15, LP-16, LP-18, LP-19, LP-23, LP-25, LP-31, LP-32  
Reason: covered (5), not_applicable (4), broken_xref (2), covered_unfavorable (2). All
excluded by the wide gate for the correct reason (the gate excludes these states; widening
only affects `partial` LPs).

**Coverage state distribution (Run-A):**  
partial=10, review_needed=6, missing=3, covered=5, not_applicable=4, covered_unfavorable=2,
broken_xref=2

**Why fewer wide-eligible vs Atlas (19 vs 27):**  
Atlas is a warehouse/industrial lease with high partial coverage across the board (23/32
partial). Atreca is a lab/office lease with a more varied coverage profile — 5 LPs fully
covered, 4 not_applicable (likely retail/co-tenancy provisions not relevant to lab use), and
4-6 missing. Fewer partial LPs → smaller wide set. This is lease-specific, not a defect.

---

## 4. Decisive / Abstain / Context-Dependent Distribution

**Both runs (N=19 assessed):**

| Consequence | Count | LPs |
|-------------|-------|-----|
| harmful | 16 | LP-01, LP-02, LP-03, LP-05, LP-07, LP-10, LP-11, LP-13, LP-14, LP-17, LP-22, LP-24, LP-26, LP-27, LP-28, LP-29 |
| neutral | 2 | LP-20, LP-30 |
| beneficial | 1 | LP-21 |
| context_dependent | 0 | — |

**Agreement distribution:**  
- 3-0 (assert): 15 LPs — LP-01, LP-02, LP-03, LP-05 (one run 2-1), LP-07 (one run 2-1), LP-10, LP-13, LP-14, LP-20 (one run 2-1), LP-21, LP-22, LP-24, LP-26 (one run 3-0), LP-27, LP-28, LP-29, LP-30  
- 2-1 (assert_weak): 4 LPs — LP-11, LP-17, and agreement level varies across runs for LP-05/LP-07/LP-20

No LP reached context_dependent or abstain on either run. This is stronger than Atlas
(which had LP-17 and LP-21 reach context_dependent on one run each).

**Use profile (both runs):** "Research and development laboratory with related office uses,"
tenant perspective. Inferred from the permitted use clause and building description. Consistent
between runs.

---

## 5. Run-to-Run Stability (Value Churn)

**Value churn (consequence-level):** 0/19 — ZERO mismatches.

Every one of the 19 assessed LPs returned the same consequence classification in both runs.
Materiality nondeterminism is present (e.g. LP-02: medium/high; LP-26: medium/high; LP-21:
medium/low) but consequence direction is perfectly stable.

| LP | Run-A | Run-B | Same? |
|----|-------|-------|-------|
| LP-01 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-02 | harmful/medium/3-0 | harmful/high/3-0 | == |
| LP-03 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-05 | harmful/high/2-1 | harmful/high/3-0 | == |
| LP-07 | harmful/medium/3-0 | harmful/low/2-1 | == |
| LP-10 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-11 | harmful/low/2-1 | harmful/low/2-1 | == |
| LP-13 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-14 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-17 | harmful/medium/3-0 | harmful/medium/2-1 | == |
| LP-20 | neutral/low/2-1 | neutral/low/3-0 | == |
| LP-21 | beneficial/medium/3-0 | beneficial/low/3-0 | == |
| LP-22 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-24 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-26 | harmful/medium/3-0 | harmful/high/3-0 | == |
| LP-27 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-28 | harmful/high/3-0 | harmful/high/3-0 | == |
| LP-29 | harmful/medium/3-0 | harmful/medium/3-0 | == |
| LP-30 | neutral/low/3-0 | neutral/low/3-0 | == |

This is a substantially cleaner result than Atlas (which had 3/27 value-churn LPs: LP-05,
LP-17, LP-21). Possible explanations: (a) the Atreca lease has clearer clause language
leaving less room for evaluator disagreement; (b) the use profile (R&D lab) interacts more
unambiguously with most LP categories than a warehouse/distribution use.

---

## 6. Newly-Admitted LP Yield

Newly admitted = wide-eligible but outside the narrow (>=50%) gate for at least one run.

**Run-A newly admitted (7):** LP-02, LP-07, LP-11, LP-13, LP-24, LP-29, LP-30  
**Run-B newly admitted (7):** LP-07, LP-10, LP-11, LP-13, LP-24, LP-29, LP-30  
**Union (8):** LP-02, LP-07, LP-10, LP-11, LP-13, LP-24, LP-29, LP-30

| LP | Consequence | Agreement | Notes |
|----|-------------|-----------|-------|
| LP-02 | harmful | 3-0 both runs | Newly admitted in Run-A only (review_needed in B → narrow) |
| LP-07 | harmful | 3-0 / 2-1 | CAM charges — mostly-covered but still harmful |
| LP-10 | harmful | 3-0 both runs | Newly admitted in Run-B only (review_needed in A → narrow) |
| LP-11 | harmful | 2-1 both runs | Default & Remedies — weak majority harmful |
| LP-13 | harmful | 3-0 both runs | Indemnification — strong harmful signal |
| LP-24 | harmful | 3-0 both runs | Damage & Destruction — clear signal |
| LP-29 | harmful | 3-0 both runs | Landlord Access — clear signal |
| LP-30 | neutral | 3-0 both runs | Estoppel Certificate — neutral/not-material for this use |

**Yield: 8/8 decisive (100%), 0 context_dependent, 0 abstain.**

Comparison: Atlas 406 achieved 18/20 decisive (90%). Atreca 407 achieves 8/8 (100%). Both
leases show that widening produces actionable signal on mostly-covered partial LPs, not noise.

**Consequence direction:** 7/8 harmful, 1/8 neutral (LP-30). No beneficial among newly-admitted.
For a lab/office tenant, the mostly-covered-but-partial LPs are almost uniformly reading as
harmful — the partial coverage doesn't protect. This contrasts with the narrow set where LP-21
(beneficial) was always eligible.

---

## 7. Token / Chunk / Parser Behavior

| Metric | Run-A | Run-B |
|--------|-------|-------|
| Pipeline runtime (full Mode C) | ~1392s (~23 min) | ~1383s (~23 min) |
| Total API calls | 86 | 88 |
| Stage 5e chunks | 2 (11 + 8) | 2 (11 + 8) |
| Stage 5e fallback | False | False |
| Stage 5e truncation | None | None |
| Stage 5e parse errors | None | None |
| use_impact_meta | Not stored in pipeline_results | Not stored in pipeline_results |

**Chunking note:** 19 LPs wide → 2 chunks (11 + 8), both well under max_output_tokens=3000.
No truncation event occurred. The 406 chunk sizing (<=11) scales correctly to the smaller
Atreca eligible set.

**use_impact_meta not in pipeline_results:** The `run_lease_coverage_only` pipeline stores
`use_impact_governance` rather than `use_impact_meta` as the top-level field. The harness
captured Stage 5e complete/chunk count from console output. This is a field-name mismatch in
the harness, not a pipeline defect — Stage 5e ran and completed normally as confirmed by the
log lines.

---

## 8. Multi-Finding-per-LP Stress Result

### Coverage-card structure (1:1 confirmed)

The `coverage_assessment` list contains exactly 32 entries, one per LP, with no duplicate
`issue_area_id`. On Atreca EX-10.18, as on Atlas, the coverage card layer is 1:1: each LP
has one coverage card and one `use_impact` verdict. This is confirmed both runs.

### Stage 7 compound findings — the actual multi-finding structure

Stage 7 synthesis produced 6 compound findings (CRX-01 through CRX-06) across both runs,
each spanning MULTIPLE LPs:

| Compound finding | Pattern | LPs involved |
|-----------------|---------|--------------|
| CRX-01 | One-sided enforcement machinery | LP-01, LP-11, LP-27 |
| CRX-02 | Rights without enforcement levers | LP-01, LP-11, LP-17, LP-27 |
| CRX-03 | Dead-end impairment structure | LP-01, LP-14, LP-24, LP-27, LP-29 |
| CRX-04 | Full rent during operational shutdown | LP-14, LP-19, LP-24, LP-27, LP-29 |
| CRX-05 | One-sided termination rights | LP-11, LP-27 |
| CRX-06 | Conditional non-disturbance trap | LP-22, LP-26 (or LP-22, LP-27) |

LP-01, LP-11, LP-27 each appear in 3+ compound findings. LP-14, LP-24, LP-29 each appear
in 2+ compound findings.

### Does per-LP use_impact mislead on compound findings?

**YES, for a specific reason:** The `lease_finding_consequence` log reports:

```
G-cand lane: 19 directional finding(s) → 19 already-assessed (copy), 0 unassessed (new 5e),
             6 compound (not_assessed)
```

The 6 compound findings are `not_assessed` for use_impact. The Stage 5e widening correctly
assessed LP-01 as harmful and LP-27 as harmful at the coverage-LP level. However, a compound
finding like CRX-01 ("One-sided enforcement machinery — LP-01 + LP-11 + LP-27") is a distinct
legal risk pattern that cannot be represented as the consequence of LP-01 alone, LP-11 alone,
or LP-27 alone. The compound risk exists precisely BECAUSE of how these three provisions
interact. A per-LP use_impact verdict for LP-27 ("harmful") is correct at the LP level but
does not capture the compound consequence.

If a lease had a CRX-01-type compound risk where the individual LP verdicts were all "harmful"
but the compound interaction produced a catastrophic structural defect (or, conversely, if two
"harmful" LPs offset each other through a cross-provision mechanism), the per-LP use_impact
would miss it in both directions.

On Atreca EX-10.18, all individual LP verdicts happen to be aligned with the compound risk
direction (all harmful → compound risk also adverse for tenant), so there is no specific
misleading case to point to. But this alignment is lease-specific, not architectural.

### Is the multi-finding-per-LP caveat TESTED or UNTESTED?

**The coverage-card 1:1 question: UNTESTED (still).**  
The question 405 §4 raised was whether a single LP provision generates MULTIPLE lawyer-facing
COVERAGE CARDS (i.e. two rows in `coverage_assessment` for the same LP-xx). This did not
occur on either Atlas or Atreca. Two clean leases confirming 1:1 is absence of evidence, not
evidence of absence. A lease with a compound/split clause (where one physical section of text
addresses two distinct LP obligations) could produce multi-card LPs. The test has not been run.

**The compound-finding layer gap: OBSERVED AND LIVE.**  
The compound findings are a real output of the pipeline (Stage 7) that use_impact currently
does not assess. This gap exists now on both Atlas and Atreca. The 6 `not_assessed` compound
findings on Atreca are the strongest evidence in this diagnostic arc that widening the LP-level
gate (Option A) does not, by itself, address the compound-risk consequence question. Finding-
level consequence architecture (Option D/E) is required to assess cross-provision patterns.

---

## 9. Does Option A Have Transfer Evidence Toward Default?

**Transfer evidence status:**

Option A (widen the LP-level gate) now has clean signal from two leases of different property
types (warehouse/industrial + lab/office) and two runs per lease:
- Eligibility churn eliminated (0/0 across 4 runs)
- Value churn low (Atlas: 3/27 on stably-eligible LPs; Atreca: 0/19)
- Yield decisive on newly-admitted (Atlas: 18/20 = 90%; Atreca: 8/8 = 100%)
- No parser/truncation/fallback events across 4 runs

This is positive transfer evidence. The gate produces actionable signal on both leases.

**Does this warrant flipping the default?** No. The evidence is:
- Two leases, N=2 per lease, same Atreca fixture both Atreca runs
- No multi-finding-LP stress test (still absence of evidence)
- Compound findings not assessed under either Option A or the narrow gate
- The compound-finding gap is independent of whether the LP gate is wide or narrow

The 405 recommendation stands: Option A remains authorized as a controlled diagnostic
prototype, not as the final architecture. The transfer evidence strengthens the diagnostic
case but does not close the open architectural questions.

---

## 10. Finding-Level Consequence and Priority Exposure

**Finding-level consequence remains required for Priority Exposure.**

The compound findings on Atreca EX-10.18 directly illustrate why. A Priority Exposure surface
that ranks tenant risk should include compound patterns like "One-sided enforcement machinery"
(LP-01 + LP-11 + LP-27). These compound findings:
- Are high-confidence (3/3 evaluators agreed on CRX-01 in both runs)
- Are distinct from and more severe than any individual LP's consequence
- Cannot be derived from LP-level use_impact verdicts even if widened

Stage 5e widening gives every partial LP a consequence verdict. That is useful for
LP-level coverage cards. It does not give compound findings a consequence verdict — those
remain `not_assessed` in the current architecture.

**Recommendation:**
- Widen gate (`_WIDEN_PARTIAL_ELIGIBILITY`) remains default-off. 407 confirms the gate
  produces good signal but does not close the architectural gap that prevents promotion.
- The compound-finding `not_assessed` gap should be the next design decision point: does
  the COV-A finding-level architecture (Option D/E) extend to compound findings, or does
  compound consequence require a separate lane?
- Do NOT promote Option A as the final architecture based on this diagnostic. Two clean
  leases with 0 multi-card LP events is not multi-finding validation.

---

## Interpretation Discipline

**Scope:** Directional, two leases (Atlas + Atreca), N=2 per lease, four independent runs
total. NOT promoted. NOT patent record. Not a production validation.

**On transfer:** Atlas and Atreca are both CA-governed tenant-perspective reviews. Transfer
to other jurisdictions, landlord perspectives, or NNN/retail lease types is untested.

**On compound findings:** The `not_assessed` compound finding gap was not introduced by
widening — it exists in the narrow gate too. The 406 run logged the same pattern. Widening
does not make it worse; it just doesn't fix it.

**On the multi-finding caveat:** The caveat from 405 §4 (one LP → two lawyer-facing cards
with different consequence directions) has NOT appeared in two leases. It remains a live
architectural concern, not a resolved one. Do not cite "two clean leases" as validation.

---

*Report artifact: Step 407 diagnostic.  
Harness: `build_log/run_407_gate2.py`. Committed to main, not pushed.  
No routing change, no default flip, no cam/core/ change, no _merge_verdicts change.*
