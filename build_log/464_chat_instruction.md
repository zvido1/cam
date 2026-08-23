# Step 464 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 464. Shape structure. DIAGNOSTIC ONLY — no fix, no prompt change.

Three attractors from six calls at temperature 0, byte-identical within
each shape. Two questions.

1. IS THE SHAPE SET STABLE OR IS THE SAMPLE TOO SMALL?
   Six more extraction-only Atlas runs, same harness, persisted.
   Do they fall into shapes A, B and C, or do new shapes appear?
   Report the shape distribution across all twelve.

   If no new shapes appear in twelve, the attractor set is small and
   enumerable, which makes this tractable. If run 13 produces shape D,
   it is continuous variance that happens to cluster and the fix is
   different.

2. DOES PINNING DECODING COLLAPSE IT?
   Separately, six runs with top_p and top_k pinned to greedy values in
   addition to temperature 0. Do not change the prompt.
   Report the shape distribution.

   Temperature 0 requests greedy decoding; top_p and top_k are currently
   unpinned and no seed is set. If pinning collapses twelve runs to one
   shape, this is a decoding-configuration defect, not a semantic one, and
   the fix is a config line rather than a prompt.

Report both distributions. Do not change the deployed configuration, do not
edit the prompt, do not attempt a fix.
