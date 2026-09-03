# Step 537 — Instruction

**Received:** 2026-09-03, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 537. Run ex6-4 end to end. First real lease with parseable headings.

ex6-4 is the only usable new fixture: 82 headings, all four previously
absent concepts present in genuine non-negated context, clean conversion.

Full-LP Mode C, canonical, through run_mode_c.py. Verify the panel first.

REPORT
  1. Completes or aborts. If it aborts, which LPs — and note that its
     clue matches are TRUE positives, so an abort here means something
     different from everbridge's.
  2. LP-20, LP-21, LP-23, LP-12 specifically. These are the four concepts
     the corpus has never had. Does the panel find them, and does it find
     them for the right reasons? Quote the evidence and the verdicts.
     This is the first test of whether the pipeline handles these at all,
     as opposed to correctly reporting their absence.
  3. Locator resolution rate. 82 headings against Atlas's 89 — first real
     document where the prefix should work. Against Atlas 99%,
     quanterix 0.6%, divall 7.2%.
  4. The four seamed LPs — spans or fallback?
  5. assessment_status distribution.
  6. The qualifier pass. Step 524's patterns are Atlas-derived and found
     nothing on quanterix. A shopping-centre lease words limitations
     differently again.
  7. Read the report as a lawyer would. Substantive or generic?

Item 2 is the point. Everything measured so far is the pipeline being
right or wrong about absence. This is the first document where it has to
be right about presence on these four.

Do NOT tune anything.
