# Step 515 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 515. Deploy and verify the manifest check.

1. Preflight as before: fetch, unpushed count, deployable commits, six
   flags from HEAD, tests against HEAD, branch only, no tags.

2. Push. Wait for the rebuild.

3. Request /api/provider-health authenticated.

   THE PREDICTION, stated before the result: sdk_change should be SILENT.
   The manifest was generated from this environment. A mismatch means
   something changed between generation and this boot — report which
   package and by how much rather than explaining it away.

4. Report the full body: status, failures, per-model detail, sdk_versions,
   and the email block.

5. State plainly what remains: alerting.run() has no caller,
   CAM_ALERT_EMAIL is unset, and boot-only cadence means a model retired
   between deploys is invisible until the next one.

Do NOT set CAM_ALERT_EMAIL. Do NOT schedule.
