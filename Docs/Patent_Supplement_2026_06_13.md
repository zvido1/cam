# Patent Supplement — 2026-06-13

## Architecture A Phase 2: Verdict Distance and Confidence Capping at the LP Layer

**Status:** Reduced to practice. Code shipped Steps 351 / 351b / 352 (2026-05-19 / 2026-05-20), git `6c6f799` and follow-on. This supplement formalizes for the patent record what was already implemented, validated, and running. Patent sentences for this contribution were previously captured in `Patent_Current_State.md`; this document is the full standalone record the orientation doc flagged as owed.

**Relationship to prior supplements:** This is the LP-layer instantiation of the ordinal verdict-distance governance first established at the element layer in Supplement #18 (2026-05-15-b, ordinal verdict distance; three-dimensional run-time governance) and Supplement #21 (2026-05-17, element-level merge governance, Phase 1 RTP 2026-05-18). Supplement #18 established the principle and the six-rung ladder; Supplement #21 reduced it to practice at the element layer (the `Disputed` merge output). The present supplement reduces the same governance to practice at the **LP layer** — one layer up — and documents what that second instantiation proves that a single-layer implementation cannot.

---

## 1. What was built

Architecture A Phase 2 adds ordinal verdict-distance computation and distance-driven confidence capping at the LP layer of CAM's coverage decomposition. Concretely:

**New module:** `cam/adapters/lease_review/lease_verdict_distance.py`, containing:

- `VERDICT_RANK` — the six-rung ordinal ladder with a deliberate gap before `missing`:
  ```
  explicitly_present      = 0
  implicitly_present      = 1
  covered_in_other_lp     = 2
  covered_by_default_law  = 2
  unclear                 = 3
  missing                 = 5   (rank 4 deliberately empty)
  ```
- `derive_verdict_distance(v1, v2)` — pairwise ordinal distance, `|rank(v1) - rank(v2)|`.
- `derive_disagreement_severity(verdicts)` — over a list of per-evaluator LP verdicts, returns max distance, severity band, and the most-distant pair.
- `apply_distance_confidence_cap(base_confidence, severity, vote_count, consequence)` — caps assertion confidence as a function of disagreement severity, modulated by consequence.
- `derive_review_priority_distance_signal(severity, consequence)` — independently computes review escalation / hard-flag.
- `derive_per_evaluator_lp_verdict(element_verdicts)` — derives each evaluator's single LP-level verdict by plurality over that evaluator's own element verdicts, so that LP-layer distance is computed between evaluators, not between elements.

**Integration:** `assess_coverage_305()` (in `lease_coverage_305.py`) computes, after element merge, each evaluator's LP-level verdict, then the cross-evaluator disagreement severity, and writes `verdict_distance`, `lp_confidence_base`, and `per_evaluator_lp_verdicts` to the LP's output. Stage 5f (in `lease_adapter.py`, both Mode B and Mode C pipelines) applies the confidence cap **after** Stage 5e, so that use-aware materiality is available as the consequence input to the cap.

**Sequencing of the cap (load-bearing):** the cap is applied at Stage 5f, downstream of Stage 5e's use-aware materiality assessment. This ordering is itself a design commitment: it means the consequence term in the confidence cap is the use-specific consequence of the contested reading, not a generic severity. Distance governs how far apart the evaluators are; consequence governs how much that distance matters for this tenant's use. The two are combined at cap time, not before.

---

## 2. The distance metric and the deliberate gap

The ordinal ladder is not linear. Rank 4 is intentionally empty, so `missing` sits at rank 5 with a gap beneath it. This is the single most load-bearing design decision in the metric, and Step 351b (doctrine errata) is the record of its defense.

The gap does two things simultaneously that no linear scale can do at once:

- It keeps `unclear ↔ missing` at distance 2 (moderate). "I could not determine" versus "I am confident it is absent" is a real but bounded disagreement — both evaluators decline to assert presence; they differ on whether absence is established. Moderate is correct.
- It pushes `implicitly_present ↔ missing` to distance 4 (severe). `implicitly_present` is a *presence* verdict — it asserts substantive coverage exists through functional language. `missing` asserts no valid coverage path exists. That disagreement crosses the presence/absence boundary and is severe, even though the presence claim is inferential rather than literal.

