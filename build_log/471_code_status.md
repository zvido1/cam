# Step 471 — Citation gate: presence versus meaning

**Date:** 2026-08-23 · **Instruction:** `build_log/471_chat_instruction.md`
**DIAGNOSTIC ONLY.** No fix, no runs, no schema or code change. Computed offline over the four
persisted runs (`s457_r1`, `s457_r3`, `s468_r1`, `s468_r2`) — 33 LPs, **1,775 non-null `section_ref`
values**, 788 element merges.

**Method note:** the merge was replicated offline and validated **788/788 against stored verdicts**
before any counterfactual. Heading index = the 89 line-anchored headings in the canonical Atlas text
(65 `Section N.N`, 24 `ARTICLE N`).

---

## Headline — the gate is weaker than it should be, but the exposure is small and localised

**1,758 of 1,775 non-null `section_ref` values (99.0%) name a heading that actually exists.** The
17 that do not are almost entirely `covered_by_default_law`. Requiring resolution would change
**1 merged verdict in 788 (0.13%)**.

**The two earlier findings stand, but they are narrower than they looked.** The `'Paragraph 1'` route
(Step 460) was measured *before* the locator prefix existed and does not appear in these four runs at
all; the `'Default statute of limitations law'` route (Step 470) is real and is essentially the whole
of the residue.

## Q1 — Resolution rates

| class | count | share |
|---|---|---|
| **resolves** — every section token names a real heading | **1,758** | **99.0%** |
| partial — some tokens real, some not | 0 | 0.0% |
| non-resolving — has section tokens, none exist | 0 | 0.0% |
| **unparseable** — no section-like token at all | **17** | **1.0%** |

By verdict class:

| verdict | total | resolves | unparseable |
|---|---|---|---|
| explicitly_present | 1,478 | **1,478** | 0 |
| implicitly_present | 140 | **140** | 0 |
| missing | 68 | 68 | 0 |
| unclear | 35 | 35 | 0 |
| covered_in_other_LP | 36 | 32 | **4** |
| **covered_by_default_law** | **18** | **5** | **13** |

**Every presence verdict on lease text resolves. The failures are concentrated in the two verdict
classes that are not about lease text** — `covered_by_default_law` (72% unparseable) and
`covered_in_other_LP` (11%).

### Beyond the brief: does the quote sit in the section it cites?

"Resolves" only means the heading exists. Testing containment (ellipsis-aware — evaluators elide with
`...`, and a naive substring test mislabels those as fabrication):

| | count | share |
|---|---|---|
| **quote inside the cited section** | **1,716** | **98.2%** |
| **real section, but the quote is elsewhere in the lease** | **0** | **0.0%** |
| no fragment found in the lease (paraphrase / reconstruction) | 20 | 1.1% |
| quote too short to test | 11 | 0.6% |

**Zero cases of naming a real-but-wrong section.** The 20 residual are paraphrases — reordered or
smart-quoted reconstructions rather than verbatim — e.g. LP-01 `Section 3.2`, LP-22 `Section 19.2`.
That is a separate (and much smaller) issue from the one this step was asked about.

## Q2 — The 17 non-resolving, categorised

**Prose restatement of the verdict — 11 (all `covered_by_default_law`):**

```
'Default statute of limitations law'                    LP-17
'Default law; jurisdiction-dependent'                   LP-26
'Applicable default statute of limitations'             LP-17
'Default law - applicable statutes of limitation'       LP-17
'Default law (jurisdiction-dependent; governing law not specified)'   LP-27
'Default law; governing law not specified'              LP-09
'Default law/statute of limitations'                    LP-17
'Default law; jurisdiction-dependent equitable remedies' LP-27
'Default law - applicable environmental reporting laws' LP-32
'Default law - continuing environmental liability'      LP-32
```

**Cross-LP reference — 4:** `'LP-31'` on `LP-05.co_tenancy_anchor_dependency`, verdict
`covered_in_other_LP`. Names an issue area, not a document location. **Arguably correct behaviour** —
the prompt tells evaluators the citation *"must name the other LP and its section"*, and this names
the LP but omits the section.

