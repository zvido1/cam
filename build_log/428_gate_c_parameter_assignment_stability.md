# Step 428 — Gate C: Parameter Assignment Stability Measurement

**Date:** 2026-07-14
**Status:** COMPLETE — measurement only, no code changed

---

## Required Statements

> This measures parameter assignment stability on ONE document. It does
> not validate the architecture and does not measure stability on unseen
> documents.

> Gate C is a measurement, not a fix. No code was changed in this step
> regardless of the result.

---

## Plain Verdict

**NO. The parameter block is not stable enough to wire into the live
pipeline.**

Not "mostly stable." **0 of 10 runs produced a single verified parameter.
0 of 10 runs passed Gate B. 10 of 10 runs aborted.** Every one of the four
declared dependencies (`tenant_share`, `building_share`,
`rent_adjustment_pct`, `base_rent`) failed on every run. LP-07's
attachment list and LP-02's attachment list were empty on all 10 runs.

This is a worse result than the brief anticipated, and the reason is
important: **the underlying values were not missing.** A supplementary
diagnostic probe (below) shows the model located and quoted all four
values correctly, with the correct percentages and dollar figure, in the
same call shape used by the measurement. The 0/10 is not evidence that
`canonical_v2` elicitation cannot find these parameters. It is evidence
that `extract_parameters()`'s mechanism for recognizing which target a
quote answers is fragile to a model-output variation this project has
already observed and named — and that fragility, this time, is total
rather than cosmetic.

---

## Config-Integrity Assertion

```
runs: 10
prompt_hashes: {'bbb1e99d0963887d'}
config_hashes: {'7c2ac3de05b6e9ba'}
canonical_flags: {True}
fallback_flags: {False}
```

**PASS.** Identical to 424/426/427's hashes — the prompt and declared
config genuinely did not vary across the 10 runs, and did not vary from
the 427 report's successful single demonstration run either. The
measurement is not void on config-integrity grounds. Whatever caused the
0/10 result, it was not a config drift.

---

## Per-Parameter Table (the headline)

| Parameter | Extraction rate | Offsets (10 runs) | Span text stability |
|---|---|---|---|
| `tenant_share` | **0/10** | n/a — never resolved to a `Parameter` in any run | n/a |
| `building_share` | **0/10** | n/a | n/a |
| `rent_adjustment_pct` | **0/10** | n/a | n/a |
| `base_rent` | **0/10** | n/a | n/a |

There is no offset-stability or span-text-stability data to report for
any parameter, because `extract_parameters()` returned an **empty**
`parameters` dict on all 10 runs — not a partial result, not a
differently-worded quote, not a shifted offset. Nothing to compare across
runs because nothing was ever produced in the first place.

---

## Gate B Outcome Per Run

| Run | Extracted | Gate B |
|---|---|---|
| 1 | `[]` | **abort** |
| 2 | `[]` | **abort** |
| 3 | `[]` | **abort** |
| 4 | `[]` | **abort** |
| 5 | `[]` | **abort** |
| 6 | `[]` | **abort** |
| 7 | `[]` | **abort** |
| 8 | `[]` | **abort** |
| 9 | `[]` | **abort** |
| 10 | `[]` | **abort** |

Every abort carried the identical `GateAbortError` message, naming all
four dependencies:

```
Gate B failure: 4 declared parameter dependency(ies) unsatisfied:
[('LP-02', 'base_rent'), ('LP-02', 'rent_adjustment_pct'),
 ('LP-07', 'tenant_share'), ('LP-07', 'building_share')].
Cannot produce a valid legal analysis without required parameters.
Agreement among evaluators cannot substitute for a satisfied dependency.
```

Gate B itself behaved exactly as designed: it correctly detected that
none of the four declared dependencies were satisfied, and it correctly
raised `GateAbortError` in canonical mode on all 10 runs, with zero false
passes. **Gate B is not the problem. It is functioning as the fail-closed
gate it is supposed to be** — it is faithfully reporting that the layer
beneath it produced nothing to gate.

---

## Attachment Correctness Per Run

Vacuously "correct" and uninformative on all 10 runs: `attach_parameters_to_lp_evidence`
was called for LP-07 and LP-02 against an empty `parameters` dict each
time, and correctly returned `[]` for both — there was nothing to attach.
No attachment-mechanism defect is implicated; the dict-lookup logic tested
in 427 is untouched and has no bug surface exercised here, because its
input was empty on every run.

---

## Root-Cause Diagnosis (measurement context, not a fix)

