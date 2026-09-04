# Step 560 — The three labels are wrong, and correcting them changes the answer: 535's rule fixes two of the three LP-20 causes but unblocks only one document.

**Date:** 2026-09-04 · **Instruction:** `build_log/560_chat_instruction.md`
**DESIGN. No code changed, no clue list touched. Not deployed.**

---

# 0. PREMISE CORRECTION — ALL THREE CHARACTERISATIONS

Measured by running Step 535's documented rule against each document (throwaway script, repo unchanged):

| document | brief says | **what it actually is** | 535's rule |
|---|---|---|---|
| everbridge | negation | **subject error** — *"**Landlord** shall have the exclusive right to conduct such contests, protests…"*, ×3 occurrences | **STILL ACTIVATES** |
| ncino | enumeration item | **negation** — 5 hits, all negated | **SUPPRESSED** |
| albireo | third-party covenant | **negation** — 1 hit, `non-exclusive use` | **SUPPRESSED** |

**Step 535 already recorded everbridge's LP-20 correctly** — *"a **subject** error. Landlord holds the
right, not Tenant. There is no negation to detect."* The brief has swapped it with ncino's.

**The enumeration case is everbridge LP-23**, not ncino LP-20 — *"(xxxi) Fixed or percentage rent under
any ground or underlying lease"*, item xxxi of an exclusions list. **535's rule suppresses it.**

**The third-party-covenant case is ex6-4 LP-20** — Dollar Tree's exclusive inside a 23-page Existing
Exclusives schedule. **ex6-4 did not abort.** It completed, and the panel returned 0 of 7 elements
present, which is the correct answer.

## What that does to the arithmetic

**535's negation rule addresses two of the three LP-20 causes, not one.** But **it unblocks one
document, not two**, because two of the three have a second blocker it cannot reach:

```
ncino       aborts on LP-20 only              -> LP-20 suppressed  =>  WOULD COMPLETE
albireo     aborts on LP-20 + LP-21           -> LP-21 survives    =>  STILL ABORTS
everbridge  aborts on LP-20 + LP-21 + LP-23   -> LP-20, LP-21 survive => STILL ABORTS
```

**One of three real leases unblocked.** That is the honest figure, and it is neither the brief's
"one of three causes" nor Step 535's "2 of 4 calls".

---

# 1. WHAT APPLICABILITY IS FOR — TWO CONSUMERS, AND THEY WANT OPPOSITE ERRORS

**It is not only the abort decision.** `is_applicable` has two consumers.

**Consumer A — `lease_coverage.py:377`, and it is the bigger one:**

```python
        applicability_result = is_applicable(pid, full_tenant_text)

        if applicability_result in ("excluded", "not_applicable"):
            ... coverage_state="not_applicable", assessment_status="not_assessed" ...
            continue
        if applicability_result == "unclear":
            ... coverage_state=get_default_when_unclear(pid), assessment_status="not_assessed" ...
            continue
```

**Three of five values skip the panel entirely, on every run, for every LP.** Applicability decides
whether the provision is evaluated at all.

**Consumer B — `lease_adapter.py:1549`, the 422C gate:**

```python
        _applicability_by_lp = {pid: _is_applicable(pid, _doc_lower) for pid in _failed_ids}
        _must_abort = [pid for pid, ap in _applicability_by_lp.items()
                       if ap not in DEGRADABLE_APPLICABILITY and pid not in _span_evidence]
```

## The asymmetry is the finding

| error | effect in A (panel routing) | effect in B (the gate) |
|---|---|---|
| false **`applicable`** | **harmless** — the LP goes to the panel, which is what we want | **fatal** — aborts the run |
| false **`not_applicable`/`unclear`** | **silent and harmful** — a real provision is never judged | harmless — degrades |

**A permissive matcher is safe in A and fatal in B; a strict matcher is the reverse.** One function
serves two consumers whose failure modes point in opposite directions, and it is tuned for neither.

**And its reach is narrower than it looks: the matcher decides 12 of 32 LPs.** The other 20 have empty
`activation_clues` and return `required` unconditionally.

```
WITH activation_clues (matcher decides): 12
  LP-04, LP-07, LP-12, LP-15, LP-16, LP-20, LP-21, LP-22, LP-23, LP-30, LP-31, LP-32
WITHOUT (always 'required'):             20
```

