# Step 482 — LP-12 end to end: the false all-clear is fixed, and it cost divall

**Date:** 2026-08-24 · **Instruction:** `build_log/482_chat_instruction.md`
**RUNS ONLY.** No fix, no schema change, nothing tuned, not deployed.
Config as Step 478 — `SPAN_EVIDENCE_LPS {LP-07, LP-27}`, expansion off, `ENTAILMENT_TEST_LPS {LP-27}`.
Panel verified before spending (`gpt-5.5`, 3.3s, no fallback) and clean throughout (**202/202** role-B
on the completed run).

| fixture | attempts | outcome |
|---|---|---|
| **Atlas** | 1 | **COMPLETED**, 0 aborts, 96 calls, 1005s |
| **divall** | **4** | **ABORTED 4/4 — every attempt on LP-12** |

---

## 1. LP-12's coverage entry — the false all-clear is gone

**Atlas, before → after:**

| | Step 478 | **Step 482** |
|---|---|---|
| applicability | `not_applicable` | **`applicable`** |
| coverage_state | `not_applicable` | **`review_needed`** |
| requires_attention | `False` | **`True`** |
| evidence_summary | *"No activation clues found; issue area absent by design"* | *"Step 305 per-element assessment (0 present, 1 missing, 2 disputed, 0 unclear of 5 elements; 3/3 evaluators; 12.9s)"* |
| element verdicts | **0** | **5** |
| tenant_text | 0 chars | **767 chars** |
| materiality / confidence | low / — | low / high |

**The entry is now produced by the evaluators rather than by a short-circuit.** The assertion "absent
by design" — false on a lease with §13.2 and §13.3 — is replaced by an assessed
`review_needed` that a reviewer is told to look at.

`elements_found: []`, `elements_missing: ['Co-tenancy termination trigger is addressed (if
applicable)']`.

**An apparent inconsistency, checked and dismissed:** three elements merge to `missing` but only one
appears in `elements_missing`. The other two — `termination_fee`, `unamortized_ti_recovery` — are in
`favorable_or_non_adverse_absences` with `absence_adverse_to: "landlord"`. On a tenant perspective
their absence is not adverse, so they are correctly excluded. Deliberate behaviour, not a defect.

## 2. Does it find the right clauses? Yes — §13.2 and §14.2

`tenant_text` opens: *"Section 13.2. Termination Right. If the damage cannot be restored within two
hundred forty (240) days…"* — the exact clause the arc has been chasing since Step 463.

Element **"Triggering conditions for early termination right"** → merged `disputed`:

| role | verdict | `section_ref` | quote |
|---|---|---|---|
| A claude-sonnet-4-6 | `missing` | `None` | — |
| B gpt-5.5 | `explicitly_present` | **`Sections 13.2 and 14.2`** | *"If the damage cannot be restored within two hundred forty (240) days… either party may terminate this Lease; If more t…"* |
| C grok-4.3 | `explicitly_present` | **`Section 13.2`** | *"If the damage cannot be restored within two hundred forty (240) days, or if the damage occurs during the last twelve (12)…"* |

Element **"Notice period required"** → `disputed`, same split; B cites `Sections 13.2 and 14.2` quoting
*"upon sixty (60) days' written notice given within ninety (90) days of the damage"*.

**Both citations resolve** — `Section 13.2` and `Section 14.2` are real line-anchored headings in the
Atlas index.

Three elements merge `missing` on 3/3 agreement — termination fee, unamortized TI recovery,
co-tenancy trigger. **Correct: Atlas contains none of those.**

*[my reading]* B and C found the right clauses and quoted them accurately. **A voted `missing` on both
elements while B and C quoted §13.2 verbatim** — that is the disagreement driving `disputed`, and it
is the panel working as designed: the split is preserved rather than resolved away. The net outcome —
`review_needed`, `requires_attention: True`, two critical elements disputed — is a defensible reading
of a lease whose only termination rights are casualty- and condemnation-triggered.