**Other — 2:** `'Default environmental reporting law'`, `'Default environmental liability law'`
(LP-32). Same shape as the prose restatements.

**Invented locator — 0 in these four runs.** The `'Paragraph 1'` / `'Proportionate Share definition'`
class from Step 460 predates the locator prefix and does not recur.

## Q3 — Span path vs bucket path: parity

| population | n | resolves | rate | unparseable |
|---|---|---|---|---|
| **SPAN path** (LP-07, LP-27) | 164 | 162 | **98.8%** | 2 |
| **BUCKET path** (other 31 LPs) | 1,611 | 1,596 | **99.1%** | 15 |

**No material difference.** The interesting part is the comparison to *before* the locator prefix:
Step 460 measured **0 of 30** LP-27 citations carrying a resolvable `section_ref` on the span path.
**The locator prefix took the span path from 0% to parity with the bucket path.** That is the clearest
evidence yet that the Step-455 change did what it was built to do.

Both of LP-27's two residual failures are B's `covered_by_default_law` prose — the Step-470 route, not
a span-path defect.

## Q4 — Yes, computable; the merge needs one thing it does not have

The check itself is trivial and fully deterministic: parse `\d+\.\d+` tokens (and `Article N`) out of
`section_ref`, test membership in the heading index. No model call, no ambiguity, ~µs per citation.

**What is missing is the document.** `merge_element_verdicts(verdicts, element)` at
`lease_coverage_305.py:922` receives only the verdict list and the element dict. **The module holds no
lease text at all** — grep for `full_tenant_text` / `canonical_text` / `build_canonical_source` in
`lease_coverage_305.py` returns **0 hits**. `tenant_text` appears only as a prompt-building parameter,
and it is the *provision* text, not the whole document, so it cannot supply the heading index for
cross-LP citations.

So the requirement is: **build the heading index once from the canonical source and thread it to the
merge** — either as a parameter or via the `cfg` dict already passed to the evaluator layer. That is a
signature change through the call chain, not a local edit. Note also that the index already exists in
`lease_coverage.py` (`_build_heading_index`), so the logic would be shared, not duplicated — but that
is currently the *seam's* helper, and using it here would couple the 305 evaluator to it.

## Q5 — Applying the check: 1 merged verdict changes in 788

```
s468_r1   LP-17   LP-17.claims_time_limit
          covered_by_default_law  ->  unclear (citation_required_but_absent)
```

**0.13% of merges. One LP affected.**

That is the whole cost on this fixture — because the only merged verdict that currently *rests* on a
non-resolving citation is that one. The other 16 non-resolving citations belong to evaluators who were
outvoted, or whose element merged on a different evaluator's resolvable citation.

**The check would be near-free and would do almost nothing here.** Its value is not the verdicts it
changes today but the class of failure it forecloses: on this fixture, presence verdicts on lease text
resolve 100% of the time, so the gate has nothing to catch — but nothing currently *prevents* the
Step-460 `'Paragraph 1'` behaviour from recurring on a document where the locator prefix fails to
resolve a section, and that is exactly when it would matter.

## The question asked

**Yes — "the citation must resolve" is a deterministic constraint the pipeline could enforce.** It
costs a heading index threaded into the merge, and on this fixture it changes one verdict in 788.

**But it does not address either false positive.** Elements 6 and 7 cite `Section 11.2` and
`Section 5.1` — both real, both containing the quoted text, both resolving perfectly. **A resolution
check tests that a citation points somewhere real. It cannot test whether what it points at supports
the claim.** That remains the operative-entailment problem, and this constraint does not touch it.

## What is NOT established

- Generalisation. One lease, one heading convention (`Section N.N` at line start), 1,775 citations.
  A document whose headings the index cannot parse would show a very different resolution rate — and
  would also degrade the locator prefix, so the two failures are correlated, not independent.
- Whether the 4 cross-LP `'LP-31'` citations *should* fail such a check. The prompt asks for LP + section;
  a resolution check as specified would reject them, which may be wrong.
- Whether the 20 paraphrase quotes matter. Not investigated beyond counting.
- Whether threading the index into the merge has side effects on the other consumers of
  `merge_element_verdicts`. Not traced.
