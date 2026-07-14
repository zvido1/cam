# Step 423C — Element-Guided, Non-Exclusive Span Elicitation

**Date:** 2026-07-14
**Status:** COMPLETE — sidecar only, slice three of 423

---

## Required Smoke-Test Disclaimer

> This is an n=1 plumbing smoke test. It proves the elicitation path runs
> and produces resolvable spans. It is not a measurement of recall, it is
> not evidence the architecture works, and no count from it may be cited
> as validation.

---

## What Was Built

1. **`cam/adapters/lease_review/lease_element_elicitation.py`** (new module):
   element loading from `expected_elements_305`, the element-guided
   elicitation call, code-side resolution through the **unmodified** 423A
   substrate, offset-based deduplication, and a sidecar-artifact builder.
2. **`cam/adapters/lease_review/prompts/element_elicitation.txt`** (new
   prompt): element-aware, structured as a neutral ordinal target list,
   explicit repetition requirement, parameter-grained quoting instruction.
3. **`cam/adapters/lease_review/schemas/element_elicitation_schema.json`**
   (new schema): `additionalProperties: false` at both levels, same
   LP-blindness enforcement mechanism as 423B.
4. **`build_log/423C_span_universe_smoke_sidecar.json`**: output of the one
   authorized n=1 plumbing smoke test (LP-07 + LP-02, see Part 6).
5. **`cam/adapters/lease_review/tests/test_423c_element_guided_elicitation.py`**:
   28 new tests.

**423B's module (`lease_segmentation.py`) was left in place, untouched.**
It is a tested, committed, historical artifact. 423C supersedes it as the
elicitation approach going forward but takes no destructive action against
it — no file was deleted or modified beyond what this step's own new files
require. **`lease_evidence_spans.py` (423A) was not modified** — confirmed
by `git status` showing zero diff and by a dedicated seam test.

---

## Why 423B's Approach Changed (context, not new work)

423B's LP-blind call had no target — asked to "find every legally material
passage," it proposed 18 spans and stopped. Two consequences visible in
the 423B sidecar: (1) `EV-000001` was an 802-char blob carrying ten
distinct parameters at once — unattachable to a single dependency; (2) the
Controllable Expenses Cap, a declared LP-07 element, was never proposed.

**The correction, and the distinction that must not collapse:**
LP-blindness was a means (stop partitioning), not an end (stop the model
knowing what to look for). Guided elicitation asks about one element at a
time, over the whole document, with repetition explicitly required — the
opposite of a partition. The **prompt** is element-aware; the **artifact**
stays LP-unassigned. A span's identity is its offsets, never the element
that elicited it.

---

## Batching Choice and Rationale

**Chosen: batch by LP.** One elicitation call per LP that declares
`expected_elements_305` (32 LPs in the current schema — `LP-01` through
`LP-33` minus one that has none — not the 33 the brief estimated; confirmed
by `load_expected_elements_by_lp()` and `TestLoadExpectedElements`), with
all of that LP's elements (4–8 typically; LP-07 has 6) presented in one
call as a neutral, ordinal target list.

**Why:** 212 total elements exist across all LPs (confirmed by direct
count against `retail_lease_knowledge.json`). Calling once per element,
each call carrying the full ~160K-char document, would be a 212-call sweep
— roughly 6.6x the cost of the 32-call LP-batched alternative, for a slice
whose brief explicitly says "your call on cost." LP-batching keeps the call
count in the same order of magnitude as extraction's own per-LP structure
while still asking about each element as an independent target within the
call (see prompt: "Every target is independent and gets its own answer").

**Why this does not reintroduce partitioning:** the model is never told
these targets are grouped under a provision. `_build_target_list_text()`
renders each element as `"Target N: <element_label>"` plus synonyms —
never `element_id`, never an LP identifier. `TestElicitationPromptIsLPBlind`
proves the rendered prompt for every one of the 32 LPs contains no
substring matching that LP's own id. The grouping is an artifact of how
*we* chose to batch a cost decision; from the model's perspective it is
just N unlabeled search targets in one call, and it is explicitly
instructed to answer each independently and to repeat a passage across
targets rather than withhold it.

---

## Parameter-Grained Spans

The prompt instructs: *"Quote the NARROWEST passage that fully carries the
target. If the target is a discrete labelled fact — a single value,
percentage, date, or defined term in a table or key-terms block — quote
just that line or row, not the surrounding paragraph or the whole table."*

The smoke run (Part 6) shows this working on the real fixture: `Tenant's
Share of Operating Expenses of Building: 100%` and `Building's Share of
Project: 45.79%` resolved as **two separate, narrow spans** — not one
802-char blob as in 423B. This is what makes a later dependency-map
attachment (`LP-07 depends_on: tenant_share`) point at something specific
rather than a paragraph carrying ten unrelated facts.

