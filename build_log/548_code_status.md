# Step 548 — Pushed. 11 commits, branch only, both sanction tags still local. The brief's "three categories" is five.

**Date:** 2026-09-03 · **Instruction:** `build_log/548_chat_instruction.md`
**`43e0f83..f0415d9  main -> main`. Railway will deploy from this. Tests: 427 passed, 3 skipped, 12 subtests.**

---

# 1. PREFLIGHT — CLEAN

```
git fetch origin          -> no incoming
git status -sb            -> ## main...origin/main [ahead 11]
git rev-list --count      -> 11
```

**Deployable files, by commit** (536 through 547; the seven commits not listed touched only
`build_log/`):

```
536  05 Lease Analyzer/test_data/edgar_corpus_manifest.json + 4 lease fixtures  (test data only)
538  cam/adapters/lease_review/lease_display.py
539  05 Lease Analyzer/app/summary_generator.py
     cam/adapters/lease_review/{lease_coverage,lease_display,lease_report_generator}.py
543  cam/adapters/lease_review/{lease_docx_annotator,lease_pdf_annotator,lease_report_generator}.py
546  cam/adapters/lease_review/{lease_display,lease_docx_annotator,lease_exposure,lease_pdf_annotator}.py
     + tests/test_546_resolution_scope.py
547  cam/adapters/lease_review/{lease_docx_annotator,lease_exposure,lease_pdf_annotator}.py
     + tests/test_547_partial_scope.py
```

**537, 540+541, 542, 544, 545 shipped no code** — diagnostics and reports.

```
forbidden paths (results/, _*_results/, .env, .tmp.driveupload, keys, creds) : NONE
secret scan on the full diff (sk-/xai-/AIza/ghp_/PRIVATE KEY/Bearer/api_key)  : NO MATCHES
```

The only hits for `secret|token` in added lines are lease prose (*"Attn. Corporate Secretary"*, a
vending-machine clause naming *"coin or token operated"* machines) and output-token counts in status
files.

**No frontend file is in this batch** — no `static/` or `index.html` change — so the `index.html`
version bump does not apply. `app.js?v=475` from Step 533 is already live.

---

# 2. FLAG STATE — NOT ONE FLAG LINE IS TOUCHED BY THESE 11 COMMITS

```
git diff origin/main..HEAD -- lease_adapter.py lease_coverage.py lease_coverage_305.py
  | grep flags  ->  NONE
```

What goes live, read from the deployed source:

```
SPAN_EVIDENCE_ENABLED       = True                                lease_coverage.py:51
SPAN_EVIDENCE_LPS           = {"LP-07","LP-12","LP-17","LP-27"}   lease_coverage.py:52
SECTION_EXPANDED_SPAN_LPS   = set()                               lease_coverage.py:76
ENTAILMENT_TEST_LPS         = {"LP-27"}                           lease_coverage_305.py:284
GATE_ABORT_RETURNS_DEGRADED = True                                lease_adapter.py:173
DEGRADABLE_APPLICABILITY    = {"not_applicable","unclear"}        lease_adapter.py:194
```

**Identical to the Step-537 run's recorded flags.** No behavioural flag moves in this deploy.

---

# 3. WHAT CHANGES FOR A USER

## The top line is FIVE categories, not three — correcting the brief

The brief describes *"three categories plus not_assessed beside it."* **What deploys is five**, and
this was already established at Step 540 §0 against the same premise:

```
needs_attention | worth_reviewing | minor_gaps | not_assessed | covered
```

butler_crossing, tenant, as it will render:

```
4 issue area(s) require attention, 8 worth reviewing,
18 substantially addressed with minor gaps, 2 NOT ASSESSED, 0 covered.
```

**`minor_gaps` is the fifth and it is the point of Step 539.** Collapsing it into `covered` is what made
the Step-537 report say *"18 covered"* about a lease with **zero** LPs in state `covered` — all 18 were
partials reclassified on low materiality. Collapsing it into `needs_attention` instead would put an LP
with 5 of 6 elements beside one with 0 of 7.

**`not_assessed` beside the top line and never inside it — that part of the brief is right**, and it was
already live (Step 522).

**One shared helper across six sites** is accurate: `summarize_display_buckets` at
`lease_display.py:312`, with `lease_coverage.summarize_coverage` delegating to it. Before Step 539 the
same result object carried **both 0 and 18** for `covered_count` from two independent formulas.

## Exports admit more, and the cost is length not volume

`ANNOTATED_BUCKETS` gains `minor_gaps`:

```
{asymmetric_terms, favorable_to_your_side, minor_gaps, needs_attention, worth_reviewing}
```

Measured per document — LPs admitted to the annotated DOCX/PDF:

```
run              LPs   admitted before   admitted now
ex6-4/butler      32          12              30
solidpower(528)   32          10              21
atlas(524)        32           8              27
divall(496)       32           0               0   <- see caveat
```

**A typical report roughly doubles to triples its findings**: on butler_crossing that is **7 → 23
rendered `[GAP]` callouts**, for **+3.2% bytes and +10.7% characters** — 16 extra paragraphs on a
330-paragraph document. The findings are not the bulk of the artefact.

**divall(496) shows 0 both ways because that run predates Step 522**, so its `assessment_status` is
unset and every LP fail-closes to `not_assessed`. That is an artefact of an old stored result, not of
this deploy.

