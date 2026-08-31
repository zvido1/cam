# Step 517 — Run preflight built. It found a dead fallback and a cost-accounting gap.

**Date:** 2026-08-31 · **Instruction:** `build_log/517_chat_instruction.md`
**Tests 369 passed, 3 skipped, call-free. One real Atlas run: proceeded unmarked, clean panel.**
**Not deployed.**

---

# WHAT WAS BUILT

`tools/run_preflight.py` — beside `check_models.py`, importing only `cam.core` and that module, so
`cam/` imports nothing from the app (Step 461's layering constraint).

Wired at **`run_lease_coverage_only`**, the pipeline entry — the only place a run cannot bypass. The
API route misses the harness; `job_manager` misses direct adapter calls, **including `run_mode_c.py`,
which made every measurement in this arc.**

| decision | condition |
|---|---|
| `proceed` | every seat's primary available |
| `proceed_marked` | primary down, a substitute exists |
| `refuse` | a seat has no available candidate at all |

Blocking, 5-minute TTL. New result fields: **`panel_substitution_known_at_start`** and
**`run_preflight`**.

## The dissent is a comment at the decision point

`lease_adapter.py` now carries, at the line that chooses:

> *"...the user is being handed a report produced by models other than the ones it names, having
> already spent their run to produce it, and is TOLD AFTERWARDS. The honest shape is to surface the
> degradation at submission... IF A SUBMISSION-TIME CONSENT SURFACE IS EVER BUILT, THIS DEFAULT SHOULD
> BE REVISITED. It is a stand-in for asking, not a decision that asking is wrong."*

A status file is read once; a comment is read by whoever next touches that line.

---

# THE EXERCISE — seven cases, providers stubbed

```
1. all healthy                      decision=proceed
2. role A down, pool covers         decision=proceed_marked  substituted=['evaluator_A']
3. panel UNASSEMBLABLE              REFUSED   unavailable=['evaluator_A']
4. extractor entirely down          REFUSED   unavailable=['extractor']
5. second run inside TTL            calls=0   from_cache=True
6. TTL expired                      calls=8   from_cache=False
7. preflight itself errors          decision='proceed_marked'  reason='preflight_error'
```

**The refusal message** names the seat, says it is not the document's fault, and **does not claim
nothing was charged** — asserted in the test, not read. The preflight itself just spent calls, and a
false reassurance about cost is the defect class this arc has spent fifteen steps removing.

**Case 7, defended:** on its own failure the preflight returns `proceed_marked` — not `proceed`, which
would claim health it never verified, and not `refuse`, which would let a bug in the guard block every
run in the product. Marking says the honest thing: *we do not know.* It mirrors `startup_health`'s
`unknown`, which is likewise never a pass.

---

# THE REAL RUN — and my prediction was wrong

```
503 baseline : calls=98   elapsed=857.7s
517 with pre : calls=97   elapsed=878.4s
DELTA        : -1 call
```

**I predicted 106. The record says 97.**

**The preflight's 8 calls are not counted in `api_calls_total`.** The log shows all eight
`modelcheck-*` router initialisations, so the spend genuinely happened — but `api_calls_total` counts
only the pipeline's own calls, and the preflight runs through `check_models`' router before that
counter exists. The 97-vs-98 difference is ordinary variance; Step 491 measured 96-99 across runs.

**So a run's own cost accounting now under-reports what the run spent, by 8 calls, permanently, until
someone fixes it.** Recorded as an open item, not fixed — it touches the pipeline's accounting and is
outside this step's brief.

**Elapsed is where the cost shows: +20.7s**, consistent with 8 probes including the ~10s mistral
backoff this run still paid (it started before the fatal-retry fix below).

## Preflight verdict, on the result

```
decision='proceed'  substituted=[]  unavailable=[]  from_cache=False
known_at_start=False   panel_substituted=False

evaluator_A   primary=anthropic:claude-sonnet-4-6     primary_ok=True  available=3
evaluator_B   primary=openai:gpt-5.5                  primary_ok=True  available=3
evaluator_C   primary=xai:grok-4.3                    primary_ok=True  available=2
extractor     primary=google:gemini-3.1-pro-preview   primary_ok=True  available=2

census: 606 records, 0 stubs, 0 contradictions, degraded=False
   role A claude-sonnet-4-6 202 | role B gpt-5.5 202 | role C grok-4.3 202
```

---

# THREE DEFECTS FOUND, TWO OF THEM MINE

## 1. The suite made real provider calls — MINE, fixed

Adding the preflight made **15 tests fail and the suite jump 2.4s to 87s.** Found by running it.

Fixed with `CAM_SKIP_RUN_PREFLIGHT`, set in `conftest.py`. **The skip is recorded on the result**
(`run_preflight.decision == "skipped"`), so a bypassed preflight can never be mistaken for a passed
one — the same rule as `sent: False` versus a bare `True`.

## 2. Fatal errors were retried — MINE, fixed

`try_call` retried **everything**, including `FatalProviderError`. Retrying exists to absorb
transients; a missing adapter fails identically forever.

```
before: mistral probe attempts=3  ~10s of backoff
after : mistral probe attempts=1  0.00s  retry_skipped='fatal_not_transient'
        anthropic probe attempts=1  2.22s  (healthy models unaffected)
```

**Every preflight was burning ten seconds on a guaranteed failure.**

## 3. `mistral` in the shared fallback pool CANNOT BE CONSTRUCTED — pre-existing, NOT fixed

```
RAW (FatalProviderError): Unknown provider: mistral      [in 0.00s -- no network involved]
```

`_SHARED_FALLBACK_POOL` (`lease_coverage_305.py:124`) lists
`("mistral", "mistral-large-latest", "Mistral Large")` as a shared fallback for **all three evaluator
seats**, and `ProviderRouter._get_adapter` has no mistral adapter. **It has never been able to fire.**

**The shared pool is effectively one entry — `gemini-2.5-pro` — while the config claims two.**

**The consequence is concrete.** At Step 487, when role A's own chain was exhausted, the pool tried
gemini and it worked. **Had gemini also been down, mistral would have raised `Unknown provider` and
the seat would have been lost entirely** — the `all_failed` stub case from Step 488. The chain looks
two-deep and is one-deep.

**Not fixed: it is a behaviour change to the fallback chain and needs its own decision.** Two options
— add a mistral adapter, or remove the entry. **I would remove it.** A fallback that cannot fire is
worse than no fallback, because it makes the chain look deeper than it is and nothing ever says
otherwise.

**It is visible in the record now**: `available=3` on evaluators A and B, where the config promises
four.

---

## WHAT IS NOT ESTABLISHED

- **The refuse path has never fired on real providers.** Proven with stubs only; no real outage has
  met the condition.
- **`api_calls_total` under-reports every run by 8 calls.** Open, unfixed.
- **The mistral pool entry is dead and still configured.** Open, deliberately not fixed here.
- **Only `run_lease_coverage_only` is wired.** `run_lease_analysis` (Mode A) has no preflight; Mode C
  is what this arc measures, but Mode A shares the evaluator seats and is unguarded.
- **The 5-minute TTL is a judgement, not a measurement**, unchanged from Step 516.
- **Not deployed**, so no deployed run has ever been preflighted.
