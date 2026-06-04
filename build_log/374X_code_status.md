# Step 374X — Status: exposure-headline polarity containment (OUTPUT PROSE ONLY)
**Date:** 2026-06-03  **Scope:** backend `cam/adapters/lease_review/lease_exposure.py` only. No app.js, no
version bump. **NO routing / coverage_state / materiality / partial_class / count / hard_flag change.**

---

## HARD PRECONDITION — PASSED (exposure/headline prose is terminal/display-only)
Grepped every reader of the exposure-prose fields (`exposure_statement`, `exposure_headline`,
`exposure_elements_used`). None feed classification/routing/state/materiality/hard_flag:
- **`lease_coverage.py:810`** `"exposure": a["exposure_statement"]` — attaches prose to a display
  `attention_items` entry; the gating key is `a["requires_attention"]` + `coverage_state`, independent of prose.
- **app.js** — all 10 refs (14410, 16213, 16322/16332, 17117/17124, 18338/18350/18408/18421) are card/sidebar/
  tooltip text. A targeted grep of `exposure_statement|exposure_headline` intersected with
  `classif|isPriority|_reviewSubtype|bucket|route|hard_flag` → **NONE**. The frontend classifier
  (`classifyFindingType`/`isPriorityReview`/`_reviewSubtypeOf`) routes on `coverage_state`,
  `verdict_distance`, `review_priority_distance_signal`, `use_impact`, `partial_class` — never the prose.
- **lease_synthesis.py** — no reads of exposure prose. Annotators / report_generator / cli_block — display output.
- **Order of computation** (`generate_exposure`, lease_exposure.py:487-490): `materiality` and `partial_class`
  are computed and stored on the assessment from `elements_missing` **before** `_build_model_exposure`
  (:509). `hard_flag` / `verdict_distance` / `coverage_state` come from the upstream 305/coverage path.
  The prose is pure output (`assessment.update(exposure)`).

Conclusion: the headline is terminal display. The patch is safe → proceeded.

## The change (lease_exposure.py)
1. **New helper `_absence_polarity_by_label(pid)`** — maps each Step-305 `element_label` → its schema
   `absence_adverse_to` (via `get_issue_area(pid)["expected_elements_305"]`). Returns `{}` for LPs with no
   305 schema (older LPs) → caller falls back to current handling.
2. **Partition the model input** (`_build_model_exposure`, the `else`/missing branch). For the selected
   `perspective`, each missing element is routed by `absence_adverse_to`:
   - `== opposite party` → **`favorable_absences`** slot (context only; NOT a gap). *(the only behavior change)*
   - everything else (`== selected perspective`, `"both"`, `null`/contextual, unknown, or no-305-schema LP)
     → **adverse-gap input**, unchanged. `elements_used = adverse_missing[:4]`.
   - For `neutral` perspective `opposite` is `None` → nothing moves (current behavior preserved).
   - `assessment["elements_missing"]` is **NOT mutated** — only a local partition of a copy is read.
3. **Prompt template** gained a `Favorable or non-adverse absences (context only — do NOT describe as a gap
   or exposure): {favorable_absences}` line, and a `{polarity_note}` instruction:
   *"Describe <perspective> exposure ONLY from <perspective>-adverse or contextually-adverse elements. Do NOT
   describe the absence of a burden on the <perspective> as a gap or exposure. Favorable/non-adverse absences
   may be mentioned only as offsetting context, or omitted from an adverse headline."*
   Opposite-polarity elements are passed in the separate slot (not dropped), so the model keeps the info.

## Validation (without a full re-run — exposure prose is model-generated at pipeline time)
The visible headline only changes on a NEW run; the stored 030920/181402 headlines are frozen in their result
JSONs and cannot be replayed. So I validated the **model INPUT** deterministically by unit-testing the
partition + rendering the actual prompt (no model call):

- `_absence_polarity_by_label('LP-27')` against the live schema → self-help `absence_adverse_to = tenant`;
  lender-notice/cure `absence_adverse_to = landlord`.
- Partition (tenant perspective) of LP-27's `elements_missing`:
  - **adverse slot (narrated):** `["Tenant may perform landlord's obligation and offset against rent"]` (self-help).
  - **favorable slot (context only):** `["Tenant must notify lender and afford lender cure period…"]` (lender).
  - Asserted: self-help ∈ adverse, lender ∈ favorable, **lender ∉ the "Missing or unfavorable elements" line**.
- Rendered `_EXPOSURE_USER_TEMPLATE.format(...)`:
  - `Missing or unfavorable elements: Tenant may perform landlord's obligation and offset against rent`
  - `Favorable or non-adverse absences (context only …): Tenant must notify lender and afford lender cure …`
- `python -m py_compile lease_exposure.py` → clean; module imports clean.
- `_EXPOSURE_USER_TEMPLATE.format` is called in exactly ONE site; no `assessment["elements_missing"]` mutation;
  `materiality`/`partial_class` computed upstream of the exposure call.

**Result:** on the next run, LP-27's self-help/offset stays eligible as tenant exposure; the lender-notice/cure
absence is no longer narrated as a tenant gap / "lender cure delay". LP-27 STAYS Risk (LP-27 high-materiality
floor + missing self-help) — `partial_material` and the Risk bucket are computed upstream from
`elements_missing`, untouched by this prose partition. No count changes.

## Out of scope / residual (noted, not changed)
- NOT wiring polarity into `derive_lp_state` / `_classify_materiality` / routing — that is the measure-first
  374Y-Q step.
- NOT reinterpreting `null` / `"both"` / contextual polarity (stay adverse-eligible here).
- **Schema-path residual:** `_build_schema_exposure` has a `f"… {missing[0]} is absent."` fallback (only when
  an LP has no schema `exposure_statement`); it is NOT polarity-filtered. LP-27 uses the MODEL path (so it is
  fixed), and LPs with a schema statement don't hit the `missing[0]` fallback. Flagged for 374Y-Q; left as-is
  to stay inside this narrow model-input brief.

## Decisions Needed
None.
