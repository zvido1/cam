# Diagnostic 372-ID — Evaluator identity verification

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Read-only gating diagnostic. No code, no reruns, no model calls.
**Base SHA:** `e08d47a` (372MAP). Status file only.

---

## VERDICT: CONTAMINATED + UNAUDITABLE

Stated plainly:

**CONTAMINATED:** At least one stored element verdict in the six 370c runs was produced
by a fallback model (gpt-5.4) and labeled as the primary model ("GPT-5.5") with no
record of the substitution. Confirmed: H1/LP-22/Eval-B and H2/LP-09/Eval-B.

**UNAUDITABLE:** Three of the six runs (W1, W2, W3) are web-server runs whose stdout was
not captured by the web runner logs. Fallback status for all LPs in those three runs is
unknown. The stored data cannot distinguish primary from fallback verdicts for any run
because the identifier field (`evaluator_verdicts[].label`) always shows the static
primary model label regardless of which model actually answered, and `evaluator_meta`
(which records the actual model) is not saved to `pipeline_results.json`.

---

## Part 1 — Does stored data record the actual answering model?

### Code-path analysis

**`_call_single_evaluator_305` return format** (lines 358-363 and 383-387):
When the PRIMARY model succeeds:
```python
return {"role": role, "model": model, "provider": provider, "label": label, ...}
```
When a FALLBACK (own_chain) succeeds — **same format**, with `model`/`provider`/`label`
reflecting the FALLBACK, not the primary.

So the evaluator result dict DOES carry the actual model. The fallback is NOT silent at
the call level.

**`_extract_verdicts_for_element`** (lines 485–547):
Builds `evaluator_verdicts` per element. Lines 496, 514, 541:
```python
"label": EVALUATOR_LINEUP_305.get(role, {}).get("label", f"Evaluator {role}")
```
This is a **STATIC LOOKUP** from the fixed lineup config — always returns the PRIMARY
model label ("GPT-5.5" for role B, "Claude Sonnet 4.6" for A, "Grok 4.3" for C),
regardless of which model actually answered. **The actual model from the call result
(`result["label"]`) is NOT used here.**

**`assess_coverage_305` return** (lines 851-877):
Does build and return `evaluator_meta` with `r["model"]` (the actual answering model)
per role:
```python
evaluator_meta = {role: {"completed": r["completed"], "model": r["model"], ...}}
```
**But `lease_coverage.py` (lines ~246-310) does NOT save `evaluator_meta` to the
assessment dict** — it propagates `element_verdicts`, `coverage_state_baseline`,
`verdict_distance`, and other fields, but not `evaluator_meta`.

### Resulting audit gap

| Field | Records actual model? | Persisted? |
|---|---|---|
| `evaluator_verdicts[].label` | **NO** — always static primary label | Yes (in `pipeline_results.json`) |
| `evaluator_verdicts[].role` | A/B/C only | Yes |
| `evaluator_meta[role]["model"]` | **YES** — actual answering model | **NOT persisted to disk** |

**The only record of which model actually answered is in the stdout log of the run** —
which is available for headless runs, not for web-server runs.

---

## Part 2 — M2 long-prompt LP contamination map

### Confirmed fallbacks (from headless run logs)

| Run | LP | Role | Primary | Failure | Fallback | Stored label | Verdict stored |
|---|---|---|---|---|---|---|---|
| **H1** | LP-22 | B | gpt-5.5 | `empty_output` | **gpt-5.4** | "GPT-5.5" ← **WRONG** | explicitly_present |
| **H2** | LP-09 | B | gpt-5.5 | `empty_output` | **gpt-5.4** | "GPT-5.5" ← **WRONG** | missing |
| H3 | LP-09 | — | gpt-5.5 | none | — | "GPT-5.5" | missing |
| H3 | LP-22 | — | gpt-5.5 | none | — | "GPT-5.5" | missing |

**LP-11 (17 elements, 14K chars) succeeded with gpt-5.5 in all three headless runs** —
H1/H2/H3 all show gpt-5.5 called and no failure line. The failure is intermittent, not
guaranteed by element count alone.

**LP-27 (10 elements, 8.3K chars): no failures in any headless run.**

### Web runs (W1, W2, W3) — UNVERIFIABLE

The web runner logs (`_370c_W1.log` etc.) capture only poll-status output; all Step 305
calls run inside the uvicorn server process, whose stdout was not redirected to a file.
**The fallback status for W1/W2/W3 on ALL LPs is unknown from stored data.**

### Impact on LP-22 SNDA B flip

LP-22 `landlord_obligation_obtain_snda_existing_lenders` — B=EP×3/missing×3 at N=6:

| Run | B verdict | Actual B model | Source |
|---|---|---|---|
| W1 | EP | **unknown** | no server log |
| H1 | EP | **gpt-5.4** (fallback) | ✓ confirmed in log |
| H2 | missing | gpt-5.5 (primary) | confirmed: no failure in H2 LP-22 |
| W2 | EP | **unknown** | no server log |
| W3 | missing | **unknown** | no server log |
| H3 | missing | gpt-5.5 (primary) | confirmed: no failure in H3 LP-22 |

- H1's EP was gpt-5.4, not gpt-5.5 (confirmed).
- H2's and H3's missing were gpt-5.5 (confirmed no fallback).
- If W1/W2 were also gpt-5.4 fallbacks (possible but unverifiable), the LP-22 B split
  would be: gpt-5.4 → EP, gpt-5.5 → missing — **cross-model divergence** between
  versions, NOT within-gpt-5.5 non-determinism.