---

## Deduplication Rule

`resolve_elicited_spans()` resolves every `(target, quote)` pair through
the **unmodified** 423A `resolve_span()` — one raw record per quote, no
deduplication. `dedupe_elicited_spans()` is the single function that
implements Task 3:

- Two records are the same span **iff** both are `verified` and their
  `(start_char, end_char)` are identical.
- Merge combines `elicited_by` (union, first-seen order) and
  `quote_variants` (union) into one record with one fresh
  `evidence_span_id`.
- **Overlapping-but-not-identical ranges are never merged** — the function
  performs no containment check of any kind; the only comparison is exact
  offset-pair equality (`TestOverlappingNotMerged`).
- `ambiguous`/`unverified` records have `start_char = end_char = None` and
  are therefore never merged with anything, including each other — each
  stays its own record (`TestSpanIdentityOffsetsOnly::test_ambiguous_records_never_merged_by_none_offset`).

This single function is applied whether the duplicate quotes come from two
targets in the *same* LP-batched call or from *different* LPs' calls
entirely — `elicit_and_resolve_for_lp()` returns raw (undeduped) records
per LP specifically so a caller running multiple LPs can pass **all** raw
records through one `dedupe_elicited_spans()` call and get cross-LP
non-exclusivity for free. The smoke run demonstrates this: a Base Rent
escalation clause was independently elicited by three different LP-02
elements in one call and collapsed into one span with three `elicited_by`
entries (see Part 6).

---

## Provenance Is Not Routing

`elicited_by` is populated only after resolution, by `dedupe_elicited_spans`,
and is documented in the module docstring as audit-only. `TestSpanIdentityOffsetsOnly`
proves this two ways: (1) behaviorally — two records at the *same* offset
with *different* `elicited_by` merge, and two records at *different*
offsets with *identical* `elicited_by` do **not** merge, proving the key
is strictly `(start_char, end_char)`; (2) structurally — a code-inspection
test asserts `dedupe_elicited_spans`'s source contains no `elicited_by ==`
comparison anywhere.

---

## How Elicited Spans Resolve Through 423A (unchanged)

`resolve_elicited_spans()` and `dedupe_elicited_spans()` call
`lease_evidence_spans.resolve_span()` and `is_usable_in_canonical_stage5()`
— imported, not duplicated, not modified. `TestVerificationSemanticsUnchanged`
directly re-proves the four core 423A outcomes (unique→verified,
duplicate→ambiguous, invented→unverified, changed-digit→unverified) through
this module's wrapper, confirming the wrapper adds provenance/dedup
bookkeeping without altering verification semantics.

---

## Segmentation-Call Integrity (same doctrine as 423B)

`elicit_spans_for_targets()` mirrors `propose_spans()`'s doctrine exactly:
`ModelTarget` built the same way, `_check_generation_integrity()` (imported
from `cam.core.provider_router`, not modified) asserted before the call,
`canonical` an **explicit** parameter written to an **explicit** metadata
field — never inferred from `fallback_used`.
`test_canonical_flag_never_inferred_from_fallback_used` constructs the
422D-bug-class case directly: `fallback_used=False` (no fallback provider
exists) **and** `canonical=False` **and** the primary call fails, and
asserts `canonical` still reads explicitly `False`. In canonical mode, a
primary failure raises `ElicitationIntegrityError` (mirrors
`ExtractionIntegrityError`/`SegmentationIntegrityError`) rather than
silently degrading.

---

## Tests Executed — `test_423c_element_guided_elicitation.py` (28 tests)

