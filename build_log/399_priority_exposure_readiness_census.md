# 399 — Priority Exposure Readiness Census (read-only measurement)

**Type:** Measurement / report only. NO code, NO UI, NO pipeline, NO prompt, NO `cam/core/`, NO commit.
**Date:** 2026-07-05
**Author:** Chat (measurement against real artifact + render-path trace)

## Artifact under census

`results/lease_review_20260611_145145_3131a1/tenant_0/pipeline_results.json` (frozen Atlas run, 2026-06-11). Mode C. 32 coverage items. This is the guaranteed-hit artifact; the live 2026-07-05 run (`lease_review_20260705_182229_1771a4`) was NOT available to this census — see n=1 caveat at end. Screenshots under discussion are the 2026-07-05 run; the *mechanisms* below are the same code path, but per-card specifics for that run are unverified here.

---

## Executive finding

**This is a PROVENANCE + COVERAGE problem first. Not an ontology problem. Not primarily an ordering problem. Secondarily a badge-semantics problem.**

Three facts drive the conclusion:

1. **Assessed consequence is sparse: 7 of 32 coverage items carry assessed `use_impact`. 25 do not.** A lawyer-facing "biggest traps first" surface has real signal for 7 items and nothing but generic/table data for the other 25.
2. **The finding text itself is templated on 30 of 32 cards.** `exposure_source = schema` on 30/32; only 2 cards have a `model`-generated exposure statement. The sentence the lawyer reads as "the finding" is a schema-default string keyed to the LP, not written about this lease, on 94% of cards.
3. **The honest-provenance fields already reach the browser and are not shown.** Per `398_code_status.md`, `buildItem(a)` receives the raw `coverage_assessment` dict; `a.use_impact`, `a.exposure_statement`, `a.exposure_source`, `a.use_adjusted` are all at the render point. The fix to make assessed-vs-default *look different* is therefore DISPLAY-LAYER, not pipeline.

**Consequence:** the machine currently presents 30 schema-default exposure statements and 29 table-default `low` materiality values with the same visual authority as genuinely assessed cards. That is the "stamp-not-reason" defect, and on this run it is the majority case, not the exception.

---

## The 7 assessed cards (the only Priority-Exposure-eligible subset today)

| LP | Label | cov_state | table_mat | ASSESSED use_impact.materiality | use_consequence | agreement | reasoning | hard_flag |
|----|-------|-----------|-----------|-------------------------------|-----------------|-----------|-----------|-----------|
| LP-03 | Lease Term & Renewal | partial | low | **high** | harmful | 3-0 | yes | false |
| LP-05 | Permitted Use | review_needed | low | **high** | context_dependent | 1-1-1 | yes | true |
| LP-10 | Alterations | partial | low | medium | harmful | 2-1 | yes | false |
| LP-14 | Force Majeure | review_needed | high | medium | harmful | 3-0 | yes | true |
| LP-16 | Parking | partial | low | **medium** | harmful | 3-0 | yes | true |
| LP-20 | Exclusivity | missing | high | not_applicable | neutral | 2-1 | yes | true |
| LP-32 | Hazardous Materials | partial | low | medium | harmful | 3-0 | yes | true |

The other 25 cards: no `use_impact`. Their only materiality is the generic table value (29 low / 3 high across the full set), and their exposure text is schema-default.

---

## Required counts

1. **Total coverage items:** 32
2. **With assessed `use_impact`:** 7
3. **Without:** 25
4. **By consequence provenance (exposure_source):** schema 30 · model 2
5. **exposure_reason_code:** schema_default 30 · high_materiality_missing_element 2
6. **Item-level (table) materiality:** low 29 · high 3
7. **use_adjusted:** False on all 32 (assessment never rewrote coverage_state on this run)
8. **Eligible for honest Priority Exposure ranking today:** eligible 7 · partial 0 · not-eligible 25

---

## hard_flag driver census (the badge-semantics finding)

7 cards carry `hard_flag = true`. Driver breakdown:

| LP | agreement | verdict_distance severity | consequence | actual driver |
|----|-----------|--------------------------|-------------|---------------|
| LP-05 | 1-1-1 | severe | context_dependent | **outcome disagreement** (the only true one) |
| LP-06 | none | severe | (no use_impact) | verdict_distance despite no outcome split |
| LP-14 | 3-0 | severe | harmful | verdict_distance despite UNANIMOUS outcome |
| LP-16 | 3-0 | severe | harmful | verdict_distance despite UNANIMOUS outcome |
| LP-32 | 3-0 | severe | harmful | verdict_distance despite UNANIMOUS outcome |
| LP-20 | 2-1 | severe | **neutral** | outcome split on a NON-HARMFUL item (priority flag on non-harm) |
| LP-15 | none | severe | (no use_impact) | verdict_distance despite no outcome split |

