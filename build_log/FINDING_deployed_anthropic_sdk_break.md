# Finding: an unpinned SDK removed role A from production for five days

**Date:** 2026-08-30 · **Status:** ROOT CAUSE FOUND. Pin prepared and verified locally. **NOT
DEPLOYED.**
**Step:** 501 · **Companions:** `487_code_status.md`, `488_..._unmarked.md`, `500_code_status.md`

---

## The error, verbatim from the Railway log

```
2026-08-30T23:26:31.170069806Z  Eval-A (LP-01): calling claude-sonnet-4-6 (anthropic)...
2026-08-30T23:26:31.171187326Z  Eval-A (LP-01): claude-sonnet-4-6 FAILED (api_error):
    anthropic_error: TypeError: Messages.create() got an unexpected keyword argument 'temperature'
```

**1.1 milliseconds.** No HTTP request was ever made. This is a client-side `TypeError`.

## Root cause

`requirements.txt:13` read `anthropic>=0.78.0` — **no upper bound**, set at `ec692d3`, 2026-03-16,
"Initial deployment", and never revisited.

**`anthropic` 1.0.0 removed `temperature` from `Messages.create()`.** Verified by downloading and
inspecting wheels, no installs:

```
anthropic 0.75.0   -> temperature ACCEPTED
anthropic 0.78.0   -> temperature ACCEPTED
anthropic 0.125.0  -> temperature ACCEPTED     (last 0.x)
anthropic 1.0.0    -> temperature REMOVED      (the break)
anthropic 1.2.0    -> temperature REMOVED      (latest; what Railway installs)
```

`cam/core/provider_router.py:458` sets it unconditionally outside extended-thinking mode:

```python
            else:
                params["temperature"] = target.temperature
            ...
            resp = self.client.messages.create(**params, timeout=target.timeout_sec)
```

Railway rebuilds on every push. **The 2026-08-26 push (Step 487) resolved `anthropic` to 1.x, and
every Anthropic call in production has failed since.**

## Why it was invisible for five days

**Local was never running what production runs.** Local had `anthropic 0.75.0` — which does not even
satisfy the declared floor of `>=0.78.0`. So:

| | SDK | role A |
|---|---|---|
| **Local** — 6 runs (491 x3, 494, 496, 498) | 0.75.0 | `claude-sonnet-4-6` served **202/202 every time** |
| **Deployed** — 3 runs (487 x2, 500) | 1.x | Anthropic failed **100%, every time** |

Six local successes against three deployed failures was read at Step 500 as an environment or
credential difference. **It was a dependency difference, and local was the environment that had
drifted.**

## The blast radius is wider than Stage 305

Step 500's census looked only at Stage-305 element records and reported *"gemini-2.5-pro stood in on
30 issue areas."* **That understates it.** The log shows Anthropic dying in five subsystems, and in
three of them the fallback dies too:

```
lease_coverage_305         Eval-A x30 LPs                  -> gemini via shared pool
lease_use_aware            Eval-A                          -> gemini via shared pool
lease_use_impact           Eval-A: ALL ATTEMPTS FAILED     -> no substitute at all
lease_synthesis            Eval-A, Compound, Pass2: fallback FAILED
lease_finding_consequence  Eval-A: ALL ATTEMPTS FAILED     -> no substitute at all
```

**Role A's own-chain fallback is `claude-haiku-4-5`, also Anthropic, so it failed identically.** Only
the shared pool (`gemini-2.5-pro`, Google) could answer — and the stages that have no shared-pool path
simply lost the evaluator.

## `api_error` was not merely lossy — it was wrong

`_classify_failure` (`lease_coverage_305.py:161`) matched on `"_error:" in m`, the substring inside
`"anthropic_error:"`, and labelled a **client-side TypeError** as an **API error**.

Step 488 §3 recorded that the label was lossy across timeout/429/401/5xx. **It is worse than that: the
label asserts the call reached the API. It never did.** That mislabel sent this investigation to the
Railway credential page and the billing page before the raw string was read.

**Refinement to Step 488 §5.2:** that section said `error_msg` "does not appear in the event record"
and I generalised it to "the raw error is gone." **The record loses it; stdout does not.**
`lease_coverage_305.py:611` prints the exception verbatim, and the Railway log had the answer all
along. The open item is smaller than stated — put what is already printed into the record — but the
mislabel is a separate and sharper defect.

## The fix, prepared and verified

```
anthropic>=0.78.0,<1.0.0
```

Preserves the deliberate `0.78.0` floor and excludes the major version that removed the argument.

**Local was brought onto the pinned range** — `0.75.0 -> 0.125.0`, the version production will now
resolve to — and verified:

```
anthropic 0.125.0   temperature in create(): True
claude-sonnet-4-6            OK 'OK' in 1.71s  usage={'output_tokens': 4, 'input_tokens': 18}
claude-haiku-4-5-20251001    OK 'OK' in 0.58s  usage={'output_tokens': 4, 'input_tokens': 17}
367 passed, 12 subtests passed
```

**Both the primary and its own-chain fallback work on the version production will get**, and the
suite passes on the upgraded SDK.

## NOT DONE

- **Not deployed.** This needs a push, which is Tzvi's call.
- **Not migrated to 1.x.** `anthropic` 1.x is a deliberate major-version API change; adapting
  `provider_router` to it is separate work with its own measurement.
- **The other twelve dependencies remain unbounded** — `fastapi`, `uvicorn`, `openai>=2.0.0`,
  `google-genai`, `httpx`, `PyMuPDF` and the rest all carry `>=` with no ceiling and the identical
  exposure. Only `anthropic` was fixed, because only it is known to have broken.
- **The `api_error` mislabel is unfixed**, as is persisting the raw provider error (Step 488 open
  item 1).

## WHAT THIS INVALIDATES

**Every deployed measurement in this arc was taken on a two-primary panel with Gemini in role A**, and
several stages ran with role A absent entirely. That includes Step 487's two runs and Step 500's
Atlas run.

**Step 500's Atlas comparison against the six local runs is therefore not a like-for-like
comparison** — in particular LP-17's move to `covered 6/0`, which I flagged there as possibly
panel-related. It was, and now there is a mechanism.

**What it does NOT invalidate:** Step 500's disclosure result. `panel_substituted: true` firing was
correct and is *more* clearly correct now — the panel genuinely was substituted, for a concrete
reason, and the report said so. The fix worked on exactly the case it was built for.
