# 421B — Extraction Integrity Guard, Gemini Reliability Fix, Retroactive Audit

**Date:** 2026-07-13
**Step:** 421B
**Status:** Implementation complete (no push)
**Commit:** pending (see bottom)

---

## Part 1 — Retroactive Extractor Audit

**Scope:** All 159 `pipeline_results.json` files across `05 Lease Analyzer/_*_results/` directories.

### Extractor identity across 159 pipeline runs

| Extractor | Runs | % |
|-----------|------|---|
| gemini-3.1-pro-preview (primary) | 140 | 88.1% |
| gpt-5.5 (fallback position 3) | 8 | 5.0% |
| gpt-5.2 (fallback position 5) | 2 | 1.3% |
| gemini-2.5-pro (fallback position 2) | 1 | 0.6% |
| none (all failed, stub provisions) | 8 | 5.0% |

**Source:** `models_used.extractor` field, present in all 159 runs. Retroactive audit is fully possible with existing provenance.

**Key findings:**

1. **11.3% of runs used a non-primary extractor** (18/159). Of those, 8 produced stub provisions — no legal analysis.
2. **All non-Gemini fallbacks are silent.** `run_degraded=False`, `fallback_events=[]` in all 18 runs. A downstream consumer of `pipeline_results.json` cannot distinguish a gpt-5.5-extraction run from a Gemini-primary run without reading `models_used.extractor` or `_stage_data.extraction_meta`.
3. **gpt-5.5 extraction is high-variance.** Run 417/418c/run06 (gpt-5.5): 124,065 LP chars. Run 418c/run02 (gpt-5.5): 60,028 LP chars. Same document, different extraction volumes. gpt-5.5 runs at temperature=1 (`TEMPERATURE_ONLY_DEFAULT_MODELS`), making extraction non-deterministic.
4. **Gemini primary is deterministic at temp=0.** 6 consecutive Gemini-primary runs on atreca_eastjamie_southsf_lease.txt produced byte-identical extraction output (hash `ab80aafe9f7bce07c5c6113ceb5cd06d`, 110,153 LP chars). This is strongly evidenced but not proved — determinism may not hold across document types, Gemini API version changes, or load conditions.
5. **Extraction variance confirmed as a material wobble source.** 418c showed LP-07 `proportionate_share_calculation` flipped between `explicitly_present` and `missing` purely because gpt-5.5 extraction included the first-page percentage table while Gemini did not. 12 of 32 LPs in the 417 baseline had extraction-driven instability (Step 419).

### Same-bug-class as Step 414

The 414 evaluator guard fixed silent substitution of evaluator models. This step applies the same fix to extraction: a canonical Mode C run must not silently use a fallback extractor. The bug class is identical; the surface is different.

---

## Part 2 — Canonical Extraction Fail-Closed Guard

**File changed:** `cam/adapters/lease_review/lease_extract.py`

**New exception:** `ExtractionIntegrityError(message, errors, attempt_chain)`

**New parameter:** `extract_provisions_single_doc(..., canonical=True)`

**Guard logic:** In canonical mode, when `chain_idx > 0` is about to be entered (primary Gemini failed), raise `ExtractionIntegrityError` immediately. The fallback chain is never attempted.

**Propagation in lease_adapter.py:**
- `ExtractionIntegrityError` is caught in `run_lease_coverage_only()` and re-raised as `GateAbortError` with a descriptive message.
- The run hard-aborts. No coverage assessment is generated. No report is emitted.

**Rule:** A run whose entire evidence base came from a fallback extractor must never be indistinguishable from a clean Gemini-primary run.

---

## Part 3 — Stub-Provision Fail-Closed

**File changed:** `cam/adapters/lease_review/lease_adapter.py`

**Guard:** After extraction, if `meta.get("extraction_failed") is True`, raise `GateAbortError` before Stage 5. This closes the path where all extractors fail (non-canonical/debug mode) and the pipeline continues with empty `tenant_text` stubs, producing a legal analysis report from no evidence.

**This path cannot be reached in canonical mode** (the fail-closed guard in Part 2 fires first), but the guard is present for defence-in-depth and for non-canonical/debug mode callers.

---

## Part 4 — Guard-First Tests

**File:** `cam/adapters/lease_review/tests/test_421b_extraction_integrity.py`

**10 tests across 6 classes:**

| Class | Tests | What it proves |
|-------|-------|----------------|
| `TestCanonicalFailClosed` | 3 | Guard fires on primary failure; no error when primary succeeds; fallback chain runs in non-canonical mode |
| `TestStubProvisionGuard` | 1 | `extraction_failed=True` flag present on stub return; all stubs have empty `tenant_text` |
| `TestAttemptChain` | 2 | Success and failure both recorded in `attempt_chain` |
| `TestRawFailureCapture` | 1 | `raw_response_preview` and `raw_response_len` stored on JSON parse failure |
| `TestEvidenceHashes` | 1 | `primary_model`, `primary_provider`, `extraction_attempt_chain` present in meta |
| `TestTokenCeiling` | 1 | `EXTRACTION_MAX_TOKENS_SINGLE > 40,000` |
| `TestExtractionIntegrityErrorShape` | 1 | Exception carries `errors` and `attempt_chain` attributes |

