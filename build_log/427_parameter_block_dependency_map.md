# Step 427 — Named Parameter Block + Declared Dependency Map

**Date:** 2026-07-14
**Status:** COMPLETE — built and tested, NOT wired into the live pipeline

---

## The Question This Step Exists to Answer

**Does LP-07's evidence context now contain the 100% tenant share?**

**Yes.** Run against the real Atreca lease, under `canonical_v2`
(`source_document_hash=7118cc6ddf65bd7b09f436071f02c431bacc14b2a7c66bb9f84f8335ded0b03b`),
`attach_parameters_to_lp_evidence(parameters, "LP-07")` returns two
`Parameter` objects. Quoted directly, not characterized (CLAUDE.md Rule 6):

```
tenant_share:
  verification_status: verified
  offsets: [1942, 1996)
  span_text: "Tenant's Share of Operating Expenses of Building: 100%"

building_share:
  verification_status: verified
  offsets: [1997, 2032)
  span_text: "Building's Share of Project: 45.79%"
```

`canonical_text[1942:1996]` and `canonical_text[1997:2032]` were checked
against `span_text` directly and are byte-identical (`match: True` for
both, printed by the demonstration run below). This is the first time in
this project's record that LP-07's evidence context contains this figure
— not in any of the 101 Gemini-primary pipeline runs, not in the Atlas
validation corpus (421C §2c), not once before this step.

Gate B, run against this same extraction: `{'gate_status': 'pass',
'failures': []}`.

---

## What Was Built

New module: `cam/adapters/lease_review/lease_parameter_block.py`. Not
wired into `lease_adapter.py` or `lease_coverage.py` in this slice — see
"What Remains Unwired" below for why.

### 1. Parameter Schema

```python
@dataclass
class Parameter:
    name: str
    span: EvidenceSpan
    provenance: Dict[str, Any] = field(default_factory=dict)
```

A `Parameter` is never a provision and never an LP — it carries a name, a
verified `EvidenceSpan` (the actual 423A object, imported unmodified —
`resolve_span` is called directly, not reimplemented), and a provenance
dict (which elicitation target produced it, quote index, source hash).

`PARAMETER_TARGETS` declares exactly the four named in the brief —
`tenant_share`, `building_share`, `rent_adjustment_pct`, `base_rent` —
each with a document-level label and search-hint synonyms. **No
lease-specific value (a percentage, a dollar figure) appears anywhere in
`PARAMETER_TARGETS` or anywhere else in the module** — only labels
describing what to look for. Confirmed by
`TestGateBNoLiteralValues::test_whole_module_has_no_lease_specific_literals`,
which greps the entire module's source for `"45.79"`, `"100%"`, `"3.75"`,
`"3%"` and asserts none are present.

### 2. Extraction — document-level, not LP-scoped

`extract_parameters(canonical_source, canonical=True)` calls the **same**
element-guided elicitation call path as LP elements
(`lease_element_elicitation.elicit_spans_for_targets`) — same prompt file,
same schema, same resolver, zero changes to any of them — but with
`PARAMETER_TARGETS` as the target list, which is entirely separate from
any LP's `expected_elements_305`. This is the architectural point stated
in the brief: the key-terms table is not "LP-00's content" or any other
LP's content; it is extracted independently, as a document parameter, and
only afterward attached to whichever LPs declare a dependency on it. Each
returned quote is resolved through `lease_evidence_spans.resolve_span()`
directly — the unmodified 423A resolver, not a parameter-specific
reimplementation. Only a `VERIFIED` quote becomes a `Parameter`; a missing
or unverified target is simply absent from the returned dict (extraction
itself never raises — that is Gate B's job).

### 3. Declared Dependency Map

```python
DEPENDENCY_MAP: Dict[str, List[str]] = {
    "LP-02": ["base_rent", "rent_adjustment_pct"],
    "LP-07": ["tenant_share", "building_share"],
}
```

Exactly the two LPs and four parameters named in the brief. No
speculative entries. Every entry is justifiable from Step 426's
measurement: all four parameters verified at 5/5 with byte-stable offsets
under `canonical_v2`.
`TestDependencyMapContent::test_dependency_map_has_no_overlapping_parameters`
confirms the production map's two LPs are disjoint by construction — the
non-destructive-assignment property (Task/Test requirement) is real but
not exercised by the production map itself, so it is proven separately
(see below).

### 4. Deterministic Attachment

```python
def attach_parameters_to_lp_evidence(parameters, lp_id, dependency_map=None) -> List[Parameter]:
    dep_map = dependency_map if dependency_map is not None else DEPENDENCY_MAP
    dep_names = dep_map.get(lp_id, [])
    return [parameters[name] for name in dep_names if name in parameters]
```

Pure dict lookup. No model call, no discretion — confirmed by
`test_attachment_uses_dependency_map_only_no_model_call`, which inspects
the function's actual referenced names (`__code__.co_names`, not
docstring prose) for absence of `elicit`/`adapter`/`model`.

