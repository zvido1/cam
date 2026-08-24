# Step 470 — Should `covered_by_default_law` be presence-tier? Diagnostic

**Date:** 2026-08-23 · **Instruction:** `build_log/470_chat_instruction.md`
**DIAGNOSTIC ONLY.** No fix, no runs, no schema change, no code change. Counterfactuals computed
offline over the four persisted runs (`s457_r1`, `s457_r3`, `s468_r1`, `s468_r2`) — 788 element merges.

**Method note:** the merge function was replicated offline and **validated against the stored merged
verdicts: 788 of 788 match, 0 mismatches.** The counterfactuals below rest on that replication.

---

## CORRECTION to Step 469 — the harm is larger than I recorded

`469_code_status.md` and `FINDING_prompt_strictness_does_not_fix_entailment.md` both state that had
evaluator B returned `missing` on LP-27 element 7, *"the merge would still have been a presence
majority (2 of 3) — but with a recorded dissent."*

**That is wrong.** I asserted merge behaviour without quoting the code path. There is a **disputed
gate** at `lease_coverage_305.py:994` that runs *before* the majority is honoured:

```python
    has_presence = any(v["verdict"] in PRESENCE_VERDICTS for v in active)
    has_missing  = any(v["verdict"] == "missing" for v in active)
    if has_presence and has_missing:
        return {
            "verdict": "disputed",
            "confidence": "low",
            ...
            "reason": "distant_split_presence_missing",
```

Any presence/missing split returns `disputed` regardless of majority. Simulated:

```
s468_r1  actual=implicitly_present   if B had said 'missing' -> disputed (distant_split_presence_missing)
s468_r2  actual=implicitly_present   if B had said 'missing' -> disputed (distant_split_presence_missing)
```

**The TBD-backed `covered_by_default_law` vote did not merely erase a dissent. It converted a
`disputed` / low-confidence outcome into `implicitly_present` at high confidence.** That is the
correct statement of the harm, and it strengthens rather than weakens the Step-469 finding.

## Q1 — The tiers, and what the rank determines

`lease_coverage_305.py:52-57`:

```python
PRESENCE_VERDICTS = frozenset({
    "explicitly_present",
    "implicitly_present",
    "covered_by_default_law",
    "covered_in_other_LP",
})
```

`:71-82`:

```python
_PRESENCE_TIER: frozenset = frozenset({
    "explicitly_present",
    "implicitly_present",
    "covered_by_default_law",
    "covered_in_other_LP",
})
_PRESENCE_TIER_EXPANSION_RANK: dict = {
    "explicitly_present":    0,
    "implicitly_present":    1,
    "covered_in_other_LP":   2,
    "covered_by_default_law": 3,
}
```

**Rank of `covered_by_default_law` is 3 — last, behind `explicitly_present` (0) and
`implicitly_present` (1).** The rank determines **only which label is reported when the presence tier
wins**, at `:980-985`:

```python
    if majority_tier == "present_like":
        presence_active = [v for v in active if v["verdict"] in _PRESENCE_TIER]
        majority_verdict = min(
            (v["verdict"] for v in presence_active),
            key=lambda vv: _PRESENCE_TIER_EXPANSION_RANK.get(vv, 99),
        )
```

**It does not affect whether the element counts as satisfied.** All four labels are collapsed to
`present_like` for counting; the rank is cosmetic re-expansion. So a `covered_by_default_law` vote has
exactly the same weight in the consensus arithmetic as `explicitly_present`, and its lower rank only
means its label loses when a more explicit one is present — which is precisely why it is invisible in
the output on LP-27 element 7.

**Incidental defect: the comment above the dict contradicts the dict.** It states
`covered_by_default_law = 2` and describes a tie with `covered_in_other_LP` broken by `VERDICT_RANK`.
The code says `3`, and there is no tie. Documentation only — the behaviour follows the dict.

## Q2 — What the two verdicts mean, and the incoherence

Prompt text, `lease_coverage_305.py:232-234`:

> `- implicitly_present: Same-LP text functionally satisfies the element without using expected phrasing. Citation required. Only valid when implicit_coverage_acceptable is true.`
>
> `- covered_by_default_law: Absent from lease but applies by background law per schema annotation. Only valid when default_law_covers is true or "jurisdiction-dependent".`

**Yes — the distinction is exactly as put in the brief.** `implicitly_present` is a claim about the
document: *same-LP text functionally satisfies*. `covered_by_default_law` is defined as **"Absent from
lease"** — a claim about law, not about the document.

**And the elements ask about the document.** LP-27's element labels are of the form *"Tenant has right
to specific performance or injunctive relief"* — read against a lease, in a coverage assessment whose
output is `elements_found` / `elements_missing`. A verdict meaning *"the lease does not contain this,
but background law might supply it"* is being counted into `elements_found` and reported as coverage.

**The incoherence is visible in the prompt itself.** Hard rule 5, `:243`:

> `5. Any presence verdict (explicitly_present, implicitly_present, covered_by_default_law, covered_in_other_LP) requires section_ref in the citation. If section_ref is null, use unclear instead.`

**The prompt requires a section reference for a verdict it defines as "Absent from lease".** There is
no section to cite. The instruction is unsatisfiable on its own terms, and Q4 shows what evaluators do
about it.

## Q3 — Counterfactuals, 788 merges across 4 runs and all 33 LPs

### Variant A — `covered_by_default_law` as NEUTRAL (abstains, like `unclear`)

**12 of 788 merged verdicts change (1.52%).**

