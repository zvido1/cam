# Step 520 — LP-07 survey. It is already conditional; the defect is one clue, and the corpus is contaminated.

**Date:** 2026-08-31 · **Instruction:** `build_log/520_chat_instruction.md`
**DIAGNOSTIC ONLY. Nothing changed, no provider calls, not deployed.**
**Ground truth established by reading. 31 of 32 fixtures have a real CAM provision; 1 does not.**

---

# 0. THE BRIEF'S PREMISE IS WRONG IN EVERY CLAUSE

> *"LP-07 is applicability_mode 'always' — hardcoded required, no clue list, no mechanism to be wrong."*

The schema entry, verbatim:

```json
"id": "LP-07",
"name": "Common Area Maintenance (CAM)",
"applicability": "conditional",
"activation_clues": ["common area","CAM","CAM charges","operating expenses",
                     "triple net","NNN","proportionate share","shared expenses","common facilities"],
"exclusion_clues": ["gross lease","full service lease","all-inclusive rent",
                    "no additional charges","landlord pays all operating"],
"default_when_unclear": "applicability_unclear",
"notes": "Not applicable in gross or full-service leases."
```

**LP-07 is `conditional`, carries nine activation clues and five exclusion clues, and has a
`default_when_unclear`.** There is no `applicability_mode` field anywhere in the codebase —
`grep -rn "applicability_mode"` over `cam/` and `05 Lease Analyzer/app/` returns nothing.

**Nor is divall a ground lease.** In the full document: `ground lease` **0**, `ground rent` **0**,
`unimproved` **0**, `Absolutely Net` **12**. It is an absolutely-net lease of built premises.

**And divall is not "zero CAM language."** It contains the phrase *common area maintenance* once
(quoted in §2 below). That single occurrence is why LP-07 fires.

**The step as briefed — "should LP-07 become conditional" — has no target. It already is.** The
answerable question is whether its existing clue list should be narrowed, which is Step 495's method
exactly. That is what follows.

---

# 1. TODAY'S VERDICT: `applicable`, 32 of 32 — the LP-16 shape again

```
verdict distribution across 32 fixtures: {'applicable': 32}

activation fire counts        exclusion fire counts
  common area          32       gross lease                   0
  CAM                  31       full service lease            0
  proportionate share  29       all-inclusive rent            0
  triple net           25       no additional charges         0
  CAM charges          23       landlord pays all operating   0
  operating expenses    7
  NNN                   2
  common facilities     1
  shared expenses       0   <-- fires on nothing
```

**No exclusion clue fires anywhere.** `common area` alone guarantees the verdict on all 32 before any
narrower clue is consulted — the same structure Step 495 found on LP-16.

## 1.1 `CAM` is a substring match, and it matches ordinary words

`lease_knowledge.py:152` — `if clue.lower() in text_lower:`. **No word boundaries.**

So the clue `CAM` matches `became`, `came`, `campus`, `Campbell`, `Cameron`, `camera`. Word-boundary
counts of standalone `CAM` versus what the clue actually fires on:

| fixture | standalone `CAM` | other words containing `cam` |
|---|---|---|
| divall | 1 | `came` ×2 |
| everbridge | 1 | `became` ×1 |
| solidpower | 1 | `Campbell` ×4, `became` ×1 |
| ncino | 1 | `Cameron` ×2, `CameronCo` ×2 |
| quanterix | 1 | `campus`, `camera` |
| albireo | **0** | — |

## 1.2 THE CORPUS IS CONTAMINATED — in 8 of 10 real leases the only standalone `CAM` is ours

Every EDGAR fixture opens with a `#` header written by our own importer. Line 5 of eight of them:

> `# Imported 2026-06-14 for the EDGAR mini-corpus (Tier-1 external validation, CAM NEW_THREAD_PROMPT).`

**In atreca ×2, bokf, divall, everbridge, ncino, quanterix and solidpower, that line is the only
standalone occurrence of `CAM` in the entire file.** Only atlas (10, real `CAM Charges` provisions)
and albireo (0) differ. divall's header also supplies `triple-net NNN` — its only `NNN`.

**`lease_parser._parse_txt` returns `path.read_text()` unchanged.** No comment stripping exists
anywhere in the load path, so the header is part of every document the extractor, the elicitor and the
panel read. It also states conclusions about the document — `Landlord's-Work / Work-Letter: ABSENT`,
`'Absolutely Net' (triple-net NNN) restaurant lease` — for LPs the pipeline is supposed to decide.

**Today this changes no applicability verdict** (all 32 are `applicable` regardless). It is a latent
validity problem for every measurement taken on this corpus, and it is a live argument for preferring
a clue set that does not depend on it — see §3.3.

---

# 2. GROUND TRUTH BY READING — 31 positive, 1 negative

Per Step 495, the test is whether the document has a **provision**, not whether the word appears.

