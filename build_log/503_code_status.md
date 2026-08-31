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
