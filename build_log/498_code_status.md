# Step 498 — run_quality reaches the API. The emitter is covered by test, not by the run.

**Date:** 2026-08-30 · **Instruction:** `build_log/498_chat_instruction.md`
**Part A verified against the real endpoint. Part B run completed and left the emitter
UNEXERCISED — reported as such, not as coverage.** Tests **367 passed** (359 + 8 new).
**Not deployed.**

---

# PART A — THE ENDPOINT NOW CARRIES THE VERDICT

## The change

`apply_outcome_to_job()` copies the outcome's scalar verdict onto the job dict, called immediately
after `_append_job_event`:

```python
outcome = _build_job_outcome(job_id, tenants, job.get("started_at"))
_append_job_event(job_id, "job_outcome", **outcome)
# Step 498: and onto the job dict, which is what the API returns.
apply_outcome_to_job(job_id, outcome)
```

**Only seven scalar fields are copied.** `per_tenant` and `totals` stay in the event stream: they are
large, their shape changes, and a status poll does not need them.

## The four responses, verbatim from `GET /api/jobs/{id}`

Exercised through FastAPI's `TestClient` against the real route — **HTTP 200 on all four**, not a
code reading.

```json
=== GET /api/jobs/s498_SUBSTITUTED_487
{
  "run_quality": "degraded",
  "report_incomplete": false,
  "invalid_for_legal_analysis": false,
  "incomplete_statement": null,
  "issue_areas_with_no_evidence": [],
  "panel_substituted": true,
  "panel_fallback_noted": false
}

=== GET /api/jobs/s498_NOTED_496
{
  "run_quality": "degraded",
  "report_incomplete": false,
  "invalid_for_legal_analysis": false,
  "incomplete_statement": null,
  "issue_areas_with_no_evidence": [],
  "panel_substituted": false,
  "panel_fallback_noted": true
}

=== GET /api/jobs/s498_CLEAN_491
{
  "run_quality": "clean",
  "report_incomplete": false,
  "invalid_for_legal_analysis": false,
  "incomplete_statement": null,
  "issue_areas_with_no_evidence": [],
  "panel_substituted": false,
  "panel_fallback_noted": false
}
```

**A fourth case, added because it is Step 491 §4's original complaint** and cost nothing:

```json
=== GET /api/jobs/s498_INCOMPLETE_496divall
{
  "run_quality": "incomplete",
  "report_incomplete": true,
  "invalid_for_legal_analysis": true,
  "incomplete_statement": "INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS. Extraction returned no
    text for 3 required issue area(s): LP-30, LP-31, LP-32. Those areas were assessed with no
    evidence and their findings are unsupported. The rest of this report was produced normally,
    but the document has not been fully analysed.",
  "issue_areas_with_no_evidence": ["LP-30", "LP-31", "LP-32"],
  "panel_substituted": false,
  "panel_fallback_noted": false
}
```

**All four discriminate correctly, and the three degradation kinds stay distinct:** substituted panel
(`degraded` + `panel_substituted`), benign fallback (`degraded` + `panel_fallback_noted`), incomplete
extraction (`incomplete` + `report_incomplete`), clean (`clean`).

**This closes Step 491 §4 and the Step-497 open item.**

---

# PART B — THE RUN, AND WHAT IT DID NOT PROVE

## 2. The run

```
calls=96   elapsed=772.0s   gate_attempts=1   aborts=0   degraded=False
records=606  stubs=0  contradictions=0  fallback_events=0
   role A: {'claude-sonnet-4-6': 202}  fallback=0
   role B: {'gpt-5.5': 202}            fallback=0
   role C: {'grok-4.3': 202}           fallback=0
```

Panel verified before spending: `A 1.76s · B 2.75s · C 1.94s — PANEL INTACT`. **It stayed intact for
all 606 records.**

**Was a stub emitted? No.**

```
element records carrying a `served` key : 0
records with served=False (stubs)       : 0
panel_substitution on result            : None
panel_substituted                       : False
```

**The Step-497 emitting path was NOT exercised by this run**, exactly as the brief anticipated. The
`served` field appears on no record, because it is written only on the stub branch and no evaluator
failed. **This run is evidence the fix does no harm on a clean panel. It is not evidence the fix
works.** Saying otherwise would be the written-versus-wired claim Rule 4 exists to stop.

