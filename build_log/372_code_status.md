# Step 372 — Action-Bucket Stability Decomposition

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Diagnostic only. Read-only over stored 370c artifacts. No code, no reruns.
**Base SHA:** `af00247` (371).

---

## BLUF

**All 12 lawyer-facing bucket flips are Tier 1 (clean vs needs_attention — reassurance-boundary).** Every flip swings between "nothing to act on" and "protect this client." There are no Tier 2 or Tier 3 flips — the shape is maximally severe.

**First divergence: always at the evaluator judgment layer** (8 LPs at `element_verdicts`, 4 at `per_evaluator_lp_verdicts`). Nothing diverges in the merge logic, dispute propagation, or UI rendering. The instability is in what the evaluators return about specific elements, not in any downstream aggregation.

**Dominant class: E2 (9 of 12)** — the flipping element has the same citation or no citation across runs, but the evaluator returns a different verdict. This is interpretation instability without evidence differentiation — the same clause (or absence of one) produces different element-level calls run-to-run. Not a retrieval problem; not a downstream merge bug.

**1 LP (LP-20) is E3-downstream** — the evaluator output is stable but `use_impact.gap_impact` (Stage 5e) flips `favorable` vs `adverse` on the same coverage_state, driving the bucket change.

---

## 1. Per-LP table (12 flipping LPs)

**Field notes — REAL JSON field names:**
- `per_evaluator_lp_verdicts` = LP-level verdict per role (A/B/C) stored as dict
- `element_verdicts` = per-element array with `element_id`, `verdict`, `citation.{section_ref,quote,citation_quality}`
- `coverage_state_baseline` = merged coverage before dispute override
- `coverage_state` = final governed state (may differ from baseline after dispute)
- `use_impact.gap_impact` = Stage 5e field (present only on flagged LPs, ~11–14 of 32 per run)
- `lp_confidence` = confidence-cap equivalent (no field named `confidence_cap`)
- `review_priority_distance_signal.{escalated, hard_flag}` = no plain `review_priority` field
- `action_bucket` = **not stored** — re-derived from coverage_state + partial_class + use_impact

| LP | Name | Tier | Flip | First-divergence layer | E-class | Key flipping element(s) |
|---|---|---|---|---|---|---|
| LP-03 | Lease Term & Renewal | **1** | clean vs needs_attention | `per_evaluator_lp_verdicts` | E2-no-cite | `expiration_date`: missing/unclear flip — no citation in any run |
| LP-05 | Permitted Use | **1** | clean vs needs_attention | `element_verdicts` | E2-mixed | `specific_permitted_use` (missing/unclear), `co_tenancy_anchor_dependency` (missing/disputed) — no citations on key elements |
| LP-09 | Subletting & Assignment | **1** | clean vs needs_attention | `element_verdicts` | E2-same | `change_of_control_addressed` (disputed/missing), `use_restrictions_bind_transferee` (unclear/disputed/covered_in_other_LP) — no citations |
| LP-13 | Environmental/Hazmat | **1** | clean vs needs_attention | `element_verdicts` | **E1** | `negligence_carveouts`: different sections cited (11.2 vs Sections 11.1+11.2) — evidence selection variance |
| LP-16 | Parking & Access | **1** | clean vs needs_attention | `element_verdicts` | E2-no-cite | `parking_cost`: unclear/disputed flip — no citation |
| LP-19 | Utilities | **1** | clean vs needs_attention | `element_verdicts` | E2-mixed | `installation_connection_costs` (unclear/disputed/implicitly_present), `utility_upgrade_costs` (missing/unclear/disputed) — mixed citations |
| LP-20 | Exclusivity Protection | **1** | clean vs needs_attention | `per_evaluator_lp_verdicts` | **E3-downstream** | element-verdicts present, coverage_state stable (`missing`); `use_impact.gap_impact` flips `favorable`→`adverse` (Stage 5e) |
| LP-22 | SNDA | **1** | clean vs needs_attention | `per_evaluator_lp_verdicts` | **E1** | `landlord_obligation_obtain_snda_existing_lenders`: explicitly_present/disputed flip with different section refs; `subordination_mechanism_self_executing`: missing/disputed |
| LP-26 | Quiet Enjoyment | **1** | clean vs needs_attention | `element_verdicts` | E2-same | `constructive_eviction_addressed` (missing/unclear/disputed), `remedies_for_breach_of_quiet_enjoyment` (unclear/covered_in_other_LP) — no citations on flipping elements |
| LP-28 | Compliance with Laws | **1** | clean vs needs_attention | `element_verdicts` | E2-no-cite | `grandfathering_pre_existing`: disputed/missing flip — no citation |
| LP-29 | Right of Entry | **1** | clean vs needs_attention | `element_verdicts` | E2-same | `emergency_entry`: unclear/explicitly_present flip — same section cited where cited, absent in others |
| LP-32 | Environmental Remediation | **1** | clean vs needs_attention | `per_evaluator_lp_verdicts` | E2-same | `de_minimis_carveout` (explicitly_present/disputed), `notification_requirement` (disputed/unclear) — same section across runs |

