# Step 485 — Export gap closed. Verified by artefact, and artefact verification caught a real bug.

**Date:** 2026-08-24 · **Instruction:** `build_log/485_chat_instruction.md`
**Tests 359 passed.** Artefacts generated from both the Step-476 degraded and clean results and read
back. **Not deployed.**

---

## Triage — 4 changed, 3 skipped

**Changed** (each reaches a human on a route that bypasses the web banner):

| consumer | route | insertion point |
|---|---|---|
| `lease_docx_annotator` | annotated lease DOCX via `/api/jobs/{id}/results/{i}/annotated` | `_insert_summary_section()` already prepends at `body[0]` |
| `lease_pdf_annotator` | annotated lease PDF, same route | **no cover page existed** — new page inserted at index 0 |
| `summary_generator` | "Contract Analysis Summary" DOCX via `…/summary` | directly under the title |
| `lease_display` | **helper, not a display surface** — added the shared formatter here only | see below |

**Skipped, with reasons:**

- **`main.py`** — serves, does not render. `/api/jobs/{id}/results` returns the persisted result
  **verbatim**, so markers already flow through (verified Step 475). Its human surfaces are
  `index.html` + `app.js` (closed Step 477) and the DOCX/PDF endpoints, which delegate to the
  annotators changed here. A banner in `main.py` would duplicate what the artefact now carries.
- **`index.html`** — already hosts `#incomplete-report-banner`, rendered first in `renderResults()`.
  Its `print` / `export` / `download` occurrences are links to the DOCX/PDF endpoints, not separate
  render paths, so they are covered by fixing the artefacts.
- **`lease_display.py` as a presenter** — its public surface is `resolve_perspective`,
  `resolve_sections`, `_resolve_display`, `extract_headline`: a formatting library consumed by
  `lease_exposure` and `lease_docx_annotator`. Nothing it returns reaches a human except through a
  consumer already changed.

**A distinction worth stating plainly:** I skipped `lease_display` as a *presenter* but did **add** the
shared formatter `incomplete_report_lines()` to it. It imports nothing from the consumers (verified: 0
references), so it is the only cycle-safe home — `lease_report_generator` imports
`lease_docx_annotator`, so the annotators cannot import back from it. One source of wording for all
three exports, rather than three copies to drift.

## What a reader actually sees

### Annotated lease DOCX — degraded

First three paragraphs of the file, **above the report title**:

```
INCOMPLETE REPORT - NOT VALID FOR LEGAL ANALYSIS
INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS. Extraction returned no text for 1 required
issue area(s): LP-12. Those areas were assessed with no evidence and their findings are
unsupported. The rest of this report was produced normally, but the document has not been
fully analysed.
Issue areas with no evidence: LP-12
CAM Lease Analysis Report                       <- the previous first line
August 25, 2026  |  atlas_meridian_warehouse_lease.txt
```

Red bold on a `#FEF3F2` fill with a `#B42318` left border.

### Annotated lease PDF — degraded

**A new page one.** 13-page source → **14 pages**. Page one reads:

```
INCOMPLETE REPORT - NOT VALID FOR LEGAL ANALYSIS
INCOMPLETE REPORT -- NOT VALID FOR LEGAL ANALYSIS. Extraction returned no text for 1 required
issue area(s): LP-12. Those areas were assessed with no evidence and their findings are
unsupported. The rest of this report was produced normally, but the document has not been fully
analysed.
Issue areas with no evidence: LP-12
```

Inserted **after** all annotation work, immediately before `doc.save()`, so `doc[0]` (the conflict-note
block at `:203`) and the `for page in doc` search loops all run against the original page indices. A
word-wrap helper was needed — `insert_text` does not wrap, and an unwrapped statement runs off the page
edge unread.

### Summary DOCX — degraded

```
Contract Analysis Summary          <- title
INCOMPLETE REPORT - NOT VALID FOR LEGAL ANALYSIS
INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS. Extraction returned no text for 1 required…
Issue areas with no evidence: LP-12
Tenant: atlas_meridian_warehouse_lease.txt
Contract Overview                  <- findings begin here
```

### All three, clean — unchanged

| artefact | clean output |
|---|---|
| annotated DOCX | first line `CAM Lease Analysis Report` — as before |
| summary DOCX | first line `Contract Analysis Summary` — as before |
| annotated PDF | **13 pages**, page one is `STANDARD RETAIL LEASE AGREEMENT` — as before |

`incomplete_report_lines(clean)` returns **`None`**, so every banner block is skipped and the clean
output is **unchanged by construction**, not merely by inspection.

## ARTEFACT VERIFICATION CAUGHT A REAL BUG — a code read would not have

First generation produced:

```
[docx_annotator] Summary section insertion failed (non-fatal): Argument must be bytes or unicode,
                 got 'RGBColor'
```

I had passed `RGBColor(0xB4, 0x23, 0x18)` to the annotator's local `_add_para`, whose `color` argument
is written straight into `w:val` and **requires a hex string** — unlike `summary_generator`, which uses
python-docx runs and *does* take `RGBColor`. Two DOCX writers, two different colour contracts.

**The failure mode is exactly the Step-477 `escapeHtml`/`esc` class:** the whole summary insertion is
wrapped in a non-fatal `try/except`, so the degraded DOCX emerged as the **raw lease with no banner and
no summary section at all**, while the clean DOCX was unaffected. Silent, degraded-only, invisible to
static reading. **Fixed to hex strings and re-verified end to end.**

## What is NOT established

- Behaviour on real customer DOCX/PDFs. Verified on `T-04_subtle.docx` / `.pdf`; source documents with
  unusual structure may place the DOCX banner differently.
- The combined/batch summary PDF (`generate_combined_summary_pdf`, `generate_batch_summary`) was not
  exercised — only `generate_tenant_summary`. It is reached from `job_manager:1661` and `main.py:2341`
  and remains **unverified**.
- Whether the PDF's extra page breaks any downstream consumer that assumes page counts match the
  source. Not traced.
- Deployed behaviour. Local only.