**Results:** 10/10 pass. 84/84 existing 414/416 tests still pass.

---

## Part 5 — Gemini Reliability Fix: Token Ceiling

**File changed:** `cam/adapters/lease_review/lease_extract.py`

```
EXTRACTION_MAX_TOKENS_SINGLE = 32_000  →  65_000
```

**Rationale:** 6 successful Gemini-primary runs on the Atreca document produced 27k–31k output tokens. The prior ceiling of 32,000 left <10% headroom. A truncation event at 32,000 tokens would produce a partial JSON response, trigger `_repair_truncated_json()`, and if repair failed, cause the canonical fail-closed guard to fire — aborting the run.

The new ceiling (65,000) provides >2× headroom over the observed maximum. This materially reduces the probability of Gemini truncation causing extraction failure.

**Gemini structured output (`response_mime_type`, `response_schema`) — deferred.**

The Google adapter (`cam/core/provider_router.py`) is outside `cam/core/` modification scope. Structured output parameters would need to pass through `ModelTarget` or a new adapter-layer wrapper. Neither was scoped in this step. The token ceiling is the higher-leverage immediate fix: truncation is the primary Gemini failure mode.

**Reliability impact:** Without structured output enforcement, Gemini can still return malformed JSON. The raw failure capture (Part 6) will expose this when it occurs. Canonical fail-closed will abort rather than silently produce a garbage report.

---

## Part 6 — Raw Failure Capture

**File changed:** `cam/adapters/lease_review/lease_extract.py`

On JSON parse failure in `extract_provisions_single_doc()`, the error dict now includes:

```python
{
    "model": model_name,
    "error": f"json_extract: {ve}",
    "raw_response_len": len(raw),
    "raw_response_preview": repr(raw[:2000]),  # first 2k chars, escaped
}
```

This is persisted to `meta["errors"]`, which flows to `_stage_data.extraction_meta.errors` in `pipeline_results.json`. Future debugging of extraction failures no longer requires re-running the pipeline.

---

## Part 7 — Google Adapter Config Integrity (scope note)

`_check_generation_integrity()` (Step 416) covers Anthropic, OpenAI, and xAI adapters. The Google adapter is not covered.

**Findings:**
- Google adapter at `cam/core/provider_router.py:GoogleGenAIAdapter.call()` transmits only `temperature`, `max_output_tokens`, and `system_instruction` to the genai client. No `top_p`, `top_k`, `seed`, `response_mime_type`, `response_schema`.
- Extraction uses `temperature=0.0`. Gemini accepts this at the API level (confirmed by 6+ successful runs). No silent drop observed.
- `_check_generation_integrity()` cannot be called from `lease_extract.py` without a cam/core/ change.

**Decision:** Google extraction integrity is not asserted at the `_check_generation_integrity()` level. The extraction attempt chain now records every attempt with outcome, which gives post-hoc visibility into Gemini call success/failure. A future step should either extend ModelTarget to carry response_mime_type or add a parallel assertion path for the Google adapter.

**Governance question recorded as open:** single-model semantic evidence governance — the same Gemini call both segments AND selects which text represents each LP. There is no independent verification that Gemini selected the correct text. Evidence correctness is structurally unverifiable within a single-provider extraction call. This is a design-level open question, not a bug.

---

## Part 8 — Evidence Hash in Provenance

**Files changed:** `cam/adapters/lease_review/lease_adapter.py`, `lease_extract.py`

### New top-level fields in `pipeline_results.json` (Mode C)

| Field | Type | Description |
|-------|------|-------------|
| `source_document_hash` | str (SHA-256 hex) | Hash of full parsed document text. Identifies the input document uniquely. |
| `extraction_output_hash` | str (SHA-256 hex) | Hash of all LP `tenant_text` fields concatenated. Identifies the extraction output. |
| `extraction_provider` | str | Provider that produced the extraction (e.g., `"google"`). |
| `extraction_model` | str | Model that produced the extraction (e.g., `"gemini-3.1-pro-preview"`). |
| `extraction_primary_provider` | str | Intended primary provider (always `"google"`). |
| `extraction_primary_model` | str | Intended primary model (always `"gemini-3.1-pro-preview"`). |
| `extraction_fallback_used` | bool | True if a fallback extractor was used (will be False in canonical runs). |
| `extraction_degraded` | bool | Alias of `extraction_fallback_used`. |
| `extraction_attempt_chain` | list | Per-model attempt records with outcome strings. |
| `extraction_failure_reason` | str/null | Populated if extraction aborted; null on success. |