---

# 2. IS THE MATCHER THE RIGHT LAYER? — NO, AND STEP 494's CASE IS NOT THE OBSTACLE

**The panel outperforms it on the same phrase in the same document.** ex6-4 contains 23 pages of other
tenants' exclusive-use covenants; the matcher called LP-20 `applicable`, and the panel returned
**0 of 7 elements present** — the correct answer, reached by reading whose covenant it is.

## Step 494's LP-17 does not constrain this, and the brief's premise needs correcting

```
LP-17  activation_clues: []
       is_applicable(LP-17, divall)  = required
       is_applicable(LP-17, albireo) = required
```

**LP-17 is `required`. The matcher never decides it, so no change to the matcher can affect it.** And
Step 494's own title is *"LP-17 seamed: fixed on both fixtures"* — **it stopped aborting because the 423
seam supplied verified spans, not because applicability caught anything.** The case the brief asks me to
preserve is preserved by construction.

## What would actually break

**Every abort we have on record is on a conditional LP.** albireo's failed set is LP-12, LP-16, LP-20,
LP-21, LP-23, LP-31; everbridge's and ncino's are LP-12, LP-20, LP-21, LP-23, LP-31; divall's were
LP-07 and LP-16. **All of them are in the conditional 12. Not one `required` LP has ever failed
extraction in a recorded run.**

**So the protective value of `applicable ⇒ must_abort` is unmeasured.** It has never once fired on a
`required` LP, and every time it has fired on a conditional LP the classification was false.

**The real loss** if the gate stops aborting on conditional LPs: a conditional provision that genuinely
IS in the lease, which extraction genuinely missed, would degrade to `not_assessed` instead of stopping
the run. **That is a real regression and I am not going to minimise it** — it is the exact failure the
422C gate was built for. It has simply never been observed.

---

# 3. IF THE MATCHER STAYS — CAN A SUBSTRING RULE ANSWER "WHOSE OBLIGATION"? NO.

**Negation** is tractable and Step 535 measured it: sentence-scoped preceding span, refined tokens,
zero synthetic recall loss. **It handles ncino and albireo.**

**Enumeration** is also tractable in principle — everbridge LP-23's hit is *"(xxxi) Fixed or percentage
rent under any ground or underlying lease"*, and 535's rule already suppresses it via the `exclud*`
token in the list's preamble. **Not a separate problem in the one case we have.**

**Attribution is not tractable, and this is the honest answer.** Two shapes:

> **everbridge:** *"**Landlord** shall have the exclusive right to conduct such contests, protests and
> appeals of the Taxes"* — the subject sits four words before the clue. A window short enough to be
> precise misses it; a window long enough to catch it reaches unrelated sentences. Step 535 measured
> exactly this trade-off and rejected the whole-sentence variant for it.

> **ex6-4:** *"Dollar Tree shall have the exclusive right to operate a single price point variety
> retail store"* — **grammatically correct, factually true, and about a different tenant.** There is no
> negation, no enumeration, and no lexical marker of any kind. The only thing that makes it
> inapplicable is knowing that Dollar Tree is not this lease's tenant.

**A substring matcher cannot answer "whose obligation is this", because the answer depends on resolving
a party name against the lease's own definition of Tenant.** That is a reading task. **Every rule that
tries will be a proxy, and the proxy will fail on the case that matters most — a real exclusive
belonging to someone else, which is precisely the case a retail tenant is paying to have found.**

---

# 4. albireo's TRUE POSITIVES — HALF THE PREMISE HOLDS

**LP-12 Early Termination — real, and the rule preserves it.** Three occurrences, **all three survive**:

> *"If the Premises or the Building are deemed 'substantially damaged,' **Landlord may elect to
> terminate this Lease** by giving Tenant wri…"*
> *"…the Premises are rendered untenantable for the Permitted Use, then **Tenant may elect to terminate
> this Lease** by giving Landlord wr…"*
> *"…notice of such termination within sixty (60) days after the Event of Casualty. **If either party
> elects to terminate this Lease** as set forth above…"*

**Genuine casualty-termination rights, held by both parties, and 535's rule touches none of them.** The
falsification base the brief asked for exists and the rule passes it.

