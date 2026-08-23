# Step 463 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

**Note on numbering:** no Step 462 exists in `build_log/`. Numbering jumps 461 → 463 as instructed;
not queried, recorded here so the gap is not later read as a lost step.

---

Step 463. LP-12 extraction gate. DIAGNOSTIC ONLY — no fix, no deploy.
Side-track engineering; nothing in the patent plan depends on this.

WHAT IS KNOWN
Atlas §13.2 "Termination Right" is located on 6 of 6 extraction-only runs
and stably assigned to LP-24 Damage & Destruction. Whether it is ALSO
cross-filed into LP-12 varies 2 of 6. When it is not, LP-12 has zero
characters, the completeness gate scores fail_missing, and the whole run
aborts. Recall is fine; the second placement is the coin flip.

WHAT IS NOT KNOWN — this is the diagnostic
Why the extractor sometimes cross-files and sometimes does not, given
identical input, the same model, no fallback, and temperature 0.

Using the six persisted runs at build_log/LP12_extraction_runs/, compare
the two cross-filing runs against the four that did not:

1. Does anything ELSE differ between them, beyond LP-12? Compare all 33
   provisions across all six runs. Are the four non-cross-filing runs
   identical to each other? Are the two cross-filing runs identical to each
   other? If the runs cluster cleanly into two shapes, that is a different
   phenomenon from six independent samples.

2. Does LP-24's content differ between the two groups? If §13.2 appears in
   LP-24 identically in all six, the variance is purely in the second
   placement. If LP-24 also varies, the whole assignment is unstable and
   LP-12 is just where it shows.

3. What does the extraction prompt say about a clause serving multiple
   issue areas? Quote it verbatim. Is cross-filing instructed, permitted,
   or unmentioned? If unmentioned, the 2-of-6 is the model choosing
   unprompted, which is a different fix from the model disobeying.

4. Is temperature actually 0 on this call? Quote the config and the
   transmitted parameter. The extractor is gemini-3.1-pro-preview; confirm
   it accepts temperature 0 rather than silently defaulting like gpt-5.5.

Report. Change nothing. Do not attempt a fix.
