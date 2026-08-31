# Step 513 — Design only. The cheapest fix removes the hardest requirement.

**Date:** 2026-08-31 · **Instruction:** `build_log/513_chat_instruction.md`
**Nothing built. Nothing deployed. No provider calls.**

---

## THE HEADLINE, BEFORE THE OPTIONS

**Item 3 dissolves items 1 and 2 for the trigger that matters.** `sdk_change` — the one that would
have caught 2026-08-26 — **needs no scheduler, no live call and no persistent state** if it compares
against a *committed manifest* at boot. The repo survives redeploys by construction; that is what a
repo is.

**And once `sdk_change` leaves the periodic path, state persistence stops being load-bearing.** The
remaining use of prior state is de-duplication — not re-alerting daily about a known failure. **If
dedup state is lost, the cost is a duplicate alert, not a missed one.** Duplicates are annoying;
misses cost five days. That flips item 1 from "must solve" to "nice to have."

---

# 1. STATE PERSISTENCE

| option | survives redeploy | cost | trade |
|---|---|---|---|
| **Railway volume** | yes | **billed storage — I cannot quote the rate**; configured per-service in the dashboard, not in `railway.toml` | Simplest persistent option. Adds a paid resource and a mount path. **I could not verify the current plan's volume pricing and will not guess it.** |
| **External store** (DB / object store) | yes | a new dependency and credentials | The repo has **no database**. Adding one to hold a 2 KB JSON file is disproportionate. |
| **Commit state to the repo** | yes | free | **Production cannot write back to the repo.** Viable only where the writer is a CI job or a local run — which is exactly item 3's manifest, and exactly why item 3 is the right shape. |
| **Accept ephemeral, use state for dedup only** | no | free | **Recommended.** Losing it duplicates an alert; it cannot cause a miss. |

## Fail-closed, and the current code is NOT

`load_state` returns `{}` on a missing *or corrupt* file, which becomes a cold start, which is
**silent**. That is fail-closed against crying wolf and **fail-OPEN against missing a failure** — the
exact direction this arc keeps getting burned by.

**The distinction that must exist: "no state because this is the first run" vs "state should be here
and is gone."** They are different facts and the code cannot currently tell them apart.

**Proposed:** an explicit `CAM_ALERT_STATE_PERSISTENT=1` declaring the expectation. With it set, a
missing state file is itself an alert (`state_lost`) rather than a silent reset. Without it, cold
start stays silent because it is genuinely expected. **The alerting system must be able to alert on
its own inability to alert** — the same rule as Step 511, one level up.

---

# 2. PERIODIC EXECUTION — and Step 505's cost argument does not survive re-examination

**At daily cadence: 7 calls/day.** Step 505 rejected a live-calling endpoint at **1,728/day**. That
is a **247× difference**, and the objection was entirely about volume.

For scale without inventing prices: **7 calls/day is 2,555/year — roughly 26 Atlas runs' worth of
calls, spread over twelve months.** Against a defect that cost five days of production running a
two-model panel, that is not a close call. **Step 505's rejection was right for its cadence and does
not transfer. I am not inheriting it.**

| option | environment observed | would it have caught Aug 26? | notes |
|---|---|---|---|
| **Railway cron** | **deployment** | **YES** | The only option that runs the deployed SDKs. Railway runs cron as a scheduled service invocation; a web service needs a separate cron service or a command entrypoint. **I could not verify the exact mechanism on the current plan.** |
| **External scheduler -> authenticated endpoint** | deployment, **but stale** | no, as built | `/api/provider-health` returns the **cached boot result** and makes no calls. It would need a re-check trigger; that is a new authenticated write-ish path. |
| **Windows scheduled task (local)** | **API only** | **NO** | Step 505's distinction holds exactly. Free, but blind to the failure class that motivated all of this. |
| **GitHub Actions** | **a fresh resolve of `requirements.txt`** | **YES, and EARLIER** | A runner doing `pip install -r requirements.txt` reproduces the resolver decision Railway will make **before Railway makes it.** No repo CI exists today (`.github/workflows` absent). |

## THE TRIGGER DESIGN AND THE CADENCE ARE COUPLED — and Step 505 set triggers with no cadence

**"Two consecutive checks" at daily cadence means up to 48 hours to alert.** For a provider outage
that is far too slow, and it was designed against an unstated frequent cadence.

