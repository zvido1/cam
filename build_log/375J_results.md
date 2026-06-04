# Step 375J — 375E-DIR Routing-Boundary Counterfactual Results

**Frozen run:** lease_review_20260604_033046_52adbf
**Keyless:** yes — no model calls, arithmetic over frozen artifacts only
**Stage 7 source:** `pipeline_results.json` → `cross_provision_findings` (26 directional_mismatch + 6 compound_risk)
**Materiality source:** `build_log/375I_q3_results.json` (N=10 per eligible LP)
**Current-bucket derivation:** Python port of `classifyFindingType()` (app.js:18032), synthesis mode, perspective=tenant

---

## Per-finding policy table (directional_mismatch findings only)

| Finding | LP | direction | mat dist (h/m/l) | boundary | source | cur | A | B | C | D | E | stable-B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dir-01 | LP-01 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-02 | LP-02 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-03 | LP-03 | adverse | high:9, medium:1 | adjacent_hig | assessed | risk | VARIES:needs_r | actionable_mat | actionable_mat | risk | actionable_mat | YES |
| Dir-04 | LP-04 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-05 | LP-05 | adverse | medium:10 | stable_tier | assessed | risk | needs_review | actionable_mat | actionable_mat | risk | actionable_mat | YES |
| Dir-06 | LP-06 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-07 | LP-07 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-08 | LP-10 | adverse | high:1, medium:9 | adjacent_hig | assessed | risk | VARIES:needs_r | actionable_mat | actionable_mat | risk | actionable_mat | YES |
| Dir-09 | LP-11 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-10 | LP-14 | adverse | high:1, medium:9 | adjacent_hig | assessed | risk | VARIES:needs_r | actionable_mat | actionable_mat | risk | actionable_mat | YES |
| Dir-11 | LP-15 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-12 | LP-16 | adverse | high:4, medium:6 | adjacent_hig | assessed | risk | VARIES:needs_r | actionable_mat | actionable_mat | risk | actionable_mat | YES |
| Dir-13 | LP-17 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-14 | LP-18 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-15 | LP-19 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-16 | LP-20 | adverse | low:10 | stable_tier | assessed | risk | low_materialit | low_materialit | low_materialit | low_materialit | low_materialit | YES |
| Dir-17 | LP-21 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-18 | LP-22 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-19 | LP-24 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-20 | LP-25 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-21 | LP-26 | adverse | high:2, medium:8 | adjacent_hig | assessed | risk | VARIES:needs_r | actionable_mat | actionable_mat | risk | actionable_mat | YES |
| Dir-22 | LP-27 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-23 | LP-28 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-24 | LP-29 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-25 | LP-30 | adverse | — | no_samples | not_eligible | risk | consequence_un | consequence_un | consequence_un | needs_review | consequence_un | YES |
| Dir-26 | LP-32 | adverse | high:1, medium:9 | adjacent_hig | assessed | risk | VARIES:needs_r | actionable_mat | actionable_mat | risk | actionable_mat | YES |

Policy abbreviations:
- **A** = high-only adverse-gated  |  **B** = high+medium collapse adverse-gated
- **C** = B + source-strict overlay  |  **D** = B with unassessed → needs_review
- **E** = materiality-only diagnostic control (direction ignored) — **NOT a production policy**
- cur = current bucket (classifyFindingType, 3-0 verified, all adverse → risk)

---

## Q1 — Bucket stability under high+medium collapse (Policy B)

**PASS — 0 bucket changes under Policy B across all 6 wobbling LPs.**

Wobbling LPs: LP-03, LP-10, LP-14, LP-16, LP-26, LP-32.
All have direction=adverse and materiality values in {high, medium} only.
Under Policy B, every sample maps to actionable_material_risk.
0 routing-relevant crossings across 60 sample-slots (6 LPs × 10 samples).

