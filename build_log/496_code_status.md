# Step 496 — C5 adopted. divall COMPLETES for the first time. Atlas held.

**Date:** 2026-08-30 · **Instruction:** `build_log/496_chat_instruction.md`
**One array changed.** Extraction status semantics untouched. **Tests 359 passed.** Panel verified
intact before spending. **Not deployed.**
**Spend: divall 74 calls + Atlas 98 calls + 3 probe calls.**

---

## THE CHANGE

`cam/adapters/lease_review/schemas/retail_lease_knowledge.json`, LP-16 `activation_clues` 8 → 6:

```json
"activation_clues": [
  "parking spaces", "parking rights", "garage",
  "surface parking", "unreserved parking", "reserved parking"
]
```

Removed: `parking`, `parking area`, `spaces`, `parking lot` — the four responsible for every false
positive. **`exclusion_clues` unchanged.** C3/C4's four never-firing clues **not** adopted.

Verified live across 32 fixtures before spending: **TP=28 FP=0 TN=4 FN=0** — exactly the Step-495
prediction.

---

# 1. divall — IT COMPLETES

**First completion of divall under any configuration in this arc.**

```
attempt 1  must_abort=['LP-07']  degradable=['LP-16','LP-30','LP-31','LP-32']  seam_exempt=['LP-12','LP-17']
attempt 2  must_abort=[]         ->  COMPLETED
74 calls, 716.4s, 2 attempts, 1 abort
```

**LP-16 moved out of `must_abort` and into `degradable`, exactly as intended.** LP-07 aborted attempt
1 — the shape-variant cause, 1 of 4 at Step 494 — and cleared on attempt 2.

**Abort trajectory for divall:**

| step | config | result |
|---|---|---|
| 482 | pre-seam | 4/4 abort, LP-12 every time |
| 492 | LP-12 seamed | 4/4 abort — LP-16 + LP-17 deterministic |
| 494 | + LP-17 seamed | 4/4 abort — LP-16 alone |
| **496** | **+ LP-16 clues narrowed** | **COMPLETES on attempt 2** |

# 2. LP-16's ENTRY ON divall — and my prediction was wrong

**I predicted the banner would name LP-16. It does not.**

```
LP-16: applicability='unclear'   coverage_state='not_applicable'   requires_attention=False
       tenant_text=0 chars       element_verdicts=0                found=0 missing=0
       evidence_summary="Cannot determine whether this issue area applies;
                         defaulting to 'not_applicable'"
```

I flagged before the run that `is_applicable()` returns **`unclear`**, not `not_applicable`, because
LP-16 is `conditional` and `lease_knowledge.py:155-160` reserves `not_applicable` for `optional`.
That part was right. **What I got wrong was the consequence:** `default_when_unclear` resolves to
`not_applicable` at the coverage layer, so **the user-visible state is exactly what the brief
specified** — `not_applicable`, zero element verdicts, no attention flag. The `unclear`/
`not_applicable` distinction lives only inside `is_applicable()` and does not reach the report.

**Does the banner name it? No.** The run is degraded, but on other LPs:

```
run_degraded=True  degraded_reason='extraction_completeness_failed'
invalid_for_legal_analysis=True
extraction_completeness_failed_lps=['LP-30','LP-31','LP-32']
summary REPORT_INCOMPLETE=True
summary issue_areas_with_no_evidence=['LP-30','LP-31','LP-32']

degraded_statement: "INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS. Extraction returned no text
for 3 required issue area(s): LP-30, LP-31, LP-32..."
```

**LP-30/31/32 are a pre-existing condition, not caused by this change** — all three were already
`unclear`/degradable in the Step-492 and Step-494 gate logs. Each is
`extraction_status='AMBIGUOUS', tenant_text_len=0, applicability='unclear'`.

**So divall now completes and produces a report marked INCOMPLETE naming three other issue areas.**
That is an improvement over a hard abort and is not a clean pass.

## 2.1 LP-17 on divall — the Step-494 open item, answered

**First LP-17 coverage entry ever on this fixture.** All three clauses reached the evaluators,
verified by needle against `tenant_text`:

```
governing_law §14.13   in tenant_text: True
atty_fees A  @27675    in tenant_text: True
atty_fees B  @44589    in tenant_text: True
```

| element | verdict | confidence |
|---|---|---|
| `governing_law` | **explicitly_present** | high |
| `dispute_mechanism` | missing | high |
| `jury_trial_waiver` | missing | high |
| `venue_jurisdiction` | disputed | low |
| `attorney_fee_allocation` | disputed | low |
| `claims_time_limit` | disputed | low |

**The panel got the two verifiable facts right.** §14.13 found; arbitration/mediation and jury waiver
correctly reported missing at high confidence — matching Step 493's census (`arbitrat` 0, `mediation`
0, `jury trial` 0).

*[observation, not a claim]* `attorney_fee_allocation` is `disputed` at low confidence despite both
fee clauses being present in the evidence. That is panel disagreement, not an evidence gap. Not
investigated.

# 3. LP-16 ON ATLAS — did not flip, byte-identical across five runs

