# 415 — Temperature / Config Transmission Trace

**Date:** 2026-07-12
**Type:** Read-only measurement. No code change, no prompt change, no push.
**Purpose:** Determine per-provider whether `temperature=0` is (a) declared in config, (b) actually transmitted in the API call, and (c) documented as honored by the provider. Distinguish the four root-cause tiers: not-set / not-transmitted / transmitted-but-ignored / genuinely-nondeterministic model.

**Files read:**
- `cam/adapters/lease_review/lease_evaluate.py` — Stage 2 evaluator config and ModelTarget construction
- `cam/adapters/lease_review/lease_coverage_305.py` — Stage 5 evaluator config and ModelTarget construction
- `cam/adapters/lease_review/lease_synthesis.py` — Stage 7 evaluator config
- `cam/core/provider_router.py` — All four provider adapters (Anthropic, OpenAI, xAI, Google)
- `cam/adapters/lease_review/model_config.py` — Central model registry
- `build_log/411_stage5_coverage_reproducibility_trace.md` — Empirical flip data

---

## 1. Executive Summary

**Primary finding: Evaluator B (GPT-5.5 / gpt-5.4) never receives `temperature=0`.** The OpenAI adapter at `cam/core/provider_router.py:220–228` explicitly omits the `temperature` parameter for all `gpt-5.*` models. The provider default (temperature=1) governs every Role B call across Stage 2, Stage 5, and Stage 7. The `temperature=0.0` declared in all three stages' evaluator config dicts is set, but silently dropped before the API call. This is a **not-transmitted** failure for Role B.

**Secondary finding: Role A (Claude Sonnet 4.6) transmits temperature=0 correctly for Stage 2, 5, and 7 (primary path), but extended-thinking mode suppresses temperature — any future reasoning_effort flag on Role A would silently drop temperature again.**

**Role C (Grok 4.3) transmits temperature correctly via the xAI adapter for all stages.**

**No seed parameter is used anywhere in the lease pipeline.** `seed` appears only in sampling harnesses for SciFact and ContractNLI (Python-RNG seeds, not API-level), not in any provider adapter or ModelTarget construction.

**Empirically confirmed same-model no-fallback verdict flips exist for Roles A, B, and C** across the 17 element flips measured in Step 411. Minimum one example per role is documented below.

**Root-cause classification:** Role B (OpenAI gpt-5.x) operates at the not-transmitted tier — temperature is declared but dropped. Roles A and C operate at the transmitted tier. The residual nondeterminism in Roles A and C after the 414 fallback fix is either transmitted-but-not-honored or genuinely-nondeterministic; this cannot be resolved from code and artifacts alone (see §6).

---

## 2. Config Declaration: Per-Role, Per-Stage

### Stage 2 — `cam/adapters/lease_review/lease_evaluate.py`

```python
# lease_evaluate.py lines 61–99
EVALUATORS = {
    "A": {
        "provider": "anthropic",   "model": "claude-sonnet-4-6",
        "temperature": 0.0,        # line 68
        "reasoning_effort": None,  # key absent — defaults to None via .get()
    },
    "B": {
        "provider": "openai",      "model": "gpt-5.5",
        "temperature": 0.0,        # line 80
        "reasoning_effort": "medium",  # line 82 — ONLY in Stage 2
    },
    "C": {
        "provider": "xai",         "model": "grok-4.3",
        "temperature": 0.0,        # line 93
    },
}
```

`temperature=0.0` is declared per-role in the `EVALUATORS` dict. It is not global — each role carries its own copy. Stage 2 is the only stage where Role B has an explicit `reasoning_effort`.

### Stage 5 — `cam/adapters/lease_review/lease_coverage_305.py`

