# 412 — Evaluator Fallback Integrity Trace

**Date:** 2026-07-08
**Type:** Read-only measurement and design. No code changes. No push. No commit unless instructed.
**Purpose:** Answer 9 questions about the Grok→Gemini evaluator fallback finding from Step 411. Characterize fallback scope (roles A/B/C), trigger conditions, provenance, frequency, material impact, frozen-stack integrity, fail-open vs fail-closed posture, patent relevance, and temperature deferral.

**Code read:**
- `cam/adapters/lease_review/lease_coverage_305.py` (lines 83–202, 340–640, 643–762, 1170–1249) — evaluator lineup, two-phase fallback, `is_fallback` recording, LP-level summary
- `cam/adapters/lease_review/model_config.py` (full, 105 lines) — primary/fallback config for all three roles
- `cam/core/provider_health.py` (full, 91 lines) — health tracker, cooldown, singleton
- `cam/adapters/lease_review/stage_fallback.py` (full, 126 lines) — single-stage fallback helper (NOT Stage 5 path)

**Data read:**
- `05 Lease Analyzer/results/lease_408c_atreca_runA/pipeline_results.json` — all 32 LPs scanned for `is_fallback=True` in `evaluator_meta` and `element_verdicts`
- `05 Lease Analyzer/results/lease_408c_atreca_runB/pipeline_results.json` — same

---

## 1. Executive Summary

**Scope is role C (Grok) only in N=2 Atreca runs.** No role A or B fallbacks were detected. However, the fallback code is wired for all three roles — A can fall back to Haiku, B to GPT-5.4, and C (with no same-provider option since grok-3 retired) falls directly to Gemini 2.5 Pro from the shared cross-provider pool.

**In both Atreca runs, one LP per run triggered a Grok failure and received all-Gemini role-C verdicts** (runA: LP-29, trigger=`malformed_response`; runB: LP-15, trigger=`empty_response`). In both cases the Gemini verdict materially differed from Grok's verdict on a coverage-determining element, producing LP-level coverage state changes that crossed the Stage 7 flagging threshold. **Both fallback events had material impact; no silent fallbacks exist in this dataset.**

**Provenance is recorded, not silent.** Machine-readable `is_fallback=True`, `actual_model`, and `fallback_reason` fields exist at per-element and per-LP granularity. The fallback is not laundered as the primary model's output. It is, however, not visually signaled in user-facing output.

**Frozen-stack integrity is conditional.** The stack is frozen at configuration time (A=Sonnet, B=GPT-5.5, C=Grok); at execution time, a run where Grok fails on one or more LPs is not a clean frozen-stack run. Whether the Grok failure is transient (API blip) or structural depends on the trigger type (`malformed_response` ≠ `api_error` ≠ `timeout`), and cannot be determined from pipeline artifacts alone.

**The fallback is fail-open.** The pipeline completes with Gemini verdicts rather than failing or flagging. This is appropriate for operational continuity but insufficient for frozen-stack or patent-claim runs where evaluator identity is a defined invariant.

---

## 2. Triggering 411 Finding

From `build_log/411_stage5_coverage_reproducibility_trace.md`, Section 8:

> Grok 4.3 failed for some LP evaluations in some runs, triggering a Gemini 2.5 Pro fallback. Evidence: LP-15 Run B: eval-C = `gemini-2.5-pro`, `is_fallback=True`. LP-29 Run A: eval-C = `gemini-2.5-pro`, `is_fallback=True`. In both cases the fallback substitution changed the outcome materially.

Specifically:
- **LP-15 Run B (fallback LP):** Grok failed (empty_response); Gemini substituted. For element `landlord_modify_remove`, Grok (runA) = `missing`; Gemini (runB) = `explicitly_present`. This resolved a `disputed` state to `explicitly_present`, removing the last absent element and flipping LP-15 from `partial_typical` (Run A) to `covered` (Run B).
- **LP-29 Run A (fallback LP):** Grok failed (malformed_response); Gemini substituted. For element `minimize_interference`, Gemini = `explicitly_present`; Grok (runB) = `missing`. Combined with Claude changing from `implicitly_present` to `missing`, the LP flipped from `covered` (Run A) to `partial_typical` (Run B).

