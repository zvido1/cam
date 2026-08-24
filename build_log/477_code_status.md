# Step 477 — Degraded markers reach the user; and the divall answer that bears on deploy

**Date:** 2026-08-24 · **Instruction:** `build_log/477_chat_instruction.md`
**NOT DEPLOYED.** The heading said "Then deploy", the closing line said "Do NOT deploy. Report and
stop." Executed as no deploy, per the explicit final line.
Tests: **354 passed.** `node --check` clean on `app.js`.

---

## 3 (taken first) — the consumer census was incomplete, and I found more

Step 476 checked four files. The real presentation surface is nine, and **`static/app.js` is the
frontend**, not `index.html` — Step 476 checked the wrong file for the UI question.

| consumer | degraded-marker refs (before) | reads `summary` |
|---|---|---|
| **`static/app.js`** | **0** | **160** |
| `static/index.html` | 0 | 10 |
| `app/job_manager.py` | 0 | 23 |
| `app/main.py` | 0 | 35 |
| `app/summary_generator.py` | 0 | 35 |
| **`lease_report_generator.py`** | **0** | **20** |
| `lease_display.py` | 0 | 5 |
| `lease_docx_annotator.py` | 0 | 4 |
| `lease_pdf_annotator.py` | 0 | 0 |

**Nine consumers, zero awareness.** This step closes the two the instruction named. **Seven remain
unclosed** — see "Still open" below.

## 1 — job_manager: markers folded into the aggregate

`_build_job_outcome` now reads the result's own `run_degraded` / `invalid_for_legal_analysis`, sets a
new `has_any_incomplete`, and surfaces it both per-tenant and job-level. A new top-ranking
`run_quality` value — **`incomplete`** — outranks `partial` and `degraded`, because a fallback means a
substitute model answered while this means required evidence was never extracted.

Verified by running the real function over both real Step-476 results:

```
DEGRADED (s476_r2)
   run_quality                      "incomplete"
   report_incomplete                true
   invalid_for_legal_analysis       true
   issue_areas_with_no_evidence     ["LP-12"]
   incomplete_statement             "INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS. …"
   per_tenant[0]  run_degraded=True degraded_reason="extraction_completeness_failed"

CLEAN (s476_r1)
   run_quality                      "clean"
   report_incomplete                false
   issue_areas_with_no_evidence     []
   incomplete_statement             null
```

## 2 — Frontend: banner above everything

`index.html` gains `#incomplete-report-banner` as the **first block inside the overview tab, above
`#deal-brief-banner`** and above every summary counter. `app.js` gains `renderIncompleteBanner()`,
called **first** in `renderResults()` — before `renderDealBrief`, `renderAISummaryBar`,
`renderProvisionHeatmap` and the rest.

**What the user actually sees.** Rendered by executing the real `renderIncompleteBanner` source
against the real degraded result with a stubbed DOM:

```html
<div class="incomplete-report-banner__title">⚠ INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS</div>
<div class="incomplete-report-banner__body">INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS.
Extraction returned no text for 1 required issue area(s): LP-12. Those areas were assessed with no
evidence and their findings are unsupported. The rest of this report was produced normally, but the
document has not been fully analysed.</div>
<div class="incomplete-report-banner__lps">Issue areas with no evidence: <strong>LP-12</strong></div>
```

On the clean result: `hidden=true`, `innerHTML` empty. Styling is a red-bordered block
(`#b42318` on `#fef3f2`) appended to `style.css`.

**Caught during implementation:** I first wrote `escapeHtml(...)`, which **does not exist** in
`app.js` — the global helper is `esc()`. That would have thrown `ReferenceError` on every degraded
render and shown nothing. Fixed before testing; `node --check` passes.

---

## THE DIVALL QUESTION — answered offline. LP-12 IS special, and this bears on deploy.

`is_applicable(provision_id, document_text)` depends only on the LP schema and the full document —
**not on extraction** — so this is computable offline without running divall.

| LP | divall applicability | atlas applicability | divall extracted chars | would an empty extraction be assessed? |
|---|---|---|---|---|
| **LP-12** | **`not_applicable`** | **`not_applicable`** | 0 | **No — ruled out independently** |
| LP-07 | `applicable` | `applicable` | 1260 | **YES** |
| LP-16 | `applicable` | `applicable` | 1260 | **YES** |
| LP-17 | `required` | `required` | 1650 | **YES** |
| LP-30 | `unclear` | `applicable` | 0 | **YES** |
| LP-31 | `unclear` | `unclear` | 0 | **YES** |
| LP-32 | `unclear` | `applicable` | 0 | **YES** |

**LP-12 is the only one of the seven the applicability layer rules `not_applicable`, on both
documents.** Its "identical output clean vs degraded" property comes entirely from that, and **it does
not generalise.**

For the other six, an empty extraction reaching coverage does **not** produce the same output. It
produces a confident *wrong* one — `lease_coverage_305.py` explicitly instructs:

> `NOTE: No provision text was found for this issue area. The lease is silent on this topic. Return`
> `verdict 'missing' for every element.`

**"The lease is silent on this topic" is asserted to the panel when the truth is that extraction
failed.** Which is verbatim what the gate exists to prevent:

> `Gate 3: required LPs with empty tenant_text and no NOT_APPLICABLE provenance must not reach Stage 5`
> `coverage. Missing required evidence is indistinguishable from present evidence once it enters`
> `coverage assessment — this gate prevents a confident "missing" verdict from being produced for a`
> `provision that simply was not extracted.`

### What this means for the deploy decision

**Step 476's framing was too generous, and I should correct it here.** `476_code_status.md` observed
that the gate "aborts on a distinction that makes no difference." **That is true only for LP-12.** On
divall — six LPs, every attempt — degraded continuation would generate confident `missing` verdicts
across six issue areas whose evidence was never extracted, converting an extraction failure into a
substantive finding that the lease is silent.

The Step-476/477 markers *do* flag such a run: the banner fires, `run_quality` is `incomplete`, and
each affected LP carries `evidence_missing`. **But the false `missing` verdicts are still generated,
still counted in `coverage_states`, and still rendered in the body beneath the banner.** A reader who
reads past the banner sees six issue areas reported as absent from the lease.

**So: not safe to deploy as-is.** The banner makes the *run* honest; it does not make the *findings*
honest. The gap is that an LP marked `evidence_missing` should not also be emitting element verdicts —
LP-12 avoids that only by accident of applicability.

Options, none taken here: suppress element verdicts for `evidence_missing` LPs; or exclude them from
the summary counters; or keep the gate's abort for `required`/`applicable` LPs and degrade only for
`not_applicable`/`unclear` ones.

## Still open — seven consumers unclosed

`main.py`, `summary_generator.py`, `lease_report_generator.py`, `lease_display.py`,
`lease_docx_annotator.py`, `lease_pdf_annotator.py`, `index.html` (beyond the banner element). The
**report generator and the DOCX/PDF annotators matter most**: they produce artifacts a reader may open
without ever seeing the web banner. Not in this step's scope; recorded so nobody assumes the surface
is covered.

## What is NOT established

- Any deployed behaviour. Local only.
- What the six divall LPs would *actually* return. Predicted from the prompt instruction and the
  gate's own comment; **divall coverage has never run**, so this is inference from code, not a
  measurement.
- Whether the banner renders correctly in a real browser. Verified by executing the real function
  against a stubbed DOM, not in a live page.
- Whether `run_quality: "incomplete"` breaks any caller that switches on the old three values.
  Not audited.
