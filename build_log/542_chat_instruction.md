# Step 542 — Instruction

**Received:** 2026-09-03, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 542. Include unfavourable and conditional findings in exports.

export_findings filters on `deviates` — missing or broken_xref only.
Step 541 established this was not a design decision: _extract_deviations
carried five states and export_findings used two, a copy that lost three
with nothing recorded.

Include everything with requires_attention: True. Report the resulting
filter and confirm it derives from the same helper as the summary — one
source, not a seventh duplicated test.

Order matters more at 12 findings than at 6. Propose an ordering and
defend it: deviating first, then unfavourable, then conditional, or by
materiality, or something else. A lawyer reading twelve wants the worst
first.

Verify by artefact on the Step-537 result:
  - LP-20 and LP-30 entries in DOCX and PDF, before and after
  - total findings and document length, before and after
  - confirm the summary top line and the export contents now agree —
    a reader must not see 12 requiring attention and 6 findings

Also confirm not_assessed items are excluded from findings but visible
somewhere, per Step 522. An LP nobody assessed is not a finding, but it
must not vanish.

Do NOT change any panel verdict. Do NOT touch the citation gate.