The 411 report classified this mechanism as "structurally distinct from sampling nondeterminism — it substitutes a different model tier for one evaluator role, producing qualitatively different verdicts on the same element."

---

## 3. Fallback Code Path (All Three Roles)

### 3.1 Location

`cam/adapters/lease_review/lease_coverage_305.py`, function `_call_single_evaluator_305` (lines 325–593). This is the Stage 5 multi-evaluator path. It is **separate** from `stage_fallback.py` (`call_with_fallback`), which handles single-call stages (challenge, cascade, severity) and is not involved in Stage 5.

### 3.2 Two-Phase Structure

```
Phase 1: own-provider chain
  own_candidates = [primary] + own_chain entries
  Try each in order until one succeeds.

Phase 2: shared fallback pool (only if Phase 1 exhausted)
  _SHARED_FALLBACK_POOL = [
      ("google", "gemini-2.5-pro", "Gemini 2.5 Pro"),
      ("mistral", "mistral-large-latest", "Mistral Large"),
  ]
  Try pool entries in order, claiming each provider mutex.
```

Three evaluators run in parallel (ThreadPoolExecutor max_workers=3). Each evaluator independently exhausts its own chain before competing for shared pool slots. The pool uses a `pool_claimed` list + `pool_lock` so each provider is claimed at most once per LP.

### 3.3 Per-Role Configuration

| Role | Primary | Own chain | Phase 2 (shared pool) |
|------|---------|-----------|----------------------|
| A | `claude-sonnet-4-6` (Anthropic) | `claude-haiku-4-5-20251001` (Anthropic) | Gemini 2.5 Pro → Mistral Large |
| B | `gpt-5.5` (OpenAI) | `gpt-5.4` (OpenAI) | Gemini 2.5 Pro → Mistral Large |
| C | `grok-4.3` (XAI) | **empty** — `grok-3` retired 2026-05-15 | Gemini 2.5 Pro → Mistral Large |

Code evidence:
```python
# model_config.py
EVALUATOR_C_FALLBACK = ("xai", "grok-4.3")   # same as primary; own_chain in lineup is []

# lease_coverage_305.py line 119
"own_chain": [],  # grok-3 retired 2026-05-15; no same-provider fallback
```

**Role C fallback path is shorter than A and B:** one failure → shared pool (Gemini). Roles A and B get one same-provider retry first (Haiku, GPT-5.4) before entering the shared pool.

### 3.4 Provider Health and Cascade Risk

`cam/core/provider_health.py` (`get_health_tracker()`) provides a singleton `ProviderHealth` with a 60-second cooldown. `_call_single_evaluator_305` checks `health.is_available(provider)` before each attempt (line 453) but does **not** call `health.mark_degraded()` on failure. Stage 5 failures are per-LP and do not update the health tracker. This means:

- A Grok failure for LP-N does not mark Grok as degraded for LP-N+1.
- Each LP independently tries Grok first.
- The observed pattern (1 fallback event per run, not all-32-LPs-fallback) is consistent with this: the failure is per-call, not per-provider.
- If `ProviderRouter.call_json()` (the router path used by non-Stage-5 stages) marks a provider degraded, that degradation WOULD be visible to Stage 5 calls in the same process. But Stage 5 is typically not interleaved with stages that use the router path.

---

## 4. Trigger Conditions

### 4.1 Observed Triggers (from pipeline data)

| Run | LP | Role | Trigger | `fallback_reason` |
|-----|-----|------|---------|-----------------|
| runA | LP-29 | C | Grok returned malformed (non-parseable) JSON response | `malformed_response` |
| runB | LP-15 | C | Grok returned empty string | `empty_response` |

### 4.2 Classification Logic (`_classify_failure`, lines 160–180)

```python
def _classify_failure(error_msg: str, model: str) -> str:
    if "degraded" in m or "already claimed" in m:     → "provider_unavailable"
    if timeout/rate/429/connection/401/500/502/503     → "api_error"
    if "empty_content" / "empty content":
        → "reasoning_exhaustion" (gpt-5.x) else "empty_response"
    if "truncation":                                   → "truncation"
    if "malformed" / "not a list" / "nonetype":
        → "reasoning_exhaustion" (gpt-5.x) else "malformed_response"
    default:                                           → "unknown"
```