**Bucket-by-run detail (W1/H1/H2/W2/W3/H3):**

| LP | W1 | H1 | H2 | W2 | W3 | H3 |
|---|---|---|---|---|---|---|
| LP-03 | clean | clean | **needs** | clean | clean | **needs** |
| LP-05 | clean | clean | clean | clean | clean | **needs** |
| LP-09 | **needs** | **needs** | clean | **needs** | clean | **needs** |
| LP-13 | **needs** | clean | **needs** | clean | clean | clean |
| LP-16 | **needs** | **needs** | clean | **needs** | **needs** | **needs** |
| LP-19 | **needs** | clean | clean | clean | **needs** | **needs** |
| LP-20 | clean | clean | **needs** | clean | **needs** | **needs** |
| LP-22 | clean | clean | **needs** | clean | **needs** | **needs** |
| LP-26 | **needs** | **needs** | clean | **needs** | **needs** | **needs** |
| LP-28 | **needs** | clean | **needs** | clean | **needs** | **needs** |
| LP-29 | **needs** | clean | **needs** | clean | clean | clean |
| LP-32 | clean | **needs** | **needs** | **needs** | clean | clean |

---

## 2. First-divergence histogram

| Layer (REAL field name) | Count | Layer description |
|---|---|---|
| `element_verdicts` | **8** | Per-element verdict from evaluators |
| `per_evaluator_lp_verdicts` | **4** | LP-aggregate verdict per evaluator role (A/B/C) |
| `coverage_state_baseline` | 0 | Merged baseline (no divergence here) |
| `coverage_state` | 0 | Post-dispute final state |
| `use_impact.gap_impact` | 0 | Stage 5e consequence (LP-20's driver is upstream, E3) |
| `lp_confidence` / `review_*` | 0 | |
| `action_bucket` (derived) | 0 | |

**Critical interpretation:** `element_verdicts` and `per_evaluator_lp_verdicts` are both
evaluator-judgment artifacts — they represent what the Stage 5 evaluators (A/B/C) assert
about individual elements and the LP overall. **The entire first-divergence picture lives at
the evaluator judgment layer. Nothing diverges downstream in aggregation, dispute propagation,
or rendering.**

LP-20 is the one exception where E3-downstream was triggered: the evaluators were stable but
Stage 5e (`use_impact.gap_impact`) produced different consequence assessments on the same
coverage state.

---

## 3. E1/E2/E3 counts

| Class | Count | Meaning |
|---|---|---|
| **E1** — different sections cited on flipping element | **2** (LP-13, LP-22) | Evidence-selection variance: different clause targeted |
| **E2-no-cite** — flipping element has no citation in any run | **3** (LP-03, LP-16, LP-28) | Pure interpretation instability: same absence, different call |
| **E2-same/mixed** — same or cross-LP citation, different verdict | **6** (LP-05, LP-09, LP-19, LP-26, LP-29, LP-32) | Evidence-stable, interpretation unstable; same text → different verdict |
| **E3-downstream** — stable evidence+coverage, downstream flip | **1** (LP-20) | Stage 5e (`use_impact.gap_impact`) non-deterministic |

**E2 total: 9 of 12.** The dominant mechanism is the evaluator returning different verdicts on the
same evidential basis — either the same cite, or no cite at all. This is not a retrieval or
section-targeting problem; it is evaluator interpretation instability at the element-assessment
step.

**E1 (2 LPs):** LP-13 cites `11.2` in some runs vs `Sections 11.1 and 11.2` in others — a minor
scope difference on a real clause, but the verdict flips (unclear → explicitly_present). LP-22
cites different authority for the SNDA obligation in different runs (section ref vs no ref). True
evidence-selection variance in both cases, but these are the minority.

**Note on evidence anchoring:** the initial analysis flagged `E1` for all 12 LPs because citation
SETS (across all elements) differed across runs. The refined analysis shows this was an artifact:
the citation differences occur mainly in **stably-assessed elements** (minor quote wording),
while the **flipping elements themselves are mostly uncited or cite the same section**. Evidence
anchoring (Step 305) is working for present elements; the instability is in elements where the
evaluator must call absence/presence/dispute on ambiguous lease language.

---

## 4. Tier 1/2/3 counts

| Tier | Count | Meaning |
|---|---|---|
| **Tier 1** — clean vs needs_attention | **12** | Reassurance-boundary: one run says "nothing here," another says "protect client" |
| Tier 2 — improvement vs risk/review | 0 | |
| Tier 3 — risk vs review (both demand attention) | 0 | |

**Every single flip is the worst kind.** There are no Tier 2 or Tier 3 cases where both buckets demand
attention in some form. The instability moves between "no lawyer action required" and "protect this
client," with no intermediate or softer cases.

---

## 5. Evidence anchoring: present-but-insufficient?

**Yes** — for E2 cases (9 LPs): the cited evidence where present is correctly anchored (Step 305
working, no `explicitly_present` verdict without a citation in the flipping elements except where
noted). However the anchoring is **insufficient** because the ambiguous-clause elements — `change_of_
control_addressed`, `expiration_date`, `constructive_eviction_addressed`, `grandfathering_pre_existing`
etc. — involve legal inference rather than explicit clause text. The evaluator must decide whether
the lease language *implicitly* covers the element, and that call is non-deterministic. Evidence
anchoring catches false positives ("it's here" when it's not) but does not resolve true judgment
calls ("does the silence mean absence or implication?").

---

## 6. Layers that cannot be audited (not separately persisted)

| Layer | Persistence status |
|---|---|
| Element-verdict merging rule (element_verdicts → coverage_state_baseline) | **Not persisted** — only the output is stored |
| Dispute-signal application (baseline → coverage_state) | **Not persisted** — only the final state |
| Stage 5e computation (model call → use_impact) | **Not persisted** — model prompt + raw response not stored |
| Action bucket derivation | **Not persisted** — re-derived at render time from stored fields |

These gaps mean:
1. A coverage_state_baseline difference cannot be traced back to the individual merge step that produced it without re-running Stage 5.
2. A use_impact difference (LP-20) cannot be attributed to a specific Stage 5e prompt or temperature event.
3. Audit trails for a disputed LP assessment cannot reach below the stored `element_verdicts` layer.

---

## 7. Zero-total-CPF watch

No new runs were produced in this step (read-only). Carried from 371: minimum CPF=23 (222051), six 370c runs 30–34. Zero-total-CPF remains a **known-but-unobserved** blind spot. No fix.

---

## 8. Recommendation (explicitly separated from proven findings — phrased as recommendation, not conclusion)

**Finding (not recommendation):** All 12 flips are Tier 1 (clean vs needs_attention), first diverging at the evaluator judgment layer (element_verdicts / per_evaluator_lp_verdicts), with 9/12 classified E2 (same or absent evidence, different verdict). LP-20 diverges in Stage 5e consequence assessment (E3). The product currently shows no instability signal to the lawyer.

**Recommendation (for Chat to route):**

1. **Containment is warranted before Stage 5 remediation is specced (372a scope).** The 12 Tier-1 flips present a concluded, stable bucket to the lawyer with no signal that the same run on the same document could show the opposite tomorrow. Whether or not the root cause is fixable, the product should not present a coin-flip as a conclusion. This is the 370a doctrine applied upstream: surface and flag, do not wash instability away. I have **not** specced 372a; this recommendation is for Chat to authorize it.

2. **Root cause appears to be in Stage 5 element-level evaluator judgment on boundary clauses** — specifically elements where the lease does not explicitly state the provision (absence/implication calls) and where one evaluator call (`disputed`, `unclear`, `missing`, `implicitly_present`) flips relative to another run. The implication is a narrower rubric question, not a temperature/seed fix — the evaluator is making a boundary call that the current prompt doesn't resolve deterministically. This is for Chat to scope after seeing the classification.

3. **LP-20 (E3-downstream) requires separate handling** — Stage 5e (`use_impact.gap_impact`) flipping favorable→adverse on the same coverage state is a different sub-component from the element-verdict instability. It should not be collapsed into the same remediation.

4. **E1 cases (LP-13, LP-22) may respond to section-targeting improvements** — the evaluator is finding different clauses. These are the minority (2/12) and should not define the remediation for the E2 majority.

**Not claimed:** that the evaluator-judgment instability is temperature-driven, that seed-pinning would fix it, that the flipping verdicts are wrong (both may be legally defensible reads), or that any specific remediation would reduce variance without harming correctness. Those questions require a different test.

---

## Scope / commit

- Read-only analysis; no code changes, no model calls, no reruns. No `cam/core/`.
- Committed: `_step372_decomp.py` (analysis script) + this status file (force-add).
- Pre-existing uncommitted `app/config.py` (Step 369 reload comment) left untouched.
