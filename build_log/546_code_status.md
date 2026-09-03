# Step 546 — The headline now reads the record. LP-20 is untouched. The label is built and nothing reads it.

**Date:** 2026-09-03 · **Instruction:** `build_log/546_chat_instruction.md`
**Tests: 418 passed, 3 skipped, 12 subtests (406 → 418; 12 new). No verdict changed. `derive_lp_state` untouched. No `coverage_state` added. Not deployed.**

---

# 0. ONE PART IS INERT, AND IT IS THE ONE THE BRIEF NAMED FIRST

**The scope label is built and no consumer reads it.**

```
every python read of a `label` key off a _resolve_display result
in cam/ and 05 Lease Analyzer/ (excluding tests):  ZERO
```

Step 279 removed the state label from the annotator header — *"The state label
(UNFAVORABLE TERMS / FAVORABLE TERMS / etc.) was redundant with the marker + materiality and is
dropped"* — and nothing has read it since. `lease_report_generator:257` and `summary_generator:1179`
take `_resolve_display(...)["bucket"]` only; `resolve_sections` returns `(item, disp)` pairs and
`lease_report_generator:453` sorts `pair[0]`, discarding `disp`.

**So `REVIEW NEEDED — 1 OF 17 ELEMENTS UNRESOLVED` is correct, tested, and reaches no reader today.**
It is the right home for the scope if a surface starts reading labels, and I built it because the brief
asked for it — but calling it delivered would be the written-vs-wired claim Rule 4 exists to stop.

**The scope does reach readers, by two other routes that are wired:** the corrected `exposure_headline`
(rendered by both annotators, `lease_report_generator:339` and `summary_generator:1576`) and the new
`Resolved:` / `Unresolved:` lines in the DOCX and PDF callouts. §A and §C.

---

# A. THE HEADLINE — ONE BRANCH, AND IT FIRES ONLY WHERE THE RECORD CONTRADICTS THE PROSE

Added to `_build_schema_exposure` immediately before the catch-all. It fires only when
`total_elements` and `settled_present` are both non-zero; otherwise control falls through to the
catch-all exactly as before.

## Before and after, on the artefacts

```
ex6-4 LP-11 Default & Remedies   (elements_missing: 1)
  BEFORE  Default and remedy framework absent or incomplete
  AFTER   1 of 17 elements unresolved
          "15 of 17 expected elements are confirmed present and 1 absent. 1 element unresolved
           (evaluators split): Abandonment or vacating as event of default."

ex6-4 LP-25 Condemnation          (elements_missing: 0)
  BEFORE  Condemnation rights are undefined
  AFTER   1 of 7 elements unresolved
          "6 of 7 expected elements are confirmed present. 1 element unresolved (evaluators
           split): Definition of total taking vs material partial taking is provided."

atlas(524) LP-26 Quiet Enjoyment  (elements_missing: 0)
  BEFORE  Quiet enjoyment covenant absent or undefined
  AFTER   1 of 7 elements unresolved
          "6 of 7 expected elements are confirmed present. 1 element unresolved (evaluators
           split): Constructive eviction is acknowledged or addressed in the lease."
```

## LP-20 IS UNTOUCHED — verified three ways

```
ex6-4 LP-20 Exclusivity   0 of 7 present, elements_missing: 5
  BEFORE  Exclusivity protection absent or undefined     reason_code: schema_default
  AFTER   Exclusivity protection absent or undefined     reason_code: schema_default
  DOCX    [GAP] LP-20 Exclusivity — Exclusivity protection absent or undefined (LOW materiality)
          Missing: Specific exclusive use scope is defined ... (5 elements)
  display NO ELEMENTS FOUND / needs_attention / ✕      (Step 538's guard, unchanged)
```

**`settled_present == 0` is the guard.** When nothing was confirmed present the provision genuinely is
absent, the canned schema statement is the accurate thing to say, and the branch declines to fire.
ex6-4 LP-02 (0 of 4) behaves identically. `test_absent_lp_keeps_schema_statement` fails if a later
change softens this.

## A polarity bug I introduced and caught before committing

My first version wrote *"and N absent"* from `summarize_resolution`'s raw count of non-present,
non-unresolved elements. On Atlas LP-22 that rendered **"5 of 11 confirmed present and 4 absent"** —
and all four of those elements are `absence_adverse_to: landlord`:

```
missing  adverse_to=landlord  Subordination is automatic or self-executing...
missing  adverse_to=landlord  Tenant must execute subordination documents...
missing  adverse_to=landlord  Attornment is automatic or self-executing...
missing  adverse_to=landlord  SNDA execution timing and consequence...
```

**They are favorable absences for this tenant, which is why `elements_missing` is correctly `[]`** —
Step 374Z strips them precisely so they are never narrated as gaps. The prose now uses the
perspective-adverse `missing` list, and `settled_absent` carries an explicit
`POLARITY-BLIND … do not narrate it as one` comment in the helper.

---

# B. `summarize_resolution` — DETERMINISTIC, FROM `element_verdicts` ALONE

New in `lease_display.py`. No API call, no state derived, no verdict altered.

```json
{"_source": "lease_display.summarize_resolution",
 "total_elements": 17, "settled_present": 15, "settled_absent": 1,
 "unresolved_elements": 1,
 "unresolved_labels": ["Abandonment or vacating as event of default"],
 "unresolved_reasons": {"no_consensus": 1}}
```