Grok is not a `gpt-5.x` model (fails `_is_split_model("grok-4.3")`), so:
- Empty output → `empty_response` (not `reasoning_exhaustion`)
- Malformed JSON → `malformed_response` (not `reasoning_exhaustion`)

### 4.3 What These Triggers Mean

- `malformed_response` (LP-29 runA): Grok returned a syntactically invalid JSON response that could not be parsed as a verdict array. This is an inference-side failure — the model completed successfully at the API level but produced unparseable output. May indicate prompt/context issues specific to that LP's element set, not a network failure.

- `empty_response` (LP-15 runB): Grok returned an empty string. Could be an API-level failure (server returned 200 but empty body) or a model-level failure (reasoning consumed entire budget before output). No HTTP error code is available in `pipeline_results.json`; the XAI API call logs would be needed to distinguish.

### 4.4 What These Triggers Do NOT Mean

- These are NOT temperature-controlled failures. Temperature=0 affects sampling within a completed model call; it cannot prevent empty or malformed outputs at the API/inference level.
- These are NOT cascading across LPs within a run (health tracker not updated by Stage 5 failures).
- These are NOT predictable from LP difficulty — LP-15 (Signage Rights) and LP-29 (Right of Entry) are standard commercial lease provisions, not edge cases.

---

## 5. Provenance and Silence

### 5.1 Is the Fallback Silent?

**No, in the machine-readable artifact.** Provenance is recorded at three granularities:

**Per-element** (`element_verdicts[n].evaluator_verdicts[k]`):
```json
{
  "role": "C",
  "actual_model": "gemini-2.5-pro",
  "actual_label": "Gemini 2.5 Pro",
  "is_fallback": true,
  "verdict": "explicitly_present",
  "confidence": "high"
}
```

**LP-level evaluator_meta** (`evaluator_meta.C`):
```json
{
  "is_fallback": true,
  "model": "gemini-2.5-pro",
  "actual_model": "gemini-2.5-pro",
  "fallback_reason": "malformed_response",
  "fallback_trigger_stage": "305"
}
```

**LP-level summary** (`lp_meta`):
```json
{
  "fallback_used": true,
  "fallbacks": [{"role": "C", "actual_model": "gemini-2.5-pro", "actual_label": "Gemini 2.5 Pro"}]
}
```

### 5.2 Provenance Fix History

A prior version (before Step 372a) laundered fallback verdicts under the primary model's identity. The code comment at line 689–696 is explicit:

> "this is the line that was previously laundering a fallback's verdict under [the primary model's identity]"

The fix is in place. The `actual_model` / `is_fallback` fields reflect the real answering model, not the slot's configured primary.

### 5.3 Is the Fallback User-Visible?

**No, in user-facing output.** The `is_fallback` fields are in `pipeline_results.json` and `evaluator_meta` (marked "admin-side only — never lawyer-facing" in code comments at line 1191). The legal report, exposure statement, and coverage summary presented to users do not surface which model evaluated which provision. A user receiving a coverage report for LP-29 cannot tell whether Grok or Gemini produced the evaluation.

---

## 6. Frequency

**PROVENANCE-AVAILABILITY CAVEAT (stated first):** The `fallback_reason` field tells why the primary failed (`malformed_response`, `empty_response`) but does not include the HTTP status code or XAI-side error message. Call-level API logs (XAI dashboard, Railway server logs) would be needed to distinguish a 500-level server error from a model-level inference failure. The frequency counts below are from `pipeline_results.json` and are complete for this artifact, but the root cause of each trigger is not determinable from artifact data alone.

### 6.1 Measured Frequency (N=2 Atreca Runs)

| Metric | Value |
|--------|-------|
| Total evaluator calls (32 LPs × 3 roles × 2 runs) | 192 |
| Fallback events observed | 2 |
| Fallback rate (events / total calls) | 1.0% |
| LPs affected per run | 1 of 32 (3.1%) |
| Roles that triggered fallback | C only |
| Role A fallbacks | 0 |
| Role B fallbacks | 0 |
| Role C fallbacks | 2 (one per run) |
| Both fallbacks resulted in Gemini 2.5 Pro substitution | Yes |

### 6.2 Interpretation Discipline

