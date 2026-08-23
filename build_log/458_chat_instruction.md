# Step 458 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 458. Commit the span seam. No new runs, no code changes, no deploy.

The seam has 141 uncommitted insertions in lease_coverage.py and has now
been measured across five runs. Leaving working code uncommitted through
another session is how it becomes undiffable.

1. Report the full diff before committing. Every hunk accounted for by
   something known: the seam assembly, the Step-455 locator machinery
   (_HEADING_RE, _build_heading_index, _locator_for_offset, the [<locator>]
   prefix), the SPAN_EVIDENCE flag and LP set, the all_lp_texts update, the
   fallback path. Any hunk you cannot account for is a HALT.

2. Confirm the flag state being committed:
     SPAN_EVIDENCE_ENABLED  = ?
     SPAN_EVIDENCE_LPS      = ?
   Commit it as-is and STATE the value. Do not change it to look tidier —
   what shipped in the measured runs is what should be in the commit.

3. The two failing layering tests. Report which they are and exactly what
   they assert. Then state, without fixing them: are they failing because
   the seam violates the layering rule, or because the rule was written on
   the assumption the 423 stack would stay unwired? Do not change either
   the tests or the seam — this is a decision for later and it needs the
   distinction stated correctly now.

4. Commit message must record:
   - the seam wires 423C element-guided span elicitation into
     lease_coverage.py as the evidence source for the LPs in
     SPAN_EVIDENCE_LPS; all others keep the extraction-bucket path
   - Step-455 locator prefix derives a section reference deterministically
     from each verified span's canonical offsets
   - measured result: LP-07's false "proportionate share calculation
     method is defined" finding flipped to elements_found and held 3/3;
     LP-27 went 0/1 found with 8 elements suppressed as
     citation_required_but_absent, to 8/1 found with zero such suppressions
     across 2 clean-panel runs
   - LP-07's evaluators now cite 'Section 1.2' unanimously — the supplied
     locator — where five prior runs produced None, 'Paragraph 1',
     'Para. 1', 'Proportionate Share definition'
   - 81 of 82 non-null citations match a supplied locator; the exception is
     a cross-LP reference on the one element with no supporting span
   - NOT deployed, NOT extended beyond the LP set, two layering tests
     failing by design pending a decision
   - the precision question is UNASKED: whether the spans are the RIGHT
     evidence for those elements is not established

Commit. Do NOT push. Do NOT deploy. Report the commit SHA and the
committed flag values.
