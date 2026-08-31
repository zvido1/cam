# Step 514 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 514. Build the manifest-at-boot sdk_change check. Nothing else.

Item 3 from Step 513. This closes the August 26 trigger with no scheduler,
no volume, no persistent state and no provider call.

1. A committed manifest of expected installed versions for all thirteen
   dependencies. Generate it FROM PRODUCTION, not local — Step 507
   established they differ on 6 of 13, and local is the drifted one.
   Use the versions the authenticated /api/provider-health already
   reports. State the file and format.

2. At boot, compare installed against the manifest. Any difference is an
   sdk_change alert. Report both versions and the direction.

   It must fail closed: a missing or unreadable manifest is an alert, not
   a pass. Distinguish "no manifest" from "manifest matches" — that is the
   defect you found in load_state, and it must not be reproduced here.

3. Replace the two-consecutive-checks rule with retry-within-the-run, per
   your own finding. State the retry count and interval and defend them.

4. VERIFY BY EXERCISE, transport stubbed, no email sent:
   - manifest matches installed -> silent
   - one version differs -> ALERT, naming package, expected, installed
   - manifest missing -> ALERT, distinguishable from a match
   - manifest unreadable/corrupt -> ALERT, distinguishable from missing
   Quote each.

5. State plainly what this does NOT cover: model retirement and provider
   outage still need the live check, which still has no caller. Do not
   let a working sdk_change imply the other two are handled.

Do NOT set CAM_ALERT_EMAIL. Do NOT schedule anything. Do NOT deploy.
