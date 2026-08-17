# 407 Code Status

**Step:** 407 — Second-lease widened Stage 5e transfer test  
**Date:** 2026-07-07  
**Status:** COMPLETE — Part 0 (406 cleanup) committed; Parts 1-4 complete, both runs done

---

## Fixture

**Lease:** Atreca, Inc. EX-10.18 — 450 East Jamie Court, South San Francisco, CA  
**File:** `05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt`  
**Property type:** Lab/office (vs Atlas Meridian warehouse/industrial — genuine cross-type transfer test)  
**Jurisdiction:** CA  
**Work scope:** Populated (Exhibit C = Landlord's Work, private offices)  
**EDGAR:** accession 0001104659-19-041460, CIK 1532346, EX-10.18

---

## Part 0 — 406 Report Cleanup

Cleaned stray inline "Correction:" scratch line from `build_log/406_stage5e_widening_yield.md` §3.
Consequence breakdown rewritten as one coherent count (harmful=15, neutral=1, beneficial=0
decisive; LP-17/LP-21 = value-churn). No conclusion change.  
Commit: `ee5eb3a` — "406 report: clean stray inline correction in consequence breakdown"

---

## Run Configuration

**Entry point:** `run_lease_coverage_only(tenant_path, run_id, config={"widen_partial": True})`  
**Flag:** `_WIDEN_PARTIAL_ELIGIBILITY` (default-off, threaded via `cfg`) — unchanged from 406  
**Chunking:** `_CHUNK_SIZE=11` — unchanged from 406  
**Merge semantics:** `_merge_verdicts` unchanged  
**cam/core/:** NOT TOUCHED  
**Routing:** NOT TOUCHED

---

## Actual Cost Incurred

| Run | Wall time | API calls | Extraction | Coverage | Stage 7 |
|-----|-----------|-----------|------------|----------|---------|
| Run-A (lease_407_atreca_runA) | ~1392s (~23 min) | 86 | 204s (Gemini) | Parallel 3x per LP | 453s |
| Run-B (lease_407_atreca_runB) | ~1383s (~23 min) | 88 | 209s (Gemini) | Parallel 3x per LP | 441s |

Both runs: Stage 5e 2 chunks (11+8), no fallback, no truncation, no parse error.  
Total runtime: ~47 min combined (two sequential Mode C full-pipeline runs).

---

## Gate Results

**Gate 1:** N/A — no code change in this step; 406 Gate 1 remains the preflight for the widen flag.

**Gate 2:** COMPLETE, N=2  
- Wide eligible: 19/32 both runs (identical set)
- Eligibility churn: 0
- Assessed: 19/19 both runs
- Value churn: 0/19
- Newly-admitted yield: 8/8 decisive
- Multi-finding (coverage card): 1:1 confirmed both runs
- Compound findings not_assessed: 6 both runs (this is pre-existing, not introduced by widening)

See `build_log/407_second_lease_widened_5e_diagnostic.md` for full report.

---

## Commit SHA

`46fefaf`

---

## Harness

`build_log/run_407_gate2.py` — committed with this step (explicit git add, no git add .)

---

## Deployment Note

`_WIDEN_PARTIAL_ELIGIBILITY=False` remains the default. Main is behaviorally unchanged.
No push. The compound-finding `not_assessed` gap documented in §8 of the report is the
next design decision point.
