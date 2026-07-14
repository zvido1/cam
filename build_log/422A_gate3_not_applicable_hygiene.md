# Step 422A — Gate 3 / NOT_APPLICABLE Schema Hygiene
**Date:** 2026-07-14  
**Status:** COMPLETE

---

## Root Cause

Gate 3 (structural prerequisite gate) was failing for LP-20, LP-21, LP-23, LP-31 on the
industrial sublease because the extraction module produced `status=AMBIGUOUS` for all missing
provisions — regardless of whether the miss was:

- (a) A genuine extraction failure (model couldn't parse / returned unparseable response), or
- (b) A provision structurally absent from this lease type (Exclusivity, Guaranty, Percentage
  Rent, Co-Tenancy are not present in industrial/warehouse leases by design).

These two conditions were indistinguishable in the artifact. Gate 3 logic could not tell
"evidence failure" from "inapplicable provision." This caused four industrial-sublease LPs
to hard-fail every Gate 3 check, masking what is actually a correct outcome.

---

## Changes Made

### 1. `cam/adapters/lease_review/lease_extract.py`

**Added:** `KNOWN_ABSENT_BY_DOC_TYPE` constant (adapter layer, not cam/core/):
```python
KNOWN_ABSENT_BY_DOC_TYPE: Dict[str, frozenset] = {
    "industrial": frozenset({"LP-20", "LP-21", "LP-23", "LP-31"}),
    "warehouse":  frozenset({"LP-20", "LP-21", "LP-23", "LP-31"}),
}
```
- Keyed to normalized property_type (lowercase, first token before comma).
- Document-type-scoped — not a global flat list. A retail lease with empty LP-23 is
  extraction failure, not NOT_APPLICABLE.
- Hard-fail behavior: unrecognized property_type → AMBIGUOUS with explicit explanatory
  note, never silently treated as no-known-absent.

**Added:** `_VALID_EXTRACTION_STATUSES` frozenset (includes NOT_APPLICABLE).

**Added:** `_classify_missing_stub(provision_id, deal_overview)` helper:
- Called only from the "provision not found in model output" paths (extraction succeeded
  but LP absent from results).
- NOT called from all-models-failed paths — those remain AMBIGUOUS unconditionally.
- Derives NOT_APPLICABLE from the known-absent registry; does not assert it directly.
- Returns (status, alignment_notes) — notes include basis, decision source, and type.

**Updated:** `_validate_extraction()` line ~105:
- Changed `"FOUND_BOTH", "TEMPLATE_ONLY", "TENANT_ONLY", "AMBIGUOUS"` tuple check
  to reference `_VALID_EXTRACTION_STATUSES` frozenset (adds NOT_APPLICABLE).

**Updated:** Missing-from-results paths (two locations):
- Dual-doc extraction path (~line 515): uses `_classify_missing_stub()`
- Single-doc extraction path (~line 904): uses `_classify_missing_stub()`

**NOT changed:**
- All-models-failed paths (~lines 482-510 and 869-901): still produce AMBIGUOUS.
  Rationale: when all models fail, no deal_overview is available; cannot assess
  document-type applicability; extraction failure is the correct classification.

### 2. `cam/adapters/lease_review/schemas/extraction_schema.json`

**Updated:** `status` field enum:
- Before: `["FOUND_BOTH", "TEMPLATE_ONLY", "TENANT_ONLY", "AMBIGUOUS"]`
- After:  `["FOUND_BOTH", "TEMPLATE_ONLY", "TENANT_ONLY", "AMBIGUOUS", "NOT_APPLICABLE"]`
- Description updated to explain semantic distinction.

### 3. `cam/adapters/lease_review/lease_coverage.py` — NOT changed

The coverage module already handles `not_applicable` as a coverage_state (line 117-131).
The bridge from extraction status to coverage applicability was already present via
`is_applicable()` text-clue matching. No changes needed.

---

## State / Schema Used

```
extraction status field values (post-422A):
  FOUND_BOTH      — clause found in both template and tenant
  TEMPLATE_ONLY   — clause in template, absent in tenant
  TENANT_ONLY     — clause in tenant, absent in template
  AMBIGUOUS       — extraction failure OR provision not found AND not known-absent
  NOT_APPLICABLE  — provision known-absent for this document type (derived, not asserted)
                    Conditions for NOT_APPLICABLE:
                      1. Extraction succeeded (obj is not None)
                      2. LP absent from extraction results
                      3. deal_overview.property_type normalizes to a key in KNOWN_ABSENT_BY_DOC_TYPE
                      4. LP ID is in the known-absent set for that type
                      5. Converse: LP has ANY text → would be in results → never reaches this path
```

---

## Document-Type Scoping

Registry key: `property_type` from `deal_overview`, lowercased, first token before comma.
- `"Industrial"` → `"industrial"` → hits registry
- `"Industrial, Mixed-Use"` → `"industrial"` → hits registry  
- `"Warehouse"` → `"warehouse"` → hits registry
- `"Retail"` → `"retail"` → NOT in registry → AMBIGUOUS with explicit note
- `""` (unknown) → AMBIGUOUS with explicit note

Known-absent set for `industrial`/`warehouse`:
- LP-20 Exclusivity
- LP-21 Guaranty  
- LP-23 Percentage Rent
- LP-31 Co-Tenancy

These provisions are absent by lease structure in industrial/warehouse leases, not by
extraction failure. On a retail lease, LP-23 empty = extraction failure = AMBIGUOUS.

---

## Derivation Constraint

NOT_APPLICABLE is derived from the registry, not asserted. An LP in the known-absent set
WITH tenant_text would already be present in extraction results with status FOUND_BOTH or
similar — it would never reach the missing-from-results path. The derivation constraint
is architecturally enforced: only absent provisions reach `_classify_missing_stub()`.

---

## Downstream Impact

Consumers that distinguish extraction statuses must now handle NOT_APPLICABLE:
- Gate 3 logic: NOT_APPLICABLE satisfies structural prerequisite check for industrial LPs
- Coverage assessment: existing `not_applicable` coverage_state path already handles this
- Reporting: NOT_APPLICABLE should not be counted as "evidence missing" in LP-07 analysis
- Stage 5 evaluators: NOT_APPLICABLE provisions should be excluded from evaluation queues

Consumers that only check for AMBIGUOUS (as a proxy for "something went wrong") will
correctly not trigger on NOT_APPLICABLE — these are distinct states.

---

## Test Criteria (manual verification, no automated test run)

| Scenario | Expected status |
|---|---|
| Industrial lease, LP-20 absent from extraction results | NOT_APPLICABLE |
| Industrial lease, LP-21 absent from extraction results | NOT_APPLICABLE |
| Industrial lease, LP-23 absent from extraction results | NOT_APPLICABLE |
| Industrial lease, LP-31 absent from extraction results | NOT_APPLICABLE |
| Industrial lease, LP-20 with tenant_text (in results) | FOUND_BOTH or TEMPLATE_ONLY |
| Retail lease, LP-23 absent from extraction results | AMBIGUOUS |
| Any lease, all models failed | AMBIGUOUS (extraction failure path, unchanged) |
| Industrial lease, LP-07 absent from extraction results | AMBIGUOUS (not in known-absent set) |
| Unknown property_type, LP-20 absent | AMBIGUOUS with explicit note |
| Unrecognized property_type (e.g. "Office"), LP-20 absent | AMBIGUOUS with explicit note |

---

## Deferred Issues

1. **Gate 3 logic itself** — Gate 3 still uses `status=AMBIGUOUS` as its gate-fail trigger.
   It needs to be updated to treat NOT_APPLICABLE as passing (or as a distinct non-failure).
   This is downstream of 422A and should be a separate targeted fix.

2. **Lease-structure-driven classification** — Some LPs may be absent for structural reasons
   not derivable from property_type alone (e.g., subleases vs. direct leases). A second basis
   dimension ("lease-structure-driven") may be needed in a future step.

3. **423 evidence assignment** — See 423_evidence_assignment_architecture_spec.md (pending).
   NOT_APPLICABLE provisions should be excluded from evidence selection.

4. **Schema migration for existing artifacts** — All 101 existing Gemini-primary extraction
   artifacts and 3 Atlas artifacts use the 4-value status enum. They are unaffected (their
   AMBIGUOUS values remain correct). New runs will produce NOT_APPLICABLE where applicable.

---

## Files Changed

- `cam/adapters/lease_review/lease_extract.py` — KNOWN_ABSENT_BY_DOC_TYPE, _classify_missing_stub(), _VALID_EXTRACTION_STATUSES, validation update, two missing-from-results paths
- `cam/adapters/lease_review/schemas/extraction_schema.json` — status enum + description
- `build_log/422A_gate3_not_applicable_hygiene.md` — this file
