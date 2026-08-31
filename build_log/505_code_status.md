# Step 505 — Where the checks belong. DESIGN ONLY. Nothing built, scheduled or wired.

**Date:** 2026-08-31 · **Instruction:** `build_log/505_chat_instruction.md`
**No code written. No provider spend. Item 1 BLOCKED — see below.**

---

# 1. THE RAILWAY LOG GREP — BLOCKED, and here is exactly why

The CLI is installed (`railway 4.56.1`, on PATH), **but its OAuth token is expired**:

```
Warning: failed to refresh OAuth token: Token refresh failed: invalid_grant
Unauthorized. Please run `railway login` again.
```

`railway login` opens a browser for interactive auth. **I cannot drive that.** There is also no
log-exposing endpoint on the app — I checked `main.py`'s route table.

**The grep is one command once you have re-authed:**

```bash
railway login
railway logs | grep -c "Email not configured"
```

**How to read it:**

- **count > 0** → SendGrid is unset in production. Every notification since the path was written has
  logged and `return True`d into a value nobody reads. **Nothing has ever been emailed.**
- **count == 0** → the SendGrid branch is being taken; then `grep "SendGrid:"` shows
  `SendGrid: sent to ... — HTTP {status}` (`notifications.py:404`) or
  `SendGrid failed to ... — falling back to SMTP` (`:408`), which is the real answer.

**I will not guess between them.** What is established: the code cannot distinguish the two states
from the inside, because the unconfigured path returns the same `True` as a successful send, and the
call site discards it.

---

# 2. WHERE EACH CHECK RUNS — AND A CORRECTION TO THE PREMISE

## 2.1 The brief says the drift test "would have caught August 26." **It would not have.**

This matters enough to state before the design rests on it.

On 2026-08-26 the declared spec was `anthropic>=0.78.0`. Railway installed **1.2.0**.
**`1.2.0` satisfies `>=0.78.0`.** The Step-502 drift test asks *"does installed satisfy declared"* — it
would have returned **green** on the exact day everything broke.

What would have caught it is the *other* Step-502 test — `test_every_dependency_has_an_upper_bound` —
and only as a **risk warning before the fact**, not as a detection of the break. It would have said
"this is unbounded," not "this is broken."

**So: neither existing check would have detected August 26 on the day. Only something making a real
call from inside production would have.** That is what §3 is for, and the premise correction is why
§3 is not optional.

## 2.2 The model check — `tools/check_models.py`

**Runs: outside the deployed app** — locally, or from a scheduler that is not Railway.

| | |
|---|---|
| **Green MEANS** | The provider APIs list and serve these models, to a client holding these keys, with the pipeline's parameters, **on the machine that ran it**. |
| **Green does NOT mean** | Production can call them. Different SDK version, different env vars, different egress, possibly a different key. |
| **Catches** | Model retirement, renaming, key revocation, quota exhaustion, provider outage, a parameter the *API* rejects. |
| **Misses** | Everything environment-specific — which is precisely the August 26 class. |

**Keep it outside production deliberately.** Its value is answering "is the outside world still what we
think it is," and that answer should not depend on the deployed app being up. If Railway is down, this
check should still tell you whether Anthropic is fine.

## 2.3 The requirements drift test — Step 502

**Runs: in the deployed environment, at startup.** It is currently in the local test suite, where it
guards *local* drift — real value, since local-below-floor is what hid August 26 for five days — but
that is a different question from what production installed.

| | |
|---|---|
| **Green MEANS** | Installed packages satisfy the declared ranges **in the environment that ran it**. |
| **Green does NOT mean** | The code works. A package can satisfy `>=0.78.0,<1.0.0` and still change behaviour inside that range. |
| **Catches** | A resolver landing outside the declared band; a package missing entirely. |
| **Misses** | Any break inside the band — and, before Step 502 added ceilings, any break at all. |

---

# 3. THE DEPLOYED-HEALTH CHECK

## 3.1 The three candidates, costed

| option | when it runs | cost | catches Aug 26? | objection |
|---|---|---|---|---|
| **(a) Startup assertion** | every boot / deploy | **~6 calls per deploy** (~1/day at current cadence) | **YES — at the moment the break is introduced** | a provider blip at boot must not take the service down |
| **(b) Health endpoint making live calls** | every poll | 6 × poll frequency. A 5-min monitor = **1,728 calls/day** | yes, but late | cost scales with monitoring, which is backwards |
| **(c) Scheduled job in production** | every N hours | 6 × N per day | yes, but up to N hours late | needs a scheduler the app does not have |

