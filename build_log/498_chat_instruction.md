# Step 498 — Instruction

**Received:** 2026-08-30, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 498. Two closures. No new features.

PART A — make run_quality reach the API
Step 491 §4 and Step 497 both end at the same wall: run_quality,
panel_substituted and panel_fallback_noted are computed in
_build_job_outcome but go to _append_job_event, not the job dict, so
GET /api/jobs/{id} never carries them. A polling client sees nothing.

Propagate them into the job dict. Report what the endpoint returns for:
  - a Step-487 result (substituted)
  - the Step-496 Atlas result (noted)
  - a Step-491 result (clean)
Quote the actual JSON, not the code.

PART B — observe Part A's fix emitting, not inferring it
No run has executed with the served/is_fallback change. Run one Atlas
through run_mode_c.py, full-LP, canonical. Verify the panel first.

If the panel is intact the whole way, no stub will be produced and the fix
will be unexercised — say so rather than claiming coverage. In that case
report whether a stub can be produced deterministically without a provider
outage: a forced-failure path, a test double, anything that exercises the
emitting code rather than the rule applied to stored data.

REPORT
  1. The three API responses from Part A, verbatim.
  2. The run: panel census, calls, elapsed, aborts, and whether any stub
     was emitted.
  3. If no stub: how the emitting path can be exercised, and what it costs.
  4. Seam LPs against Step 491/496. Nothing should move.

Do NOT deploy. Report and stop.
