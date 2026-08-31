# Step 512 — Alerting wired. Part C caught a cry-wolf defect in it.

**Date:** 2026-08-31 · **Instruction:** `build_log/512_chat_instruction.md`
**Tests 369 passed, 3 skipped. No real email sent — transport stubbed throughout. Not deployed.**

---

# PART A — THE TRIGGER SET

`05 Lease Analyzer/app/alerting.py`. Keys on the **per-model set**, never the summary.

| kind | condition | why |
|---|---|---|
| `unhealthy` | healthy -> unhealthy, **two consecutive** checks | absorbs a transient blip |
| `delisted` | `listed=False`, **immediately** | a retirement is never transient |
| `sdk_change` | any installed version changed, **even when every call passes** | the 2026-08-26 signal, visible *before* it breaks anything |

**Alert on state CHANGE, not state.** `unhealthy` fires at exactly `consecutive == 2`, so it alerts
once rather than on every later check; `delisted` fires only on the True->False transition.

## Where prior state lives, and the cold start

`05 Lease Analyzer/telemetry/provider_alert_state.json`, overridable via `CAM_ALERT_STATE_DIR`.

**Cold start — no prior state — is SILENT.** `evaluate()` computes `cold_start` from the absence of
both prior models and prior SDK versions and skips every trigger. A missing *or corrupt* file is also
a cold start: `load_state` catches and returns `{}` rather than raising. **A first boot must never
alert — every model would look like a change from nothing.**

## THE STRUCTURAL LIMIT, and it is serious

**`.gitignore:23` records that Railway uses ephemeral storage.** The state file does not survive a
redeploy. Consequences:

- **`sdk_change` cannot fire in production as designed.** The versions change *at* a rebuild, and the
  rebuild is exactly what erases the prior state to compare against. Every deploy is a cold start.
- **`unhealthy` needs two consecutive checks, but the startup assertion runs ONCE per boot.** With
  state erased each deploy, a second consecutive check never happens in the deployed environment.

**So the trigger set is correct and testable, and in production only `delisted` could fire** — and
only if a check ran twice in one container lifetime, which nothing currently arranges.

**This is a real gap, not a caveat.** Closing it needs either a persistent store (a Railway volume —
none is configured) or a periodic in-process re-check (Step 505 rejected a scheduler on cost grounds,
and that trade deserves revisiting now the reason is concrete). **Not built; flagged for decision.**

---

# PART B — DISPATCH RECORDS ITS OWN OUTCOME

`dispatch()` uses the Step-511 contract and **captures** `{"sent", "channel", "reason"}`:

```python
    result = _send_email(target, subject, body)
    rec = {"attempted": True, "sent": bool(result.get("sent")),
           "channel": result.get("channel"), "reason": result.get("reason"), ...}
```

**An alerting system that discards its own send result is the defect this step exists past** — it
would report success while never alerting anyone: the shape Step 510 found in SendGrid, Step 497 in
`is_fallback`, Step 502 in `api_error`, Step 508 in the gate's fail-open.

## Where a failed alert is visible, and why there

1. **Logged at ERROR** — `[alerting] N alert(s) NOT DELIVERED: channel=... reason=...` — reaching the
   Railway log, the same surface that carried the raw `TypeError` which solved Step 501.
2. **Persisted into the state file as `last_dispatch`**, so it survives the log scroll and sits next
   to the state that produced it.

**Defence:** a human asking *"why didn't I get an alert?"* has exactly two places to look — the log
and the alert state — and both now answer. The health endpoint was deliberately **not** chosen: it
reports *provider* health, and an email-transport failure is a different fact that would muddy it.

**`dispatch` never raises.** A failure to alert must not take down whatever called it.

---

# PART C — IT DISCRIMINATES, AND IT CAUGHT A DEFECT IN ITSELF

