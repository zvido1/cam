# 416b — Follow-up: Three Reporting Gaps

**Date:** 2026-07-12
**Type:** Read-only reporting. No code changes. No commit. No push.
**Purpose:** Close three gaps from the 416 report: contamination boundary, full parameter enumeration, assertion scope.

---

## 1. Contamination Boundary

### Commit that introduced the broad guard

```
784efa7  2026-03-18  "brief description of what changed"
```

This is confirmed by `git log -S 'startswith("gpt-5")' -- cam/core/provider_router.py`, which returns three commits: `a0fe4a3` (416 fix, 2026-07-12), `784efa7` (guard introduction, 2026-03-18), `ec692d3` (initial deployment, 2026-03-16). The initial deployment did not contain the OpenAI evaluator adapter in its current form; `784efa7` introduced both the OpenAI adapter and the broad guard in the same commit bundle.

### Two distinct contamination stories

**Story A — Role B primary (gpt-5.5), all runs from 2026-03-18 onward:**
gpt-5.5 rejects `temperature=0` at the API level with a BadRequestError. The broad guard correctly omitted temperature for gpt-5.5 (for the wrong stated reason, but with the right practical effect). If the bug had been "fixed" naively by removing the guard before the probes confirmed this, every gpt-5.5 call would have errored out. The 416 fix preserves the gpt-5.5 omission via `TEMPERATURE_ONLY_DEFAULT_MODELS`. **Role B primary runs were and remain at provider-default temperature=1, not from the bug but from a model capability constraint. The fix does not change this.** All runs using gpt-5.5 as Role B primary — from 2026-03-18 through today and after — have Role B at temperature=1. This is not a contamination window that closes; it is a standing constraint while gpt-5.5 is the primary model.

**Story B — Role B own-chain fallback (gpt-5.4), runs from 2026-03-18 through 2026-07-12:**
gpt-5.4 accepts `temperature=0`. The broad guard incorrectly dropped temperature for gpt-5.4. Any evaluator call that hit the gpt-5.4 path (Stage 2 own-chain fallback; Stage 7 primary B path) during this window transmitted no temperature and ran at provider default. **The 416 fix corrects this for gpt-5.4: calls after `a0fe4a3` transmit temperature=0 on the gpt-5.4 path.** Contamination window for gpt-5.4: 2026-03-18 (`784efa7`) through 2026-07-12 (`a0fe4a3`, the 416 commit).

**Summary table:**

| Role B path | Model | Temperature before 416 | Temperature after 416 | Contamination window |
|-------------|-------|------------------------|----------------------|----------------------|
| Primary (Stage 2 / Stage 5) | gpt-5.5 | Provider default (1) — model rejects temp=0 | Provider default (1) — unchanged, model still rejects | No window; permanent constraint while gpt-5.5 is primary |
| Own-chain fallback (Stage 2 / Stage 5) | gpt-5.4 | Provider default (1) — bug dropped it | Transmitted 0 — fixed | 2026-03-18 to 2026-07-12 |
| Stage 7 primary B | gpt-5.4 | Provider default (1) — bug dropped it | Transmitted 0 — fixed | 2026-03-18 to 2026-07-12 |

**Benchmark caveat scope:** The Atreca A/B runs (Steps 408C–411, all post-2026-03-18) used Role B at temperature=1 throughout. For the primary path (gpt-5.5) this is unfixable regardless of the bug. For the gpt-5.4 fallback path (LP-15 Run B, LP-29 Run A — the two Grok-fails-to-pool fallback cases documented in Step 411), those calls went through a different path entirely (not gpt-5.4 but Gemini 2.5 Pro from the shared pool), so the gpt-5.4 temperature bug is not implicated in those specific fallback instances. The gpt-5.4 temperature fix affects runs where gpt-5.4 was the own-chain fallback for Role B, which is a narrower case than the total fallback set.

---

## 2. Full Parameter Enumeration Table