**The 22 synthetics** (21 `T-*` + `standard_template`) all carry `ARTICLE IX — COMMON AREA` and
`Section 9.1. CAM Charges. Tenant shall pay to Landlord, as Additional Rent...`, with
`"CAM Charges" shall mean Common Area Maintenance charges as defined in Section 9.1`. `T-07_reordered`
has the same article renumbered `ARTICLE VII`. **All 22 POSITIVE.** No `[Intentionally Omitted]` CAM
article exists in any of them — the Step-495 `T-09_mixed` trap does not recur here.

**The nine real positives**, each read:

| fixture | the provision |
|---|---|
| atlas | `Section 3.3. Real Estate Taxes and CAM Charges` — *"Common Area Maintenance charges ("CAM Charges") for each calendar year"* |
| albireo | `6.2 Additional Rent` — *"Tenant's Share of Expense Increases above Operating Expenses for the Base Expense Year"* |
| atreca ×2 | *"Base Rent, Tenant's Share of Operating Expenses and all other amounts payable..."* |
| bokf | proportionate share ×35, operating expense ×23 |
| everbridge | operating expense ×64 |
| ncino | `5.02 Expenses` — *"Tenant agrees to pay Landlord as Additional Rent, Tenant's Proportionate Share of Expenses"*, exclusions in Exhibit B |
| quanterix | `2.6. Operating Costs and Real Estate Taxes...` — *"Tenant shall pay Tenant's Proportionate Share of Real Estate Taxes and Operating Costs... in accordance with Exhibit G"* |
| solidpower | common area maintenance ×20, proportionate share ×11 |

**ncino and quanterix were the two I could have got wrong from counts alone** — ncino shows
`operating expense` twice and quanterix once. Both have real regimes; the low counts are because they
say *Expenses* and *Operating Costs*. Reading caught it, exactly as at Step 495.

## 2.1 The one negative: divall

Both body occurrences of any CAM clue, verbatim:

**Line 599**, inside `6.1 Maintenance and Repair by Tenant`:

> "In the event the Premises are or become subject to the common area maintenance charges, or other
> third party billings, Tenant shall be responsible therefor."

**Line 727**, inside a radius restriction:

> "...where all customers must enter the restaurant by first passing through common areas of the mall."

No CAM article, no proportionate share, no operating-expense pool. **NEGATIVE.**

---

# 3. Q2 + Q3 — THE POSITIVE COUNT, THEN THE CANDIDATES

**A narrowed clue set must keep firing on 31 fixtures and stop firing on 1.**

| set | clues | TP | FP | TN | FN | dead clues |
|---|---|---|---|---|---|---|
| **CURRENT** | the nine above | 31 | **1** | 0 | 0 | `shared expenses` |
| **C1** | proportionate share · pro rata share · operating expense · operating cost · CAM charges | **31** | **0** | **1** | **0** | none |
| **C2** | C1 minus `CAM charges` | 31 | 0 | 1 | 0 | none |
| **C3** | CAM charges · proportionate share · operating expense | 31 | 0 | 1 | 0 | none |
| **C4** | C1 with `common area maintenance` added | 31 | **1** | 0 | 0 | none |

**The only fixture that flips is divall, and the flip is correct.** No positive is lost by any of
C1–C3.

## 3.1 Rejections

- **`shared expenses` fires on 0 of 32.** Rule 1 — it cannot be shown to add coverage. Reject.
- **C4 is rejected**, and it is the instructive one: adding `common area maintenance` — the most
  obviously CAM-ish phrase available — **reintroduces the false positive**, because divall's contingent
  sentence contains that exact phrase. *The clue that reads most like the right answer is the one that
  breaks it.*
- **The five exclusion clues fire on 0 of 32.** I am **not** applying Rule 1 to these: no fixture in
  this corpus is a gross or full-service lease, so they are **untested, not dead**. Deleting them on
  this evidence would be reasoning from an absent test case.

## 3.2 C3 scores 31/31 partly by accident — do not take it

C3 keeps quanterix only via `operating expense`, which appears there **once**, inside a fair-market-rent
definition (*"a comparable term and comparable operating expenses and real estate taxes"*) — **not** in
its actual regime, which is captioned *Operating Costs*. A set that holds a true positive through an
incidental phrase is fragile. **C1 and C2 catch quanterix through `operating cost`, its real caption.**

## 3.3 C1 is the only candidate that is header-independent

| set | with importer header | header stripped |
|---|---|---|
| CURRENT | 3 fixtures depend on header-supplied clues | — |
| **C1** | TP=31 FP=0 TN=1 FN=0 | **TP=31 FP=0 TN=1 FN=0** |

**Recommend C1.** It is perfect on the corpus, has no dead clue, catches every regime through its own
caption rather than an incidental mention, and scores identically whether or not our own annotation is
present.

---

# 4. Q4 — WHAT IT COSTS, AND WHY THE FEARED FAILURE DOES NOT APPLY HERE

> *"a false not_applicable on a lease that DOES have CAM is a silent all-clear on the tenant's largest
> variable cost."*

