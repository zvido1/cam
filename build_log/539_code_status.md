# Step 539 — The report said "18 covered" about a lease with ZERO covered provisions. Now it says 0.

**Date:** 2026-09-03 · **Instruction:** `build_log/539_chat_instruction.md`
**Tests: 406 passed, 3 skipped, 12 subtests. No panel verdict changed. Not deployed.**

---

# 0. THREE PREMISE CORRECTIONS, AND THEY RELOCATE THE DEFECT

**"`covered` is total minus deviating, computed independently at six sites, where deviating counts only
missing and broken_xref."** There are **two** definitions, and neither is that formula:

```
lease_coverage.summarize_coverage:1163   covered_count = state_counts.get("covered", 0)   -> 0
lease_report_generator:253-285           covered_count = residue of the bucket if/elif     -> 18
```

**On the Step-537 result those return 0 and 18.**

**"LP-20 (0 of 7 elements, suppressed)"** — no suppression is involved. All seven element verdicts are
`missing` (5), `disputed` (1), `unclear` (1); **none is a presence verdict, so none requires a
citation** and the citation gate never fires. `citation_quality` is `None` throughout because there is
nothing to cite. **The panel found the elements genuinely absent, which is correct — this tenant has no
exclusivity covenant.** LP-20 was also **already fixed by Step 538**: it now reads `NO ELEMENTS FOUND`,
`needs_attention`, and is annotated.

**"LP-30 (covered_unfavorable, invisible in the DOCX)"** — LP-30 is `partial` with
`partial_class: partial_typical`, **5 of 6 elements present**, `requires_attention: True`,
`materiality: low`. Not `covered_unfavorable`. **"Invisible in the DOCX" is correct**, and §4 explains
why.

## Where the defect actually is

```
state_counts: {'partial': 18, 'review_needed': 9, 'not_applicable': 1, 'missing': 3, 'broken_xref': 1}
LPs in state `covered`:  ZERO
PDF top line:            "18 covered"
API summary:             requires_attention: 31 of 32
```

**Not one provision in butler_crossing was assessed as covered.** All 18 are partials — incomplete
provisions — reclassified because `_classify_partial` assigns `partial_typical` on low materiality.
**Step 521 raised this; Step 538 explicitly deferred it. This step closes it.**

---

# 1. WHAT EACH STATE MEANS, AND THE TOP LINE THAT CARRIES IT

| state | what a reader should conclude |
|---|---|
| `covered` | The provision is present and every expected element was found. Nothing to do. |
| `partial` | **Present and largely complete, but at least one expected element is missing.** Not a gap; not clean. |
| `missing` | The provision is absent from the lease. A real gap. |
| `broken_xref` | A section exists but points at something absent or reserved. The lease is internally incomplete. |
| `covered_unfavorable` | Present, complete, and tilted against the reader's side. Worse than a gap — it is a term, not an omission. |
| `potentially_unenforceable` | Present but may not survive challenge in this jurisdiction. |
| `review_needed` | **The panel withheld a verdict.** A human must decide; no machine conclusion exists. |
| `ambiguous` | The text supports more than one reading. |
| `not_applicable` | The provision does not apply to this lease type. Nothing was judged. |
| `applicability_unclear` | We could not determine whether it applies. Nothing was judged. |

**Smallest set that preserves those distinctions — five top-line categories:**

```
needs attention   missing, broken_xref, covered_unfavorable, potentially_unenforceable,
                  partial_material, and ANY assessed LP with zero elements present   -> LP-20
worth reviewing   review_needed, ambiguous, partial_review
minor gaps        partial (partial_typical / unclassed)                              -> LP-30
not assessed      not_applicable, applicability_unclear, assessment_status != assessed
covered           covered, and only covered
```

**Both named cases are handled.** LP-20 lands in *needs attention* via Step 538's evidence guard —
zero elements present outranks its state. LP-30 lands in *minor gaps*, which is new here and is the
category the scheme previously lacked entirely.

**Why five and not four:** collapsing *minor gaps* into *covered* is the defect. Collapsing it into
*needs attention* would put an LP with 5 of 6 elements beside one with 0 of 7, which is the opposite
error and would make the attention list unreadable — 22 of 32 on this document.

---

# 2. `assessment_status` — BESIDE THE TOP LINE, AND IT ALREADY IS

An LP nobody assessed is **neither covered nor deviating**, so it cannot be folded into either.

**It is already its own top-line count** — Step 522 added the `not_assessed` bucket and it renders as
its own clause. **No change needed; this step confirms rather than alters it.**

It stays *orthogonal* rather than becoming a sixth category, because it answers a different question:
the other four say what was concluded, this one says whether anything was. **An LP can be
`not_assessed` for a state that would otherwise be `missing`** — that is why it is checked first in
`_resolve_display`, ahead of every coverage_state branch.

---

# 3. ONE SHARED HELPER

**New: `lease_display.summarize_display_buckets(coverage_items, perspective)`** — the single source of
truth. It returns the bucket counts, the total, named scalars, and `_source` naming itself so a
divergent seventh formula is identifiable in any result object.

**Call sites, all six, and none computes a variant afterwards:**