## 3. THE GATE — the trade is real and it is expensive

**divall: 4 attempts, 4 aborts, LP-12 in every one.**

```
attempt 1  GATE ABORT 176s  Failed LPs: ['LP-12']  Applicability: {'LP-12': 'applicable'}
attempt 2  GATE ABORT 195s  Failed LPs: ['LP-07','LP-12','LP-16','LP-17']
attempt 3  GATE ABORT 181s  Failed LPs: ['LP-12']  Applicability: {'LP-12': 'applicable'}
attempt 4  GATE ABORT 195s  Failed LPs: ['LP-07','LP-12','LP-16','LP-17']
```

**Step 478 produced the first completed divall coverage result in the project's history. Step 481's
clue-list change destroyed it.** LP-12 was previously waved through as `not_applicable` — degradable
under the Step-478 partition — and is now `applicable`, so the same empty extraction is
non-degradable and kills the run. **Divall has gone from "processable" back to "not processable."**

**Atlas: 0 aborts in 1 attempt — and that is NOT a rate.** One completion is one sample. The honest
estimate comes from the 18 persisted extraction runs of Steps 463/464:

```
LP-12 populated: 5 of 18     LP-12 empty: 13 of 18
```

**Under the new rule every empty LP-12 must abort. Predicted Atlas abort rate ≈ 13/18 = 72%**, against
the ~60% Step 475 measured and the 0% that Step 478's degrade path produced for this LP. Getting a
completion first try had roughly a 28% prior. **I am not reporting "Atlas is fine" — I am reporting
that Atlas got lucky once and the expected rate went up.**

**The trade, stated plainly:** the false all-clear on LP-12 is fixed on both fixtures. The price is
that LP-12 emptiness — the single most common extraction failure in this project — is now fatal
rather than degradable. On Atlas that is a predicted ~72% abort rate; on divall it is 100% across four
attempts.

## 4. Knock-on — 8 of 32 LPs moved, and most of it is noise

Atlas `s482` vs `s478_atlas_r2`: 32 entries both, 94 → 96 calls, `requires_attention` 27 → 27.

| | Step 478 | Step 482 |
|---|---|---|
| partial | 20 | 22 |
| review_needed | 5 | 4 |
| covered | 2 | 3 |
| missing | 2 | 1 |
| not_applicable | 3 | **2** |

**8 of 32 LPs moved:** LP-06, **LP-12**, LP-17, LP-19, LP-20, LP-21, LP-22, LP-28.

*[my reading]* Only **LP-12** is attributable to this change — it is the one LP whose applicability the
edit touched, and `not_applicable → review_needed` is exactly the intended effect. The other seven sit
inside the **7–9 of 32 run-to-run noise floor** established in Steps 456–457, and the moves are the
usual shuffling among adjacent states (`review_needed ↔ partial`, `missing → review_needed`,
`review_needed → covered`). **I cannot attribute them to the clue-list change**, and two runs cannot
separate them from noise.

`not_applicable` dropped 3 → 2 exactly as expected: LP-12 left that bucket, LP-23 and LP-31 remain and
were verified correct in Step 480.

## What is NOT established

- **Atlas's actual abort rate under the new rule.** One attempt. The 72% figure is a prediction from
  extraction-shape data, not a measurement of this configuration.
- Whether the 7 non-LP-12 movements are caused by the change or are noise. Two runs cannot separate them.
- Whether divall can complete at all now. Four attempts, zero completions; whether some extraction
  shape populates LP-12 on that fixture is unknown — Step 472's standalone extraction left it empty too.
- Whether `disputed` is the right merged verdict for Atlas's triggering-conditions element. A voted
  `missing` against two verbatim quotes; whether A is wrong or applying a stricter reading is untested.
- Anything about the other 9 real leases the clue change flipped to `applicable`. Not run.
