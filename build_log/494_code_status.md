# Step 494 — LP-17 seamed: fixed on both fixtures. divall still aborts, on LP-16 alone.

**Date:** 2026-08-30 · **Instruction:** `build_log/494_chat_instruction.md`
**One line changed.** LP-16 untouched, verified. **Tests 359 passed.** Panel verified intact before
spending. **Not deployed.**
**Spend: 1 divall run (4 aborted attempts) + 1 Atlas run + 1 standalone extraction + 3 probe calls.**

---

## THE CHANGE — one line

`cam/adapters/lease_review/lease_coverage.py:45-52`:

```python
SPAN_EVIDENCE_LPS = {"LP-07", "LP-12", "LP-17", "LP-27"}
```

with a comment recording the Step-493 evidence behind it. **`'LP-16' in SPAN_EVIDENCE_LPS → False`,
verified after the edit.** `git diff --stat`: 1 file, 7 insertions, 1 deletion.

---

# 1. DOES divall COMPLETE? — No. LP-17 is fixed; LP-16 alone now blocks it.

**LP-17 went from 4/4 failures to 0/4.** From the persisted abort history:

| LP | Step 492 | **Step 494** |
|---|---|---|
| **LP-17** | **4 / 4** | **0 / 4 — seam-exempt on every attempt** |
| **LP-16** | 4 / 4 | **4 / 4 — unchanged** |
| LP-07 | 2 / 4 | 1 / 4 — still shape-variant |

```
attempt 1: failed_lps=['LP-07', 'LP-16']    seam_exempt=['LP-12', 'LP-17']
attempt 2: failed_lps=['LP-16']             seam_exempt=['LP-17']
attempt 3: failed_lps=['LP-16']             seam_exempt=['LP-17']
attempt 4: failed_lps=['LP-16']             seam_exempt=['LP-17']
```

**LP-17 never appears in `must_abort` again.** The one-line change did exactly what Step 493 predicted,
and the gate's seam exemption fired on all four independent extraction draws.

**Three of four attempts now fail on LP-16 and nothing else.** divall is one LP away from completing,
and that LP is the applicability defect the brief deliberately left alone.

# 2. LP-17's COVERAGE ENTRY ON divall

**There is none — the run aborted, so no coverage stage ran.**

What *is* established: LP-17 obtained span evidence on all four attempts (`seam_exempt=['LP-17']` is
emitted only when elicitation produced verified spans — the Step-484 production-not-membership rule).
**Whether the three clauses reach the evaluators cannot be answered until a divall run completes**,
which requires LP-16 resolved.

Step 493 measured the elicitation output directly: 3 verified spans, 1,056 chars, all element-relevant.
That stands. **It is not the same as observing them in a coverage entry, and I am not reporting it as
if it were.**

# 3. WHICH BUCKET TOOK LP-17's CONTENT — both 421C failure modes, on one LP

**Method note:** the divall run again persisted no extraction — see §Harness below — so this is a
**standalone extraction, a fresh draw, not one of the four aborted attempts.** Persisted to
`build_log/runs/494_divall-extraction-probe_20260830_171938/extraction_full.json`. Needles verified
unique in the canonical text, whitespace-normalised.

```
governing_law §14.13     *** DROPPED ENTIRELY -- in no bucket ***
atty_fees A  @27675      *** DROPPED ENTIRELY -- in no bucket ***
atty_fees B  @44589      *** MIS-BUCKETED -> ['LP-11'] ***
```

**Both 421C failure modes, on the same LP, in the same extraction.** Two clauses vanish from the
output entirely; the third is absorbed exclusively by **LP-11 (Default & Remedies)** — a plausible
topical neighbour, since @44589 sits inside a default-and-cure clause. That is destructive exclusive
assignment and outright loss side by side.

**This is the question Step 493 could not reach.** The answer is not "one or the other."

## 3.1 A second finding: `AMBIGUOUS`, not `NOT_APPLICABLE`

```
LP-16 bucket: status='AMBIGUOUS'  tenant_text=0 chars
LP-17 bucket: status='AMBIGUOUS'  tenant_text=0 chars
buckets with content: 26 of 33
```

**This is precisely what makes the gate fire.** The 422C rule is `fail_missing` = empty `tenant_text`
**and not `NOT_APPLICABLE`. `AMBIGUOUS` fails that test.**

