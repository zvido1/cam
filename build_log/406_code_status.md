# 406 Code Status

**Step:** 406 — Stage 5e all-partial widening diagnostic + chunking  
**Date:** 2026-07-07  
**Status:** COMPLETE — Gate 1 PASSED, Gate 2 COMPLETE (N=2 runs)

---

## What Changed

**File:** `cam/adapters/lease_review/lease_use_impact.py`

### Change 1 — `_WIDEN_PARTIAL_ELIGIBILITY` flag (default-off)

Added after `USE_IMPACT_ENABLED`:
```python
_WIDEN_PARTIAL_ELIGIBILITY: bool = False
```

The flag is default-off.  The current narrow behavior (>=50% non-present to admit a
partial LP) remains the production default.  The wide path is opt-in via
`cfg={"widen_partial": True}`.

### Change 2 — `_should_assess` widening

Added `widen_partial: bool = False` parameter.  The partial branch now:

1. Resolves element_verdicts (existing)
2. Excludes partial LPs with no element data in BOTH modes (guard applies before widening)
3. If `widen_partial=True`: admits all partial LPs with element data
4. If `widen_partial=False` (default): applies existing >=50% non-present threshold

The narrow path computation is unchanged — same threshold, same `_PRESENT_VERDICTS` set.
`missing` and `review_needed` are unconditionally eligible as before.

### Change 3 — `_chunk_list` helper

```python
def _chunk_list(lst: list, size: int) -> list[list]:
    return [lst[i:i + size] for i in range(0, len(lst), size)]
```

### Change 4 — `assess_use_impact` chunking

The function now:
- Reads `widen_partial = cfg.get("widen_partial", _WIDEN_PARTIAL_ELIGIBILITY)`
- Passes `widen_partial` to `_should_assess`
- Splits flagged LPs into chunks of `_CHUNK_SIZE=11`
- For each chunk: runs 3 evaluators in parallel (same thread-pool pattern as before)
- Accumulates per-evaluator lp_output dicts with `.update()` across chunks
- After all chunks: calls `_merge_verdicts` once on the full per-evaluator dicts

`_merge_verdicts` receives exactly the same data shape as before chunking — a list of
`{role, label, lp_output, completed}` dicts where `lp_output` is a complete LP→verdict
map.  `_merge_verdicts` does not know chunking occurred.

**Claimed-providers note:** `claimed_providers` set is reset fresh per chunk call
(local variable inside the chunk loop).  This is correct — each chunk is a new
evaluator call and needs its own provider-claim cycle.  Across chunks, the same
evaluator role re-claims the same provider (it is the only registered target after
filtering), which is stable.  No correctness change to provider-claim semantics.

### Unicode fix

Replaced `≤` characters in two comment/print locations with `<=` (ASCII) to avoid
`UnicodeEncodeError` on Windows cp1255 console.  No behavioral change.

---

## Scope Confirmation (from 406 instruction)

- `_merge_verdicts` governance rules (3-0→assert, 2-1→assert_weak, 1-1-1→context_dependent;
  materiality=most-conservative): **NOT TOUCHED**.
- `_SYSTEM_PROMPT`, consequence/materiality label sets: **NOT TOUCHED**.
- `classifyFindingType`, `sevTriage` (frontend routing): **NOT TOUCHED**.
- `cam/core/`: **NOT TOUCHED**.
- `max_output_tokens`: **NOT RAISED** — chunking is the fix.
- Priority Exposure: **NOT BUILT**.

---

## Gate 1 — PASSED

Synthetic fixture test (`gate1_test.py`), 18 checks, all green.

Key verified:
- Narrow `_should_assess` identical to pre-406 behavior
- Wide `_should_assess` admits all partial LPs with element data
- LP-13 (partial, no element_verdicts) excluded in BOTH modes
- `_chunk_list` no LP lost or duplicated; correct chunk counts
- Mock evaluator output merges correctly through `_merge_verdicts`
- `use_adjusted` field untouched by `_should_assess`

---

## Gate 2 — COMPLETE

Two runs on frozen Atlas Meridian artifacts (443e33 and 3131a1):

| Metric | Run-A (443e33) | Run-B (3131a1) |
|--------|---------------|---------------|
| Wide-eligible | 27 | 27 |
| Assessed | 27 | 27 |
| Unassessed (excluded) | 5 | 5 |
| Chunks | 3 (11/11/5) | 3 (11/11/5) |
| Wall time | ~83s | ~88s |
| Fallback | False | False |
| Truncation/parse errors | None | None |

See `build_log/406_stage5e_widening_yield.md` for full disaggregated results.

Summary:
- **Eligibility churn (wide gate): ZERO** — same 27 LPs both runs
- **Value churn: 3/27** (LP-05, LP-17, LP-21)
- **Yield newly-admitted: 18/20 decisive**, 2/20 value-churn, 0 abstain
- **Multi-finding check: 1:1 confirmed** on Atlas

---

## Commit SHA

`<SHA>` — to be filled after commit

---

## Deployment note

The widened path ships behind `_WIDEN_PARTIAL_ELIGIBILITY=False`.  Main is behaviorally
unchanged — production runs continue on the existing narrow gate until an explicit
decision to promote.  No push made per 406 spec.
