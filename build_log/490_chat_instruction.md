# Step 490 — Instruction

**Received:** 2026-08-26, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 490. Persist run results by default. No behaviour change to the
pipeline; harness/runner change only.

Step 489 established that Steps 457-484's runs were never persisted, so
their fallback censuses cannot be re-verified. This is the second time an
unpersisted run has cost an answer — Step 463 recorded the same for five
LP-12 observations.

Make every local run harness write its full result to a dated directory
under build_log/ by default, as the Step-463 and Step-472 probes already
do. Not opt-in.

Report which harnesses exist and which already persist. Do not change the
pipeline, the app, or anything deployed.
