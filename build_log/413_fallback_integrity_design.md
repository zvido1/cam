# 413 — Fallback Integrity Design Spec

**Date:** 2026-07-08
**Type:** Design only. No code changes. No implementation. No push.
**Purpose:** Specify the Stage 5 evaluator fallback integrity fix. Root cause: Role C has an empty `own_chain` after the grok-3 retirement (2026-05-15), causing a first Grok failure to cross model families directly to Gemini. This is a config-drift risk that A and B inherit the day their same-provider fallback models retire. 412 confirmed provenance is recorded and not silent; this step specifies how to enforce chain integrity, add a transient-vs-hard retry distinction, add a startup guard against retirement drift, add a run-level degraded flag, and gate canonical vs product runs on fallback behavior.

**Upstream:** Step 412 (`build_log/412_evaluator_fallback_integrity_trace.md`).

---

## 1. Executive Summary

Role C's fallback chain is structurally weaker than Roles A and B. When Grok 4.3 fails on a single evaluator call:

- Role A: Sonnet → Haiku (same provider) → shared pool (Gemini)
- Role B: GPT-5.5 → GPT-5.4 (same provider) → shared pool (Gemini)
- Role C: Grok 4.3 → (no same-provider retry; own_chain is empty) → shared pool (Gemini)

This means the FIRST Grok failure crosses model families. Roles A and B absorb a transient failure with a same-provider retry that preserves evaluator identity. Role C has no such buffer and immediately substitutes a Google model for an XAI evaluator slot.

The root cause is retirement-driven config drift: grok-3 was retired 2026-05-15; the code comment at `lease_coverage_305.py:119` records this but carries no enforcement. The same drift pattern threatens A and B: if claude-haiku-4-5-20251001 or gpt-5.4 are retired without a chain repair, Roles A and B acquire the same empty-own_chain vulnerability. This is a class of config-drift risk, not a Grok-specific quirk.

**412 confirmed:** provenance is machine-readable (is_fallback, actual_model, fallback_reason, lp_meta.fallback_used). The Step 372a fix already prevents verdict laundering. But provenance-as-audit-trail is not the same as enforcing canonical run integrity. A run with is_fallback=True in evaluator_meta is not a clean frozen-stack run; it needs to be marked and, in canonical/patent/benchmark contexts, either aborted or abstained.

**Recommendation sequence:** implement C same-provider retry (transient-failure buffer) + retirement-drift startup guard (class fix) + run-level degraded flag (propagates across pipeline) + strict/permissive mode gate (canonical vs product). Temperature/config work deferred behind fallback integrity because fallback changes evaluator identity — a more fundamental invariant than temperature setting.

---

## 2. 412 Findings Carried Forward

These are facts from the 412 trace; this spec does not re-derive them.

**Provenance exists and is not silent.** Three granularities:
- Per-element: `evaluator_verdicts[n].is_fallback`, `.actual_model`, `.actual_label`
- LP evaluator_meta: `evaluator_meta.C.is_fallback`, `.fallback_reason`, `.fallback_trigger_stage`
- LP summary: `lp_meta.fallback_used`, `.fallbacks[{role, actual_model, actual_label}]`

**Step 372a already fixed verdict laundering.** Prior to 372a, a fallback model's verdict was emitted under the primary model's label. The fix is in place. This spec does not revisit 372a.

**Measured fallbacks were material.** In the 411/412 pair (N=2 Atreca runs):
- LP-29 runA: Grok failed (malformed_response); Gemini substituted; verdict on `minimize_interference` was opposite (Gemini=`explicitly_present`, Grok=`missing`); LP crossed coverage threshold (covered → partial_typical).
- LP-15 runB: Grok failed (empty_response); Gemini substituted; verdict on `landlord_modify_remove` was opposite (Gemini=`explicitly_present`, Grok=`missing`); LP crossed coverage threshold (partial_typical → covered).

**Frequency uncharacterized.** N=2 runs, 1 fallback event per run (1 of 32 LPs = 3.1% rate), both on Role C. Sample too small to estimate baseline fallback rate. Future monitoring should accumulate across runs and stratify by fallback_reason.