**LP-23 Percentage Rent — albireo has NONE.**

```
LP-23  albireo   0 hit(s)
```

**Not one activation clue matches anywhere in the document.** Albireo is a lab/office lease; there is no
percentage rent, so it contributes no true positive for LP-23 and cannot falsify anything about it. **The
brief's "real percentage rent" is not in this document.**

**Comparison across the three, under the rule:**

```
LP-12   everbridge  4 hits, 2 survive -> ACTIVATES   ncino 3/2 -> ACTIVATES   albireo 3/3 -> ACTIVATES
LP-23   everbridge  1 hit,  0 survive -> suppressed  ncino 0/0                albireo 0/0
LP-20   everbridge  5 hits, 3 survive -> ACTIVATES   ncino 5/0 -> suppressed  albireo 1/0 -> suppressed
```

**LP-12 activates on all three and should** — every one of them has a real termination provision. **The
rule is recall-neutral on the only true positives these documents contain.**

---

# 5. CHEAPEST vs MOST CORRECT — THEY ARE DIFFERENT, AND I AM LABELLING WHICH IS WHICH

## CHEAPEST — one constant. Unblocks all three today.

```python
DEGRADABLE_APPLICABILITY = {"not_applicable", "unclear", "applicable"}
```

**Effect:** `_must_abort` becomes empty for every conditional LP, so albireo, everbridge and ncino all
complete as degraded runs. **`required` LPs still abort**, which is the strongest signal and the one
that has never yet been exercised.

**This is NOT the most correct thing.** It makes the gate blind to a genuine extraction failure on any
of the 12 conditional LPs. **It trades a measured false-abort rate of 3-of-4-documents against an
unmeasured true-abort rate of zero-so-far.** That trade is defensible on the evidence and indefensible
in principle, and the difference matters because the evidence is four documents.

## MIDDLE — Step 535's negation rule. ~30 lines, measured, recall-neutral.

**Unblocks ncino only.** Preserves every synthetic true positive (measured at 535: zero loss across 12
conditional LPs) and every albireo LP-12 hit (measured here). **Correct as far as it goes, and it does
not go far enough to unblock the documents that matter most.**

## MOST CORRECT — move the question to the panel.

Let conditional LPs through to the panel and let it decide applicability as part of the reading, which
it already does better. **Applicability stops being a substring question and becomes an evidence
question.** ex6-4 is the proof it works: 0 of 7, on 23 pages designed to fool exactly this.

**Cost:** panel calls for LPs that are genuinely absent — roughly 12 LPs × 3 evaluators on documents
where several do not apply. **And it does not remove the gate problem**, because an LP the panel would
have found inapplicable still has empty extraction and still hits consumer B. **The gate would need the
cheap change as well.** The two are complementary, not alternatives.

## What I would do, stated as a recommendation and not a decision

**The cheap change plus the seam is what unblocks the corpus; the panel change is what makes
applicability right.** If only one is authorised, the cheap one is the one that turns three aborted
documents into three readable reports today — **and its cost is that the 422C gate stops protecting a
case we have never seen it protect.** Whether that trade is acceptable is a judgement about how much
the unobserved failure matters, and that is not mine to make.

---

# WHAT IS NOT ESTABLISHED

- **Nothing was built and no clue list was touched**, per the brief.
- **All three of the brief's document characterisations were wrong**, and §0 corrects them by
  measurement. If the labels came from a source I have not seen, that source needs correcting too.
- **"Every recorded abort is on a conditional LP" covers four documents** — albireo, everbridge, ncino,
  divall. It is a real pattern in the data we have and not a proof about leases in general.
- **The cheap change was not simulated end to end.** I reasoned it from the gate code
  (`_must_abort` empties ⇒ `GATE_ABORT_RETURNS_DEGRADED` degrades instead of raising); I did not run a
  document with the constant changed.
- **The panel-decides proposal has one measurement behind it** — ex6-4's 0 of 7. One document, one LP.
- **I did not measure what the panel would cost** in calls or minutes if 12 conditional LPs always ran.
- **LP-21 was not analysed in §3.** Its albireo blocker is `Guarantor: None` and `guarantor (if any)` —
  post-positional absence markers, a fourth shape, reported at Step 559 and not addressed here because
  the brief scoped this step to LP-20.
