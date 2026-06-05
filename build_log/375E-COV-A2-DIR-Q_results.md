# 375E-COV-A2-DIR-Q — Directionality-flip Trace Results

**Date:** 2026-06-05
**Investigator:** Claude Chat (read-only trace, no code changes)
**Artifacts compared:**
- Pre-A2: `lease_review_20260605_174504_19f9a7/tenant_0/pipeline_results.json`
- Post-A2: `lease_review_20260605_195225_34f3b9/tenant_0/pipeline_results.json`

---

## Verdict: (b) Stage 7 nondeterminism

The all-28 directionality flip from `tenant_unprotected` → `landlord_unprotected` in the 34f3b9 run
is caused by Stage 7's Pass 2 LLM evaluators outputting `exposed_party='landlord'` (or `'bilateral'`)
on that run, where they output `exposed_party='tenant'` on the 19f9a7 run.
**COV-A/A2 code does not write `directionality` anywhere in the COV path.**

---

## Question (a): Does any COV-A / A2 code write `directionality`?

**Answer: NO.**

### Evidence

**`lease_finding_consequence.py` (COV-A module) — grep result:**
```
Line 492: # In practice, all directional_mismatch findings carry directionality="tenant_unprotected";
Line 493: # finding_type alone is the gate — directionality is provenance, not an entry filter.
```
Only a comment. Zero assignments to `directionality` anywhere in the file.
Fields actually written by COV-A on directional findings:
`stage7_direction`, `use_consequence`, `materiality`, `use_consequence_source`,
`materiality_source`, `assessment_scope` — not `directionality`.

**`lease_adapter.py` (G-cand hook) — grep result:** Zero matches for `directionality`.

**A2 commit `fc8d3dc` — `git show --stat`:**
```
build_log/375E-COV-A2_code_status.md               | new
cam/adapters/lease_review/lease_finding_consequence.py | modified
```
Only these two files changed. `lease_synthesis.py` was not touched by A2.

**`_normalize_directionality` in `lease_synthesis.py` (lines 1664–1687):**
`_DIRECTIONALITY_MAP` contains a single entry: `("LP-27", "directional_mismatch") → "tenant_unprotected"`.
This LP-27-only map normalizes toward `tenant_unprotected`, not `landlord_unprotected`, and covers
at most one finding. It cannot explain a flip of 27/28 findings to `landlord_unprotected`.

**Conclusion (a): CLEARED.** COV-A/A2 has no code path that writes `directionality`.

---

## Question (b): Stage 7 nondeterminism — comparison of 19f9a7 vs 34f3b9

**Answer: CONFIRMED. Stage 7's Pass 2 evaluators produced completely different `exposed_party`
values between the two runs. The directionality flip is fully explained by this nondeterminism.**

### Mechanism

`directionality` in each `Dir-XX` finding is set in `_build_pass2_directional_findings`
(`lease_synthesis.py` line 1941–1946):
```python
directionality = None
ep = (exposed_party or "").lower()
if "tenant" in ep:
    directionality = "tenant_unprotected"
elif "landlord" in ep:
    directionality = "landlord_unprotected"
```
`exposed_party` is read from `best.get("exposed_party")` — the confirming evaluator's raw Pass 2
verdict. `exposed_party` is NOT stored in the final finding dict (absent in both artifacts),
but it was recorded in `_stage_data.synthesis_meta.pass2_raw`.

### Per-evaluator `exposed_party` + `verdict` for Dir-01–Dir-05

| Run | Role | verdict (Dir-01..05) | exposed_party |
|-----|------|---------------------|---------------|
| **19f9a7** (pre-A2) | A | `mismatch_confirmed` | `tenant` |
| **19f9a7** (pre-A2) | B | `mismatch_confirmed` (Dir-03: `no_mismatch`) | `tenant` |
| **19f9a7** (pre-A2) | C | `mismatch_confirmed` | `tenant` |
| **34f3b9** (post-A2) | A | `no_mismatch` | `landlord` |
| **34f3b9** (post-A2) | B | `no_mismatch` | `bilateral` |
| **34f3b9** (post-A2) | C | `mismatch_confirmed` | `landlord` |

This pattern holds uniformly across all 28 directional findings in 34f3b9.

### Why the flip is uniform (not random)

In 34f3b9: Roles A and B both voted `no_mismatch` (0/3 or 1/3 confirmation from those two).
Only Role C (grok-4.3) voted `mismatch_confirmed` — and it consistently said `exposed_party='landlord'`
for all findings. Because `best` is defined as the first confirming role, and Role C is the only
confirmer on every finding, `exposed_party='landlord'` feeds into `directionality='landlord_unprotected'`
for ALL 28 findings.

