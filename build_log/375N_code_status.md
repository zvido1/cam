# Step 375N — Code Status: COV Gate-Widening Diagnostic

**Date:** 2026-06-05  **Mode:** READ-ONLY / keyless. No code changed, no model called.
**External-use pause:** still in force. 375N does not lift it.

---

## What was done

Keyless diagnostic answering Q1–Q6 from `375N_chat_instruction.md`. All reads were
from frozen artifacts on disk; no pipeline runs were triggered.

### Files read (all read-only)

| File | What was read for |
|---|---|
| `build_log/375N_chat_instruction.md` | Instruction |
| `build_log/375J_results.json` | Q1 (not-eligible count), Q3 (direction split), Q6 (policy bucket projections) |
| `build_log/375H_code_status.md` | Q4 (375H Part A+B findings), Q5 (LP-09 schema defect characterization) |
| `05 Lease Analyzer/results/lease_review_20260604_033046_52adbf/tenant_0/pipeline_results.json` | Q1 (coverage_states via element_verdicts), Q2 (threshold sensitivity), Q3 (cross_provision_findings direction), Q4/Q5 (LP-09 coverage_state + covered_unfavorable_adverse_to + caution_signals + element_verdicts), Q6 (volume projections) |
| `cam/adapters/lease_review/lease_use_impact.py` | `_should_assess` exact gate logic |

### Normalizer used

All `use_impact` values from 52adbf were read through `_normalize_use_consequence` (Python,
375M contract):
- If `use_consequence` key present → use it
- Else map `gap_impact`: `"favorable"` → `"beneficial"`, `"adverse"` → `"harmful"`, others unchanged

The frozen artifact carries `gap_impact` (pre-375M write). The normalizer correctly translates:
- LP-03: `gap_impact="adverse"` → `"harmful"`, materiality=high, confidence=assert
- LP-05: `gap_impact="favorable"` → `"beneficial"`, materiality=medium, confidence=assert
- LP-10: `gap_impact="adverse"` → `"harmful"`, materiality=high, confidence=assert
- LP-14: `gap_impact="adverse"` → `"harmful"`, materiality=medium, confidence=assert
- LP-16: `gap_impact="adverse"` → `"harmful"`, materiality=high, confidence=assert
- LP-20: `gap_impact=None` (was abstain in use_aware_governance); use_impact present with
  `gap_impact="adverse"` normalized → `"harmful"`, but materiality=low, confidence=assert_weak.
  (NOTE: 375J records LP-20 as gap_impact wobbled in Q3 replays. Single artifact value used here.)
- LP-26: `gap_impact="adverse"` → `"harmful"`, materiality=high, confidence=assert
- LP-32: `gap_impact="adverse"` → `"harmful"`, materiality=medium, confidence=assert

---

## ⚠️ 375M Write-Path Check: OWED on next keyed run

**Status: OPEN. Not closeable by 375N.**

The newest artifact on disk is the pre-deploy frozen 52adbf (timestamp 2026-06-04T03:47:23Z),
which pre-dates the 375M commit (`a939b01`, pushed to main 2026-06-05).

The 375M write-path verification requires a FRESH keyed run produced AFTER `a939b01`:
- Stage 5e output must contain `use_consequence` key (not `gap_impact`)
- `use_consequence` value must be in `{"beneficial", "neutral", "harmful", "context_dependent"}`
- `gap_impact` key must be ABSENT from the `use_impact` dict in the new artifact
- All downstream consumers must route correctly via `normalizeUseConsequence()` / `_normalize_use_consequence()`

**This check must be performed on the first keyed run after `a939b01` is deployed.**
375E-COV validation MUST NOT proceed until this check passes.

Record: as of 2026-06-05, the write-path check is OPEN. The next production lease run on vered.ai
(post-deploy) will produce the first artifact to verify against. Tzvi or Code should inspect
`pipeline_results.json` → `coverage_assessment[LP-03|05|10|14|16|20|26|32].use_impact` for the
`use_consequence` key.

---

## Key measurement findings (used in Q1–Q6)

### `_should_assess` eligibility

Correct eligibility uses `element_verdicts` (list of dicts with `verdict` field), NOT
`elements_found`/`elements_missing` counts. The two fields differ: `elements_missing` excludes
favorable-to-tenant absences; `element_verdicts` counts all evaluated elements.

Example: LP-09 has 8 in `elements_found`, 0 in `elements_missing` (→ `covered`), but 12 items in
`element_verdicts` (4 with verdict=missing, all adverse-to-landlord = favorable-to-tenant).

Confirmed eligible (8 LPs): LP-03, LP-05, LP-10, LP-14, LP-16, LP-20, LP-26, LP-32  
Confirmed not-eligible (24 LPs): all others

### LP-09 coverage investigation

LP-09 (Subletting & Assignment):
- `coverage_state: "covered"` (12 elements, 8 present, 4 missing but all adverse-to-landlord)
- `covered_unfavorable_adverse_to: null` — NOT flagged by system
- `requires_attention: False` — system considers it resolved
- `caution_signals: ["common_dispute_area", "landlord_leverage_point"]` — ONLY potential signal

The `landlord_leverage_point` caution signal is the sole detectable artifact hook, and it is
insufficient as a structural present-hostile entry condition (too noisy; fires on other LPs).

### Threshold sensitivity (not-eligible directional LPs only)

At 33% threshold: 11 new LPs pass (LP-04, LP-06, LP-07, LP-15, LP-17, LP-19, LP-21, LP-22, LP-28, LP-29, LP-30)  
At 25% threshold: 12 new LPs pass (adds LP-02)  
At 20% threshold: 14 new LPs pass (adds LP-18, LP-27)  
LP-01 (17%), LP-11 (12%), LP-24 (14%), LP-25 (14%) remain not-eligible at 20%

---

## Files changed

None. Step 375N is read-only. New files:

| File | Purpose |
|---|---|
| NEW `build_log/375N_results.md` | Q1–Q6 answers + A/B/C/D recommendation + two COV design calls |
| NEW `build_log/375N_code_status.md` | This file |

---

## Queue after 375N

1. **Tzvi makes two COV design calls** with 375N's numbers:
   - Call 1: Gate shape (33% vs 25% vs 20%, or B/C/D variant)
   - Call 2: Landing bucket for consequence_unassessed directional findings (floor vs visible subtype vs source-strict)
2. **Spec 375E-COV** (Chat writes chat_instruction) — widen `_should_assess` to chosen threshold +
   add `use_consequence_source` provenance field (assessed | defaulted_floor | not_eligible | absent)
3. **375E-DIR** (after COV) — routing formula consuming COV fields
4. **375H-C** (separate workstream) — keyed fixture matrix → schema repair for present-hostile
   covered LPs (enables Strategy C → Strategy D)
5. **Close 375M write-path check** on first keyed run after `a939b01` (before 375E-COV validation)

**DEPLOYMENT TRAP:** 375H repair findings must NOT enter lawyer-facing Risk until 375E-DIR fixes
routing. This constraint is unchanged.
