# Step 547 — All 19 fixed. The shape differs from `review_needed` in one structural way, and the polarity trap was live on three of them.

**Date:** 2026-09-03 · **Instruction:** `build_log/547_chat_instruction.md`
**Tests: 427 passed, 3 skipped, 12 subtests (418 → 427; 9 new). No verdict changed. `derive_lp_state` untouched. No `coverage_state` added. Not deployed.**

---

# 1. THE 19 — ALL SIX RUNS

Schema-sourced `partial` LPs whose perspective-adverse missing list is empty, and which therefore fell
past `if state == "partial" and missing:` to the catch-all:

```
run              LP      pres/tot unres  rawAbs  advMiss  stored_em pcls             headline (before)
ex6-4            LP-01     5/6        1       0        0          0 partial_typical  Tenant's payment obligation and enforcement timeline...
ex6-4            LP-05     3/4        1       0        0          0 partial_typical  Use restrictions absent or undefined
ex6-4            LP-06     4/5        1       0        0          0 partial_typical  Maintenance allocation undefined
ex6-4            LP-08     5/6        1       0        0          0 partial_typical  Insurance obligations incompletely defined
ex6-4            LP-09     9/12       1       2        0          0 partial_typical  Assignment rights absent or over-restricted
ex6-4            LP-19     4/6        2       0        0          0 partial_typical  Utility cost allocation and service interruption rights...
solidpower(528)  LP-08     5/6        1       0        0          0 partial_typical  Insurance obligations incompletely defined
solidpower(528)  LP-17     4/6        2       0        0          0 partial_typical  Dispute framework absent
solidpower(528)  LP-18     4/5        1       0        0          0 partial_typical  Holdover protection undefined
solidpower(528)  LP-19     4/6        2       0        0          0 partial_typical  Utility cost allocation and service interruption rights...
solidpower(525)  LP-08     5/6        1       0        0          0 partial_typical  Insurance obligations incompletely defined
solidpower(525)  LP-09    11/12       1       0        0          0 partial_typical  Assignment rights absent or over-restricted
solidpower(525)  LP-17     3/6        3       0        0          0 partial_typical  Dispute framework absent
solidpower(525)  LP-18     4/5        1       0        0          0 partial_typical  Holdover protection undefined
solidpower(525)  LP-19     5/6        1       0        0          0 partial_typical  Utility cost allocation and service interruption rights...
atlas(524)       LP-09     8/12       2       2        0          0 partial_typical  Assignment rights absent or over-restricted
atlas(522)       LP-09     8/12       3       1        0          0 partial_typical  Assignment rights absent or over-restricted
atlas(522)       LP-19     4/6        2       0        0          0 partial_typical  Utility cost allocation and service interruption rights...
divall(496)      LP-10     4/5        1       0        0          0 partial_typical  Alteration rights undefined
```

**`elements_missing` is empty on all 19** — the column is measured, not assumed. **All 19 are
`partial_typical`**; no `partial_material` or `partial_review` is in the set. `partial` LPs by exposure
source across the six runs: **96 schema, 3 model**.

## Is the shape the same? Yes for the guard, no for the mechanism — and the difference is structural

```
THE 19 -- unresolved verdict mix: {'disputed': 28}
THE 19 -- unresolved reason mix : {'distant_split_presence_missing': 28}
```

**Not one `unclear` element among them, and that is forced by `derive_lp_state`, not a coincidence.**
`any_unclear` is the first branch and returns `review_needed`, so an LP can only *be* `partial` if no
element is `unclear`. Its unresolved population is therefore **entirely `disputed`** — where
`review_needed`'s was 17 `no_consensus` unclears plus disputed elements.

**Nothing in the review_needed branch handles that wrongly.** Both reason codes are in `_SPLIT_REASONS`,
so *"(evaluators split)"* is the correct parenthetical for both, and the branch keys on counts rather
than on verdict names. **The one case it would have handled wrongly is the polarity of the absent
count** — §3.

Two guards were checked against the population rather than assumed safe: **every one of the 19 has
`settled_present >= 3`**, so the `settled_present == 0` guard never blocks a member; and every one has
`unresolved_elements >= 1`, so none takes the "Flagged for review" fallback path.

---

# 2. THE TREATMENT — ONE SHARED HELPER, NOT A SECOND COPY

`_build_scope_exposure(assessment, adverse_missing, reason_code)` is extracted from the Step-546 branch
and now serves both states. It **returns `None`** — fall through unchanged — when the item carries no
element verdicts or when nothing was confirmed present.

```python
    if state in ("review_needed", "partial"):
        scoped = _build_scope_exposure(
            assessment, missing,
            reason_code=("review_needed_scope" if state == "review_needed"
                         else "partial_scope"),
        )
        if scoped is not None:
            return scoped
```

**`partial` reaches this only when the adverse-missing list is empty** — a partial with a real gap
matches the earlier branch and never gets here. The reason codes stay distinct so the two populations
remain separable in any later audit.