**Non-destructive assignment**, proven with a test-local dependency map
that deliberately overlaps two LPs on `tenant_share` (the production map's
two LPs are disjoint, so this property needed its own test): calling
`attach_parameters_to_lp_evidence` for both LPs returns the **identical**
`Parameter` object (`assertIs`, not merely equal) to both — the same span,
same offsets, unmutated, still present in the source `parameters` dict
afterward. This is the property the old LP-bucketed extractor structurally
could not have: a clause assigned to one LP was gone from every other
LP's context.

### 5. Gate B

```python
def check_gate_b(parameters, lp_ids=None, dependency_map=None) -> List[dict]:
    ...
    satisfied = param is not None and param.span.verification_status == VERIFIED
    ...

def enforce_gate_b(parameters, canonical=True, ...) -> dict:
    ...
    if failures:
        if canonical:
            raise GateAbortError(...)
        return {"gate_status": "degraded", "failures": failures}
    return {"gate_status": "pass", "failures": []}
```

`GateAbortError` is imported directly from `cam.adapters.lease_review.lease_adapter`
— the same exception type and same fail-closed doctrine as the 422C
extraction-completeness gate, not a new class. `canonical` is an explicit
parameter, read directly — never inferred from `fallback_used` or any
other flag (422D doctrine, carried forward).

---

## Required Statements

> Attachment is deterministic. The model is never asked to include a
> parameter in a dependent LP and therefore cannot forget to.

> Gate B is keyed to declared dependencies, never to literal values, and
> never to evaluator agreement. Agreement is not sufficiency.

> This step does not build the selector panel. Span-to-LP relevance beyond
> the declared parameter dependencies remains ungoverned.

---

## Tests Executed — `test_427_parameter_block.py` (22 tests)

```
TestParameterExtraction::test_all_four_parameters_verified_with_correct_offsets PASSED
TestParameterExtraction::test_meta_carries_canonical_flag_explicitly PASSED
TestParameterExtraction::test_missing_parameter_is_absent_not_a_crash PASSED
TestDeterministicAttachment::test_attachment_uses_dependency_map_only_no_model_call PASSED
TestDeterministicAttachment::test_lp02_gets_base_rent_and_rent_adjustment_every_call PASSED
TestDeterministicAttachment::test_lp07_gets_tenant_share_and_building_share_every_call PASSED
TestDeterministicAttachment::test_same_span_attaches_to_multiple_lps_without_being_consumed PASSED
TestGateB::test_gate_b_aborts_canonical_when_dependency_missing PASSED
TestGateB::test_gate_b_aborts_when_dependency_present_but_unverified PASSED
TestGateB::test_gate_b_check_reports_pass_for_every_declared_pair PASSED
TestGateB::test_gate_b_degraded_not_abort_when_non_canonical PASSED
TestGateB::test_gate_b_passes_when_all_dependencies_satisfied PASSED
TestGateBNoLiteralValues::test_check_gate_b_source_has_no_lease_specific_literals PASSED
TestGateBNoLiteralValues::test_enforce_gate_b_source_has_no_lease_specific_literals PASSED
TestGateBNoLiteralValues::test_whole_module_has_no_lease_specific_literals PASSED
TestGateBNoEvaluatorVotes::test_gate_b_functions_never_reference_evaluators_or_votes PASSED
TestGateBNoEvaluatorVotes::test_gate_b_signature_takes_no_evaluator_argument PASSED
TestDependencyMapContent::test_dependency_map_has_no_overlapping_parameters PASSED
TestDependencyMapContent::test_dependency_map_is_exactly_two_lps_four_params PASSED
TestDependencyMapContent::test_every_dependency_name_is_a_declared_parameter PASSED
TestPipelineSeam::test_lease_adapter_does_not_import_parameter_block PASSED
TestPipelineSeam::test_lease_coverage_does_not_import_parameter_block PASSED
22 passed in 0.19s
```

**Mapped to the brief's required test list:**

- Each parameter extracts to a verified span with correct offsets —
  `test_all_four_parameters_verified_with_correct_offsets` (mocked model
  call, real 423A resolver against a fixture text).
- Deterministic attachment, every run — `test_lp07_gets_tenant_share_and_building_share_every_call`
  / `test_lp02_gets_base_rent_and_rent_adjustment_every_call`, each calling
  the attachment function 5 times and asserting identical results.
- Non-destructive multi-LP assignment — `test_same_span_attaches_to_multiple_lps_without_being_consumed`.
- Gate B passes when satisfied — `test_gate_b_passes_when_all_dependencies_satisfied`,
  `test_gate_b_check_reports_pass_for_every_declared_pair`.
- Gate B aborts (canonical) on a missing dependency —
  `test_gate_b_aborts_canonical_when_dependency_missing` (deletes
  `building_share` and asserts `GateAbortError` naming `LP-07` and
  `building_share`), plus `test_gate_b_aborts_when_dependency_present_but_unverified`
  (a present-but-`unverified` span also fails the gate — proves the gate
  reads `verification_status`, not mere presence).
