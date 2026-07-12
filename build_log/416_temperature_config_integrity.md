# 416 — Evaluator Config Integrity Fix

**Date:** 2026-07-12
**Type:** Diagnostic probes + targeted adapter patch + assertion layer + tests + doc update.
**Purpose:** Narrow the broad `startswith("gpt-5")` temperature-drop guard to an explicit per-model capability map; add a config-vs-payload integrity assertion that makes undocumented parameter omissions a hard failure.

---

## Part 1 — Branch History and Contamination Boundary

### Commit that introduced the broad guard

```
784efa7  2026-03-18  "brief description of what changed"
```

Diff excerpt from `cam/core/provider_router.py` in that commit:

```python
# GPT-5.2 requires max_completion_tokens instead of max_tokens
# GPT-5.2 only supports default temperature (1), not custom values
if target.model.startswith("gpt-5"):
    params["max_completion_tokens"] = target.max_output_tokens
    # Don't set temperature for GPT-5.2 (uses default 1)
else:
    params["max_tokens"] = target.max_output_tokens
    params["temperature"] = target.temperature
```

The comment names `gpt-5.2` but the condition matches all `gpt-5.*` models. The commit was a UI + adapter bundle (13 files); the temperature omission was a side-change, not the focus.

### Prior commit (initial deployment)

```
ec692d3  2026-03-16  "Initial deployment: CAM Lease Analyzer"
```

The initial deployment did not contain an OpenAI adapter; the `startswith("gpt-5")` branch arrived with `784efa7`.

### Contamination boundary

All evaluator runs from **2026-03-18** onward had Role B operating at provider-default temperature (1) rather than declared temperature=0 for gpt-5.5, and with dropped temperature for gpt-5.4 / gpt-5.2 on fallback paths. Runs before 2026-03-16 (initial deployment) did not yet have an OpenAI evaluator in the lease pipeline. Runs between 2026-03-16 and 2026-03-18 are a small window (two days) before the guard landed; these likely used a different adapter path (not documented here).

The Atreca A/B runs used in Steps 408C–411 were run after 2026-03-18 and are in the contaminated window.

---

## Part 2 — Probe Results

All probes run 2026-07-12 against the live OpenAI API, env loaded from `C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env`.

### Probe A — gpt-5.5 (current Role B primary, Stage 2 / Stage 5)

| Parameter | Value | Result |
|-----------|-------|--------|
| model | gpt-5.5 | — |
| temperature | 0 | **REJECTED** `BadRequestError 400: "Unsupported value: 'temperature' does not support 0 with this model. Only the default (1) value is supported."` |
| temperature | 0.5 | **REJECTED** — same error, same message |
| temperature | 1 | **ACCEPTED** — empty content (model returned no text for minimal prompt) |
| temperature | 1.0 | **ACCEPTED** |

**Conclusion:** gpt-5.5 only accepts temperature=1 (the provider default). Any non-default value is rejected. The declared `temperature=0.0` for Role B cannot be honored by the current primary model.

### Probe A2 — gpt-5.4 (Stage 7 Role B; own-chain fallback in Stage 2/5)

| Parameter | Value | Result |
|-----------|-------|--------|
| model | gpt-5.4 | — |
| temperature | 0 | **ACCEPTED** — `{"ok":true}` returned |

**Conclusion:** gpt-5.4 accepts temperature=0. The broad guard incorrectly excluded it.

### Probe B — gpt-5.2 (negative control; model the original comment cited)

| Parameter | Value | Result |
|-----------|-------|--------|
| model | gpt-5.2 | — |
| temperature | 0 | **ACCEPTED** — `{"ok":true}` returned |

**Conclusion:** gpt-5.2 accepts temperature=0. The original adapter comment ("GPT-5.2 only supports default temperature (1)") was factually wrong. gpt-5.2 does not need the temperature-drop guard.

### Reference — gpt-4o

| model | temperature | Result |
|-------|-------------|--------|
| gpt-4o | 0 | **ACCEPTED** |

### Interpretation

The probes yield the "current Role B accepts, old model rejects" category — except the model that originally motivated the guard (gpt-5.2) was never actually the rejecting model. The rejecting model is gpt-5.5 only. The broad prefix guard was both incorrectly motivated (wrong model cited) and over-broad (excluded models that accept temperature).

---

## Part 3 — Evaluator-Critical Parameter Enumeration

Config-integrity table for the lease evaluator stack.

