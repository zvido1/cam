# Step 507 — Gated, deployed, and production's SDK versions are observable for the first time.

**Date:** 2026-08-31 · **Instruction:** `build_log/507_chat_instruction.md`
**Tests 369 passed against HEAD. Pushed `969453e..92b8d1a`, branch only, 0 tags on remote.**
**Alerting NOT wired. Model check NOT scheduled.**

---

# PART A — GATED, VERIFIED BY REQUEST

## The mechanism, and it is the existing one

The app has **one** access-code mechanism: compare a submitted value to `config["ACCESS_CODE"]`. Two
transports exist:

```
main.py:303   /api/auth/verify     ->  if submitted == config["ACCESS_CODE"]: return {"valid": True}
main.py:709   /api/jobs/lease      ->  if config["ACCESS_CODE"] and access_code != config["ACCESS_CODE"]:
```

A GET has neither a body nor a form field, so the same comparison is fed from an **`X-Access-Code`
header**. **A query parameter was deliberately not offered** — it would put the shared secret into
Railway's request logs.

## The deliberate divergence

`/api/auth/verify` treats an unset `ACCESS_CODE` as *"gate disabled, allow all."* **This endpoint does
the opposite: unset means anonymous-only.** Following the existing convention would publish SDK
versions and provider reachability from any misconfigured deploy. **Fail closed** — the same principle
as `startup_health`'s `unknown` default.

## Verified by request, not by reading

```
ANONYMOUS      -> HTTP 200   {"status": "unhealthy"}
WRONG CODE     -> HTTP 200   {"status": "unhealthy"}
AUTHENTICATED  -> HTTP 200   keys: [checked_at, elapsed_sec, error, failures,
                                    models, sdk_versions, started_at, status]
```

**A wrong code returns the anonymous body, not a 401.** No leak, and the response does not reveal that
a gate exists — and it holds the always-200 contract, so nothing about auth can reach the platform
channel.

---

# PART B — DEPLOYED

```
969453e..92b8d1a  main -> main
unpushed: 0    tags on remote: 0    tracked files differing from HEAD: 0
```

Six flags confirmed from HEAD (`SPAN_EVIDENCE_LPS = {LP-07, LP-12, LP-17, LP-27}`,
`SECTION_EXPANDED_SPAN_LPS = set()`, `ENTAILMENT_TEST_LPS = {LP-27}`,
`GATE_ABORT_RETURNS_DEGRADED = True`, `DEGRADABLE_APPLICABILITY = {not_applicable, unclear}`,
`SPAN_EVIDENCE_ENABLED = True`). Deployable commits: `ec10970` (`tools/check_models.py`), `0e58a90`
(`startup_health.py`, `main.py`), `92b8d1a` (the gate).

**This is the first Railway build to install against upper-bounded requirements.**

---

# PART C — OBSERVED IN PRODUCTION

## C.1 It reproduces the Step-506 discrimination, exactly

```
status='unhealthy'   elapsed=18.7s
started=2026-08-31T02:57:03.824343+00:00   checked=2026-08-31T02:57:22.527718+00:00
failures: ['anthropic:claude-sonnet-4-20250514 (FatalProviderError)']

anthropic  claude-sonnet-4-6           listed=True  callable=True  served=claude-sonnet-4-6
anthropic  claude-haiku-4-5-20251001   listed=True  callable=True  served=claude-haiku-4-5-20251001
openai     gpt-5.5                     listed=True  callable=True  served=gpt-5.5
xai        grok-4.3                    listed=True  callable=True  served=grok-4.3
google     gemini-3.1-pro-preview      listed=True  callable=True  served=gemini-3.1-pro-preview
google     gemini-2.5-pro              listed=True  callable=True  served=gemini-2.5-pro
anthropic  claude-sonnet-4-20250514    listed=False callable=False served=None
   RAW (FatalProviderError): anthropic_error: NotFoundError: Error code: 404 -
     {'type': 'error', 'error': {'type': 'not_found_error',
      'message': 'model: claude-sonnet-4-20250514'}
```