Every generation parameter checked across all four provider adapters (`OpenAIAdapter`, `AnthropicAdapter`, `XAIAdapter`, `GoogleGenAIAdapter`) in `cam/core/provider_router.py` after the 416 commit.

| Parameter | Declared on ModelTarget | OpenAI (gpt-5.5) | OpenAI (gpt-5.4 / 5.2 / 4o) | Anthropic (no reasoning_effort) | Anthropic (with reasoning_effort) | xAI (Grok) | Google (Gemini) | Silent drops found? |
|-----------|------------------------|-------------------|-------------------------------|----------------------------------|-----------------------------------|------------|-----------------|---------------------|
| `temperature` | Yes: 0.0 (all roles/stages) | **Omitted — capability exception** (model rejects non-default; TEMPERATURE_ONLY_DEFAULT_MODELS; logged) | Transmitted: `params["temperature"] = target.temperature` | Transmitted: `params["temperature"] = target.temperature` | **Omitted — capability exception** (Anthropic extended thinking rejects temperature; logged) | Transmitted: `params["temperature"] = target.temperature` | Transmitted: `config["temperature"] = target.temperature` | **None after 416.** Pre-416: gpt-5.4 and gpt-5.2 were silently dropped. |
| `max_output_tokens` / `max_tokens` | Yes: varies by stage/role | Transmitted as `max_completion_tokens` | Transmitted as `max_completion_tokens` (gpt-5.x) or `max_tokens` | Transmitted as `max_tokens` | Same | Transmitted as `max_tokens` | Transmitted as `max_output_tokens` in config dict | None. |
| `reasoning_effort` | Stage 2 Role B only: "medium"; all others: None | Transmitted as `params["reasoning_effort"]` when is_reasoning_model AND effort set | Same (gpt-5.x matches is_reasoning_model) | Not applicable (Anthropic maps to `thinking.budget_tokens`, not `reasoning_effort`) | Anthropic: maps to `thinking["budget_tokens"]`, not a direct pass-through | Not transmitted — xAI does not expose reasoning_effort in API | Not transmitted — Google does not expose reasoning_effort | Soft omission for non-reasoning models: recorded in `omitted`, not a hard failure. |
| `top_p` | Not declared on ModelTarget; not in any evaluator config | Not transmitted | Not transmitted | Not transmitted | Not transmitted | Not transmitted | Not transmitted | No silent drop — not declared. No assertion needed. |
| `top_k` | Not declared | Not transmitted | Not transmitted | Not transmitted (Anthropic Claude API does not support top_k in standard messages) | Same | Not transmitted | Not transmitted (Google config dict supports it but it is not set) | No silent drop — not declared. |
| Frequency penalty | Not declared | Not transmitted | Not transmitted | N/A (Anthropic API does not expose this) | Same | Not transmitted | N/A | No silent drop — not declared. |
| Presence penalty | Not declared | Not transmitted | Not transmitted | N/A | Same | Not transmitted | N/A | No silent drop — not declared. |
| `seed` | Not declared | Not transmitted | Not transmitted | Not available in Anthropic API | Not available | Not transmitted (xAI support undocumented) | Not available | No silent drop — not declared. |
| Response format / JSON mode | Not declared | Not transmitted (pipeline uses text extraction, not API-enforced JSON mode) | Same | Same | Same | Same | Same | No silent drop — not declared. |
| `timeout_sec` | Yes: 300.0 (evaluator calls) | Passed as kwarg to `chat.completions.create(..., timeout=target.timeout_sec)` — not a generation parameter, not in params dict | Same | Passed to `client.messages.create(..., timeout=target.timeout_sec)` | Same | Used at client construction, not as a params key | Enforced via signal.alarm and elapsed-check loop | No drop — timeout is a transport control, not a generation parameter; not in scope for integrity assertion. |

### Explicit statement on silent drops

