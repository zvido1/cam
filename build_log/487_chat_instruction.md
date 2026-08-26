# Step 487 — Instruction

**Received:** 2026-08-25, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 487. Deploy, then measure. Push first, measure second.

1. Preflight: fetch, unpushed count, list every commit touching
   "05 Lease Analyzer/" or "cam/". Confirm the six flag values that go live.
   HALT if anything unexpected.

2. Push branch only. NOT --follow-tags. Both sanction tags stay local.

3. Wait for the Railway deploy, then confirm the deployed SHA if
   observable. If it is not observable, say so — Step 475 established
   GIT_SHA is startup-log only.

4. THEN MEASURE. Six deployed Atlas runs, full-LP Mode C, canonical.
   Six, not one — the point is a rate, not a completion.

   Report:
     - completions vs aborts, and on which LPs
     - LP-12's coverage entry on each completion
     - LP-07 and LP-27 against the local Step-484 runs
     - whether any run comes back DEGRADED, and if so what the job status
       and the report say
     - role B model and fallback census
     - calls and elapsed per run

5. Then ONE deployed divall run. It has never completed deployed.

Do NOT tune anything. If the deployed behaviour differs from local, that is
the finding.

---

## AMENDMENT — received 2026-08-26, verbatim, transcribed before execution

Context: the six-run measurement was stopped mid-flight for spend after the user
raised a credit constraint. This amendment converts the remainder of Step 487
into a write-only record of what was actually measured.

Step 487 record. Write-only, no spend.

Record both deployed runs in build_log/487_code_status.md:

  atlas_1  completed, 98 calls, 944s, clean panel (gpt-5.5 202/202),
           degraded False
  atlas_2  completed, 98 calls, 902s, run_degraded TRUE,
           degraded_reason evaluator_fallback

  Both non-aborts. Seamed LPs match between them and match local Step 484:
  LP-07 5/1 with 5 spans; LP-12 13 spans, 2,605 chars, §13.2 present,
  applicable, requires_attention True; LP-27 8/1.

Record what this establishes and what it does not:

  ESTABLISHED — the 476-486 code executes correctly deployed. Step 475's
  four attempts produced zero completions; this is the first. The seam, the
  seam-aware gate and the LP-12 applicability fix all work in production
  and match local exactly.

  NOT ESTABLISHED — the abort rate. Two completions is not a rate, and the
  six-run measurement was stopped for spend. Three more Atlas runs (~290
  calls) would give one with a wider interval. Divall has never completed
  deployed.

  atlas_2 was cancelled but the cancel arrived after completion — record
  that so a "cancelled" job status is not later misread as a deployed
  failure.

THE PROVIDER FINDING, recorded as its own item:

  30 of 30 role-A calls hard-failed to Anthropic with same-provider retry
  also failing, from 04:04 UTC, falling back to gemini-2.5-pro. Atlas_1 an
  hour earlier was clean. Provider-level, not sporadic.

  _classify_failure at lease_coverage_305.py:161 collapses timeout, 429,
  401 and 5xx into api_error and persists only the class, not the raw
  message. So the record cannot distinguish credit exhaustion from an
  outage from auth failure. Same shape as the reasoning_exhaustion naming
  defect in Step 449 — a label asserting a cause the classifier does not
  observe.

  CONSEQUENCE: a degraded panel COMPLETES and produces a report. If the
  cause is credit, further runs degrade silently rather than failing
  loudly, and the only signal is the fallback census. Record that the
  frozen-panel claim does not hold on a run where role A is served by a
  substituted model.

  Record as an open item, not a fix: persist the raw provider error
  alongside the class.

Commit. Do not push. No runs.
