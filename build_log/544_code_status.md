# Step 544 — The citation gate has never fired. Not once, on any run, on any document. The overwrite is real, and something else does it.

**Date:** 2026-09-03 · **Instruction:** `build_log/544_chat_instruction.md`
**DIAGNOSTIC. No code changed. Tests: 406 passed, 3 skipped, 12 subtests. Not deployed.**

---

# 0. THREE PREMISE CORRECTIONS FIRST, BECAUSE THEY RELOCATE THE DEFECT

**`_apply_citation_gate` does not exist.** `grep` across the whole repository returns nothing. The real
mechanism is an inline block in `merge_element_verdicts`, `lease_coverage_305.py:1063-1079`.

**`covered_favorable` is not a coverage state.** It appears in exactly two places, both cosmetic:

```
05 Lease Analyzer/static/app.js:7897:  covered_favorable: 'Favorable', covered_unfavorable: 'Unfavorable',
05 Lease Analyzer/static/style.css:11895: .ev-state-covered_favorable { background: #dcfce7; ... }
```

**No Python ever produces it.** So LP-20 cannot have had a `covered_favorable` verdict replaced.

**The gate operates on ELEMENTS, not on LP verdicts.** It can never "replace an LP verdict" directly.
Its only output is one element verdict → `unclear`, which then reaches the LP through
`derive_lp_state`. That indirection matters for everything below.

---

# 1. THE COUNT: ZERO. ACROSS 1,111 ELEMENTS AND SIX RUNS.

Census of merged `reason` on every element of every completed Mode C run in `build_log/runs/`:

```
## ex6-4 / butler_crossing   LPs=32 elements=196
   merged-reason census: {'distant_split_presence_missing': 18, 'no_consensus': 7}
   GATE FIRINGS: 0
## solidpower (528)          LPs=32 elements=173
   merged-reason census: {'no_consensus': 5, 'distant_split_presence_missing': 17}
   GATE FIRINGS: 0
## solidpower (525)          LPs=32 elements=179
   merged-reason census: {'no_consensus': 3, 'distant_split_presence_missing': 17}
   GATE FIRINGS: 0
## atlas (524)               LPs=32 elements=202
   merged-reason census: {'distant_split_presence_missing': 18, 'no_consensus': 2}
   GATE FIRINGS: 0
## atlas (522)               LPs=32 elements=202
   merged-reason census: {'distant_split_presence_missing': 19, 'no_consensus': 1}
   GATE FIRINGS: 0
## divall (496)              LPs=32 elements=159
   merged-reason census: {'distant_split_presence_missing': 18, 'no_consensus': 3}
   GATE FIRINGS: 0
```

**`citation_required_but_absent` appears zero times.** Per document: ex6-4 **0**, solidpower **0**,
Atlas **0**, divall **0**. There are no LPs to list and no original verdicts to report, because nothing
was overwritten.

**This is not a persistence artefact.** The `reason` field is written and survives — two *other* reason
codes are present in the same records, 130 times across the six runs. The gate's code simply never took
its branch.

## quanterix has no coverage run at all

`build_log/runs/` contains no quanterix Mode C run. Its only record is
`529_extract-only.../run_03_full.json`:

```json
{"fixture": "quanterix_crosby_bedford_lease.txt", "doc_chars": 224528, "provisions_emitted": 33, ...}
```

**Extraction only — the panel never ran on it, so the gate could not fire and no locator rate for it
exists in our records.** I substituted divall, which has a completed run at the low end of the locator
range.

## Why it never fires — the evaluators self-police, and the gate needs unanimity to lose

`lease_coverage_305.py:267`, hard rule 5 in the evaluator prompt:

> *"Any presence verdict (explicitly_present, implicitly_present, covered_by_default_law,
> covered_in_other_LP) requires section_ref in the citation. If section_ref is null, use unclear
> instead."*

Measured compliance:

```
document                 evalPresence  noSecRef    rate | mergedPresence  withCite
ex6-4/butler_crossing             394         3    0.8% |            120       120
solidpower(528)                   370         3    0.8% |            115       115
atlas(524)                        434         4    0.9% |            136       136
divall(496)                       261         2    0.8% |             80        80
```

**Every merged presence verdict on all four documents carries a section_ref — 451 of 451.** Individual
evaluators omit one about 0.8% of the time, and the gate requires that the *entire majority cohort*
omit it simultaneously. That has not happened.

---

# 2. WHAT THE GATE PROTECTS AGAINST — quoted, and it is a patent claim, not a heuristic

**Code comment**, `lease_coverage_305.py:1063`:

> `# Citation-or-it-didn't-happen check (architecture spec §6)`