A clean linear ladder (EP0 IP1 CO2 CD3 UN4 MI5) was considered and rejected, because it makes `unclear ↔ missing = 1` (minor) — semantically wrong. A perfectly clean rank scale that produces a wrong semantic outcome is not clean. The gap is the right tool, and it is load-bearing, not accidental.

The corrected full distance table (Step 351b, authoritative, formula-derived):

| | EP | IP | CO | CD | UN | MI |
|---|---|---|---|---|---|---|
| **EP** | 0 | 1 | 2 | 2 | 3 | **5** |
| **IP** | 1 | 0 | 1 | 1 | 2 | **4** |
| **CO** | 2 | 1 | 0 | 0 | 1 | 3 |
| **CD** | 2 | 1 | 0 | 0 | 1 | 3 |
| **UN** | 3 | 2 | 1 | 1 | 0 | 2 |
| **MI** | **5** | **4** | 3 | 3 | 2 | 0 |

Severity bands: distance 0 → none; 1 → minor (mechanism only); 2–3 → moderate; 4–5 → severe (presence/absence boundary crossed). Distance 4 is reachable only by spanning the gap — it is never produced by any pair of adjacent rungs. That is the gap doing its job.

Errata note for the record: Step 351 originally shipped an Appendix A table with several hand-authored values inconsistent with the implemented formula (IP↔MI listed as 3; CO↔CD as 1; CO↔UN and CD↔UN as 2). The **code was correct as shipped**; only the documentation table was wrong. Step 351b corrected the table to the formula-derived values above and made the implemented `VERDICT_RANK` authoritative. No code changed. This is worth preserving in the patent record because it demonstrates the metric is defined by a mechanical formula over an ordinal rank assignment, not by a hand-curated lookup that could encode arbitrary judgments — the formula is the invention; the table is merely its rendering.

---

## 3. What the LP-layer instantiation proves that the element layer did not

Supplement #18 stated the principle that ordinal verdict distance "operates at every layer of CAM's coverage decomposition." At the time, only the element layer was reduced to practice. Architecture A Phase 2 is the second independent instantiation, and the existence of two working layers is itself the contribution — it converts a stated generality into a demonstrated one.

The two layers are genuinely distinct in what they compute:

