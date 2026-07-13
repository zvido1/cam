# 420 — Stage 5 Stabilization Policy Simulation

**Date:** 2026-07-13
**Type:** Offline analysis — zero API calls, no production code changes, no commit until review
**Input dataset:** 419 N=10 frozen-extraction panel runs (hash `ab80aafe…`, all 10 runs, 32 LPs, 416 evaluations)
**Panel:** post-414/416 (A=claude-sonnet-4-6 temp=0 / B=gpt-5.5 default / C=grok-4.3 temp=0)

---

## Executive Summary

Six stabilization policies were simulated against the N=10 frozen-input data. The critical finding is that policy selection has a binary consequence on LP-22 (the genuine 5/5 split): **P1, P5, and P6 falsely stabilize it by coin-flipping plurality; P2, P3, and P4 correctly route it to REVIEW_NEEDED.** That distinction is not a tie-breaker — it is the acceptance criterion. Any policy that stabilizes LP-22 has laundered a genuine disagreement into a confident answer.

Among the three honest policies, **P4 (threshold-classify: ≥8/10 stable, else REVIEW_NEEDED) is recommended for 421 design.** It cleanly separates boundary noise from genuine disagreement, requires no extraction caching to function correctly at the LP level, and has a well-defined resample trigger. The cost model shows 43.8% of LPs would trigger a resample under the known-unstable-set approach, or 25% under boundary-only.

Extraction caching **must accompany** Stage 5 stabilization — not precede it as a prerequisite, but as a co-delivered fix. Without it, the 12 extraction-driven LPs remain stochastic in production and can fool a threshold policy into false confidence on runs where three roles happen to agree on different inputs.

---

## Instability Classification

| Category | Count | LPs |
|----------|------:|-----|
| BOUNDARY noise (8/2 or 9/1) | 8 | LP-03, LP-05, LP-07, LP-09, LP-10, LP-16, LP-25, LP-28 |
| DIRECTIONAL preference (6/4 or 7/3) | 5 | LP-14, LP-15, LP-17, LP-26, LP-27 |
| GENUINE SPLIT (5/5) | 1 | LP-22 |
| **Total unstable** | **14** | |
| Stable 10/10 | 18 | all others |

**LP frequencies (complete):**

| LP | State distribution | Category |
|----|-------------------|----------|
| LP-03 | review_needed 9, partial 1 | BOUNDARY |
| LP-05 | review_needed 9, missing 1 | BOUNDARY |
| LP-07 | partial 8, review_needed 2 | BOUNDARY |
| LP-09 | covered 8, partial 2 | BOUNDARY |
| LP-10 | partial 8, review_needed 2 | BOUNDARY |
| LP-16 | review_needed 8, partial 2 | BOUNDARY |
| LP-25 | covered 9, partial 1 | BOUNDARY |
| LP-28 | partial 9, missing 1 | BOUNDARY |
| LP-14 | missing 7, partial 3 | DIRECTIONAL |
| LP-15 | partial 6, covered 4 | DIRECTIONAL |
| LP-17 | partial 7, review_needed 3 | DIRECTIONAL |
| LP-26 | partial 6, review_needed 2, covered 2 | DIRECTIONAL |
| LP-27 | partial 7, review_needed 3 | DIRECTIONAL |
| LP-22 | partial 5, review_needed 5 | **GENUINE SPLIT** |

---

## Policy Simulation Table

Six policies simulated against N=10 LP-level coverage_state distributions:

| Policy | Resolved/14 | Routes to RN | Unstable remaining | LP-22 output | False-stability risk |
|--------|------------:|-------------:|-------------------:|:-------------|:---------------------|
| P1: Plurality (N=10) | 14/14 | 3 | 0 | **partial (COIN FLIP)** | **HIGH — LP-22 laundered** |
| P2: Supermajority >=7/10 | 14/14 | 6 | 0 | REVIEW_NEEDED | Low — genuine splits surface |
| P3: Supermajority >=8/10 | 14/14 | 9 | 0 | REVIEW_NEEDED | Low — more conservative |
| P4: >=8/10 stable, else RN | 14/14 | 9 | 0 | REVIEW_NEEDED | Low — identical to P3 |
| P5: Asymmetric-missing | 14/14 | 3 | 0 | **partial (COIN FLIP)** | **HIGH — LP-22 laundered, LP-14 biased** |
| P6: Missing needs >=2 confirms | 14/14 | 3 | 0 | **partial (COIN FLIP)** | **HIGH — LP-22 laundered** |

