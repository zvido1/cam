# Step 541 — Instruction

**Received:** 2026-09-03, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 541. Should exports include unfavorable and conditional findings?

export_findings filters on `deviates` — missing or broken_xref only — so
seven LPs on ex6-4 including LP-20 and LP-30 appear in no DOCX or PDF,
despite requires_attention: True.

1. Why was the filter written that way? Report the original intent if it
   is recoverable — a comment, a commit message, a spec.
2. What SHOULD an export contain? A tenant's counsel reading the PDF is
   the audience. covered_unfavorable means the provision exists and
   disfavours the tenant — arguably the most useful thing in the report.
3. Propose the filter and report the volume change. Ex6-4 goes from 6
   findings to 13. State whether that is a better report or a longer one.
4. Verify by artefact. Quote LP-20's and LP-30's entries in the DOCX
   before and after, and the document length.

This changes what every report contains. Report before building.

---

**Accompanying note from Tzvi:** "Point 3 matters. Doubling the findings could
make the report less usable, not more — and 'everything requiring attention
appears' is a defensible rule, but so is 'the export is the short list.' That's
a product decision, not a bug fix."
