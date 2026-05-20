# Step 353 Code Status

**Date:** 2026-05-20
**SHA:** 52b496d
**Status:** COMPLETE

---

## Changes Made

### `cam/adapters/lease_review/lease_synthesis.py`

**Change 1 — New constant + updated comment block (lines 77–83)**

Replaced the stale comment that said "gpt-5.5 is used for Pass 2 only (short cluster prompt, succeeds)" with the accurate statement that gpt-5.5 fails all three Stage 7 paths. Added:

```python
_SYNTHESIS_PASS2_B_MODEL = "gpt-5.4"   # gpt-5.5 returns wrong format (dict not array)
```

**Change 2 — New `_EVALUATOR_LINEUP_PASS2` dict (lines 96–105)**

Added directly after `_EVALUATOR_LINEUP_PASS1`:

```python
_EVALUATOR_LINEUP_PASS2: Dict[str, dict] = {
    role: (
        cfg if role != "B" else {
            **cfg,
            "model": _SYNTHESIS_PASS2_B_MODEL,
            "label": "GPT-5.4",
        }
    )
    for role, cfg in EVALUATOR_LINEUP.items()
}
```

Verification: `_EVALUATOR_LINEUP_PASS2["B"]["model"] == "gpt-5.4"` ✓

**Change 3 — Pass 2 ThreadPoolExecutor uses `_EVALUATOR_LINEUP_PASS2` (line ~1872)**

```python
# BEFORE:
for role, ev_cfg in EVALUATOR_LINEUP.items()

# AFTER:
for role, ev_cfg in _EVALUATOR_LINEUP_PASS2.items()
```

**Change 4 (optional, also applied) — Improved error logging in `_call_pass2_evaluator._try_call`**

`unparseable response` error now includes a 200-char raw preview.
`expected list` error now includes the type name and dict keys on failure.
Makes future diagnosis faster without changing behavior.

---

## Static Verification

- `_EVALUATOR_LINEUP_PASS2["B"]["model"]` resolves to `_SYNTHESIS_PASS2_B_MODEL` which is `"gpt-5.4"` ✓
- Eval-A (Claude) and Eval-C (Grok) are unaffected — Pass 2 lineup mirrors Pass 1 structure ✓
- Fallback logic in `_call_pass2_evaluator` retained as-is — now dead code for Eval-B but harmless ✓
- No UI changes, no version bumps ✓

---

## Expected Outcome

Next run should show:
- No `Pass2 Eval-B: gpt-5.5 FAILED (RuntimeError)` in logs
- `[synth_debug] Eval-B: model=gpt-5.4` in Pass 2 debug line
- Pass 2 completes without fallback (~60–70s faster per tenant)

---

## Decisions Needed

None.