**Notes on P1:** LP-03 and LP-05 correctly resolve to review_needed because the modal state IS review_needed (9/10). LP-16 similarly (8/10). These are not false stabilities. But LP-22 (5/5 tie) resolves to "partial" by Python Counter tie-breaking — this is undefined behavior on a real signal, not a design choice.

**P3 and P4 are identical** in this dataset because the threshold is at 8 and no LP falls between 7 and 8.

**RN LPs under P2:** LP-14, LP-15, LP-22, LP-26, LP-27, LP-17 (6 directional + genuine split — all correct)
**RN LPs under P3/P4:** LP-03*, LP-05*, LP-14, LP-15, LP-16*, LP-17, LP-22, LP-26, LP-27 (9 LPs)
*Boundary-noise LPs with review_needed as modal state are routed correctly even under P3/P4.

---

## Required Analysis 1: Directional Bias on Asymmetric Rules

### P5: Asymmetric-missing (presence wins if any run shows presence)

P5 changed exactly one LP outcome vs. plurality:

**LP-14: `missing` (P1) → `partial` (P5) [direction: toward-covered]**

Root cause: LP-14.rent_abatement is explicitly_present in Roles B and C on all 10 runs but Role A returns missing on 7 of 10 runs. When Role A returns missing, the LP-level state is "missing" (missing rent_abatement + 3 other always-missing elements tip the merge below "partial"). P5's rule detects any presence reading and excludes the missing votes, yielding "partial."

**Is P5's output more accurate?** Possibly. Role B (10/10 explicitly_present) and Role C (10/10 explicitly_present) both consistently find the rent_abatement clause. Role A stochastically misses it 7 times. The "partial" output is arguably more accurate than "missing" — the clause is apparently in the lease, only one evaluator intermittently fails to find it. But the correct intervention is not P5 (which encodes a blanket presence-wins prior); it is stabilizing Role A's rent_abatement reading specifically.

**Systematic bias measurement:** P5 moved one outcome toward-covered, zero toward-gap. That is a sample-of-one — insufficient to characterize the rule's systemic direction from this dataset. However, the rule's design encodes an asymmetric prior: absence evidence is downweighted relative to presence evidence. For a tenant-side tool, this prior is dangerous. A lease where the rent_abatement clause is genuinely absent (or conditionally present but not triggered) should return "missing," not be pulled toward "partial" because one evaluator found something adjacent. P5 gets the right answer here for the wrong reason.

**P6 (missing needs >=2 confirmations) did not change any outcome** relative to plurality in this dataset. Every LP where "missing" was the plurality result had missing appear >=2 times across runs. P6 is inert on this data.

### Directional bias verdict

Both rules are designed to reduce false-missing findings. On this dataset, P5 produces one toward-covered shift (LP-14), zero toward-gap shifts. P6 produces no shifts. Neither rule produces false confidence on the boundary-noise LPs. But both **fail to correctly handle LP-22** (leaving it as a coin-flipped "partial" instead of routing to REVIEW_NEEDED), which is the more important failure. A rule that avoids false-missing at the cost of laundering a genuine split is not an improvement.

---

## Required Analysis 2: Is Grok Wrong, or Just Noisy?

Per-element analysis of Role C minority verdicts across the 14 unstable LPs. Assessment is qualitative, based on the verdict patterns (no API calls, no additional clause reads — verdicts only).

### Cases where Grok's minority reading is likely a false negative (wrong)

