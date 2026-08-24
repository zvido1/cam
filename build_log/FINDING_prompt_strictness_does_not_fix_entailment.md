# Finding: prompt-level strictness does not fix entailment errors

**Date:** 2026-08-23 · **Status:** MEASURED. Flag left ON at zero cost.
**Step:** 468 (measurement), recorded here at Step 469 Part B.
**Config:** `ENTAILMENT_TEST_LPS = {"LP-27"}` in `lease_coverage_305.py`, injected into the per-LP 305
user prompt before the element list. Evidence, spans, locators and `SPAN_EVIDENCE_LPS` untouched;
`SECTION_EXPANDED_SPAN_LPS = set()` throughout. Two runs, clean panel (`gpt-5.5` 197/197,
`is_fallback` False).
**Rollback:** `ENTAILMENT_TEST_LPS = set()`.
**Companions:** `460_LP27_precision_evidence.md`, `FINDING_context_widening_regression.md`,
`468_code_status.md`, `469_code_status.md` (the TBD escape-hatch census).

---

## What was tried

Step 466 established that widening the *evidence* made precision worse. The remaining lever was the
panel's *instructions*. An operative-entailment test was added to LP-27's prompt: a clause supports an
element only if its legal effect entails it; topic overlap is insufficient; grant, trigger,
beneficiary and remedy must align; indemnities, waivers, definitions, limitations and general
"all remedies" language do not satisfy a specific-remedy element unless they create or expressly
identify that remedy.

## The full table

`b` = Step 457 baseline · `e` = Step 468 with the entailment test

| # | element | b1 | b3 | **e1** | **e2** | |
|---|---|---|---|---|---|---|
| 1 | Landlord default is defined | EXP | EXP | **EXP** | **EXP** | unchanged |
| 2 | Written notice of default | EXP | EXP | **EXP** | **EXP** | unchanged |
| 3 | Cure period specified | EXP | EXP | **EXP** | **EXP** | unchanged |
| 4 | Self-help / offset against rent | MIS | MIS | **MIS** | **MIS** | unchanged (correct) |
| 5 | Right to terminate | EXP | EXP | **EXP** | **EXP** | unchanged |
| 6 | **Monetary damages** | EXP | EXP | **EXP** | **EXP** | **still false** |
| 7 | **Specific performance** | EXP | IMP | **IMP** | **IMP** | **still false** |
| 8 | Lender notice and cure | MIS | MIS | **MIS** | **MIS** | unchanged |
| 9 | Common law remedies preserved | EXP | EXP | **EXP** | **EXP** | unchanged |
| 10 | Remedies cumulative | IMP | IMP | **IMP** | **IMP** | unchanged |

LP-level both runs: `partial` · materiality `high` · confidence `high` · 8 found / 1 missing / 0
unclear · merge reasons `{None: 10}`.

## The precision check PASSES

**Elements 1, 2, 3, 5, 8, 9, 10 are identical to baseline in both runs.** No correct finding was
suppressed. No disputes, no `citation_required_but_absent`, no `unclear`.

Against the criterion Step 467 established — *an intervention must be evaluated on the elements it was
not aimed at* — **this is the first intervention in the arc with no measured cost.** Step 466 cost a
correct verdict; this costs nothing.

## Elements 6 and 7: unchanged

Both false positives survive. Element 6 remains `explicitly_present` at high confidence on §11.2's
indemnity; element 7 remains presence-tier on the savings clause.

## THE MECHANISM — the headline

**An instruction to check entailment is evaluated by the same model whose entailment judgment is the
defect.**

The block was read. It was then used to *certify* the very inferences it was written to block.

**B, on element 6, using the block's own framing to justify the false positive:**

> *"Section 11.2 expressly obligates Landlord to indemnify Tenant against damages arising from
> Landlord's breach or default. This creates an express monetary recovery right tied to landlord
> default, **rather than merely relying on general remedies language**."*

The final clause is B distinguishing itself from the failure mode the block describes — reaching for
the test's vocabulary to certify an indemnity as a damages grant. C, run 2, does the same more
directly: *"Indemnity clause directly imposes liability for damages arising from landlord breach,
**satisfying the element without unstated inference**."*

