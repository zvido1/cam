# Step 510 — SendGrid IS configured in production. It can send; whether it has, still unknown.

**Date:** 2026-08-31 · **Instruction:** `build_log/510_chat_instruction.md`
**Tests 369 passed, 3 skipped. Pushed `b983b6e..dad0662`. Alerting NOT wired. Part C NOT fixed.**

---

# PART A — THE SAME PREDICATES, NOT A REIMPLEMENTATION

## The dispatcher, verbatim (`notifications.py:325-338`)

```python
    if not email_configured(config) and not sendgrid_configured(config):
        logger.info(f"Email not configured — logging notification:\n...")
        return True

    if sendgrid_configured(config):
        return _send_via_sendgrid(to_email, subject, body, html, attachments, config)

    if gmail_api_configured(config):
        return _send_via_gmail_api(to_email, subject, body, html, attachments, config)

    return _send_via_smtp(to_email, subject, body, html, attachments, config)
```

## The health endpoint, verbatim

```python
        from app.config import email_configured, gmail_api_configured, sendgrid_configured
        _cfg = get_config()
        if not email_configured(_cfg) and not sendgrid_configured(_cfg):
            _branch = "not_configured"      # dispatcher logs and returns True
        elif sendgrid_configured(_cfg):
            _branch = "sendgrid"
        elif gmail_api_configured(_cfg):
            _branch = "gmail_api"
        else:
            _branch = "smtp"
```

**Same three predicates, imported from `app.config` — the identical objects the dispatcher calls — in
the dispatcher's own order.** Nothing is reimplemented, so this cannot drift from real behaviour.
**Sends nothing; reads config only.**

Anonymous callers are unchanged: verified by request, `keys: ['status']`.

---

# PART B — THE PRODUCTION ANSWER

```json
GET /api/provider-health (authenticated) -> HTTP 200
provider status: 'healthy'   failures: []

"email": {
  "branch": "sendgrid",
  "can_send": true,
  "sendgrid_configured": true,
  "gmail_api_configured": false,
  "email_configured": false,
  "sendgrid_from_email_set": true
}
```

**SendGrid is configured in production, with a from-address set.**

**What this settles:** the `not_configured` branch — the one that logs and `return True`s without
sending — **is not the branch production takes.** Notifications have been *attempted* through
SendGrid, not silently swallowed at `notifications.py:330`. That was the live worry from Step 504 §A.3
and it is now ruled out.

**`sendgrid_from_email_set: true` matters too.** Unset, `_send_via_sendgrid` falls back to
`NOTIFICATION_FROM` or the hardcoded `noreply@vered.ai` (`:354`), and an unverified sender is a
standard SendGrid 403. That failure mode is also ruled out.

**A note on the local reading, because it was misleading:** locally the block reports `branch:
sendgrid` too — **but only because my test harness's `bootstrap_env()` injects `SENDGRID_API_KEY` from
the DoubleCheck keys file, which the app itself does not load** (`05 Lease Analyzer/.env` carries only
`SMTP_*`). Production also differs on `email_configured`: **false** there, **true** locally. The local
answer was contaminated by the probe and is not evidence about production.

## What this does NOT settle, and what would

**It does not settle whether SendGrid has ever actually delivered a message.** `can_send: true` means
a real send would be *attempted*. It says nothing about whether the API accepted it, whether the
sender is verified at SendGrid's end, or whether anything arrived.

**Three things would settle it, in ascending cost:**

1. **The Railway log.** `_send_via_sendgrid` logs `SendGrid: sent to {to} — HTTP {status}` on
   success (`:404`) and `SendGrid failed to {to}: {e} — falling back to SMTP` on failure (`:408`).
   `railway logs | grep "SendGrid:"` answers it outright. **Blocked for me** — expired CLI token.
2. **The SendGrid dashboard's Activity Feed**, which lists every message and its delivery state.
   Also outside what I can reach.
3. **A test send.** That emails a real person — an outward-facing action I am not taking unasked.