## 3.2 What I would choose: **(a), with (b) reading its cached result**

**The break is introduced at deploy time.** Railway rebuilds and re-resolves dependencies on every
push — that is the *only* moment the installed SDK can change. A startup check runs exactly when the
risk materialises, costs ~6 calls, and would have failed on 2026-08-26 within seconds of that deploy
going live.

A health endpoint then **reports the cached startup result** rather than making its own calls, so
polling is free and the expensive part happens once.

## 3.3 The smallest thing that would have caught it

```
On boot, for each provider: one call through the REAL adapter path with the
pipeline's own parameters (temperature=0.0), and record the installed SDK version.
```

**Both halves matter.** The call detects the break; **the recorded SDK version names the cause.** Step
501 spent two exchanges not knowing `anthropic` had moved, and the version was never in any artefact.

## 3.4 Failing loudly — and the trap this arc keeps hitting

Every defect in this arc is **something returning success on a broken path**: SendGrid's `return True`
when unconfigured; `is_fallback: False` on a stub no model produced; `api_error` asserting a call
reached the API. A startup check that merely logs would join that list.

So the design is:

1. **Default state is UNHEALTHY, not healthy.** If the check has not run, or crashed, or the module
   failed to import, the status is `unknown` and is treated as failing. **The absence of a result is
   never a pass.**
2. **`/api/health` returns non-200 when any provider is unhealthy** — machine-visible, not a log line
   somebody has to read.
3. **Every job result carries the provider-health snapshot and the SDK versions**, so a report made on
   a degraded panel is self-describing after the fact. This is the Step-497 disclosure principle
   applied one layer down.
4. **The app still starts.** A boot-time provider blip must not take down a service that can serve
   stored results and accept jobs — but it starts *marked unhealthy*, and the marking is what is loud.

**Deliberately not chosen: crash-on-failure.** It converts a transient provider incident into an
outage, and Railway's restart policy would then loop.

---

# 4. ALERTING — designed around the gemini false positive

Step 504's check reported the **live extractor** as broken because my probe budget was 16 tokens.
Shipped, that is a **daily false alarm on a healthy component**, and the next real failure gets
ignored. Every rule below exists to prevent that.

## 4.1 What triggers an email

- **A target transitions healthy → unhealthy and stays there for 2 consecutive checks.**
- **Any target fails the LISTED check.** Retirement is never transient — one occurrence is enough.
- **An installed SDK version changes between deploys**, even if every call passes. That is the
  August 26 signal, visible *before* it breaks anything.
- **The deployed startup check reports `unknown`** — the check did not run, which §3.4 treats as
  failure.

## 4.2 What stays silent

- Everything green.
- **A single probe failure that succeeds on retry.** Explicitly: on failure, **retry once with a
  larger output budget** before declaring anything. If the retry passes, log
  `probe calibration warning` and **do not alert** — that is the gemini case, caught by the check
  rather than by a human.
- A target already alerted on and still failing. **Alert on state change, not on state.**
- Latency variation. `grok-4.3` runs ~7s against ~1.5s for the others (Step 504); a latency threshold
  would fire on that today and it is not a fault.

## 4.3 Rate limiting

**At most one email per target per state-change per 24h.** A flapping provider produces one message,
not ninety.

## 4.4 The rule underneath all of it

**An alert must be able to be wrong in only one direction.** A missed real failure costs five days —
that already happened. A false alarm costs the credibility of every future alert, which costs the
*next* five days. **So: bias toward silence on anything that could be transient, and toward noise only
on things that cannot be** — a de-listed model, a changed SDK version, a check that did not run.

---

## WHAT IS NOT ESTABLISHED

- **Whether SendGrid has ever sent from production.** Item 1 is blocked on interactive auth. The
  command and the reading are in §1.
- **Nothing was built, scheduled or wired**, per instruction.
- **The startup-check cost estimate assumes Railway restarts only on deploy.** If it restarts on crash
  or idle-sleep, the per-day call count rises and I have not measured that.
- **Whether `/api/health` returning non-200 would upset Railway's own healthcheck** and cause a restart
  loop. Not checked, and it is a real risk in this design.
- **The two-consecutive-failures rule assumes a check cadence that does not exist yet.** It is
  meaningless until §3 is built and scheduled.