```python
# lease_coverage_305.py lines 93–122
EVALUATOR_LINEUP_305 = {
    "A": { "provider": "anthropic", "model": "claude-sonnet-4-6", "temperature": 0.0 },  # line 99
    "B": { "provider": "openai",    "model": "gpt-5.5",           "temperature": 0.0 },  # line 108
    "C": { "provider": "xai",       "model": "grok-4.3",          "temperature": 0.0 },  # line 117
}
# No reasoning_effort key in any Stage 5 evaluator entry.
```

All three roles declare `temperature=0.0`. No `reasoning_effort` anywhere in Stage 5.

### Stage 7 — `cam/adapters/lease_review/lease_synthesis.py`

```python
# lease_synthesis.py lines 56–84
EVALUATOR_LINEUP = {
    "A": { "provider": "anthropic", "model": "claude-sonnet-4-6", "temperature": 0.0 },  # line 63
    "B": { "provider": "openai",    "model": "gpt-5.4",           "temperature": 0.0 },  # line 71
    # Note: Stage 7 B-model is gpt-5.4, not gpt-5.5 (gpt-5.5 RuntimeError on long prompts)
    "C": { "provider": "xai",       "model": "grok-4.3",          "temperature": 0.0 },  # line 80
}
# No reasoning_effort key in any Stage 7 evaluator entry.
```

Step 410 claimed Stage 7 runs at temperature=0. **Claim verified at config level.** However, the transmission gap documented in §3 applies identically here for Role B.

### Summary: Config Declaration

| Role | Provider | Stage 2 | Stage 5 | Stage 7 | reasoning_effort (Stage 2) |
|------|----------|---------|---------|---------|----------------------------|
| A | anthropic | 0.0 ✓ | 0.0 ✓ | 0.0 ✓ | absent |
| B | openai | 0.0 ✓ | 0.0 ✓ | 0.0 ✓ | "medium" (Stage 2 only) |
| C | xai | 0.0 ✓ | 0.0 ✓ | 0.0 ✓ | absent |

Temperature=0.0 is set at config level for every role in every stage. The declaration is correct everywhere.

---

## 3. Transmission Trace: Config → API Call

### 3a. Role B — OpenAI Adapter (CRITICAL FINDING)

The ModelTarget construction in Stage 2 (`lease_evaluate.py:334–342`):

```python
target = ModelTarget(
    name=f"{provider}:{model_name}-eval-{evaluator_key}",
    provider=provider,
    model=model_name,
    priority=1,
    max_output_tokens=evaluator_cfg.get("max_output_tokens", 8000),
    temperature=evaluator_cfg.get("temperature", 0.0),   # 0.0 from EVALUATORS["B"]
    timeout_sec=evaluator_cfg.get("timeout_sec", EVALUATOR_ATTEMPT_TIMEOUT),
    reasoning_effort=evaluator_cfg.get("reasoning_effort") if is_own else None,  # "medium" for Stage 2
)
```

`target.temperature = 0.0` is correctly set on the ModelTarget object. But the OpenAI adapter at `cam/core/provider_router.py:207–244` (`_call_once`):

```python
# provider_router.py lines 216–228
params = {
    "model": target.model,
    "messages": messages,
}
# GPT-5.2 requires max_completion_tokens instead of max_tokens
# GPT-5.2 only supports default temperature (1), not custom values
if target.model.startswith("gpt-5"):
    params["max_completion_tokens"] = target.max_output_tokens
    # Don't set temperature for GPT-5.2 (uses default 1)
else:
    params["max_tokens"] = target.max_output_tokens
    params["temperature"] = target.temperature
```

**`temperature` is unconditionally absent from `params` for any model matching `gpt-5*`.** This covers gpt-5.5 (Stage 2 primary B), gpt-5.4 (Stage 2 B-fallback and Stage 7 B), gpt-5.2 (SINGLE_STAGE_CHAIN), and gpt-4o (SINGLE_STAGE_CHAIN non-5 branch, but gpt-4o does not match `gpt-5*` so it WOULD receive temperature).

