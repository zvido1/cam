# Step 495 — LP-16 clue survey: the list is 87.5% right and can never say no

**Date:** 2026-08-30 · **Instruction:** `build_log/495_chat_instruction.md`
**DIAGNOSTIC. Nothing implemented. No code, schema or flag touched. Zero provider calls.**
32 `.txt` fixtures surveyed; ground truth established by reading, and **corrected twice** in the
process.

---

## HEADLINE

**LP-16's clue list returns `applicable` on 32 of 32 fixtures. It has never returned anything else.**

**But it is not LP-12's failure.** LP-12's list was tuned to synthetics and missed 9 of 10 real
leases — a *recall* failure. LP-16's list has **100% recall and 87.5% precision**: it is right about
28 documents and wrong about 4. **The defect is that it cannot produce a negative, not that it
produces the wrong positives.**

**A 2-clue set reaches 28/0/4/0 — 100% precision, 100% recall — on all 32 fixtures.**

---

# PART A — THE SURVEY

## A.1 Today's verdict: `applicable`, 32 of 32

```
LP-16 applicability mode: 'conditional'
activation_clues (8): ['parking','parking spaces','spaces','garage','parking area',
                       'parking lot','surface parking','reserved spaces']
exclusion_clues (4):  ['no parking','street parking only','parking not included',
                       'tenant is responsible for own parking']

verdict distribution across 32 fixtures: {'applicable': 32}
```

**No fixture returns `not_applicable`, `unclear`, or `excluded`.** No exclusion clue fires anywhere.

`parking` fires on all 32. `parking area` fires on all 32. Between them they guarantee the verdict
before any narrower clue is consulted.

## A.2 Ground truth — and I got it wrong twice before reading

The Step-493 test is whether the document has a *provision*, not the bare word. My first automated
proxy (numeric allocation / reserved-unreserved / cost-per-space / visitor parking) **misclassified
two fixtures in each direction**, and only reading the text caught it:

- **ncino** scored 0 on the proxy but contains `ARTICLE 29. PARKING. Tenant shall have the right of
  non-exclusive use…` — a real provision.
- **atreca_eastjamie** scored 0 but contains `10. Parking . …designated for non-reserved parking…
  Landlord may allocate parking spaces among Tenant and other tenants… pro rata`.
- **T-09_mixed** was classified HAS by my heading regex — but its article reads:

  > `ARTICLE XVIII — PARKING (LP-16)` … `Section 18.1. [Intentionally Omitted]`

  **A heading with nothing under it.** That is a negative, and I had it as a positive.

**Corrected ground truth: 28 of 32 have a parking provision; 4 do not.**

## A.3 The four negatives, every occurrence quoted

**T-09_mixed** — `ARTICLE XVIII — PARKING (LP-16)` / `Section 18.1. [Intentionally Omitted]`, plus 3
CAM/common-area mentions. The article is a deliberately emptied placeholder.

**T-12_omissions** — 3 hits, all definitional:
> *"…including but not limited to parking areas, walkways, landscaped areas…"* (Common Areas
> definition) · *"…maintain all Common Area facilities including parking lots…"* · *"CAM Charges
> shall include… parking lot maintenance and repaving…"*

**albireo** — 2 hits, both inside common-area/CAM definitions, and both hedged:
> *"…loading areas, parking areas (if any) and Building amenities…"* ·
> *"…maintenance and repair of the parking areas (if any), roadways and light poles…"*

**divall** — 3 hits: two maintenance obligations, one condemnation carve-out (quoted in full at
Step 493).

**Every one of the four is a common-area, maintenance, CAM or condemnation mention.** None grants,
allocates, prices or reserves parking.

## A.4 The baseline, split real vs synthetic

| corpus | TP | FP | TN | FN | precision |
|---|---|---|---|---|---|
| **Real leases (10)** | 8 | **2** | 0 | 0 | **80.0%** |
| Synthetics (22) | 20 | **2** | 0 | 0 | 90.9% |
| **All (32)** | 28 | **4** | 0 | 0 | **87.5%** |