**No claim silent fallback is impossible.** "Zero silent fallbacks in N=2" is a dataset observation; a Gemini verdict that matched Grok's verdict on a different LP would not have been detectable as a discrepancy. Silent fallback (same verdict, different model) is observable from is_fallback=True even without a paired run comparison. It cannot be ruled out from absence of evidence.

**Fallback events are high-severity even at low frequency.** They change evaluator identity — the most fundamental invariant of the frozen stack. A single cross-family substitution in a patent-claim or reproducibility run invalidates the "three-evaluator frozen-stack" characterization for that LP. Low-frequency events at high-severity require structural prevention or explicit marking, not monitoring alone.

---

## 3. Role C Chain Problem

### 3.1 Current State

```python
# model_config.py
EVALUATOR_C_PRIMARY  = ("xai", "grok-4.3")
EVALUATOR_C_FALLBACK = ("xai", "grok-4.3")  # same model — no true same-provider fallback exists

# lease_coverage_305.py line 112-120
"C": {
    "provider": EVALUATOR_C_PRIMARY[0],
    "model": EVALUATOR_C_PRIMARY[1],
    ...
    "own_chain": [],  # grok-3 retired 2026-05-15; no same-provider fallback
}
```

`EVALUATOR_C_FALLBACK` in model_config.py is set to the same model as the primary — a deliberate record that no XAI same-provider alternative is currently active. The lineup builds `own_chain=[]` from this. The comment is accurate; the enforcement is absent.

**Call sequence on Grok failure:**
1. `_try_call("xai", "grok-4.3", ...)` → fails
2. Phase 1: `own_candidates = [(primary)]` + `own_chain` entries = only the primary. Own chain exhausted.
3. Phase 2: shared pool tried immediately. `("google", "gemini-2.5-pro", ...)` claimed. Gemini called.
4. Gemini verdict emitted with `is_fallback=True`, `actual_model=gemini-2.5-pro`.

There is no same-provider retry. The first failure crosses family.

### 3.2 Contrast with A and B

```
Role A failure path:
  (1) Sonnet 4.6 → fail
  (2) own_chain: Haiku 4.5 → try same-provider
      if success: is_fallback=True, actual_model=haiku (same family, different tier)
      if fail: shared pool → Gemini (cross-family)
  Result: one intra-family buffer before cross-family.

Role B failure path:
  (1) GPT-5.5 → fail
  (2) own_chain: GPT-5.4 → try same-provider
      if success: is_fallback=True, actual_model=gpt-5.4 (same family, different version)
      if fail: shared pool → Gemini (cross-family)
  Result: one intra-family buffer before cross-family.

Role C failure path:
  (1) Grok 4.3 → fail
  (2) own_chain: empty (grok-3 retired 2026-05-15)
  (3) shared pool immediately → Gemini (cross-family)
  Result: zero intra-family buffer. First failure crosses family.
```

### 3.3 The Retirement-Drift Inheritance

A and B are currently safer than C because their same-provider fallback models are still active. They inherit C's vulnerability on the day their fallback models retire. The pattern:

1. Provider retires a model.
2. `model_config.py` is updated (or not) to reflect the retirement.
3. If `own_chain` is not repaired, it becomes empty or points to a retired model.
4. First failure on that role crosses family silently (unless the startup guard below fires).

This is not a Grok-specific problem. It is a lifecycle management gap in the evaluator chain config. Any role can reach this state. The design must prevent the state, not just document it after it occurs.

---

## 4. Proposed Chain Fix

### 4.1 Failure Classification: Transient vs Hard

Observed trigger types (from `_classify_failure`):

| Classification | Signals | Meaning | Retry appropriate? |
|---|---|---|---|
| `malformed_response` | JSON parse fail, "not a list", NoneType | Inference completed but output is unparseable. May succeed on retry. | Yes |
| `empty_response` | Empty string from non-gpt model | Inference may have dropped completion. May succeed on retry. | Yes |
| `truncation` | Unclosed JSON, not ending `]`/`}` | Output cut off mid-stream. May succeed on retry. | Yes |
| `reasoning_exhaustion` | Empty from gpt-5.x | GPT-5.x reasoning budget exceeded. Retry with shorter prompt or split. Structural for this input. | Maybe (see B-split) |
| `api_error` | HTTP 4xx/5xx, timeout, rate limit, connection failure | Provider-side failure, not inference-specific. Retry may help for rate limits; may not for 5xx. | Context-dependent |
| `provider_unavailable` | "degraded" or "already claimed" | Health tracker says degraded, or provider claim lock contention. | No (will fail immediately) |
| `unknown` | None of the above | Unknown. | No (cannot predict) |

