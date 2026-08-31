# Step 504 — Model check built and proven. It caught a false positive in itself.

**Date:** 2026-08-31 · **Instruction:** `build_log/504_chat_instruction.md`
**NOT scheduled. Email NOT wired.** Spend: 7 probe calls ×2 runs + 4 budget probes.

---

# PART A — WHAT EXISTS

## A.1 SendGrid is WIRED, not shelfware

`05 Lease Analyzer/app/notifications.py:332-333` — the dispatcher:

```python
    if sendgrid_configured(config):
        return _send_via_sendgrid(to_email, subject, body, html, attachments, config)

    if gmail_api_configured(config):
        return _send_via_gmail_api(to_email, subject, body, html, attachments, config)

    return _send_via_smtp(to_email, subject, body, html, attachments, config)
```

`_send_via_sendgrid` (`:341`) POSTs to `https://api.sendgrid.com/v3/mail/send` with
`Authorization: Bearer {SENDGRID_API_KEY}` — **stdlib `urllib` only, no pip dependency**, which is why
it does not appear in `requirements.txt`.

**Live call sites, all reachable:**

```
job_manager.py:1645   send_job_failed_email(email, job_id, ...)     <- on job failure
job_manager.py:1683   send_job_complete_email(email, job_id, ...)   <- on job completion, with attachments
main.py:380           _send_email(email, subject, text)             <- POST /api/send-results-link
```

**This is not the 423 situation.** The 423 stack was built and never called; this is called from three
places on paths that run.

## A.2 Credential — and I cannot check Railway

`config.py:47-48`: `SENDGRID_API_KEY` and `SENDGRID_FROM_EMAIL`, both `os.getenv(..., "")`.

- **Present in the local keys file** (`DoubleCheck/.../api_keys/.env`).
- **`05 Lease Analyzer/.env` has only `SMTP_HOST/PORT/USER/PASSWORD`** — no SendGrid. The app loads
  its own `.env`, not the DoubleCheck one, so **locally the app would take the SMTP branch, not
  SendGrid.**
- **Railway: UNKNOWN.** I cannot read the dashboard. **But there is a decisive tell in the log** — see
  A.3.

## A.3 Does anything send successfully? UNKNOWN — and the code cannot tell you

`notifications.py:325-330`:

```python
    if not email_configured(config) and not sendgrid_configured(config):
        logger.info(
            f"Email not configured — logging notification:\n"
            f"  To: {to_email}\n  Subject: {subject}\n  Body:\n{body}"
        )
        return True
```

**An unconfigured environment logs the message and returns `True`.** And the return value is
**discarded** at the call site (`job_manager.py:1683` ignores it entirely).

**So a completely unconfigured email path reports success, and nothing anywhere checks.** This is the
same defect class the whole arc has been closing: a function that says it worked when it did not.

**I have not verified a single successful send.** My Step-500 and Step-503 deployed jobs passed no
email address, so no send was attempted. Triggering one would email a real person — an outward-facing
action I am not taking unasked.

**The decisive check, and it is free:** grep the Railway log for `Email not configured`. If that line
appears after a completed job, SendGrid is unset in production and every notification has been a
no-op. If it does not appear, the SendGrid branch is being taken and `SendGrid: sent to ... — HTTP
{status}` (`:404`) will say what the API returned.

---

# PART B — THE CHECK

**`tools/check_models.py`** — standalone, alongside the existing `tools/export_attorney_preread.py`.
Chosen over `build_log/`: this is an operations tool that will eventually run on a schedule, not a
step artefact, and `build_log/` is gitignored.

## B.1 Why two checks, not one

**A models-list check would not have caught the 2026-08-26 break.** `claude-sonnet-4-6` was listed,
available, and being served correctly to anyone calling it correctly. What broke was the SDK
signature. So:

1. **LISTED** — in the provider's models endpoint. Catches retirement, renaming, access revocation.
2. **CALLABLE** — one call **through the real `ModelTarget` → `ProviderRouter` → `_get_adapter` →
   `adapter.call` path**, with `temperature=0.0` — *the parameter anthropic 1.x rejected*. Catches SDK
   drift, parameter rejection, auth, quota.