### Per-LP field in `coverage_assessment` items

| Field | Type | Description |
|-------|------|-------------|
| `tenant_text_hash` | str (SHA-256[:16]) | 16-char hex digest of `tenant_text` for this LP. Allows downstream comparison: if two runs share the same `tenant_text_hash` for an LP but produce different verdicts, the difference is panel variance, not extraction variance. |

### New meta fields in `extraction_attempt_chain` items

```json
{"model": "gemini-3.1-pro-preview", "provider": "google", "outcome": "success"}
{"model": "gemini-3.1-pro-preview", "provider": "google", "outcome": "exception: TimeoutError"}
{"model": "gemini-3.1-pro-preview", "provider": "google", "outcome": "json_parse_failed: ..."}
```

---

## Part 9 — Extraction Quality Caveat (Stability ≠ Correctness)

Gemini extraction is deterministic at temperature=0 on the Atreca document (6/6 byte-identical outputs). This means:

- **Extraction stability does not imply extraction correctness.** A deterministic wrong segmentation produces the same wrong report every time. The Atreca LP-07 case (first-page percentage table absent from some extraction runs) shows that Gemini can deterministically omit material text from the extraction output. A canonical run that freezes on a Gemini extraction that misses LP-07's percentage table will consistently mis-report LP-07 `proportionate_share_calculation` as `missing`.

- **The correct framing:** a canonical (Gemini-primary, unmodified) extraction is the reference baseline for this pipeline. Reports are valid relative to that baseline. They are not validated against independent ground truth.

- **Implication for the patent record:** CAM's value claim is comparison fidelity (same extraction → same report, different extraction → detectable difference). The `tenant_text_hash` field per LP makes this claim verifiable: two runs with identical hashes for an LP that differ in verdict are unambiguously panel variance, not extraction variance.

---

## Part 10 — Single-Model Semantic Evidence Governance (Open Question)

**Recorded as open, not resolved.**

The current architecture uses a single Gemini call to both segment and select evidence for 18+ LPs from a single document. There is no independent verification layer:
- No second model confirms the LP-text assignment
- No structural check confirms completeness (full-text coverage audit, not implemented)
- The extraction schema captures `tenant_text` per LP but not "text that was considered and excluded"

This is a known limitation of single-provider extraction. The architecture makes it structurally unverifiable whether Gemini selected the correct text for each LP or whether it missed material clauses. The fail-closed guard ensures that when this uncertainty is compounded by a fallback substitution, the run aborts rather than silently proceeding — but it does not address the correctness question for a successful primary run.

**Deferral rationale:** Resolving this requires either (a) multi-model extraction consensus, (b) full-text coverage verification, or (c) human review of extraction output. None of these are scoped for this step.

---

## Part 11 — Docs Updated

**`Docs/CAM_Current_State.md`:** New header block added summarizing Step 421B.
**`Docs/Patent_Current_State.md`:** Not updated — 421B is a pipeline integrity fix, not a patent-record finding. The claim "same input → same output" is strengthened by the fail-closed guard, but this is an architectural improvement, not a new capability to disclose.

---

## Implementation Summary

| Part | Status | Files changed |
|------|--------|---------------|
| 1. Retroactive audit | ✅ Done | (this file) |
| 2. Canonical fail-closed guard | ✅ Done | `lease_extract.py` |
| 3. Stub-provision kill | ✅ Done | `lease_adapter.py` |
| 4. Guard-first tests | ✅ Done | `tests/test_421b_extraction_integrity.py` |
| 5. Token ceiling (32k → 65k) | ✅ Done | `lease_extract.py` |
| 5. Gemini structured output | ⏸ Deferred | cam/core/ out of scope |
| 6. Raw failure capture | ✅ Done | `lease_extract.py` |
| 7. Google adapter integrity | ⏸ Partial | Documented; assertion deferred |
| 8. Evidence hashes | ✅ Done | `lease_adapter.py`, `lease_extract.py` |
| 9. Extraction quality caveat | ✅ Done | (this file) |
| 10. Single-model governance Q | ✅ Done | (this file, recorded open) |
| 11. Docs update | ✅ Done | `Docs/CAM_Current_State.md` |
| 12. Tests run | ✅ 10/10 pass, 84/84 regression clear | |
| 13. Commit | See below | |

---

## Test Results

```
cam/adapters/lease_review/tests/test_421b_extraction_integrity.py  10/10 pass
cam/adapters/lease_review/tests/test_414_fallback_integrity.py     52/52 pass (regression clear)
cam/adapters/lease_review/tests/test_416_config_integrity.py       32/32 pass (regression clear)
```

Total: 94 tests run, 94 pass.

---

*Step 421B implementation. No push. Commit: see git log.*
