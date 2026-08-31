# Step 523 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 523. §11.3 — qualifiers the panel cannot see. DESIGN, no build.

THE DEFECT, from Step 460
Section 11.3, Limitation of Liability, sits at offsets 15490-15748:
"Neither party shall be liable to the other for any consequential,
indirect, punitive, or special damages... Landlord's liability shall be
limited to Landlord's interest in the Building and Land."

The evidence handed to the LP-27 panel ends at 15251 — 239 characters
short. The panel reported "monetary damages: explicitly present, high
confidence" without ever seeing the clause that caps the remedy.

This is NOT a bad span. Elicitation retrieves clauses matching an ELEMENT
DESCRIPTION, and no LP-27 element describes a limitation, so the qualifier
is structurally unreachable. Nothing in the output marks its absence.

WHAT IS ALREADY RULED OUT — do not re-propose these
  - Containing-section expansion (Steps 466/467). §11.2's section ends at
    15490 and §11.3 begins at 15490, so it cannot reach it. And it caused a
    measured PRECISION REGRESSION: element 4 moved from a correct "missing"
    to "disputed" because evaluator A, given more of §5.1, was seduced by
    adjacent security-deposit prose. Rolled back.
  - Prompt-level strictness (Step 468). Ruled out as a CLASS: the model
    evaluating the entailment test is the model whose entailment judgment
    is the defect.

THE INFERENCE THAT CONSTRAINS ANY FIX (Step 467)
More context did not improve reasoning — it supplied more topically
adjacent material to be seduced by. Any context-widening direction inherits
this, and must be measured on PRECISION OVER THE PREVIOUSLY-CLEAN ELEMENTS,
not only on whether the qualifier arrives. Element 4 was not the target of
that change and is where the damage landed.

DESIGN QUESTIONS

1. Is co-retrieval of adjacent sections viable, given it is itself a
   context-widening direction and inherits the above? What would it cost
   in precision, and how would you know before spending runs?

2. Is there a direction that does NOT widen the evidence handed to the
   panel? Consider: a separate retrieval pass for limitations and
   carve-outs that is not element-driven, whose output is reported
   ALONGSIDE the finding rather than mixed into the evidence the panel
   judges. That changes what the reader sees without changing what the
   panel reasons over — which is the only lever this arc has not tried.

3. If a qualifier is found but not judged, what does the report say? It
   cannot claim the panel weighed it. Does assessment_status have a role,
   or does this need its own marker?

4. What is the smallest thing that would tell a reader "there is a clause
   near this finding that may limit it, and the panel did not see it"?
   That may be more valuable than making the panel see it.

5. GENERALITY. Atlas puts the cap 239 characters away. A lease can put
   remedy limitations in a miscellaneous article, an exculpation clause, or
   an SNDA. Say whether your proposal depends on proximity, and what it
   does when it does not hold.

Do NOT build. Report the design and your recommendation.
