# Step 516 — Design only. Mark by default; refuse only when the instrument cannot exist.

**Date:** 2026-08-31 · **Instruction:** `build_log/516_chat_instruction.md`
**Nothing built. Nothing deployed. No provider calls.**

---

# 1. WHAT A RUN SHOULD DO — recommendation, with the carve-out

**"Warn only" is out.** It is the defect. **The August 26 runs completed** — every one of them warned
in the log, fell back per-LP, and produced a report nobody could tell was degraded. Adding a warning
to a system whose failure mode was "warned and carried on" changes nothing.

**Recommendation: MARK DEGRADED BEFORE ANY WORK HAPPENS — with a narrow REFUSE carve-out.**

## Why mark rather than refuse, as the default

**Our health check has already been wrong once.** Step 504's first run reported the live extractor
`gemini-3.1-pro-preview` as broken because my probe budget was 16 tokens. Had that check held a veto,
**it would have refused every run for a healthy model.**

**A check that can produce a false positive should not hold the power to refuse work.** Marking is
recoverable — the user gets a report carrying a caveat they can weigh. Refusing is not — they get
nothing, and if the check was wrong they got nothing for no reason.

**And a substituted panel is not worthless.** Step 500 measured it directly: on a run with role A
served by `gemini-2.5-pro`, LP-07, LP-16 and LP-27 came back **byte-identical** to the clean-panel
runs. It is not the product they asked for; it is also not garbage. **Marking lets the user decide
that; refusing decides it for them.**

## Why a refuse carve-out is still needed

Marking is only defensible **because the marking now works** — Step 500 proved `panel_substituted`
fires and reaches the disclosure surfaces. Before Step 497 it did not, and "mark it" would have been
"warn only" wearing a better name.

But there is a case marking cannot cover: **when the panel cannot be assembled at all.** If a role has
no primary, no own-chain fallback and no shared-pool substitute, the run does not produce a
three-model panel with a caveat — it produces a two-model panel, a structurally different instrument.
Marking that as "substituted" would understate it.

**And the extractor is the sharper case.** If `gemini-3.1-pro-preview` and its fallback are both
unavailable, there is no evidence at all — the run burns ~96 calls to produce a report over nothing.
**Refusing there costs the user nothing and saves them a pointless spend.**

## The dissent I want on the record

There is a real argument I am **not** taking: that delivering a report on a panel other than the one
named, having taken the user's run to do it, is something they should consent to *beforehand* rather
than be *told about afterwards*. **That argument is correct, and the honest shape is a third option
neither of us listed — surface the degradation at submission and let the user choose to proceed.**

I am not recommending it now because it needs a UI decision and a submission-time interstitial that
does not exist. **But "mark degraded" is the right default only until that exists, not instead of
it.**

---

# 2. RE-CHECK, BLOCKING, WITH A SHORT TTL

**Re-check. Not the cached boot verdict.**

The staleness is the whole defect. A container lives for days: boot verdict at 09:00 says healthy,
the provider breaks at 14:00, a run at 15:00 inherits "healthy" and discovers the failure one LP at a
time. **That is exactly the shape this step exists to close, and a cached verdict reproduces it.**

**Cost: 7 calls against ~96 — 7.3%.** Against a 12-15 minute run that has already been measured at
743-858 seconds, this is cheap insurance.

## Blocking, not racing

**Racing defeats the purpose.** If the verdict arrives mid-pipeline, the run has already discovered
the failure the way it does today. The entire value is knowing *before* work begins.

**Cost of blocking: ~14 seconds.** The deployed check has been measured at 14.26s and 18.7s. Against
a 750-second run that is **under 2%**.

## The refinement that makes it cheap: a short TTL

**A verdict good for 5 minutes, not forever.** A batch submission of four tenants would otherwise
probe four times for the same answer. With a 5-minute TTL the batch pays once.

**5 minutes is short enough that the staleness defect does not return** — the failure window a stale
verdict can hide shrinks from hours to minutes — **and long enough that batches and retries are
free.** It is a different thing from the boot cache, which has no expiry at all; that absence is the
bug.

---

# 3. WHICH FAILURES STOP VERSUS MARK — a different threshold from Step 512, and why

**Step 512's threshold answers "should a human be told?". This one answers "should work proceed?".
Different questions, and reusing one for the other would be a category error.**

Concretely: Step 512 alerts on *state change* — a target already failing produces no further alert.
**A run does not care whether the failure is new.** It cares whether the panel can be assembled right
now. A model that has been broken for three days is old news to alerting and completely decisive to a
run.

