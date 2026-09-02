# Step 525 — Timeout raised 300→540s. solidpower COMPLETED. The raise was not what made it complete.

**Date:** 2026-09-02 · **Instruction:** `build_log/525_chat_instruction.md`
**Tests: 389 passed, 3 skipped, 12 subtests. Panel verified clean before spending.**
**solidpower (211,735 chars): COMPLETED in 1717.2s wall / 1158.97s pipeline, 86 calls. Not deployed.**

---

# PART A — THE INVENTORY

## A.1 The ceiling, quoted

`cam/adapters/lease_review/lease_extract.py:347` (pre-change):

```python
EXTRACTION_PRIMARY_TIMEOUT = 300.0
EXTRACTION_FALLBACK_TIMEOUT = 300.0
```

It governs **one provider call** — the extraction call — passed as
`ModelTarget(timeout_sec=timeout, max_retries=0)` and enforced inside the Google adapter:

```python
raise TimeoutError(f"Router timeout exceeded: {router_elapsed:.1f}s > {target.timeout_sec}s")
```

**Its own comment refuted it.** The prior text read: *"At 50 tok/s, a 16k-token chunk response takes
~332s — 300s covers this with margin."* **332 > 300.** The arithmetic never supported the number it
justified.

## A.2 Ten timeouts on the path, not one

| where | value | governs |
|---|---|---|
| **`lease_extract.py` PRIMARY / FALLBACK** | **300s** | **the extraction call — the binding one** |
| `lease_coverage_305.py` ×3 evaluator configs | 300s | one evaluator call |
| `lease_element_elicitation.py` `ELICITATION_TIMEOUT` | 300s | one elicitation call |
| `lease_evaluate.py` `EVALUATOR_ATTEMPT_TIMEOUT` | 300s | one evaluator attempt |
| `lease_closed_form_directional.py` `_CF_TIMEOUT_SEC` | 120s | one call |
| `lease_adapter` challenge / cascade / severity / interpretation | 180 / 120 / 120 / 60s | one call each |
| `ModelTarget.timeout_sec` default | 45s | any target not overriding |
| OpenAI + Anthropic SDK clients | 600s | transport |
| Google `httpx.Client` | 600s | transport |
| `tools/check_models.try_call` | 90s | probe only |

**`DEFAULT_CONFIG["extraction_timeout"] = 300.0` is DEAD.** `grep -rn "extraction_timeout"` returns the
definition and no consumer. Anyone raising that value would change nothing and believe they had.

**There is no stage-level and no job-level timeout anywhere.** Every timeout in the system bounds a
single provider call.

## A.3 On expiry: hard fail. Not retry, not fallback.

`max_retries=0` on the extraction target, and canonical mode refuses to substitute:

```
google_error: TimeoutError: Router timeout exceeded: 308.8s > 300.0s
CANONICAL FAIL-CLOSED: primary extractor failed; fallback suppressed in canonical mode
```

It kills the **call** → `ExtractionIntegrityError` kills the **stage** → the stage kills the **job**.
That chain is why atreca produced no result at all.

**Attribution correction:** the 308.8s observation is real but is recorded in
`build_log/FINDING_lease_term_years_contingent_term.md` §3, **not Step 494** — 494 ran divall and Atlas
only, and its status contains no mention of atreca.

## A.4 Nothing downstream binds it — except one thing

`railway.toml` in full:

```toml
[deploy]
startCommand = "cd '05 Lease Analyzer' && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

No request timeout, no healthcheck, no worker/keepalive settings. **Jobs run in
`threading.Thread(daemon=True)`, so the HTTP request returns immediately** and no platform request
timeout applies to the pipeline. The client polls on `POLL_INTERVAL_MS = 5000` — a display cadence, not
a bound.

**The one real constraint is the 600s httpx transport timeout** in the Google adapter. A router ceiling
above 600 would be shadowed by the transport and could never fire.

---

# PART B — 540s, FIT TO TWO MEASURED POINTS

```
atlas    31,755 chars -> 105.74 s   (measured, Step 524 _stage_data.extraction_meta)
atreca  160,244 chars -> >= 308.8 s (CENSORED -- it timed out, so the true value is higher)

slope     = (308.8 - 105.74) / (160,244 - 31,755) = 0.001580 s/char
intercept = 105.74 - 0.001580 x 31,755            = 55.6 s
t(chars) ~= 55.6 + 0.001580 x chars

