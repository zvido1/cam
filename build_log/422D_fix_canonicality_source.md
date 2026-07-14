# Step 422D — Fix Canonicality Source for Extraction Completeness Gate
**Date:** 2026-07-14  
**Status:** COMPLETE

---

## Deferred Items

None. This step is self-contained and closes the stated bug class.

---

## Root-Cause (one line)

422C derived canonicality from `not meta.get("fallback_used", False)` — which answered "did we fall back?" instead of "are we in canonical mode?" The two coincide in Mode C today only because the canonical fail-closed guard (421B) prevents any fallback from completing. The moment `canonical=False` + primary succeeds: `fallback_used=False`, gate reads `is_canonical=True`, debug run aborts instead of degrading. Non-canonical degraded path was unreachable precisely when needed.

---

## Where Canonicality Is Now Recorded

### `cam/adapters/lease_review/lease_extract.py`

`meta["canonical"] = canonical` added at **both** return sites in `extract_provisions_single_doc()`:

**Success path** (line ~1035 after fix):
```python
"meta": {
    "model": actual_model,
    "provider": actual_provider,
    ...
    "fallback_used": fallback_used,
    "canonical": canonical,      # ← 422D
    "elapsed_sec": round(elapsed, 2),
    ...
}
```

**Stub/failure path** (all models failed, line ~992 after fix):
```python
"meta": {
    "model": "none",
    "provider": "none",
    ...
    "fallback_used": True,
    "canonical": canonical,      # ← 422D
    "elapsed_sec": round(elapsed, 2),
    ...
    "extraction_failed": True,
}
```

The field is always present regardless of outcome. `fallback_used` remains untouched and keeps its own meaning.

---

## Where the Gate Now Reads It

### `cam/adapters/lease_review/lease_adapter.py`

```python
# Before (422C):
_is_canonical = not meta.get("fallback_used", False)  # same flag the extractor sets

# After (422D):
# Read canonicality from the explicit field recorded by the extractor.
# Absent = legacy artifact; fail safe by treating as canonical.
_is_canonical = meta.get("canonical", True)
```

`fallback_used` is no longer read for canonicality. The two concepts are now orthogonal in code, not just in specification.

---

## The Bug That 422D Fixed (confirmed by test)

`test_canonical_false_fallback_false_not_misread_as_canonical` / `test_canonical_false_fail_missing_does_not_abort`:

```
Before fix: canonical=False + fallback_used=False
  → not meta.get("fallback_used", False)
  → not False
  → is_canonical=True
  → fail_missing → GateAbortError  ← WRONG: debug run aborted

After fix:  canonical=False + fallback_used=False
  → meta.get("canonical", True)
  → False
  → is_canonical=False
  → fail_missing → degraded flags   ← CORRECT
```

---

## Tests Executed — `test_422d_canonicality_source.py` (10 tests)

```
test_canonical_absent_treated_as_canonical PASSED
test_canonical_false_fail_missing_does_not_abort PASSED
test_canonical_false_fallback_false_not_misread_as_canonical PASSED
test_canonical_true_fail_missing_aborts PASSED
test_canonical_true_fallback_true_aborts PASSED
test_complete_extraction_canonical_no_abort PASSED
test_complete_extraction_non_canonical_no_abort PASSED
test_stub_failure_path_records_canonical PASSED
test_success_path_records_canonical_false PASSED
test_success_path_records_canonical_true PASSED
10 passed in 0.37s
```

**Key cases:**
- `test_canonical_false_fail_missing_does_not_abort` — the bug: would have raised GateAbortError before fix; passes after
- `test_canonical_true_fallback_true_aborts` — regression: `canonical=True + fallback_used=True` still aborts (old code would have misread this as non-canonical)
- `test_canonical_absent_treated_as_canonical` — legacy artifact: meta without "canonical" key → `meta.get("canonical", True)` → treated as canonical → aborts on fail_missing (fail-safe)
- `test_stub_failure_path_records_canonical` — all models exhausted → stub return includes `meta["canonical"]`
- `test_success_path_records_canonical_true` — primary succeeds → success return includes `meta["canonical"] = True`

**Full suite:** 210 passed (200 pre-422D + 10 new). No regressions.

---

## Test Author Note: Extractor Boundary Tests

`test_success_path_records_canonical_true` requires patching:
- `_get_adapter_for_provider` — provide a mock adapter that returns valid JSON
- `get_health_tracker` — provide a fresh mock with `is_available=True` (previous tests can corrupt the real singleton's google-degraded state)
- `lease_adapter._check_cancel` — `_check_cancel` is a local import inside the function body from `lease_adapter`, not a module-level attribute of `lease_extract`

The mock response must include at least one provision with all required fields and a valid status — the schema has `minItems` on the provisions array and `jsonschema.validate` enforces it.

---

## Files Changed

- `cam/adapters/lease_review/lease_extract.py` — `meta["canonical"] = canonical` at both return sites
- `cam/adapters/lease_review/lease_adapter.py` — gate reads `meta.get("canonical", True)` instead of `not meta.get("fallback_used", False)`
- `cam/adapters/lease_review/tests/test_422d_canonicality_source.py` — 10 new tests
- `build_log/422D_fix_canonicality_source.md` — this file
