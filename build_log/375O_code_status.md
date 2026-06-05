# Step 375O — Code Status: COV Entry-Policy Counterfactual

**Date:** 2026-06-05  **Mode:** READ-ONLY / keyless. No code changed, no model called.
**External-use pause:** still in force. 375O does not lift it.

---

## What was done

Keyless entry-strategy replay answering Q1–Q5 and per-strategy admission counts from
`375O_chat_instruction.md`. All reads were from frozen artifacts on disk; no pipeline runs
were triggered; no production code was modified.

---

## Files read (all read-only)

| File | What was read for |
|---|---|
| `build_log/375O_chat_instruction.md` | Instruction |
| `build_log/375J_results.json` | Directional LP list, materiality_source, current_bucket, compound_risk finding LP sets |
| `build_log/375N_results.md` | Q3 (direction split), Q4/Q5 (LP-09 coverage_state + threshold-lowering proof), threshold sensitivity table |
| `build_log/375H_code_status.md` | LP-09 schema defect characterization (Part A+B), `landlord_leverage_point` noisy-signal confirmation |
| `05 Lease Analyzer/results/lease_review_20260604_033046_52adbf/tenant_0/pipeline_results.json` | All 32 LP coverage states + element_verdicts (for A-threshold replay), use_impact records (already-assessed detection), cross_provision_findings (directional vs compound type + LP lists), `_stage_data.synthesis_meta` (Pass 1 candidate count, Pass 2 per-evaluator dir_verdicts for G-cand vs G-ver derivation) |
| `cam/adapters/lease_review/lease_use_impact.py` | `_should_assess` gate logic (for A50/A33/A25 replay) |

---

## Normalizer used

All use_impact fields from 52adbf read through `_normalize_use_consequence`:
- `use_consequence` key preferred if present
- Legacy `gap_impact="favorable"` → `"beneficial"`, `gap_impact="adverse"` → `"harmful"`, others unchanged

The 8 already-assessed LPs in 52adbf carry `gap_impact` (pre-375M write). After normalization:
LP-03/10/14/16/26 → `"harmful"`, LP-05 → `"beneficial"`, LP-20 → `"neutral"`, LP-32 → `"harmful"`.

---

## How G-cand and G-ver were derived

**G-cand (candidate-level, verification-agnostic):**
Source: `_stage_data.synthesis_meta.directional_guard.pass1_directional_candidate_count = 26`.
Pass 1 generated exactly 26 directional candidates, one per flagged LP. Candidate_density = 1.0
(26 candidates / 26 flagged LPs). G-cand = the 26 LPs with directional_mismatch findings in
`cross_provision_findings` (Dir-01 through Dir-26), read verification-agnostically.

**G-ver (3-0 verified):**
Source: `_stage_data.synthesis_meta.pass2_raw` — per-evaluator dir_verdicts:
- Evaluator A (claude-sonnet-4-6): `{mismatch_confirmed: 26}`
- Evaluator B (gpt-5.4): `{mismatch_confirmed: 26}`
- Evaluator C (grok-4.3): `{mismatch_confirmed: 26}`

All 26 candidates confirmed as `mismatch_confirmed` by all 3 evaluators on this run → 3-0 unanimous.
G-ver = same 26 LPs as G-cand. **Delta = 0.**

**Why delta is 0 on this run:** This artifact is a clean 3-0 run with no verification splits. The
vote-wobble re-import risk (375D-2/375-R: Pass 2 votes flip run-to-run) is real but not observable
here. Entry architecture should use G-cand (not G-ver) to prevent future vote-wobble from
propagating into the 5e eligibility gate.

---

## Key structural finding

**H = G-cand on this artifact.** Confirmed by set arithmetic:

```
A33 newly-admitted: {LP-04, LP-06, LP-07, LP-15, LP-17, LP-19, LP-21, LP-22, LP-28, LP-29, LP-30}
G-cand newly-admitted: {LP-01, LP-02, LP-04, LP-06, LP-07, LP-11, LP-15, LP-17, LP-18,
                        LP-19, LP-21, LP-22, LP-24, LP-25, LP-27, LP-28, LP-29, LP-30}

A33 ⊆ G-cand: True (all 11 A33 new LPs are in G-cand's 18)
H = A33 ∪ G-cand = G-cand (identity, not approximation)

G-cand - A33 = {LP-01, LP-02, LP-11, LP-18, LP-24, LP-25, LP-27}
(7 thin-gap LPs: <33% missing; reachable by G-cand's finding-triggered lane only)
```

---

## ⚠️ 375M Write-Path Check: STILL OWED on next keyed run

**Status: OPEN. Carried forward from 375N.**

The most recent artifact on disk (52adbf, 2026-06-04T03:47:23Z) pre-dates the 375M deploy
commit (`a939b01`, pushed 2026-06-05). Stage 5e in all fresh runs since deployment should write
`use_consequence` (not `gap_impact`). The check:

1. Run a fresh lease through the pipeline (any keyed run post-`a939b01`)
2. Inspect `coverage_assessment[LP-03|05|10|14|16|20|26|32].use_impact` in the output artifact
3. Confirm: `use_consequence` key present, value in `{beneficial, neutral, harmful, context_dependent}`
4. Confirm: `gap_impact` key ABSENT

**375E-COV validation MUST NOT proceed until this check passes.** If `gap_impact` still appears
post-deploy, there is a write-path bug in `lease_use_impact.py`.

---

## Files changed

None. Step 375O is read-only.

| File | Purpose |
|---|---|
| NEW `build_log/375O_results.md` | Per-strategy table + Q1–Q5 + gate-vs-yield caveat + architecture recommendation |
| NEW `build_log/375O_code_status.md` | This file |

---

## Queue after 375O

1. **Tzvi makes two COV design calls** with 375N + 375O numbers:
   - Call 1: Gate architecture — two-lane H (G-cand + A-rail, threshold TBD) vs G-cand alone
   - Call 2: Landing bucket for consequence_unassessed findings (~6 irreducible CRX floor + any
     5e yield failures)
2. **Spec 375E-COV** (Chat writes chat_instruction) — implement the chosen gate +
   `use_consequence_source` (assessed | defaulted_floor | not_eligible | absent)
3. **375E-DIR** — routing formula consuming COV fields
4. **375H-C** (separate workstream) — keyed fixtures → schema repair → present-hostile lane
5. **Close 375M write-path check** on first fresh keyed run post-`a939b01`

**DEPLOYMENT TRAP unchanged:** 375H repair findings must NOT enter lawyer-facing Risk until
375E-DIR routing fix is live.
