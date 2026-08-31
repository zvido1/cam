# Step 506 — The healthcheck loop does not exist, and the assertion discriminates.

**Date:** 2026-08-31 · **Instruction:** `build_log/506_chat_instruction.md`
**Tests 369 passed. NOT deployed. Alerting NOT wired. Model check NOT scheduled.**

---

# PART A — THE LOOP I FLAGGED DOES NOT EXIST HERE

## A.1 No healthcheck is configured

`railway.toml`, verbatim and complete:

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "cd '05 Lease Analyzer' && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

**There is no `healthcheckPath`.** A repo-wide search for `healthcheck` / `health_check` /
`healthcheckPath` across `.toml`, `.json`, `.py`, `.yaml` returns nothing.

**Railway's default with no `healthcheckPath`: it does not poll any HTTP path for liveness.** A
deployment is up once the process starts and binds `$PORT`. Restarts are driven by
`restartPolicyType = "on_failure"` — the process **exiting** — capped at 3 retries.

## A.2 Does the loop exist? No — but I cannot prove the negative

Nothing Railway polls can be made non-200, because Railway polls nothing. **However:** a healthcheck
path can also be set in the Railway dashboard, which does not appear in this repo, and my Railway CLI
token is expired (Step 505 §1) so I cannot read it. **I am not claiming the dashboard is clean. I am
claiming it does not matter, because of A.3.**

## A.3 The separation: health lives in the BODY, never the status code

**`/api/provider-health` always returns HTTP 200**, including when unhealthy. The verdict is in the
JSON body.

**Defence.** The status code is the channel platforms act on; the body is the channel monitors read.
Separating them makes the design safe **regardless of what the dashboard says** — a 200 can never
trigger a restart, so even a dashboard healthcheck aimed at this exact path is inert. Relying instead
on "no healthcheck is configured" would make correctness depend on a setting I cannot see and that
someone could change later without touching this repo.

The path is also deliberately **not** `/health`, `/healthz` or `/` — none of the conventional liveness
paths a platform polls by default.

**Cost of the choice:** a generic monitor that only watches status codes sees nothing. Acceptable —
alerting is not wired, and when it is (Step 505 §4) it will parse the body, which carries far more
than a code could.

---

# PART B — THE STARTUP ASSERTION

`05 Lease Analyzer/app/startup_health.py`, launched from the existing `@app.on_event("startup")` hook
at `main.py:189`, **after** `find_and_load_env()` because it needs the provider keys.

Each design point traces to a defect in this arc:

| property | why |
|---|---|
| **Initial status `unknown`** | Fail-closed. Nothing can set `healthy` except a completed check with zero failures. Absence of a result is never a pass. |
| **Import failure leaves `unknown`** | If `tools.check_models` cannot import, status stays unhealthy rather than silently passing. |
| **Daemon thread** | Boot is never delayed; a slow provider cannot stop the service coming up. |
| **App still starts** | Crash-on-failure was rejected at Step 505 — it turns a provider blip into an outage and `on_failure` loops it. |
| **Records SDK versions** | The call detects the break; **the version names the cause.** Step 501 spent two exchanges not knowing `anthropic` had moved. |
| **Raw errors only** | Step 502 established the classifier asserts a call reached the API when it never left the process. |
| **Reuses `tools/check_models`** | One definition of targets and probe parameters — the module Step 504 built and proved, `PROBE_OUTPUT_TOKENS=256`. |

---

# PART C — IT DISCRIMINATES

Booted the **real FastAPI app** through `TestClient`, which fires the actual startup hook.

**Before the check completes — fail-closed, verified:**

```
status: 'unknown'   (= UNHEALTHY)
GET /api/provider-health -> HTTP 200  status='unknown'
```

**The app answered immediately while the check was still running** — non-blocking, as designed.

**After the check completes (16.88s):**

```
HTTP STATUS CODE : 200          <-- 200 even when unhealthy, per A.3
body status      : 'unhealthy'
failures         : ['anthropic:claude-sonnet-4-20250514 (FatalProviderError)']

anthropic  claude-sonnet-4-6           listed=True  callable=True
anthropic  claude-haiku-4-5-20251001   listed=True  callable=True
openai     gpt-5.5                     listed=True  callable=True
xai        grok-4.3                    listed=True  callable=True
google     gemini-3.1-pro-preview      listed=True  callable=True
google     gemini-2.5-pro              listed=True  callable=True
anthropic  claude-sonnet-4-20250514    listed=False callable=False
   RAW ERROR (FatalProviderError): anthropic_error: NotFoundError: Error code: 404 -
     {'type': 'error', 'error': {'type': 'not_found_error',
      'message': 'model: claude-sonnet-4-20250514'}, 'request_id': 'req_011Cea4bmcSg1XYmi6LKrUqv'}
```

**UNHEALTHY, on exactly the model Part C required.** The six pipeline models are green; the document
gate's dead default is not. **A fresh boot does not report all-green, so the check is testing what it
claims.**

**And it is loud.** The failure block prints to stdout with rule lines and logs at ERROR — visible in
the Railway log without anyone querying an endpoint.

**SDK versions recorded on every boot:**

```
anthropic=0.125.0  openai=2.8.1  google-genai=2.20.0  httpx=0.28.1  fastapi=0.124.4
uvicorn=0.34.3  python-docx=1.2.0  PyMuPDF=1.26.0  reportlab=4.4.1
google-api-python-client=2.187.0  google-auth=2.57.0  python-dotenv=1.2.1
python-multipart=0.0.22
```

**Had this existed on 2026-08-26, the boot after that deploy would have printed `anthropic=1.2.0` and
UNHEALTHY on all four Anthropic targets, with the raw `TypeError` naming `temperature`.** Five days
would have been minutes.

*(Incidental: `google-auth` reads 2.57.0 here against 2.49.1 at Step 502 — pulled up by the
`google-genai` 2.x upgrade. Still inside `>=2.23.0,<3.0.0`; the drift test passes.)*

---

## WHAT IS NOT ESTABLISHED

- **Not deployed.** Verified locally against the real app object, not against Railway.
- **Whether a healthcheck is set in the Railway dashboard.** Unknown, and by design it no longer
  matters — but the negative is unproven, not disproven.
- **Boot cost in production.** 16.88s here, on a daemon thread. Railway's cold-start behaviour, and
  whether it restarts on anything other than deploy, is unmeasured — Step 505 carried the same gap.
- **The check has never run in the deployed environment**, which is the whole point of it.
- **Alerting is not wired and the model check is not scheduled**, per instruction.
- **`/api/provider-health` is unauthenticated.** It exposes installed SDK versions and provider
  reachability — fingerprinting information nobody asked to make public. Worth a decision before
  deploying.