---

# PART C — THE DEFECT, REPORTED NOT FIXED

## Every call site

| site | captures the return? |
|---|---|
| `job_manager.py:1645` — job **failed** email | **NO — discarded** |
| `job_manager.py:1683` — job **complete** email | **NO — discarded** |
| `main.py:391` — `/api/send-results-link` | **YES** — `ok = _send_email(...)`, raises 500 if falsy |
| `notifications.py:296`, `:312` | internal pass-throughs, return upward |

**Two of three external call sites discard it. One checks it.**

## And the one that checks it cannot detect the failure it checks for

```python
main.py:391    ok = _send_email(email, subject, text)
               if not ok:
                   raise HTTPException(status_code=500, detail="Failed to send email")
```

On an unconfigured environment `_send_email` returns `True` at line 330. **So `ok` is `True`, no 500
is raised, and the caller is told the link was sent when nothing left the process.** The check is
defeated by the lie one layer beneath it. **A guard that cannot observe the condition it guards
against is not a guard.**

## Every leaf CAN express failure. Only the dispatcher cannot.

```
_send_via_smtp       success -> True    failure -> False           <- honest
_send_via_sendgrid   success -> status in (200, 202)               <- honest
                     exception -> falls back to SMTP, returns its result
_send_via_gmail_api  exception -> falls back to SMTP, returns its result
_send_email          NOT CONFIGURED -> True                        <- THE DEFECT
```

## The contract, and the shape this arc keeps meeting

Four instances of one rule, violated four ways:

| where | the lie |
|---|---|
| `notifications.py:330` | `True` when nothing was sent |
| `lease_coverage_305` stub (Step 497) | `is_fallback: False` on a record no model produced |
| `_classify_failure` (Step 502) | `api_error` on a call that never left the process |
| `lease_gate` fail-open (Step 508) | `is_lease: True` when the classifier did not run |

> **A function must be able to express "I did not do the thing." Where it cannot, the absence of
> failure is not evidence of success.**

`startup_health`'s `unknown` default is the **correct** instance of the same shape: no result reads as
unhealthy, not healthy. It is the counter-example that shows the rule is implementable.

## Proposed fix — NOT built

1. **`_send_email` returns a structured result, never a bare `True` for nothing done.** A bool cannot
   distinguish *sent via SendGrid*, *sent via SMTP after SendGrid failed*, *not configured*, and
   *provider rejected* — four facts a caller may need. Shape:
   `{"sent": bool, "channel": str, "reason": str | None}`.
2. **Do not fail the job.** The unconfigured `True` was presumably deliberate so a dev environment
   without email does not break job completion, and **that instinct is right.** The resolution is to
   separate *"did the job succeed"* from *"was the notification delivered."*
3. **`job_manager` records the outcome on the job** — `notification_sent` / `notification_channel` /
   `notification_reason` — surfacing through the Step-498 fields on `GET /api/jobs/{id}`. **Exactly
   the Step-497 disclosure pattern: mark the degradation, do not hide it, do not fail the run.**
4. **`main.py:391` can then distinguish** a server misconfiguration from a provider rejection and say
   which in the 500 — instead of a guard that never fires.

**Not built, per the brief.**

---

## WHAT IS NOT ESTABLISHED

- **Whether any email has ever been delivered from production.** Only that the path is configured and
  a send would be attempted. See Part B for the three ways to settle it.
- **Alerting is not wired**, per instruction. And note that wiring it today would inherit the Part-C
  defect: an alerting send that silently failed would be discarded exactly as `job_manager`'s two call
  sites discard theirs. **Part C is a prerequisite for alerting, not an aside.**
- **The Part-C fix is proposed, not built**, and it touches a deliberate design decision (the
  unconfigured `True`), so it needs its own authorization.
- **`SENDGRID_FROM_EMAIL` is set in production but its value is unknown to me**, and an unverified
  sender is a delivery failure the config check cannot see.
