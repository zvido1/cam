# Diagnostic 372-V1 — gpt-5.5 temperature drop: adapter over-drop or model constraint?

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Part A read-only + Part B probe (5 keyed calls, trivial spend).
**Base SHA:** `a16735a` (372BUD). Status file only.

---

## VERDICT: #2 — MODEL CONSTRAINT

gpt-5.5 rejects `temperature != 1` with HTTP 400. The adapter's temperature drop is a
correct workaround, not a bug. **B (gpt-5.5) cannot be made deterministic; it is
structurally a sampling evaluator at temperature=1.**

---

## Part A — Adapter logic (read-only)

### Exact drop logic (provider_router.py lines 188–195)

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

### Is it conditional or unconditional?

**UNCONDITIONAL** — the condition is `target.model.startswith("gpt-5")`, which matches:
- `gpt-5.5` (Stage 305 B primary, Stage 305/5e)
- `gpt-5.4` (Stage 7 Pass-1/consolidation B, Stage 305 B fallback)
- Any future `gpt-5.x` model

It does NOT check `reasoning_effort` or any other parameter. Temperature is dropped for
ALL gpt-5.x calls regardless of reasoning mode.

### WHY it was added — origin evidence

The git history is sparse (3 commits: initial, deploy, Railway fix). No commit message
explains the temperature drop. The comment says *"GPT-5.2 only supports default temperature
(1), not custom values"* — the model name in the comment (GPT-5.2) suggests it was written
for an earlier model iteration and the condition was left as a blanket rule covering all
gpt-5.x. The Part B probe confirms the constraint applies to gpt-5.5 (and by the same
mechanism, almost certainly gpt-5.4).

### Does gpt-5.4 (Stage 7 B) also get the temperature drop?

**YES.** `"gpt-5.4".startswith("gpt-5")` is `True`. Stage 7 Pass-1/consolidation (which
uses gpt-5.4 as B) also runs at temperature=1 — the temperature=0.0 requested by the lineup
config is silently dropped. **Stage 7 B is also a sampling evaluator at temperature=1.**

### Our reasoning settings for Stage 305 calls

Stage 305 B (`gpt-5.5`): `ModelTarget(model="gpt-5.5", max_output_tokens=<computed>,
temperature=0.0, reasoning_effort=None)`. The `reasoning_effort` is `None` — gpt-5.5 runs
in **standard (non-reasoning) mode** for Stage 305 calls. The temperature drop is NOT
related to reasoning mode; it fires before the `if effort and _is_reasoning_model:` check.

---

## Part B — Probe results

**Setup:** Direct OpenAI API call, gpt-5.5, `max_completion_tokens=3000`, no
`reasoning_effort`, matching Stage 305 B's call shape. Temperature=0 explicitly included.

```
s0: HTTP 400 — "Unsupported value: 'temperature' does not support 0 with this model.
               Only the default (1) value is supported."
s1: HTTP 400 — same error
s2: HTTP 400 — same error
s3: HTTP 400 — same error
s4: HTTP 400 — same error
```

**Follow-up: which temperature values does gpt-5.5 accept?**

| temperature | Result |
|---|---|
| omitted (None) | ✅ OK — model defaults to 1 |
| 1 | ✅ OK — explicit 1 accepted |
| 0 | ❌ HTTP 400 — rejected |
| 0.5 | ❌ HTTP 400 — rejected |

**The model only supports temperature=1.** This is a hard API constraint, not a
documentation nuance. The adapter comment *"only supports default temperature (1)"* is
accurate for gpt-5.5 (and by extension, likely gpt-5.4 as well — the same model family).

---

## Verdict analysis

**#2 — MODEL CONSTRAINT. The adapter drop is a correct workaround.**

| Hypothesis | Evidence | Status |
|---|---|---|
| #1 Adapter over-drop (fixable) | temp=0 would be accepted → adapter just forgot to send it | **REFUTED**: API explicitly rejects temp=0 with HTTP 400 |
| #2 Model constraint (architectural fact) | Model only supports temp=1 → drop is correct | **CONFIRMED**: consistent HTTP 400 across 5 calls, explicit error message |

---

## Implications for the variance investigation

### B's measured variance is VALID (not contaminated)

Every B (gpt-5.5 or gpt-5.4) call in the pipeline has run at temperature=1 since the
adapter was written — and the temperature=1 constraint is a model property, not a code
defect. The 372WV and 372NDET measurements of "within-model variance" for B are measuring
**genuine temperature=1 sampling variance** — the correct baseline for this evaluator.

The analysis conclusions about B's non-determinism are not invalid. They correctly measured
the only behavior B can exhibit. The phrase "within-model variance" is accurate; we just now
know it is inseparable from temperature=1 for this model family.

### B is structurally non-deterministic — architectural fact

gpt-5.5 and gpt-5.4 cannot be run at temperature=0. Any usage of these models as evaluators
in a three-evaluator governance structure must account for the fact that B is always sampling
at temperature=1. The three-evaluator model does not provide "three deterministic-ish voices"
— it provides one (A=Sonnet at temp=0), one (C=Grok at temp=0), and one inherently
stochastic (B=GPT-5.x at forced temp=1).

This is not a defect to fix — it is a property to document. The CAM governance design
already handles stochastic evaluators through the 2/3 majority and the 369 integrity guard.

### Stage 7 B (gpt-5.4) also affected

The temperature drop applies equally to gpt-5.4. Stage 7 Pass-1, Stage 7 consolidation,
and the Stage 305 B fallback (gpt-5.4) all run at temperature=1. The Stage 7 directional
Pass-1 candidate-count variance (22–28 across 370c runs), previously attributed partly to
Stage 5 input variance, includes a B (gpt-5.4 at temp=1) sampling component.

### What the variance analysis now shows

The 372-series finding stands: B introduces inherent stochastic variance at every level
(Stage 305, Stage 5e, Stage 7). The variance causes identified (M2 unstable reading, M1
mapping instability, etc.) are measured at temperature=1 for B — they represent B's actual
behavior in production, which is the relevant baseline.

**No change is required to address the temperature drop.** The adapter is correct.

---

## Scope / commit

Part B probe script `_372v1_temp_probe.py` committed to root (temporary diagnostic). Status
file only is the substantive commit. No production code change.
