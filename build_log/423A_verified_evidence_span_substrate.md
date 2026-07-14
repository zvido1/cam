# Step 423A — Verified Evidence-Span Substrate

**Date:** 2026-07-14
**Status:** COMPLETE — slice one of 423 only

---

## Deferred Items (read this first)

This step builds **only** the substrate declared in 423 spec §3–§4: a canonical
hashed source, an evidence-span schema, and a code-side resolver that turns
proposed verbatim quotes into verified/ambiguous/unverified offset spans.
Everything below is deliberately **not** built in this slice:

1. **The actual segmentation model call.** No Gemini (or any model) call
   proposes quotes. `resolve_span()` / `resolve_spans()` take quotes as plain
   Python input — the code side of Layer 1 only. Layer 1's model side ("Gemini
   reads the canonical source and proposes spans") is a separate, later
   change. Tests exercise the resolver with hand-written quotes, not a live
   extraction.
2. **Wiring into `lease_adapter.py` / Mode C pipeline.** `run_lease_coverage_only()`
   is untouched. No canonical source is built inside the live pipeline. The
   new module is standalone — see the seam tests below.
3. **Layer 2 (global parameter block, dependency map, LP-00 collision fix).**
   Not started. §5 of the spec.
4. **Layer 3 (panel-governed selection, cited union merge).** Not started. §6.
5. **Layer 4 (trace validation, structural or responsiveness).** Not started. §7.
6. **Gates A–D as pipeline-enforced checks.** Gate D (regression) is satisfied
   incidentally by this step's own test suite staying green; Gates A–C require
   Layers 2–4 and are not applicable yet.
7. **Any baseline, benchmark, or pipeline run.**

This is slice one of six in the spec's §13 implementation sequence. Slices
two through six are not authorized by this brief.

---

## Doctrine Followed

> Evidence belongs to the lease. LPs cite into it. Evidence is never consumed
> by assignment. (423 spec §2)

`resolve_span()` takes no `provision_id`, no `lp_id`, no LP taxonomy of any
kind — verified directly by `test_no_lp_taxonomy_leakage_into_span_resolution`,
which inspects the function signature. Segmentation produces no LP
assignment, by construction: there is nothing in this module capable of
producing one.

---

## Canonical Source Representation

New module: `cam/adapters/lease_review/lease_evidence_spans.py`.

```python
@dataclass(frozen=True)
class CanonicalSource:
    source_document_hash: str
    canonical_text: str
    canonical_text_hash: str
    text_length: int
    normalization_profile: str
    source_type: str
    run_id: str
```

`build_canonical_source(tenant_text, source_type=..., run_id=...)` wraps the
existing deterministic parser's output (`lease_parser.parse_document`) —
`canonical_text` is that output **verbatim**, no transformation. One address
space; flat character offsets into `canonical_text`.

`source_document_hash` and `canonical_text_hash` are identical by
construction in this slice, both `sha256(tenant_text)`. The schema keeps them
as two fields because a future parser stage (e.g. PDF layout reconstruction)
could legitimately produce a `canonical_text` that differs from the raw
parse — that split gives it a place to land without a schema change. Not
exercised here; the current corpus is EDGAR `.txt`.

`normalization_profile = "canonical_whitespace_v1"` — declared and
versioned per spec §3.1. `normalize()` collapses whitespace runs to a single
space and strips; it touches **only** whitespace layout. It is used solely
to compare a proposed quote against a candidate slice — it never alters
`canonical_text` itself, so offsets stay exact regardless of which quote
proposed them.

**No `page_ref`, no `table_ref`.** Confirmed absent from both `CanonicalSource`
and `EvidenceSpan` — the brief's explicit instruction that an unpopulated
optional field becomes a silent second address space later.

---

## Evidence Span Schema

