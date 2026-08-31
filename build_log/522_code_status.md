# Step 522 — assessment_status built, fail-closed, at eight sites. 2 not_assessed on Atlas, not 5.

**Date:** 2026-08-31 · **Instruction:** `build_log/522_chat_instruction.md`
**Tests: 379 passed, 3 skipped, 12 subtests — 10 of them new and all executing the real loop.**
**One Atlas run: 97 calls, 829.9s, 32 entries — 30 assessed, 2 not_assessed, 0 suppressed, 0 unset.**
**Not deployed.**

---

# 0. THREE PREMISES CORRECTED

**"Emit at all four sites."** There are **eight** `_build_assessment` call sites, enumerated in Step 521
and re-confirmed here. All eight are wired.

**"Step 497 saw the citation gate fire on LP-27."** I could not find this. Every LP-27 presence verdict
in the Step-517 run carries `citation_quality = section_and_quote`, `coverage_method =
step_305_per_element`; Step 497's status contains no citation gate, only *"Nothing is silently
suppressed"* about `panel_substitution` tiers. The citation rule that exists is **element-level**
(`lease_coverage_305.py:267` — a presence verdict without `section_ref` becomes `unclear`) and never
produces an LP-level suppression. **`suppressed` was therefore mapped onto a mechanism that does
exist** — see §2.

**"The DOCX numbers requires_attention entries."** It does not. The DOCX summary section renders the
Mode A deviation shape and has no coverage listing at all (Step 521 §Q4). There was nothing to be
absorbed into; there was nothing there.

---

# 1. EMISSION — EIGHT SITES, FAIL-CLOSED

`_build_assessment(..., assessment_status="unset")` — `lease_coverage.py:1034`, emitted at `:1051`.

| # | line | route | value |
|---|---|---|---|
| R1 | 390 | applicability `excluded`/`not_applicable` | `not_assessed` |
| R2 | 405 | applicability `unclear` → `default_when_unclear` | `not_assessed` |
| R3 | 440 | extraction status `NOT_APPLICABLE` | `not_assessed` |
| R4 | 474 | reserved/omitted signal | `not_assessed` |
| R5 | 512 | no tenant text | `not_assessed` |
| R6 | 531 | global-scan deterministic path | `assessed` |
| R7 | 604 | **Step 305 panel** | `assessed` |
| R8 | 660 | legacy path | `_status_legacy` |

## The absent case, and why it is a fourth value

**The default is `"unset"`, never `"assessed"`.** A route that forgets must not have the schema claim a
judgment nobody made — that is the defect the field exists to prevent, so forgetting has to be *loud*,
not *clean*.

`_resolve_display` treats **anything that is not `"assessed"`** — including a missing key — as
unjudged. That makes the fail-closed property hold for **results produced before this field existed**:
every pre-522 result now renders as unrecorded rather than being silently promoted to a clean verdict.
A fail-open default would have quietly certified every historical run.

`unset` is surfaced exactly as loudly as `not_assessed`: same bucket, same section, label
**"ASSESSMENT STATUS NOT RECORDED"**.

---

# 2. `suppressed` — GROUNDED IN A REAL MECHANISM

R8 is reached two ways: normally, and **when the 305 panel raises** —
`except Exception as _e_305: ... falling through to legacy path`. Those are different facts. In the
second, evaluators ran and their product was thrown away, and **before this step nothing on the
assessment recorded it** (Step 521, R8).

`_status_legacy` is `"assessed"` by default and set to `"suppressed"` in that handler.
`test_R8_panel_raising_is_suppressed_not_assessed` monkeypatches `assess_coverage_305` to raise and
asserts the emitted value.

---

# 3. PROOF BY EXERCISE — TEN TESTS, ALL DRIVING THE REAL LOOP

`cam/adapters/lease_review/tests/test_522_assessment_status.py`