**C, on element 7, invoking the test by name to reach the opposite conclusion:**

> *"Reservation of equity remedies **entails** specific performance and injunctive relief **under the
> entailment test**."*

The same test, named explicitly, applied to the same savings clause, yielding the conclusion it was
written to prevent. **Asking the panel to apply a stricter standard does not help when the panel's
application of the standard is the thing that is wrong.**

Engagement was also uneven — judgments using entailment vocabulary: 1 and 2 in the baseline runs, 2 and
**6** in the two test runs. Run 2 shows real uptake; run 1 barely differs from baseline. Where it was
read, it was as often used to license a verdict as to withhold one.

## B's route-around on element 7

B is the one evaluator on whom the test worked as intended, and the merge absorbed it anyway.

> *"The lease includes only general language preserving remedies at law or in equity, **which does not
> expressly identify specific performance or injunctive relief**. Because the schema marks default-law
> coverage as jurisdiction-dependent, equitable remedies may be available…"*

B **correctly rejected the savings clause as textual support** — then returned
`covered_by_default_law` rather than `missing`. That verdict is in `PRESENCE_VERDICTS` and
`_PRESENCE_TIER`, so all three evaluators landed in the presence tier, **no dissent was recorded**, and
the merge reported `implicitly_present` at high confidence.

Had B returned `missing`, the merge would still have been a presence majority — but with a recorded
dissent. **The route did not change the verdict; it erased the signal that an evaluator disagreed with
its basis.**

The route is schema-sanctioned on an unfilled placeholder. `469_code_status.md` censuses this: **18 of
18 jurisdiction-dependent elements in the schema are unfilled `TBD_BY_ATTORNEY_REVIEW`, zero are
populated**, spanning LP-09, LP-11, LP-26 and LP-27 — and **five of LP-27's ten elements**, including
both false positives. `_normalize_verdict` tests only truthiness, so a non-empty placeholder string
passes.

## Element 4 — correct, but do not credit this change

`missing` in both runs, matching baseline. The Step-466 regression is gone, **but that is the expansion
rollback, not this change**: baseline already had `missing` with expansion off. The entailment test
neither helped nor hurt element 4. Its reasoning did absorb the vocabulary — C: the setoff *"does not
entail tenant performing the obligation and offsetting rent"* — but the verdict was already right.

## WHAT THIS RULES OUT

**Prompt-level strictness is ruled out as a class of fix for entailment errors.**

Not this wording — the class. The defect is that the model's judgment of what a clause entails is
unreliable on topically adjacent material. An instruction is only as good as the judgment that applies
it, and here the same judgment is on both sides of the test. Three observations make the class
conclusion rather than a wording conclusion:

1. The test was **read and understood** — evaluators quote its criteria accurately, distinguish
   "general remedies language", and use "without unstated inference" correctly as a phrase.
2. It was **applied and passed** by the same clauses it targets. The block names indemnities and
   general "all remedies" language explicitly, and evaluators certified an indemnity and a savings
   clause anyway.
3. Where it **did** bite (B, element 7), the panel architecture absorbed the result through a
   presence-tier verdict, so the correct judgment left no trace in the output.

A stronger wording, or promotion to a system-prompt hard rule, would be a different instance of the
same class. **What is not ruled out is anything that does not route the judgment through the same
model on the same evidence** — a deterministic check, a different evaluator population, or a
structural constraint on which clause types can satisfy which element types.

## Disposition

**Flag left ON.** It has no measured cost, and it is the only intervention so far that can be said of.
It also produced the one useful side effect in this arc: B's correct rejection on element 7, which is
what exposed the TBD escape hatch. **This is a disposition for Tzvi, not a decision taken here.**

## What is NOT established

- Whether element 7's `IMP`/`IMP` is stabilisation or chance. Baseline was split `EXP`/`IMP`; two runs
  landing alike has ~25% probability under a coin flip. n=2.
- Whether stronger wording or a system-prompt hard rule would bite. Not tried; the brief said do not
  tune. The class argument above predicts it would not, but that is an inference, not a measurement.
- Whether the test helps on any LP other than LP-27.
- Two runs.