```
TestDedupSamePassageTwoElements::test_quote_variants_preserved_on_merge PASSED
TestDedupSamePassageTwoElements::test_same_offsets_merge_into_one_span_with_two_provenance_entries PASSED
TestOverlappingNotMerged::test_overlapping_ranges_remain_separate_spans PASSED
TestElicitationPromptIsLPBlind::test_all_lp_elements_produce_lp_free_prompts PASSED
TestElicitationPromptIsLPBlind::test_prompt_contains_no_verdict_risk_favorability_vocabulary PASSED
TestElicitationPromptIsLPBlind::test_rendered_prompt_contains_no_lp_ids PASSED
TestSpanIdentityOffsetsOnly::test_ambiguous_records_never_merged_by_none_offset PASSED
TestSpanIdentityOffsetsOnly::test_dedupe_source_contains_no_elicited_by_equality_check PASSED
TestSpanIdentityOffsetsOnly::test_different_offset_same_elicited_by_does_not_merge PASSED
TestSpanIdentityOffsetsOnly::test_same_offset_different_elicited_by_merges PASSED
TestVerificationSemanticsUnchanged::test_changed_digit_unverified PASSED
TestVerificationSemanticsUnchanged::test_duplicated_quote_ambiguous PASSED
TestVerificationSemanticsUnchanged::test_invented_quote_unverified PASSED
TestVerificationSemanticsUnchanged::test_unique_quote_verified PASSED
TestOutputContract::test_element_id_field_rejected PASSED
TestOutputContract::test_verdict_field_rejected PASSED
TestOutputContract::test_well_formed_output_passes PASSED
TestLoadExpectedElements::test_all_returned_lps_have_nonempty_elements PASSED
TestLoadExpectedElements::test_lp07_has_six_elements_including_cam_cap PASSED
TestElicitationCallIntegrity::test_canonical_flag_never_inferred_from_fallback_used PASSED
TestElicitationCallIntegrity::test_canonical_flag_recorded_explicitly_on_success PASSED
TestElicitationCallIntegrity::test_canonical_primary_failure_raises_elicitation_integrity_error PASSED
TestElicitationCallIntegrity::test_declared_params_transmitted_and_checked PASSED
TestElicitationCallIntegrity::test_fallback_fields_visible_in_metadata PASSED
TestSidecarMetadata::test_sidecar_contains_dedup_stats_and_batching_note PASSED
TestPipelineSeam::test_evidence_spans_module_not_modified_by_this_slice PASSED
TestPipelineSeam::test_no_live_pipeline_file_imports_elicitation_module PASSED
TestPipelineSeam::test_no_live_pipeline_file_reads_the_sidecar_artifact PASSED
28 passed in 0.47s
```

No network calls in the pytest suite — every model call in the automated
tests is mocked. The Part 6 smoke run below is the one real call, run
separately (not part of `pytest`).

**Full regression:** 290 passed (262 pre-423C + 28 new). No regressions.

```
290 passed, 5 warnings in 2.27s
```

---

## Part 6 — Smoke Run (n=1, NOT Validation)

> This is an n=1 plumbing smoke test. It proves the elicitation path runs
> and produces resolvable spans. It is not a measurement of recall, it is
> not evidence the architecture works, and no count from it may be cited
> as validation.

**What was run:** elicitation calls for **2 of the 32 LPs** — `LP-07`
(Common Area Maintenance, 6 elements) and `LP-02` (Rent Escalation, 4
elements) — against the real Atreca lease source
(`05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt`,
160,244 chars, `source_document_hash=e049ee63a4e2f475`, the same document
used in the 423B smoke test). `canonical=True` for both calls, no
exception, no `ElicitationIntegrityError`. **This is a deliberately bounded
subset — 2 of 32 LPs, chosen because their declared elements are the ones
needed to observe the four items the brief asked about. It is not a
32-LP sweep and no claim is made that it is.**

**Plumbing executed.** LP-07: 7 raw quotes across 6 elements in 39.2s.
LP-02: 4 raw quotes across 4 elements in 12.7s.

**Resolver accepted/rejected, and dedup:** 11 raw quotes → **9 deduped
spans** (dedup ratio 1.222) → **8 verified, 0 ambiguous, 1 unverified.**

**Sample spans inspected** (all 8 verified, with `elicited_by`):

| Excerpt | elicited_by |
|---|---|
| "Tenant's Share of Operating Expenses of Building: 100%" | `LP-07.proportionate_share_calculation` |
| "Building's Share of Project: 45.79%" | `LP-07.proportionate_share_calculation` |
| `" Tenant's Share " shall be the percentage set forth on the first page...` | `LP-07.proportionate_share_calculation` |
| Operating Expenses definition clause | `LP-07.included_expense_categories` |
| Independent-Review / audit-rights clause | `LP-07.tenant_audit_rights` |
| Annual Statement reconciliation clause | `LP-07.reconciliation_timeline` |
| "Rent Adjustment Percentage: 3%" | `LP-02.annual_increase_mechanism` |
| Base Rent annual-anniversary escalation clause | `LP-02.annual_increase_mechanism`, `LP-02.effective_date_of_first_escalation`, `LP-02.calculation_methodology` |

The last row is a real, observed instance of the dedup mechanism doing its
job on live output, not just in unit tests: one clause, elicited
independently by three different LP-02 elements in the same batched call,
collapsed to one span carrying all three as provenance.

**Observations on the four named items (not a pass/fail checklist):**

- **`Tenant's Share ... 100%`** — resolved as its own **discrete, narrow
  span** (56 characters, the labelled line only) — not embedded in a
  larger blob as it was in the 423B sidecar's `EV-000001`.
- **`Building's Share ... 45.79%`** — likewise resolved as its own
  discrete span, separate from the Tenant's Share span. Both are
  parameter-grained, as the prompt requested.
