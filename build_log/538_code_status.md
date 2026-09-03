# Step 538 — "covered" was a fall-through, not a decision. LP-20 now reads NO ELEMENTS FOUND.

**Date:** 2026-09-03 · **Instruction:** `build_log/538_chat_instruction.md`
**Tests: 406 passed, 3 skipped, 12 subtests. Verdicts unchanged. Not deployed.**

---

# 1. WHAT DETERMINED "COVERED": NOTHING. IT WAS THE FALL-THROUGH.

`lease_display.py`, the tail of `_resolve_display` before this step:

```python
    if state == "broken_xref":
        return {"bucket": "needs_attention", ...}

    return {"bucket": "covered",
            "label":  "COVERED",
            "tone":   "covered",
            "marker": "✓"}
```

**There was no membership test for `covered`.** It was an unconditional `return` at the end of the
function. **`review_needed` is in it by OMISSION, not deliberately** — nothing tests for it, so it
falls off the end.

**Six of the ten schema states landed there the same way:**

```
covered                 <- correct, but only by accident
partial                 <- requires_attention True
ambiguous
review_needed           <- requires_attention True   <-- LP-20
not_applicable
applicability_unclear
```

**A state added to the schema tomorrow would have inherited "COVERED ✓" silently.**

---

# 2. EVERY STATE, AND WHERE IT LANDED

```
coverage_state             bucket           label                     marker  req_attn  annotated
covered                    covered          COVERED                   ✓       False     False
covered_unfavorable        needs_attention  UNFAVORABLE TERMS         ✕       True      True
partial                    covered          COVERED                   ✓       True      False
ambiguous                  covered          COVERED                   ✓       False     False
missing                    needs_attention  MISSING                   ✕       True      True
broken_xref                needs_attention  BROKEN_XREF               ✕       True      True
potentially_unenforceable  needs_attention  POTENTIALLY UNENFORCEABLE ✕       True      True
review_needed              covered          COVERED                   ✓       True      False
not_applicable             covered          COVERED                   ✓       False     False
applicability_unclear      covered          COVERED                   ✓       False     False
```

**Explicitly matched: 4 states.** `partial` splits by `partial_class` — `partial_material` →
needs_attention, `partial_review` → worth_reviewing, `partial_typical` and empty → covered.

## The surfaces

**All of them are fed by the same function**, which is why one fix reaches every one:

| surface | site |
|---|---|
| annotated DOCX | `lease_docx_annotator.py:734` |
| annotated PDF | `lease_pdf_annotator.py:350` |
| summary cover PDF (prepended to the annotated PDF) | `lease_report_generator.py:256`, `:422` |
| batch summary — bucket counts | `summary_generator.py:1179` |
| batch summary — section tiers | `summary_generator.py:1241` |
| batch summary — needs-attention filter | `summary_generator.py:1381` |
| synopsis sections | `summary_generator.py:1524` → `resolve_sections` |
| screen (web) | `classifyFindingType` in `app.js`, which branches on `coverage_state` **independently** |
| API | `summary.requires_attention` / `not_assessed` counters, which read the fields directly |

**Eight of the nine go through `_resolve_display`. The screen does not** — `app.js` has its own
`coverage_state` switch, so this fix does not reach it. **Stated, not glossed:** the web surface still
categorises independently and was not changed here.

---

# 3. THE FIX

Four changes, none of which touch a verdict:

**(a) An evidence-based guard, which is the actual answer to the brief.**

```python
    _evs = coverage_item.get("element_verdicts") or []
    if _evs and not any(
        (e.get("verdict") or "") in _POSITIVE_ELEMENT_VERDICTS for e in _evs
    ):
        return {"bucket": "needs_attention",
                "label":  "NO ELEMENTS FOUND", ...}
```

**Evidence-based, not state-based, so a state nobody has thought of yet cannot slip past it.**
Measured safe before shipping: across the Step-524, -528 and -537 runs, LPs with element verdicts and
zero present occur only in `review_needed` (2) and `missing` (1). **No LP whose state is `covered` has
zero elements present**, so the guard can only demote entries that were already self-contradictory.

