# Step 423B — LP-Blind Span Proposal Sidecar

**Date:** 2026-07-14
**Status:** COMPLETE — sidecar only, slice two of 423

---

## Required Statement

> 423B creates a sidecar span proposal path. It does not make LP-07 see the
> 100% tenant share. That requires later global-parameter/dependency-map and
> many-to-many assignment slices.

## Required Sidecar Statement

> The 423B sidecar is not live pipeline input. Nothing in Stage 5,
> `assess_coverage`, Mode C, or downstream report generation reads it. The
> first component that consumes verified spans for evaluation must be built
> in a later authorized slice.

## Required Smoke-Test Warning

> This smoke test is not validation and must not be cited as evidence of
> segmentation recall or architecture correctness.

---

## What Was Built

1. **Part 0 follow-on:** normalization matching semantics documented explicitly
   in `lease_evidence_spans.py`'s module docstring (no resolver behavior
   changed — see below).
2. **`cam/adapters/lease_review/lease_segmentation.py`** (new module): the
   LP-blind segmentation/proposal call, its schema validator, its resolver
   bridge into the 423A substrate, its sidecar-artifact builder, and its own
   canonical fail-closed / integrity-checked call doctrine.
3. **`cam/adapters/lease_review/prompts/segmentation_span_proposal.txt`**
   (new prompt): LP-blind, structural-type-only, quote-don't-summarize.
4. **`cam/adapters/lease_review/schemas/segmentation_schema.json`** (new
   schema): `additionalProperties: false` at both levels — the structural
   enforcement of the LP-blindness contract.
5. **`build_log/423B_span_universe_smoke_sidecar.json`**: output of the one
   authorized n=1 plumbing smoke test (see Part 6 below).
6. **`cam/adapters/lease_review/tests/test_423b_lp_blind_segmentation.py`**:
   33 new tests.

---

## Part 0 — Normalization Semantics Follow-On

**No resolver code changed.** The exact-then-whitespace-flexible matching
behavior already existed in 423A (`_find_normalized_matches` in
`lease_evidence_spans.py`) and was already correct — it just wasn't declared
as a property of the normalization profile in the module's documentation.
This step closes that documentation gap and adds the required safety tests.

`lease_evidence_spans.py`'s module docstring now states explicitly:

- `canonical_text` is never rewritten or normalized; offsets always index
  the raw canonical source.
- `canonical_whitespace_v1` permits whitespace-run equivalence for
  *matching* only, never for rewriting the canonical text.
- Every non-whitespace character in a proposed quote must match literally —
  no paraphrase matching, no fuzzy/edit-distance matching, no numeric/date/
  word substitution.
- A `verified` span must satisfy `is_valid_invariant()`, which is
  re-checked (not merely assumed) before the status is returned.

**Required safety tests** (`TestPart0NormalizationSafetyFollowOn`, 3 tests):

| Test | Input | Expected |
|---|---|---|
| `test_changed_digit_is_unverified` | source has `45.79%` (via `45%`-shaped test fixture: "Rent Adjustment Percentage: 3%"); proposed quote changes it to `4%`/`45.80%`-style single-digit change | `UNVERIFIED` |
| `test_whitespace_reflow_is_verified` | source has a line break/multi-space run; proposed quote reflows whitespace only, all non-whitespace chars match | `VERIFIED` |
| `test_canonical_usability_false_for_changed_substantive_content` | substantively changed quote | `is_usable_in_canonical_stage5()` is `False` |

All three pass. See also `TestProposalResolutionOutcomes::test_changed_digit_fails`
in Part 7, which exercises the same guarantee through the segmentation-layer
wrapper (`resolve_proposed_spans`) rather than the raw 423A resolver.

---

## The Structural-Only Span Taxonomy

Four allowed values, enforced by `ALLOWED_SPAN_TYPES` and by the JSON
schema's `enum`: `clause`, `table`, `definition`, `other`.

