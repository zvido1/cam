# Step 425 — Canonical Source Normalization v2

**Date:** 2026-07-14
**Status:** COMPLETE

---

## The Artifact Class

424 measured that 55% of unverified elicited spans (92 of 166) traced to typographic
artifacts in `lease_parser.parse_document()`'s raw output, not to model error or
resolver error. The worst instance: the Operating Expense exclusions list, items
(a)–(u) — LP-07's single most material tenant protection — was **0/5** across
all five 424 runs. Confirmed directly against the source
(`atreca_eastjamie_southsf_lease.txt`):

```
...renovation;
4
(b) capital expenditures...
```

The `4` is a page number from the underlying SEC filing, injected inline
mid-sentence by whatever pagination process produced this `.txt` export. It
sits alone on its own line, between "renovation;" and "(b) capital
expenditures".

**Why the resolver was right to reject.** The model quoted this passage
faithfully every run — no elision, no paraphrase. The 423A hard invariant
(`normalize(canonical_text[start:end]) == normalize(span_text)`) correctly
refused to verify a quote spanning the page break, because the `canonical_whitespace_v1`
profile treats a digit exactly like every other non-whitespace character: it
must match literally, or the quote does not resolve. A `4` is not
whitespace. The resolver did its job. **The source was wrong** — that digit
is not lease content, it's filing furniture that survived the parser.

---

## The Governing Principle

> Strip what is not in the document. Never rewrite what is.

This line was held throughout implementation:

- **Page-number lines are not lease content.** They are artifacts of how a
  structured SEC HTML filing got flattened into a character stream and
  paginated for print. Removing them makes `canonical_text` **more**
  faithful to the lease, not less. → **Stripped from the text.**
- **Ugly spacing IS lease content.** `" Assignment Termination "`,
  `"Section 22 , Tenant"` — those exact characters are genuinely in the
  document the parser produced from the filing. Rewriting them to match
  what a model happened to quote would be editing the evidence to fit the
  claim — precisely what this substrate exists to prevent. → **Left alone
  in the text. Tolerated only in the declared matching profile.**

No line of code in this step edits `canonical_text` for any reason other
than removing a line that is provably not lease content (a bare digit
line). Every other tolerance added lives in the matching/normalization
functions, which operate on temporary comparison strings and never touch
the addressable text.

---

## What Was Built

All changes are in `cam/adapters/lease_review/lease_evidence_spans.py` (the
423A substrate module — extended, not replaced).

### 1. Page-number line stripping (`canonical_v2`)

```python
_PAGE_NUMBER_LINE_RE = re.compile(r"^[ \t]*\d+[ \t]*\n", re.MULTILINE)

def _strip_page_number_lines(text: str) -> Tuple[str, int]:
    return _PAGE_NUMBER_LINE_RE.subn("", text)
```

A line is removed **only if**, after trimming leading/trailing spaces or
tabs, its entire content is one or more digits and nothing else. The
regex anchors on `^...\n` (MULTILINE), so the digit run must reach the
line's own terminating newline with only space/tab padding in between —
`Section 4`, `4. Operating Expenses`, `(4)`, `4%`, `$4`, `4 days`, and
`Page 4 of 20` all keep the digit adjacent to a non-whitespace,
non-digit character on the same line and are therefore structurally
excluded from matching this pattern, not merely excluded by a secondary
check. As required: a false strip is worse than a missed one, so the rule
stays this narrow.

`CanonicalSource` gained three new fields, all diagnostic/provenance only:

- `raw_source_text` — the parser's completely untouched output, always
  preserved regardless of profile.
- `raw_source_text_hash` — `sha256(raw_source_text)`.
- `page_number_lines_stripped` — count of lines removed (0 for v1, always).

`build_canonical_source(..., normalization_profile=NORMALIZATION_PROFILE_V2)`
now strips page-number lines from `canonical_text` before hashing it;
`normalization_profile=NORMALIZATION_PROFILE_V1` (the default — unchanged)
does not.

### 2. Matching profile `canonical_whitespace_v2` — text untouched

Two new declared tolerances, implemented **only** in the pattern-builder
(`_build_flexible_pattern`) used by the resolver's whitespace-flexible
fallback search, and in `_normalize_canonical_whitespace_v2` (used for the
hard-invariant equality check — both must agree, or a v2 match would fail
its own invariant and be demoted to `unverified` by the existing
defence-in-depth check):

- **Whitespace-run equivalence** (unchanged from v1).
- **Space adjacent to punctuation** (`,`, `.`, `;`, `:`, `)`) — `"word ;"`
  and `"word;"` normalize/match identically.
- **Padding immediately inside quote marks** (`"`) — `'" Term "'` and
  `'"Term"'` normalize/match identically. Since the source uses the same
  `"` glyph for both opening and closing, tolerance is applied
  symmetrically on both sides of every `"` occurrence.

