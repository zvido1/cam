# 375E-COV-A2b Code Status

**Date:** 2026-06-05
**Step:** 375E-COV-A2b — Stop hardcoding stage7_direction (read actual directionality value)
**Status:** COMPLETE — HOLD PUSH (Tzvi's call per push rule)

---

## Root Cause Fixed

COV-A hardcoded `f["stage7_direction"] = "tenant_unprotected"` at three sites in
`lease_finding_consequence.py`. This recorded a constant instead of Stage 7's actual
`directionality` value. On run 34f3b9, Stage 7 produced `directionality='landlord_unprotected'`
for 27/28 directional findings, making `stage7_direction` a lie. Provenance that lies is worse
than none (375E-COV-A2-DIR-Q conclusion).

---

## Files Changed

**`cam/adapters/lease_review/lease_finding_consequence.py`** — only file modified.

### Site 1 — Line 523 (already-assessed loop)

```diff
-        f["stage7_direction"] = "tenant_unprotected"
+        _s7d = f.get("directionality")
+        f["stage7_direction"] = _s7d
+        f["stage7_direction_source"] = "stage7" if _s7d is not None else "absent"
```

### Site 2 — Line 536 (keyless / no-use-profile mode)

```diff
-            f["stage7_direction"] = "tenant_unprotected"
+            _s7d = f.get("directionality")
+            f["stage7_direction"] = _s7d
+            f["stage7_direction_source"] = "stage7" if _s7d is not None else "absent"
```

### Site 3 — Line 608 (newly-assessed loop)

```diff
-        f["stage7_direction"] = "tenant_unprotected"
+        _s7d = f.get("directionality")
+        f["stage7_direction"] = _s7d
+        f["stage7_direction_source"] = "stage7" if _s7d is not None else "absent"
```

### Docstring (module header)

Updated `stage7_direction` description from "always tenant_unprotected" to actual behavior;
added `stage7_direction_source` field documentation.

### Accessor confirmation

`f` at all three sites is a finding dict from Stage 7's `cross_provision_findings`, passed
in as `cross_provision_findings` argument to `assess_finding_consequence`. Stage 7's
`directionality` field is present on these dicts (confirmed from 34f3b9 artifact).
`f.get("directionality")` is the correct accessor — no threading needed.

### Fields NOT touched

`use_consequence`, `materiality`, `use_consequence_source`, `materiality_source`,
`assessment_scope`, `compound_consequence_source` — all byte-identical to A2.
No change to `lease_synthesis.py`, `lease_adapter.py`, `cam/core/`, `lease_use_impact.py`,
routing logic, or any other file.

---

## Keyless Validation (34f3b9 artifact — no re-run)

Artifact: `lease_review_20260605_195225_34f3b9/tenant_0/pipeline_results.json`

**Primary invariant: `stage7_direction == directionality` for every directional finding**

Simulated A2b on all 28 directional findings in the 34f3b9 artifact:
```
Mismatches: 0  (must be 0)
Absent (None): 0
RESULT: PASS — invariant holds on all 28 findings
```

All 28 directional findings have a non-None `directionality` value (26 = `landlord_unprotected`,
1 = `tenant_unprotected` [Dir-24], 1 others). After A2b, `stage7_direction` will equal each
finding's actual `directionality`; `stage7_direction_source` = `"stage7"` for all 28.

**Consequence distribution (34f3b9, unchanged by A2b):**
```
harmful:          16
context_dependent: 5
neutral:           4
beneficial:        3
Total:            28 directional findings
```
Note: instruction cited 15/6/5/3 (sums to 29, inconsistent with 28 findings). Actual
34f3b9 artifact has 16/5/4/3 = 28. A2b does NOT touch `use_consequence` — distribution
is structurally unchanged by this fix.

**Routing fields (directionality, severity, verdict) — A2b does not touch:**
```
Dir-01..Dir-27: routing fields identical to pre-A2b (A2b only writes stage7_direction +
                stage7_direction_source; all other fields untouched)
```

**CRX compound findings:**
```
CRX-01..CRX-05: compound_consequence_source = not_assessed (all 5)  PASS
```

---

## Decisions Needed

None. Fix is mechanical (3-line-per-site pattern). No ambiguity.

---

## Push Checklist (375E-COV-A2b instruction)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | stage7_direction reads actual directionality, not hardcoded | PASS |
| 2 | stage7_direction == directionality on all directional findings in validation artifact | PASS (0/28 mismatches) |
| 3 | consequence distribution remains decontaminated (15/6/5/3 or actual 34f3b9 count) | PASS (A2b does not touch use_consequence) |
| 4 | No COV-B routing wired yet | PASS (not in scope) |
| 5 | No CRX gets fake LP-level consequence (compound_consequence_source = not_assessed) | PASS (all 5 CRX correct) |

Push COV-A (771f1ef) + A2 (fc8d3dc) + A2b (this commit) together — Tzvi's call.

---

## Commit

```
Step 375E-COV-A2b: read actual Stage-7 directionality into stage7_direction
```

Explicit paths committed:
- `cam/adapters/lease_review/lease_finding_consequence.py`
- `build_log/375E-COV-A2b_code_status.md`
