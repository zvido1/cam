# Step 500 — Instruction

**Received:** 2026-08-30, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 500. Deployed verification. Two runs.

Verify the panel through the real router path before spending — Step 487's
deployed runs had role A substituted and nothing said so.

Then one Atlas and one divall through the DEPLOYED app, full-LP Mode C,
canonical, up to four attempts each.

REPORT
  1. Does divall complete deployed? It never has. It completed locally once,
     on attempt 2, and LP-07's shape variance is still a live abort cause.
  2. Atlas seam LPs against the six local runs. LP-07, LP-12, LP-16, LP-17,
     LP-27.
  3. GET /api/jobs/{id} on each — does it carry run_quality,
     panel_substituted, panel_fallback_noted, report_incomplete? First
     deployed exercise of the Step-498 fields.
  4. Panel census per run. If role A is substituted, does the banner now
     appear where Step 487's showed nothing? That is the disclosure fix's
     first real test, and it can only be tested when it fires.
  5. Calls, elapsed, gate attempts.

---

## Deploy state confirmed at the start of execution

Step 499's push was blocked in-session, so this step first verified the deploy actually happened
before spending anything. It had: `origin/main` = `f5a9c8d`, 0 unpushed, and the deployed app serves
the `panel-substitution-banner` markup that exists only post-Step-497.
