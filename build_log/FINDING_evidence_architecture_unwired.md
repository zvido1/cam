# Finding: the non-exclusive evidence architecture has never run

**Date:** 2026-08-20
**Status:** RECORDED, NOT FIXED. No code, schema, or prompt changed.
**Severity:** The architecture built by Steps 423–428 to fix destructive exclusive assignment is
complete, tested, layering-checked — and not connected to the pipeline. The defect it remedies has
been live in production throughout.
**Method:** read-only. Import and call-site census across `cam/adapters/lease_review/` and
`05 Lease Analyzer/app/`.

---

## 1. Zero pipeline references

Every module that actually runs a lease review was grepped for the four stack modules
(`lease_evidence_spans`, `lease_segmentation`, `lease_element_elicitation`,
`lease_parameter_block`):

```
lease_adapter.py                 0 reference(s)
lease_coverage.py                0 reference(s)
lease_coverage_305.py            0 reference(s)
lease_use_aware_coverage.py      0 reference(s)
lease_extract.py                 0 reference(s)
app/main.py                      0 reference(s)
app/job_manager.py               0 reference(s)
```

Not "called conditionally", not "behind a flag" — **not mentioned**.

## 2. Every public function, and who calls it

Callers outside the function's own module, excluding tests:

```
build_canonical_source           lease_element_elicitation.py, lease_segmentation.py
resolve_span                     lease_element_elicitation.py, lease_parameter_block.py,
                                 lease_segmentation.py
resolve_spans                    NO PRODUCTION CALLER
is_usable_in_canonical_stage5    lease_element_elicitation.py, lease_segmentation.py
validate_span_against_source     NO PRODUCTION CALLER
propose_spans                    NO PRODUCTION CALLER
resolve_proposed_spans           NO PRODUCTION CALLER
build_span_universe_sidecar      NO PRODUCTION CALLER
elicit_spans_for_targets         lease_parameter_block.py
resolve_elicited_spans           NO PRODUCTION CALLER
dedupe_elicited_spans            NO PRODUCTION CALLER
elicit_and_resolve_for_lp        NO PRODUCTION CALLER
build_elicitation_sidecar        NO PRODUCTION CALLER
extract_parameters               (docstring mention only — lease_element_elicitation.py:94,
                                  a comment about the 428 failure, not a call)
attach_parameters_to_lp_evidence NO PRODUCTION CALLER
check_gate_b                     NO PRODUCTION CALLER
enforce_gate_b                   NO PRODUCTION CALLER
```

**Every caller listed is another module of the same stack.** The stack calls itself. Nothing
outside it calls in. The 423B entry points and the 427 Gate-B enforcement have no caller at all.

The remaining references are tests:

```
propose_spans, resolve_proposed_spans, build_span_universe_sidecar
    -> test_423b_lp_blind_segmentation.py only
elicit_and_resolve_for_lp, build_elicitation_sidecar
    -> test_423c_element_guided_elicitation.py only
extract_parameters
    -> test_427_parameter_block.py, test_429_target_resolution.py only
```

## 3. `lease_coverage.py:150` is the whole seam

What each LP's coverage evaluation sees is decided by one line:

```python
# ── Step 2: Find the extracted provision ──────────────────────────────
prov = provision_map.get(pid)
tenant_text = (prov.get("tenant_text", "") or "") if prov else ""
```

`provision_map` is keyed on extraction's `provision_id`. Plus the cross-LP map at `:83`:

```python
# Step 307b: build LP-text map for cross-LP text injection into 305 prompts.
# Maps LP ID → extracted tenant_text so evaluators can assess cross-LP elements.
all_lp_texts: dict = {
    p.get("provision_id"): p.get("tenant_text", "")
    for p in provisions
    if p.get("provision_id") and p.get("tenant_text")
}
```

**Everything the evaluators see comes from extraction's exclusive buckets, and there is no other
path in.** That is the mechanism behind
`build_log/FINDING_definitional_clause_loss.md`: the Proportionate Share definition is not in
LP-07's bucket, so LP-07 cannot see it, so the panel unanimously reports the calculation method as
undefined when the lease defines it.

## 4. Consequence

**The architecture built by Steps 423–428 to fix destructive exclusive assignment has never run.**

421C diagnosed the root cause on 2026-07-xx and voided the Step 417/419/420 baselines. 423A/B/C,
425, 427 and 428 were built in response. They are complete: LP-blind segmentation, element-guided
elicitation, an offset-addressed span substrate, canonical normalization v2, a parameter block with
Gate-B enforcement, and assignment-stability measurement. They have tests, including layering tests
that assert the dependency direction.