| Parameter | Declared in config | Providers / models that support it | Outbound key | Omission allowed | Exception reason if omitted |
|-----------|-------------------|-------------------------------------|--------------|------------------|-----------------------------|
| `temperature` | All roles, all stages: 0.0 | Anthropic (Role A): YES when no reasoning_effort. OpenAI (Role B): gpt-5.4/5.2 YES; **gpt-5.5 NO — only accepts =1**. xAI (Role C): YES. | `temperature` | Only with explicit exception | TEMPERATURE_ONLY_DEFAULT_MODELS (gpt-5.5); Anthropic extended-thinking path |
| `max_output_tokens` | All roles, all stages: varies | All providers | `max_completion_tokens` (gpt-5.x); `max_tokens` (others) | No | — |
| `reasoning_effort` | Stage 2 Role B only: "medium" | OpenAI reasoning models (gpt-5.x, o1/o3/o4) | `reasoning_effort` | Yes, for non-reasoning models | Non-reasoning model or effort not applicable |
| `top_p` | Not declared anywhere | All providers support it | `top_p` | N/A — not declared | Not in evaluator config |
| `top_k` | Not declared anywhere | Anthropic (extended thinking); Google; xAI (via OpenAI-compat) | varies | N/A — not declared | Not in evaluator config |
| Frequency / presence penalty | Not declared anywhere | OpenAI; xAI | `frequency_penalty`, `presence_penalty` | N/A | Not in evaluator config |
| `seed` | Not declared anywhere | OpenAI (gpt-4/4o); gpt-5.x / grok / Anthropic / Gemini: undocumented or absent | `seed` | N/A | Not available for current model generation |
| `response_format` / JSON mode | Not declared; evaluators return raw text parsed via json_extract | All providers in various forms | varies | N/A | Pipeline uses robust text extraction; not API-enforced JSON mode |

**Tests added:** temperature (all three providers), max_tokens field, reasoning_effort present/absent cases. top_p, penalties, seed: not declared → not tested (no assertion needed unless added to ModelTarget in future).

---

## Part 4 — Adapter Change: Narrow the Branch

### Before (broad prefix guard, `784efa7` forward)

```python
if target.model.startswith("gpt-5"):
    params["max_completion_tokens"] = target.max_output_tokens
    # Don't set temperature for GPT-5.2 (uses default 1)
else:
    params["max_tokens"] = target.max_output_tokens
    params["temperature"] = target.temperature
```

**Effect:** ALL gpt-5.x models dropped temperature. gpt-5.4 and gpt-5.2 both unnecessarily excluded.

### After (explicit model sets)

```python
# TEMPERATURE_ONLY_DEFAULT_MODELS = frozenset({"gpt-5.5"})  — probe-confirmed 2026-07-12
# MAX_COMPLETION_TOKENS_MODELS = frozenset({"gpt-5.5", "gpt-5.4", "gpt-5.2"})

if target.model in MAX_COMPLETION_TOKENS_MODELS:
    params["max_completion_tokens"] = target.max_output_tokens
else:
    params["max_tokens"] = target.max_output_tokens

if target.model in TEMPERATURE_ONLY_DEFAULT_MODELS:
    temperature_omit_reason = (
        f"model={target.model!r} only accepts temperature=1; "
        f"declared temperature omitted. Capability exception: TEMPERATURE_ONLY_DEFAULT_MODELS."
    )
    # temperature omitted from params — provider default (1) governs
else:
    params["temperature"] = target.temperature
```

**Effect:** gpt-5.5 still drops temperature (correct — it rejects non-default values). gpt-5.4 and gpt-5.2 now transmit temperature. The omission for gpt-5.5 is explicitly documented.

---

## Part 5 — Config-vs-Payload Integrity Assertion

Added `_check_generation_integrity(target, params, temperature_omit_reason)` to `cam/core/provider_router.py`.

### Behavior

- For every evaluator call, compares `ModelTarget` declared values to the outbound `params` dict.
- **temperature:** If in params → `transmitted`. If absent with `temperature_omit_reason` → `omitted` with recorded reason. If absent with no reason → raises `FatalProviderError("config_integrity_violation: ...")`.
- **max_tokens:** Either `max_tokens` or `max_completion_tokens` must be in params. Absent → raises `FatalProviderError`.
- **reasoning_effort:** If `target.reasoning_effort is not None` and absent from params → `omitted` with reason `"non_reasoning_model_or_effort_not_applicable"`. Not a hard failure (model-gated, not silent).
- Returns `effective_request_metadata` dict: `{declared, transmitted, omitted, omission_reasons, provider, model}`.

### Applied in

- `OpenAIAdapter._call_once` — after params construction, before API call. Logs integrity line on every call.
- `AnthropicAdapter.call` — same pattern; extended-thinking path supplies `temperature_omit_reason`.
- `XAIAdapter.call` — same pattern; temperature always present, so omit_reason=None.

### Silent omission is now a hard failure

Any new model added to the stack that silently drops a declared parameter without being in an explicit capability set will raise `FatalProviderError` on the first call. The check catches the defect before results are produced, not after.

