# Step 483 — "Evidence present anywhere": the rescue works, the general rule does not

**Date:** 2026-08-24 · **Instruction:** `build_log/483_chat_instruction.md`
**DIAGNOSTIC ONLY.** No fix, no runs, nothing changed. Computed offline from 18 persisted Atlas
extractions (Steps 463/464), the divall standalone extraction (Step 472), and the persisted LP-12
elicitation (`build_log/423_stack_smoke_out/`).

**Needle discipline, verified before use** — occurrences in the canonical text:
`'replacement value of the Building'` **1** (Atlas §13.2 body),
`'right to terminate the Lease as of the date of such Total Destruction'` **1** (divall).
Topic words were not used.

---

## 1. Is the needed text present elsewhere in the same extraction?

**Atlas — LP-12, 18 runs:**

| LP-12 bucket | runs | needle found in |
|---|---|---|
| 767 chars (populated) | 5 | `['LP-12', 'LP-24']` |
| **0 chars (would abort)** | **13** | **`['LP-24']` — every single one** |

**Genuinely absent: 0 of 18.** §13.2 is in LP-24's `tenant_text` in **18 of 18** extractions. The
evidence never leaves the extraction output; only the bucketing drops it.

**divall — the four gate-failing LPs, standalone extraction:**

| LP | own bucket | needle status |
|---|---|---|
| LP-12 Early Termination | 0 | **PRESENT ELSEWHERE — `['LP-24']`** |
| LP-30 Estoppel Certificate | 0 | **genuinely absent** (`estoppel` 0 occurrences in the document) |
| LP-31 Co-Tenancy | 0 | **genuinely absent** (`co-tenancy` 0) |
| LP-32 Hazardous Materials | 0 | **genuinely absent** (`hazardous` 0) |

divall mirrors Atlas exactly on LP-12. LP-30/31/32 are correctly empty — the concepts are not in the
document — and they are `unclear` applicability, so under Step 478 they degrade rather than abort.
**Only LP-12 forces the abort, and only LP-12's evidence is recoverable.**

*One sample for divall.* Aborted runs persist nothing, so this is the Step-472 standalone extraction
alone, against 18 samples for Atlas.

## 2. Abort rate under an "evidence present anywhere" gate

| | current rule | "present anywhere" |
|---|---|---|
| **Atlas** (18 runs) | **13 / 18 = 72%** | **0 / 18 = 0%** |
| **divall** | 100% (4 of 4 attempts, Step 482) | would pass on LP-12; LP-30/31/32 still degrade |

**Every abort in this project's Atlas history would be avoided.** That is the size of the prize.

## 3. What would such a gate KEY ON? — I tested the honest candidate and it fails

**The needles above are hand-picked and cannot generalise.** I chose
`'replacement value of the Building'` in Step 463 (after a heading-vs-body error), and
`'right to terminate the Lease as of the date of such Total Destruction'` today. Both required already
knowing which clause to look for.

So I tested the one general key the schema actually provides: **`expected_elements_305` synonyms**,
which exist for every element of every LP — 20 for LP-12, 24 for LP-30, 21 for LP-31, 32 for LP-32.
Authored long before this arc, so not fitted to it.

**It rescued 13 of 13 empty-LP-12 Atlas runs**, every one on the schema synonym
`"Tenant shall have the right to terminate"`.

**Then the discrimination test broke it, in both directions:**

| divall LP | genuinely absent? | synonym-anywhere fires? | outcome |
|---|---|---|---|
| **LP-12** | **no — evidence in LP-24** | **NONE** | **FALSE ABORT — would still kill the run** |
| LP-30 Estoppel | yes | NONE | correct |
| **LP-31 Co-Tenancy** | **yes** | **`'right to terminate'`** | **FALSE PASS** |
| **LP-32 Hazardous** | **yes** | **`'ordinary course of business'`** | **FALSE PASS** |

**Under-fires where needed:** Atlas §13.2 says *"Tenant **shall** have the right to terminate"*;
divall says *"Tenant **will** have the right to terminate the Lease"*. One auxiliary verb, and the
synonym misses. **divall would still abort.**