**None of it has ever executed against a real lease in the product.** Every production run since —
including the Atlas run of 2026-08-20 that produced a confident false finding — used the exclusive
extraction buckets the architecture was built to replace.

## 5. Same defect class as Step 452's `cmd_produce`

`build_log/452_PARK_RECORD.md` records that Step 452's production entrypoint was sealed as an
unconditional NOT AUTHORIZED path — the §4.10 21-step DAG specified, every Set-A producer defined,
and **none of them called**. Its headline:

> Step 452 proved the integrity of a program that was not wired to execute Step 452.

**This is the same defect, one layer over.** Written, tested, never wired.

Both passed every check because **no check asked whether the component was connected**:

- Step 452 had four gate records, a per-field producer-consumer census (72/72), a predicate
  reachability census, four-way token equality, a signed tag — and none of them asked whether
  `cmd_produce` had a body.
- The 423 stack has unit tests, integrity assertions, layering tests asserting import direction —
  and none of them asks whether anything outside the stack imports it.

A layering test proves the stack does not depend on the wrong thing. It cannot prove anything
depends on the stack. Both are "is this component internally correct?" questions asked of a
component nothing calls.

The park record's own requirement, generalised, is the missing check:

> Begin with a pre-ratification EXECUTION gate, not another prose gate… a synthetic invocation of
> the actual production entrypoint must demonstrably traverse the production DAG… Ceremony protects
> what already works; it cannot confer working.

## 6. What 423C already provides, and does NOT need

This matters for scoping the fix: **423C does not need restructuring.** It is already built for the
job.

**Document-scoped input.** `elicit_spans_for_targets(tenant_text, elements, …)` inserts the text
into the prompt directly, and both call sites pass the whole canonical document — never extraction
output:

```python
# lease_parameter_block.py:132
elicitation_result = elicit_spans_for_targets(
    canonical_source.canonical_text, elements, canonical=canonical
)

# lease_element_elicitation.py:519  (elicit_and_resolve_for_lp)
result = elicit_spans_for_targets(canonical_source.canonical_text, elements, canonical=canonical)
```

**LP-blindness at the search level**, by construction:

> The model receives a neutral, ordinal target list built from each element's
> `element_label`/`synonyms` — never `element_id`, never an LP identifier. Returns raw
> `target_matches` (still keyed by "Target N") … Mapping "Target N" back to `element_id` … happens
> afterward, in `resolve_elicited_spans` — never inside this function.

**Offset-keyed dedupe with `elicited_by` as a union** — multi-source spans are already the design:

> Two records are the SAME span if and only if both are `verified` and their
> `(start_char, end_char)` are identical. Merging combines `elicited_by` (union, order-preserving,
> first-seen order) and `quote_variants` (union) into one record with one fresh
> `evidence_span_id`.

and explicitly anticipating cross-LP union:

> callers combining multiple LPs should pass all raw records from all calls through one
> `dedupe_elicited_spans` call so cross-LP duplicates collapse too.

So a span found for two different issue areas already collapses to one record carrying both
provenances. **A union of spans from two sources is already supported.**

## 7. What the work actually is

Not "extend the architecture upstream" — the architecture exists and is document-scoped already.
The work is **the seam and its downstream consumers**:

1. Replace `lease_coverage.py:150` — one assignment reading one bucket — with span-based evidence
   assembly for the LP.
2. Update every consumer of that shape: `all_lp_texts` (`:83`), the 305 prompt builder's
   `tenant_text` parameter, negative-space detection, and the extraction completeness gate, which
   currently measures presence of a bucket rather than presence of evidence.
3. Decide what the gate means once evidence is non-exclusive — the current `fail_missing` test is
   `empty tenant_text`, which has no obvious analogue when a span set is the unit.

The smallest diff is at the seam. The cost is in the consumers.

## What is NOT established

- Whether the 423 stack works end-to-end on a real lease. It has never been run on one; the tests
  use fixtures.
- What the span-based assembly should return — a concatenation, an ordered span list, or a
  structured evidence object. Not designed here.
- Whether Gate B (`check_gate_b`/`enforce_gate_b`, 427) is the right gate once wired, or whether it
  duplicates the completeness gate. Both are currently unreferenced by the pipeline.
- Whether wiring it changes the LP-07 result. Plausible, unmeasured.
