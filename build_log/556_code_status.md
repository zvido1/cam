# Step 556 — The code that produces the signal says "subsection". The code that consumes it treats it as the whole provision. And the module's own docstring already says which is right.

**Date:** 2026-09-04 · **Instruction:** `build_log/556_chat_instruction.md`
**DIAGNOSTIC. No code changed. Not deployed.** *(The two Step-555 re-runs are still executing; their results belong to Step 555's report, not this one.)*

---

# 1. WHAT THE DETECTOR EXAMINES — A MATCH ANYWHERE, AND IT KNOWS IT

`lease_negative_space.py:228-236`:

```python
        # ── 1. Reserved / Intentionally Omitted ──────────────────────────────
        if _RESERVED_PATTERN.search(tenant_text):
            match = _RESERVED_PATTERN.search(tenant_text)
            signals.append(_make_signal(
                "reserved_or_omitted",
                f"{provision_name}: section or subsection marked as omitted/reserved",
                match.group(0),
                severity="high",
            ))
```

**`.search(tenant_text)` — anywhere in the block.** No position test, no proportion test, no check that the match is the block's only content.

**And the signal it emits says so, in its own description string:**

> *"section **or subsection** marked as omitted/reserved"*

`lease_coverage.py:463-478`:

```python
        reserved_signals = [s for s in ns if s["signal_type"] == "reserved_or_omitted"]
        if reserved_signals:
            _a = _build_assessment(
                pid=pid, area=area, coverage_state="broken_xref",
                evidence_summary="Section or subsection explicitly marked as omitted or reserved",
                elements_found=[], elements_missing=get_expected_elements(pid),
                assessment_status="not_assessed",
            )
            ...
            continue
```

**`if reserved_signals:` — any signal at all.** It then asserts **every** expected element missing, marks the LP not-assessed, and `continue`s past the panel.

**The mismatch is exact and both halves are quotable.** The producer says *"section or subsection"*. The consumer carries the same words forward into `evidence_summary` — and then acts as though only the first alternative were possible.

## The module's docstring already states the correct design

`lease_negative_space.py:7-8`:

> *"Negative space signals are **EVIDENCE, not verdicts**. They feed into the coverage state assessor
> (Step 242) which makes the actual determination."*

**`lease_coverage.py:465` violates that contract.** It converts a signal into a terminal state and skips the assessor entirely. **This is not a missing rule; it is a documented rule that the consumer does not honour.**

---

# 2. THE BLOCKS, MEASURED

Across the six runs, seven LPs carry the signal. For each I stripped the placeholder, the section labels and the punctuation, and measured what prose remains in the block the detector saw:

```
run              LP        len  residue   ratio
ex6-4            LP-23    1380     1297   94.0%
solidpower(528)  LP-07    5199     4927   94.8%
solidpower(528)  LP-29    2793     2694   96.5%
solidpower(525)  LP-29    2793     2694   96.5%
divall(496)      LP-01    3053     2809   92.0%
divall(496)      LP-02     178       88   49.4%
divall(496)      LP-21      52       17   32.7%
```

**Five of seven blocks are ≥92% substantive text beside the placeholder.** The placeholder-and-nothing-else cases are the two at the bottom.

## Each, with the placeholder and what sits beside it

| LP | placeholder, verbatim | substantive text in the same block, verbatim |
|---|---|---|
| **divall LP-01** | *"3.1 One Time Fixed Rental Charge . **Intentionally Omitted** ."* | *"3.2 Base Rent . During the Term, Tenant covenants and agrees to pay to Landlord, in advance on the first day of each month…"* |
| **solidpower LP-29** | *"23. Certain Rights **Reserved** By Landlord"* | *"Provided that such actions shall not materially interfere with Tenant's use and quiet enjoyment… after giving Tenant reasonable notice thereof…"* |
| **solidpower LP-07** | `evidence: 'reserved'` — *"use of the roof(s) is **reserved** to Landlord"* (per corpus scan) | *"…the percentage obtained by dividing (a) the number of rentable square feet in the Premises… by the rentable square feet in the Building"* |
| **ex6-4 LP-23** | *"(b) Percentage Rent : **[intentionally omitted]**"* | *"Financial Statements : Tenant shall, within Ten (10) days after receipt of a written request from Landlord, furnish…"* — **Section 26(q), a different provision, misrouted into this block** |
| **divall LP-02** | *"1.15 Fixed Rent Increases: **Intentionally Omitted**"* ×3 | **none** — residue is *"Fixed Rent Increases / Lease Years to which Fixed Rent Increases Apply / Base Rent Increases"*, all clause titles |
| **divall LP-21** | *"ADDENDUM A PERSONAL GUARANTY - **Intentionally Omitted**"* | **none** — residue is *"PERSONAL GUARANTY"*, 17 characters, the label |

**The two genuine absences are the two blocks containing no prose at all.** That is the discriminator the evidence supports.

---

# 3. THE HONEST RULE — AND TWO CANDIDATES THAT FAILED BEFORE I FOUND IT

## Candidate A: residue ratio. REJECTED.

The ratios separate cleanly — 92–96.5% against 32.7–49.4%, a wide gap — **but ex6-4 LP-23 is a TRUE absence sitting at 94.0%**, because misrouted Financial Statements text inflates its block. Any threshold in the gap drops a true positive. **Step 495's first rule rejects it.**

## Candidate B: "short-circuit only when no expected element is found". REJECTED, and instructively.

```
run              LP     truth   found/total  -> decision
ex6-4            LP-23  TRUE        4/7      -> goes to panel   ** WRONG **
solidpower(528)  LP-07  FALSE       5/6      -> goes to panel   OK
solidpower(528)  LP-29  FALSE       5/6      -> goes to panel   OK
divall(496)      LP-01  FALSE       4/6      -> goes to panel   OK
divall(496)      LP-02  TRUE        0/4      -> SHORT-CIRCUIT   OK
divall(496)      LP-21  TRUE        3/7      -> goes to panel   ** WRONG **

TP=1 FP=0 TN=4 FN=2
```

**FN=2. It loses two true positives, so Step 495 rejects it — and the reason is worth recording.**

**`_assess_elements` matched on the label of the omitted clause.** divall LP-21's entire block is 52 characters — *"ADDENDUM A PERSONAL GUARANTY - Intentionally Omitted"* — and the matcher reports **3 of 7 elements present**: *guaranty type*, *duration of guaranty*, *survival of guaranty after assignment*. **All three fired on the single word "GUARANTY" in the title of the clause that was omitted.** LP-23 likewise matched *"gross sales definition"* and *"percentage rate"* off its own label plus misrouted text.

**A keyword matcher cannot be used to decide whether a clause exists, because the clause's name survives its omission.**

## Candidate C: prose-outside-labels. TP=2, FP=0, TN=3, FN=1.

Strip placeholders and section labels; keep segments of ≥6 words containing a verb.

```
run              LP     truth  prose-segs -> decision
ex6-4            LP-23  TRUE        1     -> goes to panel  ** MISS **
      first prose: "Financial Statements : Tenant shall, within Ten (10) days after receipt of..."
solidpower(528)  LP-07  FALSE       8     -> goes to panel  OK
solidpower(528)  LP-29  FALSE       7     -> goes to panel  OK
divall(496)      LP-01  FALSE       6     -> goes to panel  OK
      first prose: "Base Rent . During the Term, Tenant covenants and agrees to pay to Landlord..."
divall(496)      LP-02  TRUE        0     -> SHORT-CIRCUIT  OK
divall(496)      LP-21  TRUE        0     -> SHORT-CIRCUIT  OK
```

**Five of six correct, and the single miss is caused by an extraction routing error, not by the rule** — LP-23's only prose is Section 26(q), which is not about percentage rent.

## The proposal, and why "losing a true positive" needs care here

**Proposed test: short-circuit to `broken_xref` only when the block contains no prose outside labels and placeholders. Otherwise emit the signal as evidence and let the panel decide.**

**Step 495's rule was written for detection capability, and short-circuiting is not detection — it is a verdict.** Sending LP-23 to the panel does not lose the finding: the panel reads a block whose text still contains *"(b) Percentage Rent : [intentionally omitted]"*, and it returns a judged state with `assessment_status: assessed`. **That is strictly better than a canned string under `not_assessed`.** Under the strict framing the rule scores FN=1; under the framing that asks whether the reader ends up with a true statement, it scores 6 of 6.

**I am reporting both framings rather than choosing the one that flatters the proposal.** If the strict reading governs, the rule is rejected and the alternative is §1's conclusion: honour the docstring and stop short-circuiting at all.

---

# 4. THE HEDGE IS A SCHEMA CHANGE, AND IT IS A DIFFERENT FIELD FROM THE ONE STEP 545 TRACED

`lease_coverage.py:1059-1064`:

```python
    if coverage_state == "not_applicable":
        exposure = ""
    elif coverage_state in ("missing", "broken_xref"):
        exposure = get_risk_if_missing(pid) or get_exposure_statement(pid)
    else:
        exposure = get_exposure_statement(pid)
```

**`broken_xref` and `missing` read `risk_if_missing`. Every other state reads `exposure_statement`.**

**This corrects Step 554.** I reported the broken_xref prose as coming from *"the same static `exposure_statement`"* Step 545 traced for `review_needed`. The rendering path is the same catch-all, but **the source field is different**, and the difference is the whole point:

```
LP-21  exposure_statement : "Guaranty terms incompletely defined; guarantor's scope, duration..."
LP-21  risk_if_missing    : "If a guaranty was negotiated, landlord has no enforceable..."
LP-29  exposure_statement : "Landlord access terms undefined; landlord may enter without notice..."
LP-29  risk_if_missing    : "Landlord may enter premises without notice, at any time, for any purpose..."
```

**`risk_if_missing` is not badly written prose. It is correctly written prose for a state the LP is not in.** The field name says what it assumes; `broken_xref` breaks that assumption by using it for a provision that may be present.

## How consistent is the hedge?

```
risk_if_missing present on 32 of 32 LPs
  opens with a hedge (if / where / to the extent / absent):  4
     LP-04  "If deposit was negotiated, landlord has no documented security mechanism"
     LP-21  "If a guaranty was negotiated, landlord has no enforceable third-party recourse..."
     LP-24  "If premises are damaged, tenant has no guaranteed right to rent abatement..."
     LP-30  "If landlord cannot obtain tenant estoppels for a sale or financing..."
  contains any hedging word anywhere: 11
```

**Four of 32, and they are not the same kind of hedge.** LP-04, LP-21 and LP-30 hedge **whether the provision was ever negotiated** — the thing the detector cannot know. **LP-24 hedges the triggering event** (*"If premises are damaged"*), which is a different move and would not help here.

**So the model is three strings, not four**, and they exist because whoever wrote LP-04, LP-21 and LP-30 happened to think about conditionality. It is not a mechanism.

## Should the others adopt it? — Yes for the conditional LPs, and it is a schema edit

**Hedging is a schema change**: edit `risk_if_missing` in `retail_lease_knowledge.json`. **No code change, no pattern change.** The field is read verbatim.

**But it is a partial remedy and I want to be plain about that.** A hedge makes the sentence *defensible*; it does not make it *responsive*. *"If landlord access terms were negotiated, landlord may enter without notice"* is still the wrong thing to say about solidpower LP-29, whose lease devotes 2,793 characters to constraining exactly that. **The hedge helps where the provision is genuinely absent and the system cannot know whether it was ever bargained for. It does not help where the provision is present and the system failed to look.**

**§1's fix is the one that matters; §4's is the one that limits the damage when §1's cannot apply** — LP-02 and LP-21, where the block really is a placeholder and the panel would have nothing to read.

---

# WHAT IS NOT ESTABLISHED

- **Nothing was changed**, per the brief. The pattern was not touched and Cause B was not touched.
- **Seven LPs, six runs, four documents.** Every measurement in §2 and §3 is that population. A corpus-wide count of "placeholder plus substantive text in the same block" is **not** available, because Mode C does not persist the extraction `provisions` — I could only measure blocks that already carry the signal, which is a biased sample by construction (it excludes any block where the pattern did not fire).
- **The prose-outside-labels rule is a heuristic I wrote for this measurement**, not shipped code. Its verb list and 6-word floor are unvalidated beyond these six cases.
- **LP-23's misrouting was not investigated.** Section 26(q) Financial Statements text is in LP-23's block and should not be; that is an extraction-routing defect and it is the direct cause of the one miss in §3.
- **I did not measure how often a placeholder is the ENTIRE provision across the corpus** — only within the seven signalled blocks.
- **Step 554's claim that broken_xref prose comes from `exposure_statement` was wrong**; §4 corrects it to `risk_if_missing`. The Step-545 tracing for `review_needed` is unaffected and remains correct.
- **The two Step-555 re-runs are still executing.** Whether solidpower LP-29 reaches the panel, and what the panel then concludes, is unmeasured at the time of writing.