## 46 headlines stop asserting absence against their own record

```
review_needed -> review_needed_scope   27
partial       -> partial_scope         19
```

Per document, **4 to 13 headlines change**. Three examples that were flatly false:

```
Atlas LP-26 Quiet Enjoyment   elements_missing: []   6 of 7 present
   was  "Quiet enjoyment covenant absent or undefined"
   now  "1 of 7 elements unresolved"
ex6-4 LP-11 Default & Remedies   15 of 17 present
   was  "Default and remedy framework absent or incomplete"
   now  "1 of 17 elements unresolved"
ex6-4 LP-05 Permitted Use   elements_missing: []   3 of 4 present
   was  "Use restrictions absent or undefined"
   now  "1 of 4 elements unresolved"
```

The cause was a static per-LP schema string emitted by a catch-all that never read the assessment.
**Measured after: zero schema-sourced headlines assert absence with an empty adverse-missing list.**

## `[REVIEW]` replaces `[GAP]` where the record names no gap

4 to 8 callouts per document. `[GAP]` was an unconditional literal chosen by display bucket; on LP-26 it
sat beside *"Resolved: 6 of 7 expected elements confirmed present"* with **no `Missing:` line at all**,
because that line is emitted only for a non-empty list.

**One flip is outside the 19 partials**: `divall LP-27`, `partial_material`, high materiality,
model-written headline untouched — only the marker moves.

## Also deployable, not in the brief's list

- **Step 538 — `NO ELEMENTS FOUND`.** `_resolve_display` no longer ends in an unconditional
  `return covered`; an assessed LP with zero elements present is `needs_attention`. This is what stops
  ex6-4 LP-20 rendering as covered.
- **Step 543 — the annotators no longer return a bare path.** They return a report
  (`complete: false` when partial) and write `results["annotation_reports"]["docx"|"pdf"]`.
  **Reader-visible effect:** the summary cover PDF gains a conditional note naming findings that could
  not be placed beside a clause. Silent when there are none.
- **Steps 546/547 — new export lines.** `Resolved: N of M expected elements confirmed present.` and
  `Unresolved (K): ...` in both DOCX and PDF callouts. `element_verdicts` reached the exports zero times
  before this.
- **Step 536 — four retail lease fixtures + manifest.** Test data. No runtime path reads them.
- **Two new test files**, 21 tests. Not user-facing.

---

# 4. WHAT DOES NOT CHANGE

- **ex6-4 LP-20 at 0 of 7 still reads as genuinely absent.** `reason_code: schema_default`, headline
  *"Exclusivity protection absent or undefined"*, `[GAP]` with its five `Missing:` elements, display
  `NO ELEMENTS FOUND`. **Byte-identical through Steps 546 and 547.** `settled_present == 0` is the
  guard, and `test_absent_lp_keeps_schema_statement` fails if a later change softens it.
- **Model-path headlines are untouched.** `_build_scope_exposure` lives in the schema path only.
  Measured across six runs: **zero model-sourced headlines changed** — 9 `missing`,
  4 `covered_unfavorable`, 3 `partial` all unchanged.
- **No `coverage_state` was added.** The schema still has exactly the states it had.
- **`derive_lp_state` is unmodified.** The `any_unclear` veto is intact; Step 545 established it is
  specified at `Docs/Step_305_Architecture.md:179` and load-bearing.
- **No panel verdict, element verdict, or `requires_attention` value changes anywhere.** Bucket totals
  across 192 LPs are identical before and after: `needs_attention 20, worth_reviewing 25, covered 14,
  minor_gaps 82, not_assessed 51`.
- **The scope label is inert.** `REVIEW NEEDED — 1 OF 17 ELEMENTS UNRESOLVED` exists on
  `_resolve_display`'s output and **no consumer reads it**; the scope reaches readers through the
  headline and the new export lines instead.

---

# 5. THE PUSH

```
To https://github.com/zvido1/cam.git
   43e0f83..f0415d9  main -> main

## main...origin/main        unpushed: 0
```

**Branch only. `--follow-tags` was NOT used.** Both sanction tags remain local and are absent from the
remote:

```
local:  stage2-sanction-431-ef1a7af7
        stage2-sanction-452-e0b985b4
remote: (no tags)
```

---

# WHAT IS NOT ESTABLISHED

- **The brief's "three categories" is wrong and the deploy carries five.** Corrected in §3; the same
  premise was corrected at Step 540. **Nothing in the repository was unexpected**, so I did not halt —
  the mismatch is in the description of what deploys, not in what deploys.
- **No pipeline was run against HEAD.** Every user-visible figure comes from calling the real functions
  on stored Step-537/-528/-524/-496 results. **The first live Mode C run on this build is unobserved.**
- **Railway's deploy is not confirmed.** I pushed; I did not watch the build, and I have not verified
  the service came up.
- **`broken_xref` still emits canned prose with no record behind it** — 7 LPs, reported at Step 547 and
  deliberately not fixed. It ships as-is.
- **`_classify_materiality` is untouched**, so callouts still read "(LOW materiality)" on things like a
  12-element assignment clause. Flagged since Step 539.
- **The web screen categorises independently.** `app.js` does not use `_resolve_display`, so
  `minor_gaps` does not exist on screen; only the exports and summary carry the five-category scheme.
