# Step 558 — Pushed, and the verdict fix holds in production. The headline does not: the model call fell back and the canned string says the same false thing by a third route.

**Date:** 2026-09-04 · **Instruction:** `build_log/558_chat_instruction.md`
**`134f01f..3d0ac42  main -> main`, branch only. Redeployed `started_at 2026-09-04T12:32:33Z`. Deployed run `lease_review_20260904_123242_956ec9`, `run_quality: clean`. Tests: 445 passed, 3 skipped, 12 subtests.**

---

# 0. THE PREFLIGHT FOUND TWO OF MY OWN FAILURES BEFORE IT FOUND ANYTHING ELSE

**An authorised fix was uncommitted.** `retail_lease_knowledge.json` — Step 555's mojibake repair, 35
sequences — was **live in the working tree and in no commit**, and had been since Step 555. Local and
production would have disagreed on the knowledge schema with neither side looking wrong. Committed as
`1f9e9d4`.

**Step 555 had no status file, and its code shipped under Step 557's message.** I staged
`lease_negative_space.py` while committing 557, so the narrowed pattern — 555's central deliverable —
is recorded against another step. Status written and committed as `3d0ac42`, opening with the fact that
it was filed three steps late.

**Neither would have surfaced without a preflight.** That is what the preflight is for, and it is the
second time in this arc it has caught something (Step 553 caught the compression premise).

---

# 1. PREFLIGHT

```
git fetch origin   -> nothing incoming
git status -sb     -> ## main...origin/main [ahead 6]
tests against HEAD -> 445 passed, 3 skipped, 12 subtests
```

**Deployable files across the six commits — four, and no flag file among them:**

```
557       cam/adapters/lease_review/lease_coverage.py
          cam/adapters/lease_review/lease_negative_space.py
          cam/adapters/lease_review/tests/test_557_placeholder_scope.py
555-fix   cam/adapters/lease_review/schemas/retail_lease_knowledge.json
553, 554, 556, 555-status  shipped no code.
```

```
forbidden paths (results/, _*_results/, .env, driveupload, keys, creds) : NONE
secret scan (sk-/xai-/AIza/ghp_/PRIVATE KEY/Bearer/aws_secret/access code) : NO MATCHES
```

*The single scan hit is my own Step-553 status file containing the words "secret scan".*

## The six flags — no flag line appears in the diff at all

```
SPAN_EVIDENCE_ENABLED       = True                                lease_coverage.py:52
SPAN_EVIDENCE_LPS           = {"LP-07","LP-12","LP-17","LP-27"}   lease_coverage.py:53
SECTION_EXPANDED_SPAN_LPS   = set()                               lease_coverage.py:77
ENTAILMENT_TEST_LPS         = {"LP-27"}                           lease_coverage_305.py:284
GATE_ABORT_RETURNS_DEGRADED = True                                lease_adapter.py:173
DEGRADABLE_APPLICABILITY    = {"not_applicable","unclear"}        lease_adapter.py:194
```

**Identical to Step 548.** `lease_coverage.py` is in the diff but the flag lines moved by one only
because an import was added above them.

---

# 2. WHAT CHANGES FOR A USER