**Transient class** (retry same model): `malformed_response`, `empty_response`, `truncation`. These are the two triggers actually observed in the 412 dataset.

**Hard class** (no same-model retry; behavior is mode-decided): `api_error` (provider outage, auth failure), `provider_unavailable`, `reasoning_exhaustion`, `unknown`.

### 4.2 Role C Same-Model Retry (Transient Failures)

Add one retry of the same Grok 4.3 model before proceeding to Phase 1 own_chain (which is empty) and Phase 2 shared pool. This is not a new fallback model; it is a second attempt at the same model.

**Design constraint:** the retry must only fire for transient-class failures. Hard-class failures (provider outage, auth) must not be retried against the same endpoint — they would fail again, waste time, and delay the fallback.

**Implementation location:** inside `_try_call` or between `_try_call` and the own_chain loop, scoped to Phase 1 primary slot only.

**Number of retries:** one. The 412 observations show two distinct trigger types (`malformed_response`, `empty_response`) that would likely succeed on a second attempt if the failure was transient. Adding more than one retry risks masking structural failures as intermittent.

**Delay:** none required. Transient API failures typically do not require backoff at this timescale (model inference, not rate limiting). If the failure was a rate limit (`api_error` class), the retry would NOT fire (hard class), so no backoff penalty from this path.

### 4.3 Same-Model Retry Does Not Solve Hard Failures

A same-model retry is not a substitute for a true same-provider fallback. If Grok 4.3 is retired, deprecated, or unreachable at the provider level, the retry will also fail (hard class, no retry). In that case:

- `own_chain` is still empty.
- Behavior is mode-decided (Section 6 below).
- Canonical mode: abstain for the affected LP, mark `evaluator_degraded`.
- Product mode: cross to shared pool with `run_degraded=True`.

**The spec must state explicitly:** a same-model transient retry is a buffer against transient API failures. It does not provide a same-family fallback identity. A run where the retry fails and the shared pool fires is still a cross-family substitution and must be marked accordingly.

### 4.4 A and B Chain (No Immediate Change Required)

Roles A and B currently have functioning same-provider chains. No change to their chains is required by this spec. However, the retirement-drift guard (Section 5) should validate all three roles at startup — ensuring that if Haiku or GPT-5.4 become unreachable, the system warns loudly rather than silently inheriting C's gap.

---

## 5. Retirement-Drift Guard (New, Required)

### 5.1 Problem

The current chain configuration is verified only at deploy time (manual review of model_config.py and lease_coverage_305.py). When a provider retires a model:

1. API calls to the retired model begin failing.
2. `own_chain` entries pointing to the retired model become dead links.
3. The next evaluator failure skips the retired model and crosses to the shared pool, with is_fallback=True correctly recorded but no startup alarm raised.

The system degrades silently. The retirement of grok-3 was handled by updating the comment and setting `own_chain: []`, but there was no enforcement preventing a run from proceeding with a degraded chain configuration.

### 5.2 Proposed Guard

Add a startup or pre-run validation step that:

1. **Inspects each role's configuration:** For every role (A, B, C), verify that `own_chain` is non-empty OR the role has a declared no-fallback justification (e.g., `own_chain_empty_reason: "no_active_same_provider_model"`). An empty `own_chain` with no declared justification should be treated as a configuration error, not a valid state.

2. **Optionally probes reachability:** For each configured primary and fallback model, issue a minimal health-check call (or consult the provider health tracker) at startup. A model that fails the health check marks the chain as degraded before the first LP is evaluated.

3. **Fails loudly on degraded chain config:** If any role's chain is deficient (empty `own_chain` with no justification, or a fallback model that fails health check), the guard should:
   - In **canonical/patent/benchmark mode:** refuse to start the run. Emit a clear error: "Role C has no same-provider fallback. Canonical run cannot proceed with a degraded evaluator chain. Repair the chain or accept degraded-mode operation with explicit flags."
   - In **product/permissive mode:** warn loudly, set `run_config_degraded=True` in the run metadata, but allow the run to proceed with cross-family fallback behavior and the degraded flag propagated to the output.

