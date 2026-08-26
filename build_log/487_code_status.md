# Step 487 — Deployed. Two runs measured, then stopped for spend.

**Date:** 2026-08-26 · **Instruction:** `build_log/487_chat_instruction.md` (+ 2026-08-26 amendment)
**Push: DONE** (`740cb9b..046cb4c`, branch only, 0 tags on remote).
**Measurement: PARTIAL — 2 of 6 Atlas runs, 0 of 1 divall.** Stopped mid-flight for spend.
**This step is a record. No runs, no fix, no schema change.**

---

## THREE CORRECTIONS TO THE BRIEF, MADE BEFORE ANYTHING ELSE

The amendment restated facts I reported in conversation. Re-reading the stored results, **three are
wrong** — and one of them is mine. Per Reporting Integrity Rule 2 the record follows the stored file,
not the recalled report.

### Correction 1 — atlas_1 is NOT clean. Both runs are degraded, identically.

The brief says `atlas_1 … clean panel (gpt-5.5 202/202), degraded False`. From
`/api/jobs/lease_review_20260826_032949_5e8709/results`:

```
run_degraded=True  degraded_reason='evaluator_fallback'  invalid_for_legal_analysis=False
fallback_events n = 30
```

**I reported `degraded=False` in conversation. That was my error** — I printed
`invalid_for_legal_analysis` (which *is* False) under a `degraded=` label. `run_degraded` is True on
**both** runs. The `gpt-5.5 202/202` figure is correct but describes **role B only**; it is not a
clean panel.

### Correction 2 — the provider failure is NOT confined to atlas_2, and there was no clean hour.

The brief says *"Atlas_1 an hour earlier was clean."* It was not. Per-role, per-element census over
`element_verdicts[].evaluator_verdicts[].actual_model`:

| run | role A | role B | role C |
|---|---|---|---|
| **atlas_1** | `gemini-2.5-pro` **196** (`is_fallback` true) + `claude-sonnet-4-6` 6 (see Correction 3) | `gpt-5.5` 202, no fallback | `grok-4.3` 202, no fallback |
| **atlas_2** | `gemini-2.5-pro` **202** (`is_fallback` true) | `gpt-5.5` 202, no fallback | `grok-4.3` 202, no fallback |

**Role A was substituted on both runs. There is no observed window in which Anthropic was serving.**

### Correction 3 — "from 04:04 UTC" is not a failure time.

Within each run **all 30 `fallback_events` carry one identical timestamp to the microsecond** —
atlas_1 `2026-08-26T03:45:34.456806+00:00`, atlas_2 `2026-08-26T04:04:42.105627+00:00` (first == last
in both). A timestamp shared by 30 events across 30 LPs spanning ~15 minutes of wall clock is stamped
at **record assembly**, not at failure. **No onset time for the outage is recoverable from these
runs.** Any temporal inference from these fields is unsupported.

---

## 1. The two deployed runs

| | **atlas_1** | **atlas_2** |
|---|---|---|
| job id | `lease_review_20260826_032949_5e8709` | `lease_review_20260826_034939_3ffec6` |
| created (UTC) | 03:29:49 | 03:49:39 |
| status | `completed` | `completed` (carries `cancel_requested`) |
| `api_calls_total` | **98** | **98** |
| `elapsed_sec` | **944.28** | **902.30** |
| `run_degraded` | **True** | **True** |
| `degraded_reason` | `evaluator_fallback` | `evaluator_fallback` |
| `invalid_for_legal_analysis` | False | False |
| `extraction_completeness_failed_lps` | `[]` | `[]` |
| `completeness_failures` | `[]` | `[]` |
| coverage entries | 32 | 32 |

**Both are non-aborts.** The extraction-completeness gate — the thing Steps 476–484 rebuilt — did not
fire on either run. Aborts: **0 of 2.**

**atlas_2 was cancelled, and the cancel arrived after completion.** `POST /api/jobs/{id}/cancel`
returned `{"status":"cancel_requested"}`; the job dict retains `cancel_requested`, and the job then
reached `completed` with a full 98-call result. **A `cancel_requested` marker on this job is not a
deployed failure and must not later be read as one.** The pipeline checks the cancel flag at stage
boundaries; this one had none left to cross.

## 2. The seamed LPs — stable across both runs, and matching local Step 484

```
  LP       state             fnd  mis  conf   spans  attn
  LP-07    partial            5    1   high     5    True     (both runs)
  LP-12    review_needed      0    0   high    13    True     (both runs)
  LP-27    partial            8    1   high   7 / 8  True
```

LP-12, both runs, identical:

```
applicability=applicable | tenant_text 2605 chars | "13.2" present: True
coverage_method=step_305_per_element | span_evidence_records=13
```