## `disputed` counts as unresolved — a deliberate divergence from `derive_lp_state`

`derive_lp_state` folds `disputed` in with `missing` (Supplement #21 Phase 1). **That is a decision
about STATE.** This set answers a different question — *was the element resolved* — and a split
evaluator cohort has resolved nothing.

**The measurement forces it:** 11 of the 32 `review_needed` LPs at Step 545 reach that state through
the Phase-3 disputed-critical override **with no `unclear` element at all**. Counting `disputed` as
settled would print *"0 of 11 elements unresolved"* on every one of them. **No state is derived from
this set**, so the divergence changes nothing downstream.

`total_elements == 0` means no scope is available; every caller falls back to prior behaviour rather
than printing zeros.

---

# C. THE EXPORTS — `element_verdicts` REACHED THEM ZERO TIMES BEFORE THIS

## The marker

```python
    _state = coverage_item.get("coverage_state", "")
    _tag = "[REVIEW]" if (_state == "review_needed" and not elements_missing) else "[GAP]"
```

**Narrow by design, exactly as briefed.** Only `review_needed` with no adverse missing element. Every
other state keeps `[GAP]` byte-for-byte.

## The scope lines

```
[REVIEW] LP-26 Quiet Enjoyment — 1 of 7 elements unresolved (LOW materiality)

Resolved: 6 of 7 expected elements confirmed present.
Unresolved (1): Constructive eviction is acknowledged or addressed in the lease

6 of 7 expected elements are confirmed present. 1 element unresolved (evaluators split):
Constructive eviction is acknowledged or addressed in the lease.
```

against the same callout before this step:

```
[GAP] LP-26 Quiet Enjoyment — Quiet enjoyment covenant absent or undefined (LOW materiality)

Quiet enjoyment covenant absent or undefined; tenant's right to undisturbed possession depends
on state law, which varies and may not protect against lender interference
```

**Marker, headline and body all asserted absence, and no missing element was named anywhere** — the
`Missing:` line is emitted only for a non-empty list.

**`per_evaluator_lp_verdicts` is NOT surfaced**, per `Step_305_Architecture.md:39` (*"not from a direct
LP-state vote"*). `test_lp_level_roll_up_is_not_surfaced` asserts no evaluator verdict string appears in
either callout.

---

# D. CORPUS REGRESSION — 6 RUNS, 192 LPs

```
schema-sourced headlines changed, state == review_needed  : 27
schema-sourced headlines changed, any other state         :  0

bucket totals BEFORE: needs_attention 20, worth_reviewing 25, covered 14, minor_gaps 82, not_assessed 51
bucket totals AFTER : needs_attention 20, worth_reviewing 25, covered 14, minor_gaps 82, not_assessed 51
identical: True
```

**Only `review_needed` moved, and no LP changed bucket.**

**A false alarm in my own first pass, recorded.** It reported 16 non-`review_needed` headlines changed.
That was my harness calling `_build_schema_exposure` on items whose stored headline came from the
**model** path — 9 `missing`, 4 `covered_unfavorable`, 3 `partial`, all `exposure_source: model`, none
of which my branch can reach. Restricting the comparison to schema-sourced items gives 0. **I checked
before reporting a regression that did not exist.**

---

# WHAT IS NOT ESTABLISHED

- **The scope label is inert.** Built, tested, read by nothing. §0.
- **THE SAME DEFECT SURVIVES ON `partial`, AND IT IS 19 LPs.** `_build_schema_exposure`'s `partial`
  branch is `if state == "partial" and missing:` — so a partial whose adverse-missing list is empty
  **also falls to the catch-all and inherits the canned absence prose**. Measured on the same six runs,
  19 schema-sourced `partial_typical` LPs with `adverse_missing == 0`, including:
  ```
  ex6-4           LP-05  "Use restrictions absent or undefined"
  solidpower(528) LP-17  "Dispute framework absent"
  atlas(524)      LP-09  "Assignment rights absent or over-restricted"
  divall(496)     LP-10  "Alteration rights undefined"
  ```
  **Same root cause, different state. The brief scoped this step to `review_needed` and I did not
  widen it. It deserves its own step and I am not calling the catch-all fixed.**
- **No pipeline was run.** Every artefact above is produced by calling the real functions on stored
  Step-537 / Step-524 results. The headline change will only appear in a *new* run's persisted JSON;
  stored results still carry the old strings.
- **The `[GAP]` marker is still unconditional for every other state**, including `covered_unfavorable`
  with an empty missing list — a term rather than an omission. Out of scope, named at Step 545 and
  again here.
- **`materiality: low` on all three exemplars is unexamined.** LP-26 quiet enjoyment and a 17-element
  default framework both read "(LOW materiality)". Flagged since Step 539, still untouched.
- **The web screen is unchanged.** `app.js` classifies independently and already renders
  `element_verdicts`; it does not use `summarize_resolution` and shows no scope phrase.
- **"evaluators split" is asserted only when every unresolved reason is `no_consensus` or
  `distant_split_presence_missing`**; anything else phrases as *"not resolved on the evidence"*. Step
  544 measured that no other reason has ever occurred, so the second phrasing is untested against real
  data.
