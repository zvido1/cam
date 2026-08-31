# Step 503 — google-genai 2.20.0 verified on the real extraction path. No SDK-attributable difference.

**Date:** 2026-08-30 · **Instruction:** `build_log/503_chat_instruction.md`
**Panel verified intact before spending. Tests 369 passed against HEAD.**

---

# 1. EXTRACTION ON google-genai 2.20.0 — PASSES

```
extractor: gemini-3.1-pro-preview   extractor_fallback_used=False
coverage entries: 32   (498: 32)    issue-area ID sets IDENTICAL
element verdicts: 202  (498: 202)   evaluator records: 606 (498: 606)
source_document_hash MATCHES 498 exactly
completeness_failed_lps=[]   gate_attempts=1   calls=98   elapsed=857.7s
extraction succeeded in 104.1s on the PRIMARY, no fallback
```

**Schema shape:** every coverage entry carries the required keys except `element_verdicts` on
**LP-23 and LP-31 — and 498 is missing exactly the same key on exactly the same two LPs.** Those are
the `unclear` applicability short-circuits (Step 478), which produce zero element verdicts by design.
**Not an SDK effect: identical before and after.**

**Panel census:** `A claude-sonnet-4-6 202 · B gpt-5.5 202 · C grok-4.3 202`, 0 stubs,
0 contradictions, 0 fallback events, `run_degraded=False`.

## 1.1 Is any difference attributable to the SDK?

**No.** 12 of 32 LPs differ from 498 on `(state, found, missing)` — inside the 13-of-32 variance floor
established across six prior Atlas runs. The decisive evidence is that **the seam LPs' evidence is
byte-identical to 498**:

| LP | 503 | 498 |
|---|---|---|
| **LP-07** | partial 5/1, 5 spans, **1635 chars** | partial 5/1, 5 spans, **1635 chars** |
| **LP-16** | partial 3/2, 0 spans, **388 chars** | partial 3/2, 0 spans, **388 chars** |
| **LP-27** | partial 8/1, **9 spans, 1243 chars** | partial 8/1, **9 spans, 1243 chars** |
| LP-12 | review_needed 1/1, 13 spans, 2605 | review_needed 0/0, 13 spans, 2605 |
| LP-17 | **covered 6/0**, 5 spans, 1176 | partial 5/0, 5 spans, 1176 |

**LP-07's 1,635 chars is the distinctive figure** — 491/494/496 all produced 1,957. 503 reproducing
498's 1,635 exactly, along with LP-27's 9 spans / 1,243 chars, means extraction assigned the same
buckets under the new SDK. The differing verdicts are evaluator variance on identical evidence.

## 1.2 A correction to Step 500

Step 500 recorded LP-17 moving to `covered 6/0` and I noted *"the one verdict that moved is on the run
where the panel differed"* — implying the substituted panel. **503 produces `covered 6/0` on a fully
intact panel.** So LP-17 at 6/0 is run-to-run variance, not a panel effect. **The Step-500 hedge was
correctly hedged but the implication was wrong, and this retires it.**

## 1.3 A correction to my own interim report this step

I said mid-run that the gate's `claude-sonnet-4-20250514` 404 had disappeared under the new SDK.
**It has not.** `grep -c "not_found_error"` returns **1** for this run. My `grep -E` window simply did
not include the `lease_gate` line, and I read absence-from-my-filter as absence-from-the-log. **The
dead model id is unchanged and still unfixed.**

# 2. PREFLIGHT

```
origin/main: 691a296 (Step 501 -- already pushed, so the anthropic pin is already live)
unpushed: 1  ->  0d79d15 "502: bound every dependency, detect env drift, stop the classifier lying"
deployable paths in it: lease_coverage_305.py, test_502_environment_matches_requirements.py,
                        requirements.txt
tracked files differing from HEAD: 0   (so tests below ARE against HEAD)
tests: 369 passed, 12 subtests
tags: 2 local, 0 on remote
```

**All six flags confirmed from HEAD:**