540 s -> (540 - 55.6) / 0.001580 = 306,539 chars = 299.4 KB
```

**That covers the largest document in the corpus — everbridge at 294,492 chars (288.6 KB) — by about
4%.** It is a **lower bound on capability**: the atreca point is censored, so the true slope is steeper
and the true capacity lower. 299 KB is optimistic and should be read that way.

**Why not higher:** 540 sits deliberately under the 600s httpx cap, leaving the router timeout as the
governing limit with 60s of headroom. Going past 600 means raising the transport timeout in
`cam/core/provider_router.py` first.

**Cost when a call genuinely hangs:** a stuck extraction holds a daemon thread for 9 minutes instead of
5. **Here it does not matter much** — single-tenant deployment, no worker pool, no queue — and the
failure it replaces is worse: atreca occupied the thread for the full 300s *and returned nothing*. It
would matter under concurrency, which does not exist yet.

---

# PART C — solidpower COMPLETED

```
build_log/runs/525_solidpower_thornton_industrial_lease.txt-modec_20260902_135645
doc            : 211,735 chars (209.6 KB)  -- 6.7x Atlas
wall (harness) : 1717.2 s
pipeline       : 1158.97 s        calls: 86 stored / 96 logged
degraded       : False            invalid_for_legal_analysis: False
stages         : extraction 231.8s   synthesis 468.6s
```

## THE RAISE DID NOT MAKE THIS RUN COMPLETE

**Extraction took 231.8s. The old ceiling was 300s.** solidpower would have completed without the
change. The raise is justified by atreca's 308.8s, and **this run does not exercise it.** The 540s
ceiling remains untested against a document that actually needs it.

The prediction was wrong in the safe direction: the model said ~395s for 211,735 chars; the measurement
is **231.8s**, so the linear fit **overestimates**. The atreca point being censored made the slope look
steeper than it is, which means 540s likely supports documents larger than 299 KB — but that is now two
points disagreeing with a third, not a validated model.

## Extraction and the gate

```
model: gemini-3.1-pro-preview   fallback_used: False
gate attempts: 1                aborts: 0
extraction_completeness_failed: False   failed LPs: []
```

**The gate passed on the first attempt with no failing LPs.** No retry, no degradation.

## The locator — 17.5%, between divall and Atlas

Same method applied to all three documents (non-null `section_ref` on element citations, resolved via
`_resolve_section_excerpt`):

| document | refs | resolve | rate | headings found |
|---|---|---|---|---|
| atlas | 136 | 114 | **83.8%** | 89 |
| **solidpower** | **120** | **21** | **17.5%** | **1** |
| divall | 80 | 2 | 2.5% | 0 |

**This is NOT Step 479's metric and does not reproduce its numbers** (479 reported 99.0% / 7.2% over
1,758 / 305 refs). My counts are an order of magnitude smaller, so 479 counted refs from more sites
than element citations. The three figures above are internally consistent with each other and should be
compared only to each other.

**The mechanism is the heading index: solidpower yields 1 heading against Atlas's 89.** The locator
degrades with heading structure, not with document size.

## The seamed LPs — all four got spans, none fell back

```
LP-07   spans= 4  tenant_text=4660  state=partial   method=step_305_per_element
LP-12   spans=12  tenant_text=5025  state=partial   method=step_305_per_element
LP-17   spans= 5  tenant_text=1745  state=partial   method=step_305_per_element
LP-27   spans= 3  tenant_text=1370  state=missing   method=step_305_per_element
fallback_events: 0        all four: fallback_used=False, 3/3 evaluators
```

**On a 209 KB document with one heading, the 423 seam worked on all four LPs.** That is the strongest
result in this run.

## assessment_status

```
{'assessed': 26, 'not_assessed': 6}      summary.not_assessed = 6

LP-04 Security Deposit         not_applicable      LP-23 Percentage Rent   not_applicable
LP-20 Exclusivity              not_applicable      LP-29 Right of Entry    broken_xref
LP-21 Guaranty of Lease        not_applicable      LP-31 Co-Tenancy        not_applicable
```

coverage states: `partial 13, review_needed 5, not_applicable 5, covered 4, covered_unfavorable 2,
missing 2, broken_xref 1`.

## The qualifier pass — it fired, and its documented limit fired with it

**9 LPs annotated, 15 distinct clauses, and every single quote resolves verbatim against the source.**
The no-fabrication property holds on a real lease.

**But `section_ref` is `None` on all of them**, because `_SECTION_RE` looks for `Section N.N` and this
document has one heading. Annotations read *"a clause elsewhere in the lease"*. `distance_chars` is
`None` on 8 of 9 and `also_retrieved_under` is empty everywhere, because `_evidence_intervals` could not
locate most LPs' `tenant_text` in the document by substring.

**This is exactly the generality limit recorded in the module docstring at Step 524, now observed
rather than predicted.** The pass degrades to "there is a clause, here it is, verbatim" — which is
still the useful half — and loses orientation, distance and cross-reference.

### And the first real lease exposed a false-positive pattern

Two of the fifteen are not liability qualifiers at all:

> *"In no event shall Tenant introduce or permit to be kept on the Premises or brought into the
> Building any hazardous..."*
> *"In no event shall any refueling occur outside and/or upon the Premises"*

**`in no event shall` is a generic prohibition formula, not a liability cap.** It did not appear in
Atlas. **Not fixed** — the brief is a timeout raise and a run, and tuning the detector here would be
scope creep. Recorded as an open item.

## Calls and cost

```
api_calls_total field      : 86
pipeline log line          : 96
sum of _coverage_api_calls : 78
```

**Three different numbers for one run.** The 86-vs-96 gap is the Step-517 accounting defect —
`api_calls_total` omits the preflight's 8 calls and the gate call — still open and now confirmed on a
second document.

---

# WHAT IS NOT ESTABLISHED

- **The 540s ceiling is untested.** solidpower's extraction finished in 231.8s, under the old limit.
  Nothing in this step exercised the new value; atreca has still never completed.
- **The linear timing model is contradicted by its own third point** (predicted 395s, measured 231.8s).
  Two points, one censored, one contradiction — it is an estimate, not a validated relationship.
- **One real lease of nine.** atreca, everbridge, ncino, quanterix, bokf, albireo and both remaining
  atreca variants are still unrun.
- **The locator comparison is my metric, not Step 479's**, and does not reproduce 479's figures.
- **The 17.5% resolution rate has no quality reading attached.** Nobody checked whether the 99
  non-resolving refs point at real sections the index missed, or at citations the evaluators invented.
- **`in no event shall` false positives are unfixed**, and no count exists of how many qualifier hits
  across the corpus are of that shape.
- **Not deployed.** No frontend change; `app.js` still does not render `qualifier_annotations`.
