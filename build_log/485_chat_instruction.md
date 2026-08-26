# Step 485 — Instruction

**Received:** 2026-08-24, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 485. Close the export gap. Prerequisite for deploying 476-484.

Step 477's census found nine user-facing consumers with zero degraded
awareness; it closed two — job_manager and static/app.js. Seven remain:

  main.py
  summary_generator.py
  lease_report_generator.py
  lease_display.py
  lease_docx_annotator.py
  lease_pdf_annotator.py
  index.html

The DOCX and PDF are the priority. A lawyer handed one of those never sees
the web banner, and the file currently carries no incompleteness statement
at all.

FIRST — triage, report before changing anything
For each of the seven: does it present a result to a human, and by what
route? Some may be dead, internal, or superseded by app.js. Say so and skip
them rather than editing files nobody reads. Report the list you intend to
change and the list you are skipping, with the reason for each.

THEN — for each one you do change
Surface REPORT_INCOMPLETE / incomplete_statement /
issue_areas_with_no_evidence BEFORE any findings, not beside or after.
The DOCX and PDF must carry it on page one, not in a footnote or appendix.

VERIFY BY ARTEFACT, NOT BY CODE READING
Generate a DOCX and a PDF from BOTH the Step-476 degraded result and a
clean result. Open each and quote what appears on page one. The degraded
pair must be unmistakable; the clean pair must be byte-comparable to what
they produce today.

Exercise every changed path against a real result. Step 477 caught an
escapeHtml/esc ReferenceError that would have rendered nothing on every
degraded page — a static read would not have found it.

Report what a reader actually sees for each consumer. Do NOT deploy.
