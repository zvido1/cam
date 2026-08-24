# Step 468 — Operative entailment test, LP-27: measured

**Date:** 2026-08-23 · **Instruction:** `build_log/468_chat_instruction.md`
**PART A:** `Docs/CAM_Current_State.md` item 1B corrected.
**PART B:** MEASUREMENT. Two runs, clean panel (`gpt-5.5` 197/197, `is_fallback` False both runs).
`ENTAILMENT_TEST_LPS = {"LP-27"}`. Evidence, spans, locators and `SPAN_EVIDENCE_LPS` untouched;
`SECTION_EXPANDED_SPAN_LPS = set()` throughout. Nothing tuned. Not deployed.

---

## Headline

**The entailment test costs nothing and fixes nothing.** No previously-clean element moved — the
precision check passes cleanly. Neither false positive was corrected. The test is being **invoked as
justification rather than applied as a filter**.

## Configuration, as run

```
SPAN_EVIDENCE_LPS         = ['LP-07', 'LP-27']   (unchanged)
SECTION_EXPANDED_SPAN_LPS = []                    (expansion off)
ENTAILMENT_TEST_LPS       = ['LP-27']
```

Verified the block reaches LP-27's prompt and not LP-07's: +851 chars on LP-27, LP-07 unchanged.
Assembled evidence back to clause bodies — 976 chars / 7 spans and 1043 / 8 — confirming expansion off.
94 calls, 733s and 698s. Gate: 2 aborts across 4 attempts.

## The full table

`b` = Step 457 baseline · `x` = Step 466 section-expanded · `e` = Step 468 entailment test

| # | element | b1 | b3 | x1 | x2 | **e1** | **e2** | vs baseline |
|---|---|---|---|---|---|---|---|---|
| 1 | Landlord default is defined | EXP | EXP | EXP | EXP | **EXP** | **EXP** | unchanged |
| 2 | Written notice of default | EXP | EXP | EXP | EXP | **EXP** | **EXP** | unchanged |
| 3 | Cure period specified | EXP | EXP | EXP | EXP | **EXP** | **EXP** | unchanged |
| 4 | Self-help / offset against rent | MIS | MIS | DISP | DISP | **MIS** | **MIS** | unchanged (correct) |
| 5 | Right to terminate | EXP | EXP | EXP | EXP | **EXP** | **EXP** | unchanged |
| 6 | **Monetary damages** | EXP | EXP | EXP | EXP | **EXP** | **EXP** | **unchanged — still false** |
| 7 | **Specific performance** | EXP | IMP | IMP | IMP | **IMP** | **IMP** | still false; see below |
| 8 | Lender notice and cure | MIS | MIS | MIS | MIS | **MIS** | **MIS** | unchanged |
| 9 | Common law remedies preserved | EXP | EXP | EXP | EXP | **EXP** | **EXP** | unchanged |
| 10 | Remedies cumulative | IMP | IMP | IMP | IMP | **IMP** | **IMP** | unchanged |

LP-level both runs: `partial` · materiality `high` · confidence `high` · 8 found / 1 missing / 0
unclear. Merge reasons `{None: 10}` — no suppression, no disputes.

## Q1 — Element 6: still `explicitly_present`. The test made it *more* confident.

Unchanged in both runs, still resting on §11.2's indemnity. Worse, the test appears to have supplied
B with a sharper rationale rather than a check:

> **B (gpt-5.5):** *"Section 11.2 expressly obligates Landlord to indemnify Tenant against damages
> arising from Landlord's breach or default. **This creates an express monetary recovery right tied to
> landlord default, rather than merely relying on general remedies language.**"*

That last clause reads as B distinguishing itself *from* the failure mode the block describes — using
the test's own framing to certify the indemnity. And C, run 2:

> **C (grok-4.3):** *"Indemnity clause directly imposes liability for damages arising from landlord
> breach, **satisfying the element without unstated inference**."*

C names the test's criterion and rules that the indemnity passes it.

## Q2 — Element 7: the test worked on one evaluator, who then routed around it

Merged `implicitly_present` in both runs. But B changed verdict, and its reasoning shows the block
landing exactly as intended:

> **B (gpt-5.5):** *"The lease includes only general language preserving remedies at law or in equity,
> **which does not expressly identify specific performance or injunctive relief**. Because the schema
> marks default-law coverage as jurisdiction-dependent, equitable remedies may be available…"*

B **rejected the savings clause as textual support** — the intended effect — and then returned
`covered_by_default_law` instead of `missing`. That is a presence-tier verdict under DEF-010a, so the
merged outcome is unchanged.

Meanwhile C, run 2, invoked the test by name and reached the opposite conclusion:

> **C:** *"Reservation of equity remedies **entails** specific performance and injunctive relief
> **under the entailment test**."*

**Incidental finding, worth its own attention.** B's escape route is schema-sanctioned but rests on an
unfilled placeholder. `retail_lease_knowledge.json`, `LP-27.tenant_right_to_specific_performance`:

```json
"default_law_covers": "jurisdiction-dependent",
"default_law_jurisdiction_dependent": {
    "applies_in": ["TBD_BY_ATTORNEY_REVIEW"],
    "modified_in": ["TBD_BY_ATTORNEY_REVIEW"],
    "requires_explicit_grant_in": ["TBD_BY_ATTORNEY_REVIEW"]
}
```

The string is truthy, so `_normalize_verdict` permits `covered_by_default_law` — confirmed by the
verdict surviving normalization in the persisted runs. **An element can be certified as covered by
default law on a jurisdiction-dependent basis whose jurisdiction lists were never filled in.** Any
element with this shape offers the same route around any prompt-level strictness.

## Q3 — THE PRECISION CHECK: passes. Nothing clean moved.

**Elements 1, 2, 3, 5, 8, 9, 10 are identical to the Step-457 baseline in both runs.** No correct
`missing` became present; no correct presence became `missing` or `unclear`. Zero
`citation_required_but_absent`, zero disputes.

This is the criterion Step 467 established, and it is the one thing the change unambiguously satisfies:
**a stricter instruction did not suppress correct findings.**

## Q4 — Element 4: correct, but do not credit the entailment test

`missing` in both runs, matching baseline. **The regression measured in Step 466 is gone — but that is
explained by the expansion rollback, not by this change**, since baseline already had `missing` with
expansion off. The honest statement is that the entailment test **neither helped nor hurt** element 4.

Its reasoning did absorb the vocabulary — A now gives a clean textual distinction where it voted
`unclear` at baseline r3, and C says the setoff *"does not entail tenant performing the obligation and
offsetting rent"* — but the verdict was already correct.

## Was the test engaged at all? Weakly, and unevenly.

Judgments whose reasoning uses entailment vocabulary (`entail`, `unstated`, `expressly identif`,
`topic overlap`, `indemnit`, …):

| run | count | config |
|---|---|---|
| s457_r1 | 1 | baseline |
| s457_r3 | 2 | baseline |
| **s468_r1** | **2** | entailment test |
| **s468_r2** | **6** | entailment test |

Run 2 shows clear uptake; run 1 barely differs from baseline. **The block is read inconsistently, and
where it is read it is as often used to license a verdict as to withhold one.**

## Assessment

The change is **precision-safe and outcome-neutral**. It is the first intervention in this arc that
costs nothing, which is a real result given Step 466 cost a correct verdict — but it does not move
either false positive.

The mechanism is visible: an instruction to check entailment is evaluated *by the same model whose
entailment judgment is the defect*. B, asked to check, concluded §11.2 "creates an express monetary
recovery right"; C concluded a savings clause "entails" specific performance. **Asking the panel to
apply a stricter standard does not help when the panel's application of the standard is what is
wrong.**

Rollback if wanted: `ENTAILMENT_TEST_LPS = set()`. **Left ON**, since it has no measured cost — but
that is a decision for Tzvi, not one I am taking.

## What is NOT established

- Whether element 7's `IMP`/`IMP` is stabilisation or chance. Baseline was split `EXP`/`IMP`; two runs
  landing the same way has ~25% probability under a coin flip. n=2.
- Whether stronger wording, or the test as a *hard rule* in the system prompt rather than per-LP
  guidance, would bite. Not tried — the brief said do not tune.
- Whether the `TBD_BY_ATTORNEY_REVIEW` default-law route affects other LPs or elements. Not audited.
- Whether the test helps on any LP other than LP-27. LP-27 only.
- Two runs.
