# Step 501 — Instruction

**Received:** 2026-08-30 from Tzvi in conversation as "start a diagnostic but I don't want to juggle
too many balls at once", following Code's recommendation to take LP-27 elements 6 and 7 next.
Transcribed to disk before execution per CLAUDE.md Reporting Integrity Rule 7. Scope was set by Code
under that instruction and is recorded here as the brief it will be audited against.

---

Step 501. LP-27 elements 6 and 7. DIAGNOSTIC ONLY.
OFFLINE — no runs, no provider calls, no fix. Persisted data only.

Constraint from Tzvi: keep it to one thread. Two deployed runs (Step 500) are
already in flight and must remain the only spend.

WHAT IS ALREADY RULED OUT — do not re-test
  - Step 466: widening evidence to containing sections made precision WORSE.
  - Step 468: prompt-level entailment strictness ruled out as a CLASS of fix.
    The block was read, quoted, and then used to certify the very inferences
    it was written to block.
  - Steps 469/470: the covered_by_default_law route on an unfilled
    TBD_BY_ATTORNEY_REVIEW placeholder converted a would-be `disputed` into
    `implicitly_present` at high confidence.

THE UNASKED QUESTION
Every prior step examined the EVIDENCE or the PROMPT. Nobody has read the
ELEMENT SPECIFICATION. If the schema's own definition of element 6 is broad
enough that an indemnity clause conforms to it as written, then the panel is
answering the question it was asked and the defect is in the schema, not the
evaluators.

PART A — the element specification
Quote LP-27 elements 6 and 7 verbatim from retail_lease_knowledge.json:
label, description, and every flag governing what may satisfy them
(must_be_explicit, implicit_coverage_acceptable, default_law_covers,
default_law_jurisdiction_dependent, criticality). State plainly whether an
indemnity clause is a conforming answer to element 6 AS WRITTEN, and whether
a general savings clause is a conforming answer to element 7 AS WRITTEN.

PART B — cross-run, cross-fixture census
Elements 6 and 7 across every persisted result now available: the six Atlas
runs (491 x3, 494, 496, 498) and divall (496). Report per-element verdict,
per-evaluator verdicts, and the cited section. Step 484 observed divall's
LP-27 move 8 -> 6 with the two moved elements being exactly these two; that
was never followed up.

REPORT the specification finding, the census, and whether the two together
locate the defect in the schema, the panel, or both. Do NOT implement.