Real-lease negatives: **albireo, divall**. Synthetic negatives: **T-09_mixed, T-12_omissions**.

**Contrast with LP-12 (Step 481):** LP-12's list failed on 9 of 10 real leases by missing them.
LP-16's fails on 2 of 10 by over-firing. **Opposite direction, and far less severe.**

---

# PART B — CANDIDATE CLUE SETS

**No clue in the candidate pool touches a single negative.** The entire false-positive problem is
carried by two clues in the current list — `parking` and `parking area` — with `spaces` and
`parking lot` responsible for the two synthetic negatives.

| candidate | TP | FP | TN | FN | precision | recall |
|---|---|---|---|---|---|---|
| **CURRENT (8)** | 28 | **4** | 0 | 0 | 87.5% | 100% |
| C1 — drop `parking`, `parking area` | 28 | 2 | 2 | 0 | 93.3% | 100% |
| C2 — drop also `spaces`, `parking lot` | 27 | 0 | 4 | **1** | 100% | 96.4% |
| **C3 — operative-language (12)** | 28 | 0 | 4 | 0 | **100%** | **100%** |
| **C4 — C2 + operative (10)** | 28 | 0 | 4 | 0 | **100%** | **100%** |
| **MINIMAL (2)** | 28 | 0 | 4 | 0 | **100%** | **100%** |
| **C5 — minimal + headroom (6)** | 28 | 0 | 4 | 0 | **100%** | **100%** |

**C2 is the cautionary one:** dropping `spaces` and `parking lot` without adding operative phrases
loses **T-14_ambiguous**, which has a real provision (`Section 18.1 Parking Rights… a ratio of not
less than four (4) spaces per one thousand (1,000) square feet`; `Section 18.2 Parking
Modifications`). **A narrower list is not automatically a better one.**

## B.1 The minimal perfect set is two clues

Exhaustive search over the pool:

```
minimal sets achieving 28/0/4/0:
   ['parking spaces', 'parking rights']
   ['parking space',  'parking rights']
```

Clue-by-clue coverage across the 28 positives, and negatives touched:

```
   parking spaces           positives=27   negatives=none
   parking rights           positives=25   negatives=none
   reserved parking         positives= 5   negatives=none
   garage                   positives= 4   negatives=none
   surface parking          positives= 2   negatives=none
   unreserved parking       positives= 2   negatives=none
   allocate parking         positives= 2   negatives=none
   reserved spaces          positives= 0   negatives=none
   right to park            positives= 0   negatives=none
   parking ratio            positives= 0   negatives=none
   parking privileges       positives= 0   negatives=none
   designated for parking   positives= 0   negatives=none
```

Only **two fixtures rest on a single clue**: T-14_ambiguous on `parking rights`, atlas on
`parking spaces`. Everything else is carried redundantly.

## B.2 The distribution, as asked — and the methodological trap

**A 2-clue list is not obviously the right answer, and saying so is the point of this section.**

`['parking spaces','parking rights']` scores perfectly **on this corpus**. But a list fitted to
exactly the documents used to evaluate it is precisely how LP-12's list came to be tuned to
synthetics. **A perfect score on 32 fixtures is evidence about 32 fixtures.**

Note also that **C3 and C4 carry four clues each that fire on nothing at all** — `right to park`,
`parking ratio`, `parking privileges`, `designated for parking`. Those are speculative scaffolding by
CLAUDE.md Rule 1: they are unfalsifiable on this corpus and should not be adopted on the strength of
a score they did not contribute to.

**My recommendation is C5** — `['parking spaces','parking rights','garage','surface parking',
'unreserved parking','reserved parking']`:

- 28/0/4/0, identical to the minimal set;
- **every clue in it demonstrably fires on at least 2 real positives** — none is speculative;
- `garage` (4 fixtures) and `surface parking` (2) cover parking *forms* the two-clue set would miss
  in a document that grants a garage without using the phrase "parking spaces", which is a real
  drafting pattern in the corpus already;