4. **Converts manual tracking to machine enforcement:** The current state is "track provider retirements by hand and update comments." The guard makes the chain integrity check automatic. Hand-patching C's chain (adding a new XAI model when one becomes available) remains required, but the guard ensures no run silently proceeds with an empty chain.

### 5.3 Retirement-Drift Invariant (Durable)

```
For each evaluator role R:
  If own_chain(R) is empty and no cross-family substitution is permitted in the current mode:
    FAIL at config-load time, not at first evaluator call.
  If own_chain(R) is empty and cross-family substitution is permitted:
    LOG the degraded chain state at startup, set run_config_degraded=True.
    Every cross-family fallback in this run is expected and must still set is_fallback=True.
```

This converts the timing of the failure from "first evaluator call that fails" (runtime, buried in parallel thread pool output) to "config load" (pre-run, visible in the startup log and in the run metadata).

---

## 6. Run-Level Degraded Flag

### 6.1 Current State

The `is_fallback=True` flag exists per-element and per-LP. There is no top-level run flag indicating that at least one evaluator used a non-canonical model. A downstream consumer reading `pipeline_results.json` must scan all 32 LPs' `lp_meta.fallback_used` fields to determine whether any fallback occurred.

### 6.2 Proposed Run-Level Degraded Field

Add to the top-level `pipeline_results.json` (or to the run metadata object):

```json
{
  "run_degraded": false,
  "degraded_reason": null,
  "fallback_events": []
}
```

When any evaluator fallback occurs:

```json
{
  "run_degraded": true,
  "degraded_reason": "evaluator_fallback",
  "fallback_events": [
    {
      "stage": "305",
      "lp_id": "LP-29",
      "role": "C",
      "requested_model": "grok-4.3",
      "requested_provider": "xai",
      "actual_model": "gemini-2.5-pro",
      "actual_provider": "google",
      "fallback_reason": "malformed_response",
      "fallback_class": "transient",
      "same_provider_retry_attempted": true,
      "same_provider_retry_succeeded": false,
      "timestamp": "2026-07-08T..."
    }
  ]
}
```

Key fields:
- `run_degraded`: boolean. True if any evaluator used a non-canonical model in any stage.
- `degraded_reason`: string enumeration. `"evaluator_fallback"` | `"chain_config_degraded"` | `null`.
- `fallback_events`: list. One entry per fallback event (per LP × role). Empty list if no fallbacks.
- Per-event: `requested_model` / `actual_model` (never conflated); `fallback_class` (`transient` / `hard`); `same_provider_retry_attempted` (did the retry logic fire?); `same_provider_retry_succeeded` (did the retry succeed, avoiding cross-family?).

### 6.3 Propagation Rule

```
run_degraded = any(lp.lp_meta.fallback_used for lp in coverage_assessment)
            OR run_config_degraded (from startup guard)
```

The `run_degraded` flag must be written as part of the standard pipeline output alongside `pipeline_results.json`. It must not require post-hoc scanning of LP-level fields to detect.

### 6.4 Downstream Use

- **Benchmark/patent/reproducibility pipelines:** filter out runs where `run_degraded=true` or require explicit justification before inclusion.
- **Product runs:** display a minimal audit indicator (admin-side only; not lawyer-facing) when `run_degraded=true`.
- **Monitoring:** aggregate `fallback_events` across runs over time to characterize Grok failure rate by LP, trigger type, and timestamp.

---

## 7. Strict vs Permissive Modes

### 7.1 Mode Definition

| Mode | When used | Fallback policy |
|---|---|---|
| **Canonical** (patent / benchmark / reproducibility) | Runs intended to demonstrate or document the frozen-stack method. Results may be cited in patent applications, reproducibility claims, or external validation. | Fail closed on cross-family fallback. Allowed: same-provider retry (transient), evaluator abstention with provenance, run marked `run_degraded=true`. NOT allowed: unmarked cross-family substitution. |
| **Product** (operational, client-facing) | Standard client lease reviews. Run completes with Gemini verdict when Grok fails. | Fallback allowed. run_degraded=true required. is_fallback=True required. Cross-family substitution permitted but must never serve as canonical reproducibility evidence. |
| **Debug** (local development) | Debugging, smoke tests, prompt iteration. | Fallback allowed. Loud provenance logging required. Never counted as benchmark output. run_degraded=true required. |

