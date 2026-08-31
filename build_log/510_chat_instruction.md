# Step 510 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 510. Make email configuration observable, then decide on C.

PART A
Add email-configuration status to the AUTHENTICATED /api/provider-health
body. Anonymous callers still get `status` only.

Report which branch send_email would take in production — sendgrid,
gmail_api, smtp, or not_configured — using the same predicates the
dispatcher uses, not a reimplementation. Quote both so they are visibly
the same logic.

Send nothing. No new mechanism.

PART B
Push, wait for the rebuild, request it authenticated, and report the
production answer.

That settles whether SendGrid has ever been able to send. It does not
settle whether it HAS sent — say so, and say what would.

PART C — the defect underneath, report only, do not fix
notifications.py returns True when unconfigured; job_manager.py:1683
discards it. Report every call site of send_email and whether each
checks the return value.

Then state what the correct contract is. A function that cannot fail is
indistinguishable from one that always works, and this arc has now met
that shape in SendGrid, in is_fallback: false, in the gate's fail-open,
and in _classify_failure. Propose the fix; do not build it.

Do NOT wire alerting.
