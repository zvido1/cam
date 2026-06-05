# Step 375E-COV-A — Code Status: G-cand Finding Consequence Provenance

**Date:** 2026-06-05
**Mode:** POPULATE/RECORD only. Code complete; keyless 0-drift proven; keyed run owed (Tzvi).
**External-use pause:** still in force. 375E-COV-A does not lift it.
**DEPLOYMENT TRAP:** still in force. 375H repair findings must NOT enter lawyer-facing Risk
until 375E-DIR routing fix is live.

---

## What was built

Implemented the G-cand finding-consequence provenance lane:

1. **`cam/adapters/lease_review/lease_finding_consequence.py`** (NEW)
   - G-cand identification: all `finding_type == "directional_mismatch"` findings
   - For already-assessed LPs (8): copies LP-scope `use_impact` to finding-level provenance
     via `_normalize_consequence` (handles pre-375M `gap_impact` field)
   - For unassessed LPs (18): runs finding-scoped 5e (3 parallel evaluators) with Stage 7
     direction as FIXED INPUT; evaluators assess use_consequence/materiality ONLY
   - For compound findings (6): attaches `compound_consequence_source: "not_assessed"`
   - Keyless mode (`use_profile=None`): copies already-assessed + marks unassessed as absent
     without model calls — enables 0-drift harness to run without API keys

2. **`cam/adapters/lease_review/lease_adapter.py`** (MODIFIED)
   - Added Stage 5e-F hook in `run_lease_coverage_only` (Mode C) AFTER Stage 7
     and BEFORE perspective leak detection
   - Non-fatal try/except block — failure does not break pipeline
   - Writes `finding_consequence_meta` to `result["_stage_data"]`
   - Gate: `FINDING_CONSEQUENCE_ENABLED and result.get("cross_provision_findings")`

3. **`build_log/_375ecova_drift_check.py`** (NEW)
   - Keyless 0-drift harness: loads frozen 52adbf, runs `assess_finding_consequence`
     with `use_profile=None`, checks all routing fields unchanged, provenance added

---

## Files changed

| File | Change | Type |
|------|--------|------|
| `cam/adapters/lease_review/lease_finding_consequence.py` | New module | NEW |
| `cam/adapters/lease_review/lease_adapter.py` | Hook in run_lease_coverage_only after Stage 7 | MODIFY |
| `build_log/_375ecova_drift_check.py` | Keyless 0-drift harness script | NEW |
| `build_log/375E-COV-A_results.md` | Results file | NEW |
| `build_log/375E-COV-A_code_status.md` | This file | NEW |

---

## Routing logic: confirmed NOT touched

- `_should_assess` in `lease_use_impact.py`: **unchanged**
- Risk/Needs Review/Improvement/Addressed bucket assignment logic: **unchanged**
- `cam/core/`: **not touched**
- Stage 7 synthesis logic: **not touched**
- Stage 5e LP-scope logic: **not touched**
- No routing field (`current_bucket`, `severity`, `verdict`, `finding_type`) is mutated
  by `assess_finding_consequence`

---

## Hard-guard confirmation

All COV-A scope guards confirmed NOT implemented:
- A-rail (threshold lane): NOT built — deferred hook only; will re-add at lease #2
- Present-hostile lane (375H-C): NOT built
- consequence_unassessed UI bucket / Needs Review subtype: NOT built (COV-B)
- CRX demotion: NOT built — CRX keeps current placement
- Any `cam/core/` change: none

---

## Field name corrections discovered during implementation

Two field name discrepancies between spec/summary and actual Stage 7 artifact:

| Expected (per spec/summary) | Actual (in pipeline_results.json) | Impact |
|---|---|---|
| `all_implicated_lps` | `implicated_lps` | Fixed in module — LP lookup uses correct field |
| `direction: "adverse"` | `directionality: "tenant_unprotected"` | G-cand gate uses `finding_type` only — no dependency on directionality value for gate logic |

Both fixed before first run. Drift check and all 4 validation checks pass.

---

## Key architectural facts confirmed

1. **`implicated_lps`** is the LP field name in Stage 7 findings (not `all_implicated_lps`)
2. **`directionality: "tenant_unprotected"`** is the adverse-direction field value on all 26
   directional findings; compound findings have `directionality: null`
3. **`current_bucket` is NOT stored** on findings in `pipeline_results.json`; it is derived
   downstream. Routing impact is structural, not artifact-field-comparable.
4. **All 26 directional findings are `finding_type == "directional_mismatch"`** — the G-cand
   gate on `finding_type` alone is correct and sufficient
5. **8 LPs with `use_impact`**: LP-03/05/10/14/16/20/26/32 — confirmed consistent with
   375N/375O analysis
6. **LP-20 `gap_impact: "neutral"`** (not "adverse" as suggested by one 375N read) — the
   frozen artifact has neutral/assert_weak. Normalizer correctly yields `use_consequence: "neutral"`

---

## 0-drift harness result

```
[PASS] 0 routing drift across all 32 findings
[PASS] Provenance fields present on all 26 directional findings
[PASS] compound_consequence_source='not_assessed' on all 6 compound findings
[PASS] Finding counts verified: 26 directional, 6 compound (matches 375J)

[PASS] 375E-COV-A DRIFT CHECK: ALL PASS -- safe to proceed with keyed run
```

---

## 375M Write-Path Check: OWED on keyed run

**Status: OPEN — carried forward from 375N/375O.**

The 375M commit (`a939b01`) changed the Stage 5e write path from `gap_impact` → `use_consequence`.
COV-A's keyed run will produce the first fresh post-a939b01 artifact for this check.

On keyed run, inspect `pipeline_results.json`:
```
coverage_assessment[LP-03|05|10|14|16|20|26|32].use_impact
```
Must have:
- `"use_consequence"` key present, value in `{"beneficial", "neutral", "harmful", "context_dependent"}`
- `"gap_impact"` key ABSENT

If `gap_impact` still appears post-deploy, there is a write-path bug in `lease_use_impact.py`.
COV-A's keyed run closes this check simultaneously with populating the 18 new findings.

---

## Queue after keyed run

1. Tzvi runs keyed pipeline → 375E-COV-A_results.md updated with 5e yield table
2. Close 375M write-path check from keyed artifact
3. Tzvi approves → push to main → Railway deploys
4. **375E-COV-B**: lawyer-facing landing (adverse+harmful/high-med→Risk; beneficial/low→Improvement;
   unassessed→Needs Review "consequence not assessed"; CRX stay-or-demote)
5. **375E-DIR**: vote≠severity routing redesign
6. **375H-C**: keyed fixture matrix → schema repair for present-hostile covered LPs

**DEPLOYMENT TRAP unchanged.**
