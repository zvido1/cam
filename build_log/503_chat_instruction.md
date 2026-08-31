# Step 503 — Instruction

**Received:** 2026-08-30, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 503. Verify google-genai 2.20.0 on the real extraction path, then push.

The extractor's full JSON path is untested at 2.x. Five live calls and the
suite are not the same as the schema-validated extraction that feeds
everything downstream — and that is the surface anthropic 1.x broke.

1. One Atlas run, full-LP Mode C, canonical, through run_mode_c.py.
   Verify the panel first.

   Report: does extraction complete, does the schema validate, do all 33
   provisions come back, and does the shape match the Step-498 run? Any
   difference attributable to the SDK rather than to shape variance?

2. If it passes, PUSH. Preflight as before: fetch, unpushed count, list
   deployable commits, confirm the six flags, tests against HEAD, branch
   only, no tags.

   This deploy carries the anthropic pin, the twelve other bounds, the
   drift test and the classifier fix.

3. Then ONE deployed Atlas run.

   THE QUESTION: does role A serve claude-sonnet-4-6? That would be the
   first deployed run in this project's history on the actual frozen panel.

   Report the panel census, panel_substituted, and whether the disclosure
   banner correctly does NOT appear.

If step 1 shows any extraction difference, HALT and report before pushing.
