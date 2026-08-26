# Step 486 — Batch summary closed; deploy-readiness report

**Date:** 2026-08-25 · **Instruction:** `build_log/486_chat_instruction.md`
**Part A implemented and verified by artefact. Part B is report-only — nothing changed.**
Tests **359 passed**. **Not deployed.**

---

# PART A — batch summary

## The batch requirement: which tenant, not merely that one of them

Handled on **two surfaces**, because they answer different questions:

- a **top banner** naming the affected tenants and the count — so a reader knows at a glance,
  without opening sections;
- a **per-tenant marker** at each tenant's own heading — so a section read in isolation still
  carries it.

## Batch DOCX — what a reader sees

```
Batch Lease Analysis Summary
INCOMPLETE REPORT - NOT VALID FOR LEGAL ANALYSIS - 1 of 2 report(s) affected
atlas_DEGRADED.txt -- Issue areas with no evidence: LP-12
Executive Summary
…
Per-Tenant Highlights
atlas_DEGRADED.txt
INCOMPLETE REPORT - NOT VALID FOR LEGAL ANALYSIS — Issue areas with no evidence: LP-12
```

Per-tenant headings verified individually:

```
heading atlas_DEGRADED.txt  -> next: INCOMPLETE REPORT - NOT VALID FOR LEGAL ANALYSIS — …LP-12
heading atlas_CLEAN.txt     -> next: All 0 provisions conform to the standard template…
```

**The clean tenant carries no marker.**

## Combined synopsis PDF — page one and the snapshot

```
COVERAGE ANALYSIS
August 25, 2026 | s486_batch
INCOMPLETE REPORT - NOT VALID FOR LEGAL ANALYSIS — 1 of 2 report(s) affected
atlas (DEGRADED) — Issue areas with no evidence: LP-12
Perspective: Tenant
```

and in the body:

```
CONTRACT STATUS SNAPSHOT
atlas (DEGRADED): INCOMPLETE REPORT - NOT VALID FOR LEGAL ANALYSIS — Issue areas with no evidence: LP-12
atlas (DEGRADED): 3 gaps found, 29 cross-provision findings | Coverage analysis complete
atlas (CLEAN): 3 gaps found, 36 cross-provision findings | Coverage analysis complete
```

## All-clean batch — unchanged

Batch DOCX first paragraphs: `Batch Lease Analysis Summary` → `Executive Summary`. Combined PDF:
3 pages, **0 occurrences** of `INCOMPLETE REPORT`, page one begins `COVERAGE ANALYSIS`.

## A second silent-path bug, caught by artefact verification

My first PDF edit put the marker on the per-tenant `TENANT:` heading. **`TENANT:` appears zero times
in the rendered synopsis** — that block is in a code path Mode C never reaches, because the synopsis
is coverage-first and skips deviation sections. The marker rendered nowhere, and a code read would
have called it done.

Moved to the synopsis **cover** and the **`CONTRACT STATUS SNAPSHOT`** loop, which Mode C does render,
and re-verified. This is the second such bug in two steps (Step 485: `RGBColor` into a hex-string
field, silent on degraded only). **Both were invisible to static reading and both were caught by
generating the artefact and reading it back.**

---

# PART B — deploy readiness. Report only.

## 1. Commits that would deploy

**12 unpushed; 7 touch code.** `build_log/` and `Docs/` are deploy-inert.

| commit | files | what it changes |
|---|---|---|
| `ea34f29` **476** | `lease_adapter` + 2 tests | Canonical gate returns a **degraded result** instead of raising. Adds `run_degraded`, `degraded_reason`, `extraction_completeness_failed(_lps)`, `invalid_for_legal_analysis`, `degraded_statement`; leads the summary block with `REPORT_INCOMPLETE`; marks failed LPs in coverage entries |
| `4fc4fce` **477** | `job_manager`, `app.js`, `index.html`, `style.css` | Job aggregate reads the markers; new `run_quality: "incomplete"`; results page renders a red banner above everything |
| `1fa84b9` **478** | `lease_adapter` + test | Gate degrades **only** where applicability short-circuits (`not_applicable` / `unclear`); `required`/`applicable` still abort |
| `a45c1ad` **481** | `retail_lease_knowledge.json` | LP-12 activation clues 10 → 14 (4 operative-language phrases added, none removed) |
| `b9b38f3` **484** | `lease_adapter`, `lease_coverage` + test | **LP-12 seamed**; `build_span_evidence()` hoisted so the gate runs after it; gate exempts a seamed LP **only when elicitation produced spans** |
| `7877959` **485** | `lease_display`, `lease_docx_annotator`, `lease_pdf_annotator`, `summary_generator` | Annotated DOCX banner first; annotated PDF gets a **new page one**; summary DOCX banner under the title |
| `90e6f44` **486** | `lease_display`, `summary_generator` | Batch DOCX + combined synopsis PDF banners and per-tenant markers |

`0fe12d1` (475), `8fe481e` (483), `7252a98` (482), `64f25dc` (479), `85ee627` (480) are
measurement/diagnostic records only.

