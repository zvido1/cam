# Step 468 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 468. Two items.

PART A — correct the stale line
Docs/CAM_Current_State.md, 08-23 block, item 1B says "Two candidate
directions, neither chosen." Section-boundary expansion is now RULED OUT
(Step 466/467): §11.2's section ends at 15490, §11.3 begins at 15490, so
containing-section expansion cannot reach it — established offline before
spending runs.

Record that co-retrieval of adjacent text is the surviving direction, that
it inherits the context-widening regression, and that any test of it must
measure precision on previously-clean elements rather than only whether the
qualifier arrives. Point at FINDING_context_widening_regression.md.

PART B — operative entailment, LP-27 only. MEASUREMENT.
This changes the panel's INSTRUCTIONS, not its evidence. Untried, and the
Step-466 result is an argument for it: more context made reasoning worse,
so the lever is how the panel reasons over what it has.

In the 305 evaluator prompt, add the entailment test. Wording to convey,
not to copy verbatim — phrase it in the prompt's own register:

  A clause supports an element only if its legal effect entails the element.
  Topic overlap is not enough. The test: if this clause were the only clause
  you had, could you truthfully tell the tenant the lease grants the right
  the element describes, WITHOUT supplying an unstated legal inference?

  Grant, trigger, beneficiary and remedy must align with the element.
  A clause can be highly relevant to the topic and still fail this test.
  Indemnities, waivers, definitions, limitations and general "all remedies"
  language do not satisfy a specific-remedy element unless they create or
  expressly identify that remedy.

Gate it behind its own flag so it applies to LP-27 only and rolls back in
one edit. Do NOT change the evidence, the spans, the locator, or
SPAN_EVIDENCE_LPS. Section expansion stays off.

Two runs, clean panel, verify gpt-5.5 before spending.

THE QUESTIONS
  1. Element 6 (monetary damages on the indemnity) — still
     explicitly_present, or does it move?
  2. Element 7 (specific performance on the savings clause) — same.
  3. THE PRECISION CHECK, per the criterion Step 467 established: do any
     of the previously-clean elements (1, 2, 3, 5, 8, 9, 10) move? A
     stricter test could suppress correct findings as easily as wrong ones.
     Report every element's verdict against the Step-457 baseline.
  4. Element 4 — it was correct at baseline. Does it stay correct?

Report the full 10-element table both runs, with evaluator reasoning for
any element that moves. Do NOT tune the wording to improve the result.
