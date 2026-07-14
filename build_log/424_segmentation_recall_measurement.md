# Step 424 Part 2 — Segmentation Recall Measurement

**Date:** 2026-07-14
**Status:** COMPLETE — measurement only, no code changes

---

## What This Measures, and What It Does Not

**It measures whether element-guided elicitation (423C) reliably surfaces known-present material on ONE document (the real Atreca lease) across 5 repeated runs, using the exact offset-based "verified or it didn't happen" criterion the substrate enforces.**

**It does not measure recall on unseen documents. It does not validate the architecture. It is not a fix — no prompt, schema, or resolver change was made, regardless of what the data showed.**

---

## Hypothesis (stated before the data, per protocol)

> Element-guided elicitation produces a materially more complete span universe than the LP-blind approach, but recall is not 100% and varies across runs on the same input.

**Verdict on the hypothesis, stated plainly:** partially supported, with one important correction discovered mid-analysis (see "The exclusions-list false positive" below). Ten of twelve predefined targets show real, substantive-clause recall at or near 5/5 when measured against their true operative boundaries. Two targets that read as "0/5" under the strict locator methodology turn out to be measurement-design artifacts, not elicitation failures. One target — the Operating Expense exclusions list itself — is a genuine, reproducible **0/5 true failure**, masked by a locator that coincidentally landed inside an adjacent, different span. Offset drift is real and observed on two targets that otherwise hit 5/5.

---

## Method

- **N = 5 runs**, same canonical source (`atreca_eastjamie_southsf_lease.txt`, `source_document_hash = e049ee63a4e2f475c133b65ceb7a454b4570e59ec288a39b37129740b200d04d`), same prompt (`element_elicitation.txt`), same declared config (temperature=0.0, max_output_tokens=16000, provider=google, model=gemini-3.1-pro-preview).
- **All 32 LPs** with `expected_elements_305` (not the 2-LP subset from the 423C smoke test) — one elicitation call per LP per run, 160 calls total.
- Calls within a run were parallelized (4-way thread pool) as a driver-script execution-speed decision only — no module code was changed for this. Runs themselves are sequential.
- **Predefined target set**, declared before any run (12 targets, table below) — every target verified present in the source by direct read before the measurement started. There is no Controllable Expenses Cap in the target set, because there is no Controllable Expenses Cap in the lease (per the 2026-07-14 correction, Part 1 of this step).
- **A target counts as HIT only if a verified span's `(start_char, end_char)` fully contains the target's located offset range.** Offsets, or it didn't happen — no "the model mentioned it" and no "a nearby span exists" credit.

---

## Config-Integrity Assertion (Step 416-class check)

```
total calls: 160
distinct prompt_hashes:  {'bbb1e99d0963887d'}
distinct config_hashes:  {'7c2ac3de05b6e9ba'}
canonical flags seen:    {True}
fallback_used flags seen: {False}
CONSISTENT: True
```

**PASS.** Every one of the 160 calls transmitted the identical prompt and declared config; `canonical=True` and `fallback_used=False` on every call, with zero LP errors (zero `ElicitationIntegrityError`s) across all 160 calls. The measurement is not void.

---

## Per-Run Stats

| Run | Raw quotes | Deduped spans | Verified | Ambiguous | Unverified | Dedup ratio | Elapsed |
|---|---|---|---|---|---|---|---|
| 1 | 266 | 214 | 182 | 0 | 32 | 1.243 | 231.1s |
| 2 | 281 | 232 | 199 | 0 | 33 | 1.211 | 228.9s |
| 3 | 264 | 213 | 184 | 0 | 29 | 1.239 | 225.1s |
| 4 | 275 | 231 | 196 | 0 | 35 | 1.190 | 216.4s |
| 5 | 282 | 231 | 194 | 0 | 37 | 1.221 | 213.7s |

**Zero `ambiguous` spans in any run**, across ~1,900 total resolved quotes. Worth recording plainly: this LP-batched elicitation path (unlike the 423C smoke path) passes no `section_ref`/`source_anchor` hints into resolution, so any two elements quoting the exact same duplicated passage with no disambiguator would resolve `ambiguous`. That this never happened across 5 runs × 32 LPs suggests the model rarely re-quotes an identically-worded passage verbatim for two different elements when the passage is itself duplicated elsewhere in the document — a property of this document, not a guarantee for others.

---

## Span-Count Variance — Is the Universe Stable?

- **Raw span count:** 264–282 (range 18, ~6.8% of the mean)
- **Deduped span count:** 213–232 (range 19, ~8.6% of the mean)
- **Verified span count:** 182–199 (range 17, ~9.1% of the mean)

**Not perfectly stable, but not wildly variable either.** A ~17-span (9%) swing in verified count across 5 runs on identical input, identical prompt, identical config, temperature=0.0 confirms the elicitation call itself is not perfectly deterministic — consistent with 421C's finding that Gemini at temperature=0 is not byte-identical across runs once output is long enough. This is a real property to carry into any future design that assumes a fixed span universe.

---

## Per-Target Hit Rate (the headline)

