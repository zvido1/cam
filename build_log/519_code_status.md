# Step 519 — Design. Do not retry: the document has no CAM provision, and the gate cannot say so.

**Date:** 2026-08-31 · **Instruction:** `build_log/519_chat_instruction.md`
**DESIGN ONLY. Nothing built, nothing edited, no provider calls, not deployed.**

---

# 0. THREE PREMISES IN THE BRIEF, CHECKED FIRST

## 0.1 There is no Step 518, and no Step 504 divall run

`ls build_log/ | grep 518` → nothing. `git log --all | grep 518` → nothing. Step 504 is the daily
model check; its status file contains no divall run.

**divall completed exactly once in this arc: Step 496, on attempt 2.** And that completion was not
clean:

```
496 divall: _harness_gate_attempts = 2
            extraction_completeness_failed = True  ['LP-30','LP-31','LP-32']
            invalid_for_legal_analysis   = True
            degraded_reason = extraction_completeness_failed
```

The retry did not produce a valid report. It converted a **hard abort on LP-07** into a
**degraded-but-delivered result flagged invalid for legal analysis** on LP-30/31/32. That is a real
improvement in user outcome, and it is not "completion."

Steps 492 and 494 both exhausted **4 attempts and never completed.**

## 0.2 "LP-07's shape variance" is not established anywhere

`grep -c "LP-07"` → **0 in `464_code_status.md`, 0 in `465_code_status.md`.**

Steps 464/465 are **Atlas** findings covering LP-00, LP-02, LP-12, LP-17. Step 464's own
not-established list says: *"Whether the three shapes reproduce on other documents or are an Atlas
artifact. One fixture."* Step 465 closes with: *"Whether shapes recur per-document or are
Atlas-specific. Untested."*

**The three-attractor result is Atlas. The gate failure is divall. Nobody has run a shape census on
divall.** The brief welds together two findings the record deliberately keeps apart.

## 0.3 The user does not see "a raw completeness-failure message"

`static/app.js:5489`, `:5589`, `:14393`:

```js
t.error && t.error.startsWith("GATE_ABORT:") ? "Not a commercial lease" : ...
```

**Four distinct causes raise `GateAbortError`** — document classifier (`lease_adapter.py:346`,
`:1391`), extraction integrity failure (`:1410`), all-extractors-unparseable (`:1424`), and 422C
completeness (`:1521`) — **and the frontend renders all four as "Not a commercial lease."**

A real, SEC-filed, executed commercial lease that trips the CAM gate is told it is not a commercial
lease. So is a user whose run died because *our own extractor broke*. **This is the arc's defect class
— one message for four facts — sitting on the user-facing surface.**

---

# 1. THE ACTUAL CAUSE: THE DIVALL LEASE HAS NO CAM PROVISION

`05 Lease Analyzer/test_data/tenants/divall_wendys_mtpleasant_lease.txt` — a freestanding
absolutely-net single-tenant Wendy's. Every occurrence of a CAM activation clue in the body:

**Line 599**, inside §6.1 *Maintenance and Repair by Tenant*:

> "In the event the Premises are or become subject to the common area maintenance charges, or other
> third party billings, Tenant shall be responsible therefor."

A **contingent pass-through** — one sentence allocating responsibility *if* CAM ever arises. It does
not establish a CAM regime.

**Line 727**, inside a radius-restriction carve-out:

> "...where all customers must enter the restaurant by first passing through common areas of the mall."

"Common areas" as geography, in a prohibited-use clause. Not CAM at all.

**There is no third occurrence.** No CAM article, no proportionate share, no expense pool.

**Extraction returning an empty LP-07 bucket is the correct extraction.**

## 1.1 A measurement hazard, scoped honestly

Lines 1–10 are a `#` provenance header written by the corpus importer, containing **"CAM
NEW_THREAD_PROMPT"**, **"triple-net NNN"**, and **"Absolutely Net"** — three LP-07 activation clues in
file metadata rather than lease text. `is_applicable()` substring-matches the whole document.

**This does not change the outcome here** — "common area" appears twice in the body independently, so
LP-07 is `applicable` either way. But fixtures carrying annotations that name the clues under test is
a latent validity problem for every applicability measurement taken on them. Production uploads are
PDF-extracted and carry no such header, so this is a harness issue, not a production bug.