**Module docstring**, `lease_coverage_305.py:21`:

> *"Claim 7: element-level unclear routes to review_needed; citation-absent downgrades presence"*

**System prompt**, `lease_coverage_305.py:232`:

> *"Any material element-level assertion without a supporting citation must be downgraded to `unclear`
> or `review_needed`. Citation may be a section number reference or a quoted text fragment; bare
> assertions of presence without textual grounding do not constitute valid assertion."*

**`Docs/Step_305_Architecture.md:167`:**

> *"If the majority verdict is `explicitly_present` … but the merged citation is null or invalid:
> downgrade to `unclear`. Enforces the citation-or-it-didn't-happen rule at the merge layer."*

**`Docs/Step_305_Architecture.md:228`:**

> *"The citation-or-it-didn't-happen rule is a Claim 7 instance at the verdict layer: a verdict without
> supporting evidence is structurally downgraded to abstention rather than asserted with false
> confidence."*

## The brief's distinction is correct, and the gate cannot make it — but it also never has to

The brief separates *"no citation at all"* from *"a citation naming a section our heading index cannot
parse."* **The gate tests only the first.** Its entire test is:

```python
        valid_citations = [
            c for c in majority_citations
            if c and c.get("section_ref")
        ]
```

**A truthiness check on a string the evaluator wrote.** It never asks whether that string resolves. So
the gate is structurally incapable of confusing the two failures — it is blind to the second one
entirely.

---

# 3. NO CORRELATION WITH THE LOCATOR — AND THE MECHANISM SAYS WHY

Recomputed against the run artefacts (same method as Steps 525/537: non-null `section_ref` on element
citations, resolved via `_resolve_section_excerpt` against `full_tenant_text`):

```
document                  refs  resolve    rate   GATE
ex6-4/butler_crossing      120       54   45.0%      0
solidpower(528)            115       19   16.5%      0
atlas(524)                 136      114   83.8%      0
divall(496)                 80        2    2.5%      0
```

**A 33-fold range in locator resolution and zero variance in gate firings.** There is no correlation to
measure.

**And there could not be, because the two live in different modules with no data path between them.**
`_resolve_section_excerpt` is defined at `lease_finding_consequence.py:224` — the 408C consequence pass
— and its only consumer is `:350`, where its sole effect is whether cited section text is added to a
*later prompt*:

```python
        input_source_map[fid] = "section_text+tenant_text" if has_section_text else "tenant_text_only"
```

**It runs after the panel and never touches an element verdict.** So the answer to the brief's question
is: the gate is not measuring our parser — it is not measuring anything, because it never runs.

**Note on the brief's figures.** *"Atlas 99%, ex6-4 45%, quanterix 0.6%"* mixes two incompatible
metrics. 99% and 0.6%/7.2% are Step 479's, over 1,758 and 305 refs, and **Step 525 recorded that those
numbers have never been reproduced.** The 45% is this method's. The four rates above are internally
consistent and comparable only to each other.

---

# 4. WHAT THE READER SEES — the brief's worry is real, LP-20 is not the case, and the cause is disagreement

## LP-20 on ex6-4 was never touched by the gate, and its display is correct

```
LP-20 Exclusivity
  coverage_state             review_needed
  coverage_state_baseline    review_needed        <- identical: no override of any kind
  per_evaluator_lp_verdicts  {'C': 'missing', 'A': 'missing', 'B': 'missing'}
  dispute_signal.triggered   False
  ELEMENTS (7):
    exclusive_use_scope          missing    reason=None      ['C=missing','A=missing','B=missing']
    existing_tenant_carveouts    missing    reason=None      ['C=missing','A=missing','B=missing']
    incidental_use_carveouts     missing    reason=None      ['C=missing','A=missing','B=missing']
    radius_restriction           disputed   reason=distant_split_presence_missing
    competing_use_definition     unclear    reason=no_consensus   ['C=missing','A=unclear','B=explicitly_present']
    exclusivity_duration         missing    reason=None      ['C=missing','A=missing','B=missing']
    remedies_for_violation       missing    reason=None      ['C=missing','A=missing','B=missing']
```

**Not one element ever reached a presence majority, so the gate's precondition
(`majority_verdict in PRESENCE_VERDICTS`) was never met.** All three evaluators independently said
`missing` at LP level. This confirms Step 539 §0, which reached the same conclusion.

**And as displayed today it does not read as a citation artefact:**

```
LP-20 display: {'bucket': 'needs_attention', 'label': 'NO ELEMENTS FOUND', 'tone': 'warning'}
       headline: "Exclusivity protection absent or undefined"
```

