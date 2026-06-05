# 375E-COV-A2 Code Status — Consequence-Independence Prompt Fix

**Date:** 2026-06-05
**Step:** 375E-COV-A2
**File changed:** `cam/adapters/lease_review/lease_finding_consequence.py`

## What Changed

### Root cause (from A1)
The old `_FINDING_SYSTEM_PROMPT` opened with:
> "Stage 7 cross-provision analysis has already established that a directional mismatch exists —
> the landlord's lease terms are adverse… The finding direction is FIXED. DO NOT reassess…
> Accept the adverse direction as a settled fact."

And `_build_finding_user_prompt` passed the Stage 7 finding title (headline) and detail verbatim:
> "Stage 7 finding (FIXED direction — adverse): Accelerated liability without limits"

Result: 5e ratified the framing instead of assessing consequence independently.
LP-11 proof: all 3 evaluators → harmful/high under A; all 3 → beneficial/medium under B (direction-redacted).
The absence of rent-acceleration remedy and mortgagee cure right is BENEFICIAL for the tenant —
the old prompt inverted the sign by construction.

### Fix applied (variant-B shape, Step 375E-COV-A2)

**System prompt (`_FINDING_SYSTEM_PROMPT`):**
- REMOVED: "Stage 7 direction is FIXED… accept the adverse direction as a settled fact."
- REMOVED: Definition of `harmful` as "The adverse finding creates meaningful practical risk…"
- ADDED: "INDEPENDENCE REQUIREMENT: Absence or structural incompleteness does NOT equal adverse by default."
- ADDED: "A structurally incomplete provision may have beneficial, neutral, or harmful use consequence depending on this specific tenant's operations. Assess consequence independently from any directional concern."
- ADDED: "For an operational tenant (warehousing, distribution, light assembly): a missing restriction typically means the landlord CANNOT restrict the tenant's activities — that is favorable, not adverse."
- ADDED: `_PRESENT_VERDICTS` constant (mirrors lease_use_impact.py) for element-verdict classification.
- Reordered definitions: beneficial → neutral → harmful (absence-first framing, not harm-first).

**User prompt builder (`_build_finding_user_prompt`):**
- REMOVED: `headline` (Stage 7 finding title — e.g., "Accelerated liability without limits")
- REMOVED: `detail` (Stage 7 explanatory text — often exposure-flavored)
- REMOVED: `"DIRECTIONAL FINDINGS TO ASSESS:"` header
- REMOVED: `"(Direction is FIXED as adverse/tenant_unprotected per Stage 7. DO NOT re-examine direction.)"`
- ADDED: `"LEASE PROVISIONS TO ASSESS (clause facts only):"` header
- ADDED: Coverage state in neutral language (e.g., "partial — 15 element(s) confirmed, 2 not confirmed")
- ADDED: `present_labels` — elements confirmed in the lease (from `element_verdicts`)
- ADDED: `missing_labels` — elements not confirmed in the lease (from `element_verdicts`)
- ADDED: `tenant_text` excerpt — relevant lease language if available (up to 400 chars)

**What is NOT changed:**
- `stage7_direction` still set to `"tenant_unprotected"` on the finding (provenance — stored, not fed to 5e)
- COV-A field schema unchanged: `use_consequence`, `materiality`, `use_consequence_source`,
  `materiality_source`, `assessment_scope`, `compound_consequence_source`
- Governance merge logic unchanged (`_merge_finding_verdicts`)
- Evaluator lineup unchanged
- Routing unchanged (still populate/record only — COV-B is later)
- `lease_use_impact.py` LP-scope prompt: **BYTE-IDENTICAL** — no changes made (confirmed via `git diff`)
- `cam/core/` — not touched

## Prompt diff (key fields removed / added)

| | Old (A1 variant A) | New (A2 / variant-B shape) |
|--|--|--|
| System framing | "direction is FIXED… accept adverse as settled fact" | "assess consequence independently; absence ≠ adverse" |
| Per-finding input | Stage 7 headline + detail (adversarial title) | Coverage state + element facts + lease text excerpt |
| direction_label fed to 5e | "FIXED direction — adverse: {headline}" | NOT FED (stored as stage7_direction provenance only) |
| Absence rule | (absent — defaults harmful by construction) | Explicit: "missing restriction = MORE freedom, not adverse" |

## LP-scope prompt (lease_use_impact.py)

Confirmed byte-identical — `git diff cam/adapters/lease_review/lease_use_impact.py` returns empty.
The finding-scoped path is the ONLY path changed.

## Canonical regression fixture (LP-11)

With the fix, LP-11 (Default & Remedies — thin gap: 15/17 elements present, missing
`rent_acceleration_remedy` + `mortgagee_guarantor_cure_right`) MUST return `beneficial` or at
minimum NOT `harmful/high` from clause facts alone. The absence of these remedies limits landlord
enforcement — that is net-positive for the tenant. Any future change that re-contaminates the
prompt will invert this back to harmful. Lock this as the A2 regression canary.

## Validation required (Tzvi runs)

Per 375E-COV-A2 instruction:
1. Re-run the keyed Meridian pipeline (19f9a7 shape)
2. Re-run `build_log/_375ecova_keyed_validate.py` on the fresh artifact
   - Criteria 1/2/3/5/6 must still PASS
   - Criterion 4 stays DEMOTED (cross-run synthesis confound — do NOT try to make it pass)
3. NEW exit criterion: LP-11 must NOT be harmful/high in the fresh run
4. Record the new directional distribution (harmful/neutral/beneficial/context_dependent counts)

## Decisions needed

None — fix is straightforward application of the proven variant-B shape from A1.

## Status

READY FOR TZVI'S KEYED RE-RUN. Code change committed (see git log). Not pushed.
Push gated on: keyed re-run passes + contamination signature gone (LP-11 ≠ harmful/high).
Then COV-A (771f1ef) + A2 fix push together.