**LP-07 cannot return `not_applicable` on a clue miss.** `applicability = conditional`, and
`lease_knowledge.py:158` returns `not_applicable` only for `optional`. A conditional miss returns
`unclear`, and `lease_coverage.py:391` then resolves it through `default_when_unclear`:

```
LP-07  conditional -> applicability_unclear     <-- 1 of 32 LPs in the schema
LP-16  conditional -> not_applicable
LP-12  optional    -> not_applicable
```

**LP-07 is the only LP in the entire schema whose unclear-default is `applicability_unclear`**
(20 LPs use `review_needed`, 11 use `not_applicable`). Someone already recognised that LP-07 must not
be allowed to fall silent, and defended it specifically.

**So the failure mode in the brief is the LP-16 failure mode, not LP-07's.** At Step 496 the LP-16
banner stayed silent precisely because its default resolves to `not_applicable`. LP-07's resolves to a
state that shows.

**The real cost is different and still real:** on `unclear` the pipeline appends an assessment with
`tenant_text=""`, no elements, and `"Cannot determine whether this issue area applies"` — **the panel
never evaluates the LP.** A false miss does not produce a silent all-clear; it produces a visible
non-answer on the tenant's largest variable cost. That is better than silence and worse than analysis.

**Measured exposure of C1: zero false negatives on 31 positives**, including the two —
ncino and quanterix — whose regimes avoid the word *CAM* entirely.

**The Step-481 comparison in the brief cuts the other way.** That change made divall *unprocessable*.
C1 makes divall *processable*: LP-07 → `unclear` → `unclear` is in `DEGRADABLE_APPLICABILITY`, so the
422C gate degrades instead of aborting. **Narrowing LP-07's clues resolves the Step 519 gate abort as a
schema-data change, without touching gate semantics** — cheaper and lower-risk than Step 519's
option (B), which needed 422C authorization.

## 4.1 The tension I am not going to paper over

C1 makes divall's LP-07 report `applicability_unclear`. The schema's own `coverage_state_rules` for
LP-07 say:

- `missing` = *"CAM references present in lease but no CAM provision found"* ← **this is divall exactly**
- `not_applicable` = *"Gross or full-service lease structure confirmed"* ← divall is net, not gross

**The schema already names divall's correct state, and it is `missing` — which requires the panel to
run.** C1 delivers `applicability_unclear` instead: right that the run should not abort, weaker than
the answer the schema describes. Step 519's option (B) is what produces `missing`.

**They are complementary, not alternatives.** C1 is the cheap correct-direction fix; (B) is what makes
LP-07 say the true thing.

---

# 5. Q5 — THERE IS NO MODE BETWEEN

```
applicability_levels: ['required', 'conditional', 'optional']
```

**Three levels, and LP-07 already holds the middle one.** `required` short-circuits before any text
check (`lease_knowledge.py:139`); `optional` returns `not_applicable` on a miss; `conditional` returns
`unclear` and defers to `default_when_unclear`.

**The graduation the brief is reaching for already exists — as `default_when_unclear`, not as a fourth
level.** That field is what separates LP-07 (`applicability_unclear`, visible) from LP-16
(`not_applicable`, silent) although both are `conditional`. **The lever is the clue list and the
unclear-default, not the mode.**

---

# RECOMMENDATION

1. **Adopt C1** — `["proportionate share", "pro rata share", "operating expense", "operating cost",
   "CAM charges"]`. 31/0/1/0, no dead clue, header-independent, and it fixes the divall abort as a data
   change.
2. **Drop `shared expenses`** (fires on nothing). **Keep the exclusion clues** — untested, not dead.
3. **Do not add `common area maintenance`.** It reads like the right clue and is the one that breaks.
4. **Strip the `#` importer header at parse time, and re-run any applicability measurement taken on
   this corpus.** Separate from LP-07: the header is in every prompt and states conclusions about the
   document.
5. **Consider word-boundary matching for short clues.** `CAM` matching `became` is not a near-miss.

**Not implementing any of it — this step is diagnostic.** Items 4 and 5 change behaviour for all 32
LPs and need their own briefs.

---

# WHAT THIS DOES NOT ESTABLISH

- **31/1 is evidence about 32 fixtures**, and 22 of them are one synthetic family sharing a single CAM
  article. The independent evidence is **10 real leases, of which 1 is negative.** A clue set scoring
  perfectly here is not validated on a gross lease, a full-service lease, or a sublease — **the corpus
  contains no negative except divall**, so TN=1 rests on one document.
- **The exclusion clues remain untested.** No fixture is gross or full-service.
- **C1 was not run through the pipeline.** Scored offline against text; no extraction, no panel, no
  provider calls. Whether divall then completes is a prediction, not a measurement.
- **The header contamination's effect on extraction and panel output is unmeasured.** I established it
  is present in the text and changes no applicability verdict today. What it does to the extractor and
  the evaluators has not been tested.
- **Nothing was changed, built, or deployed.**