---

## Part 6 — Tests (32 new, all green)

File: `cam/adapters/lease_review/tests/test_416_config_integrity.py`

| Class | What it tests |
|-------|---------------|
| `TestGpt55TemperatureOmission` (4) | gpt-5.5 in TEMPERATURE_ONLY_DEFAULT; omission documented; declared value preserved |
| `TestGpt54TemperatureTransmitted` (3) | gpt-5.4 not in exclusion set; temperature=0 in payload |
| `TestGpt52TemperatureTransmitted` (2) | gpt-5.2 not in exclusion set; temperature=0 in payload |
| `TestNoBroadPrefixRegression` (2) | Only gpt-5.5 excluded; gpt-5.4 not in exclusion set |
| `TestGuardFailure` (2) | Undocumented temperature drop → FatalProviderError; missing max_tokens → FatalProviderError |
| `TestIntegrityMetadataStructure` (2) | Metadata keys present; declared values match ModelTarget |
| `TestAnthropicThinkingTemperature` (1) | Thinking mode omission backed by capability exception |
| `TestAnthropicNormalMode` (1) | Normal mode transmits temperature=0 |
| `TestXAIAdapter` (1) | xAI temperature unconditionally transmitted |
| `TestMaxTokensField` (3) | max_tokens key present; max_completion_tokens vs max_tokens distinction |
| `TestReasoningEffort` (3) | Transmitted when set; omission recorded (not hard-fail) when absent for non-reasoning model; None → no omitted entry |
| `TestEvaluatorLineupUnchanged` (8) | 414 invariant: A=anthropic, B=openai, C=xai; distinct providers; all declare temperature=0 |

Run: `PYTHONPATH=. python -m pytest cam/adapters/lease_review/tests/test_416_config_integrity.py -v`
Result: **32/32 PASSED**

414 suite: **52/52 PASSED** (unchanged).

---

## Part 7 — Smoke Test After Patch

```
=== Smoke: gpt-5.5 via patched adapter ===
[openai][integrity] model='gpt-5.5' transmitted=['max_tokens', '_max_tokens_key', 'reasoning_effort']
    omitted=['temperature']
    reasons={'temperature': "model='gpt-5.5' only accepts temperature=1 (provider default);
             declared temperature=0.0 omitted. Capability exception: TEMPERATURE_ONLY_DEFAULT_MODELS.
             Probe: 2026-07-12."}
Result: {"ok": true}

=== Smoke: gpt-5.4 via patched adapter ===
[openai][integrity] model='gpt-5.4' transmitted=['temperature', 'max_tokens', '_max_tokens_key']
    omitted=[] reasons={}
Result: {"ok":true}
```

**gpt-5.5:** capability exception path fires, reason logged, call succeeds (temperature=1 governs).
**gpt-5.4:** temperature=0 transmitted in payload. No omission recorded.

---

## Part 8 — State Notes

### CAM_Current_State.md

Updated with 2026-07-12 block documenting:
- 415 trace finding (not-transmitted root cause for Role B)
- 416 probe results and fix
- Role B primary (gpt-5.5) capability gap
- Benchmark caveat boundary (2026-03-18 commit `784efa7`)

### Patent_Current_State.md

Added candidate note (2026-07-12) documenting:
- Config-frozen as a separate invariant from identity-frozen
- Role B primary capability gap for temperature
- Accurate framing: panel is identity-frozen AND config-integrity-asserted; Role B primary operates at provider-default temperature due to model constraint, not adapter defect

---

## Summary

| Question | Answer |
|----------|--------|
| Was temperature=0 set in config for all roles/stages? | Yes, everywhere |
| Was it transmitted for Role A (Anthropic)? | Yes (no reasoning_effort on evaluator A config) |
| Was it transmitted for Role B (OpenAI gpt-5.5)? | **No** — dropped by broad prefix guard; gpt-5.5 cannot accept it |
| Was it transmitted for Role B fallback (gpt-5.4)? | **No before 416**; yes after (gpt-5.4 accepts temperature=0) |
| Was it transmitted for Role C (xAI)? | Yes |
| Does gpt-5.5 accept temperature=0? | **No** — provider rejects with BadRequestError |
| Does gpt-5.4 accept temperature=0? | Yes — probe confirmed |
| Does gpt-5.2 accept temperature=0? | Yes — original comment was wrong |
| Root cause for Role B? | Partially not-transmitted (adapter defect for gpt-5.4/5.2); partially capability gap (gpt-5.5 cannot accept temperature=0) |
| Fix applied? | Adapter narrowed to gpt-5.5-only exception; integrity assertion added to all three provider adapters |
| Tests? | 32 new (all green); 52 existing 414 tests unchanged |

*Step 416. No push.*
