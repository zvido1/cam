# Step 375J — Code Status: 375E-DIR Routing-Boundary Counterfactual

**Date:** 2026-06-04  **Mode:** KEYLESS — no model calls, pure arithmetic over frozen artifacts.
**External-use pause:** still in force. 375J does not lift it.

---

## What was built

| File | What it does |
|---|---|
| `build_log/_375j_counterfactual.py` | The harness: loads 3 frozen inputs, replays policies A-E, writes outputs |
| `build_log/375J_results.json` | Machine-readable: 32 per-finding records + 6 Q/A blocks |
| `build_log/375J_results.md` | Human-readable: per-finding table + 6 pass/fail questions |

**READ-ONLY honored:** No edits to any production file, no routing change, no cam/core/, no Stage 5e edits.

---

## Keyless confirmation

This step is entirely keyless. No API calls, no model invocations. The harness:
1. Loads three frozen JSON files from disk.
2. Ports `classifyFindingType()` from `app.js:18032` in Python to derive `current_bucket`.
3. Applies policy routing functions (A–E) arithmetically.
4. Writes results.

Total model calls: **0**.

---

## Frozen findings file used for Stage 7 directional + verification columns

```
05 Lease Analyzer/results/lease_review_20260604_033046_52adbf/tenant_0/pipeline_results.json
  → field: cross_provision_findings
  → 26 directional_mismatch findings (Dir-01 through Dir-26)
  → 6 compound_risk findings (CRX-01 through CRX-06)
```

Verification strength column derived from: `finding.evaluator_agreement`
via `deriveDirectionalGovernanceSignal` port (≥3 agreed → ASSERT_SIGNAL → isVerified=True).
All 26 directional findings have `evaluator_agreement = "3-0"` → all ASSERT_SIGNAL → all verified.

---

## How `current_bucket` was derived

Python port of `classifyFindingType(finding, mode='c', {perspective: 'tenant', govSig: govSig})`
from `05 Lease Analyzer/static/app.js:18032`.

For synthesis findings (`_item_type = 'synthesis'`):
- `compound_risk` → always `"risk"` (guardrail #1, app.js:18041)
- `directional_mismatch` with `directionality = "tenant_unprotected"`, `perspective = "tenant"`:
  - `adverseTo = "tenant"` = perspective → check verification
  - `govSig = deriveDirectionalGovernanceSignal(finding)`: 3-0 → `"ASSERT_SIGNAL"`
  - `isVerified = (govSig === "ASSERT_SIGNAL")` = `True`
  - returns `"risk"` (line 18051)

**Result:** `current_bucket = "risk"` for ALL 32 cross_provision_findings in this run.
This matches the known behavior: this lease produces 26 verified adversary directional findings
+ 6 compound risk findings, all routing to Risk under the current classifier.

---

## Key numerical results

| Q | Result |
|---|---|
| Q1: Policy B bucket stability | **PASS** — 0 bucket changes across 6 wobbling LPs × 10 samples |
| Q2: Masquerade detection | 0 in assessed records; 18 implicit-floor findings in current routing |
| Q3: Findings without assessed materiality | 18/26 directional findings (source=not_eligible) |
| Q4: Policy A artificial instability | YES — all 6 wobbling LPs unstable under A, all stable under B |
| Q5: Policy C Needs-Review flood | 19/26 directional findings would NOT reach Risk under C |
| Q6: Policy E vs B divergence | 0 divergences under Stage 7 direction (verbatim non-divergence form applies) |

---

## LP-20 direction-instability flag

Per the spec, LP-20 is recorded as **materiality-stable / direction-unstable**:
- Materiality: all 10 Q3 samples = `low` (stable)
- 5e `gap_impact` across Q3 replays: `neutral`×8, `adverse`×1, `context_dependent`×1
- Stage 7 direction (frozen): `adverse` (tenant_unprotected)
- LP-20 is NOT used as a clean stability control anywhere in 375J.

---

## Policy E verbatim note (as required by spec)

`"Policy E is NOT a proposed production policy. It is a diagnostic control used to measure whether the adverse-direction gate is load-bearing on this artifact."`

Recorded in `375J_results.json` → `policy_E_note` and in every Q6 answer block.

---

## Queue triggered by 375J

375J Q1=PASS → no keyed 5e stabilization needed for this lease.

**Next steps (as specified):**
1. **375E-DIR implementation spec** — routing formula lock (provisional n=1):
   assessed high/medium + adverse = actionable_material tier; low = lower; defaulted/absent = source-labeled unassessed.
   375E-DIR must resolve the LP-05 axis question (Stage 7 direction vs 5e gap_impact as the adverse gate).
2. **375E-COV** — widen Stage 5e past the 8/32 gate + add `materiality_source` field to prevent
   silent floor masquerading; partly keyless. **Must precede production 375E-DIR release** (Q5 finding).
3. **375H-C** — keyed fixture matrix (present-hostile AND disproportionate-remedies clauses).
4. **Direction-sensitive schema repair** — gated behind 375H-C.

**DEPLOYMENT TRAP unchanged:** validated 375H repair findings must NOT enter lawyer-facing Risk
until 375E-DIR fixes routing.

---

## Decisions needed from Chat

1. Confirm 375J Q1=PASS triggers the 375E-DIR candidate lock (provisional n=1).
2. Confirm the LP-05 axis question (Stage 7 vs 5e gap_impact as adverse gate) is a 375E-DIR design decision.
3. Confirm 375E-COV is required before production release.
4. Queue ordering: 375E-DIR spec → 375E-COV → 375H-C → schema repair.