```
SPAN_EVIDENCE_ENABLED          True
SPAN_EVIDENCE_LPS              {"LP-07", "LP-12", "LP-17", "LP-27"}
SECTION_EXPANDED_SPAN_LPS      set()
ENTAILMENT_TEST_LPS            {"LP-27"}
GATE_ABORT_RETURNS_DEGRADED    True
DEGRADABLE_APPLICABILITY       {"not_applicable", "unclear"}
```

**All thirteen dependencies bounded in HEAD.** Nothing unexpected; no HALT warranted.

# 3. DEPLOYED RUN — THE FIRST ON THE ACTUAL FROZEN PANEL

**Pushed `691a296..969453e`, branch only, no tags. 0 unpushed, 0 tags on remote.**
Job `lease_review_20260831_005604_2c7470`, completed in 1,248s wall.

## 3.1 Role A serves claude-sonnet-4-6

```
role A: {"claude-sonnet-4-6": 202}   fallback=0
role B: {"gpt-5.5": 202}             fallback=0
role C: {"grok-4.3": 202}            fallback=0

stubs=0  contradictions=0  fallback_events=0
run_degraded=False  degraded_reason=None
calls=97  elapsed=762.0s  extractor=gemini-3.1-pro-preview
```

**This is the first deployed run in this project's history on the specified three-model panel.**
Every prior deployed run — Step 487 atlas_1, Step 487 atlas_2, Step 500 — had role A served by
`gemini-2.5-pro` because `anthropic` 1.x rejected `temperature`. **The pin fixed it in production.**

## 3.2 The disclosure fix's NEGATIVE case — silent, correctly

```
GET /api/jobs/{id}:
   run_quality                  'clean'
   panel_substituted            False
   panel_fallback_noted         False
   report_incomplete            False
   invalid_for_legal_analysis   False

panel_substitution_lines(): None
incomplete_report_lines():  None
```

**`run_quality` is `clean` — the first deployed run ever to report it.** Step 500 fired the banner on
a substituted panel; this proves the other half: **on an intact panel it says nothing.** A disclosure
that always fires is worthless, and until now the negative case had never been observed deployed.

## 3.3 Seam LPs — deployed now matches local

| LP | local 503 | **DEPLOYED 503** | DEPLOYED 500 |
|---|---|---|---|
| **LP-07** | 5/1, 5 spans, 1635 | **5/1, 5 spans, 1635** | 5/1, 5 spans, 1635 |
| **LP-16** | 3/2, 0 spans, 388 | **3/2, 0 spans, 388** | 3/2, 0 spans, 388 |
| **LP-27** | 8/1, 9 spans, 1243 | **8/1, 9 spans, 1243** | 8/1, 9 spans, 1243 |
| LP-12 | review_needed 1/1 | review_needed 0/0 | review_needed 0/0 |
| LP-17 | covered 6/0 | **partial 5/0** | covered 6/0 |

**LP-07, LP-16 and LP-27 are byte-identical across local and both deployed runs.**

**LP-17 lands at `partial 5/0` here**, where local 503 and deployed 500 both gave `covered 6/0`. That
is the third distinct value for LP-17 across runs (5/1, 5/0, 6/0) on identical evidence, and it
**further confirms §1.2**: the 6/0 outcome tracks neither the panel nor the environment. It is
evaluator variance, and this run — the only one on the correct panel — produced the *lower* value.

## 3.4 Cost

97 calls / 762.0s pipeline. Deployed 500 was 98 / 839.9s; local runs 96–99 / 743–858s. Unremarkable.

---

## WHAT IS NOT ESTABLISHED

- **One deployed run on the correct panel.** Not a rate. Whether Anthropic stays healthy in
  production across many runs is unmeasured.
- **divall deployed.** Not attempted this step. It failed at Step 500 on LP-07 with no retry, and the
  deployed app still does not retry a gate abort.
- **Whether `client_error` ever fires deployed.** The classifier fix shipped in this deploy and has no
  live instance — by construction, since the condition it names was just repaired.
- **The gate's dead model id** (`claude-sonnet-4-20250514`) is unchanged and still 404s on every run.
- **The Step-500 failed-job gap** — a failed job still carries none of the Step-498 fields — is
  unfixed.
