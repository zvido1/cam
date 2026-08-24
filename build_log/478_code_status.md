# Step 478 — Applicability-aware gate

**Date:** 2026-08-24 · **Instruction:** `build_log/478_chat_instruction.md`
**NOT DEPLOYED.** Tests **357 passed** (354 + 3 new). Flags:
`GATE_ABORT_RETURNS_DEGRADED = True`, `DEGRADABLE_APPLICABILITY = {"not_applicable", "unclear"}`.
Everything from 476/477 — markers, aggregate, banner — retained on the degrade path.

---

## The `unclear` judgment call: DEGRADE. Reasoned, then verified.

The gate's stated purpose is to prevent *"a confident 'missing' verdict … for a provision that simply
was not extracted."* That harm requires the LP to reach the 305 evaluator, where
`lease_coverage_305.py` injects:

> `NOTE: No provision text was found for this issue area. The lease is silent on this topic. Return`
> `verdict 'missing' for every element.`

**An `unclear` LP never reaches it.** `lease_coverage.py:359-369` short-circuits with `continue`:

```python
        if applicability_result == "unclear":
            default_state = get_default_when_unclear(pid)
            _a = _build_assessment(
                pid=pid, area=area, coverage_state=default_state,
                applicability=applicability_result,
                evidence_summary=f"Cannot determine whether this issue area applies; defaulting to '{default_state}'",
                supporting_provisions=[], negative_space=ns_signals.get(pid, []),
                elements_found=[], elements_missing=[], tenant_text="",
            )
```

`tenant_text` is forced to `""` and no evaluator runs, so **extraction's output is not consulted on
that branch at all** — the entry is identical whether extraction returned text or nothing. That is
exactly LP-12's property, and it is not an inference: on the real Atlas run, LP-23 and LP-31 (both
`unclear`) carry **0 element verdicts**, like LP-12.

Aborting an `unclear` LP therefore destroys the whole report to prevent an output that cannot differ.
The "be cautious under uncertainty" counter fails on *cautious against what?* — the named harm is
unreachable, and the entry already self-labels *"Cannot determine whether this issue area applies."*

**Confirmed live in this step:** across the four degraded LPs on divall (`LP-12` not_applicable,
`LP-30/31/32` unclear), **total element verdicts = 0.** No false `missing` was generated.

**This corrects Step 477**, which predicted LP-30/31/32 "WOULD be assessed with no evidence." That was
inferred from the 305 prompt without checking whether `unclear` reaches it. It does not.

The choice is one edit: drop `"unclear"` from `DEGRADABLE_APPLICABILITY` for the stricter posture.

## The change

The gate partitions its failures with `is_applicable(pid, document_text)` — schema plus document only,
no extraction dependency:

```
required | applicable      -> ABORT   (reaches 305; empty evidence becomes asserted silence)
not_applicable | unclear   -> DEGRADE (short-circuits before Stage 5; output cannot differ)
```

Any non-degradable failure aborts the whole run. The abort message now names **only the blockers** and
carries the applicability map, so the reason is legible rather than a bare list. The degrade path
records only the degradable LPs, each annotated with its applicability.

## TEST — Atlas

**Still degrades and continues.** `s478_atlas_r2`:

```
completeness gate applicability: {'LP-12': 'not_applicable'} | must_abort=[] degradable=['LP-12']
COMPLETENESS GATE DEGRADED (canonical): 1 LP(s) missing evidence, all on a short-circuit
applicability branch: ['LP-12']. Continuing; run marked invalid_for_legal_analysis.
```

Summary: `REPORT_INCOMPLETE=true`, `issue_areas_with_no_evidence=["LP-12"]`. Banner renders.

**LP-07 flip holds — unchanged across every run:**

| run | found/missing | `22.4` | state | conf | pshare in `elements_found` |
|---|---|---|---|---|---|
| 468-e1 / 468-e2 | 5/1 | ✅ | partial | high | ✅ |
| 476-DEG | 5/1 | ✅ | partial | high | ✅ |
| **478-DEG** | **5/1** | **✅** | **partial** | **high** | **✅** |