```python
@dataclass
class EvidenceSpan:
    evidence_span_id: str
    source_document_hash: str
    canonical_text_hash: str
    start_char: Optional[int]
    end_char: Optional[int]
    span_text: str
    span_text_hash: str
    normalization_profile: str
    verification_status: str        # "verified" | "ambiguous" | "unverified"
    section_ref: Optional[str] = None
    source_anchor: Optional[str] = None
```

`start_char`/`end_char` are `None` for `ambiguous` and `unverified` spans —
there is no offset to report when resolution didn't produce exactly one
location. `__post_init__` rejects any status outside the three declared
values.

`EvidenceSpan.is_valid_invariant(canonical_source)` checks the hard
invariant from spec §3.2:

```
normalize(canonical_text[start_char:end_char]) == normalize(span_text)
```

and additionally checks `source_document_hash` equality — a span is never
treated as valid against a source it wasn't resolved from, even if the
offsets happen to be in range.

---

## Resolver Behavior

`resolve_span(canonical_source, quote, evidence_span_id, section_ref=None, source_anchor=None)`:

1. **Exact substring search** for `quote` in `canonical_text` (fast path —
   the model copied text byte-for-byte). If this finds matches, those are
   used.
2. **Whitespace-flexible fallback** if no exact match: the quote is tokenized
   on whitespace, every non-whitespace token is regex-escaped and must match
   literally, every whitespace run becomes `\s+`. This tolerates a model
   reflowing line breaks/spacing without ever tolerating a substantive text
   change — every non-whitespace character in the quote must still appear
   literally in the source.
3. **Zero matches → `unverified`.** Offsets `None`. Fail-closed.
4. **One match → `verified`.** Offsets set from the match.
5. **>1 matches → try `source_anchor`, then `section_ref`** as a disambiguator:
   a candidate location is accepted only if the anchor string appears within
   500 characters immediately preceding it. If exactly one candidate
   survives, `verified`; otherwise `ambiguous`, offsets `None` — **never**
   silently promoted to `verified`.