The comment says "GPT-5.2 only supports default temperature (1)" but the condition applies to ALL gpt-5.x models. Whether this restriction is correct for gpt-5.5 and gpt-5.4 specifically is an API question (see §5), but the practical effect is clear: **temperature=0.0 is never sent for Role B in any stage.**

**For Stage 5 Role B** (`lease_coverage_305.py:425–432`):

```python
target = ModelTarget(
    name=f"{provider}:{model}-305-{role}-{pid}",
    provider=provider,
    model=model,
    max_output_tokens=budget,
    temperature=evaluator_cfg.get("temperature", 0.0),   # 0.0
    timeout_sec=evaluator_cfg.get("timeout_sec", 300.0),
)
```

Same ModelTarget construction, same adapter, same omission. No `reasoning_effort` in Stage 5 evaluator B config — so `target.reasoning_effort = None` — but temperature omission is unconditional on the gpt-5.x branch regardless of reasoning_effort.

### 3b. Role A — Anthropic Adapter

The Anthropic adapter at `cam/core/provider_router.py:294–338`:

```python
# provider_router.py lines 304–322
params = {
    "model": target.model,
    "max_tokens": target.max_output_tokens,
    "system": system_prompt,
    "messages": [{"role": "user", "content": user_prompt}],
}

# Enable extended thinking if reasoning_effort is set
if target.reasoning_effort:
    budget_map = {"low": 5000, "medium": 10000, "high": 20000, "xhigh": 32000}
    budget = budget_map.get(target.reasoning_effort, 10000)
    params["thinking"] = {"type": "enabled", "budget_tokens": budget}
    # Extended thinking doesn't support custom temperature
else:
    params["temperature"] = target.temperature   # line 320
```

**When `target.reasoning_effort` is None (all current Role A configurations), `temperature=target.temperature` is included in the request.** For Stage 2/5/7 Role A, `reasoning_effort` is absent from the evaluator config dict, so `target.reasoning_effort = None`, and `temperature=0.0` is transmitted.

**Edge case: if `reasoning_effort` were ever added to Role A config, temperature would be silently dropped** (same pattern as the OpenAI adapter, with a different condition). This is not a current risk but is a latent trap.

### 3c. Role C — xAI Adapter

The xAI adapter at `cam/core/provider_router.py:601–628`:

```python
# provider_router.py lines 610–618
resp = client.chat.completions.create(
    model=target.model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=target.temperature,       # line 615 — unconditionally included
    max_tokens=target.max_output_tokens,
)
```

**`temperature=target.temperature` is unconditionally included in every xAI call.** For Role C (grok-4.3), `temperature=0.0` is transmitted in all three stages. No `reasoning_effort` key exists in any Role C evaluator config, so no conditional branch suppresses temperature.

### Transmission Summary

| Role | Provider | Temperature set on target | Temperature in API params | Net state |
|------|----------|--------------------------|--------------------------|-----------|
| A | anthropic | 0.0 | YES (no reasoning_effort) | transmitted |
| B | openai (gpt-5.x) | 0.0 | **NO** — gpt-5.x branch omits it | **not-transmitted** |
| C | xai | 0.0 | YES (unconditional) | transmitted |

---

## 4. Seed / Determinism Parameters

### OpenAI Chat Completions API

The OpenAI `chat.completions.create` API supports a `seed` parameter (integer). When present, it requests deterministic sampling — "with the same seed and parameters, you should receive the same result." This was introduced for gpt-4 and gpt-4o; its support for gpt-5.x models has not been confirmed in available documentation.

**Usage in the lease pipeline:** `seed` is **not set** anywhere in the `OpenAIAdapter._call_once` method or in any `params` dict. No seed parameter is present for any Role B call.

**For non-lease adapters:** The `seed` parameter in `scifact_adapter.py` and `contractnli_adapter.py` is a Python `random.seed()` call for dataset sampling — not an API-level determinism parameter. These are unrelated.

### Anthropic Claude API