| # | site | what it does now |
|---|---|---|
| 1 | `lease_coverage.summarize_coverage` | **delegates** — `covered_count` is now the helper's, not `state_counts["covered"]` |
| 2 | `lease_report_generator:256` | bucket loop with an explicit `minor_gaps` branch; the `else` can no longer absorb it |
| 3 | `lease_report_generator:422` | `resolve_sections`, which groups from the same `_resolve_display` |
| 4 | `summary_generator:1179` | `bucket_counts` over `BUCKET_SECTION_HEADERS` |
| 5 | `summary_generator:1241` | section tiers over `BUCKET_ORDER_BY_PERSPECTIVE` |
| 6 | `summary_generator:1524` | `resolve_sections` |

**All six now derive from `_resolve_display`.** Sites 2-6 already did; site 1 is the one that did not,
and it is why the same result object carried both 0 and 18.

**The structural guard against a seventh:** adding a bucket to `BUCKET_ORDER_BY_PERSPECTIVE` without
adding it to `summary_generator`'s `bucket_phrase` raises `KeyError` at
`parts = [f"{bucket_counts[b]} {bucket_phrase[b]}" for b in order]`. **Step 522 hit that trap; I hit it
again here and it caught me both times.** It is a real forcing function and worth keeping.

---

# 4. WHY LP-30 WAS INVISIBLE, AND WHETHER 1-3 FIXES IT

**Cause:** `partial_typical` → `covered` bucket, and `ANNOTATED_BUCKETS` excludes `covered`. The
annotator loop skips any item whose bucket is not in that set, so LP-30 got **no margin callout at
all** — its one missing element was invisible to anyone reading the document itself.

**It is the same root as the arithmetic defect, not a separate one.** Both are `partial_typical`
resolving to `covered`. **Fixing the category fixes the annotation**, provided the new bucket is
annotated — so `minor_gaps` was added to `ANNOTATED_BUCKETS` deliberately:

```python
ANNOTATED_BUCKETS = {
    "needs_attention", "favorable_to_your_side", "asymmetric_terms",
    "worth_reviewing",
    "minor_gaps",     # Step 539
}
```

**No separate change was required.** The DOCX went from **7 coverage-gap callouts to 23**.

---

# 5. THE ARTEFACTS — SAME RESULT FILE, RE-RENDERED

## Top line

```
Step 537 (as shipped):  3 require attention, 0 worth reviewing, 2 NOT ASSESSED, 27 covered.
after Step 538:         4 require attention, 8 worth reviewing, 2 NOT ASSESSED, 18 covered.
after Step 539:         4 require attention, 8 worth reviewing,
                        18 substantially addressed with minor gaps, 2 NOT ASSESSED, 0 covered.
```

**"0 covered" is the truthful number.** `state_counts` contains no `covered` entry.

Shared helper output:
```
{"buckets": {"needs_attention": 4, "worth_reviewing": 8, "covered": 0,
             "minor_gaps": 18, "not_assessed": 2}, "total": 32}
```

## LP-20

**PDF before (Step 537):** absent entirely — inside the 27 covered, whose tail the cover omits.
**PDF after:**
> *LP-20 Exclusivity — Exclusivity protection absent or undefined. Missing: Specific exclusive use scope
> is defined (protected business activities), Carve-outs for existing tenants at the center are
> addressed, Carve-outs for ancillary or incidental use by other tenants are addressed, Duration of
> exclusivity...*

**DOCX before:** no callout. **DOCX after:**
> *[GAP] LP-20 Exclusivity — Exclusivity protection absent or undefined (LOW materiality)*

## LP-30

**PDF before:** absent — inside the covered tail.
**PDF after:**
> *LP-30 Estoppel Certificate — Estoppel certificate terms undefined. Missing: Limitation on request
> frequency is addressed. …tenant faces uncertainty over required scope of certification, liability for
> inaccurate statements, and deemed-approval traps…*

**DOCX before:** no callout, anywhere. **DOCX after:**
> *[GAP] LP-30 Estoppel Certificate — Estoppel certificate terms undefined (LOW materiality)*
> *Missing: Limitation on request frequency is addressed*
> anchored at *"Within ten (10) days after Landlord's written request, Tenant shall execute and deliver
> to Landlord an estoppel certificate…"*

**The callout is anchored to the actual estoppel clause** — a reader sees the missing element beside
the provision it belongs to.

**No panel verdict changed.** Every state, element verdict and `requires_attention` value is
byte-identical; only categorisation and rendering moved.

---

# WHAT IS NOT ESTABLISHED

- **23 DOCX callouts may be too many.** Every one names a real missing element, but whether a reader
  wants 23 margin notes on a 242 KB lease is a judgement nobody has made. **The count is honest; the
  ergonomics are untested.**
- **The web screen still categorises independently.** `app.js`'s `classifyFindingType` does not use
  `_resolve_display`, so `minor_gaps` does not exist on screen. Unchanged from Step 538 and still the
  one surface of the six this does not reach.
- **"LOW materiality" on LP-20 exclusivity remains wrong-looking** for a retail tenant.
  `_classify_materiality` is untouched and out of scope.
- **Measured on one result file.** The 0-vs-18 divergence is butler_crossing's; Atlas and solidpower
  were not re-checked under the new scheme.
- **The five categories are a proposal validated on one document.** Whether *minor gaps* at 18 of 32 is
  a useful signal or just a differently-shaped residue needs a second lease.
- **The citation gate was not touched**, per the brief — though §0 records that it is not implicated in
  LP-20 at all.