**LP-16/exclusive_parking_protection**: C = implicitly_present 5/10, missing 5/10. A = implicitly_present 10/10. B = explicitly_present 9/10. When C reads "missing," both A and B see presence (one implicit, one explicit). An evaluator that intermittently fails to find a clause that two others consistently find is exhibiting a false-negative pattern, not a genuine legal reading.

**LP-22/non_disturbance_obligation_for_future_lenders**: C = explicitly_present 3/10, missing 7/10. A = explicitly_present 10/10. B = explicitly_present 9/10. When C reads "missing," A and B agree on explicit presence 9-10/10. C's majority reading on this element (missing 7/10) contradicts a 2-role consensus. This is the most problematic case: Grok's modal verdict on this element is likely wrong.

### Cases where Grok's minority reading is defensible or uncertain

**LP-03/initial_term_duration**: C = missing 8/10, unclear 1/10, explicitly_present 1/10. A = unclear 10/10. B = explicitly_present 10/10. Three-way disagreement: B finds an explicit term; A can't make the determination; C mostly says it's missing. This is a genuine reading dispute about what qualifies as "explicit" statement of term duration. All three positions are legally defensible.

**LP-26/constructive_eviction_addressed**: C = missing 6/10, covered_in_other_LP 4/10. A = unclear 3/10, covered_in_other_LP 3/10, missing 4/10. B = covered_by_default_law 10/10. B's reading (California default law covers constructive eviction) is legally correct as a background rule. C's covered_in_other_LP reading (4/10) is also defensible. C's missing reading (6/10) is arguably wrong but reflects a schema where "not explicitly stated in this LP" could mean missing. Genuine interpretive ambiguity.

**LP-27 elements (common_law_remedies, remedies_cumulative, tenant damages/performance)**: C oscillates between missing and covered_by_default_law. B consistently says covered_by_default_law. A mostly says missing or unclear. This is a real legal question: California common law provides these remedies by default unless waived; the lease doesn't address them explicitly. Both missing and covered_by_default_law are defensible depending on the evaluator's interpretation of what "default law coverage" means in the schema.

**LP-17/venue_jurisdiction and claims_time_limit**: C = mostly covered_by_default_law with some unclear. B = covered_by_default_law 10/10. A = mostly missing. Same dynamic as LP-27 — a CA default-law coverage question where B and C mostly agree and A is more skeptical.

### Cases where Grok is actually the majority or correct reading

**LP-14/rent_abatement**: C = explicitly_present 10/10 (same as B). The LP instability is driven by Role A's stochastic misses (missing 7/10), not by Grok. Grok is correct and stable here.

**LP-28 elements**: C flips once on three elements (future_changes_in_law, structural_allocation, grandfathering) but modal is explicitly_present 9/10 in all cases — same as A (10/10) and B (mostly). The 1/10 flips are isolated excursions; Grok's majority reading is correct.

### Defensibility verdict

**Grok is wrong (false negative) on 2 elements:** LP-16/exclusive_parking_protection (when missing) and LP-22/non_disturbance_obligation (majority reading = missing, contra A 10/10 and B 9/10 EP). These are the two cases where a majority-suppression policy would improve the answer.

**Grok's minority reading is defensible on 7+ elements** (LP-03, LP-05/specific_permitted_use, LP-17, LP-26, LP-27, LP-15/approval_process). On these, a policy that overrules Grok's minority reading would suppress legitimate legal uncertainty.

**Grok is the correct or majority reading on several elements** (LP-14/rent_abatement, LP-28 elements, LP-17/claims_time_limit). The 417 attribution ("Grok is 43-49% of flips") is numerically accurate but narratively misleading: Grok also provides stabilizing signal in multiple cases.

**Conclusion:** Grok is noisy, and on 2 elements is likely wrong in a predictable direction (false-negative missing). It is not systematically wrong. A policy that suppresses Grok-minority readings globally would degrade the panel on the majority of cases where those readings are defensible.

---

## Required Analysis 3: Downstream CRX Identity Stability

