# Step 515 — Deployed. The prediction held: sdk_change is SILENT in production.

**Date:** 2026-08-31 · **Instruction:** `build_log/515_chat_instruction.md`
**Pushed `dad0662..5c090d4`, branch only, 0 unpushed, 0 tags on remote. Tests 369 passed, 3 skipped.**
**`CAM_ALERT_EMAIL` NOT set. Nothing scheduled.**

---

# 1-2. PREFLIGHT AND PUSH

```
origin/main before: dad0662   unpushed: 5   tracked files differing from HEAD: 0
tags: 2 local / 0 remote      tests: 369 passed, 3 skipped
```

Five commits, three touching deployable paths: `dde4255` (the Step-511 send contract across
`job_manager`, `main`, `notifications`), `fe21073` (`alerting.py`), `5c090d4` (`alerting.py`,
`startup_health.py`, `deps.manifest.json`, `tools/check_models.py`). The other two are `build_log/`
records.

Six flags confirmed from HEAD, unchanged. Manifest present in HEAD with 13 packages.

```
dad0662..5c090d4  main -> main     unpushed: 0     tags on remote: 0
```

# 3. THE PREDICTION HELD

**Stated before the result: `sdk_change` should be SILENT**, with the hedge that Railway re-resolves
on every rebuild and a package publishing a new version in the intervening hour would legitimately
trip it.

```
sdk_alerts (0)
   [] -> SILENT
```

**Nothing changed between manifest generation (12:43:34Z) and this boot (12:55:08Z).**

## And the silence is a real match, not an empty comparison

A check that silently compared nothing would also print `[]`. Verified independently by diffing the
committed manifest against the versions the deployed service reports:

```
manifest packages: 13 | deployed reported: 13
MISMATCHES: 0
```

**All thirteen present on both sides and identical.** The comparison ran and matched.

# 4. THE FULL BODY

```
GET /api/provider-health (authenticated) -> HTTP 200

status   : 'healthy'
checked  : 2026-08-31T12:55:08.303579+00:00   elapsed=14.26s
failures : []
sdk_alerts: []

anthropic  claude-sonnet-4-6           listed=True  callable=True  served=claude-sonnet-4-6
anthropic  claude-haiku-4-5-20251001   listed=True  callable=True  served=claude-haiku-4-5-20251001
openai     gpt-5.5                     listed=True  callable=True  served=gpt-5.5
xai        grok-4.3                    listed=True  callable=True  served=grok-4.3
google     gemini-3.1-pro-preview      listed=True  callable=True  served=gemini-3.1-pro-preview
google     gemini-2.5-pro              listed=True  callable=True  served=gemini-2.5-pro
anthropic  claude-haiku-4-5-20251001   listed=True  callable=True  served=claude-haiku-4-5-20251001

sdk_versions: anthropic 0.125.0 - openai 2.54.0 - google-genai 2.20.0 - httpx 0.28.1
              fastapi 0.124.4 - uvicorn 0.34.3 - python-docx 1.2.0 - PyMuPDF 1.28.2
              reportlab 4.5.1 - google-api-python-client 2.199.0 - google-auth 2.57.0
              python-dotenv 1.2.3 - python-multipart 0.0.32

email: {"branch": "sendgrid", "can_send": true, "sendgrid_configured": true,
        "gmail_api_configured": false, "email_configured": false,
        "sendgrid_from_email_set": true}
```

**All seven model targets listed and callable. Thirteen SDK versions matching the verified baseline.
Zero failures.** This is the first deployed boot where every check the system has passes.

**Elapsed dropped 18.7s to 14.26s.** The manifest comparison adds no provider call, so it costs
effectively nothing; the difference is provider latency variation, not the new check.

# 5. WHAT REMAINS — a green board does not mean a working alarm

**These are unchanged by this deploy, and the result above must not be read as covering them.**

- **`alerting.run()` has no caller.** The live check runs at boot and `sdk_change` is computed and
  surfaced on the endpoint — **but nothing converts any of it into an alert.** The values are visible
  only to someone who queries the endpoint and knows to look.
- **`CAM_ALERT_EMAIL` is unset.** Even a raised alert would record `no_alert_recipient_configured` and
  tell nobody. Correct and loud, per Step 512 — and still nobody told.
- **Boot-only cadence.** A model retired between deploys is invisible until the next one. Retired on a
  Tuesday with no deploy until Friday: **three days unreported.** Only periodic execution fixes that,
  and Step 513's recommendation (Railway cron, daily, 7 calls) is designed and **not built**.

**Of the three triggers: `sdk_change` computes correctly and is proven in production. `delisted` and
`unhealthy` compute at boot but reach nobody. None of the three currently reaches a person.**

---

## WHAT IS NOT ESTABLISHED

- **The manifest check has only ever been observed MATCHING in production.** Its mismatch path is
  proven locally — six real divergences at Step 514 — but has never fired deployed. The first real
  deployed mismatch is still ahead.
- **`local != production` remains true and unaddressed.** Local runs `openai` 2.8.1 against
  production's 2.54.0, plus five other divergences, so local boots `unhealthy` by design. Step 513's
  lockfile recommendation is the structural fix and is not built.
- **No alert has ever been sent to anyone**, in any environment, at any point.
- **Nothing verifies the deployed boot delay** — the same gap Step 507 §C.3 recorded, still open.