**Step 538's evidence guard already routes it to the substantive finding.** The reader is told the
provision is absent, which is what the panel unanimously found.

## The overwrite the brief describes is real — one document over, and the input is `no_consensus`

`derive_lp_state`'s **first branch** is an absolute veto (`lease_coverage_305.py:1150`):

```python
    if any_unclear:
        return "review_needed"
```

One `unclear` element outranks every other element in the LP. Across the four documents, 24 LPs land in
`review_needed`; **17 unclear elements drive them and all 17 carry `reason: no_consensus`. Zero carry
`citation_required_but_absent`.**

**Four LPs — one per document — would be `covered` but for a single disagreed element:**

```
ex6-4      LP-25  Condemnation / Eminent Domain  1 unclear of 7   panel LP: C/A/B all explicitly_present
           headline: "Condemnation rights are undefined"
           unclear: LP-25.total_vs_partial_taking  evals=['missing','explicitly_present','unclear']
atlas      LP-26  Quiet Enjoyment                1 unclear of 7   panel LP: C/A/B all explicitly_present
           headline: "Quiet enjoyment covenant absent or undefined"
           unclear: LP-26.constructive_eviction_addressed  evals=['covered_in_other_LP','unclear','unclear']
solidpower LP-01  Rent & Payment Terms           2 unclear of 6   panel LP: C/A/B all explicitly_present
divall     LP-23  Percentage Rent                2 unclear of 5   panel LP: C/B explicitly_present, A unclear
```

**Atlas LP-26 is the clearest case: all three evaluators found the quiet-enjoyment covenant explicitly
present, and the report headline says it is "absent or undefined."** That headline is false about the
document. ex6-4's LP-25 is the same shape. LP-11 Default & Remedies on ex6-4 shows the magnitude —
**15 of 17 elements `explicitly_present`, one unclear, and it reads `REVIEW NEEDED` under the headline
"Default and remedy framework absent or incomplete."**

**So the brief's concern is sound and the diagnosis needs to move: the flag is an artefact of evaluator
disagreement on one sub-element, not of citation quality, and it is not on LP-20.**

## Does the original verdict survive? In the artefact yes. On any reader surface, no.

**In the result JSON it survives three times over:** `per_evaluator_lp_verdicts` carries each
evaluator's LP-level verdict; every element keeps its full `evaluator_verdicts` array; and
`coverage_state_baseline` is retained beside `coverage_state`.

**No reader surface shows any of them.** `per_evaluator_lp_verdicts` is written at
`lease_coverage.py:623` and read only by `05 Lease Analyzer/_step372_decomp.py`, an analysis script —
**no report generator, no annotator, and no line of `app.js` reads it.** A lawyer reading "Quiet
enjoyment covenant absent or undefined" has no way to reach the fact that all three evaluators said it
was explicitly present.

**Had the gate fired, the same would hold with one improvement:** its return preserves the full panel in
`"disagreements": verdicts`, so the suppressed majority would be recoverable from the JSON — and equally
invisible to a reader.

---

# WHAT IS NOT ESTABLISHED

- **quanterix was not measured.** No coverage run exists for it; nothing in this report covers that
  document, and its "0.6%" locator rate is not a figure this project has ever produced.
- **Zero firings is a statement about six runs on four documents, not a proof.** The gate is live code
  and a document whose evaluators all omit `section_ref` on the same element would trigger it. Nothing
  here says it *cannot* fire — only that it never has.
- **I did not measure whether the 0.8% of citations lacking `section_ref` are correct omissions.** They
  cluster on `LP-17.claims_time_limit`, `LP-18.notice_to_terminate_holdover` and `LP-32.*`, mostly from
  evaluator C, but I did not read the underlying lease text to judge them.
- **`no_consensus` was not audited for correctness.** I established that it, not the citation gate,
  drives the review_needed veto. Whether the individual disagreements are reasonable — LP-26's
  `['covered_in_other_LP','unclear','unclear']` in particular — needs a reading of the clauses, not a
  census.
- **The exposure headlines were not traced to their producer.** I report that "Quiet enjoyment covenant
  absent or undefined" contradicts the panel; I did not open the code that composes it.
- **Six review_needed LPs have zero unclear elements** (ex6-4 LP-03/LP-29, solidpower LP-14/LP-22,
  atlas LP-14/LP-22/LP-28, divall LP-24/LP-29). Two routes account for them —
  `if not element_results: return "review_needed"` for the empty ones, and the Supplement #21 Phase 3
  override at `lease_coverage.py:571` (`elements_disputed_critical > 0`). **Also disagreement-driven,
  also not the citation gate**, but I did not attribute each of the six individually.
- **No fix was made and none is proposed here**, per the brief.
