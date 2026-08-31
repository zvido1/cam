# Step 513 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 513. Make the alerting able to fire. Design first, no build.

Two of three triggers cannot fire in production because Railway storage is
ephemeral and the startup assertion runs once per boot. The trigger that
would have caught August 26 — sdk_change — is the one structurally blocked.

Report a design for each, then stop:

1. STATE PERSISTENCE. Where does prior state live so it survives a
   redeploy? Options include a Railway volume (none configured — report
   what configuring one costs), an external store, or committing the state
   to the repo. State the trade for each, including what happens if the
   store is unavailable — it must fail closed, not silently reset.

2. PERIODIC EXECUTION. Something must call alerting.run() more than once
   per boot. Report the options and their real cost at a DAILY cadence,
   not a five-minute one: 7 models, one call each. Step 505 rejected a
   scheduler against a live-calling endpoint at 1,728 calls/day; at daily
   cadence that argument does not apply and I want it re-examined rather
   than inherited.

   Consider: Railway cron, an external scheduler hitting the authenticated
   endpoint, a Windows scheduled task locally, or GitHub Actions.
   State which environment each observes — Step 505 established the local
   model check answers API health, not deployment health, and that
   distinction still holds.

3. sdk_change SPECIFICALLY. It does not need a live call at all — it
   compares installed versions between deploys. Is there a cheaper home
   for it than the health check? A build-time or boot-time comparison
   against a committed manifest would need no scheduler and no live call.
   Report whether that is viable.

4. CAM_ALERT_EMAIL is unset everywhere. State what setting it requires and
   in which environments.

Do NOT build. Do NOT deploy. Report the design and your recommendation.