Anthropic's API does not expose a `seed` or equivalent determinism parameter in the standard `messages.create` interface. The API documentation states that outputs "may vary even for identical inputs" and does not guarantee reproducibility at temperature=0. No seed-equivalent exists to implement.

### xAI (Grok) API

xAI's Grok API uses the OpenAI-compatible endpoint (`https://api.x.ai/v1`). Whether Grok supports a `seed` parameter is not documented in available xAI API documentation at the time of this trace. No seed parameter is set in `XAIAdapter.call`.

### Google GenAI API

Google's GenAI API does not use a `seed` parameter in the config dict structure used by the `GoogleGenAIAdapter`. The `config` dict (`cam/core/provider_router.py:378–381`) includes only `temperature` and `max_output_tokens`. No seed equivalent exists for Gemini.

### Seed Summary

| Provider | Seed/determinism param in API | Set in adapter | Available |
|----------|------------------------------|----------------|-----------|
| OpenAI | `seed` exists for gpt-4/4o; gpt-5.x status unclear | Not set | Unknown for gpt-5.x |
| Anthropic | Not available | N/A | No |
| xAI | Possibly available (OpenAI-compat); undocumented | Not set | Unknown |
| Google | Not available | N/A | No |

---

## 5. Other Sampling Parameters

| Role | Provider | top_p | top_k | penalties | reasoning_effort |
|------|----------|-------|-------|-----------|-----------------|
| A | anthropic | not set | not set | not set | absent (normal mode) |
| B | openai (Stage 2) | not set | not set | not set | "medium" |
| B | openai (Stage 5/7) | not set | not set | not set | absent |
| C | xai | not set | not set | not set | absent |

Neither `top_p` nor `top_k` nor any penalty parameters are set in any of the three provider adapters for the evaluator roles. The `reasoning_effort="medium"` on Stage 2 Role B is an OpenAI-specific parameter that controls the internal reasoning depth of the o-series / gpt-5 reasoning models; it has an uncertain relationship with output determinism (see §6).

---

## 6. Provider Documentation: Determinism at temperature=0

### Anthropic (Role A)

Anthropic's published documentation states: "Constraining to temperature=0 does reduce the range of outputs but does not completely eliminate variation." Anthropic explicitly does **not** guarantee deterministic outputs at temperature=0. The underlying cause cited is floating-point non-associativity in GPU arithmetic — the same computation run across different hardware or batch configurations can produce slightly different softmax outputs, which at temperature=0 are amplified into discrete token selection differences.

**Claim status: transmitted. Honored documentation status: provider explicitly disclaims determinism at temperature=0 for Claude.** Residual Role A flip rate is consistent with this documented behavior.

### OpenAI (Role B)

OpenAI's documentation for the `seed` parameter states: "Deterministic outputs are not guaranteed even when a seed is used; there may still be small differences due to system updates or floating-point arithmetic." For gpt-5.x models specifically, the relationship between temperature and output variance is complicated by the reasoning-model architecture: the internal chain-of-thought generation uses its own sampling parameters independent of the output temperature.

**Current state: temperature is not transmitted for gpt-5.x (not-transmitted tier).** Role B effectively runs at provider default, which OpenAI documents as temperature=1 for reasoning models in this family. Even if temperature were transmitted, OpenAI does not guarantee determinism for the gpt-5.x reasoning model family at temperature=0.

### xAI (Role C)

xAI's public documentation for Grok does not explicitly address temperature=0 determinism. The API is OpenAI-compatible and accepts the `temperature` parameter. Based on general LLM inference architecture, temperature=0 should enforce greedy decoding, but hardware-level FP non-associativity caveats apply identically to those documented by Anthropic.

**Claim status: transmitted. Honored documentation status: undocumented. Cannot assert honoring without provider-level evidence or controlled measurement.**

---

## 7. Empirical Evidence: Same-Model No-Fallback Verdict Flips