- it removes exactly the four clues responsible for every false positive.

**Adopting it is still a change that needs its own measurement**, per Step 481. This step proposes;
it does not implement.

---

# PART C — THE LAYER QUESTION

## C.1 They do not conflict. They are different questions.

- **Applicability** is a *pre-filter*: "should this document be expected to contain this?" It runs on
  raw text before extraction.
- **Extraction status** is a *post-observation*: "did I find it?" `AMBIGUOUS` currently means "I
  should have found this and did not," which is what fails 422C's `fail_missing` test
  (empty `tenant_text` **and** not `NOT_APPLICABLE`).

Fixing either resolves LP-16 on divall. **Fixing both would be coherent, not redundant** — the
pre-filter narrows what is asked for, the post-observation reports honestly on what was asked.

## C.2 I would choose the applicability fix, and the reasons are not about elegance

**1. It is decidable offline, and the decision is already made.** 32 fixtures, zero provider calls,
28/0/4/0. The extraction fix cannot be evaluated without runs across 33 LPs and multiple fixtures —
and Step 492 measured what one divall attempt costs.

**2. The extraction fix asks the model for the judgment this arc has repeatedly shown to be
unreliable.** Distinguishing "this document has no parking provision" from "I could not locate the
parking provision" is an entailment judgment. **Step 468 ruled out prompt-level strictness as a
*class* of fix precisely because the model's judgment is the defect** — the entailment test was read,
quoted, and then used to certify the very inferences it was written to block. Asking the extractor to
self-report absence invites the same failure with no independent check.

**3. The applicability fix is a set literal in a JSON schema.** Reversible in one line, auditable by
`git diff`, and its blast radius is one LP.

**4. It alone would have prevented the divall abort.** `not_applicable` ∈ `DEGRADABLE_APPLICABILITY`,
so even with extraction still returning `AMBIGUOUS`, the gate degrades rather than aborts. **The
extraction fix is not required to unblock divall.**

## C.3 But the extraction fix is the more valuable change, and I am not arguing against it

The brief's framing is right: **applicability fixes LP-16; extraction status would fix every LP whose
content is genuinely absent.** Step 494 found LP-16 *and* LP-17 both returning `AMBIGUOUS` with 0
chars — one genuinely absent, one present-but-lost. **`AMBIGUOUS` is currently doing the work of two
different facts, and that conflation is the general defect.**

**These are not alternatives on a schedule.** My recommendation is applicability **first** because it
is cheap, decided, reversible and unblocks divall — not because the extraction question should be
dropped. The extraction change is a `cam/core`-adjacent semantic change to what a status *means*, and
under CLAUDE.md it needs explicit authorization and its own measurement arc.

**One caution against doing extraction first:** if extraction begins returning `NOT_APPLICABLE` for
content it merely failed to find, **the gate stops firing on real extraction failures** — which is
the LP-17 case exactly. That would convert a loud abort into a silent false all-clear, the same
trade Step 482 measured and rejected for LP-12. **The extraction fix is the more dangerous of the
two and should not be done casually.**

---

## WHAT IS NOT ESTABLISHED

- **Whether C5 generalises beyond 32 fixtures.** It is fitted to them. 22 of the 32 are synthetics
  derived from one template, so the effective real-lease sample is **10**, of which 2 are negatives.
- **Whether `garage` is right for LP-16 at all.** It fires on 4 fixtures, but a garage clause could
  belong to a different issue area. Not checked.
- **The `.docx` and `.pdf` fixtures.** 9 files were skipped; only `.txt` was surveyed. The three
  documents with both forms (T-04, T-07, T-10) were covered by their `.txt` twins.
- **Whether flipping LP-16 to `not_applicable` changes any coverage verdict.** Applicability
  short-circuits produce zero element verdicts (Step 478), so divall's LP-16 would report as absent
  by design — correct here, but **unmeasured on the 28 positives**, which do not flip.
- **Whether divall completes with LP-16 resolved.** LP-07 still failed 1 of 4 attempts at Step 494.
