# Step 539 — Instruction

**Received:** 2026-09-03, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 539. What should the summary assert? DESIGN, then build.

Step 538 established there is no categorisation logic. `covered` is
total minus deviating, computed independently at six sites, where
deviating counts only missing and broken_xref. Everything else is residue.

1. Enumerate every coverage_state and say, for each, what a reader should
   conclude. Not which bucket it belongs to — what it MEANS. Then propose
   the smallest set of top-line categories that carries those meanings
   without collapsing distinctions a reader needs.

   LP-20 (0 of 7 elements, suppressed) and LP-30 (covered_unfavorable,
   invisible in the DOCX) are the two cases the current scheme handles
   worst. Any proposal must handle both.

2. assessment_status already exists and is orthogonal. Does the summary
   need to reflect it — an LP nobody assessed is not covered and not
   deviating either. Say whether it belongs in the top line or beside it.

3. ONE shared helper, six call sites. Report every site and confirm none
   computes its own variant afterward. Step 538 found six duplicated
   formulas; the fix is worthless if a seventh appears.

4. LP-30's absence from the DOCX is a separate defect from the arithmetic.
   Report why it is excluded and whether the fix in 1-3 resolves it or
   whether it needs its own change.

5. Verify by artefact on the Step-537 result. Quote the top line and
   LP-20's and LP-30's entries, before and after, on DOCX and PDF.

Do NOT change any panel verdict. Do NOT touch the citation gate — the
suppression is a real defect and its own step.
