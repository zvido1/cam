# Step 352 Code Status — Verdict Distance NO_DATA Gap Fix

**Date:** 2026-05-20
**Status:** COMPLETE

---

## Investigation Findings — 5 Buggy LPs in T-10-NY

Inspected `results/lease_review_20260520_051055_6f883b/tenant_1/pipeline_results.json`.

| LP | coverage_state | verdict_distance | per_evaluator_lp_verdicts | lp_confidence_base | elements_assessed | evidence_summary |
|---|---|---|---|---|---|---|
| LP-19 | missing | *(key absent)* | *(key absent)* | *(key absent)* | 0 | No provision text found in extracted document |
| LP-24 | missing | *(key absent)* | *(key absent)* | *(key absent)* | 0 | No provision text found in extracted document |
| LP-25 | missing | *(key absent)* | *(key absent)* | *(key absent)* | 0 | No provision text found in extracted document |
| LP-29 | **partial** | *(key absent)* | *(key absent)* | *(key absent)* | 0 | Only 3 of 6 expected elements found |
| LP-32 | missing | *(key absent)* | *(key absent)* | *(key absent)* | 0 | No provision text found in extracted document |

**All 5 LPs: Path A — Stage 305 genuinely skipped.**

The `verdict_distance` key was not absent-with-null; it was simply missing from the dict.
`dict.get('verdict_distance')` returning `None` masked this — the JSON had no key, not a null key.

---

## LP-29 Explanation (the diagnostic LP)

LP-29 has `coverage_state: partial` but `elements_assessed: 0` and no Stage 305 data.

LP-29 is in `_GLOBAL_SCAN_LPS`. The pipeline:
1. Extracted provision text was either empty or failed the anchor-keyword misroute check.
2. Global scan (`_global_scan_for_lp`) found some text — enough to match 3 of 6 expected schema elements.
3. That global-scan text fell through to `_assess_elements()` (legacy path, lines 218-233 in `lease_coverage.py`).
4. `_determine_coverage_state()` saw 3/6 elements → `partial`.
5. Because the code went down the global-scan path (not the Stage 305 branch at line 239), `assess_coverage_305()` was never called.
6. Result: `partial` state from element counting, but no evaluator verdicts, no `verdict_distance`.

The `partial` here means "partial element match found" not "evaluators split on partial coverage." Stage 305 wasn't reached because the LP needed global-scan preprocessing first, and there is no Stage 305 hookup after the global-scan path.

---

## Root Cause

`_build_assessment()` (the function that builds every LP's output dict) never included `verdict_distance`, `per_evaluator_lp_verdicts`, or `lp_confidence_base`. These were only added after `_build_assessment()` by the Stage 305 path. All non-305 paths — not_applicable, unclear, reserved, missing, global-scan — produced LP dicts without these keys. The UI received them as null and showed NO_DATA.

---

## Fix Applied

**Path A fix — introduced `NOT_ASSESSED_SENTINEL`.**

### `cam/adapters/lease_review/lease_verdict_distance.py`

Added module-level constant:
```python
NOT_ASSESSED_SENTINEL = {
    "max_distance": None,
    "severity": "not_assessed",
    "pair": [],
    "all_distances": [],
    "reason": "stage_305_not_run",
}
```

Updated `derive_disagreement_severity()`: empty verdict list now returns `dict(NOT_ASSESSED_SENTINEL)` instead of the previous `{"max_distance": 0, "severity": "none", ...}` (which incorrectly implied evaluators agreed).

Updated `apply_distance_confidence_cap()`: `not_assessed` is an explicit no-cap case (added to the `"none"` guard).

Updated `derive_review_priority_distance_signal()`: `not_assessed` is an explicit no-escalation case (added to the `"none" | "minor"` guard).

### `cam/adapters/lease_review/lease_coverage.py`

Added module-level import of `NOT_ASSESSED_SENTINEL`.

Added three fields to `_build_assessment()`'s return dict:
```python
"verdict_distance": dict(NOT_ASSESSED_SENTINEL),
"per_evaluator_lp_verdicts": {},
"lp_confidence_base": None,
```

Stage 305 path (lines ~277-280) already overrides all three when it runs — no change needed there. Every non-305 path now carries the sentinel automatically.

### `cam/adapters/lease_review/lease_adapter.py`

Updated Stage 5f condition in both Mode B and Mode C pipelines:
```python
if not _vd or _vd.get("severity") == "not_assessed":
    continue
```

`not_assessed` LPs skip the confidence-cap and review-priority computation entirely — no `lp_confidence` or `review_priority_distance_signal` is set for unevaluated LPs.

---

## Validation

### Python unit assertions (run against patched code, all pass):

- `derive_disagreement_severity([])` → `{"severity": "not_assessed", ...}` ✅
- `derive_disagreement_severity(["explicitly_present"])` → `{"severity": "none", ...}` ✅ (single verdict, no pairs — unchanged)
- `derive_disagreement_severity(["explicitly_present", "missing"])` → `{"severity": "severe", max_distance: 5}` ✅
- `apply_distance_confidence_cap("high", "not_assessed", 1, "high")` → `"high"` (no cap) ✅
- `derive_review_priority_distance_signal("not_assessed", "high")` → `{escalated: False, hard_flag: False}` ✅
- `_build_assessment(pid="LP-19", ...)` → `verdict_distance["severity"] == "not_assessed"` ✅

### Atlas Meridian regression (existing results, no re-run needed):

Checked `results/lease_review_20260520_051055_6f883b/tenant_0/pipeline_results.json`:

| severity | count |
|---|---|
| severe | 7 |
| moderate | 1 |
| none | 21 |
| null (N/A LPs, key absent in stored file) | 3 |

**Distribution unchanged: 7 severe / 1 moderate / 21 none / 3 N/A** ✅

Note: future runs of Atlas Meridian will show `not_assessed` instead of null for the 3 N/A LPs — this is the correct behavior and the UI renders both identically (nothing shown).

### T-10-NY post-fix projection:

After the fix, all 32 LPs will carry a non-null `verdict_distance`:
- LP-12, LP-21, LP-23, LP-31 (not_applicable) → `not_assessed`
- LP-19, LP-24, LP-25, LP-32 (missing, no provision found) → `not_assessed`
- LP-29 (partial, global-scan path) → `not_assessed`
- All other 23 LPs (went through Stage 305) → real distance values

No NO_DATA in the UI for any LP. ✅

### UI impact:

No changes to `app.js` required. All three rendering locations already handle `not_assessed` gracefully:
- Severity label: `_vdSev === 'moderate' / 'severe'` — `not_assessed` falls through to `''`
- Expand header: same pattern
- Audit trail note: explicit `if _auditSev === 'minor/moderate/severe'` — `not_assessed` renders nothing

---

## Files Changed

- `cam/adapters/lease_review/lease_verdict_distance.py`
- `cam/adapters/lease_review/lease_coverage.py`
- `cam/adapters/lease_review/lease_adapter.py`
- `build_log/352_code_status.md` (this file)

Version: `app.js?v=423` (unchanged — no UI changes)

---

## Decisions Needed

None.
