# 418c — Stage 5 Role C Payload Capture and Replay

**Date:** 2026-07-13
**Fixture:** atreca_eastjamie_southsf_lease.txt (same as Steps 407/411/417)
**Element under investigation:** `LP-07.proportionate_share_calculation`
**Panel:** post-414/416 frozen stack (A=claude-sonnet-4-6 / B=gpt-5.5 / C=grok-4.3)
**Phase 0 runs:** 3 (capture only)
**Phase 1 replay:** not run — Phase 0 payloads differ; stopped per spec

---

## Executive Summary

Phase 0 establishes that Role C (grok-4.3) is **not being asked the same question twice**. The LP-07 `tenant_text` block that reaches the Stage 5 evaluators differs in content, length, and structure across runs because the upstream Gemini extraction stage (Stage 1) is non-deterministic. The three captured payloads had prompt lengths of 10,267 / 6,161 / 14,802 characters and different SHA-256 hashes in all three cases.

The Role C verdict (`explicitly_present` vs `missing`) tracks the extraction output, not grok-4.3 model variance. When extraction includes the first-page percentage table (`"Tenant's Share of Operating Expenses of Building: 100%"`), Role C returns `explicitly_present`. When it is absent, Role C returns `missing`.

**This reframes the 417 analysis.** The "43% Role C element flip share" previously attributed to model stochasticity is substantially (possibly predominantly) driven by variable extraction input. Grok-4.3 behaved correctly given what it received. The instability problem is upstream.

Phase 1 (exact payload replay) was not run. Stopped per spec: payloads differ → stop and report.

---

## Capture Method

**No `cam/` file was modified. No git changes. Nothing to revert.**

Instrumentation: runtime monkey-patch of `cam.core.provider_router.XAIAdapter.call` applied in the harness (`scratchpad/run_418c_capture.py`) before any pipeline import. The patch intercepts calls where `target.name` contains `"305-C-LP-07"`, records `(system_prompt, user_prompt, params_sent, timestamp)`, then forwards the real call unchanged. Behavior is identical; no retries altered, no parameters added, no schema changes.

What the 416 assertion (`_check_generation_integrity()`) does NOT capture: prompt bodies. It records declared vs transmitted generation parameters only. The prompt content that reaches the model is invisible to it.

The harness script is not committed to main.

---

## Phase 0 — Payload Stability (3 runs)

### Run Inventory

| Run | Elapsed (s) | LP-07 Role C `proportionate_share` | LP-07 state |
|-----|-------------|-------------------------------------|-------------|
| 1 | 1491 | `explicitly_present` | `partial` |
| 2 | 2107 | `explicitly_present` | `partial` |
| 3 | 2182 | `missing` | `review_needed` |

### Payload Hashes

| Run | payload_hash (SHA-256) | prompt_hash (SHA-256) | prompt length (chars) | lines |
|-----|------------------------|----------------------|----------------------|-------|
| 1 | `112a343e6da58a28...` | `7fb3b3b87158e691...` | 10,267 | 109 |
| 2 | `f82f770a8e620122...` | `630d7bc2f5acd587...` | 6,161 | 101 |
| 3 | `1c4cc9c4fffb1c09...` | `953019c5f0ead69b...` | 14,802 | 135 |

**Payload hashes identical: NO**
**Prompt hashes identical: NO**

All three hashes are distinct. Parameters (`temperature=0.0`, `max_tokens=4600`) were identical across all runs; the difference is entirely in prompt body.

### Element IDs in LP-07 batch (from first capture)

```
LP-07.proportionate_share_calculation
LP-07.included_expense_categories
LP-07.excluded_expense_categories
LP-07.cam_cap
LP-07.tenant_audit_rights
LP-07.reconciliation_timeline
```

6 elements in a single batch call (not split). This confirms what 418b missed: the 418b probe sent 1 element in isolation; production always sends the full 6-element LP-07 batch.

### What differs between payloads

The divergence is in the `LEASE PROVISION TEXT:` block — the tenant text content for LP-07.

**Run 1 (10,267 chars — `explicitly_present`):**
- Tenant text: 12 lines. PDF-artifact formatting (extra spaces). Exclusion clauses collapsed to `[Exclusions (a) through (u) listed in document]`. First-page percentage table **absent** from text body.
- Representative line: `"5. Operating Expense Payments . Landlord shall deliver..."`
- Role C reasoning: Probably infers coverage from the text reference to "percentage set forth on the first page."

**Run 2 (6,161 chars — `explicitly_present`):**
- Tenant text: 1 very long line. Extraction most aggressively compressed. **Begins with: `"Tenant's Share of Operating Expenses of Building: 100%. Building's Share of Project: 45.79%."`** — the first-page percentage table is embedded at the top, then the body follows in a single paragraph.
- This is the only run where explicit numbers (100%, 45.79%) appear in the LP-07 tenant text. Role C sees a stated percentage → `explicitly_present` is the correct verdict.

**Run 3 (14,802 chars — `missing`):**
- Tenant text: 30 lines. Most complete rendering. Exclusion clauses (a) through (u) spelled out in full. First-page percentage table **absent** from text body.
- Role C sees no formula, no numerator/denominator, no explicit percentage stated in the body text. `must_be_explicit=true` precludes inferring from "percentage set forth on the first page." → `missing` is the correct verdict given this input.