```
test_default_is_unset_not_assessed                        PASS
test_every_entry_carries_the_field                        PASS
test_no_entry_is_silently_unset_in_a_real_pass            PASS
test_R1_R2_applicability_routes_are_not_assessed          PASS
test_R3_extraction_not_applicable_short_circuit           PASS
test_R4_reserved_or_omitted_is_not_assessed               PASS
test_R5_missing_evidence_is_not_assessed_despite_...      PASS
test_R8_panel_raising_is_suppressed_not_assessed          PASS
test_requires_attention_keeps_its_boolean_contract        PASS
test_summary_counts_not_assessed_fail_closed              PASS

379 passed, 3 skipped, 12 subtests passed
```

**R7 was exercised by the live Atlas run** (30 entries `assessed`). **R6 was NOT exercised** — the
global-scan path needs a document that misses extraction and hits the scan, and I did not construct
one. Its value is read from the call site, not observed. Stated rather than glossed.

`requires_attention` keeps its boolean contract: `test_requires_attention_keeps_its_boolean_contract`
asserts `isinstance(..., bool)` on every entry, so the `lease_exposure:523` truthiness test cannot be
broken later without a red test.

---

# 4. DISPLAY

**`_resolve_display` checks `assessment_status` BEFORE any `coverage_state` branch.** Step 521 measured
`not_applicable`, `applicability_unclear`, `review_needed`, `ambiguous` and `partial_typical` all
falling through to `COVERED ✓`; status now outranks state, because a conclusion nobody reached is not a
conclusion.

New bucket `not_assessed` — slate `#475569`, deliberately neither green nor amber: this is an absence
of information, not a risk grade.

| surface | treatment |
|---|---|
| summary cover PDF | own **"Not Assessed"** section, own slate tier colour, own count in the Findings line |
| annotated PDF | same — `generate_outputs` prepends the cover to every `.pdf` output (`lease_report_generator.py:725-727`) |
| annotated DOCX | new summary block listing each entry with its label |
| batch summary | counted as its own bucket, phrase **"NOT ASSESSED"** |
| synopsis / `resolve_sections` | own section, before "Covered", all three perspectives |
| API | `summary.not_assessed` |
| web | routed to the existing `review_needed` — see §6 |

**Per-item labels are restored for this bucket only.** Step 279 dropped per-item state labels because
the section header carries the category; that reasoning fails here, because this one section holds two
different facts. `_render_coverage_item` now prints `[NOT ASSESSED]` / `[ASSESSMENT DISCARDED]` /
`[ASSESSMENT STATUS NOT RECORDED]`.

**The schema's exposure prose and `Missing: <elements>` list are suppressed for these entries.**
Printing them would assert the R4/R5 "verdict nobody voted on" — a named finding with no evaluator
behind it. A reason line replaces them.

---

# 5. THE EXERCISE — FOUR KINDS, QUOTED

Result built from the real Step-517 Atlas run with four kinds present.

**Summary cover PDF:**

```
Findings
2 issue area(s) require attention, 0 worth reviewing, 3 NOT ASSESSED, 27 covered.

Coverage & Gaps
LP-05 Permitted Use -- No restriction on how tenant uses space
Missing: Specific permitted use description is stated, Continuous operation obligation is addressed, ...

Not Assessed
The following provisions were NOT evaluated. They are not findings and they are not clean bills of
health -- no judgment was reached about them, so their absence from the sections above means nothing
was checked, not that nothing was wrong.
LP-27 Landlord Default & Tenant Remedies  [ASSESSMENT DISCARDED]
An evaluation was attempted and its result was discarded; the state shown elsewhere does not rest on it.
LP-23 Percentage Rent  [NOT ASSESSED]
No evaluation was performed for this provision.
LP-31 Co-Tenancy  [NOT ASSESSED]
No evaluation was performed for this provision.
```

**Annotated DOCX** (`T-04_subtle.docx` + the same result):

```
NOT ASSESSED — 3 provision(s)
These provisions were not evaluated. They carry no margin callout below, and that absence means
nothing was checked — not that nothing was wrong.
LP-23 Percentage Rent  [NOT ASSESSED]
LP-27 Landlord Default & Tenant Remedies  [ASSESSMENT DISCARDED]
LP-31 Co-Tenancy  [NOT ASSESSED]
```

**assessed-and-clean (LP-13, `covered`)** appears in neither — it is inside the `27 covered` tally. The
"Covered" tail is omitted from the cover by pre-existing design (`lease_report_generator.py:374`), and
Step 522 did not change that.

