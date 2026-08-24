# Step 472 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 472. Second-document check. Fixture selection FIRST, then run.

The whole arc is measured on one lease. Atlas parses cleanly, and both the
locator prefix and the resolution check depend on the line-anchored heading
index. Nobody has tested a document where that index struggles, and those
two failures are correlated.

PART A — choose the fixture. Report before running anything.

1. List every lease fixture available, with size and a heading-index parse
   result: how many headings does _build_heading_index find, and what
   fraction of the document is covered by parsed sections?
2. Atreca is excluded unless it completes — it has never finished Mode C
   (308.8s vs the 300s router ceiling on 160,244 chars). Report whether any
   other fixture is over ~100k chars.
3. Recommend one fixture and say why. Prefer a document whose heading style
   DIFFERS from Atlas's "Section N.N." pattern, since that is what stresses
   the index. State what you expect to break.

PART B — run it, once selected.

Full-LP Mode C, canonical, same configuration as Step 468:
  SPAN_EVIDENCE_LPS = {"LP-07","LP-27"}
  SECTION_EXPANDED_SPAN_LPS = set()
  ENTAILMENT_TEST_LPS = {"LP-27"}
Verify gpt-5.5 before spending. Up to four gate attempts.

REPORT
  - did the heading index parse, and did the locator prefix produce real
    section names or fall back
  - what fraction of section_ref values resolve, against Atlas's 99.0%
  - do LP-07 and LP-27 get span evidence at all, and does it contain
    anything element-relevant
  - the extraction completeness gate: does it abort, and on which LPs
  - anything that crashes rather than degrades

Do NOT tune anything to make it work. A fixture that breaks the index is
the finding, not a problem to fix tonight.
