# Step 562 — The catch-all was 1 of 100. The `partial`-with-a-gap branch was 93. One guard now runs before every state.

**Date:** 2026-09-04 · **Instruction:** `build_log/562_chat_instruction.md`
**Tests: 445 passed, 3 skipped, 12 subtests. One existing test CHANGED, deliberately — §6. `derive_lp_state` untouched, no `coverage_state` added. Not deployed.**

---

# 0. THREE PREMISE CORRECTIONS, AND THE THIRD REFRAMES THE FIX

**albireo LP-05 is not the defect.** Its headline is **"1 of 4 elements unresolved"**,
`reason_code: review_needed_scope` — the Step-546 branch working. The brief says it *"says absent or
undefined"*. It does not.

**solidpower LP-16 is not `broken_xref` and not medium materiality.** It is `partial`, materiality
**low**, `elements_missing: 1` — so it took the **pre-existing `partial`+missing branch**, not the
catch-all. **Its headline *"Parking rights undefined or unprotected"* at 4 of 6 present IS the defect**,
by a different route than the brief names.

**And the third correction is the one that matters.** Recomputing every schema-sourced entry across
eleven runs with today's code — not reading stored headlines, which predate 546/547:

```
100 of 311 schema-sourced entries asserted absence over a record showing presence

   partial + adverse-missing  (pre-existing branch)   93
   missing                    (pre-existing branch)    6
   THE CATCH-ALL                                       1
   scope branch (546/547)                              0
```

**The catch-all is 1 of 100.** The brief says *"fix the catch-all"* — that would have fixed 1% and left
99, which is the pattern the last four steps have been repeating one state at a time. **The 546/547
branches produce zero defects; they are not the problem, and the problem is the branches that were
never touched.**

---

# 1. EVERY PATH INTO `_build_schema_exposure`

Measured across eleven runs, schema-sourced entries only:

| state | branch taken | count | source field |
|---|---|---|---|
| `partial` | `partial` + adverse-missing (pre-existing) | 120 | `exposure_statement` |
| `review_needed` | scope branch (546) | 68 | `exposure_statement` |
| `not_applicable` | `not_applicable` (generated) | 38 | `""` |
| `covered` | `covered` (generated) | 33 | `exposure_statement` |
| `partial` | scope branch (547) | 32 | `exposure_statement` |
| `broken_xref` | **CATCH-ALL** | 10 | **`risk_if_missing`** |
| `missing` | `missing` (pre-existing) | 9 | **`risk_if_missing`** |
| `covered_unfavorable` | **CATCH-ALL** | 1 | `exposure_statement` |

**Materiality never routes here** — it routes *away*. `generate_exposure` sends `_MODEL_STATES` and
`high`-materiality `partial`/`missing` to the model; everything else lands in the schema path
regardless of materiality.

**Step 556's claim still holds**, quoted from `lease_coverage.py:1059-1064`:

```python
    if coverage_state == "not_applicable":
        exposure = ""
    elif coverage_state in ("missing", "broken_xref"):
        exposure = get_risk_if_missing(pid) or get_exposure_statement(pid)
    else:
        exposure = get_exposure_statement(pid)
```

**`covered_unfavorable` reaching the catch-all is the one surprise** — it is a `_MODEL_STATES` member, so
it is only here when the model call failed and fell back. **That is Step 558's route 3**, showing up in
the census as a single entry.

---

# 2. THE RULE — ONE GUARD, BEFORE EVERY REMAINING BRANCH

```python
    # These two compose their prose from the state itself, not from the LP's
    # static schema string, so they cannot contradict the record.
    if state == "covered":       return _shape(f"{name} is addressed and consistent...", [])
    if state == "not_applicable": return _shape(f"{name} does not apply to this lease.", [])

    # ── Step 562: ONE GUARD, EVERY STATE ──
    scoped = _build_scope_exposure(
        assessment, missing, reason_code=f"{state or 'unknown'}_scope")
    if scoped is not None:
        return scoped

    # Below here: settled_present == 0, or no element verdicts.
    if state == "partial" and missing: ...
    if state == "missing": ...
    stmt = schema_statement or f"{name}: {state}."
```

**The two per-state branches FOLD IN.** `if state in ("review_needed", "partial")` is gone — the guard
covers those states and every other one. `covered` and `not_applicable` stay above it because they build
their prose from generated f-strings, not from the LP's static string, so they cannot contradict a
record.

## Measured effect

```
schema-sourced entries: 284   (model-sourced, untouched: 36)
  now composed from the record (rc=*_scope):                       204
  STILL using a canned string while the record shows presence:       0
```

**Zero residual.** Every canned absence claim over a record showing presence is gone, in one guard
rather than a fourth per-state branch.

---

# 3. THE WORDING — SCOPE GENERALISES, WITH ONE ADDITION

Step 546's *"N of M elements unresolved"* covers the case where evaluators split. It does **not** cover
a `partial` or `missing` LP with a real gap and nothing unresolved, which is 93 of the 100.

**Added a third form**, driven by the record and not by the state:

```
unresolved > 0            ->  "K of M elements unresolved"
else, adverse-missing > 0 ->  "K of M elements absent"          <- NEW at 562
else                      ->  "N of M elements present — review flagged"
```

**"K of M elements absent" is the same claim the canned string was making, quantified.** ex6-4 LP-14
goes from *"No excused performance"* — with 2 of 6 elements present — to *"4 of 6 elements absent"*.

**No state needs different wording.** The three forms are selected by the record, so `partial`,
`missing`, `broken_xref` and a fallen-back `covered_unfavorable` all get the form their own counts
justify. **That is what made a single guard possible.**

---

