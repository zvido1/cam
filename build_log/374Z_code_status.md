# Step 374Z — Status: enforce C3 polarity correction + materiality-landmine neutralization (FIXTURE-GATED)
**Date:** 2026-06-03  **Scope:** backend coverage/exposure logic. **PROVISIONAL** pending broader-contract
validation (validation, not correctness, is what more leases add). Behavior change is authorized (directional
invariant repair), fixture-gated before this push (push = Railway deploy).

## What changed (consume `absence_adverse_to` as designed — 374W found it was dead data)
Operative policy C3, selected perspective (coverage stage defaults to **tenant**; see limitation note):
- `absence_adverse_to == selected_perspective` → missing MAY contribute as adverse coverage (unchanged).
- `absence_adverse_to == opposite_party` → missing MUST NOT contribute as adverse coverage; retained
  separately as a favorable/non-adverse candidate (NOT deleted, NEVER offsets Risk).
- `absence_adverse_to == null` / `both` / context-dependent → preserved as adverse/reviewable (conservative;
  this is why C3 beat C2 on the null-polarity LP-01 case — no auto-favorable flip).

### Sink 1 — `derive_lp_state` (lease_coverage_305.py)
Added a `perspective` param + polarity awareness: a missing element whose `absence_adverse_to == opposite`
is a *favorable absence* — excluded from the adverse-missing set and counted as satisfied/non-adverse for
the `all_non_adverse` (→ covered) check. So an LP whose only non-present elements are favorable absences is
`covered` for this perspective; genuinely adverse missing (e.g. LP-27 self-help) still drives partial/Risk.
Only one caller — `assess_coverage_305` (now passes perspective).

### Sink 1b — favorable data slot (`assess_coverage_305` + `lease_coverage.py`)
In the per-element loop, a clear opposite-polarity `missing` element is routed to
`favorable_or_non_adverse_absences` (with `element_id`, `element_label`, `absence_adverse_to`,
`absence_severity`, and **`cross_LP_coverage`** for the dependency caveat — e.g. LP-27 lender → LP-22 SNDA)
instead of `elements_missing`. `elements_missing` is therefore adverse-only downstream (state, materiality,
exposure prose, "Missing:" display all become polarity-correct in one move). The slot is propagated to the
assessment in `lease_coverage.py`. Data only — no UI bucket, no numeric Risk offset.

### Sink 2 — exposure `missing[0]` schema fallback (lease_exposure.py, the 374X residual)
`_build_schema_exposure` now reads `_perspective_adverse_missing(...)`, so the `"{missing[0]} is absent"`
fallback can never narrate a favorable absence as a gap.

### Sink 3 — materiality LANDMINE (lease_exposure.py)
New `_perspective_adverse_missing(assessment, perspective)` filters the `_HIGH/_MEDIUM_MATERIALITY_ELEMENTS`
string-match to perspective-adverse missing only. `_classify_materiality` takes `perspective` and uses it.
**Rule enforced: high materiality AMPLIFIES an adverse absence; it never REVERSES perspective polarity.** A
missing landlord-favorable remedy (rent acceleration / recapture) can never become a tenant Risk via a
materiality-string match — **even if its label is later normalized to the 305 label** (the latent landmine
374Y-Q flagged). Proven by fixture 5. The `_HIGH_MATERIALITY_LPS={"LP-27"}` floor is LP-level (legitimate —
LP-27 stays Risk via the self-help gap), left intact.

## Fixtures — `cam/adapters/lease_review/tests/test_polarity_374z.py` (6/6 PASS)
Run: `python -m cam.adapters.lease_review.tests.test_polarity_374z`
1. Missing tenant PROTECTION only → `partial`, adverse gap, Risk-eligible. **PASS**
2. Missing tenant BURDEN only → `covered`; retained as favorable candidate. **PASS**
3. Mixed LP (LP-27 shape) → `partial` (Risk on the protection gap); favorable burden retained, does NOT
   disappear and does NOT offset the Risk. **PASS**
4. Null-polarity missing → `partial`, stays conservative/reviewable, NOT auto-favorable. **PASS**
5. Exact-match high-materiality OPPOSITE-polarity absence (rent-acceleration string ALIGNED to its real
   LP-11 305 label, tenant perspective) → materiality `low`, NOT `high` → no tenant Risk. **PASS**
6. Cross-document dependency favorable candidate (LP-27 lender-cure) → favorable slot retains
   `cross_LP_coverage=[LP-22]` dependency caveat (not an unconditional advantage). **PASS**

## Exit criteria (like 374P) — ALL MET
Validated with the REAL post-374Z functions over stored runs (`build_log/_374z_validate_runs.py`,
governance-gated to missing-count-governed LPs):
- **030920:** ΔRisk=**+0**, ΔPriority=**+0**, genuine-adverse-leaving-Risk=**NONE**. Only flip: **LP-08
  partial→covered (Improvement→Addressed)**. LP-27: production=partial, new_derive=**partial** (stays Risk).
- **181402:** identical — ΔRisk=+0, ΔPriority=+0, none lost; LP-08 Improvement→Addressed; LP-27 stays partial/Risk.
- Matches the 374Y-Q C3 prediction exactly (LP-08 moves; LP-27 stays Risk; nothing else).
- No genuine adverse finding lost; favorable candidates retained (not deleted, not offsetting).
- `py_compile` clean on all three modules; modules import clean; CLI dry-run path (`_classify_materiality`
  default perspective) unaffected.

## Documented limitation / follow-up (not a blocker)
The **coverage stage runs perspective-blind** (`assess_coverage` has no perspective param; perspective
enters only at the exposure stage). `derive_lp_state` therefore defaults to **tenant** — correct for all
current runs and fixtures. Threading the real perspective into the coverage stage (for landlord/neutral
reviews) is a separate follow-up; until then a landlord-perspective coverage_state would use tenant polarity.
Flagged, out of 374Z scope.

## DID NOT bundle (per instruction)
- NO favorable-position UI / 5th bucket — only the `favorable_or_non_adverse_absences` data slot is added,
  for later measured surfacing + lawyer validation. Favorable items do NOT offset Risk.
- NO tie-break / Priority-Risks governance (separate measured work).

## Files
- `cam/adapters/lease_review/lease_coverage_305.py` (derive_lp_state + partition + return slot)
- `cam/adapters/lease_review/lease_coverage.py` (propagate favorable slot to assessment)
- `cam/adapters/lease_review/lease_exposure.py` (_classify_materiality perspective guard,
  _perspective_adverse_missing, schema-exposure missing[0] filter)
- `cam/adapters/lease_review/tests/{__init__.py,test_polarity_374z.py}` (6 fixtures)
- `build_log/_374z_validate_runs.py` (exit-criteria run validation)

## Provisional marker
PROVISIONAL — directional invariant is corrected and fixture-gated; broader-contract runs add validation
confidence (not correctness). app.js display surfaces (favorable slot rendering) are intentionally NOT added.

## Decisions Needed
None for this step. (Follow-ups: perspective threading into the coverage stage; favorable-position surfacing
decision fed by the accumulating `favorable_or_non_adverse_absences` data.)
