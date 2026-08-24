# Finding: widening context made precision worse, not better

**Date:** 2026-08-23 · **Status:** MEASURED, direction RULED OUT, rolled back.
**Steps:** 466 (measurement), 467 (rollback and this record).
**Rollback:** `SECTION_EXPANDED_SPAN_LPS = set()` in `cam/adapters/lease_review/lease_coverage.py`.
The machinery is left in place — `_section_bounds_for_offset` and the expansion branch are measured
and may be wanted later. **Only the flag is empty.**
**Companions:** `460_LP27_precision_evidence.md` (the precision measurement this responds to),
`466_code_status.md` (the full run detail).

---

## 1. Containing-section expansion cannot reach §11.3

`460_LP27_precision_evidence.md` §1B recorded that the panel received §11.2's indemnity and never saw
§11.3's liability cap, and named **two candidate directions**. This measures the section-boundary one.

**It cannot work, and that was established offline before spending any runs:**

```
[Section 5.1]   offsets  8631- 9905   1272 chars
[Section 11.2]  offsets 14905-15490    583 chars
'Limitation of Liability' present: False    '11.3' present: False
```

**§11.2's section ends at 15490. §11.3 begins at 15490.** Expansion widens a span to its *containing*
section; the liability cap is a *different* section. The mechanism stops at the exact doorstep of the
239-character gap it was meant to close.

Confirmed in the runs: **zero mentions** of the liability cap, consequential damages, or §11.3 in any
evaluator's reasoning across both runs.

**Of the two candidate directions, the section-boundary one is now RULED OUT. CO-RETRIEVAL OF ADJACENT
TEXT remains untested and is the only one of the two that could reach a neighbouring section.**

## 2. Cost: +81% evidence, zero new element-relevant content

| | baseline (Step 457, clause bodies) | expanded (Step 466) |
|---|---|---|
| assembled evidence | 1043 chars | **1886 chars (+81%)** |
| units | 8 spans | 2 sections |
| provider cost | 94 calls, ~723s | 94 / 93 calls, 719s / 727s |

The 843 added characters are **§5.1's security-deposit prose** and **§11.2 subsections (b) and (c)** —
negligence and condition of common areas. That is precisely the material the clause-body spans had
**correctly excluded**.

**This trades under-inclusion across sections for over-inclusion within one — the bucket failure,
reintroduced.** Extraction buckets over-included within a section (LP-27's bucket led with Security
Deposit prose); span elicitation under-included across sections. Section expansion does not resolve
the dilemma, it moves back along it.

Provider cost is unchanged: expansion is a text-assembly change, not an extra retrieval.

## 3. THE REGRESSION — the substantive result

**Element 4, "Tenant may perform landlord's obligation and offset against rent", moved from a correct
`missing` to `disputed`.** Merge reason `distant_split_presence_missing`, confidence `low`.
**Identical in both runs — a stable regression, not noise.**

Step 460 recorded element 4 as the panel's *best* moment: the one place it declined a near-miss,
because the element asks for offset against **rent** and the lease gives setoff against the **security
deposit**.

With the full §5.1 in view:

- **A (claude-sonnet-4-6) → `explicitly_present`**, citing `Section 5.1`, quoting *"Tenant shall have
  the right to draw upon the Security Deposit as a setoff against damages"* — *"…which constitutes an
  explicit self-help and offset [right]"*.
- **B (gpt-5.5) → `missing`**: *"The lease allows Tenant to draw upon the Security Deposit as a setoff
  against damages, but it does not expressly allow Tenant to perform Landlord's obligation or offset
  costs against Rent."*
- **C (grok-4.3) → `missing`**: *"Section 5.1 permits drawing on the Security Deposit as a setoff
  against damages but does not authorize Tenant to perform Landlord's obligations and offset costs
  against rent."*

**B and C held the exact distinction they held at baseline. A did not. The only thing that changed was
that A was shown more of §5.1.**

Note the accounting artefact: `elements_missing` went 1 → 0, which reads on the surface like an
improvement. It is not. The element left `elements_missing` **without joining `elements_found`** — it
now sits in neither, as a low-confidence dispute. **A headline count improved while the answer got
worse.**

## 4. THE INFERENCE

**More context did not improve reasoning. It supplied more topically adjacent material to be seduced
by.**

This is a direct measurement of the **operative-entailment problem**. The failure mode throughout this
arc is that **topical proximity substitutes for entailment** — evidence that is *about* the right
subject is accepted as evidence that *establishes* the proposition. Step 460 measured it on elements 6
and 7. Step 466 tested whether more context helps, and the answer is that **adding proximity makes it
worse**: the extra §5.1 text was topically adjacent to self-help/offset and nothing more, and one
evaluator took it as entailing the element.

**Any future context-widening direction inherits this.** Co-retrieval of adjacent text — the surviving
candidate from §1 — is itself a context-widening direction, so it inherits it too. It may still be
worth testing, because §11.3 is a *qualifier* whose effect on a verdict is subtractive rather than
additive, but it must be measured against precision on the previously-clean elements, not only against
whether §11.3 arrives.

**The general lesson: an evidence-widening change must be evaluated on the elements it was NOT aimed
at.** Element 4 was not the target of this change and is where the damage landed.

## 5. Elements 6 and 7 — unchanged and worse-stabilised

**Element 6 (monetary damages): unchanged.** Still `explicitly_present` at high confidence, both runs,
still resting on §11.2's indemnity. The expansion added §11.2(b) and (c), which are *further* from a
damages grant, not closer. **The false positive stands, and the clause that limits damages is still
absent.**

**Element 7 (specific performance): stabilised to `implicitly_present` in both runs**, where the
baseline disagreed (`explicitly_present` / `implicitly_present`).

**This is worse than the baseline disagreement, not better.** Every judgment still rests on §5.1's
savings clause; `"specific performance"`, `"injunctive"` and `"equitable relief"` remain **0-hit in the
lease**. The verdict is wrong either way — but the baseline's run-to-run disagreement was a *signal
that the evidence was thin*, and the expansion removed the signal while leaving the error. **Stability
on a wrong answer suppresses the only indicator that anything was amiss.**

## What is NOT established

- Whether co-retrieval of adjacent text reaches §11.3, and at what precision cost. Untested.
- Whether element 4's regression generalises, or is specific to §5.1's structure — a landlord-default
  paragraph appended to a security-deposit clause, where the adjacent text is unusually confusable.
- Whether expansion would behave differently on another LP. LP-27 only; LP-07 was left unexpanded.
- Two runs. The regression is identical in both, but n=2.