## 3. HOW THE EMITTER CAN BE EXERCISED — done, and it costs nothing

**A provider outage cannot be scheduled, so a live run cannot be relied on to cover this path.** The
emitter can be driven directly, deterministically, with no network:

`cam/adapters/lease_review/tests/test_497_stub_provenance.py` — **8 tests, 12 subtests, 0.05s, zero
provider calls.** They call `_extract_verdicts_for_element` with the exact dict shape both
failure-path returns produce (`lease_coverage_305.py:696` and `:785`): `model`/`label` taken from
`evaluator_cfg` — the **requested** model — with `completed: False`. That combination is precisely
what used to make a stub claim Anthropic served it.

**Cost: zero, and permanent.** It runs in the normal suite on every future step.

### The tests discriminate — verified, not assumed

A test that passes before and after proves nothing. Replaying the pre-497 emitter verbatim from
`HEAD~1`:

```
PRE-497 stub for role A:
   label          'Claude Sonnet 4.6'
   actual_model   'claude-sonnet-4-6'
   actual_label   'Claude Sonnet 4.6'
   is_fallback    False
   served         <absent>

   actual_model is None    FAIL       served is False        FAIL
   actual_label is None    FAIL       requested_model set    FAIL
   is_fallback is None     FAIL       no model claimed       FAIL

Against the PRE-497 emitter: 6 of 6 assertions FAIL.
```

Three further tests pin the cases that must **not** change: primary service still named, a real
fallback still flagged `is_fallback=True` with its true model (Step 496's benign case), and
`match is None` still treated as service — because there the evaluator *did* serve and merely omitted
one element.

**What remains uncovered:** behaviour under real concurrency during an actual provider failure. That
needs an outage and cannot be scheduled. **The test covers the emitting logic; it does not cover the
conditions that invoke it.**

## 4. SEAM LPs — nothing moved

| LP | 491 ×3 | 494 | 496 | **498** |
|---|---|---|---|---|
| **LP-07** | 5/1, 5 spans ×3 | 5/1, 5 spans | 5/1, 5 spans | **5/1, 5 spans** |
| **LP-16** | 3/2, 388 chars ×3 | 3/2, 388 | 3/2, 388 | **3/2, 388** |
| **LP-17** | 5/1, 5/1, 5/0 — 0 spans | 5/0, 5 spans, 1176 | 5/0, 5 spans, 1176 | **5/0, 5 spans, 1176** |
| **LP-27** | 8/1 (7/9/7 spans) | 8/1, 8 spans | 8/1, 7 spans | **8/1, 9 spans** |
| LP-12 | 1/0, 1/1, 0/0 | 0/1 | 2/0 | **0/0** |

- **LP-16 byte-identical across all six runs** — the C5 clue change (496) still has not perturbed
  Atlas's true positive.
- **LP-17 identical to 494 and 496** on all fields — the seam is stable across three runs.
- **LP-27** found list identical across all six; span count varies 7–9 as before.
- **LP-12 back to 0/0**, inside its now-established 0–2 range on byte-identical evidence.

**One difference worth recording rather than smoothing: LP-07's `tenant_text` is 1,635 chars here
versus 1,957 in all five prior runs**, while its span count (5) and verdict (5/1) are unchanged. The
elicited spans differ in extent without changing what was found. Not investigated.

---

## WHAT IS NOT ESTABLISHED

- **The emitter under a live failure.** Covered by test, not by a run. Unschedulable without an outage.
- **Whether any deployed client reads the new fields.** The API now returns them; nothing has been
  updated to consume them, and `app.js` polls status but renders its banners from the *results*
  payload, not the status payload.
- **Whether adding keys to the job dict breaks a caller** that enumerates or round-trips it. Not
  audited — the same open question Step 486 §B5 raised for `run_quality` values.
- **`panel_substituted` on a real substituted run.** Every verification uses Step-487 stored data;
  no run since has substituted a seat.
- **The threshold between ~0% and ~95% primary service.** Unchanged from Step 497 — still untested.
- **Deployed behaviour.** All local. 12 commits unpushed.