```
491_r01  partial 3/2  0 spans  388 chars  applicable
491_r02  partial 3/2  0 spans  388 chars  applicable
491_r03  partial 3/2  0 spans  388 chars  applicable
494_r01  partial 3/2  0 spans  388 chars  applicable
496_r01  partial 3/2  0 spans  388 chars  applicable
```

`elements_found` identical on all five: *"Parking space allocation is defined (count or ratio per
square foot)"*, *"Reserved vs unreserved parking designation is stated"*, *"Exclusive or protected
parking for tenant is addressed"*.

**The narrowed clue list preserved Atlas's true positive exactly.** Atlas's parking article contains
`parking spaces`, which is C5's highest-coverage clue.

# 4. SEAM LPs ACROSS ATLAS 491 / 494 / 496

| LP | 491 ×3 | 494 | **496** | reading |
|---|---|---|---|---|
| **LP-07** | 5/1, 5 spans, 1957 ×3 | same | **same** | **byte-identical, 5 runs** |
| **LP-27** | 8/1 (7/9/7 spans) | 8/1, 8 spans | **8/1, 7 spans** | found list identical, 5 runs |
| **LP-17** | 5/1, 5/1, 5/0 — **0 spans** | 5/0, **5 spans**, 1176 | **5/0, 5 spans, 1176** | seam stable across both runs |
| LP-12 | 1/0, 1/1, 0/0 | 0/1 | **partial 2/0** | see below |

**LP-12 reached `partial` with 2 found for the first time on Atlas** — previously `review_needed` in
all four prior runs, with found counts 1, 1, 0, 0. Evidence unchanged at 13 spans / 2,605 chars.

**I am not attributing this to the LP-16 change.** LP-16's clue list cannot affect LP-12's evidence,
which is byte-identical. Step 491 recorded LP-12's element count as unstable at 0–1 on identical
evidence; this run puts it at 2. **The honest statement is that the instability range is wider than
previously measured — 0 to 2 — not that anything improved.**

# 5. PANEL CENSUS, CALLS, ELAPSED

Verified before spending: `A claude-sonnet-4-6 1.83s · B gpt-5.5 2.71s · C grok-4.3 1.73s —
PANEL INTACT`.

| run | calls | elapsed | census |
|---|---|---|---|
| **divall** | 74 | 716.4s | 0 stubs, 0 contradictions |
| **Atlas** | 98 | 750.4s | 0 stubs, 0 contradictions, **1 fallback event** |

Atlas role census: **A `claude-sonnet-4-6` 191 + `claude-haiku-4-5-20251001` 11 · B `gpt-5.5` 202 ·
C `grok-4.3` 202.**

## 5.1 A real fallback, correctly labelled — the contrast with Step 487

```json
{"event_type": "fallback", "lp_id": "LP-22", "role": "A",
 "requested_model": "claude-sonnet-4-6", "actual_model": "claude-haiku-4-5-20251001",
 "fallback_reason": "malformed_response", "fallback_class": "transient",
 "same_provider_retry_attempted": true, "same_provider_retry_succeeded": true}
```

One LP, 11 element records, role A's **declared own-chain fallback**. Every one of the 11 carries
`is_fallback=true` and `actual_model='claude-haiku-4-5-20251001'`. **Zero stubs, zero provenance
contradictions.**

**This is what the provenance machinery looks like when it works** — and the direct contrast with
Step 487's `all_failed` stubs, which named a model that served nothing. The defect there was the
total-failure path, not the fallback path.

**But `invalid_for_legal_analysis=False`, so the banner predicate is False and nothing tells the user
role A was substituted on LP-22.** Step 488 §2.4 reconfirmed on a fresh, benign, real instance.
**Open item unchanged.**

Cost is unremarkable: Atlas 98 calls / 750.4s sits inside the 96–99 / 743–795s baseline.

---

## WHAT THIS RESOLVES

**The divall abort chain is closed.** Every deterministic cause identified across Steps 492–495 is now
addressed: LP-12 by the seam (484), LP-17 by the seam (494), LP-16 by the clue list (496). What
remains is LP-07, which is shape-variant and cleared on a retry.

## WHAT IS NOT ESTABLISHED

- **divall's completion rate.** **One completion in one run, on the second attempt.** LP-07 failed 1
  of 4 attempts at Step 494 and 1 of 2 here. A single completion is not a rate — the Step-491 bound
  applies with more force here, not less.
- **Whether LP-30/31/32 are genuinely absent from divall or mis-extracted.** Not investigated. They
  are `AMBIGUOUS` with `applicability='unclear'` — the same conflation Step 495 §C.3 identified, and
  the same two possibilities as LP-16 versus LP-17.
- **Whether C5 generalises beyond the 32 fixtures it was fitted to.** Unchanged from Step 495. The
  effective real-lease sample is 10.
- **Whether divall's `partial`/`disputed` verdicts are correct.** The run completing is not the same
  as the run being right. LP-17's three disputed elements were not adjudicated.
- **Deployed behaviour.** All local. divall has still never completed deployed.
- **LP-12's Atlas instability.** Now measured at 0–2 across five runs on byte-identical evidence.
  Unexplained.