## 2. Flag state that would go live

```
SPAN_EVIDENCE_ENABLED        = True
SPAN_EVIDENCE_LPS            = ['LP-07', 'LP-12', 'LP-27']
SECTION_EXPANDED_SPAN_LPS    = set()                       # expansion OFF for every LP
ENTAILMENT_TEST_LPS          = ['LP-27']
GATE_ABORT_RETURNS_DEGRADED  = True                        # gates the degrade path
DEGRADABLE_APPLICABILITY     = ['not_applicable', 'unclear']
```

## 3. What changes for a user

- **Runs that previously failed hard now complete, marked incomplete.** A completeness failure on an
  LP whose applicability short-circuits no longer ends the job with a raw traceback; it produces a
  report headed *"INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS"* naming the affected issue areas,
  on the results page, the annotated DOCX, the annotated PDF, the summary DOCX, the batch DOCX and
  the combined PDF. Job status reports `run_quality: "incomplete"`.
- **LP-12 is assessed rather than declared absent by design.** Previously `not_applicable` /
  `requires_attention: false` / *"absent by design"* on both fixtures — false on both. Now assessed:
  Atlas `review_needed` with the panel split three ways; divall `partial` with 2 elements found.
- **LP-07, LP-12 and LP-27 source evidence from verified spans**, with a deterministic
  `[Section N.N]` locator prefix, instead of extraction's exclusive buckets. Every other LP is
  unchanged.
- **Cost:** ~+1 provider call per seamed LP (Atlas 96 → 97). Elicitation runs *before* the gate, so an
  aborting run spends ~3 calls it discards.

## 4. What is NOT fixed and would ship as-is

- **LP-27 elements 6 and 7 are false positives.** *"Right to monetary damages for landlord default"*
  rests on §11.2, an **indemnity** clause; *"specific performance or injunctive relief"* rests on a
  91-character savings clause, with `"specific performance"`, `"injuncti"`, `"equitable relief"` all
  **0 hits** in the lease. Both ship reported as present. (Steps 460, 468.)
- **The §11.3 qualifier-reach problem.** The panel receives §11.2's indemnity and stops **239
  characters** before §11.3, which caps landlord liability at its interest in the building. The
  qualifier matches no LP-27 element, so it is **structurally unreachable** by element-driven search.
  Nothing in the output marks its absence. Section-boundary expansion was measured and **ruled out**
  (Step 467); co-retrieval is untested.
- **`covered_by_default_law` is presence-tier and can be reached on an unfilled placeholder.** 18 of 18
  jurisdiction-dependent elements are `TBD_BY_ATTORNEY_REVIEW`; `_normalize_verdict` tests truthiness
  only. On LP-27 element 7 this converted a would-be `disputed` into `implicitly_present` at high
  confidence. (Steps 469, 470.)
- **The citation gate tests non-nullity, not resolution.** On divall only **7.2%** of `section_ref`
  values resolve against the heading index, versus 99.0% on Atlas. Prose like *"Default statute of
  limitations law"* satisfies it. (Step 471.)
- **Non-Atlas heading structures degrade the locator.** Four real leases yield **0** headings; the
  locator emits `ARTICLE\nXI` with an embedded newline on divall, splitting the block. Cosmetic, not
  comprehension-breaking, but undetected — the string is truthy so the counter increments. (Steps 472,
  479.)
- **`requires_attention` has no "not assessed" state.** A short-circuited LP and an LP with nothing to
  report are indistinguishable. Step 481 Part B recommended a separate `assessment_status` field;
  **not implemented.**
- **The LP-12 gate abort still costs whole runs when elicitation falls back.** divall attempt 1 aborted
  on LP-07/LP-16/LP-17 after spending elicitation calls.
- **`main.py`, `index.html`, `lease_display` as a presenter** were deliberately skipped (Step 485
  triage) — covered indirectly, not directly.

## 5. What I would want measured before shipping, and has not been

1. **A deployed run that actually completes.** Step 475 attempted four and all aborted, so **no code
   from 476–486 has executed against a real request.** Every measurement here is local.
2. **The Atlas abort rate under the current configuration.** Steps 482/484 each completed on one
   attempt. The pre-seam prediction was ~72%; the post-seam expectation is near zero for LP-12, but
   **one attempt is not a rate.**
3. **Whether the banner renders in a real browser.** Verified by executing `renderIncompleteBanner`
   against a stubbed DOM, never in a live page.
4. **A degraded run end-to-end through the deployed app**, confirming `run_quality: "incomplete"`
   reaches the polled status and the banner appears.
5. **Whether any caller switches on the old three `run_quality` values** and breaks on `"incomplete"`.
   Not audited.
6. **The DOCX/PDF banners on real customer documents.** Verified on `T-04_subtle.docx` / `.pdf` only.
7. **Whether the PDF's extra page breaks a downstream consumer** assuming page counts match the source.

**My reading:** items 1 and 2 are the ones I would not ship without. The rest are known and bounded;
those two mean the deployed behaviour of this entire arc is unobserved.
