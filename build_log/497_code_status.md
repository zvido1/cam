# Step 497 — Provenance fixed, then substitution disclosed on all six surfaces

**Date:** 2026-08-30 · **Instruction:** `build_log/497_chat_instruction.md`
**Part A verified against Step-487 stored data. Part B verified by artefact on three real results.**
**Tests 359 passed. Zero provider calls. Not deployed.**

---

# PART A — PROVENANCE, FIXED FIRST

## What a stub carries now, and why

`lease_coverage_305.py:854`, the branch taken when an evaluator produced nothing:

```python
"label": f"Evaluator {role}",
"actual_model": None,
"actual_label": None,
"is_fallback": None,
"served": False,
"requested_model": _primary_model,
```

**Reasoning, field by field:**

- **`actual_model: None`.** The field's name asserts *what actually served*. No model served. `None`
  is the only true value; naming the requested model was the defect.
- **`is_fallback: None`, not `False`.** `False` is an affirmative denial that substitution occurred,
  on a record that exists *because* the fallback chain came up empty. `None` says the question does
  not apply.
- **`served: False` — new, and the point of the change.** The truth previously lived only in the
  free-text `reasoning` string. A census cannot key on prose. This makes it structured and queryable.
- **`requested_model` — new.** Nothing is lost: the information the old `actual_model` held is kept,
  under a name that is true.
- **`label`** no longer falls through to the lineup label (which produced `"Claude Sonnet 4.6"`).

**`evaluator_meta` (`:1344`) had the same defect** — on a failed evaluator both failure-path returns
set `r["model"]` from `evaluator_cfg`, i.e. the requested model. Now nulled unless `completed`.

**Deliberately NOT changed:** the second stub branch (`match is None`). There the evaluator *did*
serve and merely omitted one element, so `actual_model` is correct and must stay.

## Verified against the Step-487 stored results

The brief's test: *"the census must report role A served 0, not 196 or 202."* Applying the corrected
rule to the stored files:

```
atlas_1  (202 role-A records, 6 stubs)
   OLD (file as written)    role A: {'gemini-2.5-pro': 196, 'claude-sonnet-4-6': 6}
   STEP-497 corrected       role A: {'gemini-2.5-pro': 196, None: 6}
   claude-sonnet-4-6 served:  OLD=6   CORRECTED=0

atlas_2  (202 role-A records, 0 stubs)
   claude-sonnet-4-6 served:  OLD=0   CORRECTED=0
```

**`claude-sonnet-4-6` served 6 → 0.** `gemini-2.5-pro`'s 196 is unchanged and correct — it did serve
those. The 6 that were falsely attributed to Anthropic are now attributed to no model.

---

# PART B — DISCLOSURE

## The threshold rule, and the defence of it

Two tiers, in `lease_display.panel_substitution()`:

**Tier `substituted` — banner.** Either:
- **(a)** some issue area lost a seat entirely (a role produced no verdict there), so that area was
  decided by **two evaluators, not three**; or
- **(b)** some role's own primary served **fewer than half** of that role's element verdicts.

**Tier `noted` — recorded in the structured field and the job aggregate, no banner.** Any
substitution clearing both bars.

**Why this rule:**

- **The claim being protected is panel composition** — "three named models evaluated this". Clause
  (b) fires exactly when the model the report names did a *minority* of its own seat's work.
- **50% is a majority, not a tuned constant.** It is the point at which the named model stops being
  the one that mostly did the work. I did not pick it to make the examples come out right.
- **(a) is separate on purpose.** A lost seat is not a substitution question at all — it is a
  **quorum** question. A 2-of-3 majority is a different instrument, not a different model, and no
  percentage of substitution captures that.
- **Nothing is silently suppressed.** Tier `noted` is carried in `panel_substitution` on the result
  and surfaces as `panel_fallback_noted` in the job aggregate. It is not a banner because a single
  transient retry on one issue area does not falsify the panel claim for the other 31.

**Against the three real cases:**

| case | tier | why |
|---|---|---|
| **487 atlas_1** | **substituted** | (a) LP-17 seat lost **and** (b) role A primary served 0 of 202 |
| **487 atlas_2** | **substituted** | (b) role A primary served 0 of 202 |
| **496 atlas** | **noted** | role A primary served **191 of 202** (94.6%); one LP, transient |
| 491 atlas | *(None)* | every seat served by its primary |
| 496 divall | *(None)* | panel clean — its degradation is extraction, not panel |

**496 divall is the case that proves the two facts are kept apart:** its report is INCOMPLETE
(LP-30/31/32) and its panel is clean. The panel banner correctly stays silent.

## The message is distinct, deliberately

```
PANEL SUBSTITUTED - NOT THE EVALUATOR PANEL THIS REPORT NAMES
This document was evaluated by a substituted panel: gemini-2.5-pro stood in on 29 issue area(s).
Evaluator seat(s) A were served mostly by a model other than the one named.
Decided by two evaluators rather than three: LP-17.
Findings are not invalid, but the evaluator panel is not the one this report names.
```

`incomplete_statement` is **not** overloaded — separate function, separate constant, separate colour
(**amber `#B45309`**, not the incompleteness red `#B42318`), and the closing line states the
difference explicitly: *the findings are not invalid*. Incompleteness says part of the document was
not analysed; this says the analysis was done by a different panel.

## The six surfaces