Mechanically, the v2 pattern builder inserts an **optional** `\s*` (never
required) immediately before every tolerated punctuation/quote character
and immediately after every quote character, while every other character
— every letter, every digit, every punctuation mark not in the tolerated
set — is still escaped and required to match literally. `\s*` matching
zero characters is exactly v1's behavior when there's no whitespace to
tolerate; matching one-or-more characters is the new tolerance. Neither
touches `canonical_text`.

### 3. Provenance

`normalization_profile`, `raw_source_text_hash`, `canonical_text_hash`,
and `page_number_lines_stripped` are all recorded on `CanonicalSource` as
plain fields — read, not asserted as validation. `EvidenceSpan.source_document_hash`
continues to be keyed to `canonical_text_hash` (unchanged design from
423A) — this is what makes hash-drift protection work correctly across
profiles: a v1 `CanonicalSource` and a v2 `CanonicalSource` built from the
identical `raw_source_text` have **different** `canonical_text_hash`
values (v2's is missing the stripped lines), so a span resolved against
one is provably invalid against the other. `raw_source_text_hash` is
identical across profiles (same underlying document) and is diagnostic
only — it never participates in the validity check.

---

## Why the Split Is Where It Is

The temptation, seeing `"Section 22 , Tenant"`, is to "clean up" the
source. That would be the exact same failure this project spent 421C–424
diagnosing at a different layer: editing an artifact to make a claim about
it match, rather than verifying the claim against the artifact as it
actually is. A page-number line is different in kind: it is not an
untidy-but-real feature of the document, it is provably not part of the
document at all — it's a byproduct of how the filing was paginated for a
different medium (print) than the one this system reads (a character
stream). Removing it is closing a parser gap, not editing evidence.
Everything else observed in 424 — the spacing quirks — are real characters
genuinely present in what the parser handed back from the real filing.
Those get tolerance, not deletion.

---

## Tests Executed — `test_425_canonical_source_v2.py` (22 tests)

```
TestPageNumberStripResolvesExclusionsList::test_stripped_text_has_page_number_removed PASSED
TestPageNumberStripResolvesExclusionsList::test_unverified_under_v1 PASSED
TestPageNumberStripResolvesExclusionsList::test_verified_under_v2 PASSED
TestNarrowStripRule::test_all_survivors_kept_verbatim PASSED
TestNarrowStripRule::test_bare_digit_line_is_stripped PASSED
TestNarrowStripRule::test_mixed_survivors_and_strips_in_one_document PASSED
TestNarrowStripRule::test_multiple_bare_digit_lines_all_stripped PASSED
TestNarrowStripRule::test_whitespace_padded_digit_line_is_stripped PASSED
TestCanonicalTextByteIdenticalExceptPageLines::test_punctuation_and_quote_spacing_never_rewritten_in_text PASSED
TestCanonicalTextByteIdenticalExceptPageLines::test_v2_canonical_text_equals_raw_minus_page_lines_only PASSED
TestV2MatchingTolerance::test_quote_mark_padding_tolerated PASSED
TestV2MatchingTolerance::test_quote_mark_padding_unverified_under_v1 PASSED
TestV2MatchingTolerance::test_space_before_punctuation_tolerated PASSED
TestV2MatchingTolerance::test_space_before_punctuation_unverified_under_v1 PASSED
TestSubstantiveDifferenceNeverTolerated::test_punctuation_tolerance_does_not_bridge_a_real_gap PASSED
TestSubstantiveDifferenceNeverTolerated::test_v2_normalize_does_not_mask_digit_change PASSED
TestSubstantiveDifferenceNeverTolerated::test_v2_normalize_does_not_mask_word_change PASSED
TestSubstantiveDifferenceNeverTolerated::test_v2_still_refuses_changed_digit PASSED
TestHashDriftAcrossProfiles::test_span_resolved_against_v1_invalid_against_v2 PASSED
TestHashDriftAcrossProfiles::test_v1_and_v2_hashes_differ_when_page_lines_present PASSED
TestHashDriftAcrossProfiles::test_v1_hashes_equal_raw_hash_when_no_page_lines PASSED
TestV1BackwardCompatibility::test_default_profile_is_still_v1 PASSED
22 passed in 0.05s
```

**Mapped to the brief's required test list:**

1. Page-number line stripped; exclusions-list quote now resolves — built
   from the real `renovation;\n4\n(b)` text (`TestPageNumberStripResolvesExclusionsList`,
   3 tests: `unverified_under_v1`, `verified_under_v2`, and the text
   actually losing the page line).
2. `Section 4`, `4%`, `$4`, `(4)`, `4 days` (plus `4. Operating Expenses`
   and `Page 4 of 20`) all survive — `TestNarrowStripRule`, verified both
   individually and mixed together in one document with real strips
   interspersed.
3. Space-before-punctuation and quote-padding tolerated in matching, with
   canonical text unchanged — `TestCanonicalTextByteIdenticalExceptPageLines`
   (asserts `canonical_text` equals raw text with *only* page-number lines
   removed) and `TestV2MatchingTolerance` (4 tests: both tolerances proven
   to work under v2 and proven to still fail under v1 — the profile
   opt-in is real, not a global behavior change).
4. `45.79%` vs `45.80%` → still `UNVERIFIED`, non-negotiable —
   `TestSubstantiveDifferenceNeverTolerated` (4 tests, including one that
   confirms the punctuation tolerance can't be exploited to bridge an
   actual content gap: `"3%, subject to annual review"` vs `"3%, subject
   to biennial review"` stays `UNVERIFIED`).
5. Hash drift: a span resolved against v1 canonical is invalid against v2
   — `TestHashDriftAcrossProfiles` (3 tests, including confirmation that
   `raw_source_text_hash` stays identical across profiles — only
   `canonical_text_hash`/`source_document_hash` diverge, which is what
   span validity is keyed to).
6. Full regression green — see below. Plus one added backward-compatibility
   test confirming v1's default behavior is provably unchanged
   (`canonical_text_hash == raw_source_text_hash` when there's nothing to
   strip).

**Full suite:** 312 passed (290 pre-425 + 22 new). No regressions.

```
312 passed, 5 warnings in 3.03s
```

---

## Smoke Run (n=1, NOT Validation)

> This is an n=1 plumbing smoke test. It is not a measurement of recall,
> not evidence the architecture works, and no count from it may be cited
> as validation.

One elicitation call, LP-07 only (the LP whose `excluded_expense_categories`
element was the 0/5 case in 424), against the real Atreca lease, under
`canonical_whitespace_v2`.

**Plumbing executed.** `canonical_v2` stripped **38** page-number lines
from the 160,244-character document (`raw_source_text_hash=e049ee63a4e2f475...`,
`canonical_text_hash=7118cc6ddf65bd7b...` — the two now differ, as
designed). LP-07 elicitation returned 7 raw quotes, deduplicated to 7
spans, **all 7 verified, 0 unverified** — including
`LP-07.excluded_expense_categories`'s exclusions-list quote, which was the
0/5 failure named in 424.

**Observation (not a hit rate, not a checklist):** the exclusions-list
content — `"(a) the original construction costs of the Project and
renovation..."` — resolved `verified` under `canonical_v2` in this run.
This is the same quote text the model produced consistently across all
five 424 runs under v1; nothing about the model's output changed. What
changed is that the page-number line it used to cross no longer exists in
`canonical_text`.

No claim is made about recall, about the other 32 LPs, about run-to-run
stability, or about the architecture more broadly from this single call.

---

## The Canonical-Source Layer Is a Known-Weak Seam

Today's parser flattens a structured SEC HTML filing into a character
stream, discarding markup in which page breaks and footers were
unambiguous — and we now infer them back from character patterns. The
page-number strip is a narrow, testable rule that removes content provably
not in the lease. **It is not a general solution to document parsing.** A
structure-aware parser (reading the HTML as HTML, where a page-break
element is a page-break element and never a bare digit that merely
resembles lease content) is a real future step, not a hypothetical one.
This is recorded now so it is not rediscovered as a surprise on the next
document — a filing with page numbers formatted differently, or with
footers containing digits in a different pattern, will not be caught by
this rule, and that is a known, accepted scope limit rather than an
oversight.

---

## What This Does Not Do

**This does not make LP-07 see the 100%.** The parameter block, the
dependency map, and the selector panel remain unbuilt. This step closes
one class of false-negative at the resolver layer — it does not attach
any span to any LP, does not decide relevance, and does not feed anything
into Stage 5.

---

## What Remains Deliberately Unchanged / Unwired

- The resolver's core rule is untouched: a digit is never treated as
  whitespace, under either profile.
- No fuzzy matching, no edit distance, no paraphrase tolerance was added
  anywhere.
- No parameter block, dependency map, selector panel, or many-to-many
  assignment was built.
- No spans were fed into Stage 5.
- No baseline or recall measurement was run — only the one quarantined
  n=1 smoke call above.
- `cam/core/`, evaluator identities, Stage 5 stabilization, and Priority
  Exposure were not touched.
- `lease_segmentation.py` (423B) and `lease_element_elicitation.py` (423C)
  are unmodified — they already accept a `CanonicalSource` as a parameter,
  so v2 support required zero changes to either; a caller simply passes a
  v2-built `CanonicalSource` in.
- The 48 ellipsis-elision failures from 424 (the model eliding text with
  `"..."`) are untouched by this step — a parser fix cannot address a
  model behavior.

---

## Files Changed

- `cam/adapters/lease_review/lease_evidence_spans.py` — page-number
  stripping (`_strip_page_number_lines`), `NORMALIZATION_PROFILE_V2` +
  `_normalize_canonical_whitespace_v2`, profile-aware
  `_find_normalized_matches`/`_build_flexible_pattern`, `CanonicalSource`
  gained `raw_source_text`/`raw_source_text_hash`/`page_number_lines_stripped`
- `cam/adapters/lease_review/tests/test_425_canonical_source_v2.py` — 22
  new tests
- `build_log/425_chat_instruction.md` — the Part 0 brief, written verbatim
  before any work began
- `build_log/425_canonical_source_normalization_v2.md` — this file