### 7.2 Canonical Mode: Fail-Closed Behavior

When canonical mode is active and a cross-family fallback fires:

1. **Preferred:** abort the LP evaluation for the failed evaluator role. Record:
   - `evaluator_meta.C.completed = false`
   - `evaluator_meta.C.error = "canonical_mode_cross_family_fallback_aborted"`
   - `evaluator_meta.C.abstained = true`
   - `evaluator_meta.C.abstain_reason = "primary_failed_no_same_provider_retry_succeeded"`
2. Proceed with 2/3 evaluators for that LP (A and B). Governance rules for incomplete evaluator set apply (lower confidence ceiling; Review Needed propagation as warranted).
3. `run_degraded = true`, `degraded_reason = "evaluator_fallback"`, fallback event recorded.
4. The run is NOT counted as a clean canonical run. It may be reported as a "2-evaluator degraded run" for the affected LPs, but it cannot be reported as a "3-evaluator frozen-stack run."

The **abstain** output is not an error state — it is an honest output. The alternative (silently using Gemini) is worse because it passes a non-canonical result off as canonical.

### 7.3 Product Mode: Fallback-With-Provenance Behavior

Current behavior, with additions:
1. Same-model transient retry fires first (new, Section 4).
2. If retry fails or failure is hard class, shared pool fires (current behavior, unchanged).
3. `is_fallback=True`, `actual_model`, `fallback_reason` recorded (current behavior, 372a).
4. `run_degraded=true`, `fallback_events` record appended (new, Section 6).
5. Gemini verdict used for that LP's affected role (current behavior).
6. No user-visible alarm; admin-side audit fields only (current behavior per 372a note).

### 7.4 Mode Switch Mechanism

A run-time configuration flag (e.g., `evaluator_fallback_mode: "canonical" | "product" | "debug"`) in the pipeline run configuration. The startup guard (Section 5) reads this flag to determine whether to refuse or warn on a degraded chain config.

If the flag is absent, default to `product` mode. Canonical mode must be explicitly activated; it should never be the default because it would abort operational runs on transient API failures.

---

## 8. Material-Impact Handling

### 8.1 Provenance Completeness