---

# 2. Q4 — WHY THE SEAM DID NOT SAVE LP-07

Because **the seam worked and returned the right answer.**

`lease_adapter.py:1490`, the Step 484 comment, states it outright:

> "membership in `SPAN_EVIDENCE_LPS` is **NOT sufficient**, because elicitation can fall back (LP-07
> returned zero verified spans on divall). `_span_evidence` ... contains an LP only when elicitation
> **actually produced verified spans**, so the exemption is conditional on evidence existing rather
> than on the LP being listed."

The seam is a **second evidence route, not a gate bypass**. Membership guarantees the route is
attempted; it cannot guarantee arrival. Elicitation searched the document for verbatim CAM spans and
found none — **because there are none.**

**Contrast, from this arc's own runs:** on Atlas at Step 503, LP-12's `tenant_text_hash` was
`e3b0c44298fc1c14` — sha256 of the empty string. The bucket was empty and the run **completed with no
completeness failure**, because elicitation found real §13.2 spans. Same seam, same empty bucket,
opposite outcome. **The seam distinguishes "extraction lost it" from "the document lacks it." That is
exactly the distinction the gate needs and does not use.**

---

# 3. Q1 — BOTH SIDES, WEIGHED ON WHAT THE RETRY ACTUALLY DID

## What attempt 2 put in LP-07 (from `496 divall run_01_full.json`)

```
LP-07  applicability  = applicable
       coverage_state = missing
       tenant_text len = 1260
```

> "6.1 Maintenance and Repair by Tenant. (a) Tenant shall, at its own cost and expense, keep, maintain
> and repair the Premises in good condition... In the event the Premises are or become subject to the
> common area maintenance charges, or other third party billings, Tenant shall be responsible
> therefor..."

**The retry did not find CAM evidence. It filed the tenant's repair covenant into the CAM bucket.**
The panel then read it correctly: `coverage_state = missing`, **0 of 6 elements present, 3/3
evaluators**.

**The gate's predicate is that `tenant_text` is non-empty. It does not ask whether the text is
relevant.** So on a document that genuinely lacks the provision, the *accurate* extraction (empty
bucket) triggers a hard abort, and the *sloppy* extraction (adjacent clause mis-filed) sails through
— and produces the correct verdict. **The gate punishes the more accurate extraction.**

That is what "retry until the gate passes" buys here: not a better shape, but a looser one.

## Correction to a hypothesis I held before checking

I expected the mis-filing to have *stolen* §6.1 from LP-06 under 421C exclusive assignment. **It did
not.** On this run the clause is duplicated:

```
LP-06 Maintenance & Repairs   len 2347  state partial
LP-07 CAM                     len 1260  state missing
LP-28 Compliance with Laws    len 2347  state missing
```

**No content was lost on this run.** The correctness cost of the 496 retry was *not* cross-filing
damage — it was that the run's validity depended on extraction being imprecise.

## For retry

- The failure is genuinely non-deterministic; attempts 1 and 2 differed with nothing tuned.
- The alternative today is telling a user with a valid lease that it is **not a commercial lease**.
- On the one observed instance the retry produced the **correct** LP-07 verdict and lost nothing.
- Cost is one extraction call, ~100s.

## Against retry

- **It optimises for a non-empty bucket, which is not the property we want.** The worry in the brief
  is confirmed, and the mechanism is worse than described: the winning extraction here *manufactured*
  coverage from a repair clause rather than choosing between two real shapes.
- **Step 465's Atlas evidence shows the shapes genuinely differ in content**, and that a plausible
  selection rule picks the losing one: *"'Majority wins' gives B for both, which loses §13.2 and
  re-aborts the gate."*
- **A retry that succeeds hides the defect.** Two of the four abort causes are *our* breakage
  (integrity failure, all-extractors-unparseable). Retrying those masks an outage.
- **It is unbounded in principle.** Steps 492 and 494 burned four attempts each and still failed —
  ~400s of extraction to arrive at the same place.

## Verdict

**Retry is treating a symptom, and the symptom is a gate that cannot express "correctly absent."**
Every argument for retry is really an argument that a hard abort is the wrong response to an empty
bucket on a document that genuinely lacks the provision. Fixing that removes the need for the retry
and does not risk selecting a worse extraction.

