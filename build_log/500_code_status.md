# Step 500 — The disclosure fix FIRED on a deployed run. divall failed: deployed does not retry.

**Date:** 2026-08-30 · **Instruction:** `build_log/500_chat_instruction.md`
**Deploy state verified before spending:** `origin/main` = `f5a9c8d`, 0 unpushed, deployed app serves
the post-497 markup. Panel verified intact locally before submitting.
**2 deployed jobs: Atlas COMPLETED, divall FAILED.**

---

# 1. divall — STILL has never completed deployed. The reason is not the fixture.

```
job lease_review_20260830_232700_fd9844   TERMINAL=failed after 221s
error: "Extraction completeness failure: 1 required LP(s) have missing evidence and are not
        classified NOT_APPLICABLE. Failed LPs: ['LP-07']."
```

**Failed on LP-07 — the shape-variant cause — on the first and only attempt.**

**THE FINDING: the deployed app does not retry a gate abort.** The four-attempt allowance is a
property of the local harness (`run_mode_c.py --gate-attempts 4`), **not of the pipeline**. Deployed,
attempt 1 *is* the run.

This resolves the local/deployed discrepancy exactly:

| | attempt 1 | attempt 2 | outcome |
|---|---|---|---|
| **Step 496 local** | abort on LP-07 | completed | **COMPLETES** |
| **Step 500 deployed** | abort on LP-07 | *(never happens)* | **FAILS** |

**Same fixture, same code, same failing LP — different retry policy.** Every local divall completion
in this arc came on a retry, so **none of them predicted the deployed outcome.** LP-16 and LP-17,
fixed at Steps 494/496, did not appear in the failure: **LP-07 is the only remaining cause.**

## 1.1 A second gap: the Step-498 fields are ABSENT on a failed job

```
run_quality                    <ABSENT>
panel_substituted              <ABSENT>
report_incomplete              <ABSENT>
invalid_for_legal_analysis     <ABSENT>
```

`apply_outcome_to_job` is called only on the success path, immediately before `mark_job_completed`.
**A failed job carries `error` and nothing else.** Step 498 verified those fields on completed jobs
and that verification stands — **the failure path was never exercised, and it is blank.** Unfixed.

# 2. Atlas seam LPs vs the six local runs

| LP | deployed 500 | six local runs |
|---|---|---|
| **LP-07** | partial 5/1, 5 spans, **1635** | 5/1, 5 spans; 1957 x5, **1635** on 498 |
| **LP-16** | partial 3/2, 388 chars | **identical on all six** |
| **LP-27** | partial 8/1, 9 spans, 1243 | 8/1 on all six; spans 7-9 |
| LP-12 | review_needed 0/0, 13 spans | 0/0 twice, 1/0, 1/1, 0/1, 2/0 |
| **LP-17** | **covered 6/0**, 5 spans, 1176 | partial 5/0 or 5/1; **never `covered`** |

**LP-16 byte-identical deployed and local — the C5 clue change behaves identically in production.**
LP-07 and LP-27 sit inside their established local ranges.

**LP-17 moved: `covered 6/0` where every local run gave `partial`.** Evidence is identical (5 spans,
1,176 chars — the same as 494/496/498). *[my reading]* **this run had role A substituted by
`gemini-2.5-pro`, so it is not the same panel that produced the six local results** — the one verdict
that moved is on the run where the panel differed. **I am not claiming causation from one run**, and
LP-17 was already at 5/0 in four of six local runs, one element short of `covered`.

# 3. GET /api/jobs/{id} — the Step-498 fields, first deployed exercise

**Completed job:**

```json
{ "run_quality": "degraded", "panel_substituted": true, "panel_fallback_noted": false,
  "report_incomplete": false, "invalid_for_legal_analysis": false,
  "incomplete_statement": null, "issue_areas_with_no_evidence": [] }
```

**All present and correct.** `run_quality: "degraded"` with `panel_substituted: true` — a polling
client now sees what Step 487's runs concealed.

**Failed job: all six absent** (see §1.1).

# 4. PANEL CENSUS — the disclosure fix's first real test, and IT FIRED

```
served:  A {gemini-2.5-pro: 202}   B {gpt-5.5: 202}   C {grok-4.3: 202}
fallback_events: 30 x role=A  claude-sonnet-4-6 -> gemini-2.5-pro  (api_error)
tier='substituted'   minority_roles=['A']   seats_lost=[]
```

**This is Step 487 atlas_2 repeated exactly** — role A substituted on 202 of 202 verdicts by
`gemini-2.5-pro`, 30 `api_error` fallback events. At Step 487 that produced
`invalid_for_legal_analysis=False` and **every surface stayed silent.**

Now, from the deployed result:

```
This document was evaluated by a substituted panel: gemini-2.5-pro stood in on 30 issue area(s).
Evaluator seat(s) A were served mostly by a model other than the one named.
Findings are not invalid, but the evaluator panel is not the one this report names.
```

**A fix that can only be tested when it fires, tested — on its first deployed opportunity.**
`panel_substituted=true` reached the status API; the statement is on the result for all six
disclosure surfaces.

## 4.1 THE PATTERN NOW HAS THREE DEPLOYED DATA POINTS

| environment | runs | role A outcome |
|---|---|---|
| **Local** | 491 x3, 494, 496, 498 — **6 runs** | `claude-sonnet-4-6` served **202/202 every time** |
| **Deployed** | 487 atlas_1, 487 atlas_2, **500** — **3 runs** | Anthropic failed **100%, every time** |

A local panel probe **20 minutes before this run** showed `A anthropic:claude-sonnet-4-6 OK 1.74s`.

*[my reading, flagged as inference, not measurement]* **Six local successes against three deployed
total failures does not look like a provider outage.** It looks like the deployed environment's
Anthropic credential. An invalid or missing key produces HTTP 401, and `_classify_failure` collapses
401 into `api_error` (Step 488 §3), **so the record cannot distinguish it.** This is checkable in the
Railway dashboard, and Step 488 predicted exactly this blind spot.

**If it is the key, every deployed run since 2026-08-26 has been evaluated by a panel with gemini
standing in for Claude — and until this step, silently.**

# 5. COST

| run | calls | elapsed | attempts | outcome |
|---|---|---|---|---|
| Atlas | **98** | 839.9s (844s wall) | 1 | completed, degraded |
| divall | — | 221s | **1 (no retry)** | failed on LP-07 |

Atlas's 98 calls match Step 487's deployed 98 exactly; local runs were 96-99.

---

## WHAT IS NOT ESTABLISHED

- **Why Anthropic fails deployed but not locally.** Hypothesis only (§4.1). Not verified.
- **divall's deployed completion rate.** One attempt, one failure. With no retry, deployed success
  depends entirely on LP-07's extraction draw — measured at 1-in-4 and 1-in-2 locally.
- **Whether LP-17's `covered 6/0` is the substituted panel or run variance.** One run.
- **Whether the banner renders in a browser.** `panel_substituted` reaches the API; nobody has loaded
  the results page.