## The marker, extended to `partial`

```python
    _tag = ("[REVIEW]"
            if (_state in ("review_needed", "partial") and not elements_missing)
            else "[GAP]")
```

**This is a judgement call and I am flagging it rather than burying it.** The brief's §2 named the
headline guard; it did not name the marker. I extended it because leaving it would preserve the exact
inconsistency Step 546 identified — `[GAP]` beside *"Resolved: 3 of 4 expected elements confirmed
present"* with **no `Missing:` line at all**, since that line is emitted only for a non-empty list.
**Reverting it is a one-line change if unwanted.**

---

# 3. THE POLARITY TRAP — LIVE ON THREE OF THE 19, AND 17 OF 99 OVERALL

The brief predicted `partial` would be more exposed. It is.

```
POLARITY DIFFERENCES (raw settled_absent != adverse missing), all partial LPs: 17 of 99
   ex6-4            LP-09  raw_absent=2 adverse=0 stored_em=0 src=schema     <- in the 19
   solidpower(528)  LP-12  raw_absent=2 adverse=1 stored_em=1 src=schema
   solidpower(525)  LP-12  raw_absent=2 adverse=1 stored_em=1 src=schema
   atlas(524)       LP-09  raw_absent=2 adverse=0 stored_em=0 src=schema     <- in the 19
   atlas(524)       LP-10  raw_absent=3 adverse=2 stored_em=2 src=schema
   atlas(524)       LP-11  raw_absent=2 adverse=1 stored_em=1 src=schema
   atlas(524)       LP-27  raw_absent=2 adverse=1 stored_em=1 src=model
   atlas(522)       LP-09  raw_absent=1 adverse=0 stored_em=0 src=schema     <- in the 19
   atlas(522)       LP-10  raw_absent=3 adverse=2 stored_em=2 src=schema
   atlas(522)       LP-11  raw_absent=2 adverse=1 stored_em=1 src=schema
   atlas(522)       LP-12  raw_absent=3 adverse=1 stored_em=1 src=schema
   atlas(522)       LP-27  raw_absent=2 adverse=1 stored_em=1 src=model
   divall(496)      LP-08  raw_absent=3 adverse=2 stored_em=2 src=schema
   divall(496)      LP-11  raw_absent=5 adverse=1 stored_em=1 src=schema
   divall(496)      LP-12  raw_absent=3 adverse=1 stored_em=1 src=schema
   divall(496)      LP-22  raw_absent=4 adverse=2 stored_em=2 src=schema
   divall(496)      LP-27  raw_absent=1 adverse=0 stored_em=0 src=model
```

**Three of the 19 — the LP-09 rows — have a non-zero raw count and a zero adverse count.** Had the
helper used the raw number, atlas(524) LP-09 would read *"8 of 12 expected elements are confirmed
present and 2 absent"* about two absences that favour this tenant. The helper takes the
perspective-stripped list as an argument and its docstring says so in capitals;
`test_favorable_absences_are_not_narrated` fails if a later change reaches for the raw count.

**Measured after the change: zero schema-sourced headlines assert absence with an empty adverse-missing
list**, across all six runs.

---

# 4. THE ARTEFACTS — FOUR NAMED LPs, BEFORE AND AFTER, BOTH FORMATS

DOCX and PDF are byte-identical to each other on every case below; one is shown where they agree.

```
ex6-4 LP-05 Permitted Use            (elements_missing: 0)
BEFORE  [GAP] LP-05 Permitted Use — Use restrictions absent or undefined (LOW materiality)
        Resolved: 3 of 4 expected elements confirmed present.
        Unresolved (1): Co-tenancy or anchor tenant dependency is addressed
        Use restrictions absent or undefined; tenant may face exclusive use violations...
AFTER   [REVIEW] LP-05 Permitted Use — 1 of 4 elements unresolved (LOW materiality)
        Resolved: 3 of 4 expected elements confirmed present.
        Unresolved (1): Co-tenancy or anchor tenant dependency is addressed
        3 of 4 expected elements are confirmed present. 1 element unresolved
        (evaluators split): Co-tenancy or anchor tenant dependency is addressed.

solidpower(528) LP-17 Dispute Resolution
BEFORE  [GAP] ... — Dispute framework absent (LOW materiality)
AFTER   [REVIEW] ... — 2 of 6 elements unresolved (LOW materiality)
        4 of 6 expected elements are confirmed present. 2 elements unresolved
        (evaluators split): Dispute resolution mechanism is defined...; Time limit
        for bringing claims is defined.

atlas(524) LP-09 Subletting & Assignment
BEFORE  [GAP] ... — Assignment rights absent or over-restricted (LOW materiality)
AFTER   [REVIEW] ... — 2 of 12 elements unresolved (LOW materiality)
        8 of 12 expected elements are confirmed present. 2 elements unresolved
        (evaluators split): Change of control is addressed; Original tenant remains
        liable after assignment or sublease.
        ^ note: NO "and 2 absent" -- the two missing verdicts here are favorable absences.

divall(496) LP-10 Alterations & Improvements
BEFORE  [GAP] ... — Alteration rights undefined (LOW materiality)
AFTER   [REVIEW] ... — 1 of 5 elements unresolved (LOW materiality)
        4 of 5 expected elements are confirmed present. 1 element unresolved
        (evaluators split): Landlord contribution to tenant improvements is addressed.
```