N=2 is insufficient to characterize Grok failure rate. The two fallbacks may represent:
- A systematic fragility in Grok for specific LP element sets (both affected LPs are real estate property-access provisions with technical element lists)
- A time-correlated XAI API instability affecting both runs (if runs were close in time)
- Random API-level noise unrelated to LP content

These hypotheses are not distinguishable from artifact data. The rate (1/32 per run) is directional only.

---

## 7. Material Impact

### 7.1 Framework: Material vs. Silent

A "silent" fallback is one where the fallback model returns the same verdict as the primary would have returned for all elements, producing no coverage state change. A "material" fallback produces at least one verdict difference that changes a coverage-determining outcome.

**Caveat:** The true counterfactual (what Grok would have said had it succeeded on the fallback LP) is unobservable. The cross-run comparison (Grok on one run, Gemini on the other) is the closest available proxy, but confounds exist (other LPs processed in different order, Claude and GPT also varying slightly between runs).

### 7.2 Material Fallback Instances (Both in N=2 Dataset)

**LP-29 Run A (Gemini = fallback):**
- Element: `minimize_interference`
- Gemini verdict: `explicitly_present` (high confidence)
- Grok verdict (Run B): `missing` (high confidence)
- Impact: Opposite verdicts on the same element. With Gemini present + A=`implicitly_present` + B=`implicitly_present` → majority present → LP=`covered`. With Grok missing + A=`missing` + B=`implicitly_present` → disputed → LP=`partial_typical`.
- LP-level crossing: covered → partial_typical (CROSS flagging threshold)

**LP-15 Run B (Gemini = fallback):**
- Element: `landlord_modify_remove`
- Gemini verdict: `explicitly_present` (high confidence)
- Grok verdict (Run A): `missing` (high confidence)
- Impact: Resolves `disputed` (A=`explicitly_present`, B=`explicitly_present`, C=`missing`) → `explicitly_present` (unanimous). Removes last absent element from LP.
- LP-level crossing: partial_typical → covered (CROSS flagging threshold, opposite direction)

Both instances: Gemini and Grok produced **opposite, high-confidence verdicts** on the same element. This is not a marginal adjacent-bucket disagreement (e.g., implicitly_present vs. explicitly_present); it is a present/absent split.

### 7.3 Silent Fallbacks

**Zero silent fallbacks in this dataset.** Every `is_fallback=True` instance in N=2 runs produced a materially different verdict from the corresponding Grok verdict on the paired run. This does not mean silent fallbacks cannot occur; it is a N=2 observation.

### 7.4 Non-Fallback Elements of the Same LP

Both fallback LPs had other elements where Gemini's verdicts appear consistent with Grok-run verdicts on the non-critical elements (e.g., LP-15 elements `exterior_signage_right`, `approval_process`, `pylon_monument_sign` all returned `explicitly_present` from Gemini, consistent with the covered state in Run A on non-`landlord_modify_remove` elements). The critical-element divergence drove the state change; the non-critical elements show Gemini and Grok producing similar high-confidence present verdicts where coverage is unambiguous.

---

## 8. Frozen-Stack Integrity

### 8.1 Current Definition of "Frozen Stack"

The project defines the frozen stack as: A=`claude-sonnet-4-6`, B=`gpt-5.5`, C=`grok-4.3`. This is enforced at the configuration layer in `model_config.py` and `EVALUATOR_LINEUP_305`. The freeze is intended to make model-to-model comparison controlled: when comparing runs, any outcome difference should be attributable to content, not model identity.

### 8.2 What Fallback Does to This Guarantee

A run where Grok fails on LP-K and Gemini substitutes is, at the execution layer, a run with stack [Sonnet, GPT-5.5, **Gemini**] for LP-K and [Sonnet, GPT-5.5, Grok] for all other LPs. The "frozen stack" label does not hold for LP-K.

This matters in two scenarios:

**Scenario 1: Cross-run comparison.** If Run A used Grok on LP-29 and Run B used Gemini on LP-15, a comparison of the two runs cannot attribute all differences to content — model-identity differences are confounded. The 411 report's reproducibility trace is affected: at least 2 of the 10 unstable LP crossings (LP-15 and LP-29) are attributable to evaluator substitution rather than content-level nondeterminism.

**Scenario 2: Absolute result claim.** If a result states "LP-29 is `covered` per the three-evaluator frozen-stack analysis," but LP-29's Run A role-C verdict came from Gemini, the claim is technically inaccurate: the evaluation was not by the declared stack for that provision.

