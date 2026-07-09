# 414 — Fallback Integrity Implementation — Code Status

**Date:** 2026-07-08
**Commit:** `85a2489`
**Instruction:** Step 414 — implement the 413 fallback integrity design
**Result:** Complete. 52/52 tests green. No push (local-only, 27 commits ahead of origin).

---

## Files Changed

Three production files in `cam/adapters/lease_review/`, one new test file.

### `lease_coverage_305.py`

**Role C `own_chain` populated with grok-4.3 self-retry.**
Previously `own_chain: []` after grok-3 retirement (2026-05-15). Now:
```python
"own_chain": [(EVALUATOR_C_PRIMARY[0], EVALUATOR_C_PRIMARY[1], EVALUATOR_C_FALLBACK_LABEL)],
# grok-3 retired 2026-05-15; grok-4.3 (primary) doubles as the same-provider self-retry
```
This gives Role C one same-provider retry before crossing to the shared pool, matching the A and B buffer pattern. It is not a true different-model fallback — it is a second attempt at the same model, explicitly scoped to transient failures only.

**`_TRANSIENT_FAILURE_CLASSES` and `_is_transient_failure` helper (new).**
```python
_TRANSIENT_FAILURE_CLASSES = frozenset({"malformed_response", "empty_response", "truncation"})
def _is_transient_failure(reason: str) -> bool:
    return reason in _TRANSIENT_FAILURE_CLASSES
```
`truncation` added to the transient set: unclosed JSON can succeed on a clean retry (output budget honored differently on retry). Hard-class failures (`api_error`, `provider_unavailable`, `reasoning_exhaustion`, `unknown`) do not retry.

**Same-model-hard-skip guard in Phase 1 loop (new).**
When iterating `own_candidates` and the next candidate is the same model as the primary AND the current failure is hard-class, the loop breaks early. Hard outages don't recover on immediate re-call; the guard prevents wasting a call slot.

**Two distinct canonical abstain reason codes (new).**
Both are returned when `evaluator_fallback_mode == "canonical"` and Phase 1 is exhausted without success:
- `"hard_failure_no_retry_canonical_abstain"` — failure was hard-class; no retry fired; guard broke early.
- `"same_provider_retry_exhausted_canonical_abstain"` — retry(s) exhausted by transient failures; all own_candidates failed.

These replace a single ambiguous code, making the path traceable from the abstain record.

**Extended `evaluator_meta` dict.**
Added fields: `provider`, `abstained`, `abstain_reason`, `same_provider_retry_attempted`, `same_provider_retry_succeeded`, `fallback_class`.

**`validate_evaluator_chains` (new function).**
Called before the Stage 305 evaluation loop begins. Inspects each role's `own_chain`:
- **canonical mode:** always raises on empty `own_chain`. A declared `own_chain_empty_reason` does not grant exemption — it is informational only. The invariant: if canonical mode is requested and a role's chain is empty, refuse to proceed.
- **product/debug mode:** warns loudly and sets `run_config_degraded=True` in the return dict. Run proceeds.

Converts retirement-drift detection from "comment in source" to "runtime enforcement before first LP is evaluated."

**`collect_run_fallback_events` (new function).**
Three event types captured:
1. `"fallback"` — model substitution occurred; evaluation completed with a non-canonical model (`completed=True`).
2. `"abstain"` — canonical mode aborted evaluation for this role/LP; evaluation did not complete (`completed=False`, `abstained=True`).
3. `"all_failed"` — all candidates (own_chain + shared pool) exhausted; no evaluation (`completed=False`, `abstained` not set).

The abstain/all-failed scan is necessary because `lp_meta.fallback_used=False` on canonical abstain (no model substitution occurred — the model was simply not called), so the abstain path would have been invisible to a `fallback_used`-only scan. `run_degraded=True` is now set correctly for both substitution and abstain paths.

**`lp_meta._fallbacks` extended with `actual_provider`.**

### `lease_coverage.py`

Added `cfg: Optional[dict] = None` to the `assess_coverage` signature. Passes `cfg=cfg or {}` to `assess_coverage_305`. Required so that `evaluator_fallback_mode` in the run config reaches Stage 305.

### `lease_adapter.py`

Both Mode B and Mode C now:
1. Call `validate_evaluator_chains(lineup, mode)` before `assess_coverage`. Raises in canonical mode if any role's chain is empty.
2. Thread `cfg=cfg` through to `assess_coverage`.
3. Call `collect_run_fallback_events(coverage_result)` after coverage.
4. Write `run_degraded`, `degraded_reason`, `fallback_events` to the result dict.

---

## Test File

`cam/adapters/lease_review/tests/test_414_fallback_integrity.py` — new, 52 tests, 9 classes.

