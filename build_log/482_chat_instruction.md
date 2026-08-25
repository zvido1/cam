# Step 482 — Instruction

**Received:** 2026-08-24, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 482. Verify LP-12 end to end. RUNS ONLY — no fix, no schema change.

Part A flipped LP-12 to applicable on 10/10 real leases, measured offline
against is_applicable() alone. What an applicable LP-12 produces
downstream is unverified — it has never been assessed by the evaluators on
either fixture.

Two full-LP Mode C runs, canonical, same config as Step 478:
  SPAN_EVIDENCE_LPS = {"LP-07","LP-27"}
  SECTION_EXPANDED_SPAN_LPS = set()
  ENTAILMENT_TEST_LPS = {"LP-27"}
One Atlas, one divall. Verify gpt-5.5 before spending.

REPORT for each:

1. LP-12's coverage entry. It previously read not_applicable /
   requires_attention False / "absent by design" on both. What now?
   Coverage state, materiality, confidence, elements found/missing, and
   the evidence cited.

2. Does it find the right clauses? Atlas §13.2/§13.3; divall Total
   Destruction and condemnation. Quote what the evaluators cited and
   whether it resolves.

3. THE GATE. LP-12 is the LP that aborted Atlas ~60% of the time. Now that
   applicability says applicable, an empty extraction on LP-12 is no longer
   degradable — it must ABORT. Did it? Report gate behaviour and how many
   attempts each run took.

   This is the trade: the false all-clear is fixed, and the abort rate may
   go UP because LP-12 can no longer be waved through as not_applicable.
   Measure it, do not soften it.

4. Did anything else move? Compare against Step 478's runs for both
   fixtures. LP-12 flipping applicable changes the LP set the panel
   assesses; report any knock-on.

Do NOT tune. Report whichever way it lands.