| Target | Hit rate | Note |
|---|---|---|
| `Tenant's Share of Operating Expenses of Building: 100%` | **5/5** | Clean. Stable offsets `(1944, 1998)` every run. |
| `Building's Share of Project: 45.79%` | **4/5** | Genuine single-run miss (run 1) — see below. |
| `Rent Adjustment Percentage: 3%` | **5/5** | Clean. Stable offsets `(2099, 2129)` every run. |
| `Base Rent: $3.75 per rentable square foot` | **5/5** | Clean. Stable offsets `(1697, 1817)` every run. |
| Operating Expense exclusions list, items (a)–(u) | **0/5 (true)** — see correction below | Automated locator falsely reported 5/5; corrected. **Recall gap, named.** |
| Annual Statement / reconciliation | **5/5** | Hit every run, but offsets **unstable** — see below. |
| Independent Review (audit rights) | **5/5** | Clean. Stable offsets `(22922, 23895)` every run. |
| 95% occupancy gross-up | **0/5 (by strict locator)** — see note below | Locator-anchor artifact, not a true miss. |
| Condition Precedent (prior tenant vacates) | **2/5** | Genuine boundary drift. **Recall gap, named.** |
| Landlord's Work access rights | **0/5 (by strict locator)** — see note below | Locator-anchor artifact, not a true miss. Also: never elicited by its "designated" LP-12 in any run. |
| 120-day delivery termination right | **5/5** | Clean. Stable offsets `(5855, 6061)` every run. |
| Service-interruption rent abatement | **5/5** | Hit every run, but offsets **unstable** — see below. |

### The exclusions-list false positive (the most important finding in this report)

The automated locator (anchor phrase `"excluding only:"`) reported **5/5**, at stable offsets `(15269, 17003)` every run. Manual inspection of the matched span's actual text shows this is wrong: the span is the **Operating Expenses inclusions definition** (`"The term 'Operating Expenses' means all costs and expenses..."`), elicited by `LP-07.included_expense_categories`, which merely **ends** with the transition phrase `"excluding only:"` at its final offset. The span does **not** contain any of the actual exclusion items (a)–(u) that follow it in the source.

The element actually meant to elicit the exclusions list, `LP-07.excluded_expense_categories`, produced a quote in **every single run** that failed to verify — the same page-number-artifact failure documented below (the real source text reads `"...renovation;\n4\n(b) capital expenditures..."`, with a stray page-number line breaking the quote). **The true hit rate for this target is 0/5, not 5/5.** The mechanical locator check produced a false positive by coincidentally landing inside a different, adjacent span that happens to contain the same three words.

This is recorded as the clearest illustration in this report of why "offsets, or it didn't happen" has to be checked against the actual matched text, not just offset arithmetic — the same discipline CLAUDE.md Rule 6 now requires of prose claims about documents applies equally to claims a script makes about its own analysis.

### Locator-anchor artifacts (95% occupancy gross-up; Landlord's Work access rights)

Both targets show **0/5 by the strict locator**, but the underlying substantive clause was elicited and verified in **every run**, at stable offsets, just starting later in the source than the specific literal anchor phrase this measurement searched for:

- **95% occupancy gross-up:** locator anchor `"95% occupied"` (first occurrence) sits at `[25332, 25344)`, inside the conditional clause `"if the Building is not at least 95% occupied on average during any year of\n6\nthe Term..."` — note the embedded page-number artifact (`\n6\n`) immediately after. The verified span, stable at `(25530, 26035)` in all 5 runs (elicited by `LP-07.proportionate_share_calculation`), starts **after** that page-number break, at the computation sentence (`"...Tenant's Share of Operating Expenses for such year shall be computed as though the Building had been 95% occupied..."`). The concept was reliably found; the specific first-occurrence anchor text was not inside the boundary the model chose.
- **Landlord's Work access rights:** locator anchor `"Landlord's Work"` (2nd occurrence overall — the 1st is inside a pre-existing metadata comment block at the top of the source file, not lease text) sits at `[7155, 7170)`, inside the sentence `"...Landlord may require access to portions of the Premises in order to complete Landlord's Work."`. The verified span, stable at `(7172, 7351)` in **every run**, starts one sentence later, at `"Landlord and its contractors and agents shall have the right to enter the Premises to perform Landlord's Work..."` — and notably is elicited by **`LP-10.landlord_contribution`** and **`LP-29.permitted_purposes`**, never by `LP-12` (the LP the brief's target table names as "the boundary-drift victim" for this clause). LP-12 never gets elicitation credit for this passage in any of the 5 runs; two *other* LPs reliably do. This is a genuine, notable cross-LP attribution finding — the content is found, non-exclusively, but not by the LP a human would expect.

Neither is corrected to a "hit" in the headline table above — the strict methodology stands as measured — but both are flagged so the 0/5 is not misread as "the model never found this clause."

### Genuine recall gaps

