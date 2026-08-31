# Step 521 PART A — Design. The design does not hold, and I did not build it.

**Date:** 2026-08-31 · **Instruction:** `build_log/521_chat_instruction.md`
**PART A COMPLETE. PART B NOT BUILT — per the brief's own gate, "only if A is clean." A is not clean.**
**Nothing changed, no provider calls, not deployed.**

---

# THE HEADLINE

**`requires_attention` is not the field that fails. It is already `True` on 27 of 32 LPs in the Step-517
Atlas run — and the rendered PDF tells the reader "3 issue area(s) require attention... 29 covered."**

The brief targets entries that emit `False`. The larger defect is entries that emit **`True` and are
rendered with a checkmark anyway**, because the presentation layer does not read `requires_attention`
at all. **Adding `assessment_status` would be a third field that the six surfaces also ignore** — which
is precisely the failure the brief's own Q3 warns about.

---

# Q1 — EVERY ROUTE, FROM CODE

Eight `_build_assessment` call sites in `lease_coverage.py`:

| # | line | trigger | coverage_state | elements | panel |
|---|---|---|---|---|---|
| R1 | 380 | applicability `excluded` / `not_applicable` | `not_applicable` | **none** | no |
| R2 | 392 | applicability `unclear` | `default_when_unclear` | **none** | no |
| R3 | 422 | extraction status `NOT_APPLICABLE` | `not_applicable` | **none** | no |
| R4 | 456 | reserved/omitted signal | `broken_xref` | found=[] missing=**all expected** | no |
| R5 | 493 | no tenant text, no global-scan hit | `missing` / `broken_xref` | found=[] missing=**all expected** | no |
| R6 | 510 | global-scan hit | `_determine_coverage_state` | deterministic `_assess_elements` | no |
| R7 | 578 | **Step 305** | from element verdicts | from the panel | **YES** |
| R8 | 631 | legacy path **incl. 305 raising** | `_determine_coverage_state` | deterministic `_assess_elements` | no |

**The distinction the brief asked for:**

- **R1, R2, R3 produce zero element verdicts** — genuinely nothing assessed.
- **R4 and R5 produce a verdict nobody voted on.** They set
  `elements_missing = get_expected_elements(pid)` — the report then asserts *"Missing: <six named
  elements>"* with no evaluator having read anything. This is the sharper case, and it is **not** in the
  brief's list.
- **R6 and R8 are judged deterministically, not by the panel** — keyword matching in `_assess_elements`.
- **R8 is reached silently when the 305 path raises** (`except Exception as _e_305: ... falling through
  to legacy path`). The panel failed, regex substituted, and **nothing on the assessment records it.**
  That is this arc's Thread-B shape — a broken path returning an ordinary-looking result.

**`coverage_method` is set on R7 only** (`lease_coverage.py:588`). All seven other routes omit it.
`app.js:12107` reads `a.coverage_method || 'step_305_per_element'` — **a default that asserts the panel
ran.** *Not currently reachable:* the caller at `app.js:12266` filters to
`element_verdicts.length > 0` first. Latent, not live. Checked rather than assumed.

---

# Q2 — THE TRUTHINESS TEST STILL HOLDS; ADOPT THE ORTHOGONAL FIELD, BUT IT IS NOT SUFFICIENT

`lease_exposure.py:523` reads, verbatim:

```python
        if (materiality == "high"
                and assessment.get("coverage_state") not in ("covered", "not_applicable")
                and not assessment.get("requires_attention")):
            assessment["requires_attention"] = True
```

**`not assessment.get(...)` — confirmed, still a truthiness test.** A third value breaks it in both
directions: any non-empty string is truthy, so `not "not_assessed"` is `False` and the
high-materiality enforcement silently stops firing. `lease_coverage.py:1081`, `:1094` and `:1163` do
the same bare-truthiness test. **Step 470's reasoning holds. A third boolean value is out.**