**Six pipeline models callable in production; the document gate's dead default is not.** Same
discrimination as local, now from inside the environment it exists to guard.

## C.2 PRODUCTION SDK VERSIONS — and local is NOT production

```
package                    prod         declared                satisfies
fastapi                    0.124.4      >=0.110.0,<0.125.0      True
uvicorn                    0.34.3       >=0.27.0,<0.35.0        True
python-multipart           0.0.32       >=0.0.6,<0.1.0          True
python-dotenv              1.2.3        >=1.0.0,<2.0.0          True
anthropic                  0.125.0      >=0.78.0,<1.0.0         True
openai                     2.54.0       >=2.0.0,<3.0.0          True
google-genai               2.20.0       >=2.0.0,<3.0.0          True
httpx                      0.28.1       >=0.27.0,<0.29.0        True
google-api-python-client   2.199.0      >=2.100.0,<3.0.0        True
google-auth                2.57.0       >=2.23.0,<3.0.0         True
python-docx                1.2.0        >=1.1.0,<2.0.0          True
PyMuPDF                    1.28.2       >=1.24.0,<2.0.0         True
reportlab                  4.5.1        >=4.0.0,<5.0.0          True

ALL PRODUCTION VERSIONS SATISFY requirements.txt: True
```

**Every bound holds.** But the answer to "do they match what requirements.txt pins" is yes, while the
answer to "do they match local" is **no — six of thirteen differ**:

| package | local | **production** | gap |
|---|---|---|---|
| **openai** | 2.8.1 | **2.54.0** | **46 minor versions** |
| PyMuPDF | 1.26.0 | 1.28.2 | 2 minors |
| google-api-python-client | 2.187.0 | 2.199.0 | 12 minors |
| reportlab | 4.4.1 | 4.5.1 | 1 minor |
| python-multipart | 0.0.22 | 0.0.32 | 10 patches |
| python-dotenv | 1.2.1 | 1.2.3 | 2 patches |

`anthropic` (0.125.0), `google-genai` (2.20.0), `httpx`, `fastapi`, `uvicorn`, `google-auth` and
`python-docx` match.

**`openai` 2.54.0 is running role B in production and has never been exercised locally.** That is the
same shape as the August 26 break — a provider SDK that production has and local does not — differing
only in that this one happens to work. **The bounds contained it; they did not eliminate it.** Step
502's drift test proves local satisfies the declared ranges; it cannot prove local equals production,
and this is the first evidence of how far apart they actually are.

**Nothing is broken and nothing needs fixing today.** Recording it because it was invisible until this
endpoint existed, and because "all green" is the wrong reading of this table.

## C.3 Boot delay — NOT MEASURED in production

**Locally: 25ms.** The startup hook logged `background check started` at `22:54:42.363` and startup
completed at `22:54:42.388`, while the check itself ran 17.9s on its daemon thread.

**In production I do not have the equivalent measurement.** The check ran 18.7s
(`02:57:03.824 -> 02:57:22.527`), but I have no deployed log line for when the app began serving, and
my first poll landed after the check had already finished. **The design guarantees non-blocking — a
daemon thread launched from the startup hook — and the local figure supports it, but I am not
reporting a production number I did not take.** It is in the Railway log; my CLI token is expired
(Step 505 §1).

---

## WHAT IS NOT ESTABLISHED

- **The production boot delay.** See C.3. Design-guaranteed and locally measured, not deployed-measured.
- **Whether `openai` 2.54.0 behaves identically to 2.8.1** on the role-B path. It answered the probe;
  no pipeline run has exercised it locally, and every local run of this arc used 2.8.1.
- **Whether the deployed check would catch a break introduced mid-life** rather than at boot. It runs
  once per boot; a provider change while the container is up goes unnoticed until the next deploy.
- **Alerting is not wired and the model check is not scheduled**, per instruction. Nothing yet reads
  `status: unhealthy` and tells anyone.
- **Production has been reporting `unhealthy` since this deploy** — correctly, for the document gate's
  dead model id. Until that is fixed, `unhealthy` is the steady state, which will mask a new failure
  from any future alerting keyed on the top-level status.
