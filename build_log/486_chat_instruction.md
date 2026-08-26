# Step 486 — Instruction

**Received:** 2026-08-25, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 486. Close the batch summary path, then deploy-readiness check.

PART A
generate_combined_summary_pdf / generate_batch_summary were not exercised
in Step 485. Reached from job_manager:1661 and main.py:2341.

Verify by artefact, as before: generate a batch summary containing at least
one degraded result and one clean result. Report what a reader sees.

The batch case has a requirement the single case does not: it must be
obvious WHICH tenant's report is incomplete, not merely that one of them
is. State how you handled that.

PART B — deploy readiness, report only, change nothing

Steps 476-485 are committed and unpushed. Before any deploy decision:
  1. List every commit that would deploy, and what it changes.
  2. Confirm the flag state that would go live:
     SPAN_EVIDENCE_ENABLED, SPAN_EVIDENCE_LPS,
     SECTION_EXPANDED_SPAN_LPS, ENTAILMENT_TEST_LPS,
     DEGRADABLE_APPLICABILITY, and whatever gates the degrade path.
  3. What behaviour changes for a user, stated plainly:
     - runs that previously failed hard now complete, marked incomplete
     - LP-12 is now assessed rather than declared absent by design
     - LP-07, LP-12, LP-27 source evidence from spans
  4. What is NOT fixed and would ship as-is. Include the LP-27 false
     positives on elements 6 and 7, the §11.3 qualifier-reach problem, and
     anything else outstanding.
  5. Anything you would want measured before shipping that has not been.

Do NOT deploy. Report and stop.