| run | element | current | → neutral |
|---|---|---|---|
| s457_r1 | LP-17.claims_time_limit | disputed | unclear (`no_consensus`) |
| s457_r1 | LP-32.notification_requirement | disputed | unclear (`no_consensus`) |
| s457_r1 | LP-32.survival_after_expiration | disputed | unclear (`no_consensus`) |
| s457_r3 | LP-32.notification_requirement | disputed | unclear (`no_consensus`) |
| s457_r3 | LP-32.survival_after_expiration | disputed | unclear (`no_consensus`) |
| s468_r1 | LP-17.claims_time_limit | **covered_by_default_law** | unclear (`all_evaluators_unclear`) |
| s468_r1 | LP-32.notification_requirement | disputed | unclear (`no_consensus`) |
| s468_r1 | LP-32.survival_after_expiration | disputed | unclear (`no_consensus`) |
| s468_r2 | LP-09.tenant_remains_liable_after_transfer | disputed | **missing** |
| s468_r2 | LP-17.claims_time_limit | disputed | unclear (`no_consensus`) |
| s468_r2 | LP-32.notification_requirement | disputed | unclear (`no_consensus`) |
| s468_r2 | LP-32.survival_after_expiration | disputed | unclear (`no_consensus`) |

**Note what does NOT change: LP-27 element 7 stays `implicitly_present` in both runs.** Removing B's
vote leaves A and C both `implicitly_present` — a clean 2-of-2 presence majority. Neutral treatment
does not surface the disagreement either; it just stops the vote counting.

### Variant B — `covered_by_default_law` as DISSENT (non-presence, counts against)

**14 of 788 merged verdicts change (1.78%).**

The two that matter most:

| run | element | current | → dissent |
|---|---|---|---|
| s468_r1 | **LP-27.tenant_right_to_specific_performance** | implicitly_present | **disputed** |
| s468_r2 | **LP-27.tenant_right_to_specific_performance** | implicitly_present | **disputed** |
| s468_r1 | LP-13.negligence_carveouts | explicitly_present | disputed |
| s468_r2 | LP-09.tenant_remains_liable_after_transfer | disputed | missing |

Plus 10 cases where `disputed` becomes `covered_by_default_law` (LP-17, LP-32) — **an artefact of this
variant worth flagging honestly**: once `covered_by_default_law` is its own tier, two evaluators
choosing it form a majority *of that tier*, so it wins outright. Variant B does not merely demote the
verdict; it also lets it win where it previously produced a dispute. A real implementation would need
to decide that case separately.

**Only Variant B surfaces the LP-27 element 7 disagreement.** It is also the more disruptive of the
two, and its 10 LP-17/LP-32 flips are in the wrong direction.

**Scale in context:** ~1.5–1.8% of merges move, concentrated in five elements across LP-09, LP-13,
LP-17, LP-27, LP-32. This is not a sweeping change — but it is not confined to LP-27 either.

## Q4 — The citation gate DOES apply, and it does not bite

**Not exempt.** `covered_by_default_law ∈ PRESENCE_VERDICTS`, and the gate at `:991` tests exactly that
membership:

```python
    if majority_verdict in PRESENCE_VERDICTS:
        valid_citations = [
            c for c in majority_citations
            if c and c.get("section_ref")
        ]
        if not valid_citations:
            return {"verdict": "unclear", ..., "reason": "citation_required_but_absent", ...}
```

**But it tests non-nullity only, and evaluators satisfy it with prose that names no document
location.** All 30 `covered_by_default_law` verdicts across the four runs; 18 carried a non-null
`section_ref` (60%):

```
'Default statute of limitations law'
'Default law; jurisdiction-dependent'
'Default environmental reporting law'
'Default law (jurisdiction-dependent; governing law not specified)'
'Default law - applicable statutes of limitation'
'Applicable default statute of limitations'
'Default law; governing law not specified'
'Background environmental law; Section 12.2'
'Section 12.2 / applicable environmental laws'
```

**Not one of the pure-default-law strings is a section reference.** They are restatements of the
verdict in the citation field. Two (`'Background environmental law; Section 12.2'`,
`'Section 12.2 / applicable environmental laws'`) do name a section, which is itself odd for a verdict
meaning *"absent from lease"*.

**So this is a second route around a deterministic check** — and it is the same shape as the one
Step 460 found for LP-07, where `'Paragraph 1'` and `'Proportionate Share definition'` passed the same
gate. The gate asks *is this field non-empty*, never *does this string identify a location in the
document*. On a verdict defined as "absent from lease", it cannot ask the latter, because there is
nothing to point at. **Hard rule 5 and the definition of `covered_by_default_law` cannot both be
satisfied honestly.**

## Summary

- **Q1:** rank 3, cosmetic only; consensus weight identical to `explicitly_present`. Comment/code
  mismatch on the rank value.
- **Q2:** yes — `implicitly_present` is about the document, `covered_by_default_law` is expressly about
  law *"Absent from lease"*, and it lands in `elements_found`. The prompt then demands a section
  reference for it, which is unsatisfiable.
- **Q3:** 12 of 788 change under neutral (1.52%), 14 under dissent (1.78%). **Only the dissent variant
  surfaces LP-27 element 7**, and it carries its own artefact.
- **Q4:** the gate applies and is satisfied by prose. Second route around a deterministic check,
  identical in shape to the LP-07 fabricated-locator route.
- **Correction:** the Step-469 claim about what would have happened had B voted `missing` was wrong.
  It would have been `disputed`, not a dissent-bearing presence majority.

## What is NOT established

- Which variant is correct. This is a design question; neither is recommended here.
- Whether the 10 LP-17/LP-32 flips under Variant B are acceptable. They are an artefact of the
  simplest formulation, not an argument against the direction.
- Whether the four runs are representative. One fixture, 788 merges, 30 `covered_by_default_law`
  verdicts total.
- Whether `covered_in_other_LP` — the fourth presence label, also rank-collapsed — has the same
  problem. Not examined.