---

# 4. RECOMMENDATION — three changes, none of them a retry, in this order

## (A) Split the four abort causes at the user surface — do this regardless

Give `GateAbortError` a `reason_code` (`not_a_lease` / `extractor_broken` / `extraction_unparseable` /
`incomplete_evidence`) and branch `app.js` on it. **A valid lease is being told it is not a lease
today**, and a provider outage is being blamed on the user's document. This is a correctness bug on
the user surface, independent of everything else in this step, and it carries no epistemic risk.

## (B) Let the seam report *searched-and-found-nothing* — the real fix

`_span_evidence` records only LPs where elicitation **produced** verified spans. The complementary
fact — **elicitation ran, searched the whole document, and verified zero spans** — is currently
indistinguishable from "elicitation never ran."

Those are different facts, and the difference is exactly what the gate lacks:

| bucket | seam result | correct reading |
|---|---|---|
| empty | verified spans found | evidence exists, bucket mis-assigned → **exempt** (today's behaviour) |
| empty | **searched, zero verified spans** | **evidence absent from the document** → degrade, let the panel say `missing` |
| empty | seam did not run | unknown → abort (today's behaviour, correctly) |

**A whole-document verbatim search returning nothing is positive evidence of absence in a way an empty
bucket alone is never.** The gate's founding premise is that *missing required evidence is
indistinguishable from evidence the extractor lost* — and the seam is precisely the instrument that
makes it distinguishable.

The panel already handles the outcome correctly: given a mis-filed repair clause it returned
`missing`, 0/6 elements, 3/3 evaluators. Given nothing, it returns the same verdict on sounder
footing.

**Cost: zero additional provider calls.** Elicitation already runs for the four `SPAN_EVIDENCE_LPS`.

**This requires explicit authorization.** It changes 422C gate semantics — a frozen epistemic
artifact. I am not building it. The risk to weigh: it narrows the gate, and a bug in the seam's
"searched" flag would silently convert real extraction loss into a `missing` verdict. That flag must
be set only on a completed elicitation, never on a fallback or an exception — the same
`served` / `is_fallback` discipline as Step 497.

## (C) Retry only after (B), only if it still fails, and never blind

If (B) lands and divall still aborts, a bounded retry becomes defensible:

- **2 attempts, not 4.** 492 and 494 show 4 buys nothing; the one success came on attempt 2.
- **Only for `incomplete_evidence`.** Never retry `not_a_lease` (futile), never retry
  `extractor_broken` or `extraction_unparseable` (masks our outage — the Aug 26 lesson).
- **Record it on the result:** `extraction_attempts`, `extraction_shape_digest`, and the failed-LP
  list per attempt. A run that took two tries must never be indistinguishable from one that took one.
- **Tell the user afterwards, not during.** "Extraction was repeated once to obtain complete evidence"
  belongs with the Step-497 disclosure surfaces. The run is already 12–15 minutes and a retry is not a
  user-actionable event.

---

# 5. Q3 — WHAT THE USER GETS IF WE DO NOT RETRY

Under (A)+(B) the divall case stops being a failure at all: the report is delivered, LP-07 reads
`missing` with 0/6 elements and 3/3 evaluator agreement, and the result carries
`invalid_for_legal_analysis` only if some *other* LP is genuinely incomplete.

If a hard abort does remain right for some document, the message must say which LP, that the document
appears to lack it, and that this is a completeness limit rather than a verdict on the document's type
— **never "Not a commercial lease."**

---

# WHAT THIS DOES NOT ESTABLISH

- **Whether divall has shape attractors at all.** No shape census has been run on it. The LP-07
  variance between attempts 1 and 2 is observed; its structure is not characterised. Everything about
  three stable shapes is an **Atlas** result.
- **Whether (B) generalises.** The empty-bucket/absent-provision case is demonstrated on one LP of one
  document. LP-12 on Atlas is the counter-case and is handled correctly today.
- **Whether the panel is reliable on genuinely absent provisions.** It returned `missing` 3/3 here;
  Step 460 showed the panel can be handed correct evidence and still return a false positive on
  adjacent material.
- **n = 1 for the retry's success.** One divall completion, still flagged invalid.
- **Nothing was built, run, or deployed.** No provider calls were made in this step.