**LP-27 — all ten elements identical to e1/e2 and to 476.** `partial`, confidence `high`, 8 found /
1 missing. Zero movement.

## TEST — divall: it DEGRADED, not aborted. Prediction wrong, gate correct.

```
completeness gate applicability: {'LP-12': 'not_applicable', 'LP-30': 'unclear',
                                  'LP-31': 'unclear', 'LP-32': 'unclear'}
                                  | must_abort=[] degradable=['LP-12','LP-30','LP-31','LP-32']
divall: COMPLETED (1175s) degraded=True lps=['LP-12','LP-30','LP-31','LP-32']
```

**I predicted an abort on LP-07/LP-16/LP-17. That prediction was conditioned on Step 472's *pipeline*
failure set (6–7 LPs). This attempt's extraction failed only 4 LPs — matching Step 472's *standalone*
extraction — and all four are degradable, so `must_abort` was empty.**

The gate behaved exactly as specified; the input differed. This is extraction shape variance, the same
phenomenon Steps 463/464 measured on Atlas. **The live abort path was therefore NOT exercised** — it is
covered by three unit tests, not by a real run. Recorded as a gap, not glossed.

**And a first: this is the first completed coverage result for divall in the project's history.**
Step 472 recorded *"the pipeline CANNOT PROCESS divall_wendys_mtpleasant_lease.txt"* — four attempts,
no result. It now produces one: 32 LPs assessed, 73 calls, 735s.

The four degraded LPs, verified:

| LP | applicability | coverage_state | element verdicts | `evidence_missing` |
|---|---|---|---|---|
| LP-12 | not_applicable | not_applicable | **0** | true |
| LP-30 | unclear | not_applicable | **0** | true |
| LP-31 | unclear | not_applicable | **0** | true |
| LP-32 | unclear | not_applicable | **0** | true |

Banner on divall:

> **⚠ INCOMPLETE REPORT — NOT VALID FOR LEGAL ANALYSIS**
> …Extraction returned no text for 4 required issue area(s): LP-12, LP-30, LP-31, LP-32…
> Issue areas with no evidence: **LP-12, LP-30, LP-31, LP-32**

## The seven remaining presentation consumers — all still 0

Not fixed, per instruction. Each would present a degraded report as complete:

| consumer | degraded refs | would it present a degraded report as complete? |
|---|---|---|
| `app/main.py` | 0 | **Yes** — serves `/api/jobs/{id}/results` and the results page; no marker in any response shaping |
| `app/summary_generator.py` | 0 | **Yes** — builds the AI narrative summary from `coverage_assessment`; would summarise a 4-LP-blind report as a finished analysis |
| `lease_report_generator.py` | 0 | **Yes, and worst** — produces the report artifact a reader may open with no browser and never see the banner |
| `lease_display.py` | 0 | **Yes** — CLI/terminal rendering, no incompleteness surface |
| `lease_docx_annotator.py` | 0 | **Yes** — DOCX artifact, same detached-from-banner problem |
| `lease_pdf_annotator.py` | 0 | **Yes** — PDF artifact, same |
| `static/index.html` | 0* | Partly — it now hosts `#incomplete-report-banner`, but no other surface (tabs, exports, print view) checks the markers |

*the banner element exists; the count is of marker *reads*, and the file does none.

**The exported artifacts are the sharpest gap:** a DOCX or PDF handed to a lawyer carries no
incompleteness statement at all.

## What is NOT established

- The live abort path. Three unit tests cover it; no real run has aborted under the new logic, because
  the divall attempt happened to fail only degradable LPs.
- Whether divall's completed result is any *good*. It completed; its 32 LP verdicts are unexamined.
  Step 472's precision warnings still stand, and the locator emits `ARTICLE\nXI` labels on that fixture.
- Deployed behaviour. Local only, not deployed.
- Whether `run_quality: "incomplete"` breaks a caller switching on the old three values. Still unaudited.