```
1. first boot, no prior state                  NONE  <- silent
2. all healthy, unchanged                      NONE  <- silent
3. unhealthy, FIRST occurrence                 NONE  <- silent
4. unhealthy, SECOND consecutive               [('unhealthy', 'anthropic:claude-sonnet-4-6')]
5. unhealthy, third -- must not re-fire        NONE  <- silent
6. recovers                                    NONE  <- silent
7. listed=False -> immediate                   [('delisted', 'anthropic:claude-sonnet-4-6')]
8. still delisted -- must not re-fire          NONE  <- silent
9. still delisted, again                       NONE  <- silent
10. recovers from delisting                    NONE  <- silent
11. SDK changed, ALL CALLS PASSING             [('sdk_change', 'anthropic')]

emails sent: 3 -> ['unhealthy (1)', 'delisted (1)', 'sdk_change (1)']
```

**Three alerts across eleven checks, each firing exactly once.**

## The defect Part C caught

**The first run fired a SECOND alert at step 8** — `unhealthy` on a model that had *already* alerted
as `delisted` one check earlier. A delisted model is also unhealthy, so its `consecutive_unhealthy`
counter reached 2 the check after the delisting was reported, and it sent a message saying nothing
new.

**That is precisely the cry-wolf failure this design exists to prevent, produced by the design
itself.** Fixed by suppressing `unhealthy` while `listed is False`: delisting is the specific cause,
and it has already been reported immediately.

**A static read would not have found it.** Both triggers are correct in isolation; only running them
in sequence against the same target exposes the overlap. **Five consecutive steps now.**

## Send failure, and no recipient

```
11. ALERT SEND FAILS
   alerts raised : [('delisted', 'anthropic:claude-sonnet-4-6')]
   dispatch      : {"attempted": true, "sent": false, "channel": "sendgrid",
                    "reason": "provider_rejected: HTTP 403", "alert_count": 1, ...}
   state carries last_dispatch: {... "sent": false, "reason": "provider_rejected: HTTP 403" ...}
   ERROR [alerting] 1 alert(s) NOT DELIVERED: channel=sendgrid reason=provider_rejected: HTTP 403

12. NO RECIPIENT CONFIGURED
   dispatch: {"attempted": false, "sent": false, "channel": "none",
              "reason": "no_alert_recipient_configured", "alert_count": 2}
   ERROR [alerting] 2 alert(s) RAISED BUT NOT SENT: CAM_ALERT_EMAIL is unset
```

**Recorded, not swallowed, in both cases** — including the one where alerts were raised and there was
nowhere to send them, which is the alerting equivalent of the `not_configured` defect Step 511 fixed.

---

## THE TWO STEP-511 FLAGS, recorded as instructed

**1. A dict is always truthy.** `_send_email` now returns a dict, so any `if result:` treats every
outcome — including `not_configured` — as success. All call sites were updated and `dispatch()` reads
`result.get("sent")` explicitly, **but a caller added later that treats the result as a bool would
silently regress.** The `-> dict` annotation is the only guard, and annotations are not enforced.

**2. `notification_*` reaches `GET /api/jobs/{id}` by a different mechanism than the Step-498
fields.** `_record_notification` writes the job dict directly; `run_quality` / `panel_substituted`
travel via `_JOB_QUALITY_FIELDS` and `apply_outcome_to_job`. **Two mechanisms landing on the same
endpoint.** Both work. Neither is wrong. But a future reader cannot tell which is canonical, and a
field added to the wrong one will silently not appear.

---

## WHAT IS NOT ESTABLISHED

- **Nothing is scheduled. `alerting.run()` exists and is proven, but NO CALLER INVOKES IT.** The
  startup assertion does not call it; nothing does. **It is a wired module, not a running system.**
- **No real email has been sent.** Every transport was stubbed. Nothing here proves an alert arrives.
- **`CAM_ALERT_EMAIL` is unset everywhere**, so as configured today the module would raise alerts and
  record `no_alert_recipient_configured` — correctly and loudly, but nobody would be told.
- **The ephemeral-state limit means two of three triggers cannot fire in production.** That is the
  most important open item in this step.
- **Not deployed.**