- Even on the minimum confirmed contamination (H1 only), the "B within-model variance"
  label is incorrect for H1: gpt-5.4 answered, not gpt-5.5.

**What the LP-22 B flip may actually be:**
- EP from H1: gpt-5.4 (different model, known different reasoning style at boundary cases)
- EP from W1/W2: unverifiable — could be gpt-5.4 fallback OR gpt-5.5 succeeding
- missing from H2/H3: gpt-5.5 (confirmed)
- missing from W3: unverifiable
- The "within-model variance" conclusion for LP-22/B requires verification that W1/W2
  were also gpt-5.5; if they were gpt-5.4, the flip is version substitution, not non-determinism.

### Impact on LP-09 B

LP-09 `change_of_control_addressed` — H2's gpt-5.4 fallback produced `missing` — same
as gpt-5.5 in other runs. The contamination does not change the LP-09 B-verdict analysis
(both versions give missing here), but the substitution itself is still a silent audit gap.

---

## Part 3 — Fallback firing rate and surfacing

### Rate by run and prompt size (headless runs only)

| Run | Total 305 evaluator calls (~32 LPs × 3) | Confirmed B-primary failures | Fallback fired |
|---|---|---|---|
| H1 | ~96 | LP-22/B | 1 |
| H2 | ~96 | LP-09/B | 1 |
| H3 | ~96 | 0 | 0 |

Overall headless rate: **2/~288 ≈ 0.7%** of all calls. But for **11-12 element LPs
specifically**: 2 failures in 6 headless opportunities (LP-09 ×3 + LP-22 ×3) = **33%**
for that subgroup.

### Long-prompt failure observed vs. expected

LP-11 (17 elements, 14K chars) succeeded in all 3 headless runs with gpt-5.5 — no
fallback. This is consistent with the intermittent nature of the failure (not a hard wall
at a specific element count).

The failure mode is `empty_output` — gpt-5.5 returns an empty string. This is a known
model behavior on over-long prompts where the model terminates early (likely output-token
or response-assembly issue). The production `own_chain` fallback to gpt-5.4 (a smaller,
more reliable model on long outputs) is the correct recovery.

### Web runs — total unknown

The three web runs (W1/W2/W3) each processed all LPs through the server, which has the
same fallback logic. There are no server logs to count web fallback events. **The total
fallback rate across all six runs is unknown for three of the six runs.**

### Is fallback substitution surfaced anywhere?

| Audit surface | Shows fallback? |
|---|---|
| `pipeline_results.json` / `evaluator_verdicts[].label` | **NO** — static primary label |
| `pipeline_results.json` / `evaluator_meta` | **NOT PERSISTED** (field exists in result dict but not saved) |
| `pipeline_results.json` / `evidence_summary` | **NO** — counts number of evaluators but not which model |
| Headless run stdout / log | **YES** — `"Eval-B (LP-22): gpt-5.5 FAILED: empty_output"` and `"Eval-B (LP-22): calling gpt-5.4"` |
| Web server stdout | **NOT CAPTURED** — not piped to a file in 370c setup |
| Frontend / lawyer-visible UI | **NO** |

**Silent substitution is the current behavior.** A lawyer, an auditor, and the 372-series
analysis all assumed "GPT-5.5" when a verdict was labeled with Eval-B, but for at least
two of 18 LP-×-run pairs (and potentially more for the web runs), that assumption is wrong.

---

## What this gates

### M1–M5 histogram status

The M2 count of 5/12 is impacted as follows:
- **LP-22 (M2):** At minimum H1's B=EP verdict was gpt-5.4. The "within-model reading
  variance" for LP-22/B is partially or wholly gpt-5.4 vs gpt-5.5 version differences,
  not gpt-5.5 non-determinism. If W1/W2 were also gpt-5.4, the LP-22 B flip is 100%
  model substitution and should be reclassified M5 (doesn't fit: "two models, one label").
- **LP-09 (M2):** H2 B was gpt-5.4 but gave the same verdict (`missing`) as gpt-5.5
  runs. Contamination confirmed but verdict is not affected for LP-09.
- Other M2 LPs (LP-03, LP-19, LP-26) had no confirmed fallbacks in headless logs; web
  runs unverifiable.

### Can the four-cause finding (R1/R2/R3/R4) proceed?

**Not until the LP-22 B flip is re-attributed.** If the EP/missing split for LP-22/B
is gpt-5.4 vs gpt-5.5, it reclassifies from "M2 gpt-5.5 reads element label
inconsistently" to "two different model versions read the element differently" — which
is cross-model divergence (M3-like), not within-model non-determinism. This changes the
diagnosis: the fix is not "stabilize gpt-5.5's reading" but "ensure the same model
answers on every run."

For the other M2 LPs (LP-03/C's S2.2 inference, LP-09/C's synonym wobble, LP-26's
cross-LP scope variation) no confirmed substitution was found in the headless logs. Those
remain plausibly genuine within-model variance, but the web-run unverifiability means
they cannot be ruled out either.

### Silent fallback substitution as independent defect

Regardless of how the contamination impacts the M1–M5 histogram, the governance defect
stands independently: the three-evaluator structure promises A=Sonnet/B=GPT/C=Grok, but
the stored data cannot confirm this for any run (label always shows primary, actual model
not persisted). This is a separate issue from the flip analysis — it affects audit
integrity and patent-record accuracy whenever gpt-5.5 fails on a long prompt.

---

## Scope / commit

Status file only. No code. No model calls.