A CRX/compound finding keys off element-level identity — specifically which elements have which merged verdicts, and which elements are in disagreement. LP-level coverage_state stability is a necessary but not sufficient condition for CRX identity stability.

### Element-level churn (proxy for CRX fingerprint stability)

- **Total elements in unstable LPs:** 98
- **Stable element identity (same merged verdict all 10 runs):** 81/98 (82.7%)
- **Churning element identity:** 17/98 (17.3%)

The 17 churning elements, by severity:

| Element | Verdict distribution (10 runs, 3-role merged) | Notes |
|---------|----------------------------------------------|-------|
| LP-03.initial_term_duration | missing 4, explicitly_present 3, unclear 3 | 3-way split; no majority |
| LP-22.non_disturbance_source_is_binding | missing 5, unclear 4, explicitly_present 1 | LP-22's core instability |
| LP-26.constructive_eviction_addressed | missing 5, covered_in_other_LP 5 | 50/50 genuine split |
| LP-05.specific_permitted_use | unclear 6, explicitly_present 2, missing 2 | B=missing, C=EP, A=unclear |
| LP-15.landlord_modify_remove | implicitly_present 6, explicitly_present 4 | Adjacent presence states |
| LP-16.parking_allocation | unclear 6, explicitly_present 2, missing 2 | A=unclear, B=EP, C=missing |
| LP-17.venue_jurisdiction | covered_by_default_law 6, missing 4 | A=missing 10/10; B,C say default |
| LP-05.prohibited_use_restrictions | explicitly_present 7, implicitly_present 3 | Presence subtype only |
| LP-09.use_restrictions_bind_transferee | implicitly_present 7, covered_in_other_LP 3 | Presence subtype only |
| LP-27.common_law_remedies_preserved | missing 7, covered_by_default_law 3 | |
| LP-27.tenant_right_to_damages | covered_by_default_law 7, missing 2, unclear 1 | |
| LP-27.tenant_right_to_specific_performance | covered_by_default_law 7, missing 3 | |
| LP-15.approval_process | explicitly_present 8, implicitly_present 2 | Presence subtype only |
| LP-17.claims_time_limit | covered_by_default_law 8, missing 2 | |
| LP-27.remedies_cumulative_not_exclusive | missing 8, covered_by_default_law 2 | |
| LP-15.directory_listing | implicitly_present 9, explicitly_present 1 | Presence subtype only |
| LP-16.exclusive_parking_protection | implicitly_present 9, missing 1 | Grok's false-negative |

### Per-policy CRX stability projection

**P1 (plurality):** Routes the merged verdict to the modal value for each element. The 3 severe genuine splits (LP-03/initial_term, LP-22/non_disturbance_source, LP-26/constructive_eviction) get non-deterministic merged verdicts on tied cases. **CRX fingerprint is unstable for those 3 elements across production runs.** LP-22's LP-state instability propagates into its compound-finding fingerprint.

**P4 (>=8/10 threshold):** Elements with modal_count < 8 get "REVIEW_NEEDED" as merged verdict consistently. The 3 genuine-split elements above would always resolve to REVIEW_NEEDED — same merged verdict every run. **CRX fingerprint becomes stable, but as "unresolved" elements.** CRX findings that depend on those elements being resolved are blocked, not corrupted.

**Assessment:** P4 is the only policy that prevents churning CRX fingerprints on the severe splits. Under P1/P5/P6, LP-03/initial_term_duration, LP-22/non_disturbance_source_is_binding, and LP-26/constructive_eviction_addressed would produce different compound-finding identities in different production runs — a direct downstream manifestation of the panel's disagreement.

**Key finding:** Stabilizing LP-level coverage_state alone does not stabilize CRX identity. The 17 churning elements span 12 different unstable LPs. A policy must operate at the element level (or explicitly route element-level disagreement to REVIEW_NEEDED) to achieve stable compound-finding fingerprints.

---

## Cost Implications of Conditional Repeat

### Resample trigger options