### 8.3 Can Fallback Be Prevented?

At the code level: no, without either (a) aborting the run when the primary fails, or (b) never having a fallback path. The fallback exists because Grok has historically failed for specific LPs, and aborting a 17–25 minute run due to one LP's evaluator failure was an unacceptable cost. The fallback is a deliberate design decision trading frozen-stack purity for operational completeness.

The frozen-stack concept requires the following addition to be accurate: *"frozen stack unless any evaluator's primary model fails at call time, in which case a fallback model substitutes for that evaluator role on that LP."*

---

## 9. Fail-Open vs. Fail-Closed by Run Type

### 9.1 Three Modes (from brief)

| Mode | Behavior | Current? |
|------|----------|----------|
| Mode 1: Fail-open | Fallback substitutes; run completes; fallback recorded but not visually flagged | **Yes — current behavior** |
| Mode 2: Fail-soft | On primary failure, emit `unclear` for all affected elements; run completes; LP flagged as degraded | No |
| Mode 3: Fail-closed | Abort run or LP evaluation on any evaluator primary failure; no verdict emitted | No |

### 9.2 Appropriate Mode by Run Type

**Automated batch (operational, e.g., 408C):** Mode 1 is acceptable. The primary purpose is producing a complete coverage map; a Gemini substitute for one LP per run is preferable to a failed run. The `is_fallback` flag in the artifact is sufficient for audit.

**Frozen-stack reproducibility run:** Mode 2 is the minimum requirement. If any evaluator falls back, the affected LP's elements should be emitted as `unclear` (not the fallback model's verdicts) with a `degraded_evaluator` flag. This allows the run to complete while clearly marking the LP as requiring re-evaluation. A result set with `unclear` elements from a primary failure is honestly incomplete; a result set with Gemini verdicts labeled as Grok-slot verdicts is misleading.

**Patent-claim or evidence-production run:** Mode 3 is appropriate. A run intended to demonstrate the declared stack should abort rather than silently substitute. The abort itself is a signal that the declared stack was not achievable at that moment; a rescheduled run at a different time is preferable to a result set with undisclosed model substitution.

---

## 10. Patent/Claim Relevance

**Both doctrines below are assessed. This is not a legal opinion; it is an accuracy and integrity analysis of what the pipeline produces relative to what may be claimed.**

### 10.1 Doctrine 1: Frozen-Stack Claim

If any patent claim or patent application describes the evaluation system as using a three-model frozen stack (A=Anthropic, B=OpenAI, C=XAI), a run where role C actually used a Google model (Gemini) for some LPs is a factual discrepancy between the claim and the execution. Whether this discrepancy is claim-defeating depends on claim construction:

- "Configured to use" vs. "using": a claim that the system is *configured* with XAI as role C is met even if a fallback fires, because the configuration is correct. A claim that the system *used* XAI for each evaluation is not met for the fallback LPs.
- "Substantially" language: if the claim includes "substantially all" or "in general" qualifiers, 1/32 LPs (3.1%) falling back may not be claim-defeating depending on the qualifier's scope.

**Conservative finding:** for a clean frozen-stack patent-claim run, Mode 3 (fail-closed) should be used. If the run cannot complete without fallback, that is a material fact about system reliability that should be documented rather than silently corrected.

### 10.2 Doctrine 2: Provider Diversity / Independence Claim