**So `assessment_status: "assessed" | "not_assessed"` as an orthogonal field is correct — and
insufficient on its own**, for the reason in Q3.

---

# Q3 — THE CONSUMER CENSUS. THERE IS ONE SHARED CONSUMER, AND IT IS THE DEFECT

**`_resolve_display(coverage_item, perspective)` in `lease_display.py:88` is the single gatekeeper**
for every presentation surface:

| surface | call site |
|---|---|
| annotated DOCX | `lease_docx_annotator.py:660` |
| annotated PDF | `lease_pdf_annotator.py:350` |
| summary cover PDF / synopsis | `lease_report_generator.py:255` |
| batch summary | `summary_generator.py:1179`, `:1235` |
| section grouping (web) | `lease_display.py:219` (`resolve_sections`) |

**None of them reads `requires_attention`.** They read `coverage_state` + `partial_class` and nothing
else. `requires_attention` is consumed only by `lease_adapter.py:2199` (a counter) and three
`lease_coverage.py` log lines.

## The catch-all — exercised, not read

```
coverage_state             label                  bucket           marker
covered                    COVERED                covered          ✓
not_applicable             COVERED                covered          ✓
applicability_unclear      COVERED                covered          ✓
review_needed              COVERED                covered          ✓
ambiguous                  COVERED                covered          ✓
partial (partial_typical)  COVERED                covered          ✓
missing                    MISSING                needs_attention  ✕
broken_xref                BROKEN_XREF            needs_attention  ✕
```

**`_resolve_display` has no branch for `not_applicable`, `applicability_unclear`, `review_needed`,
`ambiguous`, or `partial_typical`. All five fall through the final
`return {"bucket": "covered", "label": "COVERED", "marker": "✓"}`.**

**The two derived fields already contradict each other:**

```
coverage_state          requires_attention    display
review_needed           True                  COVERED ✓
partial/partial_typical True                  COVERED ✓
```

---

# Q4 — WHAT A READER SEES. MEASURED ON REAL RUNS AND RENDERED FILES

## The counts disagree with each other on the same result object

Step-517 Atlas, `run_01_full.json`:

```
coverage_summary.attention_count            = 27
requires_attention == True                  = 27 of 32 LPs
```

The **rendered** `_summary_cover.pdf`, generated from that exact result:

> **Findings**
> **"3 issue area(s) require attention, 0 worth reviewing, 29 covered."**

**27 internally, 3 to the reader.** The other 24 are inside "29 covered."

## LP-14 Force Majeure — the case that should not be a checkmark

From the same result:

```
LP-14  dispute_signal.triggered = true
       reason = "1 critical rubric element(s) disputed — majority verdict withheld,
                 human review required"
       materiality = high     requires_attention = True
       _resolve_display -> COVERED ✓ , bucket "covered"
```

**The panel withheld a verdict on a critical element at high materiality, and the reader is shown a
checkmark.** The rendered PDF contains no occurrence of `withheld`, `human review`, or `review_needed`.
LP-14 surfaces only incidentally, through an unrelated `DIRECTIONAL MISMATCH [LP-14] [HIGH]` finding
produced by a different mechanism.

## The genuinely not-assessed entries are invisible, not merely unflagged

Step-517 Atlas has two: **LP-23** and **LP-31**, both `applicability=unclear` → `not_applicable`, zero
element verdicts. **Neither appears anywhere in the rendered PDF.** Both are counted in "29 covered."

Step-496 divall has nine such entries; five render `COVERED ✓`.

## Surface-by-surface, as generated

| kind | example | annotated DOCX/PDF | summary cover PDF |
|---|---|---|---|
| assessed + missing | LP-05 | `[GAP]` callout | *"LP-05 Permitted Use — No restriction on how tenant uses space / Missing: ..."* |
| assessed, verdict withheld | LP-14 | **no callout** (`covered` ∉ `ANNOTATED_BUCKETS`) | **counted in "29 covered"** |
| not assessed | LP-23, LP-31 | **no callout** | **absent; counted in "29 covered"** |

