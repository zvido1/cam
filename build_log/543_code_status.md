# Step 543 — Dropped anchors are recorded. The annotators no longer return a bare path.

**Date:** 2026-09-03 · **Instruction:** `build_log/543_chat_instruction.md`
**Tests: 406 passed, 3 skipped, 12 subtests. No verdict changed. Not deployed.**

---

# 1. THE RECORD

## What was there

```python
        if para is None:
            coverage_not_found += 1
            print(f"[docx_annotator] Could not anchor coverage gap for {pid}", flush=True)
            continue
```

…and, at the end, `return output_path` — **the same string whether it placed 23 of 27 callouts or 0 of
27.** That is the Step-511 shape exactly: a bare success for something partially done.

## What it returns now

```json
{
 "output_path": "...",
 "deviations_annotated": 0,
 "coverage_callouts_added": 23,
 "coverage_admitted": 27,
 "anchor_drop_count": 4,
 "skipped_absent_provisions": ["LP-14", "LP-28", "LP-31"],
 "complete": false
}
```

**`complete: false` is the load-bearing field.** A caller that reads nothing else can still tell the
artefact is partial.

**`skipped_absent_provisions` is deliberately a separate field from `anchor_drops`.** An absent
provision has no paragraph to annotate — that is expected and correct. An anchor *failure* is not.
**Summing them would conflate a design property with a defect**, so they never share a counter.

## Both returned and written onto `results`

```python
    if isinstance(results, dict):
        results.setdefault("annotation_reports", {})["docx"] = _report
    return _report
```

**Both, because the two call paths differ.** `generate_outputs` persists `results` afterwards; the
download endpoint in `main.py` loads it from disk and discards it, so only the return value reaches
that caller. Writing to one place would have covered one path.

**Widening the return is zero-risk: no caller reads it.** All five sites —
`lease_report_generator:701/714/734` and `main.py:1367/1383` — call the annotator as a statement and
compute the path separately. Verified before changing the signature.

Applied identically to `lease_pdf_annotator.py`.

---

# 2. DOES A READER NEED TO KNOW? — YES, CONDITIONALLY, AND ONLY WHERE IT IS TRUE

**The argument against surfacing is real:** nothing is lost. Every dropped finding is in the summary,
and Step 542 confirmed all four appear in the cover PDF. A reader has no action to take about an
anchoring failure, and explaining an internal mechanism is noise.

**What decides it is the workflow, not the information.** A lawyer working through a marked-up lease
clause by clause is relying on the margin. **If a finding has no margin note, they do not learn it
exists at that clause — they learn it only if they separately read the summary.** The two halves of the
report then disagree in count with nothing saying so, which is the shape this whole arc has been
removing.

**So: surface it, minimally, and only when it happened.**

```
Note: 4 finding(s) below could not be placed beside a clause in the marked-up document
and appear in this summary only: LP-21, LP-22, LP-29, LP-32.
```

**Naming the LPs is what makes it actionable** — the reader can find those four in the list below
rather than being told an abstract count.

**Verified silent when it did not happen:**
```
no annotation_reports -> note present: False
zero drops            -> note present: False
```

## Where it can go, and one place it cannot

**The PDF cover carries it**, because `generate_outputs` builds the cover at `:753` *after* annotating
at `:714` — the report exists by then.

**The DOCX cannot carry it without restructuring.** `_insert_summary_section` runs at `:676` and the
coverage loop at `:736`, so the summary is written before any drop is known. **I did not restructure
that ordering in a step scoped as small**, and the DOCX therefore records the drops on the result but
does not tell its own reader. **That is a real remaining gap and I am not calling it closed.**

---

# 3. THE FOUR DROPPED LPs, AS RECORDED

```
LP-21  Guaranty of Lease      state=partial        reason=no_anchor_found  anchors available: ['issue_area_name', 'issue_area_id']
LP-22  SNDA                   state=review_needed  reason=no_anchor_found  anchors available: ['issue_area_name', 'issue_area_id']
LP-29  Right of Entry         state=review_needed  reason=no_anchor_found  anchors available: ['issue_area_name', 'issue_area_id']
LP-32  Hazardous Materials    state=partial        reason=no_anchor_found  anchors available: ['issue_area_name', 'issue_area_id']
```

Accounting on the Step-537 result:
```
coverage_admitted 27  =  coverage_callouts_added 23  +  anchor_drop_count 4
skipped_absent_provisions 3 (LP-14, LP-28, LP-31), counted separately
30 admitted by bucket - 3 absent = 27 attempted
```

## What the record immediately shows, and it is diagnostic

**All four had only `issue_area_name` and `issue_area_id` available — `tenant_text` and `section_ref`
were both empty.** The anchor chain is `tenant_text → section_ref → issue_area_name → issue_area_id`,
and `anchor_text` is read from `provisions_by_id`, i.e. the *extraction provisions*, which are empty on
this Mode C path. So the chain fell straight to matching an LP's **name** against the carrier
document's text.

**This is exactly the information the old code discarded**, and it points at the cause rather than the
symptom.

**Caveat, and it matters:** the carrier here is `T-04_subtle.docx`, a *different lease*, because the
ex6-4 fixture is `.txt` and the annotator needs a real DOCX. A document that actually contains "SNDA"
or "Hazardous Materials" as text would likely anchor. **These specific four drops are carrier-specific
and should not be read as a production failure rate.**

---

# WHAT IS NOT ESTABLISHED

- **The DOCX does not tell its own reader.** The record is on the result and in the return value, but
  the summary block precedes the coverage loop, so no note is rendered there. **Only the PDF cover
  surfaces it.**
- **The four drops are carrier-specific.** Measured against `T-04_subtle.docx`, not the real ex6-4
  document. The real production drop rate is unmeasured.
- **The `anchors_tried` record captures availability, not why each match failed** — it says
  `section_ref` was absent, not that a present `section_ref` failed to match. For the four here that
  distinction does not arise, since only name and id were available at all.
- **The PDF annotator's report was not exercised on a real PDF.** Its code path mirrors the DOCX one
  and is covered by the same tests passing, but no PDF artefact was generated in this step.
- **No production run carries `annotation_reports` yet.** For Mode C the annotators run at download
  time, after the result JSON is written, so the persisted run record still will not contain the
  report unless `generate_outputs` is the caller.
- **The filter, ordering and citation gate were not touched**, per the brief.
