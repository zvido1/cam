# Step 488 — Instruction

**Received:** 2026-08-26, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 488. Record the provenance defect. Write-only, no runs, no fix.

Own finding file.

1. THE MISLABELLING. Quote atlas_1 LP-17's role-A LP-level record
   (all_failed, actual_model null) beside its six element records
   (actual_model claude-sonnet-4-6, is_fallback False, reasoning
   "Evaluator A did not complete"). Six verdicts produced by no model,
   labelled with the model that did not produce them. Record that it
   defeated a census run against the same data.

2. THE SILENT PATH, traced not inferred. app.js:18740 and
   lease_display.py:378-381 key on invalid_for_legal_analysis /
   extraction_completeness_failed, both False on an evaluator-fallback run.
   run_quality is computed but goes to _append_job_event, not the job dict,
   so GET /api/jobs/{id} never carries it — confirmed on both jobs.
   State plainly: the 476-486 degraded-marker work covers EXTRACTION
   failures only. Evaluator substitution is unmarked on every surface.

3. THE DIAGNOSTIC GAP. _classify_failure at lease_coverage_305.py:161
   collapses timeout, 429, 401 and 5xx into api_error and persists only the
   class. Credit exhaustion, outage and auth failure are indistinguishable
   in the record. Same shape as the reasoning_exhaustion defect in
   Step 449.

4. CORRECTIONS TO THE RECORD, attributed. Chat asserted three facts that
   the stored results falsify: that atlas_1 had a clean panel (it did not —
   role A substituted on 196 of 202 verdicts); that there was a clean
   window an hour earlier (there was none observed); and that the failure
   began at 04:04 UTC (all 30 events share one assembly-time timestamp; no
   onset is recoverable). Record that the "clean hour" claim was the basis
   for calling this a discrete provider event, and that basis is gone.

5. OPEN ITEMS, none fixed: persist the raw provider error alongside the
   class; propagate run_quality into the job dict; mark evaluator
   substitution on the six presentation surfaces; and stop element records
   claiming a model that did not serve them.

THEN update Docs/Patent_Current_State.md, as a BOUND not a retraction:
  Any measurement from a run whose panel was substituted is not a
  measurement of the frozen three-model panel. Both deployed runs of
  Step 487 had role A served by gemini-2.5-pro. Agreement observed on a
  substituted panel is not panel agreement, and nothing in the output
  discloses the substitution. This does not alter frozen L1 measurements;
  it bounds how any future deployed measurement is read.

Commit. Do not push.
