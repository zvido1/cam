# Step 532 — Instruction

**Received:** 2026-09-03, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 532. Why coverage fails above ~225KB. DIAGNOSTIC, no fix.

Step 531 established: extraction succeeds 9 of 9, coverage fails on
everbridge (294KB) and ncino (230KB), quanterix (224KB) passes. Clean
boundary, no exceptions. Cause unmeasured.

1. Run coverage ONLY on ncino — the smaller failure, 230KB — with the
   extraction result from the Step-529 persisted run. Do not re-extract.

   Report where it fails: which stage, which LP, what error, and how many
   provisions survived to the coverage layer.

2. Is it the same failure on everbridge, or a different one? Run it the
   same way. Two documents failing the same way is a wall; two different
   failures is coincidence at a size that happens to correlate.

3. Quote lease_extract.py:1057 and its message. A document that extracted
   33 of 33 provisions is being told it "may not be a lease" because a
   later stage failed. Report every place that message can be emitted and
   whether any of them can legitimately mean what it says.

4. What survives to coverage? Extraction emitted 33 provisions for both.
   Report how many reach assess_coverage and what happens to the rest —
   if provisions are dropped between stages, that is the finding, not the
   size.

Do NOT fix. Do NOT re-extract. Report where it breaks.
