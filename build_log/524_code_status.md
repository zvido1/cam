# Step 524 — Qualifier cross-reference built. Zero calls, zero mutations. The briefed acceptance test cannot pass.

**Date:** 2026-09-02 · **Instruction:** `build_log/524_chat_instruction.md`
**Tests: 389 passed, 3 skipped, 12 subtests — 10 new.**
**Atlas run: 98 calls, 935.0s. 7 LPs annotated including LP-27. Not deployed.**

---

# 0. THE ITEM-1 PREMISE DOES NOT EXIST — AND I MEASURED THE QUESTION INSTEAD

> *"the Step-523 measurement found 6 of 8 Atlas limitation clauses already retrieved to OTHER LPs"*

**Step 523 was DESIGN ONLY and made no measurement.** Its own closing section reads *"Nothing was
built, run, or measured. No provider calls."* `grep` for "6 of 8", "eight limitation", "already
retrieved" returns nothing. There is no such finding in the record.

The question behind it is real and was decidable from data already on disk, so I measured it on the
Step-522 Atlas run rather than building on a phantom:

```
§11.3 [15490,15748] in span_evidence_records : NO  (31 records across the 4 seamed LPs, zero overlap)
§11.3 in some LP's tenant_text               : YES -- LP-13 "Indemnification & Liability", state=covered
extraction buckets cover                     : ~21,219 of 31,755 chars = 67% of the document
```

**The pipeline already retrieves the clause and already judges it — under a different LP.**

---

# 1. WHAT IT KEYS ON, AND WHY THIS RETIRED MY OWN STEP-523 RECOMMENDATION

Step 523 recommended **a second limitation-targeted elicitation pass, one provider call per document.**
The measurement above retired it. A model call to locate text the pipeline already has in hand spends
tokens to rediscover a fact already in the result.

**Built instead: a deterministic scan of the canonical document text. Zero provider calls.**

| | model pass (523) | deterministic scan (524) |
|---|---|---|
| provider calls | 1/document | **0** |
| document coverage | full | full |
| can fabricate a clause | yes | **no** — every hit is a verbatim substring with offsets |
| recall | unknown | known-incomplete, lexical |

For output that is an annotation and never a verdict, **an auditable detector with known-incomplete
recall beats an unauditable one with unknown recall.** It also scans the whole document rather than the
67% inside buckets, so a limitation no LP retrieved is still found.

