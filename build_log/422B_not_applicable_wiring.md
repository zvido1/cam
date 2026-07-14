# Step 422B — NOT_APPLICABLE Wiring Through Coverage and Gate 3
**Date:** 2026-07-14  
**Status:** COMPLETE

---

## Root-Cause Audit (re-read code, not 422A report)

422A added `NOT_APPLICABLE` as a schema state and added `_classify_missing_stub()` on the
missing-from-results path. But three independent no-ops nullified it:

**No-op 1: Wrong path.** `_classify_missing_stub()` fired only when an LP was absent from
the model's JSON output. Per `build_log/422_code_status.md` and confirmed by reading
`05 Lease Analyzer/_422_results/extraction_f7f64b5c4b08b55c.json`, the observed behavior
is that Gemini RETURNS LP-20/21/23/31 in results with `status=AMBIGUOUS, tenant_text=""`.
Those provisions never reach the missing-from-results path.

```python
# Confirmed from extraction JSON (f7f64b5c hash):
# LP-20: status=AMBIGUOUS, tenant_text=""
# LP-21: status=AMBIGUOUS, tenant_text=""
# LP-23: status=AMBIGUOUS, tenant_text=""
# LP-31: status=AMBIGUOUS, tenant_text=""
```

**No-op 2: No bridge.** `assess_coverage()` never reads `status`. It reads `prov.get("tenant_text")`
and branches on emptiness. `is_applicable()` uses text clues from the full document and has
no connection to extraction status. The 422A report's claim that "a bridge exists via
`is_applicable()`" was wrong. Verified by reading `lease_coverage.py:114-131`.

**No-op 3: Gate 3 not implemented.** The 422_code_status.md (line 281) explicitly states:
"Gate 3 rescoping mechanism (not yet implemented)". No Python function existed. Gate 3
checks were manual QC in the step 422 analysis, not enforced in cam/ code.

---

## Gate 3 Location

Gate 3 was NOT in `lease_coverage.py`, `lease_extract.py`, or `lease_adapter.py`. It was
a manual rejection criterion in the step 422 analysis script's QC table. The check was:
"zero stubs" (provisions with `status=AMBIGUOUS, tenant_text=""`). That gate was too strict
because it rejected known-absent industrial provisions as failures.

Gate 3 is now implemented as `check_extraction_completeness()` in `lease_extract.py` — a
callable that evaluators or adapter-layer QC can invoke to get per-provision gate status.

---

## Changes Made

### 1. `cam/adapters/lease_review/lease_extract.py`

**Added returned-empty reclassification loop** (after the missing-from-results fill-in,
at BOTH dual-doc and single-doc return paths):

```python
# Reclassify returned-empty AMBIGUOUS provisions: model returned the LP but
# with empty tenant_text and AMBIGUOUS status. Apply registry logic.
for p in obj["provisions"]:
    if p.get("status") == "AMBIGUOUS" and not (p.get("tenant_text") or "").strip():
        _status, _notes = _classify_missing_stub(p["provision_id"], _deal_overview)
        if _status == "NOT_APPLICABLE":
            p["status"] = "NOT_APPLICABLE"
            p["alignment_notes"] = _notes
```

This fires AFTER the model returns (obj is not None), so deal_overview is available.
All-models-failed stubs (returned early before this loop) remain AMBIGUOUS unconditionally.

**Added `check_extraction_completeness()`** — Gate 3 as a callable:

```python
def check_extraction_completeness(provisions, deal_overview) -> List[dict]:
    # Returns per-provision: gate_status = "pass" | "not_applicable" | "fail_missing"
    # "fail_missing": AMBIGUOUS + empty + NOT in known-absent set = evidence failure
```

### 2. `cam/adapters/lease_review/lease_coverage.py`

**Added Step 2a (extraction status bridge)** in `assess_coverage()`, between Step 2
(find provision) and Step 2b (misrouted-extraction guard):

```python
# ── Step 2a: Extraction status bridge ─────────────────────────────────────────
if prov and prov.get("status") == "NOT_APPLICABLE":
    _a = _build_assessment(
        pid=pid, area=area, coverage_state="not_applicable",
        applicability="not_applicable",
        evidence_summary=(
            prov.get("alignment_notes")
            or "Provision classified NOT_APPLICABLE by extraction layer."
        ),
        ...
    )
    assessments.append(_a)
    _emit(_a)
    continue
```

This bridge is the only code path that reads extraction `status`. It fires after Step 1
(text-clue applicability), so it only matters when `is_applicable()` returns "required"
or "applicable" but extraction tagged the provision NOT_APPLICABLE.