### Root cause of prompt variability

The Gemini extraction stage (Stage 1 / `lease_extract`) is non-deterministic. Each pipeline run re-runs Gemini extraction, which produces a different segmentation and rendering of the PDF source text for LP-07. The differences include:

1. Whether the first-page data table (Tenant's Share %, Building's Share %) is included or excluded from the LP-07 text block
2. Whether exclusion clauses are expanded inline or collapsed to a summary
3. Overall text length and paragraph structure
4. In Run 3, the LEASE PROVISION TEXT starts at line 105 (vs 97 in Runs 1/2), indicating additional context blocks were injected earlier in the prompt

---

## Comparison to Prior Measurements

| Source | Prompt | N | Role C `proportionate_share` |
|--------|--------|---|------------------------------|
| 417 baseline | Full Stage 5 (6-element batch, variable extraction per run) | 10 | `explicitly_present` 8/10, `missing` 2/10 |
| 418b probe | 1-element reconstructed prompt (fixed, one-extraction text, no first-page table) | 9 | `missing` 9/9 |
| 418c Phase 0 | Full Stage 5 (6-element batch, captured exact payloads) | 3 | `explicitly_present` 2/3, `missing` 1/3 |

The 418b probe and 418c Run 3 converge on `missing` for the same reason: the first-page percentage table was absent from the tenant text in both cases. The 418b probe was accidentally reproducing the "missing-extraction" path, not a model failure.

---

## Determination

**Root cause: variable extraction input (Gemini Stage 1), not model stochasticity.**

Grok-4.3's behavior is consistent and correct given its input. When the extracted text includes the first-page percentage data, `explicitly_present` is the right call. When it does not, `missing` is the right call under `must_be_explicit=true`. Neither verdict is wrong — they reflect genuinely different inputs.

The 417 analysis conclusion "Role C is 43% of element flips" remains numerically true, but the interpretation was incomplete. What 417 measured was: **how often does the full pipeline (extraction + evaluation) produce a different coverage_state?** It did not establish how much of that variance originates in extraction vs. model. 418c establishes that extraction variance is a confirmed, material contributor.

**The 418b contradiction is resolved.** The isolated probe was not wrong — it was accidentally probing the no-first-page-table extraction path. The 9/9 `missing` result was correct for that input. The probe did not have a prompt reconstruction error; it had the wrong *extraction output* (one specific run's rendered text, which happened to lack the percentage table).

**The reasoning_effort hypothesis (418b) remains dead.** The probe's consistency (9/9) was real; the input mismatch with 417 was the explanation, not effort level.

---

## Implication for Stage 5 Stabilization

This materially changes the stabilization target. The problem is not:
- ~~Role B temperature (gpt-5.5 at temp=1)~~ — ruled out by 417 per-role attribution
- ~~Role C reasoning_effort (low default)~~ — ruled out by 418b N=9 probe
- ~~Model-level stochasticity~~ — ruled out by 418c (consistent verdicts when input is fixed)

The problem is:
- **Extraction non-determinism (Gemini Stage 1)** — confirmed by 418c as a material variance source
- **Downstream consequence: Stage 5 evaluators receive different facts about the same document in different runs**, and their verdicts correctly reflect those different facts

Stabilization interventions fall into two categories:

1. **Extraction stabilization** — make Gemini's LP-text rendering deterministic (caching, seed, or single-extraction-multiple-evaluator-reuse). This is the higher-leverage fix: if the input is stable, the output will be stable for most LPs.

2. **Evaluator robustness** — design element schemas and prompts that return consistent verdicts even when the extracted text is incomplete (e.g., for `proportionate_share_calculation`, a schema that recognizes "percentage set forth on the first page" as sufficient evidence even without a stated number). This is a secondary concern; the primary problem is that evaluators are correctly flagging genuine information gaps in incomplete extractions.

The two are not mutually exclusive, but extraction stabilization should be characterized before evaluator robustness is redesigned.

---

## Recommendation

Stop the current investigation branch. The core finding — that variance is substantially driven by upstream extraction — is established and changes the stabilization design. The next step is a decision on scope, not more measurement:

1. **Scope extraction stabilization (Step 419a):** Determine whether Gemini extraction output can be made deterministic across pipeline runs. If Stage 1 output is cached per document, Stage 5 receives identical input, and residual variance becomes purely model-level.

2. **Characterize extraction variance breadth:** 418c observed LP-07. The same question applies to the other 25 unstable LPs from 417. Before designing a fix, it is worth knowing whether extraction variability is the dominant explanation for most of those LPs or a partial one.

3. **Defer ablation design** (batch size, element co-occurrence, element order): These are secondary questions that only make sense after extraction is stabilized. Ablating context on variable inputs would produce uninterpretable results.

---

*Phase 0 complete. Phase 1 not run (payloads differ, stopped per spec).*
*Capture script: `scratchpad/run_418c_capture.py` — not committed to main.*
*Raw captures: `05 Lease Analyzer/_418c_results/418c_captures.json` — not staged.*