| Class | Tests | What it covers |
|---|---|---|
| `TestRoleCChainAfterFix` | 5 | Role C `own_chain` is populated; entry matches primary model and provider; FALLBACK_LABEL is a string |
| `TestTransientFailureHelper` | 7 | All transient classes return True; all hard classes return False; unknown returns False |
| `TestValidateEvaluatorChains` | 6 | Canonical raises on empty `own_chain` even with declared `own_chain_empty_reason`; product warns + sets `run_config_degraded`; populated chain passes both modes |
| `TestRoleCCanonicalHardFailAbstain` | 9 | Hard failure → no retry → `hard_failure_no_retry_canonical_abstain`; correct `completed=False`, `abstained=True`, `same_provider_retry_attempted=False` |
| `TestRoleCTransientRecovery` | 7 | Transient failure → retry succeeds → `run_degraded=False`; no fallback/abstain event emitted; `same_provider_retry_attempted=True`; `same_provider_retry_succeeded=True`; actual_model stays grok-4.3 |
| `TestAbstainReasonCodes` | 4 | Two distinct reason codes; hard path → hard code; retry-exhausted path → exhausted code; codes are distinct strings |
| `TestTruncationInTransientSet` | 3 | `truncation` is in `_TRANSIENT_FAILURE_CLASSES`; treated same as `malformed_response`/`empty_response` by `_is_transient_failure` |
| `TestCollectRunFallbackEvents` | 5 | Three event types captured; fallback event contains required fields; abstain event sets `completed=False`; empty result → empty events list |
| `TestRunDegradedLogic` | 6 | `run_degraded=True` on substitution; `run_degraded=True` on canonical abstain (no `fallback_used`); `run_degraded=False` on recovered transient; `degraded_reason` set correctly |

All 52 pass.

---

## Four Covered States

| State | Description | `run_degraded` | Events |
|---|---|---|---|
| **Recovered transient** | Grok fails (transient), retry succeeds. Primary model answered on second attempt. Stack stayed intact. | `False` | None. `same_provider_retry_attempted=True`, `same_provider_retry_succeeded=True` in provenance only. |
| **Exhausted transient / abstain-degraded** | Grok fails (transient), retry also fails. Canonical mode: abstain for this LP, no Gemini call. `abstain_reason = "same_provider_retry_exhausted_canonical_abstain"`. | `True` | `"abstain"` event in `fallback_events`. |
| **Hard-fail / abstain-degraded** | Grok fails (hard class). Same-model-hard-skip guard fires; no retry. Canonical mode: abstain immediately. `abstain_reason = "hard_failure_no_retry_canonical_abstain"`. | `True` | `"abstain"` event in `fallback_events`. |
| **Substitution degraded** | Grok fails, own_chain exhausted. Product mode: shared pool fires; Gemini substitutes. `is_fallback=True`, `actual_model=gemini-2.5-pro`. | `True` | `"fallback"` event in `fallback_events` with `requested_model`, `actual_model`, `fallback_class`, `same_provider_retry_attempted/succeeded`. |

---

## 413 Design Checklist — Implementation Coverage

| 413 Spec Item | Status |
|---|---|
| Role C same-provider retry (transient only) | Implemented — `own_chain` populated with grok-4.3 self-retry |
| Transient vs hard failure classification | Implemented — `_is_transient_failure` helper + frozenset |
| Same-model-hard-skip guard | Implemented — Phase 1 loop break on hard fail + same-model next candidate |
| Retirement-drift startup guard | Implemented — `validate_evaluator_chains` called before Stage 305 loop |
| Strict/permissive mode gate | Implemented — `evaluator_fallback_mode` key in run config, threaded from `lease_adapter.py` |
| Run-level degraded flag | Implemented — `run_degraded`, `degraded_reason`, `fallback_events` in result dict |
| Three-level provenance preserved | Implemented — extended `evaluator_meta` fields; abstain path emits same-retry fields |
| Two distinct abstain reason codes | Implemented — hard vs retry-exhausted paths |
| No cam/core/ changes | Confirmed — all changes in `cam/adapters/lease_review/` only |
| No Priority Exposure / Stage 7 changes | Confirmed — out of scope, untouched |

---

## What Was NOT Done (Deferred Per Instruction)

- **Temperature/config trace** — orthogonal dimension; separate investigation. Deferred behind this step by 413 design (Section 9).
- **Stage 5 stabilization** — deferred; needs fresh scoped instruction.
- **No push** — arc is 27 commits ahead of `origin/main`. All commits are local-only. Push requires explicit authorization.

---

## Decisions Needed / Open

None. Implementation complete per spec. Both candidate next steps (temperature/config trace, Stage 5 stabilization) require fresh scoped instructions from the architect before beginning.

---

*Code status: Step 414. Committed `85a2489`. 52/52 tests green. No push.*