*[my reading, flagged]* **LP-16 is therefore resolvable at either of two layers** — applicability
returning `not_applicable` (Step 493's diagnosis), or extraction returning `NOT_APPLICABLE` instead of
`AMBIGUOUS` for a provision the document does not contain. Both layers currently assert "this should
be here and I could not find it" about a parking provision that does not exist. **Not proposing
either; recording that the choice exists.**

# 4. ATLAS — the baseline did not move

| LP | 491_r01 | 491_r02 | 491_r03 | **494_r01** |
|---|---|---|---|---|
| **LP-07** | partial 5/1, 5 spans, 1957 | same | same | **partial 5/1, 5 spans, 1957** |
| **LP-27** | partial 8/1, 7 spans | 8/1, 9 spans | 8/1, 7 spans | **partial 8/1, 8 spans** |
| **LP-17** | partial 5/1, **0 spans**, 958 | 5/1, 0 spans, 958 | 5/0, 0 spans, 1088 | **partial 5/0, 5 spans, 1176** |
| LP-12 | review_needed 1/0 | 1/1 | 0/0 | review_needed 0/1 |

**LP-07 is byte-identical across all four runs.** LP-27's found list is identical across all four.

**LP-17 is the one to read carefully.** Its evidence source changed exactly as intended — `spans 0 →
5`, `tenant_text 958 → 1176 chars` — while **its found count stayed at 5**, and its `5/0` split
matches 491_r03 exactly. **The seam changed the provenance of LP-17's evidence without changing the
answer.** That is the outcome you want from a provenance fix.

**LP-12's `0/1` differs from all three 491 runs**, but only in the missing count, with 13 spans and
2,605 chars unchanged. Consistent with the 0–1 instability already reported at Step 491.

## The "7 of 32 outside the envelope" number is not a finding

A mechanical comparison says 7 of 32 LPs produced a `(state, found, missing)` signature not seen in
the three 491 runs. **Three runs do not define an envelope.** With 13 of 32 LPs varying run to run, a
fourth run necessarily produces unseen combinations. **This number is expected arithmetic, not
evidence that LP-17's seaming perturbed anything** — and note LP-17 itself is *not* in that list.

# 5. PANEL CENSUS

Verified before spending: `A anthropic:claude-sonnet-4-6 1.89s · B openai:gpt-5.5 3.52s ·
C xai:grok-4.3 1.50s — PANEL INTACT`.

Atlas run census, computed automatically at write time:

```
records=606  stubs=0  contradictions=0  fallback_events=0  degraded=False
   role A: {'claude-sonnet-4-6': 202}  fallback=0
   role B: {'gpt-5.5': 202}            fallback=0
   role C: {'grok-4.3': 202}           fallback=0
```

**No census for divall** — it aborted before the evaluator layer, so no evaluator records exist.

# 6. COST vs the Step-491 baseline

| run | calls | pipeline elapsed |
|---|---|---|
| 491 r01 | 96 | 745.6s |
| 491 r02 | 99 | 743.5s |
| 491 r03 | 97 | 787.5s |
| **494 Atlas** | **97** | **794.8s** |

**Squarely inside the baseline range.** Seaming a fourth LP adds ~1 elicitation call and it is
invisible against the 96–99 spread.

**divall:** 927.2s wall across four aborted attempts, `api_calls_total` unavailable (no result).
Plus the standalone extraction: 127.3s, 1 call, `gemini-3.1-pro-preview`.

---

## THE HARNESS: my Step-492 fix was incomplete

The brief said *"This persists, so the extraction output survives."* **It does not.**

The Step-492 fix worked as far as it went — `run_01_gate_aborts.json` (2,492 bytes) captured all four
attempts, its first real exercise, and it is the source of the §1 table. **But the run directory still
holds no extraction output**, because the gate raises before any result object exists and the
extraction lives inside that unbuilt result.

**I captured the decision and not the evidence the decision was made on.** Item 3 was answerable only
by spending a separate extraction call.

**Not fixed here.** Persisting the rejected extraction requires the *adapter* to surface it on the
abort path, which is a pipeline change and outside this step. Recorded as an open item.

## OPEN ITEMS

1. **LP-16.** The sole remaining divall blocker. Resolvable at the applicability layer or the
   extraction-status layer (§3.1). Needs its own measurement per Step 481.
2. **Persist the rejected extraction on gate abort.** Requires an adapter change.
3. **LP-07's divall elicitation still falls back on every attempt** — 4/4 here, 4/4 at Step 492.
   Never investigated. It is shape-variant as an *abort* cause only because its extraction bucket is
   sometimes non-empty.
4. The `ARTICLE\nXI` locator newline (Steps 472/479) and the dead `claude-sonnet-4-20250514` gate
   model (Step 491) remain unfixed.

## WHAT IS NOT ESTABLISHED

- **Whether divall completes with LP-16 resolved.** Never observed. LP-07 failed 1 of 4 attempts here,
  so a completion is not guaranteed even then.
- **LP-17's divall coverage entry, verdict, or whether the three clauses reach the evaluators.**
  Requires a completing run.
- **Whether the drop/mis-bucket pattern in §3 is stable.** One extraction draw. The four aborted
  attempts would have given four more, had they been persisted.
- **Whether LP-17's Atlas `5/0` is the seam or run-to-run variance.** 491_r03 produced `5/0` from the
  *bucket* path, so both paths reach it. One seamed run cannot separate them.
- **Deployed behaviour.** All local.