**Neither subsumes the other.** LISTED-but-not-CALLABLE is the 2026-08-26 failure exactly.
CALLABLE-but-not-LISTED would be a soon-to-retire alias still being served.

Each probe uses a **single-target router**, so no fallback can mask a failure: a failure is a failure
of *that model*, not of the chain.

## B.2 Raw errors only

Failures print the raw exception type and message, never a classified label — because Step 502
established `_classify_failure` matched the `_error:` substring inside every wrapped provider
exception and labelled a client-side `TypeError` as `api_error`, sending an investigation to the
billing dashboard.

## B.3 Output

```
provider   model                       listed  callable  elapsed  role
------------------------------------------------------------------------------------------------
anthropic  claude-sonnet-4-6           yes     yes       1.78s    panel role A (primary)
anthropic  claude-haiku-4-5-20251001   yes     yes       0.59s    panel role A (own-chain fallback)
openai     gpt-5.5                     yes     yes       1.37s    panel role B (primary)
xai        grok-4.3                    yes     yes       7.07s    panel role C (primary)
google     gemini-3.1-pro-preview      yes     yes       2.05s    extractor (primary)
google     gemini-2.5-pro              yes     yes       2.56s    shared fallback pool
anthropic  claude-sonnet-4-20250514    NO      NO        0.18s    document gate default

1 OF 7 TARGETS FAILED -- raw errors below, unclassified:

  anthropic:claude-sonnet-4-20250514  (document gate default)
     listed   : False
     callable : False
     RAW ERROR (FatalProviderError): anthropic_error: NotFoundError: Error code: 404 -
       {'type': 'error', 'error': {'type': 'not_found_error',
        'message': 'model: claude-sonnet-4-20250514'}, 'request_id': 'req_011Cea3HC3E4rvmKfJJdwfn7'}
```

`--json` emits the same data machine-readably and exits non-zero on any failure, ready for scheduling.

---

# PART C — IT DISCRIMINATES, AND IT CAUGHT A DEFECT IN ITSELF

## C.1 The required test passes

**`claude-sonnet-4-20250514` fails on BOTH checks** — `listed: NO` *and* `callable: NO`, with the raw
404 quoted above. That is the model the document gate has been silently falling back from on every
run since Step 491 observed it. **The check does test what it claims.**

## C.2 The first run had a FALSE POSITIVE, and Part C is why it was found

The first run reported **`gemini-3.1-pro-preview` — the live extractor — as NOT CALLABLE**:

```
RAW ERROR (ProviderError): google_error: RetryableProviderError:
    google_empty_output: no extractable text
```

**That model demonstrably works** — it extracted the Atlas lease in 104.1s at Step 503, hours earlier.
So I tested the hypothesis rather than shipping the alarm:

```
gemini-3.1-pro-preview at increasing output budgets:
   budget=16    FAIL  google_empty_output: no extractable text
   budget=64    FAIL  google_empty_output: no extractable text
   budget=256   OK  'OK'  1.85s
   budget=1024  OK  'OK'  2.12s
```

**My probe budget was the defect, not the model.** A reasoning model spends its output budget thinking
before emitting text; at 16 tokens it emits none. `PROBE_OUTPUT_TOKENS` is now **256**, with the
measurement recorded in the code so nobody "optimises" it back down.

**Had this shipped, it would have produced a daily false alarm on the extractor** — and a monitor that
cries wolf on a healthy component is worse than no monitor, because the next real failure gets
ignored. Part C's discrimination requirement is what surfaced it.

---

## WHAT IS NOT ESTABLISHED

- **Not scheduled, email not wired.** Per instruction.
- **Whether SendGrid works in production.** Unknown, and the code's `return True` on an unconfigured
  environment means no existing signal answers it. The Railway log grep in A.3 would.
- **The check has never run against the deployed environment.** It runs locally, against the same
  provider APIs. It would not have caught the 2026-08-26 break *as deployed*, because that break was
  in Railway's installed SDK, not in the APIs — **only the Step-502 requirements test catches that,
  and only if it runs there.**
- **`grok-4.3` took 7.07s and 6.69s** across two runs — roughly 4× the others. Not investigated; noted
  because a latency threshold would need it.
- **The gate's dead model id is still unfixed.** This check now reports it every run; it does not
  repair it.
