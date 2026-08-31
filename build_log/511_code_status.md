# Step 511 — The return contract is fixed. All four outcomes are distinguishable.

**Date:** 2026-08-31 · **Instruction:** `build_log/511_chat_instruction.md`
**Tests 369 passed, 3 skipped. Alerting NOT wired. No real email sent. Not deployed.**

---

# 1. `_send_email` RETURNS A RESULT DICT

```python
{"sent": bool, "channel": str, "reason": str | None, "attempts": list}
```

**The unconfigured branch no longer returns `True`:**

```python
    if not email_configured(config) and not sendgrid_configured(config):
        logger.info("Email not configured - logging notification: to=%s subject=%s" % (to_email, subject))
        return {"sent": False, "channel": "none", "reason": "not_configured", "attempts": []}
```

## How the four facts are kept apart

`_send_via_sendgrid` falls back to SMTP **internally**, so the dispatcher cannot infer the real
channel from the branch it chose. The three leaves therefore take an **optional `trace` list** and
append their own outcome. Their bool return contract is unchanged — nothing existing moved.

`channel` is the transport that actually decided the outcome (last trace entry); `attempts` carries
the whole chain.

---

# 2. VERIFIED BY EXERCISE — all four, transports stubbed, nothing sent

```
=== 1. NOT CONFIGURED
   {"sent": false, "channel": "none", "reason": "not_configured"}
   attempts: []

=== 2. CONFIGURED AND SUCCEEDS
   {"sent": true, "channel": "sendgrid", "reason": null}
   attempts: [{"channel": "sendgrid", "ok": true, "reason": null}]

=== 3. CONFIGURED AND REJECTED
   {"sent": false, "channel": "sendgrid", "reason": "provider_rejected: HTTP 403"}
   attempts: [{"channel": "sendgrid", "ok": false, "reason": "provider_rejected: HTTP 403"}]

=== 4. SENDGRID FAILS -> SMTP SUCCEEDS
   {"sent": true, "channel": "smtp", "reason": "fallback_after:sendgrid"}
   attempts: [{"channel": "sendgrid", "ok": false,
               "reason": "provider_error: OSError: simulated SendGrid outage"},
              {"channel": "smtp", "ok": true, "reason": null}]
```

**Case 4 used the REAL `_send_via_sendgrid` leaf** with `urllib.request.urlopen` stubbed to raise, so
the fallback chain is genuinely exercised rather than simulated. **`attempts` shows both hops** —
the fact a bool could never carry.

**Nothing was sent in any case.** Every transport was stubbed.

---

# 3. THE JOB RECORDS IT, AND THE JOB DOES NOT FAIL

`_record_notification(job_id, result)` writes `notification_sent` / `notification_channel` /
`notification_reason` onto the job dict and logs at ERROR when undelivered. **It never raises.**

**Not-configured is not an error — it is a deployment state.** Failing the job over it would break dev
environments, which is exactly why the original returned `True`. The fix is to record it, not to
raise. Same disclosure pattern as Step 497: mark the degradation, do not hide it, do not fail the run.

## Verified through the real route

```
GET /api/jobs/{id}

delivered via sendgrid   {"notification_sent": true,  "notification_channel": "sendgrid", "notification_reason": null}
smtp after sendgrid      {"notification_sent": true,  "notification_channel": "smtp",     "notification_reason": "fallback_after:sendgrid"}
NOT configured           {"notification_sent": false, "notification_channel": "none",     "notification_reason": "not_configured"}
provider rejected        {"notification_sent": false, "notification_channel": "sendgrid", "notification_reason": "provider_rejected: HTTP 403"}
```

And both undelivered cases logged loudly:

```
ERROR [notification] job s511_NOT_configured NOT delivered: channel=none reason=not_configured
ERROR [notification] job s511_provider_rejected NOT delivered: channel=sendgrid reason=provider_rejected: HTTP 403
```

---

# 4. `main.py` DISTINGUISHES MISCONFIGURATION FROM REJECTION

```python
    result = _send_email(email, subject, text)
    if not result.get("sent"):
        reason = result.get("reason") or "send_failed"
        if reason == "not_configured":
            raise HTTPException(500, "Email is not configured on this server, so no message was sent.")
        raise HTTPException(500, "Failed to send email via %s: %s" % (result.get("channel"), reason))
    return {"ok": True, "channel": result.get("channel"), "reason": result.get("reason")}
```

**The guard can now fire on the condition it exists for.** Before, an unconfigured environment
returned `True`, so `ok` was truthy, no 500 was raised, and the caller was told the link was sent when
nothing left the process.

---

## A CHANGE I MADE THAT WAS NOT ASKED FOR, recorded rather than slipped in

The original unconfigured branch logged the **entire email body** to the log:

```python
        logger.info(
            f"Email not configured — logging notification:\n"
            f"  To: {to_email}\n  Subject: {subject}\n  Body:\n{body}"
        )
```

Mine logs **only `to` and `subject`**. A lease-analysis notification body carries tenant names,
property addresses and finding counts, and Railway logs are retained — so this was PII going into a
log store. CLAUDE.md Rule 10 forbids persisting raw content. **I judged this in scope as part of
rewriting the branch, but it is a behaviour change nobody requested and it is on the record.**

## WHAT IS NOT ESTABLISHED

- **Not deployed.** Verified locally against the real route and the real leaf, not in production.
- **No real email was sent in any test.** Every transport was stubbed, so nothing here proves SendGrid
  delivers — only that the four outcomes are now distinguishable when they occur.
- **`notification_*` reaches `GET /api/jobs/{id}` because `_record_notification` writes the job dict
  directly.** It is NOT in `_JOB_QUALITY_FIELDS`, so it does not flow through the Step-498
  `apply_outcome_to_job` path — a different mechanism reaching the same endpoint. Both work; they are
  not unified.
- **Old callers passing the result to a boolean context would now always see truthy**, since a dict is
  always truthy. All three call sites were updated; **any caller added later that treats it as a bool
  would silently regress.** A type annotation change (`-> dict`) is the only guard.
- **Alerting is still not wired**, per instruction — but the prerequisite it was blocked on is now
  closed: an alerting send can no longer report success while failing.