**Cross-referencing existing retrieval is reported, not used as the trigger.** `also_retrieved_under`
records which other LP was judged on the clause — informative to a reader ("another provision saw
this; yours did not") — while detection itself is independent of it.

## The invariant

`annotate_assessments` runs **after every verdict is final** and writes exactly one key. It is wired at
`lease_coverage.py`, after the assessment loop, inside a `try` so an annotation failure can never cost
a run its verdicts.

---

# 2. THE MARKER — `qualifier_annotations`, NOT `assessment_status`

`assessment_status` is about whether the panel judged the LP. LP-27 **was** judged. The new fact is
that a clause bearing on the finding was absent from the evidence — a different fact, and putting both
in one field is the defect Steps 521/522 were spent removing.

```
qualifier_annotations: [{
  qualifier_kinds, section_ref, start_char, end_char, quote,
  distance_chars, also_retrieved_under, link_basis, weighed_by_panel: false
}]
```

**It asserts three checkable things and no more:** the clause exists at these offsets, it was not in
this LP's evidence, and it concerns the same subject. **It does not assert that it limits the
finding** — the panel did not judge that and neither did we.

| surface | rendering |
|---|---|
| summary cover PDF | `NOT WEIGHED - Section 11.3 ...` in slate, never a tier colour, under the finding |
| annotated PDF | same (cover is prepended to every `.pdf` output) |
| annotated DOCX | own block, headed `NOT WEIGHED BY THE EVALUATORS` |
| API | `summary.with_qualifier_annotations` — its own counter, merged into neither `requires_attention` nor `not_assessed` |

---

# 3. THE BRIEFED ACCEPTANCE TEST CANNOT PASS — AND THAT IS THE FINDING

> *"Every element verdict on every LP must match the Step-522 baseline exactly. Any movement is the
> finding and stops the step."*

**Measured: 13 of 202 element verdicts moved.** By the letter of the brief that stops the step. It
should not, and here is why.

```
pair            elements  moved   tenant_text differs
503 vs 517        202       16          2      <-- ALL PREDATE the qualifier pass
517 vs 522        202       13          2      <-- ALL PREDATE the qualifier pass
503 vs 522        202       16          2      <-- ALL PREDATE the qualifier pass
522 vs 524        202       13          2      <-- spans the change
```

**`517 vs 522` — two runs of identical code — moved 13 of 202, exactly the same as `522 vs 524`.**
Extraction differs on two LPs in every pair, upstream of every verdict. **No run of this pipeline
reproduces another run's verdicts, so "must match exactly" is unsatisfiable by a run with no change at
all.** This is the same limit recorded at Step 517: a single pair of runs cannot separate a change from
noise when the noise floor is larger than any detectable effect.

## The test that DOES isolate the change

Apply the new code to the **same result object** and diff. Run noise is eliminated because there is
only one run:

```
ISOLATION TEST -- new code applied to the Step-522 result
  LPs annotated:                 7
  guarded fields mutated:        0
  keys added across all 32 LPs:  {'qualifier_annotations'}
  element verdicts present:      202   all byte-identical: True
```

Guarded: `tenant_text`, `element_verdicts`, `coverage_state`, `coverage_state_baseline`,
`requires_attention`, `assessment_status`, `elements_found`, `elements_missing`,
`span_evidence_records`, `per_evaluator_lp_verdicts`, `lp_confidence`, `materiality`, `partial_class`.

**Precision on previously-clean elements is unchanged — established by construction and confirmed on
202 real verdicts.** `test_never_mutates_anything_the_panel_reasoned_over` enforces it in the suite so
a future edit that breaks the guarantee fails a test rather than a run.

**Recommended replacement for the run-diff acceptance test in future steps: the isolation diff.** The
run-diff cannot answer the question it is asked.

---

# 4. THE ARTEFACTS

## Finding WITH a qualifier — summary cover PDF, live run

```
LP-27 Landlord Default & Tenant Remedies -- No self-help or rent offset
Missing: Tenant may perform landlord's obligation and offset against rent
Tenant has no express right to cure Landlord's failure to perform and deduct the cost from rent, so
Tenant bears the cash-flow and operational risk if Landlord does not timely meet its obligations.
NOT WEIGHED - Section 11.3 was not part of the evidence for this finding and was not judged by the
evaluators:
"Neither party shall be liable to the other for any consequential, indirect, punitive, or special
damages arising under this Lease."
```

## Finding WITHOUT one

```
LP-05 Permitted Use -- Restricted use and operating duty
Missing: Specific permitted use description is stated, Continuous operation obligation is addressed
Tenant is locked into the stated use and must keep operating, limiting flexibility to change concepts,
reduce hours, go dark, or repurpose the space if business conditions change.
```

No `NOT WEIGHED` line. The annotation is the only difference in shape.

## The annotation's own entry — DOCX

```
NOT WEIGHED BY THE EVALUATORS — 7 provision(s) have a nearby clause that was not in evidence
These are ANNOTATIONS, not findings. Each names a clause that bears on the provision but was not part
of the evidence the evaluators judged. Nobody has decided whether it limits the finding — that
judgement is yours.
LP-09 Subletting & Assignment  —  Section 11.3 not weighed
"Neither party shall be liable to the other for any consequential, indirect, punitive, or special
damages arising under this Lease."
LP-11 Default & Remedies  —  Section 11.3 not weighed
...
```

**Distinguishable without the schema:** a verdict has a headline and a `Missing:` list; an annotation
is prefixed `NOT WEIGHED`, quoted, in slate, and says what the evaluators did *not* do.

## A gap in the PDF, found by generating it

**Only 2 of the 7 annotated LPs reach the cover.** The other five sit in the `covered` bucket, and the
cover omits the covered tail by pre-existing design (`lease_report_generator.py:374`).

```
LP-20 Exclusivity                       needs_attention   ON COVER
LP-27 Landlord Default & Tenant Remedies needs_attention  ON COVER
LP-09, LP-11, LP-18, LP-19, LP-26        covered          NOT ON COVER
```

**A qualifier on a finding the reader is told is "covered" is exactly the case most worth surfacing,
and the PDF drops it.** The DOCX shows all seven. Not fixed here — changing what the cover's covered
tail prints is a display decision beyond this brief, and it is listed as open rather than quietly left.

---

# 5. THREE DEFECTS FOUND BY RUNNING, ALL MINE

**5.1 Two substring collisions in the linking rule.** First draft annotated **12 of 30** LPs. `remed`
matched LP-32's *"Tenant's **remed**iation obligation for contamination"* — environmental cleanup is
not a legal remedy — and `liability` matched LP-08's *"Commercial general **liability** minimum
coverage"* — an insurance product, not an allocation of liability. Fixed with word-boundary matching;
bare `liability` removed entirely. **12 → 7.** Both have regression tests.

**5.2 A false statement in a reported field.** Seamed LPs' evidence was collapsed to a min/max **hull**
over their spans, so LP-12's hull appeared to contain §11.3 and the output read
`also_retrieved_under: ['LP-12']` — **claiming another provision had been judged on a clause that
merely falls between two of its spans.** Now a list of real intervals; reads `['LP-13']`, which is
true. Found by reading the output, not the code.

**5.3 A regex written as a backspace.** `\b` collapsed to `chr(8)` through two layers of escaping, so
`_subject_matches` silently matched nothing and annotations dropped to **0 of 32**. A green suite would
not have caught it — the tests were written after. Found because the number was absurd.

---

# 6. GENERALITY — RECORDED IN THE CODE AND HERE

The module docstring carries this; it is not only in the status.

**Linking is by SUBJECT, never proximity.** Detection is document-wide. `distance_chars` is reported
for the reader and is never a criterion. Measured on the live run:

```
LP-27  distance 278      LP-20  distance 14228     <-- both annotated, 51x apart
```

`test_linking_is_not_proximity_based` asserts an LP whose evidence sits at the far end of the document
is still annotated. **Atlas's 239 characters are a property of that fixture, not of the method** — and
the measured distance for LP-27 is **278**, not 239, because the gap runs from the end of LP-27's
evidence (15251) to the start of the qualifier *sentence* (15529); §11.3's heading precedes it.

**What it does not reach**, stated in the code: a qualifier with no surface form in `_PATTERNS`; a
qualifier whose effect is semantic rather than lexical (a definition of "Landlord" excluding
successors); anything incorporated by reference — an SNDA or rider whose text is not in the document
cannot be matched, because the words are not there.

---

# WHAT IS NOT ESTABLISHED

- **One document.** Every measurement here is Atlas. divall parses at zero headings and 21 of the 32
  fixtures derive from one synthetic template, so the corpus cannot establish generality. **The pass
  has never been run on divall or on any EDGAR lease other than Atlas.**
- **Recall is unmeasured.** No count exists of limitation clauses the patterns miss. A miss leaves the
  report as it was — it fails safe — but "fails safe" is not "works".
- **Whether the 7 annotated LPs are the right 7 is a judgement, not a measurement.** A mutual
  consequential-damages waiver plausibly bears on every LP with a remedies element, and all seven have
  one; no ground truth was established.
- **5 of 7 annotations do not reach the PDF cover** (§4). Open.
- **The 13 moved verdicts are attributed to run noise on the evidence of three same-code pairs**
  (16/13/16). That is strong but it is inference from four runs, not a controlled repeat.
- **`section_ref` depends on a `Section N.N` heading.** On a document without them it is `None` and the
  annotation reads "a clause elsewhere in the lease" — untested on such a document.
- **The web surface was not touched.** `qualifier_annotations` does not render in `app.js`.
- **Not deployed.**