**Over-fires where not:** LP-31 passes on `'right to terminate'` — a phrase from divall's casualty
clause that has nothing to do with co-tenancy. LP-32 passes on `'ordinary course of business'`, generic
boilerplate. **Both concepts are entirely absent from the document, and the rule would wave both
through.**

**A correction to my own output.** The probe I ran printed a hard-coded summary line —
*"LP-12 rescued; LP-30/31/32 correctly NOT rescued"* — which **the data on the same screen
contradicts**. I wrote the conclusion into the script before seeing the result. The actual result is
the opposite on three of four rows. Recorded rather than quietly fixed; it is the same defect class
this project's Rule 2 exists for.

### The honest answer

**Yes, a general rule exists. No, it is not sound.** The only general key the schema offers is
substring matching over element synonyms, and substring matching is exactly the mechanism that
produced LP-12's original false all-clear (Step 480: ten jargon phrases missing operative language).
**Fixing a substring-matching failure with a different substring-matching rule reproduces the failure
one layer over** — under-firing on `shall` vs `will`, over-firing on boilerplate.

**The "present anywhere" gate works when you already know which clause you are looking for. That is a
finding about the gate's ceiling, not a failure of the investigation** — and it means a sound version
needs something other than string matching to decide whether an LP's evidence is in the extraction.

## 4. Would seaming LP-12 make it moot? Largely yes — and it is the cheapest option measured

Persisted LP-12 elicitation on Atlas, `423_stack_smoke_out/LP-12_deduped.json` — **1 provider call,
46.3s, 7 raw → 7 verified spans, all verified:**

```
[ 9379, 9811]  In addition, if Landlord fails to perform any material obligation under this Lease...
[17183,17541]  If the damage cannot be restored within two hundred forty (240) days...      <- §13.2
[17812,18035]  If restoration is not completed within two hundred forty (240) days...       <- §13.3
[18090,18243]  If the entire Demised Premises shall be taken by governmental authority...   <- §14.1
[18456,18627]  If more than twenty percent (20%) of the rentable area... shall be taken...  <- §14.2
[19657,19950]  Within thirty (30) days of receipt of any assignment or subletting request...
[21466,21647]  Upon the occurrence and continuance of an Event of Default...
```

**The §13.2 needle is present in a verified span.** Elicitation reads the whole canonical document and
never consults extraction's buckets, so **bucketing cannot drop the evidence.**

*Correcting a detail in the brief:* the 7-span measurement is from
`FINDING_423_stack_verified_live.md`, not Step 471. Note also the persisted `summary.json` records
`needle_found_in_verified_span: false` — that is the **heading-word needle** (`"Termination Right"`)
whose failure Step 463 diagnosed as a test defect; the body needle
`'replacement value of the Building'` **is** present. The finding already records this.

**Cost, from Step 465's measurement:** no seam 92 calls; one seamed LP 93/93/94; two seamed LPs 94/94
— **~+1 call per seamed LP**, roughly 1% on a 92-call run.

**Would it bypass the gate problem entirely? Not quite, and the distinction matters.** The seam
supplies *coverage evidence*; the completeness gate runs on `extraction["provisions"]` **upstream of
coverage** and would still see an empty LP-12 bucket and still abort. Seaming LP-12 would fix the
*analysis* while leaving the *gate* firing on a bucket nothing downstream uses. **Making it moot
requires the gate to know which LPs are seamed** — a small change, but a real one, and not the same
statement as "seam it and the problem goes away."

**Against the alternatives:** the seam is the only option measured here that recovers the evidence
*without* string matching. It costs ~1 call per LP and carries the precision exposure Step 460
measured (2 of 8 found elements false-present on LP-27) — which is why the state doc's standing
instruction is not to extend the seam until §11.3-class qualifier-reach is addressed.

## What is NOT established

- Whether a non-string-matching general rule exists. Only the synonym key was tested.
- divall's LP-12 recoverability beyond one extraction sample.
- Whether seaming LP-12 produces *correct* verdicts. Step 482 showed the bucket path gives
  `review_needed` with two disputed critical elements; the span path is untested on LP-12 end to end.
- What the gate change to skip seamed LPs would cost or break. Not designed.