From Step 411 artifact data (`05 Lease Analyzer/results/lease_408c_atreca_run{A,B}/pipeline_results.json`), the following flips have no fallback involvement (primary model in both runs, `is_fallback=False` implied by evaluator identity staying constant):

### Eval-A (Claude Sonnet 4.6) — Role A, primary model both runs

**LP-26, element `constructive_eviction_addressed`:**
- Run A: Claude = `unclear`
- Run B: Claude = `missing`
- Other evaluators: Grok = `missing` (stable), GPT = `covered_in_other_LP` (stable)
- is_fallback for C: False (Grok answered as primary both runs for LP-26)

**LP-26, element `remedies_for_breach_of_quiet_enjoyment`:**
- Run A: Claude = `covered_in_other_LP`
- Run B: Claude = `implicitly_present`
- Other evaluators: C = `covered_in_other_LP` (stable), B = `covered_in_other_LP` (stable)

**LP-28, element `landlord_delivery_compliance`:**
- Run A: Claude = `missing`
- Run B: Claude = `explicitly_present`
- Other evaluators: stable (B=missing, C=missing both runs)

All three Claude flips are same-model (claude-sonnet-4-6), same role (A), primary model in both runs. Temperature=0.0 is transmitted to the Anthropic API for Role A. Anthropic's documentation states temperature=0 does not guarantee determinism. These flips are consistent with **transmitted-but-not-guaranteed** behavior at the provider level.

### Eval-B (GPT-5.5) — Role B, primary model both runs (no fallback for B)

**LP-01, element `accepted_payment_methods`:**
- Run A: GPT = `missing`
- Run B: GPT = `implicitly_present`
- Other evaluators: A=`implicitly_present` (stable), C=`implicitly_present` (stable)

**LP-09, element `assignee_or_subtenant_assumes_obligations`:**
- Run A: GPT = `explicitly_present`
- Run B: GPT = `missing`
- Other evaluators: A=`explicitly_present` (stable), C=`explicitly_present` (stable)

**LP-05, element `co_tenancy_anchor_dependency`:**
- Run A: GPT = `unclear`
- Run B: GPT = `missing`
- Other evaluators: A=`missing` (stable), C=`covered_in_other_LP` (stable)

GPT-5.5 is the sole changer on all three elements. No Role B fallback is documented anywhere in the 411 artifact (Role B failover triggers only on API error; gpt-5.5 answered for all LPs in both runs). **These flips are same-model (gpt-5.5), primary in both runs, and temperature was NOT transmitted (provider default=1 governs).** Role B is operating at temperature=1, not temperature=0. These flips are consistent with and expected from the not-transmitted root cause.

### Eval-C (Grok 4.3) — Role C, primary model both runs (excluding LP-15 and LP-29)

**LP-03, element `initial_term_duration`:**
- Run A: Grok = `explicitly_present`
- Run B: Grok = `missing`
- LP-03 is confirmed not a fallback case (LP-15 and LP-29 are the Grok-fails-to-Gemini cases; LP-03 is not listed as such in the 411 artifact)
- Other evaluators: A=`unclear` (stable), B=`explicitly_present` (stable)

**LP-22, elements `non_disturbance_obligation_for_future_lenders` and `non_disturbance_source_is_binding`:**
- Both: Grok flipped direction (Run A → Run B) as sole changer
- is_fallback: Not documented for LP-22 in the 411 artifact (Grok fallback cases are LP-15 and LP-29 only)

Temperature=0.0 is transmitted to xAI for Role C. These flips are consistent with **transmitted-but-not-guaranteed** behavior, as with Role A.

---

## 8. Root-Cause Classification

### Tier assignments

