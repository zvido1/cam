# Step 489 — Instruction

**Received:** 2026-08-26, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 489. Do all_failed stubs appear in the frozen record? READ-ONLY.
No runs, no writes to any frozen artifact, no fix.

Step 488 examined only the two Step-487 deployed runs. The stub shape —
role-level event_type all_failed with actual_model null, while element
records carry actual_model naming the requested model and
is_fallback: false — has not been looked for anywhere else.

Search, oldest first:

1. The FROZEN 431/447 artifacts. 431_selection_measurement_sidecar.json is
   token-bound at e0b985b4 and must not be modified — read only.
   Do any judgments carry an all_failed stub, or element records whose
   is_fallback contradicts a role-level fallback event?

2. Every persisted local run in build_log/ from this arc — the Step
   457/466/468/476/478/482/484 results, and the 463/464 extraction runs.

3. The two Step-487 deployed runs, for completeness.

Report per source: stub count, which roles, which LPs, and whether any
element record's is_fallback contradicts its role-level record.

THE QUESTION THIS ANSWERS: is this defect new, or has it been present
throughout — in which case every fallback census run in this arc, including
the ones that reported clean panels, may have counted stubs as genuine
verdicts.

If the frozen artifacts are affected, say so plainly and do NOT propose a
remedy. That is a patent-record question and it goes to the bound, not to a
fix.

Report. Change nothing.
