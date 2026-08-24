# Step 469 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 469. Two items. No runs on item 2 unless the check says otherwise.

PART A — the TBD escape hatch. DIAGNOSTIC, no fix.

  1. How many elements across the whole schema carry
     default_law_covers = "jurisdiction-dependent" with
     applies_in containing TBD_BY_ATTORNEY_REVIEW or any other unfilled
     placeholder? List them by LP and element.
  2. How many carry default_law_covers truthy but genuinely populated?
  3. Quote _normalize_verdict's handling. Does it check the VALUE of
     default_law_covers, or only truthiness?
  4. Is covered_by_default_law in PRESENCE_VERDICTS? Quote it.
  5. In the two Step-468 runs and the Step-457 baseline, how many
     covered_by_default_law verdicts were returned across ALL 33 LPs, and
     how many rest on a TBD placeholder?

  The question this answers: is this LP-27 element 7 only, or is there a
  population of elements across the schema that can be certified present on
  an unfilled placeholder?

PART B — record Step 468's result.

  Its own finding file. Record:
  - the full 10-element table, both runs against baseline
  - precision check PASSES: 1,2,3,5,8,9,10 identical, no suppression,
    zero citation_required_but_absent. First intervention in the arc with
    no measured cost.
  - elements 6 and 7 UNCHANGED
  - THE MECHANISM, as the headline: an instruction to check entailment is
    evaluated by the same model whose entailment judgment is the defect.
    Quote B on element 6 using the block's own framing to justify the false
    positive, and C invoking the test by name to reach the opposite
    conclusion on element 7.
  - B's route-around on element 7: correctly rejected the savings clause,
    then returned covered_by_default_law, which is presence-tier, so the
    merge is unchanged.
  - element 4 correct, credited to the expansion rollback not this change
  - flag left ON at zero cost, rollback ENTAILMENT_TEST_LPS = set()

  State plainly what this rules out: prompt-level strictness as a class of
  fix for entailment errors.

Commit. Do not push. Do not deploy.
