# Step 535 PART A — Negation-awareness costs no recall and fixes 2 of 4. It does not fix everbridge. I did not build it.

**Date:** 2026-09-03 · **Instruction:** `build_log/535_chat_instruction.md`
**PART A COMPLETE. PART B NOT BUILT — the brief's gate is "build only if A is clean", and A is not.**
**No provider calls, no clue list touched, nothing changed, not deployed.**

---

# THE VERDICT FIRST

A negation-aware matcher is **real, measurable and free in recall** — zero loss across 12 conditional
LPs × 23 synthetics. It removes **5 of 8** false LP-20 firings on real leases.

**But it fixes only 2 of the 4 abort-causing calls, and everbridge — the case that motivated the step
— still aborts.** The two survivors are not negations at all, so no negation rule can reach them.

---

# 1. THE PROPOSED RULE, AND THE THREE VARIANTS I REJECTED BY MEASURING

**Final form:** a clue occurrence does not activate if a negating token appears in the span
**preceding it within its sentence** — bounded by the previous `.` or blank line.

```
negating tokens:  no | not | non- | never | other than | exclud*
scope:            text BEFORE the hit, back to the previous period or paragraph break
granularity:      per OCCURRENCE, not per LP
```

**Per-occurrence is the load-bearing choice.** The LP still activates if *any* occurrence is clean, so
a document containing both `non-exclusive right` and a genuine exclusivity covenant still fires on the
second. Suppressing the LP wholesale would trade one error class for a worse one.

## Variant 1 — fixed 60-character window. Rejected.

LP-20 firings on real leases: 8 → 4. **everbridge still fires**, because its hit is *"certain areas
designated for the exclusive use of certain tenants"* with no negation within 60 characters. A window
tuned to catch `non-exclusive` cannot reach a negation eight words back.

## Variant 2 — whole sentence. Rejected, and this is the one worth recording.

Better on LP-20 (8 → 2) **but it destroyed LP-32 Hazardous Materials: 22 synthetics → 2.**

The cause, found by printing the suppressing token:

> `environmental` in *"...comply with all applicable federal, state, and local laws, ordinances,
> regulations, and codes in connection with its use and occupancy of the Premises, **including without
> limitation** all health, safety..."*

**The suppressor was `without`, inside "including without limitation"** — boilerplate that appears
dozens of times in nearly every commercial lease. Checking the *whole* sentence also inspects text
*after* the clue, which has no bearing on whether the clue is negated.

## Variant 3 — preceding span, original token list. Still rejected.

LP-32 still lost 20 of 22. Same `without`.

## Variant 4 — preceding span, refined tokens. ADOPTED as the design.

Dropping `without` and `except` — both boilerplate connectives in legal prose, neither a negation of
the following phrase.

---

# 2. RECALL — MEASURED, NOT ESTIMATED

```
LP      name                         REAL now/new  SYN now/new   recall
LP-04   Security Deposit                  9/9          23/23     preserved
LP-07   Common Area Maintenance           9/9          23/23     preserved
LP-12   Early Termination                 9/9          20/20     preserved
LP-15   Signage Rights                    9/9          23/23     preserved
LP-16   Parking                           7/7          21/21     preserved
LP-20   Exclusivity                       8/3          23/23     preserved
LP-21   Guaranty of Lease                 7/6           4/4      preserved
LP-22   SNDA                              9/9          23/23     preserved
LP-23   Percentage Rent                   2/1           2/2      preserved
LP-30   Estoppel Certificate              8/8          20/20     preserved
LP-31   Co-Tenancy                        0/0           2/2      preserved
LP-32   Hazardous Materials               8/8          22/22     preserved

TOTAL synthetic recall loss: 0
```

**Zero true positives lost.** The synthetics are the corpus that *has* the provisions — Atlas carries an
`Exclusivity` heading and *"Tenant shall have the exclusive right to use fifteen (15) designated
parking spaces"*; T-01 carries an `Exclusive Use` section heading. **Both survive**, because a heading
has no preceding negation.