**Finding:** the "PRIORITY REVIEW" badge is driven by `verdict_distance` (how far apart per-element verdicts were), NOT by evaluator outcome disagreement and NOT by harmful consequence. Only 1 of 7 flagged cards (LP-05) is flagged because evaluators actually disagreed on the outcome. 4 of 7 are flagged while evaluators AGREED 3-0. 1 (LP-20) is flagged on a neutral/non-applicable consequence. So the badge does not mean "the analysts disagreed" and does not mean "this is high-consequence." It means "the per-element verdict spread was wide." That is a real signal but it is mislabeled as urgency/priority.

---

## Special checks

**LP-16 Parking (the landmine):** table materiality = `low`; assessed `use_impact.materiality` = **medium** (NOT high); `use_adjusted = False`. So assessment DID lift Parking above the table floor (low → medium) but did not make it high, and did not rewrite coverage_state. The current-state memory that suggested "table low overridden to high for a logistics tenant" is **STALE/INACCURATE for this run** — verified against artifact. Directionally the instinct (assessment matters, don't trust the table) holds; the specific value (high) does not.

**LP-20 Exclusivity:** hard_flag = true while assessed consequence = `neutral` and assessed materiality = `not_applicable`. This is a PRIORITY badge on a non-harmful, not-applicable finding. Explicitly called out: this is the clearest case that the badge is not consequence-driven.

**LP-05 (context_dependent / 1-1-1):** assessed materiality = **high**, consequence = context_dependent. This belongs in the "high-priority DEPENDS" category, not the "uncertain but low downside" category. A Priority Exposure surface should show it near the top labelled as depends-on-context, not bury it because it is technically Review Needed.

---

## Answers to the executive questions

1. **Primary problem:** provenance + assessed-consequence-coverage, with a secondary badge-semantics problem. NOT ontology. NOT primarily ordering.
2. **Is Option A (keep Risk as action-type, sort within buckets by assessed consequence, surface provenance) sufficient for now?** YES — and it is the correct first move. But note Option A alone under-delivers unless it ALSO marks the 25 unassessed cards as unassessed; sorting 7 assessed cards while leaving 25 default cards looking equally authoritative only half-fixes the problem.
3. **Evidence for Option B (redefine Risk as severity)?** NONE. Nothing in the artifact supports collapsing action-type into magnitude. The doctrine holds.
4. **Ready for a dedicated "Top Client Traps" / Priority Exposure surface?** ONLY FOR THE ASSESSED SUBSET (7/32). Leading the entire UI with a Priority Exposure panel now would mean 25/32 findings enter as "unassessed/default" — confidence theater at the top of the product. Not ready to lead with it.
5. **Minimum honest first build (if any):** DISPLAY-LAYER provenance honesty, in two parts, both using fields already at the render point:
   - (a) Make schema-default exposure text and table-default materiality visually distinct from assessed (`use_impact`-backed) content. `exposure_source`/`use_impact` presence is already in `buildItem`'s hands.
   - (b) Within existing buckets, sort assessed cards above unassessed, and among assessed, by `use_impact.materiality`. Display-layer sort on existing fields.
   - This is smaller than a Priority Exposure surface and is the honest precondition for one. Do NOT build "Top Client Traps" as the lead surface until assessed-consequence coverage is broad enough that it is not mostly fallback.

---

## Wording discipline honored

- Not claiming "CAM knows the biggest risks" — 30/32 exposure statements are schema-default; 25/32 have no assessed consequence.
- Table/schema-default materiality is NOT called assessed anywhere above.
- `hard_flag` is NOT described as evaluator disagreement — the census shows it is verdict-distance-driven, disagreement on only 1 of 7.
- Badge semantics stated from artifact, not priors (corrects Chat's own earlier "badge = disagreement" claim, which was wrong on 6/7 cards).

## n=1 caveat

This is ONE run. The single most important number — 7/32 assessed-consequence coverage — must be checked on at least one additional run (ideally the live 2026-07-05 `1771a4`) before treating "assessed consequence is sparse" as a standing pipeline fact rather than a property of the Atlas lease. If a second run shows similar ~20% coverage, that is a finding about the pipeline (under-generation of use_impact), not this document. DIRECTIONAL. NOT promoted. NOT for the patent record.

## Recommendation

**No code change yet.** The census supports a display-only provenance+sort build as the honest first move, but that should be authorized as its own gated step after you (Tzvi) review this. Do NOT build a Priority Exposure surface yet. The real precondition for the "sexy" Top Client Traps surface is broader assessed-consequence coverage, which is a pipeline question (why does only 7/32 get use_impact?), not a UI question — and that investigation has not been done.