- Gate B keyed to names, not literal values — 3 tests in
  `TestGateBNoLiteralValues`, grepping `check_gate_b`, `enforce_gate_b`,
  and the whole module's source for `"45.79"`, `"100%"`, `"3.75"`, `"3%"`.
- Gate B consults no evaluator votes — 2 tests in
  `TestGateBNoEvaluatorVotes`, checked against the functions' actual
  referenced names (`__code__.co_names`) rather than raw source text, so
  the docstrings' own prose about *not* consulting evaluators doesn't
  trip the check.
- `canonical=False` + missing dependency → degraded, not abort —
  `test_gate_b_degraded_not_abort_when_non_canonical`.

**Full regression:** 334 passed (312 pre-427 + 22 new). No regressions.

```
334 passed, 5 warnings in 2.56s
```

---

## Demonstration Run Against the Real Document

Not a baseline, not a recall measurement, not a pipeline run — one
execution of the new mechanism (`extract_parameters` →
`attach_parameters_to_lp_evidence` → `check_gate_b`/`enforce_gate_b`)
against the real Atreca lease under `canonical_v2`, run to obtain the
quoted evidence CLAUDE.md Rule 6 requires for the claim at the top of this
report.

```
source_document_hash=7118cc6ddf65bd7b09f436071f02c431bacc14b2a7c66bb9f84f8335ded0b03b
page_number_lines_stripped=38
parameters extracted: ['tenant_share', 'building_share', 'rent_adjustment_pct', 'base_rent']
meta.canonical=True meta.fallback_used=False meta.degraded=False

tenant_share:       verified [1942, 1996) "Tenant's Share of Operating Expenses of Building: 100%"
building_share:      verified [1997, 2032) "Building's Share of Project: 45.79%"
rent_adjustment_pct: verified [2097, 2127) "Rent Adjustment Percentage: 3%"
base_rent:           verified [1695, 1815) "Base Rent:\n$3.75 per rentable square foot of the Premises per month, subject to adjustment pursuant to Section 4 hereof."

ATTACHMENT:
LP-02: ['base_rent', 'rent_adjustment_pct']
LP-07: ['tenant_share', 'building_share']

GATE B:
  {'lp_id': 'LP-02', 'dependency': 'base_rent', 'gate_status': 'pass'}
  {'lp_id': 'LP-02', 'dependency': 'rent_adjustment_pct', 'gate_status': 'pass'}
  {'lp_id': 'LP-07', 'dependency': 'tenant_share', 'gate_status': 'pass'}
  {'lp_id': 'LP-07', 'dependency': 'building_share', 'gate_status': 'pass'}

enforce_gate_b result: {'gate_status': 'pass', 'failures': []}
```

`canonical_text[start:end]` was checked against `span_text` for all four
parameters and matched byte-for-byte in every case (`match: True`).

---

## What Remains Unwired

- **Not wired into `lease_adapter.py` or `lease_coverage.py`.** Confirmed
  by `TestPipelineSeam` (no reference to `lease_parameter_block` in either
  file's source) and by `git status` showing no diff to either file. Per
  423 spec §8, no Stage 5 work proceeds until Gates A–D pass together, and
  **Gate C (assignment stability across runs) has not been built or
  measured for this substrate** — 424/426 found real offset drift on
  several targets (Condition Precedent, Annual Statement, the 120-day
  target). Wiring Gate B into the live pipeline now, ahead of Gate C,
  would risk aborting runs for reasons unrelated to whether the
  architecture is working — exactly the failure the brief's "a dependency
  map with unmeasured entries is a gate that will fail for reasons
  unrelated to the architecture" warns against, one layer up.
- **No selector panel, cited union, or trace validation.** Span-to-LP
  relevance beyond these four declared parameter dependencies remains
  ungoverned — the vast majority of clauses in the document are still
  reached only through the existing LP-bucketed extraction path, unchanged
  by this step.
- **No structural addressing.** Per the 425/426-derived design note,
  deliberately deferred.
- **No prompt, resolver, or normalization-profile change.** Confirmed:
  `git status` shows no diff to `element_elicitation.txt`,
  `element_elicitation_schema.json`, or `lease_evidence_spans.py`.
- **No baseline.** None was run and none is cited.
- **Only two LPs and four parameters.** Extending `DEPENDENCY_MAP` to more
  LPs or parameters requires its own measurement, per the brief's explicit
  instruction not to speculate.

---

## Files Changed

- `cam/adapters/lease_review/lease_parameter_block.py` — new module
- `cam/adapters/lease_review/tests/test_427_parameter_block.py` — 22 new tests
- `build_log/427_chat_instruction.md` — the Part 0 brief, written verbatim
  before any work began
- `build_log/427_parameter_block_dependency_map.md` — this file