**Proposed correction:** at daily cadence, replace *two consecutive checks* with **retry-within-the-run** — probe, and on failure re-probe two or three times, spaced, before deciding. Detection lands
inside one run instead of two days. Step 505 already proposed a retry for the gemini false positive
(*"retry once with a larger budget"*); this generalises it and **removes the only reason prior state
was load-bearing.**

---

# 3. `sdk_change` — VIABLE, AND STRICTLY BETTER

**Yes. And it is the recommendation.**

A committed `deps.manifest.json` recording the exact versions verified at the last deliberate check —
**Step 507 §C.2 already produced precisely this data from production.** At boot, `startup_health`
compares `importlib.metadata` against it.

| property | why it matters |
|---|---|
| **No scheduler** | It runs at boot, which is *when the change happens* — Railway re-resolves on every push |
| **No live call** | Pure metadata read. Zero provider cost |
| **No persistent state** | The manifest is in the repo, which survives redeploys by construction |
| **Fails closed naturally** | A missing manifest is itself a defect worth alerting on |
| **Names the cause** | It reports `anthropic 0.125.0 -> 1.2.0`, which is the sentence Step 501 took two exchanges to reach |

**Had this existed on 2026-08-26, the first boot after that deploy would have said
`anthropic 0.125.0 -> 1.2.0` before a single lease was analysed.**

## But the structural fix is a real lockfile, and I should say so

Manifest-compare **detects** drift. A **lockfile prevents it.** `requirements.lock` with pinned
versions and hashes, installed with `pip install -r requirements.lock`, makes production's resolution
identical to what was tested — **eliminating the Step-507 finding that local and production differ on
6 of 13 packages**, including `openai` 2.8.1 vs 2.54.0.

**Trade:** a lockfile needs deliberate regeneration, and platform-specific wheels can differ between a
Windows dev box and a Linux container — so the lock must be generated for the deployment platform, not
the dev one. That is real work and a real constraint.

**My recommendation: both, in order.** Manifest-compare now (cheap, no install-process change,
detects everything). Lockfile as a follow-on, because prevention beats detection and because
"local ≠ production on 6 of 13 packages" is still true and still unaddressed.

---

# 4. `CAM_ALERT_EMAIL`

| environment | how it is set | needed for |
|---|---|---|
| **Railway (production)** | a service variable, alongside `SENDGRID_API_KEY` | any deployed alert |
| **Local** | `05 Lease Analyzer/.env` | alerts from local checks |
| **GitHub Actions** (if adopted) | a repository secret | alerts from CI |

**Two things beyond simply setting it:**

- **It should be an operations address, distinct from user notification mail.** Alerts and customer
  results should not share an inbox; the failure mode is an alert lost among reports.
- **SendGrid's from-address must be verified for it to deliver.** Step 510 confirmed
  `sendgrid_from_email_set: true` in production but **its value is unknown to me**, and an unverified
  sender is a delivery failure no config check can see.

**Until it is set, the module behaves correctly and loudly:** it raises alerts and records
`no_alert_recipient_configured` at ERROR. **Correct, and nobody is told** — which is precisely why
this item is on the list rather than assumed.

---

# RECOMMENDATION, in order

1. **`sdk_change` -> committed manifest, compared at boot.** Cheapest, needs nothing else, and it is
   the trigger that would have caught the incident this whole arc came from.
2. **Set `CAM_ALERT_EMAIL`** in Railway and locally. One variable; without it nothing can be told to
   anyone.
3. **Replace "two consecutive checks" with retry-within-the-run**, which fits a daily cadence and
   removes the last dependence on persistent state.
4. **Daily execution: Railway cron for deployment health.** GitHub Actions is the valuable *addition*
   — it catches resolver drift before Railway installs it — but it observes a fresh resolve, not the
   running container, so it complements rather than replaces.
5. **Lockfile** as the structural fix, separately scoped.
6. **A Railway volume is NOT needed** if 1 and 3 are done. Revisit only if state becomes load-bearing
   again.

---

## WHAT IS NOT ESTABLISHED

- **Railway volume pricing and Railway cron's exact mechanism on the current plan.** I could not
  verify either — the CLI token is expired and neither is in the repo. **Both are stated as
  unverified rather than estimated.**
- **Whether GitHub Actions is acceptable here at all.** It would need repository secrets holding
  provider keys, which is a security decision nobody has made.
- **The retry-within-the-run proposal is untested.** It replaces a rule that was itself never tested
  against a real transient failure.
- **Nothing was built.** `alerting.run()` still has no caller, and `CAM_ALERT_EMAIL` is still unset.