If any claim relies on three *independent* evaluators from *different provider ecosystems* (as a technical feature of the evaluation architecture — diversity of model provenance as a check on any single provider's bias), then:

- Configured state: A=Anthropic, B=OpenAI, C=XAI. Three distinct ecosystems. Provider diversity is by design.
- Executed state (fallback run): A=Anthropic, B=OpenAI, C=Google. Still three distinct ecosystems (Google substitutes for XAI). Provider diversity is nominally preserved, though the specific XAI (Grok) evaluation behavior is replaced by Google (Gemini) evaluation behavior.
- Potential concern: if the claim characterizes the XAI role as providing a specifically adversarial or novel perspective distinct from Anthropic and OpenAI, then Gemini (also a large-scale instruction-tuned model similar in lineage to Claude) does not preserve that characterization. Grok's known divergence on specific verdicts (seen in data: Grok=`missing`, Gemini=`explicitly_present` on the same element, both high-confidence) suggests the models are not interchangeable from an evaluation-perspective standpoint.
- If Anthropic were also to fall back to Gemini (via the shared pool) in the same run, two of three evaluators would be Google models — a more serious diversity violation. This is theoretically possible per the code but did not occur in N=2 runs.

**Conservative finding:** Gemini substitution for XAI preserves nominal provider diversity but substitutes a model with potentially different evaluation posture for the role specifically selected for its XAI-sourced perspective. For diversity-claim purposes, the substitution should be recorded as a non-standard execution.

---

## 11. Temperature Deferral

Temperature=0 controls sampling variance within a single completed model call. It does not address and cannot prevent:

1. **API-level failures:** An empty response (LP-15 runB) or malformed JSON (LP-29 runA) occurs before or during inference at the model level; temperature does not affect whether the inference succeeds or the output is parseable.

2. **Model substitution effects:** The Grok→Gemini divergence (present/absent split on the same element) is not sampling noise. At temperature=0, both Grok and Gemini are deterministic given identical inputs. The variance is model-specific behavior on the same prompt, not sampling variance within a single model. Temperature cannot resolve this.

3. **Structural differences in evaluation posture:** Grok and Gemini may have fundamentally different legal-reasoning tendencies for commercial lease elements (evidenced by their high-confidence, opposite-polarity verdicts). No temperature setting equalizes model-specific behavior.

**Temperature is the right control for within-model run-to-run variance.** It is the wrong tool for between-model variance introduced by fallback substitution. These are orthogonal nondeterminism dimensions that require separate controls.

---

## 12. Recommendation

*Measurement only. Not a design decision. No implementation in this session.*

Three actionable options, not ordered by priority:

**Option A (Audit field, no behavior change):** Add a per-run summary field to `pipeline_results.json` counting total `is_fallback=True` evaluator calls and listing the affected (LP, role) pairs. Currently this information is available by scanning `evaluator_meta` across all 32 LPs but has no top-level summary. A summary field makes fallback events visible without inspecting individual LPs.

**Option B (Mode 2 for frozen-stack runs):** Add a run-level configuration flag (e.g., `require_primary_evaluators: true`) that switches Stage 5 fallback behavior from Mode 1 to Mode 2: on primary failure, emit `unclear` for all elements of that LP (with a `degraded_evaluator` marker) rather than substituting the fallback model's verdicts. The run completes; the LP is explicitly marked as requiring re-evaluation. Suitable for reproducibility and patent-claim runs.

**Option C (Retry before fallback):** Before entering the shared pool, retry the primary model once with a shorter timeout or simplified prompt. If Grok's failures are transient API blips, a retry might succeed and avoid Gemini substitution entirely. If the failure is structural (malformed or empty for a specific LP), the retry would also fail and the fallback would fire as now. This adds latency but reduces the fallback rate for transient failures.

**Discriminating factor:** if the `malformed_response` and `empty_response` triggers are consistently associated with specific LP element sets (LP-15, LP-29), Option C would not help (structural). If they are time-correlated and random, Option C would help. Determining which requires more than N=2 runs.

---

## Appendix: Complete Fallback Scan Results (N=2)

```
runA: is_fallback=True instances
  LP-29 (Right of Entry / Landlord Access): role=C, model=gemini-2.5-pro
    fallback_reason=malformed_response
    Elements (all 6): notice_period, emergency_entry, minimize_interference,
                      permitted_purposes, tenant_representative_present, entry_frequency_timing
    All Gemini verdicts: explicitly_present (6/6)

runA: Role A fallbacks: NONE
runA: Role B fallbacks: NONE

runB: is_fallback=True instances
  LP-15 (Signage Rights): role=C, model=gemini-2.5-pro
    fallback_reason=empty_response
    Elements (all 6): exterior_signage_right, directory_listing, approval_process,
                      landlord_modify_remove, code_compliance, pylon_monument_sign
    Gemini verdicts: explicitly_present (5/6), implicitly_present (1/6: directory_listing)

runB: Role A fallbacks: NONE
runB: Role B fallbacks: NONE
```

---

*Trace artifact: Step 412. Read-only. No code changes. No commit unless instructed.*
