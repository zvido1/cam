# Step 484 — LP-12 seamed, gate made seam-aware. Both fixtures now complete.

**Date:** 2026-08-24 · **Instruction:** `build_log/484_chat_instruction.md` (design recorded there
before the diff)
**Tests 359 passed** (357 + 2 new). Panel verified before spending (`gpt-5.5`, 4.5s, no fallback) and
clean throughout. Nothing tuned. **Not deployed.**

`SPAN_EVIDENCE_LPS = {"LP-07", "LP-12", "LP-27"}` · `SECTION_EXPANDED_SPAN_LPS = set()` ·
`ENTAILMENT_TEST_LPS = {"LP-27"}`

---

## The design worked, and proved itself on a real run

The exemption is conditional on **production**, not membership. divall attempt 1 demonstrates both
halves of that in a single gate decision:

```
completeness gate: 1 LP(s) exempt -- evidence sourced from verified spans, not the extraction
                   bucket: ['LP-12']
completeness gate applicability: {'LP-07': 'applicable', 'LP-12': 'applicable', 'LP-16': 'applicable',
                                  'LP-17': 'required', 'LP-30': 'unclear', 'LP-31': 'unclear',
                                  'LP-32': 'unclear'}
                   | must_abort=['LP-07', 'LP-16', 'LP-17'] seam_exempt=['LP-12']
```

**LP-07 is in `SPAN_EVIDENCE_LPS` and is in `must_abort`.** Its elicitation fell back on divall (zero
verified spans, as Step 472 measured), so it never entered `_span_evidence` and was correctly **not**
exempted. LP-12, which did produce spans, was. **That is exactly the fork the brief required, observed
live rather than argued.**

## Abort rates

| | before | **after** |
|---|---|---|
| **Atlas** | predicted **72%** (LP-12 empty in 13 of 18 extractions) | **0 aborts / 1 attempt** |
| **divall** | **100%** (4 of 4, Step 482) | **1 abort / 2 attempts — COMPLETED** |

**Atlas:** LP-12 was the *sole* abort cause. With the exemption it can no longer abort while
elicitation produces spans — and it produced **13**. This is structural, not luck: the 72% figure was
entirely LP-12 emptiness, and emptiness of the bucket is now irrelevant to the gate for that LP. One
run, but the mechanism is not probabilistic.

**divall: it completes again.** Step 478 produced the first divall result; Step 481 destroyed it;
this recovers it. Attempt 1 aborted on LP-07/LP-16/LP-17 — a bad extraction shape, unrelated to LP-12 —
and attempt 2 completed.

## LP-12's coverage entry

### Atlas — span path, 13 records, and the panel splits three ways

```
[Section 5.1]   if Landlord fails to perform any material obligation under this Lease...
[Section 5.1]   if such failure continues for an additional thirty (30) days, Tenant may terminate...
[Section 13.2]  If the damage cannot be restored within two hundred forty (240) days...
[Section 13.2]  either party may terminate this Lease upon sixty (60) days' written notice...
[Section 13.3]  If restoration is not completed within two hundred forty (240) days...
[Section 13.3]  Tenant shall have the right to terminate this Lease upon thirty (30) days' notice...
[Section 14.1]  If the entire Demised Premises shall be taken by governmental authority...
[Section 14.2]  If more than twenty percent (20%) of the rentable area... shall be taken...
```

**§13.2 and §13.3 both present, with clean resolvable locators.** `tenant_text` 767 → **2,605 chars**.

**But the verdict got *worse*, and the reason is interesting:**

| element | 482 (bucket) | **484 (spans)** | divall |
|---|---|---|---|
| Triggering conditions | `disputed` | **`unclear`** (`no_consensus`) | `explicitly_present` |
| Notice period | `disputed` | **`unclear`** (`no_consensus`) | `explicitly_present` |
| Termination fee / unamortized TI / co-tenancy | `missing` ×3 | `missing` ×3 | `missing` ×3 |

Atlas LP-12 stays `review_needed`, `found=0`. **More evidence produced a three-way split, not
agreement:**