**All four are distinguishable without knowing the schema:** a named gap with its missing elements; a
bracket label saying the assessment was discarded; a bracket label saying none was performed; and a
count.

---

# 6. TWO DEFECTS FOUND BY RUNNING, BOTH MINE

## 6.1 The batch summary crashed

Adding `not_assessed` to `BUCKET_ORDER_BY_PERSPECTIVE` made
`parts = [f"{bucket_counts[b]} {bucket_phrase[b]}" for b in order]` raise **`KeyError`** —
`bucket_phrase` had no entry. **Found by running the generator, not by reading it.** Fixed; the missing
key is now what forces any future bucket addition to be handled here.

## 6.2 My first web change would have made the entries vanish

I initially returned a new `'not_assessed'` bucket from `classifyFindingType`. Every downstream
consumer (`app.js:4749-4751`, `:4787-4796`, and the `:18430`-`:18506` group) is an if/else-if chain
over `risk` / `review_needed` / `improvement`. **A novel value falls through all of them and the entry
disappears from the page entirely** — trading a false all-clear for a silent omission, which is not an
improvement.

Reverted to the existing `review_needed`, which is handled everywhere. `app.js?v=474`.

---

# 7. THE ATLAS RUN — 2 NOT_ASSESSED, NOT 5

```
build_log/runs/522_atlas-modec_20260831_144914
calls=97   elapsed=829.9s   degraded=False   stubs=0   contradictions=0

assessment_status: {'assessed': 30, 'not_assessed': 2}   suppressed=0   unset=0

LP-23  Percentage Rent   status=not_assessed  state=not_applicable  appl=unclear  -> NOT ASSESSED
LP-31  Co-Tenancy        status=not_assessed  state=not_applicable  appl=unclear  -> NOT ASSESSED
```

**The brief expected 5 of 33 against "Step 521's LP-12/16/23/29/31". The measured answer is 2 of 32,
and Step 521 does not contain that list.** Step 521 measured **LP-23 and LP-31** on Atlas — exactly
these two — and a separate set of nine on **divall** (LP-01, LP-02, LP-16, LP-20, LP-21, LP-29, LP-30,
LP-31, LP-32). LP-12 appears in neither. The expectation appears to merge the two runs.

**Independent corroboration:** the set of entries with zero `element_verdicts` is `['LP-23', 'LP-31']`
— identical to the `not_assessed` set. The field agrees with a measure computed without it.

**Rendered from the real run:**

```
Findings
3 issue area(s) require attention, 0 worth reviewing, 2 NOT ASSESSED, 27 covered.
```

Against the Step-521 pre-fix baseline on the Step-517 run — *"3 issue area(s) require attention, 0
worth reviewing, 29 covered"* — the two unjudged entries have left the covered tally and are named.

**`suppressed = 0`**, consistent with `fallback_event_count = 0`: the 305 panel did not raise on this
run.

---

# WHAT IS NOT ESTABLISHED

- **The 27-vs-3 gap is UNCHANGED and still open.** `summary.requires_attention = 27`; the PDF still
  says *"3 issue area(s) require attention."* That is Step 521's item (C), and this step did not touch
  it. **22 `partial_typical` and 3 `review_needed` LPs still render `COVERED ✓`** — including a
  dispute-triggered, high-materiality withheld verdict. **`assessment_status` does not fix that,
  because those entries WERE assessed.** It was never the same defect.
- **R6 was not exercised.** Its value is read from the call site.
- **The web surface was not exercised** — no browser, no test. `review_needed` is correct-in-kind but
  the per-LP label does not yet say *which* kind of review. `app.js?v=474` is a syntax check only.
- **`suppressed` has never been observed on a live run** — only in a monkeypatched test. Its real
  trigger is a 305 exception, which did not occur here.
- **`unset` has never been observed** either, by design; a full pass asserts none is emitted.
- **One Atlas run, one fixture.** 2-of-32 is evidence about atlas.
- **The per-tenant summary DOCX still renders no coverage for Mode C** (Step 521 §Q4). Out of scope
  here; the mode branch is unbuilt and `"Deviations found: 0"` still appears on Mode C runs.
- **Not deployed.**