**Proven claim:** The high/medium boundary does not matter for action-bucket routing if Policy B is adopted.
The adjacent high↔medium wobble (6 LPs, 0 full swings) produces zero routing instability under collapse.

**Caveat:** n=1 lease, provisional-on-n=1.
All wobbling LPs are adverse; a lease with favorable-high vs favorable-medium findings
could stress the boundary differently.
This lease's one-sidedness means the adverse gate was never stressed by high-materiality
favorable findings straddling the boundary.

**Still unmeasured:** Whether the boundary matters on lease #2.
Keyed 5e stabilization is NOT needed for this lease under Policy B.

**Decision trigger:** Q1=PASS → record CANDIDATE direction:
assessed high/medium + adverse = actionable_material tier; low = lower tier; defaulted/absent = source-labeled unassessed.
Lock as a candidate design direction, provisional on n=1.

---

## Q2 — Masquerade detection (Policy C)

**No masqueraders among the 8 assessed records.
18 findings use an implicit unassessed routing floor.**

**Proven claim:** All 8 assessed records (LP-03/05/10/14/16/20/26/32) have confidence ∈ {assert, assert_weak}.
Policy C finds no assessed records that are actually floor-defaults.
However, 18 directional findings for not_eligible LPs currently route to 'risk' via the implicit
`or "moderate"` floor in `lease_adapter.py:1006+1461`, without disclosing the unassessed source.
Under Policy C/D these 18 would correctly label as consequence_unassessed.

**Caveat:** The 18 are not "masqueraders" in the fabricated-confidence sense — the artifact is honest
(those LPs have no use_impact key). The problem is silent promotion to Risk in the routing layer.

**Still unmeasured:** Whether the no_evaluators code path could produce a record that masquerades as assessed.

---

## Q3 — Findings without assessed materiality

**18/26 directional findings have source=not_eligible (no Stage 5e assessment).**

Only 8 LPs reached Stage 5e; their directional findings are Dir-03, Dir-05, Dir-08, Dir-10, Dir-12, Dir-16, Dir-21, Dir-26.
The remaining 18 have source=not_eligible (LP gated out by _should_assess).
LP-20 has assessed materiality but it is low → low_materiality tier, not actionable Risk, under all policies.
Effective count with actionable assessed materiality: 7 findings.

**Proven claim:** 7/26 directional findings have assessed medium-or-high materiality sufficient for
actionable_material_risk routing under Policy B. 18/26 have no assessed materiality at all.

**Caveat:** 18/26 is a structural gap from the 50% eligibility threshold, not an evaluation failure.
The 18 not_eligible LPs include provisions directly relevant to this warehouse tenant
(maintenance, SNDA, force majeure, CAM dispute).

**Still unmeasured:** Post-375E-COV count. Widening _should_assess could substantially increase coverage.

---

## Q4 — Policy A artificial instability

**YES — Policy A's instability is entirely an artifact of the high/medium boundary.**

Under Policy A, all 6 wobbling LPs show within-LP bucket variation:
LP-03 (9×risk / 1×needs_review), LP-10 (1×risk / 9×needs_review),
LP-14 (1×risk / 9×needs_review), LP-16 (4×risk / 6×needs_review),
LP-26 (2×risk / 8×needs_review), LP-32 (1×risk / 9×needs_review).

Under Policy B, ALL 6 are stable at actionable_material_risk.
The instability that 375I measured vanishes completely when the high/medium boundary is collapsed.

**Proven claim:** 100% of Policy A's routing instability on this lease is a boundary artifact
that high+medium collapse eliminates.

**Caveat:** Valid only for the adjacent high↔medium wobble in this run (0 full swings present).
A lease where 5e produces full low↔high swings would expose instability that collapse could not erase.

**Still unmeasured:** Whether full swings (low↔high) can occur in any lease. Q3 recorded 0; this is
a single lease under stable use-profile conditions.

---

## Q5 — Policy C Needs-Review flood

