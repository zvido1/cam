# Finding: evaluator substitution is unmarked, and the provenance fields misreport it

**Date:** 2026-08-26 · **Status:** MEASURED on two deployed runs. **Nothing fixed.**
**Step:** 488 (record). Measurement is Step 487; runs are `atlas_1`
(`lease_review_20260826_032949_5e8709`) and `atlas_2` (`lease_review_20260826_034939_3ffec6`).
**Companions:** `487_code_status.md`, `486_code_status.md` §B4, `449` (the `reasoning_exhaustion`
naming defect), `FINDING_prompt_strictness_does_not_fix_entailment.md`.

---

## The one-sentence version

**A run can lose an entire evaluator seat — or lose an evaluator outright and fabricate its verdicts
as stubs labelled with the model that did not produce them — and complete, report, and export with no
mark on any surface, while the fields an auditor would query to detect it say the opposite.**

---

# 1. THE MISLABELLING

On `atlas_1`, LP-17, role A. **Two records of the same fact, inside one result file, that contradict
each other.**

### The LP-level record — role A produced nothing

From `fallback_events`, verbatim:

```json
{
  "event_type": "all_failed",
  "stage": "305",
  "lp_id": "LP-17",
  "role": "A",
  "requested_model": "claude-sonnet-4-6",
  "requested_provider": "anthropic",
  "actual_model": null,
  "actual_provider": null,
  "fallback_reason": "api_error",
  "fallback_class": null,
  "same_provider_retry_attempted": true,
  "same_provider_retry_succeeded": false,
  "abstained": false,
  "abstain_reason": null,
  "timestamp": "2026-08-26T03:45:34.456806+00:00"
}
```

`event_type` is **`all_failed`**, not `fallback`. `actual_model` and `actual_provider` are **null**.
The primary failed, the same-provider retry failed, and **no substitute was obtained** — this is the
one LP in either run where the fallback chain itself came up empty.

The LP roll-up agrees:

```
per_evaluator_lp_verdicts = {"C": "explicitly_present", "B": "explicitly_present"}
```

**Two evaluators. Role A is absent.**

### The element records — six verdicts attributed to Anthropic

All six of LP-17's elements carry a role-A `evaluator_verdicts` entry. Verbatim, the first
(`LP-17.dispute_mechanism`); the other five are identical but for the element:

```json
{
  "role": "A",
  "label": "Claude Sonnet 4.6",
  "actual_model": "claude-sonnet-4-6",
  "actual_label": "Claude Sonnet 4.6",
  "is_fallback": false,
  "verdict": "unclear",
  "citation": null,
  "reasoning": "Evaluator A did not complete",
  "confidence": "low"
}
```

Elements: `LP-17.dispute_mechanism`, `LP-17.governing_law`, `LP-17.venue_jurisdiction`,
`LP-17.attorney_fee_allocation`, `LP-17.jury_trial_waiver`, `LP-17.claims_time_limit`. The
`reasoning` string is byte-identical across all six.

### What that is

**Six verdicts produced by no model at all, carrying four separate fields that name the model which
did not produce them** — `label`, `actual_model`, `actual_label`, and `is_fallback: false`.

`actual_model` is not a request field. Its name asserts what *actually served* the call. On these six
records it names a model that served nothing. `is_fallback: false` compounds it: the record does not
merely mislabel the model, it affirmatively denies that any substitution occurred — on a record
created *because* substitution failed.

**The only field carrying the truth is `reasoning`, a free-text string.** Nothing structured, nothing
queryable, nothing a schema would validate.

## 1.1 It defeated a census run against the same data

This is not hypothetical. **My own census, run over these exact files during Step 487, reported:**

```
=== atlas_1
   role A  claude-sonnet-4-6     6   is_fallback=0
   role A  gemini-2.5-pro      196   is_fallback=196
```

Read straight, that says *"Anthropic served 6 element verdicts on atlas_1 without falling back"* —
and I initially read it that way, as evidence that role A was partially served and therefore that the
outage began partway through the run. **All six are stubs. Anthropic served zero.**

The correction came only from opening the individual records and reading a prose field. **A census
over the provenance fields — the obvious and correct thing to query — produces a wrong answer, and
produces it silently, with no null, no error and no anomaly to notice.**

**Any count over `actual_model` / `is_fallback` over-reports provider service by exactly the stub
count.** Across both runs: 404 role-A element records, 6 of them stubs, 0 genuinely served by
Anthropic.

**This is Rule 4 in the reporting-integrity list turned on the data layer.** "Written" is not "wired";
here, *recorded* is not *served*, and the record does not distinguish them.

---

# 2. THE SILENT PATH — traced, not inferred

Both deployed runs carry `run_degraded=True`, `degraded_reason='evaluator_fallback'`. **Neither
surfaces anything to a user.** Traced to each consumer:

### 2.1 The web banner — does not render

`static/app.js:18740`, inside `renderIncompleteBanner()`:

```javascript
        if (r.invalid_for_legal_analysis || r.extraction_completeness_failed) {
```

