# Step 470 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 470. Should covered_by_default_law be presence-tier? DIAGNOSTIC.
No fix, no runs, no schema change.

The finding: a TBD-backed covered_by_default_law vote sits in the presence
tier, so an evaluator that substantively rejects the textual basis records
no dissent. In a system built on preserved disagreement, that is a
mechanism converting dissent into consensus.

Establish, from code and from the four runs:

1. Quote _PRESENCE_TIER and PRESENCE_VERDICTS in full. What is the
   expansion rank of covered_by_default_law relative to
   explicitly_present and implicitly_present, and what does that rank
   determine?

2. What does covered_by_default_law MEAN as distinct from
   implicitly_present? Quote the prompt text defining each for the
   evaluators. Is the distinction "the lease implies it" versus "the lease
   is silent but law supplies it"? If so, the second is a statement about
   law, not about the document — and the element asks about the document.

3. Across the four runs and all 33 LPs: how many merged verdicts would
   change if covered_by_default_law were treated as NON-presence — a
   distinct tier that neither certifies nor dissents, or that counts as
   dissent? Report both variants offline; do not change the code.

4. Does the citation gate apply to covered_by_default_law? A verdict
   resting on background law has no clause to cite. Quote the handling.
   If it is exempt, that is a second route around a deterministic check.

Report. Change nothing.
