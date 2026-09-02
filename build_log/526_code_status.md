# Step 526 — No 429 exists. The timeout fix worked. Two real leases are blocked by "non-exclusive".

**Date:** 2026-09-02 · **Instruction:** `build_log/526_chat_instruction.md`
**Panel verified clean before spending. atreca FAILED (gate), ncino FAILED (gate), solidpower already complete from Step 525.**
**1 of 3 real leases completes. Nothing tuned. Not deployed.**

---

# 0. THREE PREMISES CORRECTED BEFORE SPENDING

**"If the 429 recurs" — there is no 429, and there never was.** `grep -rniE "429|rate.?limit"` across
`build_log/` returns only line numbers and a job id. Atreca's recorded failure is
`TimeoutError: Router timeout exceeded: 308.8s > 300.0s` — a timeout, not a rate limit. **This run
confirms it: zero occurrences of `Router timeout`, `429`, `rate limit`, or `CANONICAL FAIL-CLOSED` in
either log.**

**"No timeout change — Step 525 established none was needed."** Step 525 established the raise was not
*exercised* by solidpower. It did change the value: `EXTRACTION_PRIMARY_TIMEOUT` is **540.0**, committed
in `ada4084`. I made no further change, and this step is the first run that actually tests it.

**Part B was already done.** solidpower ran and completed at Step 525
(`build_log/runs/525_solidpower_...20260902_135645`). Re-running would have spent ~86 calls and ~29
minutes to reproduce a reported result. **Not re-spent.** Reported below from that run.

---

# PART A — atreca: THE RAISE WORKED, AND THE FAILURE MOVED

```
build_log/runs/526A_atreca_eastjamie_southsf_lease.txt-modec_20260902_143239
doc: 160,244 chars      wall: 1497.9 s      outcome: EXCEPTION
attempts: 4  ->  all four failed on ['LP-20', 'LP-21']

Router timeout exceeded : 0 occurrences
429 / rate limit        : 0 occurrences
CANONICAL FAIL-CLOSED   : 0 occurrences
```

**Extraction succeeded on all four attempts.** The document that could not get past extraction at 300s
now gets past it every time. **That is the 540s raise doing exactly what Step 525 could not
demonstrate.**

The blocker is now one layer in: the 422C completeness gate.

```
completeness gate applicability: {'LP-20': 'applicable', 'LP-21': 'applicable',
                                  'LP-23': 'unclear', 'LP-31': 'unclear'}
must_abort=['LP-20','LP-21']  degradable=['LP-23','LP-31']  seam_exempt=[]
```

**Four attempts, identical failure. Stable, not stochastic.**

---

# PART C — ncino: SAME GATE, SAME LP

```
build_log/runs/526C_ncino_parkerfarm_wilmington_lease.txt-modec_20260902_145835
doc: 225 KB      wall: 2013.9 s      outcome: EXCEPTION
attempts: 4  ->  all four failed on ['LP-20']
must_abort=['LP-20']  degradable=['LP-21','LP-23','LP-31']  seam_exempt=['LP-12']

Router timeout / 429 / CANONICAL FAIL-CLOSED : 0 occurrences
```

Again no timeout. Again four identical aborts. **LP-20 Exclusivity blocks both leases.**

---

# 1. THE GATE IS WRONG, AND EVERY HIT IS QUOTED

## LP-20 Exclusivity — the clue matches inside its own negation

**atreca** (South San Francisco lab lease). The only two hits:

> "The portions of the Project which are for the non-**exclusive use** of tenants of the Project are
> collectively referred to herein as the ' Common Areas .'"
> "Tenant shall have the non-**exclusive right** during the Term to use the Common Areas"

**ncino** (Wilmington office). Five hits, four of them literally inside `non-exclusive`:

```
negated=True   'non-exclusive right'    x3
negated=True   'non-exclusive use'
negated=False  'exclusive use'   <- "areas of the Building NOT regularly and customarily
                                     leased for the exclusive use of tenants"
```

**All five describe common-area access. The one non-negated hit is negated semantically instead.**
Neither lease contains an exclusivity covenant — neither is a retail lease, and exclusivity is a
retail provision.

**`is_applicable` matches `exclusive use` inside `non-exclusive use`.** It is negation-blind, and this
is the same naive-substring defect measured at Step 520 (`remed` inside "remediation", `liability`
inside "commercial general liability") with a worse variant: **the affirmative clue firing on its own
negation.** At Step 520 it produced a spurious annotation. Here it produces a hard abort on a real
SEC-filed lease, four times, with no result.

## LP-21 Guaranty — a generator disclaimer and a courier typo

atreca has no guarantor and no guaranty of lease. The hits:

> "Landlord does not **guaranty** that such emergency generators will be operational at all times"
> "if delivered by reputable overnight **guaranty** courier" — apparently a typo for *guaranteed*
> "Tenant or any **guarantor** or surety of Tenant's obligations hereunder shall..." ×4 — a
> *conditional* reference inside the Insolvency Events default clause, to a guarantor who does not exist

---

# 2. WHY solidpower SURVIVED — AND IT IS NOT THE CLUE LIST

I said earlier that solidpower completed because it lacked the words. **That was wrong and I checked
it.** solidpower contains `exclusive use` ×1 and `exclusive right` ×1, and:

```
is_applicable('LP-20') on all three real leases:
  solidpower  -> applicable
  atreca      -> applicable
  ncino       -> applicable
```

**The applicability verdict is identical and wrong on all three.** What differs is downstream:

```
solidpower LP-20 evidence_summary:
  "Provision known-absent for Industrial lease type. Basis: document-type-driven.
   Decision source: KNOWN_ABSENT_BY_DOC_TYPE registry. Not found by extraction model"
  tenant_text len: 0
```

**solidpower was saved by the `KNOWN_ABSENT_BY_DOC_TYPE` registry**, which has an Industrial entry for
LP-20 and short-circuits to `not_applicable` before the gate sees an empty bucket. atreca (lab/office)
and ncino (office) have no such entry, so their empty bucket plus a false `applicable` becomes
`must_abort`.

**The registry is doing the work the clue list should be doing, for exactly one document type.**

**LP-20's `default_when_unclear` is `not_applicable`** — so if the clue list were fixed and returned a
miss, LP-20 would resolve to `not_applicable` and the abort would disappear. The fix is in the clue
list, not the gate.

---

# PART B — solidpower, from the Step-525 run (not re-spent)

| | |
|---|---|
| **completes** | **YES** |
| wall / pipeline | **1717.2 s (28.6 min)** / 1158.97 s |
| calls | 86 stored / 96 logged / 78 summed |
| extraction stage | 231.8 s |
| synthesis stage | 468.6 s |

**Extraction gate: passed on attempt 1**, zero aborts, no failing LPs, `fallback_used: False`.

**Locator: 17.5%** — 120 refs, 21 resolve. Against atlas 83.8% and divall 2.5% **by my method, which is
not Step 479's and does not reproduce its 99.0%/7.2%** (my ref counts are an order of magnitude
smaller, so 479 counted more sites). Comparable only to each other. Your expectation of "near-inert at
1 heading" holds directionally, but it still resolves ~7× better than divall's zero-heading floor —
**1 parseable heading against Atlas's 89.**

**Seamed LPs — all four held, none fell back:**

```
LP-07  4 spans   LP-12  12 spans   LP-17  5 spans   LP-27  3 spans
fallback_events: 0    fallback_used: False on all four    3/3 evaluators each
```

**assessment_status:** 26 assessed, 6 not_assessed (LP-04/20/21/23/31 `not_applicable`, LP-29
`broken_xref`).

**Qualifier pass:** 9 LPs, 15 distinct clauses, **every quote resolves verbatim**. `section_ref` is
`None` throughout and `distance_chars` `None` on 8 of 9 — the Step-524 generality limit, observed. It
also surfaced a false positive absent from Atlas: `in no event shall` matched a hazmat prohibition and
a refuelling prohibition.

## The number nobody has — and the hole in it

**End to end: 1717.2 s for a 209 KB document.** But the pipeline reports 1158.97 s, leaving **558.2 s —
32% of user-visible time — unaccounted.** Recorded stage timings sum to only 700.4 s of the 1158.97 s,
so there is unattributed time inside the pipeline too.

**I ruled out two candidates by measurement**: writing the 1.6 MB result took 0.0 s to both the
OneDrive tree and temp, and the harness post-call work is census + persist. **I have not established
where either gap goes.** The headline number is honest; its decomposition is not available.

---

# 3. THE SCORE ON REAL LEASES

| lease | size | outcome | blocked by |
|---|---|---|---|
| solidpower | 209 KB | **COMPLETE** | — (saved by the doc-type registry) |
| atreca | 156 KB | ABORT ×4 | LP-20 + LP-21 |
| ncino | 225 KB | ABORT ×4 | LP-20 |

**1 of 3 completes. 3 of 3 have a wrong LP-20 applicability verdict.**

**Size is not the blocker.** ncino (225 KB) and solidpower (209 KB) are within 8% of each other and
land on opposite sides. atreca is the *smallest* of the three and fails hardest. Every failure is the
applicability matcher, and every extraction succeeded.

**Not fixed.** Changing LP-20's or LP-21's clue list is a change to applicability semantics on a
document class now measured three times, and it needs its own brief — the same call as Step 520, where
the C1 clue set was proposed and left for decision.

---

# WHAT IS NOT ESTABLISHED

- **The 540s ceiling's upper bound is still untested.** It cleared atreca's extraction, but no run has
  approached 540 s. everbridge (288 KB), the largest, is unrun.
- **Whether fixing LP-20's clue list would let atreca and ncino complete is a prediction, not a
  measurement.** LP-21 would also need to clear on atreca, and LP-23/LP-31 are already degradable.
- **No completed run exists for any office or lab lease.** solidpower is industrial, and it completed
  only because the registry covers Industrial.
- **The 558.2 s wall-vs-pipeline gap and the 458 s intra-pipeline gap are unexplained.** Two candidates
  ruled out; no cause established.
- **The locator figures are my metric, not Step 479's**, and do not reproduce its numbers.
- **Six real leases remain unrun**: everbridge, quanterix, bokf, albireo, atreca_industrial, and the
  second atreca variant.
- **Nothing was tuned and nothing was deployed.**