**19/26 directional findings would NOT route to Risk under Policy C.**

Policy C (source-strict) correctly blocks 18 not_eligible + 1 assessed_low (LP-20) from Risk routing.
Only 7/26 directional findings have assessed medium-or-high materiality and would reach
actionable_material_risk under Policy B+C.

**Proven claim:** Source-strict routing produces a 73% reduction in directional Risk findings vs the current
classifier. This is a correct reflection of 5e's 8/32 eligibility coverage on this lease.
**375E-COV must precede production 375E-DIR release.**

**Caveat:** The 18/26 is not a Policy C failure — it correctly names the gap. The risk is presenting
a source-strict model to lawyers before widening 5e, which would display far fewer Risk items than
the current (undiscriminating) routing while silently omitting assessable provisions.

**Still unmeasured:** Post-375E-COV Risk count under C. If widening doubles eligible LPs (16/32),
the not_risk count under C could drop from 19 to ~11.

---

## Q6 — Policy E vs B/D divergence (asymmetric result)

> **Policy E is NOT a proposed production policy. It is a diagnostic control
> used to measure whether the adverse-direction gate is load-bearing on this artifact.**

**Result (verbatim required form):**
Using Stage 7 direction as the primary direction axis:
Policy E does not diverge from Policy B for any eligible LP on this artifact.
All 8 eligible LPs have direction=adverse (tenant_unprotected) in the frozen Stage 7 findings;
since B and E both route adverse + medium/high to the actionable_material tier, the direction
gate is never exercised.

Record verbatim: **"direction gate not exercised by this n=1 artifact.
Non-divergence proves the lease was too one-sided to stress the sign axis,
NOT that direction is decorative."**

**LP-05 design tension:**
Stage 7 says direction=adverse (tenant_unprotected, Dir-05), but Stage 5e says gap_impact=favorable
(absence of this provision benefits this tenant). Under Stage 7 direction, B and E agree.
Under 5e gap_impact as the direction axis, B would block LP-05 (favorable → not-adverse-gate),
while E would route it to actionable_material — a clear divergence, and confirmation that the
direction gate is load-bearing.
**375E-DIR must specify which axis governs the adverse gate before implementation.**

**Proven claim:** Under Stage 7 direction, 0 E/B divergences. The lease is fully one-sided at the
directional finding level; every eligible LP is adverse.

**Caveat:** The non-divergence is a property of the Atlas Meridian lease composition, not evidence
that direction is unnecessary. LP-05 demonstrates a concrete case where the axis choice would
produce a divergence.

**Still unmeasured:** E/B divergence on a lease with genuine favorable-direction, medium/high-materiality findings.

---

## LP-20 note

LP-20 is **materiality-stable / direction-unstable**.
Materiality: all 10 Q3 samples = low (stable tier).
5e gap_impact across 10 replays: neutral×8, adverse×1, context_dependent×1 (direction-unstable).
Stage 7 direction (frozen): adverse (tenant_unprotected, Dir-16).
375E has four output axes; stability on materiality does not launder instability on gap_impact.
Do not use LP-20 as a clean stability control.

---

## Decision summary

| Finding | Implication |
|---|---|
| Q1 PASS | Keyed 5e stabilization NOT needed for this lease. Record B+C as CANDIDATE direction (provisional n=1). |
| Q2 18 implicit floors | Add materiality_source field; 375E-COV disclosure required before production. |
| Q3 18/26 without assessed mat | 375E-COV must widen _should_assess before production 375E-DIR. |
| Q4 A instability = boundary artifact | Policy A is inferior to B on this lease; B eliminates the artifact. |
| Q5 73% not-Risk under C | 375E-COV precedes production release. Do not ship source-strict routing before widening 5e. |
| Q6 direction gate not exercised | LP-05 Stage7-vs-5e discordance is a real design question for 375E-DIR. Resolve axis before implementation. |
