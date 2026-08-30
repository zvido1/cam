# Step 499 — Instruction

**Received:** 2026-08-30, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 499. Push. Branch only.

1. Preflight: fetch, report unpushed count, list every commit touching
   "05 Lease Analyzer/" or "cam/". This is a Railway deploy.

2. Confirm the flag state that goes live:
   SPAN_EVIDENCE_ENABLED, SPAN_EVIDENCE_LPS, SECTION_EXPANDED_SPAN_LPS,
   ENTAILMENT_TEST_LPS, GATE_ABORT_RETURNS_DEGRADED,
   DEGRADABLE_APPLICABILITY.
   SPAN_EVIDENCE_LPS should now be LP-07, LP-12, LP-17, LP-27.

3. Confirm 367 tests pass against HEAD, not the working tree.

4. Push branch only. NOT --follow-tags. Both sanction tags stay local.

HALT before pushing if anything in 1-3 is unexpected.