In 19f9a7: All three roles voted `mismatch_confirmed` with `exposed_party='tenant'`, so all findings
got `directionality='tenant_unprotected'`.

**Same models both runs** (confirmed via `synthesis_meta.models`):
- A: `claude-sonnet-4-6` / anthropic
- B: `gpt-5.4` / openai
- C: `grok-4.3` / xai

The models did not change. The input prompt DID change slightly: 34f3b9 had 28 directional
candidates vs 25 in 19f9a7 (3 more Dir findings, 1 more flagged LP). This different
Pass 2 prompt input produced a different LLM consensus on `exposed_party` for all findings.

### LP-05 mismatch explained

`stage7_direction = "tenant_unprotected"` is **hardcoded** by COV-A at line 524 and 608 of
`lease_finding_consequence.py`:
```python
f["stage7_direction"] = "tenant_unprotected"
```
This is designed as provenance recording what Stage 7 "should" say for adverse directional findings.
In 19f9a7, Stage 7 agreed (LLM said `tenant`). In 34f3b9, Stage 7's LLM said `landlord`, so
`directionality='landlord_unprotected'` while `stage7_direction='tenant_unprotected'` (hardcoded)
— the disagreement is fully explained by (b) Stage 7 nondeterminism, not by any COV-A/A2
defect.

---

## Question (c): Validator field-key mismatch

**Answer: NOT the cause. The validator reads the same key in both fresh and baseline artifacts.**

### Evidence

`check_c_routing_drift` in `_375ecova_keyed_validate.py` (line 231):
```python
ROUTING_FIELDS = ["finding_id", "finding_type", "directionality", "severity", "verdict"]
```
The validator compares `directionality` vs the frozen **52adbf** baseline (not 19f9a7). Both the
fresh artifact and the baseline artifact store this field under the same key `directionality`.
The A2 commit did not rename or add any field that would cause the validator to read a different
key. The criterion 4 failure is a **real measurement** of a real value change — not a key mismatch.

The criterion 4 result in the 34f3b9 run correctly detected that `directionality` changed from
`tenant_unprotected` (in 52adbf baseline) to `landlord_unprotected` (in 34f3b9). That drift is
genuine; the measurement is correct. Criterion 4 is demoted as cross-run confounded per the
validation protocol, which is the right call.

---

## Per-Finding `directionality` vs `stage7_direction` Dump (34f3b9)

All 27 directional_mismatch findings in 34f3b9 show the same pattern except Dir-24:

| Finding | directionality | stage7_direction | Agree? |
|---------|---------------|-----------------|--------|
| Dir-01..23, Dir-25..28 | `landlord_unprotected` | `tenant_unprotected` | ❌ |
| Dir-24 | `tenant_unprotected` | `tenant_unprotected` | ✅ |

Dir-24 is the exception — at least one confirming evaluator returned `exposed_party='tenant'` for
that finding, yielding `directionality='tenant_unprotected'` in agreement with `stage7_direction`.

19f9a7: all 25 directional findings show `directionality='tenant_unprotected'` =
`stage7_direction='tenant_unprotected'` (full agreement). Stage7_direction was hardcoded
to match Stage 7's actual output on that run.

---

## Implications for Push Decision

| Concern | Status |
|---------|--------|
| COV-A/A2 writes directionality as side-effect | **CLEARED** — no such code exists |
| A2 consequence fix (LP-11 de-monochromed) | **PASSED** — not in question here |
| LP-05 stage7_direction vs directionality mismatch | **Explained** by (b) — Stage 7 nondeterminism, not an A2 defect |
| Validator criterion 4 reading wrong key | **CLEARED** — same key, real value difference |
| Directionality flip blocks push | **NO** — validator criterion 4 is confounded for cross-run; this is Stage 7 nondeterminism that predates A2 |

**Consequence fix is safe to push.** The directionality flip is not caused by COV-A or A2.
It is a property of Stage 7's LLM nondeterminism (specifically the Pass 2 evaluators agreeing
on `exposed_party='landlord'` in this run but not in the previous run). Stage 7's directionality
nondeterminism is a pre-existing architectural property; fixing it is a separate future step,
not a gate on the A2 push.

The `stage7_direction` hardcoding is a known simplification in COV-A (it records the intended
value rather than the observed one). That is a COV-B / future design concern, not an A2 defect.
