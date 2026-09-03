# Step 542 — The filter change is one LP, and the brief excludes that LP. Nothing built.

**Date:** 2026-09-03 · **Instruction:** `build_log/542_chat_instruction.md`
**No code changed. Tests: 406 passed, 3 skipped. Not deployed.**

---

# 0. THE NAMED FUNCTIONS DO NOT EXIST

```
export_findings      : 0 occurrences anywhere in cam/ or 05 Lease Analyzer/
_extract_deviations  : 0 occurrences anywhere in cam/ or 05 Lease Analyzer/
```

**The causal story in the brief describes code that is not in the repository** — there is no
`_extract_deviations` carrying five states and no `export_findings` copying two of them.

**And it inverts Step 541's finding.** Step 541 did not establish "this was not a design decision." It
established the opposite: **the intent is recoverable and it was anchoring, not severity**, from a
comment still in `lease_display.py`:

> *"`missing` items have no anchor in the document body and are excluded by the annotator regardless of
> bucket."*

The real filter is `ANNOTATED_BUCKETS`, tested at `lease_docx_annotator.py:735` and
`lease_pdf_annotator.py:351`.

---

# 1. THE PROPOSED FILTER CHANGES EXACTLY ONE LP — AND THE BRIEF EXCLUDES IT

```
requires_attention True   : 31 of 32
currently admitted        : 30
requires_attention only   : ['LP-23']
admitted only             : []
both                      : 30
```

```
LP-23  state=broken_xref  assessment_status=not_assessed  requires_attention=True  bucket=not_assessed
```

**The single LP that "include everything with requires_attention: True" would add is LP-23, which is
`not_assessed`** — and the brief's own closing requirement says *"confirm not_assessed items are
excluded from findings."*

**The instruction contradicts itself on its only effect.** Implementing it would violate the rule
stated four lines later in the same brief.

**Everything else it asks for is already in place**, shipped at Steps 538 and 539. There is nothing to
build.

## The "12 findings" and "6 findings" figures match nothing

```
admitted by ANNOTATED_BUCKETS : 30
of which state == missing     :  3   (LP-14, LP-28, LP-31 -- no anchor exists)
rendered as [GAP] in the DOCX : 23
silently dropped              :  4   (LP-21, LP-22, LP-29, LP-32)
```

30 − 3 − 23 = 4. **The accounting closes.**

---

# 2. THE SUMMARY AND THE EXPORT ALREADY AGREE

**Cover PDF top line:**
```
4 issue area(s) require attention, 8 worth reviewing,
18 substantially addressed with minor gaps, 2 NOT ASSESSED, 0 covered.
```
4 + 8 + 18 + 2 + 0 = **32** = every coverage entry.

**And nothing vanishes.** The four LPs that failed to anchor still appear in the cover PDF:

```
LP-21 in cover PDF: True     LP-29 in cover PDF: True
LP-22 in cover PDF: True     LP-32 in cover PDF: True
```

**The margin necessarily carries fewer items than the summary**, because a margin callout requires a
paragraph to attach to and an absent provision has none. **That is not a disagreement between summary
and export — it is the difference between a marginal note and a list.** A reader does not see "12
requiring attention and 6 findings"; they see 30 in the summary and 23 in the margin, with the 7-item
difference fully represented in the summary.

---

# 3. not_assessed — EXCLUDED FROM FINDINGS, VISIBLE ELSEWHERE. CONFIRMED.

```
not_assessed: LP-12 Early Termination, LP-23 Percentage Rent
```

Neither is in `ANNOTATED_BUCKETS`, so neither is a finding. Both are visible:

- **DOCX:** the Step-522 block — *"NOT ASSESSED — 2 provision(s) … LP-12 Early Termination [NOT
  ASSESSED] … LP-23 Percentage Rent [NOT ASSESSED]"*
- **PDF:** the "Not Assessed" section with its disclaimer that absence from the sections above means
  nothing was checked.

**The Step-522 requirement holds.** And note this is exactly why LP-23 must not be pulled into findings
by a `requires_attention` filter — it would appear twice, once as a finding and once as not-assessed,
asserting both that it was judged and that it was not.

---

# 4. ORDERING — AND WHY IT IS ALREADY ANSWERED, DIFFERENTLY THAN THE BRIEF ASSUMES

**The summary already orders by materiality** — `lease_report_generator.py:453-455`:

```python
                section_items = sorted(
                    [pair[0] for pair in section["items"]],
                    key=lambda it: mat_order.get(it.get("materiality", "medium"), 1),
                )
```
with `mat_order = {"high": 0, "medium": 1, "low": 2}`. **Worst first, within each section, already.**

**The margin has no meaningful global order and should not be given one.** Callouts are anchored to
clauses, so a reader meets them in document order as they read the lease. Sorting them would be
meaningless — they are not a list.

## The measurement that makes this decisive

Of butler_crossing's five high/medium-materiality LPs, **only one can reach the margin at all:**

```
LP-14  Force Majeure           high     missing         margin=NO   (absence: nothing to anchor)
LP-28  Compliance with Laws    high     missing         margin=NO
LP-31  Co-Tenancy              high     missing         margin=NO
LP-23  Percentage Rent         medium   broken_xref     margin=NO   (not_assessed)
LP-27  Landlord Default        high     review_needed   margin=YES
```

**The most material findings on this lease are absences, and an absence has no clause to annotate.**
That is why Step 541 observed nearly every callout reading *"(LOW materiality)"* — it is structural,
not a labelling bug.

**So "a lawyer reading twelve wants the worst first" is satisfied where it can be — in the summary,
which already sorts that way and which is where the high-materiality items live.** Reordering the
margin would not surface a single additional serious finding.

**No ordering change is proposed.** Materiality-first in the summary is correct and present; the margin
is positional by construction.

---

# WHAT IS NOT ESTABLISHED

- **Nothing was built.** The one behavioural change the brief requests is the addition of LP-23, which
  the same brief excludes; every other requirement was satisfied at Steps 538 and 539.
- **Four callouts are dropped silently** — `[docx_annotator] Could not anchor coverage gap for LP-21 /
  LP-22 / LP-29 / LP-32`. They survive in the summary so nothing is lost to a reader, but the annotator
  logs and discards without recording it on the result. **That is a real defect and deserves its own
  step**; it is not this one's subject.
- **Materiality was not re-examined.** Step 541 flagged `_classify_materiality` as suspect — LP-20
  exclusivity at `low` on a shopping-centre lease still looks wrong — and §4 shows the *distribution*
  is plausible (4 high, 1 medium, 27 low) without establishing that individual assignments are right.
- **One document.** All counts are butler_crossing's.
- **The DOCX carrier is `T-04_subtle.docx`**, not the real ex6-4 source, because the fixture is `.txt`.
  Anchor-failure counts are therefore specific to that carrier and would differ on the true document.
- **No panel verdict changed and the citation gate was not touched**, per the brief.