6. **Defence-in-depth:** even after a `verified` decision, the resolver
   re-checks `is_valid_invariant()` before returning. If it ever fails (it
   shouldn't, by construction of steps 1–5, but this is not assumed), the
   span is demoted to `unverified` rather than emitted as a falsely-verified
   span.

`resolve_spans(canonical_source, proposed_quotes)` batch-resolves a list of
`{"quote": ..., "section_ref"?: ..., "source_anchor"?: ...}` dicts, one
`EvidenceSpan` per entry, auto-assigning `EV-000001`, `EV-000002`, ... IDs
when not supplied. This is the code side of Layer 1 (§4) — the model side is
listed above under Deferred Items.

`is_usable_in_canonical_stage5(span)` — the single predicate that encodes
"only `verified` spans reach canonical Stage 5" (§4). Nothing else in the
module inlines a status-string comparison for this purpose.

`validate_span_against_source(span, canonical_source)` — hash-only
comparison. Never re-runs resolution, never mutates the span. Proven by
`test_hash_mismatch_is_never_silently_re_resolved`, which asserts the span's
offsets and hash are byte-identical before and after a failed validation
call against a different source.

---

## Verification States (three, exactly)

| State | Meaning | Canonical Stage 5 use |
|---|---|---|
| `verified` | quote matches exactly one location (directly or via anchor) | usable |
| `ambiguous` | quote matches >1 location, unresolved | **not** usable; recorded only |
| `unverified` | quote matches no location, OR hash mismatch, OR invariant check failed | **not** usable; fail-closed |

---

## Tests Executed — `test_423a_evidence_span_substrate.py` (19 tests)

```
TestUniqueQuoteVerified::test_unique_quote_resolves_verified PASSED
TestUniqueQuoteVerified::test_unique_quote_usable_in_canonical_stage5 PASSED
TestAbsentQuoteUnverified::test_absent_quote_resolves_unverified PASSED
TestAbsentQuoteUnverified::test_unverified_span_fails_closed_for_canonical_use PASSED
TestDuplicatedQuoteAmbiguous::test_ambiguous_span_never_silently_verified PASSED
TestDuplicatedQuoteAmbiguous::test_duplicate_quote_no_anchor_is_ambiguous PASSED
TestAnchorDisambiguation::test_ambiguous_anchor_still_ambiguous_if_it_matches_both PASSED
TestAnchorDisambiguation::test_source_anchor_resolves_duplicate_to_verified PASSED
TestNormalizationProfile::test_reflowed_newlines_normalize_equal PASSED
TestNormalizationProfile::test_reflowed_quote_still_resolves_verified_without_masking_substance PASSED
TestNormalizationProfile::test_substantive_difference_not_masked PASSED
TestNormalizationProfile::test_substantive_word_difference_not_masked PASSED
TestNormalizationProfile::test_whitespace_only_differences_normalize_equal PASSED
TestHashDriftInvalidation::test_hash_mismatch_is_never_silently_re_resolved PASSED
TestHashDriftInvalidation::test_span_invalid_against_different_source PASSED
TestHashDriftInvalidation::test_span_still_valid_against_its_own_source PASSED
TestSeamStandaloneAndUninvasive::test_module_not_imported_by_live_stage5_pipeline_files PASSED
TestSeamStandaloneAndUninvasive::test_no_lp_taxonomy_leakage_into_span_resolution PASSED
TestSeamStandaloneAndUninvasive::test_span_layer_is_produced_and_inspectable PASSED
19 passed in 0.33s
```

**Mapped to the brief's required test list:**

1. Unique quote → verified; slice equals span_text — `test_unique_quote_resolves_verified`
2. Absent quote → unverified; canonical use fails closed — `test_absent_quote_resolves_unverified`, `test_unverified_span_fails_closed_for_canonical_use`
3. Duplicated quote → ambiguous; no silent acceptance — `test_duplicate_quote_no_anchor_is_ambiguous`, `test_ambiguous_span_never_silently_verified`
4. Anchor disambiguation → duplicate + source_anchor → verified — `test_source_anchor_resolves_duplicate_to_verified` (plus a negative case: an anchor that doesn't uniquely disambiguate stays `ambiguous`)
5. Normalization profile behaves as declared, does not mask substantive differences — 5 tests in `TestNormalizationProfile`, including one that resolves a reflowed-whitespace quote to `verified` while the substantively-changed sibling quote (same shape, different number) resolves `unverified`
6. Hash drift → source hash mismatch invalidates spans — 3 tests in `TestHashDriftInvalidation`
7. Seam: span layer produced/inspectable; Stage 5 verdict behavior unchanged — `test_span_layer_is_produced_and_inspectable` (batch-resolves 4 realistic quotes into a structured, field-typed span universe) and `test_module_not_imported_by_live_stage5_pipeline_files` (asserts `lease_evidence_spans` is not referenced anywhere in the source of `lease_adapter.py`, `lease_extract.py`, or `lease_coverage.py` — the strongest available proof that adding this module changed zero live-pipeline behavior)
8. Full regression green — see below

**Full suite:** 229 passed (210 pre-423A + 19 new). No regressions.

```
229 passed, 5 warnings in 2.43s
```

---

## Constraints Honored

- `git status` on `cam/` shows exactly two new, untracked files
  (`lease_evidence_spans.py` and its test file) — zero diffs to any existing
  file. `lease_adapter.py`, `lease_extract.py`, `lease_coverage.py` are
  byte-identical to their pre-423A state.
- No `cam/core/` change.
- No `response_schema`, evaluator identity, Stage 5, or Priority Exposure
  code touched.
- No baseline, benchmark, or pipeline run executed.

---

## Files Changed

- `cam/adapters/lease_review/lease_evidence_spans.py` — new module (canonical
  source, evidence span schema, resolver, hash-validation)
- `cam/adapters/lease_review/tests/test_423a_evidence_span_substrate.py` — 19
  new tests
- `build_log/423A_verified_evidence_span_substrate.md` — this file