**Important finding:** LP-20 has `default_when_unclear="not_applicable"` in the lease_knowledge
schema. On most generic-text test inputs, `is_applicable("LP-20", ...)` returns "unclear",
and Step 1 (unclear → default) already produces `coverage_state="not_applicable"`. The bridge
is therefore redundant for LP-20 in most cases, but it is the ONLY path that uses the
extraction-layer provenance (alignment_notes) as the evidence_summary. For LPs that are
"required" (e.g. LP-01), the bridge is the only mechanism to produce not_applicable from
extraction status — text clues would never do it.

### 3. `cam/adapters/lease_review/tests/test_422b_not_applicable.py` — NEW FILE

23 tests. All executed; all pass.

---

## Tests Executed — Full Output

```
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestClassifyMissingStub::test_industrial_known_absent_lps_get_not_applicable PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestClassifyMissingStub::test_industrial_mixed_use_prefix_normalizes_correctly PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestClassifyMissingStub::test_industrial_non_known_absent_stays_ambiguous PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestClassifyMissingStub::test_retail_lp23_is_ambiguous PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestClassifyMissingStub::test_unknown_property_type_is_ambiguous PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestClassifyMissingStub::test_unrecognized_type_is_ambiguous_with_note PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestClassifyMissingStub::test_warehouse_known_absent_lps_get_not_applicable PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestReturnedEmptyReclassification::test_retail_lp23_empty_stays_ambiguous PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestReturnedEmptyReclassification::test_returned_empty_industrial_lp07_stays_ambiguous PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestReturnedEmptyReclassification::test_returned_empty_industrial_lp20_becomes_not_applicable PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestReturnedEmptyReclassification::test_returned_nonempty_lp20_not_reclassified PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestGate3ExtractionCompleteness::test_industrial_lp07_empty_fails_gate PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestGate3ExtractionCompleteness::test_industrial_lp20_ambiguous_empty_passes_as_not_applicable PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestGate3ExtractionCompleteness::test_mixed_provisions_correct_gates PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestGate3ExtractionCompleteness::test_not_applicable_status_passes_gate PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestGate3ExtractionCompleteness::test_provision_with_text_passes PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestGate3ExtractionCompleteness::test_retail_lp23_empty_fails_gate PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestGate3ExtractionCompleteness::test_unknown_doc_type_lp20_empty_fails_gate PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestCoverageBridge::test_ambiguous_status_does_not_trigger_not_applicable_bridge PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestCoverageBridge::test_not_applicable_status_yields_not_applicable_coverage PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestCoverageBridge::test_not_applicable_uses_provenance_from_alignment_notes PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestCoverageBridge::test_required_lp_with_text_does_not_short_circuit_via_bridge PASSED
cam/adapters/lease_review/tests/test_422b_not_applicable.py::TestAllModelsFailedStaysAmbiguous::test_all_models_failed_stubs_are_ambiguous PASSED
23 passed in 2.35s
```

## Full Regression

```
192 passed, 5 warnings in 1.89s
```

169 pre-existing + 23 new. No regressions.

---

## Derivation Constraint (now enforced)

The task required that LP presence overrides the registry as an EXPLICIT check, not just an
architectural assumption. It is now explicit in both:

1. The reclassify loop condition: `if p.get("status") == "AMBIGUOUS" and not (p.get("tenant_text") or "").strip()` — only fires on empty text. A provision with ANY tenant_text stays at its extraction status (FOUND_BOTH, TEMPLATE_ONLY, etc.) and is evaluated normally.

2. The Gate 3 check: `has_text = bool((p.get("tenant_text") or "").strip())` — if has_text → "pass", never not_applicable via gate.

3. Test `test_returned_nonempty_lp20_not_reclassified` confirms this explicitly.

---

## Gate 3 Status

Implemented. `check_extraction_completeness()` is callable from the adapter or QC tooling.

**NOT yet wired into the live pipeline.** `lease_adapter.py` does not call
`check_extraction_completeness()` after Stage 1. Wiring it there would require deciding
what to do on failure (abort / warn / log). That is a downstream decision — the gate
exists and is tested; the pipeline call site is deferred.

---

## Deferred Items

1. **Gate 3 pipeline call site** — `lease_adapter.py` does not yet call
   `check_extraction_completeness()`. Wiring it as a post-Stage-1 check is the
   next natural step. Behavior on "fail_missing" (abort or warn) is a Chat decision.

2. **423 evidence assignment** — `NOT_APPLICABLE` provisions should be excluded from
   evidence selection. Out of scope for 422B.

---

## Files Changed

- `cam/adapters/lease_review/lease_extract.py` — returned-empty reclassify loop (2 locations), `check_extraction_completeness()`
- `cam/adapters/lease_review/lease_coverage.py` — Step 2a extraction status bridge
- `cam/adapters/lease_review/tests/test_422b_not_applicable.py` — 23 new tests
- `build_log/422B_not_applicable_wiring.md` — this file