**On real leases only LP-20 (−5), LP-21 (−1) and LP-23 (−1) change. Nine of twelve are untouched.**

**The Step-534 ground truth holds:** all 8 LP-20 firings on real leases were false, so removing 5 is
pure gain, and the 3 that remain were already false.

---

# 3. THE ENUMERATION CASE NEEDS NO SEPARATE HANDLING — MEASURED, AND IT SURPRISED ME

I expected the exclusions preamble to be too far back. **It is not, because the list has no internal
periods.**

everbridge LP-23's hit — *"(xxxi) Fixed or percentage rent under any ground or underlying lease"* —
sits in the same period-delimited span as the `shall not include` preamble that opens the enumeration.
**Sentence-scoping catches it. LP-23 is FIXED by the negation rule alone.**

"Hundreds of characters earlier" is true in characters and false in sentences. **No enumeration-specific
mechanism is needed for this case**, and I would not build one speculatively.

---

# 4. SCOPE — CORPUS-WIDE, AND THE DEFENCE

**Apply to every conditional LP, not only the measured ones.** Three reasons:

1. **Recall loss is zero on all twelve**, measured above. The risk the brief names — changing behaviour
   on LPs nobody ground-truthed — is bounded: on real leases, nine of twelve LPs are bit-identical,
   and the three that change lose only firings that Step 534 read and found false.
2. **A per-LP allowlist would be the fourth per-LP narrowing**, which is the layer this step exists to
   move away from.
3. **The rule is about grammar, not about any LP.** `exclusive use` inside `non-exclusive use` is wrong
   for the same reason on every LP that ever matches it.

**The honest caveat:** LP-21 (7→6) and LP-23 (2→1) change on real leases, and only everbridge's and
ncino's instances were ground-truthed. **Two firings are removed that nobody has read.**

---

# WHY I DID NOT BUILD IT

Against the four abort-causing calls:

```
everbridge  LP-20   STILL ABORTS
everbridge  LP-21   STILL ABORTS
everbridge  LP-23   FIXED
ncino       LP-20   FIXED
```

**2 of 4. And the two survivors are not negation problems:**

> **LP-20:** *"**Landlord** shall have the exclusive right to conduct such contests, protests and
> appeals of the Taxes"* — a **subject** error. Landlord holds the right, not Tenant. There is no
> negation to detect.

> **LP-21:** *"Tenant and **any such guarantor** shall remain liable and responsible for all Rent"* — a
> **conditional** reference to a guarantor who may not exist. Also not a negation.

**The brief's gate is explicit: "build only if A is clean."** A negation rule that leaves the
motivating document aborting is not clean. **Building it would ship a real improvement that does not
achieve the step's purpose, and would make the next measurement harder to read** — everbridge would go
from 3 aborting LPs to 2 and still produce no report.

**What it WOULD buy, stated plainly so the decision is yours:** ncino's only abort is LP-20, so
**ncino would complete** — the second real lease ever to do so, and the first office lease. That is not
nothing, and if you want it on those terms it is a small, measured change.

**What would actually fix everbridge** is subject/role awareness — *who holds the right* — which is
semantic, not lexical, and is a different design. I am not proposing it here.

---

# WHAT IS NOT ESTABLISHED

- **Nothing was built.** All numbers come from offline simulation against persisted corpus text; no
  code path was changed and no run was made.
- **"ncino would complete" is a prediction.** LP-20 is its only `must_abort` today, but LP-12 remains
  `applicable` and seam-exempt, and a run could surface a different failure at a later stage — Step 532
  established coverage has never run on a 230 KB document.
- **The negation token list is tuned on this corpus.** `without` and `except` were removed because they
  are boilerplate here; another corpus could contain a genuine `except` negation this rule now misses.
- **Sentence boundaries are `.` and blank line.** Abbreviations, section numbers like `13.4` and
  decimals will split sentences wrongly in places. I did not measure how often.
- **Two removed firings (LP-21, LP-23 on unnamed documents) were never read.**
- **No clue list was touched**, per the brief.
