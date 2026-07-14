# Step 422C — Wire Extraction Completeness Gate into Live Pipeline
**Date:** 2026-07-14  
**Status:** COMPLETE

---

## Root-Cause (one line)

422B left `check_extraction_completeness()` callable but never called — an LP-07 with
`tenant_text=""` still walked straight into Stage 5 (`assess_coverage`) and produced a
confident `missing` verdict without any evidence.

---

## What Was Wired

### `cam/adapters/lease_review/lease_adapter.py`

Extraction completeness gate block inserted immediately after the existing `extraction_failed`
guard in `run_lease_coverage_only()`. The two guards are adjacent; same `GateAbortError`
exception type; same abort path.

```python
# ── Extraction completeness gate (422C) ────────────────────────────────────────
from cam.adapters.lease_review.lease_extract import check_extraction_completeness
_completeness_results = check_extraction_completeness(
    extraction["provisions"],
    extraction.get("deal_overview", {}),
)
_fail_missing = [r for r in _completeness_results if r["gate_status"] == "fail_missing"]
_is_canonical = not meta.get("fallback_used", False)

if _fail_missing:
    _failed_ids = [r["provision_id"] for r in _fail_missing]
    _failure_detail = [...]  # per-provision dict: provision_id, tenant_text_len, etc.

    if _is_canonical:
        raise GateAbortError(
            f"Extraction completeness failure: {len(_fail_missing)} required LP(s) "
            f"have missing evidence and are not classified NOT_APPLICABLE. "
            f"Failed LPs: {_failed_ids}. "
            "Cannot produce a valid legal analysis report from incomplete evidence. "
            f"Detail: {_failure_detail}"
        )
    else:
        # Non-canonical / debug: mark run degraded, do not abort
        run_metadata = cfg.setdefault("_run_metadata", {})
        run_metadata["run_degraded"] = True
        run_metadata["extraction_completeness_failed"] = True
        run_metadata["invalid_for_legal_analysis"] = True
        run_metadata["reason_code"] = "required_lp_missing_evidence"
        run_metadata["completeness_failures"] = _failure_detail
```

### Canonical flag

Uses `_is_canonical = not meta.get("fallback_used", False)` — the same flag the extractor
sets. No new flag introduced.

### NOT_APPLICABLE exemption

`check_extraction_completeness()` returns `gate_status="not_applicable"` for provisions
where extraction status is `NOT_APPLICABLE`. These are filtered out before `_fail_missing`
is constructed. LP-20/21/23/31 (industrial/warehouse known-absent) pass the gate.

---

## Canonical vs Debug Behavior

| Mode | `fail_missing` found | Behavior |
|------|---------------------|----------|
| Canonical (`fallback_used=False`) | Yes | `GateAbortError` raised; Stage 5 never runs |
| Canonical | No / only not_applicable | Gate passes; pipeline continues normally |
| Non-canonical (`fallback_used=True`) | Yes | `_run_metadata` degraded flags set; pipeline continues |
| Non-canonical | No | Gate passes; pipeline continues normally |

---

## fail_missing Representation

Each `fail_missing` item in `_failure_detail` is a dict:
- `provision_id` — LP ID
- `tenant_text_len` — length of tenant_text (expected 0)
- `extraction_status` — raw extraction status (expected `"AMBIGUOUS"`)
- `gate_status` — `"fail_missing"`
- `known_absent` — `False` (by definition; known-absent LPs are `not_applicable`, not `fail_missing`)
- `reason` — `"Required/applicable LP has empty tenant_text and is not classified NOT_APPLICABLE"`

The full detail list is embedded in the `GateAbortError` message string and in
`_run_metadata["completeness_failures"]` for non-canonical runs.

---

## Tests Added — `test_422c_completeness_gate_wired.py` (8 tests)

```
test_422c_completeness_gate_wired.py::TestCanonicalAbortOnMissingRequired::test_lp07_empty_raises_gate_abort_error PASSED
test_422c_completeness_gate_wired.py::TestCanonicalAbortOnMissingRequired::test_assess_coverage_not_called_on_canonical_failure PASSED
test_422c_completeness_gate_wired.py::TestCanonicalAbortOnMissingRequired::test_error_message_contains_failed_lp_ids PASSED
test_422c_completeness_gate_wired.py::TestKnownAbsentPassesGate::test_not_applicable_industrial_lps_pass_gate PASSED
test_422c_completeness_gate_wired.py::TestMixedCase::test_failure_list_excludes_not_applicable PASSED
test_422c_completeness_gate_wired.py::TestCompleteExtractionPassesGate::test_complete_extraction_does_not_abort PASSED
test_422c_completeness_gate_wired.py::TestCompleteExtractionPassesGate::test_assess_coverage_called_on_complete_extraction PASSED
test_422c_completeness_gate_wired.py::TestNonCanonicalDegradedPath::test_non_canonical_sets_degraded_flags PASSED
8 passed in 0.15s
```

**Critical test:** `test_assess_coverage_not_called_on_canonical_failure` — spy on
`cam.adapters.lease_review.lease_coverage.assess_coverage`; confirms
`assess_coverage.assert_not_called()` holds after GateAbortError is raised.

**Full suite:** 200 passed (192 pre-422C + 8 new). No regressions.

---

## Docs Updated

- `Docs/CAM_Current_State.md` — added "LATEST STATUS 2026-07-14" block covering 422A/B/C:
  NOT_APPLICABLE hygiene, wiring, Gate 3, live pipeline wiring, test counts, 423 spec reference.
- `Docs/NEW_THREAD_PROMPT.md` — phantom `422_evidence_assignment_architecture_spec.md`
  reference corrected to `423_evidence_assignment_architecture_spec.md` (done as part of
  422B/spec commit `813861a`).

---

## Honest State

The reporting layer is now defended:
- Canonical Mode C will **abort** before Stage 5 if any non-known-absent LP has empty evidence
- The fire extinguisher (`check_extraction_completeness`) is wired to the sprinkler head

The **evidence layer is still broken** exactly as 421C described. The key-terms table
(Tenant's Share 100%, Building's Share 45.79%) has 0 hits across LP-07 evidence contexts.
422A/B/C are the smoke detector and sprinkler. 423 is the wiring that actually fixes what
Gemini sends — but 423 is a spec only, not authorized for implementation.

---

## Deferred Items

1. **423 evidence assignment** — architectural spec at
   `build_log/423_evidence_assignment_architecture_spec.md`. Not authorized for implementation.
   First implementable slice: §3–§4 (canonical hashed source, span proposal, code-side offset
   resolution, three-state verification). Requires explicit go-ahead.

2. **Non-canonical callers** — `run_lease_coverage_only()` always calls
   `extract_provisions_single_doc(..., canonical=True)`, so `fallback_used` is always False
   in Mode C today. The non-canonical degraded path is wired for future debug harnesses or
   callers that produce fallback extractions.

---

## Files Changed

- `cam/adapters/lease_review/lease_adapter.py` — extraction completeness gate block
- `cam/adapters/lease_review/tests/test_422c_completeness_gate_wired.py` — 8 new tests
- `Docs/CAM_Current_State.md` — 422A/B/C status block + 421C block phantom ref fix
- `build_log/422C_wire_extraction_completeness_gate.md` — this file
