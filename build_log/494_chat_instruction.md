# Step 494 — Instruction

**Received:** 2026-08-30, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 494. Seam LP-17. One change, then measure.

LP-17's elicitation succeeds on first try against divall (3 verified spans,
1,056 chars, all element-relevant) and its content is present in the
document. It aborts only because it is not in SPAN_EVIDENCE_LPS.

Add LP-17. Do NOT touch LP-16 — that is an applicability question, not a
seam one, and Step 481 established clue changes need their own measurement.

RUN
  - divall, full-LP Mode C, canonical, through run_mode_c.py. Up to four
    gate attempts. This persists, so the extraction output survives.
  - one Atlas run, same config — LP-17 is now seamed on every document and
    Atlas's five-run baseline must not move.

REPORT
  1. Does divall complete? If it still aborts, on which LPs — LP-16 alone,
     or others?
  2. LP-17's coverage entry on divall: does it get span evidence, what
     verdict, and do the three clauses reach the evaluators?
  3. THE QUESTION STEP 493 COULD NOT ANSWER: from the persisted divall
     extraction, which bucket took LP-17's content, or was it dropped
     entirely? Both are 421C failure modes and they are distinguishable
     now.
  4. Atlas: LP-07, LP-12, LP-27 against the Step-491 runs. LP-17 against
     the same. Anything move?
  5. Panel census per run. Verify the panel before spending.
  6. Cost against the Step-491 baseline.

Do NOT tune. If divall still aborts, that is the finding.