| Role | Stage | Root-cause tier | Evidence |
|------|-------|----------------|---------|
| A (claude-sonnet-4-6) | 2, 5, 7 | Transmitted, provider-documented non-deterministic | Temperature transmitted; Anthropic disclaims determinism at temp=0; same-model flips confirmed empirically |
| B (gpt-5.5) | 2 | **Not transmitted** | `gpt-5*` branch omits temperature; provider default=1; GPT flips confirmed |
| B (gpt-5.4) | 7 | **Not transmitted** | Same adapter path; gpt-5.4 matches `gpt-5*` |
| B (gpt-5.5/5.4) | 5 | **Not transmitted** | Same adapter path for Stage 5 `_do_single_call` |
| C (grok-4.3) | 2, 5, 7 | Transmitted, provider undocumented | Temperature transmitted; provider does not document determinism at temp=0; same-model flips confirmed |

### The four tiers mapped to this pipeline

1. **Not-set:** Does not apply. `temperature=0.0` is declared in every evaluator config in every stage.

2. **Not-transmitted:** Applies to Role B (all stages). The `gpt-5*` branch in `OpenAIAdapter._call_once` unconditionally omits the `temperature` parameter from the API request body. Provider default (temperature=1) governs.

3. **Transmitted-but-not-honored (or undocumented):** Applies to Role A and Role C. Temperature is transmitted, but Anthropic explicitly and xAI implicitly may not produce deterministic outputs. The residual flip rate in Roles A and C after the 414 fallback fix is consistent with this tier. Distinguishing "transmitted-not-honored" from "genuinely-nondeterministic model" cannot be done without controlled multi-run measurement at temperature=0 vs temperature=null, which this trace does not attempt.

4. **Transmitted and honored (genuinely nondeterministic model):** Cannot be ruled in or out from existing evidence. No provider guarantees determinism at temperature=0 for any model in this pipeline.

---

## 9. Recommendation

**The actionable finding is Role B (OpenAI gpt-5.x): fix the not-transmitted defect.**

The `gpt-5*` branch in `OpenAIAdapter._call_once` should be investigated to determine:
- Whether gpt-5.5 and gpt-5.4 accept `temperature=0` in the API (the comment was written for gpt-5.2, which may have had a different constraint at the time).
- If they accept it, add `params["temperature"] = target.temperature` inside the `if target.model.startswith("gpt-5")` branch.
- If they reject it (e.g., temperature is ignored or causes an error for reasoning models), document that explicitly rather than silently omitting.

This is the only defect where the fix is mechanical and the expected effect is clear: Role B currently runs at temperature=1, not temperature=0. Even if temperature=0 is not fully honored, transmitting it is the minimum required to move Role B from the not-transmitted tier to the transmitted tier.

**Roles A and C: accept irreducible nondeterminism for now.** Both providers document (Anthropic) or implicitly exhibit (xAI) non-determinism at temperature=0. The correct response is architectural: majority-of-3 consensus already attenuates single-evaluator flips. Increasing evaluator count (majority-of-5) or caching element verdicts deterministically (by input hash) are the structural fixes. These are not in scope for this step.

**No seed parameter fix is available** for Anthropic or Google. OpenAI and xAI support seeds in principle, but their effect on gpt-5.x and grok-4.3 respectively is undocumented. Adding seeds would be speculative without controlled measurement.

**Do not fix in this step.** This trace is measurement only.

---

## 10. Caveats

- N=2 runs, one lease (Atreca). Flip rates and role-level counts are directional. The single confirmed GPT flip list (3 elements) is not a rate; the true Role B flip rate at temperature=1 vs temperature=0 (had it been transmitted) is unknown.
- The 411 artifact does not contain raw API request logs. The "temperature not transmitted" claim is a code-level finding, not an observed API log finding. The provider router path from ModelTarget to API request is deterministic given the code, and the code is unambiguous.
- Anthropic's non-determinism documentation is general; it applies to Claude Sonnet 4.6 but does not quantify the flip rate or characterize it by element type.
- "Provider default = temperature 1" for gpt-5.x is cited from OpenAI documentation for the reasoning-model family at the time of writing. OpenAI may change defaults.

*Trace artifact: Step 415. Read-only. No code change, no push.*