On both runs `invalid_for_legal_analysis` is **False** and `extraction_completeness_failed` is
**False**. The predicate is false; the banner stays hidden.

### 2.2 All six export surfaces — no banner

`cam/adapters/lease_review/lease_display.py:369-381`:

```python
def incomplete_report_lines(results: dict):
    """Return the banner lines for an incomplete result, or None if complete.

    None means "say nothing" -- a complete report must be byte-identical to what
    it produced before this step.
    """
    if not isinstance(results, dict):
        return None
    summary = results.get("summary") or {}
    incomplete = bool(
        results.get("invalid_for_legal_analysis")
        or results.get("extraction_completeness_failed")
        or summary.get("REPORT_INCOMPLETE")
```

All three disjuncts are False/absent on an `evaluator_fallback` run, so the function returns `None` —
which, by its own docstring, means *"say nothing"*. That single return governs the annotated lease
DOCX, the annotated lease PDF, the summary DOCX, the batch DOCX and the combined synopsis PDF.

### 2.3 The polled job status — `run_quality` is computed and then does not arrive

`run_quality` **is** derived correctly. `05 Lease Analyzer/app/job_manager.py:271-277`:

```python
        _run_degraded = bool(r.get("run_degraded"))
        _incomplete = bool(r.get("invalid_for_legal_analysis"))
        _missing_lps = list(r.get("extraction_completeness_failed_lps") or [])
        if _run_degraded or _incomplete:
            has_any_degraded = True
        if _incomplete:
            has_any_incomplete = True
```

`has_any_degraded` becomes True, and at `:335` that yields `run_quality = "degraded"`.

**Then it is written somewhere the API does not read.** `job_manager.py:1583-1585`:

```python
            outcome = _build_job_outcome(job_id, tenants, job.get("started_at"))
            _append_job_event(job_id, "job_outcome", **outcome)
```

The outcome goes to the **job-event stream**. It is never written onto the job dict. And
`05 Lease Analyzer/app/main.py:303`:

```python
    job = job_manager.get_job_snapshot(job_id)
```

`GET /api/jobs/{job_id}` returns that snapshot. **Confirmed empirically on both jobs: the polled
status payload contains no `run_quality` key at all.** Its keys are `job_id, domain, status,
created_at, started_at, completed_at, email, estimated_minutes, input_config, feedback, error,
lp_progress, expires_at` (atlas_2 adds `cancel_requested`).

**This answers Step 486 Part B item 4 in the negative.** That item asked for confirmation that
`run_quality` reaches the polled status. It does not.

### 2.4 State plainly

**The Step 476–486 degraded-marker work covers EXTRACTION failures only.**

Every predicate on every surface keys on `invalid_for_legal_analysis`,
`extraction_completeness_failed`, or `summary.REPORT_INCOMPLETE` — three fields set by the
extraction-completeness gate and by nothing else. `run_degraded` and `degraded_reason` are set by the
evaluator path but **read by no presentation surface**.

**Evaluator substitution is unmarked on every surface: web, five exports, and the polled job status.**

That is not a criticism of 476–486, which did what it was scoped to do. It is a statement of the
remaining hole, and the hole is larger than the part that was filled: **a run can lose an entire
evaluator seat and still present as a clean, complete, valid report.**

---

# 3. THE DIAGNOSTIC GAP

`cam/adapters/lease_review/lease_coverage_305.py:161-181`:

```python
def _classify_failure(error_msg: str, model: str) -> str:
    """Classify why a primary evaluator call failed (Step 372c observability).
    ...
    """
    m = (error_msg or "").lower()
    if "degraded" in m or "already claimed" in m:
        return "provider_unavailable"
    if ("_error:" in m or "timeout" in m or "timed out" in m or "rate" in m
            or "429" in m or "connection" in m or "unauthorized" in m
            or "401" in m or " 500" in m or " 502" in m or " 503" in m):
        return "api_error"
```

**`api_error` is one label over at least five distinct conditions:** timeout, rate limiting, HTTP 429,
HTTP 401 unauthorized, connection failure, and 5xx server errors. `error_msg` is consumed by the
classifier and **does not appear in the persisted event** — only the returned class does.

**Consequence: credit exhaustion, a provider outage, and an auth failure are indistinguishable in the
record.** All 60 role-A failures across both runs are `api_error`. Nothing recoverable from the stored
results separates *"the account is out of credit"* from *"Anthropic had an incident"* from *"the key
is wrong."* Those three call for opposite responses — top up, wait, rotate — and the record supports
choosing among them not at all.

**Same shape as the `reasoning_exhaustion` defect recorded at Step 449: a label that asserts a cause
the classifier does not observe.** `api_error` is the better-behaved of the two — it names a category
rather than a mechanism, so it does not actively assert a false cause — but it is lossy at exactly the
point where the distinction determines what to do.

**And note the pattern across §1 and §3:** the same result file mislabels *which model served*
(§1) and cannot say *why the intended one didn't* (§3). Provenance and diagnosis fail together.

---