**Assessed-and-clean, verdict-withheld, and never-assessed are today the same output: silence plus a
tally in "covered."**

## A third surface is worse than indistinguishable — it is empty

`/api/jobs/{id}/results/{i}/summary` → `generate_tenant_summary` (`main.py:2418`) has **no mode
branch**. Generated from the real Mode C Atlas result, the entire summary DOCX is:

```
Contract Analysis Summary
Tenant: atlas_meridian_warehouse_lease.txt
Contract Overview            [8-row table: Landlord, Tenant, Property, Term, ...]
Analysis Summary
Provisions analyzed: 33
Conforming: 0
Deviations found: 0
Unclear: 0
Critical: 0  |  High: 0  |  Medium: 0  |  Low: 0
```

**"Deviations found: 0" on a run with 27 attention items.** The coverage section at
`summary_generator.py:1160` is in the *batch* path; the per-tenant DOCX renders the Mode A deviation
shape and never touches `coverage_assessment`.

---

# WHY I DID NOT BUILD PART B

The brief gates it: *"BUILD, only if A is clean."*

**Adding `assessment_status` now would ship a field that all five `_resolve_display` call sites ignore,
into a layer already ignoring `requires_attention` on 27 of 32 LPs.** It would satisfy the letter of
the step and change nothing a reader sees — the exact outcome the brief's Q3 exists to prevent.

**The exercise the brief specified is what proved this**, so I ran it as a diagnostic rather than as an
acceptance test: real result → real PDF → quoted text. A static read would have found the missing
state; only generating the file showed "3 require attention, 29 covered" against an internal 27.

---

# THE CORRECTED DESIGN — three changes, ordered, none of them yet built

**(A) Fix `_resolve_display`'s catch-all first.** It is one function, five call sites, all six
surfaces. Give it explicit branches for `review_needed`, `applicability_unclear`, `not_applicable` and
`ambiguous` instead of letting them reach `COVERED ✓`. **Nothing else in this step matters until a
withheld verdict stops rendering as a checkmark.**

**(B) Then add `assessment_status: "assessed" | "not_assessed"`** as Step 470 specified — orthogonal,
never a third value of `requires_attention`, set at each of the eight routes from what actually ran
(R7 → `assessed`; R1–R5 → `not_assessed`; R6/R8 → `assessed_deterministic`, which is the honest third
value and is why the field must be a string in its own key). **R8 must record that the panel raised**,
not silently inherit the deterministic label.

**(C) Reconcile the two counters.** `coverage_summary.attention_count` and the PDF's "N require
attention" must be computed from the same predicate, or one of them must be renamed to say what it
actually counts.

**Open question for you, not for me:** whether `partial_typical → COVERED ✓` is intended.
`_classify_partial` assigns it to *low-materiality* partials, so it may be a deliberate editorial
choice. **It is defensible as display and indefensible as arithmetic** — those 22 LPs are inside
`attention_count = 27`. I have not changed it.

---

# WHAT THIS DOES NOT ESTABLISH

- **I did not build or change anything.** No schema field was added; the corrected design is a
  proposal.
- **The rendered evidence is one run** (Step-517 Atlas) plus a cross-check on Step-496 divall. The
  27-vs-3 gap is measured on that run, not shown to be constant.
- **Two of the six surfaces were not generated** — the annotated DOCX and annotated PDF. I established
  from `ANNOTATED_BUCKETS` that `covered` items get no callout, and did not produce the files to
  confirm it. **That claim is read, not exercised.**
- **The web surface was not exercised**, only its `resolve_sections` dependency.
- **`app.js`'s `coverage_method` default is latent, not live** — guarded by the caller's filter today.
- **Whether `partial_typical → COVERED` is a defect or a decision is unresolved**, and I did not treat
  it as either.