**The enumeration found no additional silent drops beyond the known gpt-5.x temperature case that was fixed in 416.** The only parameters that are declared on `ModelTarget` and have a non-trivial path through the adapters are `temperature`, `max_output_tokens`, and `reasoning_effort`. All three are now either:
- transmitted (temperature for Anthropic/xAI/Google; all three for supported OpenAI models)
- documented-exception-omitted (temperature for gpt-5.5 and Anthropic extended thinking; reasoning_effort for non-reasoning-model paths)
- soft-recorded (reasoning_effort absence for non-reasoning models: logged in `omitted`, not a hard failure)

`top_p`, `top_k`, penalties, `seed`, and JSON mode are not declared anywhere in the evaluator config or `ModelTarget` — no assertion is needed or missing for them.

**The Google adapter (`GoogleGenAIAdapter`) was not touched by 416** and does not call `_check_generation_integrity`. It transmits `temperature` and `max_output_tokens` correctly into the config dict (`provider_router.py:520–523`). Google is used only as a shared-pool fallback (Gemini 2.5 Pro), not as a primary evaluator. The Google adapter's parameter handling is correct and no silent drops exist there. Adding integrity assertion to it is out of scope for this step.

---

## 3. What the Assertion Actually Guards

`_check_generation_integrity()` is **not total over the full parameter enumeration** from §2. It is a targeted check over three parameters: `temperature`, `max_tokens` / `max_output_tokens`, and `reasoning_effort`.

### What it hard-fails on

- `temperature` absent from `params` with no `temperature_omit_reason` → `FatalProviderError("config_integrity_violation: ...")`.
- Neither `max_tokens` nor `max_completion_tokens` present in `params` → `FatalProviderError("config_integrity_violation: ...")`.

### What it soft-records (no raise)

- `reasoning_effort` declared on `ModelTarget` but absent from `params` → logged to `omitted` with reason `"non_reasoning_model_or_effort_not_applicable"`. Not a hard failure. Rationale: `reasoning_effort` is model-gated — only reasoning models (gpt-5.x, o1/o3/o4 series) accept it; its absence for other model types is expected and not silent in the same sense as temperature.

### What it does not assert

- `top_p`, `top_k`, penalties, `seed`, JSON mode: not in `EVALUATOR_CRITICAL_PARAMS` and not checked. These are not declared on `ModelTarget` and no evaluator config sets them, so asserting their absence would be trivially true and vacuous. If any of these are added to evaluator config in the future, they should be added to `EVALUATOR_CRITICAL_PARAMS` and the assertion extended.
- Google adapter (`GoogleGenAIAdapter`): not wired to `_check_generation_integrity`. Google is fallback-only; adding the call is a future scope item.
- OpenRouter adapter (`OpenRouterAdapter`): not wired. OpenRouter is disabled (`DISABLE_OPENROUTER=1`) in production; no evaluator uses it.

### Guard scope, stated plainly

The assertion is **partial** — it covers the three parameters that are actually declared in evaluator config and have non-trivial adapter paths. It is not a total parameter check. For the current evaluator stack (temperature, max_tokens, reasoning_effort as the complete declared set), it is **complete over the declared set** but not over the full parameter space a provider could accept. That distinction matters: if a future `ModelTarget` field for `top_p` is added, it would not be caught unless also added to `EVALUATOR_CRITICAL_PARAMS` and the assertion body.

---

## Summary Answers

**1. Contamination boundary commit:** `784efa7`, 2026-03-18. Two stories: gpt-5.5 primary path was and remains at temperature=1 due to model capability (not the bug); gpt-5.4 fallback path was silently at temperature=1 due to the bug from 2026-03-18 to 2026-07-12, and is now fixed.

**2. Additional silent drops found:** None. The enumeration is clean after 416. Three parameters are declared; all three are either transmitted or documented-exception-omitted across all adapters where they are applicable.

**3. Assertion scope:** Partial by design — covers the three declared parameters (temperature, max_tokens, reasoning_effort) with hard failure on the first two and soft recording on the third. Not total over the full provider parameter space. Total over the declared evaluator-critical set as currently enumerated.

*Step 416b. Read-only. No code change. No commit. No push.*