- **Element layer (Supplement #21):** within a single LP, three evaluators each produce a verdict per element; distance is computed between evaluators on the *same element*; maximally-distant dissent produces a `Disputed` element label, and (Phases 2–4) a critical Disputed element propagates a dispute signal up to the LP's bucket.
- **LP layer (this supplement):** each evaluator first reduces their own element verdicts to a single LP-level verdict (by plurality); distance is then computed between evaluators on the *whole LP*; maximally-distant dissent caps the LP's assertion confidence and independently escalates review priority.

These are not the same computation at two scales. The element layer governs *which elements CAM will assert are present*. The LP layer governs *how strongly CAM may assert the LP-level coverage conclusion at all*, and is the layer at which the use-aware consequence term enters (via the Stage 5e → 5f ordering). The element layer can flag an internal dispute while the LP-level majority still reads "covered"; the LP layer can cap confidence on an LP even when no single element crossed the Disputed threshold, because the evaluators' *aggregate* LP reads diverge. Two layers, two different governed questions, one shared ordinal-distance engine.

This is the patent-relevant point: the framework specifies the distance metric and the severity bands **once**, and instantiates them at each decomposition layer with the thresholds and the consequence-coupling appropriate to that layer. The generality claim in Supplement #18 is now backed by two reduced-to-practice instances rather than one instance plus an assertion.

---

## 4. Confidence cap and review priority are computed separately

Consistent with Guardrail #9 (the bucket tells the lawyer what to do; confidence tells how strongly CAM supports the assessment) and Supplement #18 (confidence and review priority are orthogonal governed outputs), Phase 2 produces **two** distance-driven outputs, not one:

- `apply_distance_confidence_cap()` lowers the LP's assertion confidence when severity is high. Severe disagreement hard-caps confidence at `low` regardless of consequence — CAM will not assert an LP coverage conclusion strongly when its evaluators are split across the presence/absence boundary.
- `derive_review_priority_distance_signal()` independently sets escalation and a hard review flag. At severe distance the LP is flagged for human review regardless of vote count.

These are separate because they answer separate questions. A severe split caps confidence (CAM should not assert strongly) AND escalates review (a human should look) — but the two signals are derived independently and surfaced independently, so neither collapses into the other. Low confidence is not, by itself, high review priority; consequence governs escalation independently of epistemic certainty.

---

## 5. The NOT_ASSESSED sentinel (Step 352) — a no-silent-default discipline

Phase 2's most subtle reduction-to-practice detail is the `NOT_ASSESSED_SENTINEL`, and it is worth the patent record because it is an instance of a recurring CAM discipline: **a value that was never computed must be labeled as never-computed, never as a default that happens to look like agreement.**

The defect Step 352 fixed: `_build_assessment()` (which builds every LP's output dict) originally did not include the verdict-distance fields. Only the Stage 305 path added them afterward. So every LP that did *not* go through Stage 305 — not-applicable LPs, missing-provision LPs, and LPs that took the global-scan preprocessing path — produced an output with no `verdict_distance` key. The UI read the absent key as null and showed NO_DATA. Worse, the original empty-list branch of `derive_disagreement_severity()` returned `{"severity": "none", "max_distance": 0}` — which **incorrectly implied the evaluators agreed**, when in fact no evaluators had run.

The fix introduced an explicit sentinel:
```python
NOT_ASSESSED_SENTINEL = {
    "max_distance": None,
    "severity": "not_assessed",
    "pair": [],
    "all_distances": [],
    "reason": "stage_305_not_run",
}
```
`_build_assessment()` now writes this sentinel for every LP by default; the Stage 305 path overrides it with real values when it runs. `apply_distance_confidence_cap()` and `derive_review_priority_distance_signal()` both treat `not_assessed` as an explicit no-cap / no-escalation case — distinct from `none` (which means evaluators ran and agreed). An LP where no evaluators ran is now categorically different in the data model from an LP where evaluators ran and agreed, even though both result in no confidence cap.

The doctrinal significance: "evaluators agreed" and "evaluators never ran" must never share a representation, because they have opposite epistemic meaning. Collapsing them is the same failure mode as treating a defaulted value as an assessed one (the `materiality_source="assessed"` anti-pattern condemned elsewhere in the project). The sentinel enforces the distinction at the data-model level. The corrected `derive_disagreement_severity(["explicitly_present"])` → `none` (single verdict, genuinely no disagreement) versus `derive_disagreement_severity([])` → `not_assessed` (nothing to compare) captures the boundary exactly.

---

## 6. Validation

**LP-16 synthetic end-to-end (Step 351).** Live T-10 API run was not possible in the code container (provider SDKs absent), so the end-to-end path was validated with mock evaluator outputs replicating the LP-16 Parking scenario: evaluator A all-`implicitly_present`, B all-`explicitly_present`, C all-`missing`. Result: `max_distance=5`, `severity=severe`, pair `[explicitly_present, missing]`; Stage 5f capped `lp_confidence=low` and set `hard_flag=true` at both moderate and high consequence (severe hard-caps regardless). The full computation chain — per-evaluator LP verdict derivation, cross-evaluator distance, severity banding, confidence cap, review escalation — was exercised and produced the specified outputs.

**Atlas Meridian regression (Step 352, no re-run).** Against stored results `lease_review_20260520_051055_6f883b/tenant_0`: distribution 7 severe / 1 moderate / 21 none / 3 N-A, unchanged by the sentinel fix. The seven severe LPs are the live demonstration that real evaluator runs on a real lease produce presence/absence-boundary disagreements at meaningful volume — the metric is not a synthetic-only construct.

**T-10-NY NOT_ASSESSED validation (Step 352).** Five LPs (LP-19/24/25/32 missing-no-provision; LP-29 partial-via-global-scan) confirmed to take non-305 paths and now carry the `not_assessed` sentinel rather than a null key or a false `none`. Unit assertions confirm the sentinel boundary: `[]` → `not_assessed`, `["explicitly_present"]` → `none`, `["explicitly_present","missing"]` → `severe`.

A live T-10 API run for the full 32-LP real severity distribution remains the one outstanding empirical item; the core logic is validated synthetically and via the Atlas regression. This is noted honestly rather than claimed as complete.

---

## 7. Patent sentences

> "CAM instantiates a single ordinal verdict-distance metric at multiple independent layers of its coverage decomposition. At the element layer, distance is computed between evaluators on the same element and governs which elements are asserted present. At the LP layer, each evaluator's element verdicts are first reduced to a single LP verdict, distance is computed between evaluators on the whole LP, and the result caps the strength of the LP-level coverage assertion. The metric is defined once; each layer applies it with the thresholds and consequence-coupling appropriate to that layer."

> "The LP-layer confidence cap is applied downstream of use-aware materiality assessment, so that the consequence term combined with disagreement severity is the use-specific consequence of the contested reading rather than a generic severity. Disagreement distance governs how far apart the evaluators are; consequence governs how much that distance matters for the declared use; the two are combined at cap time."

> "The verdict-distance rank scale contains a deliberate gap before the `missing` verdict. The gap simultaneously preserves `unclear ↔ missing` as a moderate disagreement and elevates `implicitly_present ↔ missing` to severe, because a presence verdict disagreeing with a missing verdict crosses the presence/absence boundary regardless of whether the presence claim is literal or inferential. A linear rank scale cannot produce both outcomes; the gap is load-bearing."

> "CAM's distance metric is computed mechanically from an ordinal rank assignment by an absolute-difference formula, not retrieved from a hand-authored lookup table. When implementation and a documentation table diverged, the formula was treated as authoritative and the table corrected to match it, because the governed quantity is the formula over ranks, not any enumerated set of pair values."

> "An LP for which no evaluators were run carries an explicit not-assessed sentinel that is categorically distinct, in the data model, from an LP for which evaluators ran and agreed. Both result in no confidence cap, but they carry opposite epistemic meaning, and CAM refuses to represent 'never assessed' as 'assessed and in agreement.' The severity function returns `not_assessed` for an empty verdict set and `none` only for a non-empty set that genuinely agrees."

> "The confidence cap and the review-priority escalation are derived independently from the same disagreement severity. A severe LP-layer split both caps assertion confidence and hard-flags the LP for human review, but neither signal is computed from the other; confidence answers how strongly CAM may assert, review priority answers whether a human must inspect, and consequence governs escalation independently of epistemic certainty."

---

## 8. Contribution map entry (for Patent_Current_State.md)

Under **Conceptual Architecture** / **Per-Element Architecture** lineage, add:

- **LP-layer verdict distance + Stage 5f confidence cap (Architecture A Phase 2)** — 06-13 (RTP Steps 351/351b/352, 2026-05-19/20). Second reduced-to-practice instantiation of the ordinal-distance governance of Supplement #18; LP-layer counterpart to the element-layer Supplement #21. Establishes: deliberate-gap rank scale (IP↔MI=4 severe, UN↔MI=2 moderate); consequence-coupled cap applied downstream of Stage 5e; NOT_ASSESSED sentinel as a no-silent-default discipline; confidence-cap and review-priority as separately-derived distance outputs.

---

## 9. What this supplement does NOT claim

- It does not claim a live 32-LP real-API severity distribution for T-10; that run is outstanding (Section 6).
- It does not claim the CO/CD split (both share rank 2; CO↔CD=0). Step 351b explicitly deferred that refinement to a future doctrine pass with its own architectural note.
- It does not extend the distance governance to a third decomposition layer. Two layers (element, LP) are reduced to practice; the per-assertion and per-document layers use other governance mechanisms and are out of scope for this metric.
- It does not modify `cam/core/`. Architecture A Phase 2 lives entirely in the lease-review adapter layer (`lease_verdict_distance.py`, `lease_coverage.py`, `lease_coverage_305.py`, `lease_adapter.py`), consistent with Guardrail #5 (core epistemic logic unmodified since Phase 1 extraction).

---

*Reduced to practice Steps 351/351b/352 (git `6c6f799` + follow-on), 2026-05-19/20. Supplement written 2026-06-13. Indexes into `Patent_Current_State.md`; does not replace the build-log code-status files, which are the implementation record.*
