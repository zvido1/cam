# Step 511 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 511. Fix the return contract. Then alerting is buildable.

Implement your own proposal from Step 510 Part C:

1. _send_email returns {"sent": bool, "channel": str, "reason": str|None}.
   Never a bare True for nothing done. The four facts a caller may need —
   sent via SendGrid, sent via SMTP after SendGrid failed, not configured,
   provider rejected — must be distinguishable.

2. Do NOT fail the job. The unconfigured True was deliberate so dev
   environments don't break, and that instinct is right. Separate "did the
   job succeed" from "was the notification delivered."

3. job_manager records the outcome on the job — notification_sent,
   notification_channel, notification_reason — surfacing through the
   Step-498 fields on GET /api/jobs/{id}. Same disclosure pattern as
   Step 497: mark the degradation, don't hide it, don't fail the run.

4. main.py:391 distinguishes server misconfiguration from provider
   rejection and says which in the 500.

VERIFY BY EXERCISE, not by code reading
Four consecutive steps have caught defects a static read missed. Drive
_send_email through all four outcomes — configured-and-succeeds,
configured-and-rejected, SendGrid-fails-then-SMTP, and not-configured —
with the transport stubbed so nothing is actually sent. Quote the returned
dict for each.

Then confirm GET /api/jobs/{id} carries the notification fields on a
completed job, exercised through the real route.

Do NOT wire alerting. Do NOT send a real email.
