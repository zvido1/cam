# Finding — perspective-polarity sign error: `absence_adverse_to` is dead data
**Date:** 2026-06-03  **Type:** READ-ONLY investigation (no production change). **Trigger:** LP-27 card on
the tenant-perspective Action Summary surfaces "No self-help; lender cure delay" and presents the *absence*
of a tenant **burden** (lender notice-and-cure) as if it were tenant exposure.

## TL;DR
The Step 305 schema correctly records, per expected element, **whom the absence hurts** (`absence_adverse_to`)
and **how much** (`absence_severity`). **`absence_severity` is consumed by the pipeline; `absence_adverse_to`
is consumed by ZERO pipeline code** — it is written into the schema and never read. Result: every missing
expected element is treated as a gap adverse to the selected perspective, even when its absence is favorable
or neutral to that perspective. This violates the documented coverage-vs-polarity architecture.

- `absence_adverse_to` references in tracked Python: **only `update_schema_305.py`** (the script that *writes*
  the field). No classifier / routing / exposure / use-impact module reads it.
- Scope: **73 of 212** Step 305 elements (34%) have `absence_adverse_to != tenant` (53 `landlord`, 20 `both`);
  **29 of those are `absence_severity: high`**. All are currently handled as tenant gaps when missing.

## LP-27 trace (the reported card)

### 1. Schema entry — CORRECT
`LP-27.lender_notice_and_cure_right` (retail_lease_knowledge.json → issue_areas[LP-27].expected_elements_305,
mirrored in Docs/Step_305_Schema_Pilot_LP-27.json):
- `absence_adverse_to`: **"landlord"**
- `absence_severity`: **"low"**
- `cross_LP_coverage`: **["LP-22"]** (lender notice/cure is often defined in the SNDA, not LP-27 directly)
- `review_notes`: *"Polarity note: this element is landlord/lender-favorable; absence is landlord-adverse
  because lender can lose practical ability to step in and cure."* (Also an ATTORNEY REVIEW FLAG on Pattern A.)
- Adjacent: `LP-27.tenant_self_help_and_offset` → `absence_adverse_to: "tenant"`, `absence_severity: "medium"`
  (a genuine tenant protection — its absence IS tenant-adverse).

The three evaluators returning **Missing** for the lender element are **factually correct** — the requirement
is absent. The defect is downstream sign handling, not the verdict.

### 2. Where the `missing` verdict flows
| Sink | Uses polarity? | LP-27 effect |
|---|---|---|
| **coverage_state** (`derive_lp_state`, lease_coverage_305.py:843) | **No** — counts missing by `absence_severity` only | Counts toward `partial`, but NOT decisively: the self-help element is also missing, so `partial` holds with or without the lender element. |
| **Risk routing** (`_classify_materiality` → `_classify_partial`, lease_exposure.py:87/114) | **No** | LP-27 ∈ `_HIGH_MATERIALITY_LPS` (lease_exposure.py:76) → any non-covered state = materiality **high** → `partial_material` → **Risk**. Driven by a per-LP floor, **independent of the lender element**. |
| **use-impact / consequence** | **No** | `use_impact = null` (defaulted; the separate Stage-5e gate bug). `absence_adverse_to` never feeds use-impact at all. |
| **Exposure prose / headline** (`_build_model_exposure`, lease_exposure.py:263) | **No** | `elements_used = missing[:4]` is passed to the exposure model as *"Missing or unfavorable elements"* with **no polarity filter**. The model includes the lender element → headline **"No self-help; lender cure delay"**. |

### 3. Does LP-27 remain Risk if the lender absence is not treated as adverse? — YES
Risk is over-determined by (a) coverage_state `partial` (caused by the missing **self-help/offset** tenant
protection) and (b) the LP-27 high-materiality floor. Removing the lender element from the adverse set
changes **no count and no routing** — LP-27 stays Risk on the correct (self-help) basis. **Only the card
summary/headline changes.** The instruction's conclusion ("do not conclude LP-27 should leave Risk") holds.

### 4. Is "lender cure delay" generated from the missing element, and backwards? — YES, both
- It is **model-generated** (`_parse_headline_envelope`), seeded by the polarity-blind `missing[:4]` list.
- The **schema's** own LP-27 `exposure_statement`/`risk_if_missing` correctly mention only self-help, offset,
  and termination — they do **not** mention lender cure. So the phrase is introduced by the exposure model,
  not the schema.
- It is **directionally backwards**: if the lender notice-and-cure requirement is *absent*, the lease shows
  **no** lender-cure delay. Absence of that burden is tenant-favorable/neutral; the headline frames a benefit
  (or non-event) as exposure.