**Proposed run threshold, reusing Step 497's vocabulary rather than inventing a third:**

| condition | outcome |
|---|---|
| every role's **primary** available | **PROCEED CLEAN** |
| a role's primary unavailable, **a substitute exists** (own-chain or shared pool) | **PROCEED, MARKED** — `panel_substituted`, the Step-497 surfaces |
| a role has **no available model at all** | **REFUSE** — the panel cannot be assembled |
| the **extractor** and its fallback both unavailable | **REFUSE** — no evidence can be produced |

**The Step-487 case lands on "PROCEED, MARKED"**, correctly: `gemini-2.5-pro` did cover role A, the
panel was three models, and the report was usable with a caveat.

**One thing this threshold deliberately does not do:** it does not count *how many* roles are
substituted. Two substituted roles is worse than one, but it is still a three-model panel and still a
disclosure question, not a refusal one. **Adding a "two or more substituted → refuse" rule would be
inventing a boundary with no evidence behind it.**

---

# 4. WHERE IT LIVES — the pipeline entry, because it is the only place a run cannot bypass

| candidate | catches | misses |
|---|---|---|
| API route `/api/jobs/lease` | web submissions | **the harness, any internal caller, any future entry point** |
| `job_manager` worker | everything routed through jobs | **direct adapter calls — including `run_mode_c.py`, which made every measurement in this arc** |
| **pipeline entry** (`run_lease_coverage_only` / `run_lease_analysis`) | **everything** | nothing |

**This project's two named precedents both fail at exactly this point.** Step 504 found SendGrid wired
into three call sites and never verified working; the 423 stack was built and never called. **A check
placed anywhere a caller can route around is a check that will eventually be routed around.**

**Recommendation: the pipeline entry, defaulting to ON**, with an explicit parameter to supply an
already-fresh verdict (so the API route can fail fast before file processing without paying twice).
**Bypass then requires a deliberate act rather than an accidental path.**

## The layering constraint this must respect

`run_lease_coverage_only` lives in `cam/adapters/lease_review/`. `startup_health` lives in the app.
**`cam/` must not import from `05 Lease Analyzer/app/`** — Step 461 established layering tests for
exactly this direction.

**The preflight logic therefore belongs beside `tools/check_models.py`, which imports only
`cam.core`.** The app passes its cached verdict *in* when it has a fresh one; the pipeline performs
its own when it does not. **The dependency points the right way and the enforcement point stays where
it cannot be bypassed.**

---

# 5. WHAT THE USER SEES

## If refused

The message must name the provider, state it is not the document's fault, and be accurate about cost:

> **This analysis could not start.**
> The Anthropic evaluator is unavailable — `claude-sonnet-4-6` and its fallback `claude-haiku-4-5`
> both failed a live check just now. This is a provider outage on our side, **not a problem with your
> document**, and nothing about your lease caused it.
> No analysis was performed. Please try again shortly; if this persists, it is being investigated.

**Deliberately not said: "nothing has been charged."** The preflight itself spent 7 calls. **Claiming
zero cost would be the same class of false reassurance this arc has spent fifteen steps removing.**

## If it proceeds marked

**No new surface. Step 497's, unchanged:** `panel_substituted` on the result, `run_quality` on the
status API, the amber banner on the results page, and all five export surfaces — annotated DOCX,
annotated PDF, summary DOCX, batch DOCX, combined PDF.

The existing wording already fits: *"Findings are not invalid, but the evaluator panel is not the one
this report names."*

**One field worth adding, not a surface:** record that the substitution was known **at start** rather
than discovered mid-run. Same disclosure, better provenance — and it is the difference between "we
found out" and "we knew and proceeded."

---

# RECOMMENDATION IN ONE PARAGRAPH

**Re-check at the pipeline entry, blocking, with a 5-minute TTL. Proceed and mark via the Step-497
surfaces when a substitute exists; refuse only when a role has no available model at all or the
extractor is entirely down. Do not give a check that has already produced one false positive the
power to refuse work it can still usefully do.**

---

## WHAT IS NOT ESTABLISHED

- **The 5-minute TTL is a judgement, not a measurement.** No data says 5 rather than 2 or 15.
- **The refuse path has never been exercised**, because no run has ever met the condition — Step 487's
  runs all had a working shared-pool substitute.
- **~14s of blocking preflight is measured from the deployed boot check**, which probes 7 targets
  serially. Probing only the models a run needs, or in parallel, would cut it; neither is designed.
- **The consent-at-submission option in §1 is described but not designed**, and I consider it the
  better long-term answer than either of the two I recommended between.
- **Nothing was built.**