Semantic/legal labels (`cap`, `carveout`, `condition`, `exception`,
`remedy`, `cross_reference`, `key_term`) are explicitly excluded from the
prompt and rejected by schema validation — `TestStructuralSpanTypesOnly`
proves both the four allowed types pass and all seven listed semantic
labels are rejected.

**Why:** those labels are legal-role judgments, not structural facts. The
Controllable Expenses Cap might be called a cap, a clause, or a carve-out
depending on the model — that classification belongs to the governed
selection/evaluation layer (423 spec §6/§7), not the single-model
segmentation layer.

---

## The LP-Blindness Contract

`segmentation_schema.json` declares `additionalProperties: false` on both
the top-level object and each span item. This is the structural enforcement
mechanism: an LP id, provision id, coverage verdict, risk label, or
favorability field added to a proposal object fails schema validation
rather than being silently accepted and carried downstream.
`TestLPBlindOutputContract` (6 tests) proves a well-formed proposal passes
and that `provision_id`, `lp_id`, `coverage_verdict`, `risk`, and
`tenant_favorable` are each independently rejected.

The prompt (`segmentation_span_proposal.txt`) explicitly instructs the
model not to output any of these, not to decide LP relevance, not to force
text into a single bucket, and not to summarize instead of quoting. It
instructs the model to propose tables, key commercial terms, exclusions,
caps, carve-outs, conditions, exceptions, and cross-references as candidate
spans **when they appear in source** — without deciding what any of them
mean or to which LP they might later matter.

---

## The Proposal Schema

Each proposed span (`segmentation_schema.json`):

```json
{
  "quote": "verbatim source text",
  "span_type": "clause | table | definition | other",
  "section_hint": "optional",
  "page_hint": "optional",
  "table_hint": "optional",
  "neutral_label": "optional, human-inspection only"
}
```

---

## Neutral Label — Non-Routing Provenance

`neutral_label` is preserved through resolution into the sidecar record but
is never read by any conditional. `TestNeutralLabelNonRouting` (3 tests)
proves: the schema allows it; two proposals identical except for
`neutral_label` resolve identically (same status, same offsets — the label
carries no weight); and `resolve_proposed_spans`'s source contains no
conditional keyed on the label's value (a direct code-inspection check, not
just a behavioral one).

---

## How Hints Are Used and Why They Are Not Persisted as Span Identity

`section_hint`, `page_hint`, and `table_hint` are proposal-layer metadata
only. `resolve_proposed_spans` maps `section_hint → section_ref` and
`table_hint`/`page_hint → source_anchor` — the two optional disambiguation
fields the **423A** `EvidenceSpan` schema already declares. No new field
was added to `EvidenceSpan`.

`TestHintsNotCanonicalIdentity` proves this two ways:
1. **Behaviorally:** a duplicated quote resolves to the correct (non-first)
   occurrence when a `table_hint` uniquely disambiguates it via the 423A
   anchor-window search — hints do useful work.
2. **Structurally:** `EvidenceSpan.__dataclass_fields__` is asserted to be
   exactly the 423A eleven fields (`evidence_span_id`,
   `source_document_hash`, `canonical_text_hash`, `start_char`, `end_char`,
   `span_text`, `span_text_hash`, `normalization_profile`,
   `verification_status`, `section_ref`, `source_anchor`) — no `page_ref`,
   no `table_ref`, no `page_hint`, no `table_hint` field exists on the
   persisted object. The authority of a persisted span is the offset-
   resolved source slice, never the model's hint.

---

## How Proposed Spans Resolve Through 423A

`resolve_proposed_spans(canonical_source, proposals)` calls
`lease_evidence_spans.resolve_span()` once per proposal — unmodified,
imported, not duplicated. For each proposal it returns a record with: the
proposed quote and structural type, the neutral label, the hints used, the
resolved `evidence_span_id`, `verification_status`
(`verified`/`ambiguous`/`unverified`), offsets if verified, all three
hashes, a human-readable `failure_reason` when not verified, and
`usable_in_canonical_stage5` (delegating to 423A's
`is_usable_in_canonical_stage5()` — the single doctrine predicate, not
reimplemented here).