- **The narrowed `_RESERVED_PATTERN`** — 92 corpus matches to 38. **55 false positives eliminated, 0
  true positives lost.** All 48 substantive `reserved` matches (*"Rent reserved hereunder"*, *"reserved
  parking"*, *"AS RESERVED BY … IN DEED RECORDED"*) stop firing; the one genuine bracketed
  `[Reserved]` still does.
- **Negative-space signals now reach the panel as evidence** where prose sits beside the placeholder,
  instead of short-circuiting past it. The prompt block is
  *"NEGATIVE SPACE CANDIDATES (candidate evidence only — verify against lease text)"*.
- **15 of 38 placeholders corpus-wide now reach the panel; 23 still short-circuit.**
- **solidpower LP-29 stops asserting an entry right the lease denies — at the verdict layer.** §4 is
  where that sentence needs its qualification.
- **Not in the brief's list: 35 mojibake sequences repaired.** LP-29's `risk_if_missing` reached the
  report as *"for any purpose ג€” disrupting tenant's business operations"*. Confirmed gone from every
  exposure string in the deployed run.

# 3. WHAT DOES NOT CHANGE

- **Genuine absences still short-circuit** — divall LP-02 and LP-21, verified on a live run:
  `broken_xref`, `not_assessed`, 0 elements, unchanged.
- **The pattern still detects all 38 true placeholders.** TP=38 before and after.
- **No schema string was hedged.** Step 556 established that is a separate decision and only a partial
  remedy.
- **No verdict semantics moved.** `derive_lp_state` untouched, no `coverage_state` added, the six flags
  unchanged.

---

# 4. THE DEPLOYED RUN — THE VERDICT HOLDS, THE HEADLINE DOES NOT

```
job lease_review_20260904_123242_956ec9   run_quality: clean   degraded: False
calls=91   elapsed=1730.39s
broken_xref LPs: []                       <- was ['LP-07', 'LP-29']
```

## LP-29 — verdict, materiality, elements: all correct in production

```
state        : covered_unfavorable
status       : assessed        method=step_305_per_element
MATERIALITY  : high            requires_attention=True
display      : UNFAVORABLE TERMS   bucket=needs_attention
elements     : 5/6 present, 0 unresolved

   LP-29.notice_period                   explicitly_present
   LP-29.emergency_entry                 explicitly_present
   LP-29.minimize_interference           explicitly_present
   LP-29.permitted_purposes              explicitly_present
   LP-29.tenant_representative_present   missing
   LP-29.entry_frequency_timing          explicitly_present
```

**Six of six element verdicts correct against the lease, in production, third run running.** The
provision that carried 0 element verdicts and `not_assessed` now carries a judged verdict at **high**
materiality in the **needs_attention** bucket.

## But the headline is false again, by a route neither 555 nor 557 touches

```
HEADLINE  : "Landlord access terms undefined"
statement : "Landlord access terms undefined; landlord may enter without notice at any time,
             disrupting business operations, exposing confidential information, and interfering
             with customers"
source    : schema_fallback          reason_code: unfavorable_provision
```

**The lease says the opposite**, verbatim: *"after giving Tenant reasonable notice thereof"*,
*"at all reasonable hours"*, *"with one (1) days prior notice"*, under
*"Provided that such actions shall not materially interfere with Tenant's use and quiet enjoyment"*.

**This is a THIRD path to the same false sentence.** Both local runs produced correct model-written
prose — *"Emergency access without notice"* (555A) and *"Landlord access can disrupt operations"*
(557), both `source=model`. In production the GPT-5.5 call for this one LP failed and
`_build_model_exposure`'s `except` branch returned the canned schema string:

```
exposure_source across the run: {'schema': 26, 'model': 5, 'schema_fallback': 1}
which LPs fell back: LP-29 only.
```

The canned `exposure_statement` for LP-29, verbatim from the schema:

> *"Landlord access terms undefined; landlord may enter without notice at any time, disrupting business
> operations, exposing confidential information, and interfering with customers"*

**Three routes to this sentence are now on the record:**

| # | route | state | status |
|---|---|---|---|
| 1 | `risk_if_missing` via the `broken_xref` short-circuit | `broken_xref` | **fixed** — Steps 555, 557 |
| 2 | `exposure_statement` via `partial`-with-a-gap | `partial` | **unfixed** — Step 549 Defect 2, Step 557 §4 |
| 3 | `exposure_statement` via `schema_fallback` on a model-call failure | any `_MODEL_STATES` | **new, found here** |

**Route 3 is the one this run exposes and it is not a regression** — the fallback has always existed.
What changed is that LP-29 now reaches a state that uses the model path at all, so the fallback became
reachable for it. **The verdict layer is fixed; the prose layer has a canned string that is wrong about
this document and three ways to reach it.**

**`fallback_events: 0`** — the exposure-stage model failure is **not** recorded as a fallback event.
The only trace is `exposure_source: schema_fallback` on the item. A run-level reader would not know it
happened.

## LP-07 — unchanged and correct

```
partial   assessed   materiality=low   4/6 present
   proportionate_share_calculation explicitly_present    cam_cap             missing
   included_expense_categories     explicitly_present    tenant_audit_rights missing
   excluded_expense_categories     explicitly_present    reconciliation_timeline explicitly_present
headline: "CAM exposure uncapped and unauditable"   (source=schema)
```

**Accurate — that is exactly what the two missing elements say.**

---

# 5. THE PUSH

```
To https://github.com/zvido1/cam.git
   134f01f..3d0ac42  main -> main
## main...origin/main        unpushed: 0

local tags:  stage2-sanction-431-ef1a7af7  stage2-sanction-452-e0b985b4
remote tags: 0
```

**`--follow-tags` not used. Both sanction tags remain local.**

---

# WHAT IS NOT ESTABLISHED

- **The LP-29 headline is still false in production.** §4, route 3. The brief asked me to confirm the
  fix holds; **the verdict fix holds and the prose fix does not exist yet.** I am not reporting this
  step as a clean success.
- **Why the GPT-5.5 exposure call failed is unknown.** `_build_model_exposure` swallows the exception
  into a `logger.warning` and returns the fallback; the reason is not persisted on the result, and
  `fallback_events` does not record exposure-stage failures at all.
- **One deployed run.** LP-29's six correct verdicts are now three observations (555A local, 557 local,
  558 production) but the `schema_fallback` is one, so how often route 3 fires is unmeasured.
- **ex6-4 and Atlas were not re-run** under the new pattern or the new scope rule. The 15 released
  placeholders elsewhere in the corpus remain untested end to end.
- **Steps 555 and 557 were both verified on solidpower and divall only.** No third document has
  exercised either change.
- **The mojibake fix was verified by absence** (`no ג in any exposure string`), not by reading all
  35 repaired strings in a rendered artefact.
