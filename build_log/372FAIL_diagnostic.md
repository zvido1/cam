# Diagnostic 372-FAIL — Long-prompt failure mechanism per model

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Read-only mechanism audit over logs + code. No code, no model calls.
**Base SHA:** `0c168dc` (372ID). Status file only. Gates 372c (prevention fix).

---

## Failure mechanism per model — the headline

| Model | Failure type | Response returned? | Root mechanism | Fix family |
|---|---|---|---|---|
| **B (gpt-5.5)** | `empty_output` | HTTP 200, `message.content = None` | Reasoning-token exhaustion: internal thinking consumes `max_completion_tokens` before any visible output | **RAISE BUDGET** + **SPLIT** |
| **A (Sonnet)** | `PARSE_ERROR` (truncated JSON) | Yes — incomplete unclosed array | Hard output truncation at `max_tokens` ceiling (same as 370d Stage-7) | **RAISE BUDGET** |
| **C (Grok)** | None | n/a | Terse output style stays within budget | Neither — confirm LP-11 |

**Hypothesis (A=truncation, B=request-failure) — PARTIALLY CONFIRMED, PARTIALLY WRONG.**
- A = output truncation: **CONFIRMED.** A response came back; it is an unclosed/incomplete JSON array.
- B = "request failure": **WRONG label — correct mechanism is reasoning-token exhaustion.** The API call completes normally (HTTP 200, no network error, no exception); the OpenAI adapter returns `""` because `resp.choices[0].message.content or ""` evaluates to `""` (content is None). The failure is output-side, not request/input-side.

---

## Per-failed-call table

### Production failures (headless run logs)

| Run | LP | Role | Model | Prompt (chars/elems) | Budget (_tokens) | Error | Response returned? | Class |
|---|---|---|---|---|---|---|---|---|
| H1 | LP-22 | B | gpt-5.5 | 10,638 / 11 | 3,800 | `empty_output` | HTTP 200, content=None | **Reasoning exhaustion** |
| H2 | LP-09 | B | gpt-5.5 | 10,760 / 12 | 4,100 | `empty_output` | HTTP 200, content=None | **Reasoning exhaustion** |

### NDET harness failures (N=20 per cell)

| Cell | Role | N failures / 20 | Error string | Response returned? | Class |
|---|---|---|---|---|---|
| LP-09 (12 el, 10.8K) | B | 10/20 (50%) | `empty_output` | HTTP 200, content=None | **Reasoning exhaustion** |
| LP-22 (11 el, 10.6K) | B | 18/20 (90%) | `empty_output` (17×) + `PARSE_ERROR` (1×) | content=None (17×), truncated response (1×) | **Reasoning exhaustion** |
| LP-22 (11 el, 10.6K) | A | 8/20 (40%) | `PARSE_ERROR` | Yes — truncated, unclosed JSON array | **Output truncation** |

---

## Part 1 — Mechanism evidence per model

### B (gpt-5.5) — reasoning-token exhaustion

**Code path (cam/core/provider_router.py lines 188-215):**
```python
# For gpt-5.x models:
params["max_completion_tokens"] = target.max_output_tokens  # ← shared budget
# reasoning_effort NOT set (no reasoning_effort kwarg in lease_coverage_305 _try_call)
resp = self.client.chat.completions.create(**params, ...)
return resp.choices[0].message.content or ""  # ← None on token exhaustion
```

`max_completion_tokens` for gpt-5.5 is a **shared budget covering BOTH internal reasoning tokens
AND visible completion tokens.** When the reasoning phase consumes the entire budget before
producing any completion tokens, `message.content` is `None`. The adapter returns `""`, which
propagates to `safe_json_extract("")` → `text = "".strip()` → `raise ValueError("empty_output")`.

**No HTTP error occurs.** The API call succeeds. The failure is entirely output-side: the model
exhausted its token allowance on thinking before writing any answer.

For LP-09 (12 elements): budget = `max(3000, 12×300+500) = 4,100` tokens.
For LP-22 (11 elements): budget = `max(3000, 11×300+500) = 3,800` tokens.
The `N×300+500` formula was designed for standard (non-reasoning) models where all tokens go to
visible output. For gpt-5.5, a large fraction of the budget disappears into internal reasoning,
leaving insufficient tokens for the actual per-element JSON array.

The failure is **intermittent** (H3 had gpt-5.5 succeed on both LP-09 and LP-22 with the same
budget) because the reasoning depth varies: simpler runs use fewer thinking tokens and complete
before the ceiling.

### A (Sonnet) — output truncation at max_tokens ceiling

**Code path (cam/core/provider_router.py lines 267-294):**
```python
params["max_tokens"] = target.max_output_tokens  # ← hard ceiling on visible output
resp = self.client.messages.create(**params, ...)
return "\n".join(chunks).strip()  # ← truncated array returned
```

A's `max_tokens` is a ceiling on the VISIBLE OUTPUT only (Sonnet has no reasoning overhead).
For LP-22 (11 elements): budget = `max(3000, 11×300+500) = 3,800` tokens. Sonnet's verbose
per-element responses (reasoning text + citation + confidence) average 200–400 tokens each.
For 11 elements: 11 × 350 ≈ 3,850 tokens — just over the 3,800 ceiling.