The elapsed time per run was notably short (8.6–12.0s, vs. the
element-elicitation calls in 424/426 typically running 15–40s for
similarly-sized target lists) — a signal the call was returning quickly
rather than doing substantial work. A single supplementary diagnostic
probe, run **outside** the official 10-run measurement, called the exact
same underlying function (`elicit_spans_for_targets`) with the exact same
`PARAMETER_TARGETS`-derived element list, to inspect the model's raw
`target_matches` output directly:

```json
[
  {
    "target": "Target 1: Tenant's Share of Operating Expenses percentage",
    "quotes": ["Tenant's Share of Operating Expenses of Building: 100%"]
  },
  {
    "target": "Target 2: Building's Share of Project Operating Expenses percentage",
    "quotes": ["Building's Share of Project: 45.79%"]
  },
  {
    "target": "Target 3: Rent Adjustment Percentage (annual escalation rate)",
    "quotes": ["Rent Adjustment Percentage: 3%"]
  },
  {
    "target": "Target 4: Base Rent amount stated in the key-terms block",
    "quotes": ["Base Rent:\n$3.75 per rentable square foot of the Premises per month, subject to adjustment pursuant to Section 4 hereof."]
  }
]
```

**The model found all four values, correctly, with the values present —
not the label without the value.** `100%`, `45.79%`, `3%`, and
`$3.75 per rentable square foot` are all there, exactly as in 427's
successful demonstration run.

**What is wrong is the `"target"` field.** The prompt and schema ask for
the bare ordinal `"Target 1"`. The model, in this probe (and, the
checkpoint data imply, in all or nearly all of the 10 measured runs),
instead echoed the full descriptive label —
`"Target 1: Tenant's Share of Operating Expenses percentage"`.

`extract_parameters()`'s mapping from that field back to a parameter name
is:

```python
target_to_param = {f"Target {i}": e["element_id"] for i, e in enumerate(elements, start=1)}
...
param_name = target_to_param.get(match.get("target", ""), match.get("target", ""))
if param_name not in PARAMETER_NAMES:
    continue
```

`target_to_param` only contains the bare keys (`"Target 1"`, `"Target
2"`, ...). When the model returns the fuller string, the dict lookup
misses, falls back to the raw (fuller) string as `param_name`, that
string is not in `PARAMETER_NAMES`, and the `continue` **silently
discards the entire record — quotes included** — without ever calling
`resolve_span` on it. This is why `parameters` came back empty on every
run despite the model doing its job correctly on (at minimum) the probed
occasion.

**This is not a new phenomenon — it is a previously-named one, now fatal
instead of cosmetic.** 424 categorized 29 raw records with this exact
"Target N: full label" pattern under `malformed_target_label`; 426 found
one on a `verified` span (`Condition Precedent`, elicited by `'Target 2:
Commencement date or conditions for commencement are defined'`).
`lease_element_elicitation.py`'s `resolve_elicited_spans()` — the LP path
— has the identical fallback (`target_to_element.get(label, label)`) but
**does not filter on membership in a known set** afterward; it tags the
record with whatever string it derived and keeps going, so a malformed
label there degrades to an audit-labeling defect. `lease_parameter_block.py`'s
`extract_parameters()` **does** filter (`if param_name not in
PARAMETER_NAMES: continue`), and that filter is what converts the same
underlying model behavior into total data loss.

**Per the brief, `lease_parameter_block.py` was not changed to fix this.**
The diagnosis above is offered so the finding is legible, not as a patch.

---

## What This Means for the Dependency Map

This is a stability finding, and it belongs to the same class 421C
documented, one layer up: **evidence that exists and is correctly located
can still fail to reach a dependent LP — not because of what the model
did, but because of an unverified assumption in the code between the
model's output and the gate.** 421C found material clauses routed to the
wrong bucket by an unreviewed single-model call. 428 finds a correctly-
located, correctly-valued parameter discarded by an unreviewed string-
match in the layer that was supposed to be the reliable one. The pattern
repeats: the failure is invisible to anything that only checks "did the
gate pass," because the gate is working exactly as designed — it aborted,
loudly, ten times out of ten, which is why this was caught rather than
silently shipped.

---

## Files Changed

- `build_log/428_chat_instruction.md` — the Part 0 brief, written verbatim
  before any work began
- `build_log/428_gate_c_parameter_assignment_stability.md` — this file

No source files were modified. `lease_parameter_block.py`, the prompt,
the resolver, and the normalization profile are byte-identical to their
427 state — confirmed by `git status` showing no diff to any of them.
