# 376 Code Status — Remove LP-27 hardcoded directional sign override

**Date:** 2026-06-05
**Step:** 376
**Status:** COMPLETE — pushed to main

---

## File Changed

**`cam/adapters/lease_review/lease_synthesis.py`** — only file modified.

## Diff Applied

```diff
-# Maps (lp_id, finding_type) → correct directionality label.
-# Perspective must not flip the factual label of who is exposed.
-_DIRECTIONALITY_MAP: Dict[tuple, str] = {
-    ("LP-27", "directional_mismatch"): "tenant_unprotected",
-}
-
-# Maps (lp_id, finding_type) → correct affected_party label.
-_AFFECTED_PARTY_MAP: Dict[tuple, str] = {
-    ("LP-27", "directional_mismatch"): "tenant",
-}
+# 376: LP-27 hardcoded sign override REMOVED. Directional sign must come from governed
+# evaluator assessment (per-evaluator exposed_party), never from a constant. Emptied
+# rather than deleted so _normalize_directionality stays a structural no-op (reversible,
+# and still available if a FUTURE governed normalization rule is ever added). Measured
+# effect: 34f3b9 Dir-24 corrects tenant_unprotected→landlord_unprotected (was contradicting
+# a 3-0 landlord consensus); 52adbf/19f9a7 LP-27 directional unchanged (evaluators already
+# said tenant). See build_log/376_chat_instruction.md.
+_DIRECTIONALITY_MAP: Dict[tuple, str] = {}
+
+_AFFECTED_PARTY_MAP: Dict[tuple, str] = {}
```

`_normalize_directionality()` function body and both call sites in `run_synthesis` —
**untouched**. With empty maps the function is a structural pass-through no-op.

Not touched: `_build_pass2_directional_findings` sign derivation (~line 1941),
`lease_finding_consequence.py`, COV-A/A2/A2b fields, `cam/core/`, routing.

---

## Unit Test Results (keyless, no API key)

```
PASS: both maps are empty {}
PASS: LP-27 directional finding NOT mutated (landlord_unprotected preserved)
PASS: tenant-facing LP-27 finding also passed through unchanged
PASS: non-LP-27 finding untouched
PASS: empty list passes through

ALL 5 ASSERTIONS PASS — _normalize_directionality is a pure pass-through
```

Test fixture used:
```python
{"finding_id": "Dir-24", "finding_type": "directional_mismatch",
 "implicated_lps": ["LP-27"], "directionality": "landlord_unprotected",
 "affected_party": "landlord"}
```
→ NOT mutated to tenant_unprotected/tenant after fix. Assertion confirmed.

---

## Measured Correction (from 34f3b9 artifact)

| Finding | LP | Old directionality | Correct (evaluator consensus) | Fixed? |
|---------|----|--------------------|-------------------------------|--------|
| Dir-24 | LP-27 | tenant_unprotected (map forced) | landlord_unprotected (3-0 landlord) | YES |

52adbf Dir-22 / 19f9a7 Dir-20 (LP-27): evaluators said tenant 3-0 — map was coincidentally
correct, now evaluator-derived value flows through naturally.

---

## Commit & Push

Committed as part of push bundle: COV-A (771f1ef) + A2 (fc8d3dc) + A2b (8de0d74) + 376.