# 4. LP-20 AT 0 OF 7 — THE INVARIANT IS NOW THE GUARD'S OWN CONDITION

```
ex6-4 LP-20 Exclusivity   state=review_needed  present=0/7  missing=5
  BEFORE headline : Exclusivity protection absent or undefined
  AFTER  headline : Exclusivity protection absent or undefined   [rc=schema_default]
  AFTER  DOCX     : [GAP] LP-20 Exclusivity — Exclusivity protection absent or undefined (LOW materiality)
  display         : NO ELEMENTS FOUND  bucket=needs_attention
```

**Byte-identical.** `_build_scope_exposure` returns `None` when `total_elements == 0` **or
`settled_present == 0`**, so LP-20 falls past the guard to the branches below and keeps prose that is
true of it.

**Step 546's invariant is not preserved *alongside* the general rule — it *is* the general rule's
condition.** That is why one guard could replace two branches without a special case for it.

---

# 5. ncino's `assessment_status` — CHECKED, AND IT AGREES WITH THE RECORD

The brief reports *"8 not_assessed where 6 were assessed"*. **Measured: 26 assessed, 6 not_assessed**, and
every one of the six is consistent:

```
LP-04  not_assessed  state=broken_xref     element_verdicts=0  applicability=applicable  CONSISTENT
LP-20  not_assessed  state=missing         element_verdicts=0  applicability=applicable  CONSISTENT
LP-21  not_assessed  state=not_applicable  element_verdicts=0  applicability=unclear     CONSISTENT
LP-23  not_assessed  state=not_applicable  element_verdicts=0  applicability=unclear     CONSISTENT
LP-29  not_assessed  state=broken_xref     element_verdicts=0  applicability=required    CONSISTENT
LP-31  not_assessed  state=not_applicable  element_verdicts=0  applicability=unclear     CONSISTENT

assessed-but-zero-verdicts (the inverse error): []
```

**All six have zero element verdicts, so nothing was assessed and `not_assessed` is the correct label.**
The inverse error — an LP marked `assessed` with no verdicts — does not occur either.

**Nothing to fix, and I did not fix anything.** If the "8 vs 6" figure came from a surface that
recomputes the count rather than reading `assessment_status`, that surface is where the disagreement
lives; I did not find it in the result.

---

# 6. ARTEFACTS — BEFORE AND AFTER

```
albireo LP-11    16/17 present, 1 missing
  BEFORE  [GAP] LP-11 Default & Remedies — Default and remedy framework absent or incomplete (LOW)
  AFTER   [GAP] LP-11 Default & Remedies — 1 of 17 elements absent (LOW materiality)
          "16 of 17 expected elements are confirmed present and 1 absent."

solidpower LP-16  4/6 present, 1 missing
  BEFORE  [GAP] LP-16 Parking — Parking rights undefined or unprotected (LOW materiality)
  AFTER   [GAP] LP-16 Parking — 1 of 6 elements unresolved (LOW materiality)
          "4 of 6 expected elements are confirmed present and 1 absent. 1 element unresolved
           (evaluators split): Landlord's right to modify parking area is addressed."

atlas524 LP-25    6/7 present, 1 missing
  BEFORE  [GAP] LP-25 Condemnation / Eminent Domain — Condemnation rights are undefined (LOW)
  AFTER   [GAP] LP-25 Condemnation / Eminent Domain — 1 of 7 elements absent (LOW materiality)

albireo LP-05     UNCHANGED — already correct at Step 546
  BEFORE / AFTER  [GAP] LP-05 Permitted Use — 1 of 4 elements unresolved (LOW materiality)

ex6-4 LP-20       UNCHANGED — the invariant
  BEFORE / AFTER  [GAP] LP-20 Exclusivity — Exclusivity protection absent or undefined (LOW)
```

**No model-path headline changes.** 23 model-sourced entries across the six runs; the guard lives inside
`_build_schema_exposure`, which `generate_exposure` calls **only in the `else` of `if use_model:`**, so a
model-path entry cannot reach it.

## A test was changed, and I am not burying it

`test_547_partial_scope.py::test_partial_with_a_real_gap_is_untouched` **failed**, correctly.

It asserted `reason_code == "schema_default"` for a `partial` with 3 of 4 present and 1 missing — **the
exact shape that is 93 of the 100 defects.** Step 547 wrote that assertion when it decided to leave that
branch alone, and Step 549 measured the decision as wrong. **The test was pinning the largest remaining
instance of the defect in place.**

Renamed to `test_partial_with_a_real_gap_now_ALSO_reports_scope`, asserting
`partial_scope` and `"1 of 4 elements absent"`, with the reason recorded in its docstring.

---

# WHAT IS NOT ESTABLISHED

- **All three of the brief's motivating examples were mischaracterised** (§0). The defect is real; two of
  the three named instances are not it.
- **No pipeline was run.** Every figure comes from calling `_build_schema_exposure` on stored
  assessments from eleven runs. **The change will appear in a new run's persisted JSON; stored results
  still carry the old strings.**
- **The `missing`-state cases are the judgement call in this step.** ex6-4 LP-14 moves from *"No excused
  performance"* to *"4 of 6 elements absent"*. The state is a considered verdict from `derive_lp_state`,
  and replacing its prose with a count is defensible but not obviously better — **it is more accurate
  and less evocative.** 5 entries.
- **"K of M elements absent" was not tested against a reader.** Neither was Step 546's wording.
- **The one `covered_unfavorable` catch-all entry is Step 558's `schema_fallback` route**, and this
  guard now covers it — but the underlying model-call failure is still unrecorded in `fallback_events`
  (Step 558), which is unfixed.
- **`derive_lp_state` untouched, no `coverage_state` added**, per the brief.