# 4. CORRECTIONS TO THE RECORD, ATTRIBUTED

Three facts were asserted in conversation and carried into the Step 488 brief. **The stored results
falsify all three.** Attribution matters here because the corrections are not symmetric — one is mine
and two are Chat's.

### 4.1 "atlas_1 had a clean panel" — FALSE. *(Origin: mine, Step 487 conversation.)*

I reported `degraded=False` for atlas_1. The stored result says:

```
run_degraded=True   degraded_reason='evaluator_fallback'   fallback_events n = 30
```

**I printed `invalid_for_legal_analysis` — which *is* False — under a `degraded=` label.** The
`gpt-5.5 202/202` figure I gave alongside it is accurate, but describes **role B only** and is not
evidence about the panel. Role A was `gemini-2.5-pro` on **196 of 202** element verdicts, with the
remaining 6 being the stubs of §1. Anthropic served **zero**.

### 4.2 "There was a clean window an hour earlier" — NOT OBSERVED. *(Origin: Chat, inherited from 4.1.)*

Both runs ran a substituted role A:

| run | role A | role B | role C |
|---|---|---|---|
| atlas_1 | `gemini-2.5-pro` 196 (fallback) + 6 stubs | `gpt-5.5` 202, clean | `grok-4.3` 202, clean |
| atlas_2 | `gemini-2.5-pro` 202 (fallback) | `gpt-5.5` 202, clean | `grok-4.3` 202, clean |

**There is no observed window in which Anthropic served this pipeline.** The two runs are the whole
deployed record.

### 4.3 "The failure began at 04:04 UTC" — NOT RECOVERABLE. *(Origin: Chat.)*

Within each run, **all 30 `fallback_events` carry one identical timestamp to the microsecond**:
atlas_1 `2026-08-26T03:45:34.456806+00:00`, atlas_2 `2026-08-26T04:04:42.105627+00:00` — first ==
last in both. Thirty events, across thirty LPs, spanning roughly fifteen minutes of wall clock,
sharing a single microsecond. **The field is stamped at record assembly, not at failure.**

**No onset time is recoverable from these runs**, and any temporal inference from these fields is
unsupported.

### 4.4 What 4.2 costs — the "discrete provider event" reading is gone

**The "clean hour" claim was the basis for characterising this as a discrete provider event** — an
outage with a beginning, which one waits out.

**That basis is gone.** What is actually observed is: every Anthropic call in the entire deployed
record failed, with no observed period of service and no recoverable onset. That is equally consistent
with a standing condition — an exhausted balance, a bad key, a revoked grant — as with an incident.
**The record does not distinguish them (§3), and nothing about the shape of the evidence favours the
transient reading.** Any plan that assumes "wait and retry" is resting on a claim that has been
withdrawn.

---

# 5. OPEN ITEMS — none fixed

1. **Persist the raw provider error alongside the class.** `_classify_failure` receives `error_msg`
   and discards it. Retaining the raw message, or at minimum the HTTP status code, would separate
   credit exhaustion from outage from auth failure. (§3)
2. **Propagate `run_quality` into the job dict.** It is computed correctly and emitted only to the
   job-event stream, so `GET /api/jobs/{job_id}` never carries it. (§2.3)
3. **Mark evaluator substitution on the six presentation surfaces** — web banner, annotated DOCX,
   annotated PDF, summary DOCX, batch DOCX, combined PDF. All six currently key on
   extraction-completeness fields only. This is a *disclosure* question, not a validity one: a
   substituted-panel run is not necessarily wrong, but the reader is entitled to know. (§2)
4. **Stop element records claiming a model that did not serve them.** On an `all_failed` stub,
   `label`, `actual_model`, `actual_label` and `is_fallback` should reflect that no model served the
   call. Whatever the encoding, it must be structured — the truth currently lives only in a free-text
   `reasoning` string. (§1)

**Sequencing note, offered not decided:** item 4 is the prerequisite for trusting any census used to
verify items 2 and 3. Fixing the surfaces while the provenance fields still misreport would produce
disclosures computed from data known to be wrong.

---

# 6. WHAT IS NOT ESTABLISHED

- **The cause of the Anthropic failures.** Unknowable from the record (§3). Not investigated here.
- **Whether the stub encoding affects any earlier measurement.** Only the two Step-487 deployed runs
  were examined. Whether `all_failed` stubs appear in the local runs of Steps 457–484, or in the
  frozen 431/447 artifacts, **was not checked.** It is the obvious next question and this step did not
  ask it.
- **Whether a substituted role A changes verdicts.** 8 of 32 LPs differ between the two runs, but
  *both* ran the substituted panel, so there is no A/B. LP-17 is suggestive — `partial 5/1` on two
  evaluators versus `covered 6/0` on three — but one pair is not evidence of causation.
- **Whether `run_quality` reaching the job dict is intended or was an oversight.** Not determined.
- **Whether any consumer switches on the existing `run_quality` values** and would break on a new one.
  Carried forward unanswered from `486_code_status.md` §B5.