**Option A — Known-unstable-set (whitelist):** Pre-run N=10 identifies 14 unstable LPs. On production runs, always resample those 14 LPs.
- **Resample rate: 14/32 = 43.8% of LP evaluations**
- Cost premium: ~44% additional evaluations per document
- Deterministic, no runtime logic needed
- Problem: the list is static. A different document may have a different unstable set.

**Option B — 3-role agreement at runtime:** If any element in an LP has 3-role disagreement, resample that LP.
- From data: 24/32 LPs (75%) have at least one run with role disagreement; 16/32 trigger on EVERY run
- **Resample rate: 64.4% of all (LP × run) evaluations trigger resample**
- Problem: triggers on currently-stable LPs (LP-06, LP-18, LP-29, LP-32 are all stable but trigger by this criterion)
- This option is impractical — 75% resample rate is not conditional repeat, it is double evaluation

**Option C — Threshold-trigger at LP level:** Collect 3-role verdicts; if LP-level state from 3 evaluations has no supermajority among the roles, resample.
- **Cannot be directly simulated** from N=10 data (we have per-role per-element verdicts, not single-run LP states derivable from 3-role LP-level vote)
- Conceptually: would trigger on LPs where the merge produces a split or tie signal
- Estimated: similar to known-unstable-set, probably 40-50% resample rate

**Option D — Boundary-only resample:** Only resample LPs that match the boundary-noise profile (8/2 or 9/1 pattern pre-characterized).
- **Resample rate: 8/32 = 25.0%** (boundary-noise LPs only)
- Does not resample directional or genuine-split LPs
- Directional LPs go to REVIEW_NEEDED under P3/P4 without resample
- LP-22 goes to REVIEW_NEEDED without resample (correct)
- Most conservative cost option that still stabilizes the boundary LPs

**Summary cost table:**

| Trigger | Resample rate | Notes |
|---------|-------------:|-------|
| Known-unstable-set (14 LPs) | 43.8% | Static, deterministic, document-specific |
| 3-role per-element disagreement | ~64% | Over-triggers on stable LPs |
| Boundary-only (8 LPs) | 25.0% | Conservative, leaves directionals as REVIEW_NEEDED |
| Threshold-based LP state | ~40-50% | Estimated, requires implementation |

**Sizing 421's per-run cost:** A single N=1 Stage 5 panel pass costs roughly 17-25 min end-to-end (extraction accounts for most of this). If extraction is cached, Stage 5 alone is ~5-8 min. An additional panel pass per LP resample adds ~3 evaluations per LP. Under Option D (25% resample), 8 additional LP evaluations per document. Under Option A (44% resample), 14 additional LP evaluations.

---

## LP-22 Under Each Policy

LP-22 state distribution: **partial 5/10, review_needed 5/10** — exact coin flip.

| Policy | LP-22 output | Assessment |
|--------|:------------|:------------|
| P1: Plurality | partial | False stability. Counter tie-breaking is undefined behavior, not a design choice. |
| P2: Supermajority >=7/10 | REVIEW_NEEDED | Correct. Neither state reaches 7. |
| P3/P4: >=8/10 threshold | REVIEW_NEEDED | Correct. |
| P5: Asymmetric-missing | partial | False stability (same coin-flip as P1 — missing not involved here). |
| P6: Missing >=2 confirms | partial | False stability (same as P1). |

LP-22's element-level analysis:
- **non_disturbance_obligation_for_future_lenders**: A=EP 10/10, B=EP 9/10, C=EP 3/missing 7 → merged: explicitly_present (EP wins 22/30 role verdicts). But C's 7/10 missing is the outlier that drags this down.
- **non_disturbance_source_is_binding**: A=unclear 10/10, B=missing 7/unclear 3, C=missing 8/EP 2 → merged: missing (churning between missing/unclear/EP — 5/10 merged = missing, 4/10 = unclear, 1/10 = EP). This is the genuine split element.
- **snda_execution_timing**: A=missing 10/10, B=missing 10/10, C=missing 9/covered_in_other_LP 1 → missing 10/10 (stable).