- **`Rent Adjustment Percentage: 3%`** — resolved as its own discrete span,
  elicited by the LP-02 element whose synonyms include escalation
  mechanism language.
- **Controllable Expenses Cap (`LP-07.cam_cap`)** — produced **zero**
  quotes in this run. This is worth stating precisely: **the real Atreca
  document as loaded contains no Controllable Expenses Cap clause at all.**
  A direct text search of the source file (`grep -i "controllable"`,
  `grep "cap\b"`) confirms zero occurrences of any cap-adjacent phrasing
  tied to CAM/Operating Expenses anywhere in the 160,244-character
  document; the Operating Expense Exclusions list (items (a)–(u)) is
  present, but no cap follows it. `LP-07.cam_cap` correctly returning zero
  quotes for a clause that is not in the source is the correct outcome,
  not an elicitation failure — the risk this slice is designed to guard
  against is the model *hallucinating* a cap clause that isn't there, and
  it did not do that. Whether the modal Gemini extraction hash described
  in 421C (which reportedly included a Controllable Expenses Cap 8/10 runs)
  refers to a different version of this document, or that finding does not
  reproduce against the file currently in the repository, is not
  established by this one run and is not claimed here either way.

**One diagnostic concern, recorded as such:** the single `unverified`
record was `LP-07.excluded_expense_categories`'s attempted quote of the
Operating Expense Exclusions list — it did not resolve. Inspecting why:
the source text contains a literal stray page-number artifact (`"...
renovation;\n4\n(b) capital expenditures..."` — the `"4"` is a mid-list
page marker from the source document) that the model's quote apparently
omitted or reflowed past. Since the whitespace-flexible resolver requires
every *non-whitespace* character to match literally in sequence, a
digit-shaped page artifact breaks the match — correctly, per the Part 0
invariant (423B) that this profile must never mask a substantive
difference, and a stray "4" inserted mid-quote is exactly the kind of
non-whitespace content the resolver is right to refuse. This is recorded
as a diagnostic concern about long multi-item list quoting near embedded
page artifacts, not a defect in the resolver or a finding about recall.

Allowed language used above: "plumbing executed," "resolver
accepted/rejected spans," "sample spans inspected," "diagnostic concern."
No claim of "found, therefore fixed," no recall fraction, no "architecture
validated," no "LP-07 fixed" is made anywhere in this report.

---

## What Remains Deliberately Unwired

- Not wired into the live Mode C / Stage 5 pipeline — confirmed by
  `TestPipelineSeam` (no reference in `lease_adapter.py`, `lease_extract.py`,
  or `lease_coverage.py` to this module or the sidecar filename) and by
  `git status` showing only new files.
- `lease_evidence_spans.py` (423A) not modified.
- No global key-terms parameter block (423 spec §5.1).
- No LP dependency map (423 spec §5.2).
- No many-to-many span-to-LP *assignment decision* — `elicited_by` is
  provenance recording which elements elicited a span, not a governed
  relevance judgment. Relevance is the selection panel's job (423 spec §6),
  not built here.
- No selector-panel voting, no cited union merge.
- No feed of spans into Stage 5.
- No 32-LP full run, no N≥2 recall measurement — only the bounded 2-LP
  smoke run above, explicitly disclaimed.
- No evaluator identity change, no Stage 5 stabilization, no Priority
  Exposure, no `cam/core/` change, no `extra_provider_params`.
- No real fallback elicitor — `fallback_chain` is `[]` and `fallback_used`
  is always `False` by construction, same as 423B.
- 423B's `lease_segmentation.py` is not deleted or modified. It remains a
  tested historical artifact; this module supersedes it as the elicitation
  approach going forward.

---

## Constraints Honored

- `git status` on `cam/` shows only new, untracked files for 423C — zero
  diff to `lease_evidence_spans.py`, `lease_segmentation.py`,
  `lease_adapter.py`, `lease_extract.py`, or `lease_coverage.py`.
- No `cam/core/` file modified.
- No dependency map, parameter block, selection panel, or cited union built.
- No recall measurement beyond the one quarantined n=1 (2-LP) smoke run.
- No push.

---

## Files Changed

- `cam/adapters/lease_review/lease_element_elicitation.py` — new module
- `cam/adapters/lease_review/prompts/element_elicitation.txt` — new prompt
- `cam/adapters/lease_review/schemas/element_elicitation_schema.json` — new schema
- `cam/adapters/lease_review/tests/test_423c_element_guided_elicitation.py` — 28 new tests
- `build_log/423C_span_universe_smoke_sidecar.json` — n=1 smoke artifact (2 of 32 LPs)
- `build_log/423C_element_guided_elicitation.md` — this file