## 5. Polarity-class scan (the systemic defect)
Over all 212 Step 305 elements, those whose absence is **not** adverse to the tenant (so missing them should
not behave like a missing protection) — **73 total**:

- by `absence_adverse_to`: **landlord 53, both 20**; by `absence_severity`: **high 29, medium 32, low 12**.
- These are exactly the "obligation/restriction on the perspective party" classes the architecture warns about:
  - **Tenant obligations** whose absence helps the tenant: LP-13 tenant indemnification (high), LP-28 tenant
    compliance (med), LP-30 tenant estoppel obligation (med), LP-32 tenant remediation/prohibition/survival
    (med), LP-22 tenant-executes-subordination / attorn-to-successor (high/med), LP-09 transfer documentation.
  - **Landlord remedy rights** whose absence helps the tenant: the entire LP-11 default suite —
    re-entry, terminate, **rent acceleration**, **recapture**, self-help-landlord-cure, monetary/non-monetary
    default definitions (several `high`); LP-24 landlord termination right.
  - **Landlord consent/control rights**: LP-09 assignment/subletting requires landlord consent (high),
    change-of-control, recapture; LP-05 prohibited-use restrictions.
  - **Landlord-protective insurance terms**: LP-08 CGL minimum (high), landlord additional-insured, certificate.
  - LP-27 itself: `notice_required_to_landlord` and `cure_period_for_landlord` are also `adverse_to: landlord`.

Because `absence_adverse_to` is never read, all 73 are currently treated as tenant gaps when missing. The
**confirmed** corruption today is at two sinks: **coverage_state** (a lease that merely *omits a burden on the
tenant* can be marked `partial`/"gap" instead of `covered`/favorable) and the **exposure prose/headline**
(favorable/neutral absence framed as tenant exposure). Risk **routing** is corrupted only where a favorable
absence also trips a materiality floor or high-state path; LP-27's lender element does **not** (LP-27 is
over-determined), but the 29 `high`-severity non-tenant elements are the cases most likely to flip
coverage_state strongly and to dominate the exposure headline on other LPs.

## Architecture note
The Step 305 design separates **coverage** ("this element is missing" — factually correct here) from
**perspective polarity** ("its absence helps or hurts this party"). The schema layer honors the split; the
runtime collapses it by reading `absence_severity` (a magnitude) while ignoring `absence_adverse_to` (the
sign). A missing element can be adverse, favorable, neutral, or context-dependent — the pipeline currently
encodes only "missing ⇒ adverse to the selected perspective."

## Recommended fix locus (NOT implemented — read-only step)
Consume `absence_adverse_to` against the selected `perspective` at the three polarity-blind sinks:
1. **`derive_lp_state`** (lease_coverage_305.py): a missing element whose `absence_adverse_to` is the *other*
   party (or `both` resolving favorable) should not, by itself, push the LP to `partial`/"gap" for this
   perspective — or should route to a favorable/neutral state rather than a coverage gap.
2. **Exposure model input** (`_build_model_exposure`, lease_exposure.py:295): filter/annotate `missing` by
   polarity so favorable-absence elements are not handed to the model as "Missing or unfavorable elements"
   (or are explicitly labeled favorable, as the `covered_unfavorable` landlord path already does at :291).
3. **`_classify_materiality`**: ensure a favorable-absence element cannot raise materiality (and confirm the
   legacy `_HIGH_MATERIALITY_ELEMENTS` strings — which include landlord-favorable "rent acceleration on
   default" and "recapture right" — cannot fire on a perspective for which those absences are favorable).

Freeze-behavior caution: this is a routing-affecting change for some LPs, so it must be measured (recompute
which LPs/counts move) before enforcement, per the 374P/374R-Q pattern. Legal/commercial framing (e.g.,
"is absence of a lender notice-and-cure prerequisite favorable for a tenant absent another lender mechanism")
can go to Joshua AFTER the deterministic fix, not before.

## Validation of this finding (read-only)
- `grep absence_adverse_to --include=*.py` → only `update_schema_305.py` (writer); zero pipeline reads.
- `derive_lp_state` (lease_coverage_305.py:843-882) and the element prompt (:228) carry `absence_severity`,
  never `absence_adverse_to`.
- `_HIGH_MATERIALITY_LPS = {"LP-27"}` (lease_exposure.py:76) → LP-27 Risk is floor-driven, lender-independent.
- `_build_model_exposure` passes `missing[:4]` unfiltered (lease_exposure.py:295-305); schema LP-27
  exposure_statement does not mention lender cure → "lender cure delay" is model-introduced.
- Polarity-class scan: 73/212 elements `absence_adverse_to != tenant` (script: ad-hoc over
  schemas/retail_lease_knowledge.json → issue_areas[*].expected_elements_305).
- No production file modified.