The LP-22 instability is concentrated on `non_disturbance_source_is_binding` (true 50/50 split in merged verdict) and secondarily on how the `non_disturbance_obligation_for_future_lenders` flipping affects the LP-level merge. No stabilization policy without element-level REVIEW_NEEDED routing can resolve this correctly.

---

## Role-Weighted Aggregation (Diagnostic Only — Non-Canonical)

Simulated for completeness. Not recommended. Not proposed as a fix.

Under a role-weighted scheme downweighting Role C by 50% (A=1.0, B=1.0, C=0.5):
- The effect would be to upweight A+B consensus when C disagrees
- On LP-22/non_disturbance_obligation: A=EP 10, B=EP 9, C=EP 3/missing 7 → weighted EP wins more often → LP-22 would likely stabilize as `partial` — **this is the launder-the-disagreement outcome**
- On LP-03/initial_term_duration: A=unclear 10, B=EP 10, C=missing 8 → A+B tie; downweighting C amplifies the A-B disagreement, not resolves it
- On LP-27 elements: A=missing/unclear, B=covered_by_default_law, C=varies → A+B already split; downweighting C doesn't help

**Why this doesn't work:** 419 measured Grok's variance rate, not its accuracy. On LP-22/non_disturbance_obligation, if Grok's "missing" reading is actually correct (SNDA language absent or buried in a cross-referenced document not in the tenant text), downweighting Grok to force "explicitly_present" would be producing a false-positive coverage finding on a potentially real gap. The fact that A and B both say EP doesn't make them right — it makes three-way verification harder to dismiss.

The diagnostic confirms: role-weighting would suppress LP-22's genuine split (producing false confidence) and would not cleanly resolve the genuine legal ambiguity cases in LP-03, LP-26, LP-27.

---

## Element-Level vs LP-Level Aggregation

**LP-level aggregation (current):** Merge element verdicts → LP state. Apply policy at LP state level.

**Element-level aggregation:** Apply policy at the per-element merged-verdict level, then derive LP state from stabilized element verdicts.

419 shows that LP-level state stability and element-level identity stability are not the same thing. 14 LPs have unstable LP-level state; but 17 elements have unstable merged-verdict identity, spanning 12 of those 14 LPs.

**Recommendation:** The policy must operate at the element level (or at minimum, route element-level disagreement to REVIEW_NEEDED) for CRX identity stability. A policy that only looks at LP-state and votes on it cannot distinguish between:
- "LP-09 is 8/10 covered because all 3 roles agree it's covered on 8 runs" (element-level agreement)
- "LP-09 is 8/10 covered because 2 roles say covered and 1 says partial on every run" (element-level disagreement masked at LP level)

These have different CRX implications. The current data has examples of both.

---

## Answers to Brief Questions

**Which unstable LPs are boundary noise vs genuine disagreement?**
Boundary (8+/10 modal): LP-03, LP-05, LP-07, LP-09, LP-10, LP-16, LP-25, LP-28. Directional (6-7/10): LP-14, LP-15, LP-17, LP-26, LP-27. Genuine split (<=5/10): LP-22 only.

**Which policies stabilize 8/2 and 9/1 without suppressing LP-22?**
P2, P3, P4. All three route LP-22 to REVIEW_NEEDED while stabilizing or correctly classifying boundary-noise LPs. P3/P4 are more aggressive (also route directionals to REVIEW_NEEDED); P2 leaves directionals as resolved but with their modal state.

**Element-level or LP-level aggregation?**
Element-level for CRX identity stability. LP-level alone is insufficient (see Analysis 3).

**Does `missing` need asymmetric confirmation, and at what directional cost?**
On this dataset: P5 produces one toward-covered shift (LP-14), zero toward-gap. P6 is inert (no LP affected). The directional cost is low on this sample but the prior is structurally biased toward-covered — dangerous for a tenant-side review tool. The better fix for LP-14 is stabilizing Role A's stochastic misses on `rent_abatement`, not encoding a blanket presence-wins prior.