- **Condition Precedent (prior tenant vacates) — 2/5.** The surrounding substantive clause (the Termination Agreement / Condition Precedent operative language, offsets `~10653–10909`) was verified in **all 5 runs**. What varies is whether the *introductory* sentence containing the literal words "condition precedent" (offsets `10108–10652`) is included in the same span. Runs 3 and 4 captured it — via `LP-03.commencement_date`, not `LP-12` — runs 1, 2, and 5 did not. This is a direct, measured instance of the boundary-drift phenomenon 421C named for this exact passage, now with concrete offsets: **the same clause, the same run count, and the boundary between "captured" and "not captured" moves by exactly one sentence, attributed to a different LP than expected in the runs where it's captured at all.**
- **Operating Expense exclusions list (a)–(u) — 0/5 true.** See above. Reproducible across all 5 runs: the same quote attempt, the same page-number-artifact failure, every time.

### Offset stability on nominally "5/5" targets

Two targets hit 5/5 but did **not** resolve to the same offsets every run:

- **Annual Statement / reconciliation:** run 1 → `(21436, 21823)`; runs 2–5 → `(21436, 22500)`. Same start, different end — run 1's elicited quote was shorter, ending mid-mechanism; runs 2–5 captured additional text extending into the reconciliation timeline.
- **Service-interruption rent abatement:** run 1 → `(38315, 39688)`; runs 2–5 → `(38374, 39688)`. Same end, different start — run 1's quote began 59 characters earlier than runs 2–5.

**Conclusion on offset stability: hit rate alone understates instability.** Two of the ten targets with any hits at all show boundary drift even where every run found the clause.

---

## Unverified Spans — Failure Reasons (166 total across 5 runs)

Every unverified span carries the same code-level reason string
(`"quote not found in canonical source (exact or whitespace-flexible match)"`) — that is the resolver's actual, correct behavior (423A, unchanged). What differs is *why* the quote didn't match. A post-hoc diff of each unverified quote against the raw source (not a code change — pure analysis) categorizes them:

| Category | Count | Mechanism |
|---|---|---|
| **Page-number artifact** | 52 | The raw parsed source embeds bare page-number lines (`"\nN\n"`, N=1–3 digits) mid-sentence. A quote spanning across one fails the literal non-whitespace-character match — correctly, per the Part 0 invariant that a digit is never treated as whitespace. |
| **Space-before-punctuation artifact** | 33 | The source contains a spurious extra space before certain punctuation (e.g. `"Section 22 , Tenant"` instead of `"Section 22, Tenant"`) — an apparent DOCX/PDF-extraction artifact. The quote, punctuated normally, doesn't match. |
| **Ellipsis elision (model-caused)** | 48 | The model inserted a literal `"..."` or `"[...]"` inside the quote to skip over intervening text, instead of quoting the passage in full — a direct violation of the prompt's "quote exact source text... do not summarize instead of quoting" instruction. An elided quote cannot resolve because the omitted text is not whitespace. |
| **Quote-mark internal spacing artifact** | 7 | The source formats quoted defined terms with an internal space (`(a " Control Permitted Assignment ")` instead of `(a "Control Permitted Assignment")`). |
| **Residual / not fully attributed** | 26 | Concentrated almost entirely in `LP-09` (assignment/subletting) and 3 recurring `LP-19` (utilities/essential services) quotes, reproducible across all 5 runs. Spot-diffed examples show the same family of source-side spacing artifacts (confirmed directly for one: `(an " Assignment Termination ")` vs the model's `(an "Assignment Termination")`) that a cruder stripping pass in this analysis failed to fully normalize — not a new failure mode, just incomplete categorization tooling. Recorded honestly as residual rather than force-fit into a bucket. |

**Three of these four confirmed categories (52 + 33 + 7 = 92 of 166, 55%) are properties of the canonical source text itself** — the deterministic parser's output contains typographic artifacts (embedded page-number lines, spurious spacing around punctuation and quoted terms) that break literal verbatim matching even for a quote the model copied faithfully in every other respect. **This is upstream of elicitation and upstream of the resolver** — it is a property of `lease_parser.parse_document()`'s output for this document, not a defect introduced in 423A, 423B, or 423C.

**One category (48 of 166, 29%) is a model behavior** — the model electing to elide text with `"..."` rather than quote in full, contrary to explicit prompt instruction — that a future prompt revision could target, but this step makes no such change.

---

## What Remains Deliberately Unchanged

Per Part 2's explicit constraint, and honored throughout: **no prompt change, no schema change, no resolver change, no pipeline wiring, no `cam/core/` change** — regardless of the findings above. The malformed-target-label artifact identified during analysis (the model occasionally echoing back `"Target N: <full element_label>"` instead of the bare `"Target N"` the schema requests — 29 raw occurrences before dedup, 0 remaining as a distinct category once merged into other buckets by offset) is recorded here as an observation for a future, separately authorized step. It was not fixed.

---

## Files Changed

- `build_log/424_chat_instruction.md` — the Part 0 brief, written verbatim before any work began (committed in Part 1)
- `build_log/424_segmentation_recall_measurement.md` — this file

No source files were modified for Part 2. The measurement checkpoint (raw per-run JSON, ~4MB) and analysis scripts live in the session scratchpad, not the repository — the 12-target hit-rate table, per-run stats, and categorized failure reasons above are the complete, audit-sufficient record of what was measured.