| surface | change |
|---|---|
| web banner | new `renderPanelBanner()`, own `#panel-substitution-banner` div, amber CSS |
| job aggregate | `panel_substituted` / `panel_fallback_noted`; does **not** set `has_any_incomplete` |
| annotated DOCX | amber block after the incompleteness block, **hex-string** colours |
| annotated PDF | own banner page at index 0, inserted after the incompleteness page |
| summary DOCX | amber block, **RGBColor** — this writer takes a different colour type |
| batch DOCX | count plus per-tenant naming, mirroring Step 486 |

The DOCX colour split is the Step-485 trap: `lease_docx_annotator._add_para` writes into `w:val` and
needs a hex string; `summary_generator` uses python-docx runs and takes `RGBColor`. Passing the wrong
one is swallowed by a non-fatal `except` and silently drops the whole section.

---

# VERIFICATION BY ARTEFACT

Three real results: **A** = Step-487 atlas_1 (whole seat substituted + seat lost), **B** = Step-496
Atlas (one LP, benign), **C** = Step-491 clean.

### Annotated DOCX — first paragraphs

```
A_487_substituted:
   | PANEL SUBSTITUTED - NOT THE EVALUATOR PANEL THIS REPORT NAMES
   | This document was evaluated by a substituted panel: gemini-2.5-pro stood in on 29 issue area(s).
   | Evaluator seat(s) A were served mostly by a model other than the one named.
   | Decided by two evaluators rather than three: LP-17.
   | Findings are not invalid, but the evaluator panel is not the one this report names.

B_496_noted:    | CAM Lease Analysis Report      <- unchanged
C_491_clean:    | CAM Lease Analysis Report      <- unchanged
```

### Annotated PDF — page one and page count

```
A_487_substituted  14 pages   | PANEL SUBSTITUTED - NOT THE EVALUATOR PANEL THIS REPORT NAMES
B_496_noted        13 pages   | STANDARD RETAIL LEASE AGREEMENT     <- unchanged
C_491_clean        13 pages   | STANDARD RETAIL LEASE AGREEMENT     <- unchanged
```

### Summary DOCX

```
A: | Contract Analysis Summary
   | PANEL SUBSTITUTED - NOT THE EVALUATOR PANEL THIS REPORT NAMES
   | This document was evaluated by a substituted panel: gemini-2.5-pro stood in on 29 issue area(s).
B: | Contract Analysis Summary / | Tenant: atlas_meridian_warehouse_lease.txt   <- unchanged
C: | Contract Analysis Summary / | Tenant: atlas_meridian_warehouse_lease.txt   <- unchanged
```

### Batch DOCX

```
MIXED     | Batch Lease Analysis Summary
          | PANEL SUBSTITUTED - NOT THE EVALUATOR PANEL THIS REPORT NAMES - 1 of 2 report(s) affected
          | atlas_SUBSTITUTED.txt -- This document was evaluated by a substituted panel: gemini-2.5-pro...
          | Executive Summary
ALL_CLEAN | Batch Lease Analysis Summary
          | Executive Summary                    <- unchanged
```

### Job aggregate

```
A substituted  run_quality=degraded  panel_substituted=True   panel_fallback_noted=False  report_incomplete=False
B noted        run_quality=degraded  panel_substituted=False  panel_fallback_noted=True   report_incomplete=False
C clean        run_quality=clean     panel_substituted=False  panel_fallback_noted=False  report_incomplete=False
```

**Clean is unchanged by construction, not by inspection:** `panel_substitution_lines()` returns
`None` for B and C, so every banner block is skipped.

**B is the important row.** A benign one-LP fallback produces **no banner anywhere** — DOCX, PDF and
summary are byte-equivalent to clean — while still being recorded as `panel_fallback_noted=True` in
the aggregate. That is the threshold rule doing its job on both sides.

## A correction against myself

I announced a bug in the job aggregate — `panel_substituted=False` on the substituted case — and
called it a fourth consecutive artefact-caught defect. **It was my test, not the code.** I passed
`results` inline; `_build_job_outcome` reads `t["result_path"]` and loads from disk, so the tenant
fell into the `missing_results` branch and never reached the new code. Retested through the real
consumer path, it is correct. **The code was right and my harness was wrong.**

## WHAT IS NOT ESTABLISHED

- **No run has executed with the Part A fix in place.** The 6 → 0 verification applies the corrected
  rule to stored data; it does not observe the new code emitting `served: False`. Zero calls were
  spent this step, by instruction.
- **`run_quality` still does not reach the polled job status.** Step 491 established the outcome goes
  to the job-event stream, not the job dict. **`panel_substituted` inherits that defect** — it is in
  the aggregate, and the aggregate is still not returned by `GET /api/jobs/{id}`. **Unfixed.**
- **The web banner was not rendered in a real browser.** Same gap Step 486 recorded for the
  incompleteness banner.
- **The threshold is untested on a middling case.** Every real case is either ~0% or ~95% primary
  service. A run at 40–60% has never been observed, and that is exactly where clause (b) decides.
- **Old stored results have no `served` field.** `panel_substitution()` honours both the new field
  and the legacy `reasoning` string; if that prose is ever reworded, legacy detection breaks silently.
- **Batch PDF (`generate_combined_summary_pdf`) was not exercised** — only the batch DOCX. Step 485
  recorded the same gap.