**(b) `review_needed` → `worth_reviewing`.** It is the state the dispute signal sets when a critical
element is disputed and the majority verdict is withheld. That is a review item by definition.

**(c) `ambiguous` → `worth_reviewing`; `not_applicable` / `applicability_unclear` → `not_assessed`.**
Neither is a clean bill of health.

**(d) `covered` is now a membership test, and the default fails loud.**

```python
    if state in ("covered", "partial"):
        return {... "COVERED" ...}

    # Unrecognised state: fail LOUD, never clean.
    return {"bucket": "worth_reviewing",
            "label":  "UNCLASSIFIED STATE: %s" % (state or "none"), ...}
```

**`partial` is named there deliberately and its behaviour is unchanged.** Step 521 recorded
`partial_typical` → COVERED as an open question — `requires_attention` is True while the display says
covered — and **that is not this step's target.** Naming it converts an omission into a recorded
decision without changing what a reader sees.

## An over-correction I caught by measuring

My first cut omitted `partial` from the membership test. Result: **`partial_typical` rendered as
"UNCLASSIFIED STATE", and 26 of 32 LPs became "worth reviewing"** — a report where everything needs
review is as useless as one where everything is covered. **Found by running it against the Step-537
result before generating any artefact.**

---

# 4. THE ARTEFACTS — BEFORE AND AFTER, SAME RESULT FILE

## The headline count

```
BEFORE:  3 issue area(s) require attention, 0 worth reviewing, 2 NOT ASSESSED, 27 covered.
AFTER :  4 issue area(s) require attention, 8 worth reviewing, 2 NOT ASSESSED, 18 covered.
```

## LP-20 in the summary cover PDF

**BEFORE — absent from the findings entirely.** It sat inside the 27 "covered", and the covered tail is
omitted from the cover, so a reader saw nothing about exclusivity at all.

**AFTER:**

> **LP-20 Exclusivity — Exclusivity protection absent or undefined**
> *Missing: Specific exclusive use scope is defined (protected business activities), Carve-outs for
> existing tenants at the center are addressed, Carve-outs for ancillary or incidental use by other
> tenants are addressed, Duration of exclusivity is defined (full term or limited period), Remedies for
> landlord violation of exclusivity are defined*

## LP-20 in the annotated DOCX

**BEFORE — no callout.** `covered` is not in `ANNOTATED_BUCKETS`, so the annotator skipped it.

**AFTER:**

> **[GAP] LP-20 Exclusivity — Exclusivity protection absent or undefined (LOW materiality)**
> *Missing: Specific exclusive use scope is defined (protected business activities), Carve-outs for
> existing…*

The DOCX run reports `7 coverage gaps` where it previously produced fewer, and the `NOT ASSESSED — 2
provision(s)` block from Step 522 still renders alongside.

**The panel's verdict is byte-identical.** `review_needed`, 0 of 7 elements, `requires_attention: True`
— unchanged. Only the categorisation moved.

---

# WHAT IS NOT ESTABLISHED

- **The web screen was not changed.** `app.js`'s `classifyFindingType` branches on `coverage_state`
  independently of `_resolve_display`, so `review_needed` on screen is unaffected by this step. It is
  the one surface of the nine this fix does not reach.
- **`partial_typical` → covered is untouched and still contradicts `requires_attention: True`** on 18
  LPs in this run. Step 521 raised it; it remains open by choice, not oversight.
- **"LOW materiality" on LP-20 looks wrong** for a retail tenant's exclusivity — that is
  `_classify_materiality`, a different component, and out of scope here.
- **Measured on three runs** (Atlas 524, solidpower 528, butler 537). The zero-present guard's safety
  rests on those; a document where a genuinely covered LP has zero positive element verdicts would be
  demoted, and none exists in the corpus.
- **No new pipeline run.** All before/after figures come from re-rendering the persisted Step-537
  result, so the comparison is exact — same verdicts, same evidence, only the display code differs.
- **Suite timing moved from ~3s to 25–34s** with high variance; the slow tests are
  `test_422b_not_applicable.py` (15.6s, 5.5s), which this step did not touch. Recorded as an
  observation, not diagnosed.
- **The qualifier pass, the locator and the seam fallback were not touched**, per the brief.