The provenance record must always carry:
- `requested_model`: the model that was supposed to answer (the role's primary model)
- `actual_model`: the model that actually answered
- `fallback_reason`: why the primary failed (from `_classify_failure`)
- `fallback_class`: `transient` or `hard` (derived from `fallback_reason` mapping)
- `is_fallback`: boolean (already implemented)
- `same_provider_retry_attempted`: boolean (new)
- `same_provider_retry_succeeded`: boolean (new)

### 8.2 No Identity Normalization

The Gemini verdict must never be labeled or stored as if it came from the Grok role. The 372a fix prevents this at the verdict-output level. This spec extends the rule: no downstream processing step (report generation, synthesis aggregation, audit export) may present a Gemini-sourced verdict as a Grok-sourced verdict. The `role` field identifies the evaluator SLOT (A/B/C); the `actual_model` field identifies the ANSWERING model. Both must be preserved through all downstream stages.

### 8.3 Verdict-Change Flag (Where Available)

In runs where a same-LP paired comparison exists (two runs of the same lease, one with Grok and one with Gemini for the same LP), the verdict-change flag should be recorded:

```json
"fallback_verdict_vs_primary": {
  "available": true,
  "primary_verdicts": {"LP-29.minimize_interference": "missing"},
  "fallback_verdicts": {"LP-29.minimize_interference": "explicitly_present"},
  "verdict_diverged": true
}
```

This field is only available when a paired run exists; it must be left absent (not null) when no comparison is available, to avoid implying "no divergence."

---

## 9. Temperature and Config Deferral

**Temperature=0 and fallback integrity are orthogonal dimensions.** Temperature controls sampling variance within a single completed model call. Fallback integrity controls evaluator identity. Resolving fallback integrity does not depend on temperature; resolving temperature behavior does not address fallback.

**Deferral rationale:** fallback changes evaluator identity, which is a more fundamental invariant than temperature setting. A run where temperature is not confirmed at 0 but evaluator identity is preserved is a better-characterized run than a run where temperature is confirmed at 0 but one evaluator is silently Gemini. Fix the identity invariant first.

**After 413 is implemented and validated:** run a separate temperature/config trace (candidate Step 414 or equivalent):
- Confirm temperature=0 is actually transmitted to all providers in all evaluator call paths (the `temperature` field in `ModelTarget` and whether each provider honors it).
- Confirm provider behavior where visible (e.g., XAI API may not expose temperature confirmation in response metadata).
- Separate provider-level stochasticity (behavior at temperature=0 is still not perfectly deterministic for all providers) from model-substitution effects (currently conflated in the 411 nondeterminism data).

Do not mix temperature confirmation with the fallback integrity work. They are separate investigations.

---

## 10. Validation Plan

**No cam/core/ changes.** All changes are in `cam/adapters/lease_review/` (lease_coverage_305.py, model_config.py) and the pipeline run metadata writer. The evaluator governance logic in cam/core/ is not touched.

**No routing, bucket, or Priority Exposure changes.** This spec is scoped to evaluator-chain integrity and run-level provenance. Stage 7 findings, compound synthesis, and the Priority Exposure module are out of scope.

### 10.1 Config Inspection

- After implementation: inspect `EVALUATOR_LINEUP_305` to confirm Role C `own_chain` contains exactly one Grok 4.3 same-model retry entry (or a designated XAI same-provider target if one becomes available).
- Confirm `own_chain` for A and B are unchanged and point to live models.
- Confirm `_SHARED_FALLBACK_POOL` is unchanged.

### 10.2 Transient Failure Retry Validation

- Simulated test: mock the Grok adapter to return `malformed_response` on first call, succeed on second call.
- Expected result: same-model retry fires (second call succeeds); `is_fallback=False` in output (primary model succeeded on retry); no cross-family substitution; no fallback_event recorded.
- Simulated test: mock to return `empty_response` on first call, succeed on second.
- Expected result: same as above.

### 10.3 Hard Failure Validation

- Simulated test: mock Grok adapter to return `api_error` (hard class) on all calls.
- Canonical mode: expected result — evaluator-C abstains for the LP; `completed=false`, `abstained=true`; `run_degraded=true`; Gemini NOT called for this LP.
- Product mode: expected result — same-model retry does NOT fire (hard class); Gemini called from shared pool; `is_fallback=True`, `actual_model=gemini-2.5-pro`; `run_degraded=true`, fallback_event recorded.
- Simulated test: mock Grok to return `malformed_response` on first call AND second call (transient retry also fails).
- Expected result: after retry fails, behavior is same as hard-failure path (canonical: abstain; product: Gemini).

### 10.4 Startup Guard Validation

- Config with `own_chain=[]` and no justification field → startup guard fires; error emitted; run refused in canonical mode; warning + `run_config_degraded=True` in product mode.
- Config with `own_chain=[]` and `own_chain_empty_reason="no_active_same_provider_model"` → guard passes; warning logged; run proceeds with `run_config_degraded=True`.
- Config with `own_chain=["grok-3.0"]` (retired model, health check fails) → guard fires same as empty-chain case.

### 10.5 Provenance Event Validation

- After a successful same-model retry: no fallback_event in `fallback_events`; `is_fallback=False`.
- After a cross-family substitution (product mode): `fallback_events[0]` contains all required fields; `same_provider_retry_attempted=true`, `same_provider_retry_succeeded=false`; `fallback_class` matches trigger type.
- `run_degraded=true` in top-level metadata.

### 10.6 Run-Level Degraded Flag

- Confirm `run_degraded=true` appears in `pipeline_results.json` top-level when any LP's `lp_meta.fallback_used=true`.
- Confirm `run_degraded=false` when no LP has fallback_used=true.
- Confirm fallback_events list is empty when no fallbacks occurred.

---

## 11. Patent and Claim Handling

**413 does not change the patent doctrine directly.** It changes the implementation to better match the doctrine already described (frozen stack; evaluator identity; provenance).

**If 413 is implemented and validated, update `Docs/Patent_Current_State.md`:**
- Canonical runs require evaluator-identity integrity. A run is canonical only if either (a) no fallback occurred, or (b) only same-provider intra-family fallback occurred (e.g., Sonnet → Haiku) with explicit run_degraded marking.
- Cross-family fallback runs (e.g., Grok → Gemini) are non-canonical regardless of is_fallback provenance. They may be used for product availability but cannot serve as clean benchmark proof.
- Fallback-with-provenance is acceptable for product/operational availability (no silent laundering; run_degraded propagated; is_fallback=True per verdict). It is not acceptable as canonical reproducibility evidence.
- Full supplement (dedicated patent document) deferred until after implementation and validation. 412 is a candidate note; 413 RTP is the supplement trigger.

**Doctrine precedent:** evaluator identity is analogous to the "deliberate non-deliberation" principle (Supplement #22) — the architecture makes a deliberate structural choice (three-provider diversity) that must be enforced at the implementation layer, not just declared in the config. A system that claims three-provider evaluation but silently substitutes a fourth provider for one role on API failure has a gap between doctrine and execution. 413 closes that gap.

---

## 12. Implementation Checklist

*Not authorized for execution in this session. Listed for Step 413 implementer.*

1. **Config inspection:** Read `model_config.py` and `EVALUATOR_LINEUP_305` in `lease_coverage_305.py`. Document current state of all three roles' `own_chain` entries.

2. **Add/repair Role C same-provider retry:** In `lease_coverage_305.py`, within `_call_single_evaluator_305`, add one transient-class retry of the primary model before proceeding to `own_chain` iteration. Gate retry on `_classify_failure` result: only transient class (`malformed_response`, `empty_response`, `truncation`) triggers retry. Hard class (`api_error`, `provider_unavailable`, `reasoning_exhaustion`, `unknown`) goes directly to own_chain / shared pool.

3. **Add transient-vs-hard branching:** Extend `_classify_failure` or add a `_is_transient_failure(reason)` helper that maps failure classifications to retry eligibility.

4. **Add retirement-drift startup guard:** Add a `_validate_evaluator_chains(lineup, mode)` function called at pipeline startup (or before the Stage 305 loop begins). Guard logic: empty own_chain with no `own_chain_empty_reason` → fail in canonical mode, warn + set `run_config_degraded=True` in product mode.

5. **Add strict/permissive mode switch:** Determine where the mode flag lives (run config dict, environment variable, or pipeline call parameter). Plumb it through to `_validate_evaluator_chains` and the fallback abort path.

6. **Add run-level degraded flag:** Add `run_degraded`, `degraded_reason`, `fallback_events` to the pipeline output object. Populate from LP-level `lp_meta.fallback_used` scan at pipeline completion. Ensure `fallback_events` is written with all required fields when a fallback fires.

7. **Propagate provenance to final artifact:** Confirm the three-level provenance (per-element, per-LP evaluator_meta, LP lp_meta) still writes correctly after the retry logic is added. The retry must not suppress `is_fallback=True` when a cross-family fallback occurs after a failed same-model retry.

8. **Add tests / simulated provider failure:**
   - Transient retry test: mock Grok → malformed_response (first), success (second). Assert no fallback_event.
   - Hard failure, canonical mode: mock Grok → api_error. Assert abstain + no Gemini call.
   - Hard failure, product mode: mock Grok → api_error. Assert Gemini called + run_degraded=true.
   - Startup guard: mock `own_chain=[]` with no justification. Assert guard fires in canonical mode.
   - Startup guard: same config in product mode. Assert warn + run_config_degraded=True.

9. **No broad model changes.** Do not change evaluator primary models (A/B/C configured stack). Do not change `_SHARED_FALLBACK_POOL`.

10. **No Priority Exposure changes.** Do not touch Stage 7, compound synthesis, or the Priority Exposure module. Those are downstream; this fix is upstream.

11. **No push.** Until explicitly authorized.

---

*Design artifact: Step 413. No code changes. Read-only investigation and design. No push.*