**Does role-neutral aggregation suffice?**
Yes, under P3/P4. No extraction of per-role weights needed. Role-neutral threshold-classify correctly routes all 14 unstable LPs (9 to REVIEW_NEEDED, 5 stabilized as boundary-modal).

**Cost under conditional-repeat policy:**
- If resample trigger = known-unstable-14: 43.8% additional evaluations per document
- If resample trigger = boundary-noise-8 only: 25.0% additional evaluations
- Runtime 3-role-disagreement trigger is impractical (64% rate, triggers on stable LPs)

**What routes to REVIEW_NEEDED rather than being forced stable?**
Under P3/P4: LPs where no state reaches 8/10 — which includes LP-22, LP-14, LP-15, LP-17, LP-26, LP-27, plus boundary-noise LPs whose modal state is review_needed (LP-03, LP-05, LP-16). Nine of 14 unstable LPs resolve to REVIEW_NEEDED, which is the honest answer for all of them.

**Must extraction caching precede or accompany Stage 5 stabilization?**
**Must accompany.** Without extraction caching, the 12 extraction-driven LPs (from 417/418c analysis) remain stochastic in production. A threshold policy applied to variable-extraction runs can be fooled: on a run where all three roles happen to agree (despite receiving different input), the threshold is met and a "stable" answer is output — but it reflects one extraction path, not the true clause text. Extraction caching is not a prerequisite (the policy works correctly on runs where extraction is already stable) but it must be co-delivered. Sequencing extraction caching first and then applying stabilization is cleaner operationally, but both can be shipped together.

---

## Recommendation for Step 421

**Policy: P4 — threshold-classify, >=8/10, element-level REVIEW_NEEDED routing**

Rationale:
1. Only honest policies are P2/P3/P4. P4 is chosen over P2 because the directional LPs (6/4 and 7/3) also have CRX-churning elements; forcing them stable at their modal state understates uncertainty.
2. P4 requires no role weighting, no asymmetric priors, no model changes.
3. LP-22 correctly surfaces as REVIEW_NEEDED. No laundering.
4. Resample trigger: boundary-noise LPs only (8 LPs, 25% cost premium) is the preferred approach if conditional repeat is the mechanism. Alternatively, if N=3 is used as the standard panel size with a fallback to N=10 on disagreement, cost is manageable.
5. The policy must operate at the element level, not only LP-level, to achieve CRX identity stability.

**What 421 needs to specify:**
- Whether stabilization is achieved via multiple panel passes (conditional repeat) or a single N=k pass with threshold aggregation
- The element-level merge logic under P4 (which element disagreement patterns route to REVIEW_NEEDED)
- Whether extraction caching ships simultaneously

**What 421 should not do:**
- Implement role-weighted aggregation
- Use an asymmetric-missing rule as a substitute for fixing Role A's rent_abatement stochasticity
- Apply threshold at LP-state level without also routing element-level disagreement to REVIEW_NEEDED

---

## False-Stability Risk Summary

| Policy | False-stability cases | Risk level |
|--------|----------------------|:-----------|
| P1: Plurality | LP-22 coin-flipped as "partial" | HIGH |
| P2: >=7/10 supermajority | None identified in N=10 data | Low |
| P3/P4: >=8/10 threshold | None identified in N=10 data | Low |
| P5: Asymmetric-missing | LP-22 coin-flipped; LP-14 biased toward-covered | HIGH |
| P6: Missing >=2 confirms | LP-22 coin-flipped | HIGH |
| Role-weighted (diagnostic) | LP-22 laundered as partial; other genuine splits may follow | Very high |

**N=10 is the ceiling of this simulation.** These counts are not rates extrapolatable to all documents. They measure what happened on this frozen extraction of this lease, under these 32 LP schemas, across 10 panel runs.

---

*Analysis complete. No code changed. No API calls made. No push.*
*Git: `git add -f build_log/420_stage5_stabilization_policy_simulation.md`*
*No commit until review.*