## The Step-546 fix is unchanged and LP-20 still reads as absent

```
ex6-4 LP-25 Condemnation   reason_code review_needed_scope   "1 of 7 elements unresolved"   [REVIEW]
ex6-4 LP-20 Exclusivity    reason_code schema_default        "Exclusivity protection absent or undefined"
        [GAP] LP-20 Exclusivity — Exclusivity protection absent or undefined (LOW materiality)
        Missing: Specific exclusive use scope is defined ... (5 elements)
        display: NO ELEMENTS FOUND / needs_attention / ✕
```

**LP-20 is byte-identical to Step 546's output.** All 12 Step-546 tests still pass after the refactor.

## Corpus regression, six runs, 192 LPs

```
SCHEMA-SOURCED HEADLINES CHANGED, by (state, new reason_code):
   ('review_needed', 'review_needed_scope')  27
   ('partial',       'partial_scope')        19

bucket BEFORE: needs_attention 20, worth_reviewing 25, covered 14, minor_gaps 82, not_assessed 51
bucket AFTER : needs_attention 20, worth_reviewing 25, covered 14, minor_gaps 82, not_assessed 51
identical: True
```

**Exactly the two target populations, nothing else, and no LP changed bucket.**

---

# 5. A THIRD STATE HAS THE DEFECT — REPORTED, NOT FIXED

```
STATES STILL REACHING THE CATCH-ALL (schema-sourced), after this step:
  broken_xref     7
      ex6-4            LP-23  present 0/0  | Percentage rent obligations unenforceable or undefined
      solidpower(528)  LP-07  present 0/0  | Tenant may owe undefined share of all building operating...
      solidpower(528)  LP-29  present 0/0  | Landlord may enter premises without notice, at any time...
      solidpower(525)  LP-29  present 0/0  | Landlord may enter premises without notice, at any time...
  review_needed   5    (all correct -- settled_present == 0, or no element verdicts)
```

**All seven `broken_xref` LPs carry ZERO element verdicts.** That makes their defect a *different* one:
`review_needed` and `partial` emitted canned prose that **contradicted the record**; `broken_xref`
emits canned prose where **there is no record at all** — *"Landlord may enter premises without notice,
at any time"* is an assertion about this lease's content with nothing behind it.

**The treatment built here would not help them.** `_build_scope_exposure` returns `None` on
`total_elements == 0`, so adding `broken_xref` to the branch would change nothing.
`test_broken_xref_still_falls_through` locks that in. **It needs its own step and a different fix.**

The 5 remaining `review_needed` items are the correct ones — ex6-4 LP-20 (0 of 7), solidpower LP-02
(0 of 4), and items with no element verdicts. The guard is doing its job.

---

# WHAT IS NOT ESTABLISHED

- **The marker change was not literally briefed.** §2 named the headline guard. I extended `[GAP]` →
  `[REVIEW]` to `partial`-with-no-adverse-gap on the argument in §2 above. **Named here so it can be
  reverted in one line.**
- **One model-path LP is caught by the marker change:** `divall(496) LP-27`, `partial_material`,
  `materiality: high`, `elements_missing: []`, 6 of 10 present with 3 unresolved. Its headline is
  model-written (*"Limited remedies for landlord default"*) and is untouched; only the marker flips.
  **`[REVIEW]` is accurate — nothing in that record is recorded as absent, and "(HIGH materiality)"
  still carries the severity** — but it is the one flip outside the 19 and I am not hiding it. That run
  also predates Step 522, so its `assessment_status` is unset and `_resolve_display` currently routes
  it to `not_assessed`, meaning the callout would not render at all in that particular artefact.
- **`broken_xref` is not fixed.** 7 LPs, §5.
- **No pipeline was run.** Every artefact is produced by calling the real functions on stored Step-537,
  -528, -525, -524, -522 and -496 results. Stored JSON still carries the old strings; the change appears
  in a new run's persisted result.
- **The scope label remains inert.** Step 546 established no consumer reads `_resolve_display`'s
  `label`; that is unchanged here.
- **`materiality: low` on all 19 is unexamined**, including a 12-element assignment clause. Flagged
  since Step 539.
- **`covered_unfavorable` keeps an unconditional `[GAP]`** even with an empty missing list — a term
  rather than an omission. Deliberately out of scope; a test asserts it is unchanged.