- **A** `unclear`, citing `Section 5.1, 13.2, 13.3, 14.1, 14.2, 15.3, 17.2` — *"The lease contains
  multiple termination triggers (landlord default, casualty, condemnation, recapture, tenant default),
  but none of these constitute a[n early termination right]"*
- **B** `explicitly_present`, `Section 13.2` — *"The lease expressly defines circumstances under which
  early termination may occur, including casualty damage…"*
- **C** `missing` — *"all termination rights are tied to landlord d[efault]"*

*[my reading]* **This is not a regression in the pipeline; it is the panel surfacing a real legal
question** — whether a casualty- or condemnation-triggered termination counts as an *early termination
right*, or whether that term means a negotiated exit option. A cited seven sections, so it read the
whole span set and reasoned from it. Step 482's `disputed` was a two-way split on thinner evidence;
`unclear`/`no_consensus` on richer evidence is arguably the more honest output. **I am not claiming the
new answer is better — I am claiming the disagreement is now substantive rather than an artefact of
truncated evidence.**

### divall — span path, 4 records, and it improves

```
[ARTICLE\nVI]  If during the first fifteen (15) Lease Years of the Term, the Premises are subject t...
[ARTICLE\nVI]  Provided Tenant has paid Percentage Rent with respect to at least one of the two (2)...
[ARTICLE\nX]   In the event that the entire Premises... (condemnation)
```

**Found the Total Destruction clause (Article VI) and the condemnation clause (Article X)** — exactly
the two the brief named. `partial`, **2 elements found**, `requires_attention: True`.

Locators carry the `ARTICLE\nVI` embedded newline recorded in Steps 472/479 — cosmetically malformed,
still functional.

**Trajectory for divall LP-12: `not_applicable` "absent by design" (478) → gate abort (482) →
`partial` with 2 elements found (484).**

## LP-07 and LP-27

| LP | run | state | found/missing | spans |
|---|---|---|---|---|
| LP-07 | 482-atlas → **484-atlas** | partial → partial | 5/1 → **5/1** | 5 → 5 |
| LP-07 | 478-divall → **484-divall** | missing → missing | 0/6 → **0/6** | 0 → 0 (fell back both) |
| LP-27 | 482-atlas → **484-atlas** | partial → partial | 8/1 → **8/1** | 8 → 7 |
| LP-27 | 478-divall → **484-divall** | partial → partial | 8/0 → **6/0** | 3 → 3 |

**LP-07 unchanged on both. LP-27 unchanged on Atlas.**

**divall LP-27 moved 8 → 6 found**, and I checked rather than assumed: the two elements that moved are
`monetary damages` and `specific performance` — `implicitly_present` → `disputed`. **Those are the two
false positives Step 460 identified.** But **the evidence is identical (3 span records both runs)**, so
this is evaluator run-to-run variance, **not attributable to this change**. Directionally the false
positives weakened; I am recording that as an observation, not a claim.

## Cost

| run | calls | elapsed | vs baseline |
|---|---|---|---|
| 482-atlas | 96 | 1004.7s | — |
| **484-atlas** | **97** | 1006.7s | **+1 call** — exactly the predicted elicitation cost for LP-12 |
| 478-divall | 73 | 734.8s | — |
| **484-divall** | **77** | 997.2s | **+4 calls** — 1 elicitation + 3 evaluator calls for an LP-12 now assessed rather than short-circuited |

Plus **257s spent on divall's aborted attempt 1**, which included elicitation for three seamed LPs that
was then discarded — the ordering cost stated in the design, now measured.

## What is NOT established

- Atlas's abort rate as a measured rate. One attempt. The claim is mechanical (LP-12 emptiness can no
  longer abort) not statistical.
- Whether `unclear`/`no_consensus` is the *correct* verdict for Atlas LP-12. The three-way split rests
  on a genuine legal question this step does not resolve.
- Whether divall LP-27's 8 → 6 is signal. Evidence identical; two runs cannot separate it from the
  7–9 of 32 noise floor.
- divall's abort rate. 1 of 2 attempts, and attempt 1 failed on LP-07/16/17, whose extraction
  variability is unmeasured on that fixture.
- Deployed behaviour. Local only.