**`elements_found` lists are byte-identical between the two runs on all three seamed LPs.**
`tenant_text` is identical on LP-07 (1957 chars) and LP-12 (2605 chars).

**One difference, recorded rather than smoothed:** LP-27 produced **7** span records / 976 chars on
atlas_1 and **8** / 1043 on atlas_2. The found/missing split is unchanged at 8/1 and the found list is
identical, so the extra span changed no verdict — but the brief's "LP-27 8/1" describes the verdict,
not the evidence, and the evidence is not identical.

These match the local Step-484 Atlas run (LP-07 5/1 @ 5 spans; LP-12 13 spans, 2,605 chars, §13.2 and
§13.3 present; LP-27 8/1).

## 3. ESTABLISHED

**The 476–486 code executes correctly deployed.** Step 475 attempted four deployed runs and produced
**zero** completions; these are the first. Specifically, and matching local exactly:

- **the 423 seam** — LP-07/12/27 source evidence from verified spans with resolvable `[Section N.N]`
  locators, on both runs;
- **the seam-aware gate** (Step 484) — LP-12's extraction bucket no longer being the gate's basis, no
  abort on either run;
- **the LP-12 applicability fix** (Step 481) — `applicability=applicable`, `requires_attention=True`,
  13 spans, §13.2 present. Previously `not_applicable` / *"absent by design"*, which was false.

## 4. NOT ESTABLISHED

- **The abort rate.** **Two completions is not a rate.** The six-run measurement was stopped for
  spend after 1.5 runs. Three more Atlas runs (~290 calls) would give a rate with a wide interval.
- **Divall deployed.** **Never completed deployed. Not attempted this step.**
- **Whether the seamed LPs are stable on a panel with role A actually served by
  `claude-sonnet-4-6`.** Both runs ran a substituted role A. The local Step-484 agreement is
  reassuring but was a different panel composition, so the deployed evidence for stability is *two
  runs of the same degraded configuration*, not two runs of the specified one.

---

# 5. THE PROVIDER FINDING

## 5.1 What was observed

**Every role-A call to Anthropic that ran hard-failed, on both runs, with same-provider retry also
failing.** Verbatim, `fallback_events[0]`, atlas_2:

```json
{
  "event_type": "fallback", "stage": "305", "lp_id": "LP-01", "role": "A",
  "requested_model": "claude-sonnet-4-6", "requested_provider": "anthropic",
  "actual_model": "gemini-2.5-pro", "actual_provider": "google",
  "fallback_reason": "api_error", "fallback_class": "hard",
  "same_provider_retry_attempted": true, "same_provider_retry_succeeded": false,
  "abstained": false, "abstain_reason": null
}
```

30 events per run. `same_provider_retry_succeeded` is **false on all 60**. `abstained` false on all 60.

**The 30 is all 30 LPs that ran 305.** The other two of the 32 coverage entries, **LP-23 and LP-31,
carry zero element verdicts and no evaluator roles at all** — the `unclear` applicability
short-circuit measured at Step 478. So the failure rate is 30/30, not 30/32.

**This is provider-level, not sporadic.** What cannot be said is *when it began* — see Correction 3.

## 5.2 The record cannot name the cause

`_classify_failure` at `lease_coverage_305.py:161-181`:

```python
    if ("_error:" in m or "timeout" in m or "timed out" in m or "rate" in m
            or "429" in m or "connection" in m or "unauthorized" in m
            or "401" in m or " 500" in m or " 502" in m or " 503" in m):
        return "api_error"
```

**`api_error` collapses timeout, rate limit, 429, 401 unauthorized, connection failure and 5xx into one
label, and only the label is persisted** — `error_msg` is consumed by the classifier and does not
appear in the event record. So the record **cannot distinguish credit exhaustion from an auth failure
from a rate limit from a provider outage.**

This is the same shape as the `reasoning_exhaustion` naming defect recorded at Step 449: **a label that
asserts a cause the classifier does not observe.** `api_error` is honest by comparison — it names a
category rather than a mechanism — but it is lossy at exactly the point where the distinction decides
what to do next.

## 5.3 Same defect one layer down: `actual_model` names a model that produced nothing

On **atlas_1 LP-17**, the fallback event is not a fallback:

```json
{"event_type": "all_failed", "lp_id": "LP-17", "role": "A",
 "requested_model": "claude-sonnet-4-6", "actual_model": null, "actual_provider": null,
 "fallback_reason": "api_error", "fallback_class": null,
 "same_provider_retry_attempted": true, "same_provider_retry_succeeded": false}
```

Role A produced nothing at all — not even a substitute. `per_evaluator_lp_verdicts` confirms it:
`{"C": "explicitly_present", "B": "explicitly_present"}` — **a two-evaluator panel.**

**But the element records say otherwise.** All six of LP-17's `evaluator_verdicts` for role A read:

```
verdict='unclear'  confidence='low'  citation=null  is_fallback=False
actual_model='claude-sonnet-4-6'
reasoning='Evaluator A did not complete'
```

**`actual_model` names Anthropic and `is_fallback` is False on six verdicts produced by no model at
all.** Only the free-text `reasoning` string carries the truth. This is why my own first census
reported "6 × `claude-sonnet-4-6`, not fallback" — the census was reading a stub as a call. **Any
count over `actual_model` / `is_fallback` over-reports provider service by exactly the stub count.**

**Measured consequence:** LP-17 is one of the LPs whose verdict differs between the two runs —
`partial 5/1` on atlas_1 (two evaluators) versus `covered 6/0` on atlas_2 (three). Not proof of
causation from one pair, but it is the one LP where the panel width demonstrably differed.

## 5.4 CONSEQUENCE — a degraded panel completes, and says nothing

**A run whose entire role-A seat was served by a substituted model produced a full report and reported
nothing to the user on any surface.** Traced to the consumers, per Rule 4:

- **Web banner** — `app.js:18740` keys on `r.invalid_for_legal_analysis || r.extraction_completeness_failed`.
  Both **False** here. Banner does not render.
- **All six export surfaces** — `lease_display.py:378-381`,
  `invalid_for_legal_analysis or extraction_completeness_failed or summary.REPORT_INCOMPLETE`.
  All **False/absent** here. No banner in the annotated DOCX, annotated PDF, summary DOCX, batch DOCX
  or combined PDF.
- **Polled job status** — `run_degraded` **does** reach `_build_job_outcome` (`job_manager.py:271-277`)
  and would set `run_quality="degraded"` at `:335`. But the outcome goes to
  `_append_job_event(job_id, "job_outcome", **outcome)` (`job_manager.py:1584-1585`) — **the event
  stream, not the job dict.** `GET /api/jobs/{job_id}` returns `get_job_snapshot(job)`
  (`main.py:303`), which carries no outcome block. **Confirmed empirically: neither job's polled status
  contains `run_quality` at all.**

**This answers Step 486 Part B item 4 in the negative: `run_quality` does not reach the polled status.**

**So if the cause is credit exhaustion, further runs degrade silently rather than failing loudly, and
the only signal is the `fallback_events` census inside the stored result** — which no surface reads and
no user sees.

**And the frozen-panel claim does not hold on these runs.** The specified panel is
A=`claude-sonnet-4-6`, B=`gpt-5.5`, C=`grok-4.3`. Both deployed runs ran A=`gemini-2.5-pro`, and
atlas_1 ran LP-17 on two evaluators. **Any measurement taken from these two runs is a measurement of a
substituted panel.** The seamed-LP agreement in §2 is reported with that caveat attached.

## 5.5 Run-to-run variance under the substituted panel

**8 of 32 LPs differ** between atlas_1 and atlas_2 on `(coverage_state, found, missing)`:

| LP | atlas_1 | atlas_2 |
|---|---|---|
| LP-02 | partial 2/1 | partial 3/1 |
| LP-03 | partial 3/3 | review_needed 3/1 |
| LP-05 | missing 1/2 | missing 1/3 |
| LP-09 | review_needed 7/0 | partial 7/0 |
| LP-17 | partial 5/1 | covered 6/0 |
| LP-21 | partial 3/2 | partial 3/1 |
| LP-26 | partial 6/0 | review_needed 6/0 |
| LP-32 | partial 4/2 | partial 6/2 |

Both runs share the substituted panel, so **this is not an A/B on panel composition** and says nothing
about what the specified panel would have produced. It is recorded as the observed variance floor
under the configuration that actually ran. **The three seamed LPs are not in this list.**

---

## 6. OPEN ITEM — not fixed this step

**Persist the raw provider error alongside the class.** `_classify_failure` receives `error_msg` and
returns only a category; the event record keeps the category. Retaining the raw message (or at minimum
the HTTP status) would separate credit exhaustion from an outage from an auth failure — currently
indistinguishable, and they call for opposite responses.

Two adjacent items surfaced by this step, also **not fixed**:

- **`actual_model` / `is_fallback` are wrong on `all_failed` stubs** (§5.3). A stub carries the
  requested model and `is_fallback: False`. Any census over these fields over-counts.
- **`run_quality` does not reach the polled job status** (§5.4). It is emitted to the job-event stream
  only. Whether that is intended was not determined.

## 7. What was NOT done from the original brief

- **Runs 3–6.** Not started. Stopped for spend.
- **The divall deployed run.** Not started.
- **Deployed SHA confirmation.** Not observable via any endpoint; `GIT_SHA` reaches
  `_build_job_outcome` (`job_manager.py:358`) but that block is not returned by
  `GET /api/jobs/{job_id}`, per §5.4. **Not confirmed.**
