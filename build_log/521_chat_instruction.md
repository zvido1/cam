# Step 521 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 521. The "not assessed" state. DESIGN, then build if the design holds.

requires_attention is a membership test over coverage_state and there is no
state meaning the LP was never assessed. not_applicable, unclear-routed and
short-circuited LPs all emit False, indistinguishable from an LP with
genuinely nothing to report.

PART A — DESIGN, report before building

1. Enumerate every route by which an LP produces a coverage entry the panel
   never judged. Step 469 named not_applicable and unclear-routed; Step 478
   added the applicability short-circuit; Step 496 showed
   default_when_unclear resolving one of them. Report the full set from
   code, not from those summaries — and say whether any produce zero
   element verdicts versus a verdict nobody voted on.

2. Step 470 measured what happens if not_applicable and unclear-routed
   entries carry requires_attention: True — 97% of the report, making the
   flag a restatement of "assessed". Its recommendation was
   assessment_status: "assessed" | "not_assessed" as an ORTHOGONAL field,
   not a third boolean value, because lease_exposure:523 does a truthiness
   test that a third value would break. Confirm that still holds, then
   either adopt it or say why not.

3. requires_attention is a DERIVED field. Where else is coverage_state
   consumed as a proxy for "was this judged"? Step 469 found the type
   argument; report every consumer, because adding a field helps nobody if
   the six presentation surfaces read the old one.

4. What does a reader see? not_assessed must be visibly different from
   "assessed and clean" on all six surfaces from Step 497 — web, both
   annotators, summary generator, batch summary, and the API. Not a new
   banner; the per-LP entry must carry it.

PART B — BUILD, only if A is clean

VERIFY BY EXERCISE. Six consecutive steps have caught defects a static read
missed. Generate a DOCX and PDF from a result containing all three kinds —
assessed-and-clean, assessed-and-missing, not-assessed — and quote what
appears for each. A reader must be able to tell them apart without knowing
the schema.

Do NOT deploy.