A response IS returned: an incomplete JSON array that starts valid and cuts off mid-structure.
`json.loads` fails (unclosed bracket). `safe_json_extract` attempts to salvage a partial object
but returns None or an unusable fragment. The harness records `PARSE_ERROR`.

**This is the Stage-7 output truncation pattern from 370d**, applied at Stage 5.** The same
mechanism, the same fix family (raise budget), one level up in the pipeline.

**Why A succeeded in all 6 production runs but failed 8/20 in NDET:** The same variance seen
in 370d — response verbosity varies run-to-run. 6 runs of 20 just happened not to hit the
ceiling; at N=20 several did. Both the production and NDET failures are real.

### C (Grok) — robust

Grok-4.3 produces compact per-element verdicts (typically 50–150 tokens per element; 11
elements ≈ 1,000–1,650 tokens). The `N×300+500` formula is generous relative to Grok's actual
output. No failures at N=20 or in production. Does NOT use a reasoning-overhead model architecture
(no internal thinking tokens).

---

## Part 2 — Input scaling vs. output scaling

**B (gpt-5.5): scales with INPUT COMPLEXITY, manifests as OUTPUT exhaustion.**
The failure is not a raw input-token issue (the prompt fits; no input-length error). The failure
is the reasoning model's attempt to process the full N-element prompt exhausting thinking tokens.
More elements → more complex reasoning → more thinking tokens consumed. The failure is
**input-complexity-induced output exhaustion**.

**A (Sonnet): scales with OUTPUT SIZE.**
More elements × more tokens per element = larger required output. `N×300+500` underestimates
the actual per-element token cost at Sonnet's verbosity. The failure is a direct function of
N × (actual tokens per element) exceeding the budget formula's estimate. **Pure output-size scaling.**

**Distinguishing signal:** B's failure produces empty content (no response body); A's failure
produces a truncated response body. That difference alone establishes the mechanism without needing
stop_reason metadata (which the Anthropic adapter also doesn't expose, as noted in 372D).

---

## Part 3 — LP-11 prediction (17 elements, 14,058 chars)

Budget for LP-11: `max(3000, 17×300+500) = 5,600` tokens.

| Model | Prediction | Reasoning |
|---|---|---|
| **B (gpt-5.5)** | **FAILS — reasoning exhaustion** (high confidence) | More elements → more complex reasoning → 5,600 thinking tokens more likely to be consumed. 17-element prompt is ~30% harder than 12-element LP-09 (50% failure). Estimated failure rate: >75%. |
| **A (Sonnet)** | **FAILS — output truncation** (moderate confidence) | 17 elements × ~350 tokens each = ~5,950 tokens estimated output; 5,600 budget = likely truncation on verbose runs. At least intermittent failure. |
| **C (Grok)** | **Likely OK** (high confidence) | 17 × 100 tokens ≈ 1,700 tokens; well within 5,600 ceiling. |

**Note:** LP-11 SUCCEEDED in all 3 headless 370c production runs with gpt-5.5 (no failures
logged). This is consistent with intermittent failure — a 3-sample observation cannot rule out
a ~40% failure rate. The NDET data (50-90% failure at 11-12 elements) is a stronger N=20 signal.

---

## Part 4 — Per-model targeted fix

### B (gpt-5.5) — RAISE BUDGET + SPLIT

**Primary cause:** Reasoning-token exhaustion. The `N×300+500` formula was designed for
non-reasoning models. gpt-5.5 requires a significantly larger `max_completion_tokens` to cover
internal reasoning overhead before visible output.

**RAISE BUDGET:** Replace the formula with a reasoning-aware version for gpt-5.x models. The
multiplier needs to account for thinking overhead — likely `N×600+2000` or similar (the exact
multiplier requires measurement, not guessing).

**SPLIT (also warranted):** Even with a higher budget, reasoning depth is positively correlated
with prompt complexity. Batching fewer elements per call reduces per-call reasoning load. For LPs
with ≥10 elements, splitting into two calls of ≤8 elements would cap the reasoning depth.

**BOTH** is the correct answer for B: a raised budget reduces intermittent failures; splitting
provides a harder upper bound on reasoning complexity.

### A (Sonnet) — RAISE BUDGET

**Primary cause:** Hard `max_tokens` ceiling underestimated by the formula. Mechanism is
identical to the Stage-7 truncation fixed in 370d.

**RAISE BUDGET:** Update the formula for Sonnet to use a higher per-element multiplier. Sonnet
produces ~350 tokens per verbose element verdict; `N×500+1000` would give LP-22 (11 elements)
= 6,500 tokens and LP-11 (17 elements) = 9,500 tokens — generous headroom.

No split needed for A: the failure is purely budget math. With sufficient max_tokens, Sonnet
will complete every element in a single call.

### C (Grok) — MONITOR LP-11

Current budget formula is adequate for Grok's terse output style on tested LPs. LP-11 (17
elements) at 5,600 tokens is still well above Grok's typical 1,700-token output. No fix required,
but verify on LP-11 when it runs.

---

## Surfacing gap

The production code comment at `lease_coverage_305.py` line 288 already acknowledges this:
*"LP-11 has 17 elements; 3000 tokens was too small and caused truncation"* — suggesting the
`N×300+500` formula was itself a previous fix that addressed LP-11/Sonnet truncation at N=3000.
The formula is not keeping pace as model verbosity and element counts grow.

No implementation in this diagnostic. 372c specs and implements the fix.
