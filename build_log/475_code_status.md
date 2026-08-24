# Step 475 — Deployed Atlas run: four attempts, four gate aborts, no comparison

**Date:** 2026-08-24 · **Instruction:** Step "474" in conversation.
**NUMBERING:** commit `740cb9b` is labelled `474:` — that is the **preflight Docs commit**, which I
numbered on my own initiative before this step was assigned 474. To avoid renumbering a pushed commit,
this step's artifacts are **475**. The gap is bookkeeping, not a lost step.

**MEASUREMENT.** Nothing tuned. Deployed app at `cam-production-5cc0.up.railway.app`, running the
pushed `740cb9b`.

---

## Headline

**The deployed app failed all four attempts on the Atlas fixture. Every one aborted on LP-12.
Questions 2 through 6 are UNANSWERABLE from this step — there is no completed deployed run to
compare.**

That is the result, not a setback to be worked around.

## FIRST — what the deployed payload carries: no bounding needed

Established from code before running, and it holds regardless of the failures:

- `/api/jobs/{id}/results` returns the persisted result file **verbatim**, with no field selection
  ([main.py:386](../05%20Lease%20Analyzer/app/main.py)).
- That file is written by an **unfiltered** `json.dump(result, f, ...)`
  ([lease_adapter.py:1906](../cam/adapters/lease_review/lease_adapter.py)).
- The deployed app calls **`run_lease_coverage_only`** at
  [job_manager.py:1404](../05%20Lease%20Analyzer/app/job_manager.py) — **the identical function the
  Step-468 local runs called.**

So per-evaluator raw verdicts and reasoning, merge `reason`, `span_evidence_records` (added in
`7169221`), and the assembled `tenant_text` are **all present** in the deployed payload. Nothing about
the payload bounds the comparison. **What bounds it is that no run completed.**

## 1. Did it complete? No — 0 of 4

| attempt | job id | started → completed | elapsed | outcome |
|---|---|---|---|---|
| 1 | `…194135_88f745` | 19:41:35 → 19:43:20 | 105s | **failed — LP-12** |
| 2 | `…194410_7112e7` | 19:44:10 → 19:45:55 | 105s | **failed — LP-12** |
| 3 | `…194615_c0b32e` | 19:46:15 → 19:48:00 | 105s | **failed — LP-12** |
| 4 | `…194820_171147` | 19:48:20 → 19:50:07 | 107s | **failed — LP-12** |

Identical error every time:

```
GATE_ABORT: Extraction completeness failure: 1 required LP(s) have missing evidence and are not
classified NOT_APPLICABLE. Failed LPs: ['LP-12']. Cannot produce a valid legal analysis report from
incomplete evidence. Detail: [{'provision_id': 'LP-12', 'tenant_text_len': 0,
'extraction_status': 'AMBIGUOUS', ...
```

**Calls and elapsed for a coverage run: not measurable.** The gate fires before coverage, so no
`api_calls_total` or `elapsed_sec` was produced. 105s is extraction plus gate — consistent with local
timings and **well inside the 300s ceiling**. Nothing timed out; nothing crashed.

## THE DEPLOYMENT FINDING — production does not retry

**This is the one thing this step establishes that local runs structurally could not.**

My local harnesses retried up to four times *inside a single invocation*. **The deployed app has no
retry: one gate abort ends the job**, and the user receives `status: failed` carrying the raw internal
message, including the Python-dict `Detail:` fragment.

So on the fixture this entire arc is built on, **a gate abort is a hard user-facing failure**, not a
recoverable hiccup. "Up to four gate attempts" had to be executed as four separate job submissions.

## Is the deployed app aborting MORE than local? Not established — and I will not claim it

Local Atlas pipeline attempts across this arc:

| step | completions / attempts |
|---|---|
| 457 | 2 / 6 |
| 466 | 2 / 5 |
| 468 | 2 / 4 |
| **local total** | **6 / 15 ≈ 40%** |
| **deployed (this step)** | **0 / 4** |

Under the local rate, P(0 completions in 4 attempts) = 0.6⁴ ≈ **13%** — uncommon but unremarkable.
**Four failures do not distinguish "the deployed app is worse" from "the known abort rate, sampled
badly."** Anyone reading this should not treat the deployment as newly broken on that evidence.

What *is* established is the **user-facing consequence**: at a ~40% completion rate with no retry,
roughly three in five production runs on this fixture end in a hard failure.

## 2–6. Unanswerable

- **2. LP-07 flip / `22.4` presence** — no coverage output. **NOT MEASURED.**
- **3. LP-27 ten-element table vs e1/e2** — no coverage output. **NOT MEASURED.**
- **4. Locator resolution rate** — the locator runs inside `assess_coverage`, downstream of the gate.
  **NOT MEASURED.**
- **5. Role-B model and fallback census** — 305 evaluators never ran. **NOT MEASURED.**
- **6. Moved set vs the 7-of-32 noise floor** — no LP verdicts. **NOT MEASURED.**

**The narrow question — "does the deployed app behave as the local runs did?" — is answered only for
the stages that ran.** Extraction and the completeness gate behave identically: same LP, same status,
same timing envelope. **Everything downstream of the gate is untested in production.**

## What this does establish

1. The deployed app is up, accepts Mode C `analyze` with `perspective=tenant`, and reaches extraction
   on the pushed `740cb9b`.
2. Extraction and the gate behave as locally — LP-12, `tenant_text_len: 0`, `AMBIGUOUS`, ~105s.
3. **Production has no gate retry**, so aborts are hard failures with raw internal error text.
4. **The seam, the locator prefix and the entailment test are deployed but have never executed in
   production.** They sit downstream of a gate that rejected every attempt.

Point 4 is worth sitting with: `134998b`, `7169221` and `bd4e20a` are live, and **not one of them has
run against a real request.** That is the same written-versus-wired shape recorded in
`FINDING_evidence_architecture_unwired.md` — this time not because nothing calls the code, but because
an upstream gate never lets execution reach it.

## What is NOT established

- Whether the deployed app would reproduce the local LP-07 flip or the LP-27 table. Untested.
- Whether the deployed abort rate differs from local. Four samples; not distinguishable.
- Whether some *other* fixture completes in production. Only Atlas was attempted.
- Whether the raw `Detail:` dict in the user-facing error is intended. Observed, not judged.