---

## Segmentation-Call Integrity

`propose_spans()` builds a `ModelTarget` exactly as `lease_extract.py`'s
extraction chain does (same `_get_adapter_for_provider`, same pattern), and
before calling the model it constructs the outbound params dict
(`{"temperature": ..., "max_tokens": ...}`) and asserts it via
`_check_generation_integrity()` — **imported from `cam.core.provider_router`,
not modified**. This is the same 416 doctrine applied to a new call site
without a `cam/core/` change, as the brief required ("if
`_check_generation_integrity()` cannot be reused directly, add an
equivalent... rather than leaving this call outside the guard" — it *can*
be reused directly here, since it's a plain importable function, so it is).

**Metadata recorded** (`result["meta"]`), always present regardless of
outcome:

| Field | Notes |
|---|---|
| `provider` / `model` | actual, or `"none"` on total failure |
| `primary_provider` / `primary_model` | declared primary |
| `canonical` | **explicit field**, set from the caller's `canonical` arg — never inferred from `fallback_used` (see below) |
| `fallback_used` | always `False` in this slice — no fallback provider is implemented |
| `fallback_chain` | always `[]` in this slice, for the same reason |
| `degraded` | `True` only on a non-canonical primary failure |
| `parse_or_validation_failure_reason` | populated on failure, else `None` |
| `declared_generation_config` | `{provider, model, temperature, max_output_tokens}` |
| `integrity_metadata` | the dict returned by `_check_generation_integrity()` |
| `prompt_hash` / `config_hash` | sha256[:16] of the prompt template / declared config |
| `elapsed_sec`, `errors`, `attempt_chain` | as in extraction |

**Canonical fail-closed doctrine, and the 422D lesson applied on day one:**
`canonical` is read from an explicit parameter and written to an explicit
metadata field — never derived from `fallback_used`. This is exactly the
bug class 422D fixed in the extraction gate (`canonical` conflated with
`fallback_used`, making the non-canonical degraded path unreachable). 423B
does not repeat it: `test_canonical_flag_recorded_explicitly_on_degraded_path`
constructs the case where `fallback_used=False` (there's no fallback
provider) **and** `canonical=False` **and** the primary failed, and asserts
`canonical` still reads explicitly `False` — not conflated with the
also-`False` `fallback_used`.

**No fallback chain exists in this slice, deliberately.** Only
`SEGMENTATION_PRIMARY` (`EXTRACTION_CHAIN[0]`, i.e. Gemini) is called. In
canonical mode, a primary failure raises `SegmentationIntegrityError`
(mirrors `ExtractionIntegrityError`, 421B) rather than silently degrading.
In non-canonical mode, a primary failure returns `spans: []` with
`degraded: True` — visibly, not silently.

---

## Sidecar Artifact

`build_span_universe_sidecar(canonical_source, segmentation_result, resolved_records)`
assembles: `source_document_hash`, `canonical_text_hash`,
`normalization_profile`, `run_id`, the full `segmentation_meta` block above,
total/verified/ambiguous/unverified counts, counts by structural type, the
verified-spans list (offsets + excerpt + neutral label), the
ambiguous/unverified list (with `failure_reason`), and two explicit
provenance markers: `neutral_label_is_non_routing_provenance: true` and
`hints_are_non_canonical_resolution_aids_only: true`.

The artifact is prefixed with `_artifact_type`, `_not_live_pipeline_input:
true`, and a `_warning` string stating in the JSON itself that nothing in
Stage 5 / `assess_coverage` / Mode C / report generation reads it.

Produced at: **`build_log/423B_span_universe_smoke_sidecar.json`**
(9.8 KB — one run's worth of spans, not a results directory).

---

## Part 6 — Smoke Test (n=1, NOT Validation)

> This is an n=1 plumbing smoke test only. It proves the segmentation
> proposal path can run and produce resolvable spans. It is not a
> measurement of segmentation recall, it is not evidence that the
> architecture works, and no count from this smoke test may be cited as
> validation.

**What was run:** one live call to `gemini-3.1-pro-preview` (the
segmentation primary) against the real Atreca lease source
(`05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt`,
160,244 chars — the same document referenced throughout 421C/422/423,
confirmed by locating `"45.79"` at char 2028), `canonical=True`,
`max_output_tokens=16000` (bounded — smaller than extraction's 65k ceiling,
deliberately, since this is a plumbing check, not production usage).

**Plumbing executed.** No exception, no `SegmentationIntegrityError`.

**Resolver accepted/rejected:** 18 spans proposed, **18 verified, 0
ambiguous, 0 unverified**. Counts by structural type: `table: 1, clause:
16, definition: 1`.

**Sample spans inspected:** the 18 verified spans include the premises
description table, the Base Term clause, Landlord's Work delivery
provisions, a condition-precedent clause, the Rent Commencement definition,
the annual rent-escalation clause, project-cost/Operating-Expense language,
a 95%-occupancy gross-up clause, holdover, essential-services abatement,
alterations, casualty/restoration, assignment/subletting economics, estoppel,
and a broker-representation clause — a structurally varied sample (tables,
clauses, one definition), consistent with what a segmenter should surface.

**Diagnostic concern, recorded — NOT a measurement:** the key-terms table
containing `"45.79%"` (Building's Share of Project Operating Expenses,
per 421C §2c) does **not** appear in any of the 18 verified excerpts in
this single run. This is the same content whose absence from LP-07 started
the 421C incident — its absence from this n=1 segmentation-layer smoke
run is noted here as a diagnostic concern for whoever designs the real
segmentation-recall measurement, not as a finding that the segmentation
layer "misses" it. **A real segmentation recall measurement requires its
own later step with N≥5 runs, a stated hypothesis, fixed prompt/config
hashes, and a predefined target set** — none of that exists here.

Allowed language used above: "sidecar produced," "resolver
accepted/rejected spans," "plumbing executed," "sample spans inspected."
No claim of "found, therefore fixed," no recall fraction, no "architecture
validated," no "LP-07 fixed" is made anywhere in this report.

---

## Tests Executed — `test_423b_lp_blind_segmentation.py` (33 tests)

```
TestPart0NormalizationSafetyFollowOn::test_canonical_usability_false_for_changed_substantive_content PASSED
TestPart0NormalizationSafetyFollowOn::test_changed_digit_is_unverified PASSED
TestPart0NormalizationSafetyFollowOn::test_whitespace_reflow_is_verified PASSED
TestLPBlindOutputContract::test_favorability_field_rejected PASSED
TestLPBlindOutputContract::test_lp_assignment_field_rejected PASSED
TestLPBlindOutputContract::test_lp_id_field_rejected PASSED
TestLPBlindOutputContract::test_risk_field_rejected PASSED
TestLPBlindOutputContract::test_verdict_field_rejected PASSED
TestLPBlindOutputContract::test_well_formed_proposal_passes PASSED
TestStructuralSpanTypesOnly::test_all_four_allowed_types_pass PASSED
TestStructuralSpanTypesOnly::test_semantic_types_rejected PASSED
TestNeutralLabelNonRouting::test_neutral_label_does_not_affect_resolution_outcome PASSED
TestNeutralLabelNonRouting::test_neutral_label_may_be_present PASSED
TestNeutralLabelNonRouting::test_no_downstream_branch_on_neutral_label PASSED
TestProposalResolutionOutcomes::test_ambiguous_quote_not_verified PASSED
TestProposalResolutionOutcomes::test_changed_digit_fails PASSED
TestProposalResolutionOutcomes::test_exact_quote_resolves_verified PASSED
TestProposalResolutionOutcomes::test_invented_quote_unverified PASSED
TestProposalResolutionOutcomes::test_whitespace_reflow_verified PASSED
TestHintsNotCanonicalIdentity::test_anchor_hint_disambiguates_but_is_not_persisted_on_evidence_span PASSED
TestHintsNotCanonicalIdentity::test_evidence_span_dataclass_has_no_page_ref_or_table_ref PASSED
TestHintsNotCanonicalIdentity::test_persisted_identity_fields_are_offset_and_hash_based_only PASSED
TestSidecarArtifactMetadata::test_sidecar_contains_required_metadata PASSED
TestSidecarArtifactMetadata::test_sidecar_is_json_serializable PASSED
TestSegmentationCallIntegrity::test_canonical_flag_recorded_explicitly_on_degraded_path PASSED
TestSegmentationCallIntegrity::test_canonical_flag_recorded_explicitly_on_success PASSED
TestSegmentationCallIntegrity::test_canonical_primary_failure_raises_segmentation_integrity_error PASSED
TestSegmentationCallIntegrity::test_declared_params_transmitted_and_checked PASSED
TestSegmentationCallIntegrity::test_fallback_chain_and_fallback_used_visible_in_metadata PASSED
TestSegmentationCallIntegrity::test_sidecar_records_actual_provider_model_config PASSED
TestPipelineSeam::test_evidence_spans_module_does_not_import_segmentation PASSED
TestPipelineSeam::test_no_live_pipeline_file_imports_segmentation_module PASSED
TestPipelineSeam::test_no_live_pipeline_file_reads_the_sidecar_artifact PASSED
33 passed in 0.51s
```

No network calls in the pytest suite — every model call in the automated
tests is mocked. The one real call is the Part 6 smoke script, run
separately (not part of `pytest`), and its result is the sidecar JSON, not
a test assertion.

**Full regression:** 262 passed (229 pre-423B + 33 new). No regressions.

```
262 passed, 5 warnings in 1.99s
```

---

## What Remains Deliberately Unwired

Per the brief's explicit "do not" list — none of the following exist after
423B:

- LP-07 does not see the 100% tenant share, or anything else, from this
  slice. No LP ever receives any span from this slice.
- No global key-terms parameter injection (423 spec §5.1).
- No LP dependency map (423 spec §5.2).
- No many-to-many span-to-LP assignment.
- No selector-panel voting (423 spec §6).
- No cited union merge (423 spec §6.2).
- No feed of spans into Stage 5. `assess_coverage`, `lease_adapter.py`, and
  `lease_extract.py` are untouched — confirmed by `git status` and by
  `TestPipelineSeam`, which asserts none of those three files' source
  references `lease_segmentation` or the sidecar filename.
- No N=10 baseline, no segmentation-recall measurement (only the one
  quarantined n=1 smoke run, explicitly disclaimed above).
- No evaluator identity change, no Stage 5 stabilization, no Priority
  Exposure, no `cam/core/` change, no `extra_provider_params`.
- No real fallback segmenter — `fallback_chain` is `[]` and `fallback_used`
  is always `False` by construction; the fields exist in metadata for a
  future slice, not because a second provider is wired up.

---

## Constraints Honored

- `git status` on `cam/` shows only new, untracked files for 423B plus one
  edit to `lease_evidence_spans.py` (Part 0 docstring only — no resolver
  logic changed; confirmed by the full 423A test suite, 19/19, still
  passing unmodified).
- No `cam/core/` file modified — `_check_generation_integrity` is imported,
  not changed.
- No result directories staged.
- No baseline, no N≥2 measurement run.
- No push.

---

## Files Changed

- `cam/adapters/lease_review/lease_evidence_spans.py` — docstring-only edit (Part 0)
- `cam/adapters/lease_review/lease_segmentation.py` — new module
- `cam/adapters/lease_review/prompts/segmentation_span_proposal.txt` — new prompt
- `cam/adapters/lease_review/schemas/segmentation_schema.json` — new schema
- `cam/adapters/lease_review/tests/test_423b_lp_blind_segmentation.py` — 33 new tests
- `build_log/423B_span_universe_smoke_sidecar.json` — n=1 smoke artifact
- `build_log/423B_lp_blind_segmentation_proposal.md` — this file
