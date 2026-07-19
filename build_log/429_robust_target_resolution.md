# Step 429 — Robust target resolution + loud failure on unresolvable target + real-output fixture; Gate C re-run

**Date:** 2026-07-19
**Status:** COMPLETE — named objective met, tests run, Gate C re-run PASSED
**Instruction:** `build_log/429_chat_instruction.md` (present on disk before any code; confirmed and read in full)

---

## Summary

429's named objective was: resolve targets by leading `Target N` ordinal, raise
loudly on unresolvable targets in BOTH modules, leave the happy path
byte-identical, and re-run Gate C. **All four met.**

Gate C (N=10, same harness method as 428) went from **0/10 → 10/10** on every
parameter, with byte-identical offsets across all ten runs and Gate B passing
10/10. Config-integrity hashes are unchanged from 427/428, confirming the
prompt and declared config did not move.

**Nothing was wired into the live pipeline.** Per the instruction, wiring is a
separately authorized step; 429 measured the gate, it did not walk through it.

**Deferred, stated up front (not a footnote):** the LP-path terminal design
question — call-level abort vs. record-level routing to Review Needed — is
NOT settled by 429. The uniform raise is live on the LP path but is
**untested by Gate C**, which exercises only the parameter path. See
§ LP-path terminal-design note.

---

## 1. What changed — exact before/after

Two files, both adapters (`cam/adapters/lease_review/`), never `cam/core/`.

### New shared resolver (additive) — `lease_element_elicitation.py`

Added one exception and one function. No existing function was edited other
than the single line in `resolve_elicited_spans()` shown below. The module
docstring, `dedupe_elicited_spans`, `elicit_and_resolve_for_lp`,
`build_elicitation_sidecar`, `elicit_spans_for_targets`, and the loaders are
byte-identical.

```python
class UnresolvableTargetError(Exception):
    """Raised (429) when a model-returned `target` label cannot be mapped back
    to a declared element: no parseable leading `Target N` ordinal, or an
    ordinal out of range for the element list that was sent.
    ...
    """


_TARGET_ORDINAL_RE = re.compile(r"^\s*Target\s+(\d+)")


def resolve_target_ordinal(target_label: str, elements: List[dict]) -> str:
    match = _TARGET_ORDINAL_RE.match(target_label or "")
    if match is None:
        raise UnresolvableTargetError(
            f"Unresolvable target label {target_label!r}: no leading 'Target N' "
            f"ordinal could be parsed. Expected 'Target N' (optionally followed "
            f"by a description), with N in 1..{len(elements)}."
        )
    ordinal = int(match.group(1))
    if not 1 <= ordinal <= len(elements):
        raise UnresolvableTargetError(
            f"Unresolvable target label {target_label!r}: ordinal {ordinal} is out "
            f"of range for the {len(elements)} target(s) sent in this call "
            f"(expected 1..{len(elements)})."
        )
    return elements[ordinal - 1]["element_id"]
```

Only the ordinal is authoritative. No fuzzy or semantic matching on the
description text was added — asserted by a test
(`test_ordinal_wins_even_when_description_names_a_different_parameter`).

### Site 1 — `lease_parameter_block.py`, `extract_parameters()`

**Before (the 428 defect — silent discard):**

```python
    target_to_param = {f"Target {i}": e["element_id"] for i, e in enumerate(elements, start=1)}
    parameters: Dict[str, Parameter] = {}

    for match in elicitation_result.get("target_matches", []):
        param_name = target_to_param.get(match.get("target", ""), match.get("target", ""))
        if param_name not in PARAMETER_NAMES:
            continue
        if param_name in parameters:
```

**After:**

```python
    parameters: Dict[str, Parameter] = {}

    for match in elicitation_result.get("target_matches", []):
        param_name = resolve_target_ordinal(match.get("target", ""), elements)
        if param_name in parameters:
```

The `if param_name not in PARAMETER_NAMES: continue` filter is **removed, not
softened**. It was reachable only via the mislabel fallback, and it is what
converted a model-output variation into total data loss. After the change,
membership in `PARAMETER_NAMES` is structurally guaranteed rather than
filtered: `elements` is built from `PARAMETER_TARGETS` with
`element_id = param_name`, so `resolve_target_ordinal` can only return a
declared parameter name or raise. The import line at the top of the function
gained `resolve_target_ordinal` alongside the existing lazy
`elicit_spans_for_targets` import.

### Site 2 — `lease_element_elicitation.py`, `resolve_elicited_spans()`

**Before (silent mislabel-and-keep):**

```python
    target_to_element = {f"Target {i}": e["element_id"] for i, e in enumerate(elements, start=1)}
    records: List[dict] = []
    counter = 0
    for match in elicitation_result.get("target_matches", []):
        target_label = match.get("target", "")
        element_id = target_to_element.get(target_label, target_label)
```

**After:**

```python
    records: List[dict] = []
    counter = 0
    for match in elicitation_result.get("target_matches", []):
        target_label = match.get("target", "")
        element_id = resolve_target_ordinal(target_label, elements)
```

Everything below that line in the function — `resolve_span` call, offsets,
`failure_reason` derivation, the record dict, `elicited_by`,
`usable_in_canonical_stage5` — is unchanged.

### Deliberate non-change, flagged rather than fixed

`extract_parameters()`'s docstring still reads "this function itself never
raises for a missing parameter." That statement remains **true** — a missing
parameter is still simply absent from the returned dict, and no raise occurs
for it. The new raise fires on a different condition (an unresolvable target
label). Under the instruction's scope fence ("only the resolution/failure
lines change") I did not edit the docstring. Flagging it here so the architect
can decide whether it wants an added sentence in a later step; it is not
false as written.

---

## 2. Happy-path behavior is unchanged — the boundary

**When the ordinal parses and is in range, both functions produce identical
output to pre-429.** This is a narrowing of the failure surface, not a change
to the happy path.

Why this holds structurally: the old code built
`{f"Target {i}": e["element_id"] for i, e in enumerate(elements, start=1)}`
and looked up the label exactly. For a well-formed bare label `"Target N"`,
that lookup returns `elements[N-1]["element_id"]`. The new code parses `N` and
returns `elements[N-1]["element_id"]`. Same index, same construction, same
1-indexing. The two agree on every input the old path resolved successfully;
they differ **only** on inputs the old path resolved *wrongly* (echoed labels)
or silently dropped.

Tested, not just argued:

- `TestHappyPathUnchangedElementElicitation` runs the bare-`Target N` fixture
  through the real `resolve_elicited_spans()` and through a **pre-429 oracle**
  (the old dict-lookup mapping inlined in the test), and asserts field-by-field
  equality on `verification_status`, `start_char`, `end_char`, `span_text`,
  `elicited_by`, `quote_variants`. For well-formed bare input the old mapping
  is trivially correct, which is what makes it a legitimate reference.
- `TestHappyPathUnchangedParameterBlock` asserts the bare fixture yields the
  same four parameters at offsets computed straight off the unmodified 423A
  resolver, and that "first verified quote wins" semantics are preserved.

---

## 3. The real-output fixture and what it recovers

The 428 defect was invisible because every pre-429 test fed clean `"Target 1"`
records — a shape the model does not actually produce. The new fixture
(`cam/adapters/lease_review/tests/test_429_target_resolution.py`) is built from
the **echoed-label output quoted verbatim in the 428 report's diagnostic-probe
JSON**, with its quotes:

```python
ECHOED_TARGET_MATCHES = [
    {"target": "Target 1: Tenant's Share of Operating Expenses percentage",
     "quotes": ["Tenant's Share of Operating Expenses of Building: 100%"]},
    {"target": "Target 2: Building's Share of Project Operating Expenses percentage",
     "quotes": ["Building's Share of Project: 45.79%"]},
    {"target": "Target 3: Rent Adjustment Percentage (annual escalation rate)",
     "quotes": ["Rent Adjustment Percentage: 3%"]},
    {"target": "Target 4: Base Rent amount stated in the key-terms block",
     "quotes": ["Base Rent:\n$3.75 per rentable square foot of the Premises per month, "
                "subject to adjustment pursuant to Section 4 hereof."]},
]
```

What it recovers: pre-429, this input produced an **empty** `parameters` dict
(428's 0/10). Post-429 it resolves all four to VERIFIED `Parameter` objects.
The fixture also asserts the span carries the **VALUE, not just the label** —
`100%`, `45.79%`, `3%`, `$3.75 per rentable square foot` must each appear
inside the resolved span text, per 428's "a span reading `Tenant's Share ...:`
without `100%` is a failure dressed as a success" warning.

It further asserts echoed and bare fixtures produce **identical** records, so
the label form is invisible below resolution.

---

## 4. Tests — run, with actual output

New file: `cam/adapters/lease_review/tests/test_429_target_resolution.py` (18 tests).

Coverage against the instruction's required list:

| Required test | Where |
|---|---|
| 1. Real-output fixture, parameter block | `TestRealOutputFixtureParameterBlock` (3 tests) |
| 2. Real-output fixture, element elicitation | `TestRealOutputFixtureElementElicitation` (2 tests) |
| 3. Raise-on-unresolvable, BOTH modules | `TestRaiseOnUnresolvableElementElicitation` (4), `TestRaiseOnUnresolvableParameterBlock` (3), `TestResolveTargetOrdinalDirect` (3) |
| 4. Happy-path unchanged, BOTH modules | `TestHappyPathUnchangedElementElicitation` (1), `TestHappyPathUnchangedParameterBlock` (2) |

Both unresolvable variants are covered in both modules: unparseable label
(`"Tenant's Share"`, ordinal stripped) and out-of-range ordinal
(`"Target 99"` against a 4-element list). Each asserts the exception message
names the offending value. Also covered: empty target, `"Target 0"`, and that
a failing record does not leave a partial result behind.

**Actual output — new tests:**

```
$ python -m pytest cam/adapters/lease_review/tests/test_429_target_resolution.py -q
..................                                                       [100%]
18 passed in 0.16s
```

**Actual output — full suite, before and after:**

```
BEFORE (pre-429 baseline):
$ python -m pytest cam/adapters/lease_review/tests/ -q
334 passed, 5 warnings in 2.39s

AFTER:
$ python -m pytest cam/adapters/lease_review/tests/ -q
352 passed, 5 warnings in 2.08s
```

334 → 352 = 334 + 18 new. **0 regressions.** (`cam/` contains no test modules
outside `cam/adapters/lease_review/tests/` — confirmed by running pytest over
`cam` with that directory ignored: "no tests ran".)

---

## 5. Gate C re-run — N=10, same method as 428

Harness: `build_log/_429_gate_c_harness.py`. Same document
(`05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt`),
same `canonical_whitespace_v2` profile, same prompt, same declared config.
Each run: `extract_parameters()` → `attach_parameters_to_lp_evidence()` for
LP-02 and LP-07 → `enforce_gate_b()`. Raw results:
`build_log/_429_gate_c_results.json`.

Source identity (confirms same document and profile as 426):

```
source_document_hash = 7118cc6ddf65bd7b09f436071f02c431bacc14b2a7c66bb9f84f8335ded0b03b
canonical_text_hash  = 7118cc6ddf65bd7b09f436071f02c431bacc14b2a7c66bb9f84f8335ded0b03b
normalization_profile = canonical_whitespace_v2
canonical_text length = 160145
```

`7118cc6ddf65bd7b...` matches the `source_document_hash` recorded in the 426
report for canonical_v2 on this document.

### Config-integrity assertion (416 class)

```
prompt_hash:    {'bbb1e99d0963887d'}
config_hash:    {'7c2ac3de05b6e9ba'}
canonical:      {True}
fallback_used:  {False}
```

**PASS.** Single-valued across all 10 runs, and **identical to the hashes
recorded in 428** (`bbb1e99d0963887d` / `7c2ac3de05b6e9ba`) and to 424/426/427.
The prompt and declared config were not changed by 429 — as required — and the
before/after comparison is therefore like-for-like. The delta is the
resolution code and nothing else.

### Per-parameter table (the headline) — 428 vs 429

| Parameter | 428 rate | **429 rate** | Offsets across 10 runs | Distinct span texts |
|---|---|---|---|---|
| `tenant_share` | 0/10 | **10/10** | `(1942, 1996)` — identical all 10 | 1 |
| `building_share` | 0/10 | **10/10** | `(1997, 2032)` — identical all 10 | 1 |
| `rent_adjustment_pct` | 0/10 | **10/10** | `(2097, 2127)` — identical all 10 | 1 |
| `base_rent` | 0/10 | **10/10** | `(1695, 1815)` — identical all 10 | 1 |

Offset stability and span-text stability are both perfect: one offset pair and
one span text per parameter across all ten runs. No drift.

### Matched text — printed and verified, not trusted

Per 428's "verify the matched text" requirement, the actual `span_text` for
each parameter, and confirmation the VALUE is present (not the label alone):

```
tenant_share:        "Tenant's Share of Operating Expenses of Building: 100%"
building_share:      "Building's Share of Project: 45.79%"
rent_adjustment_pct: 'Rent Adjustment Percentage: 3%'
base_rent:           'Base Rent:\n$3.75 per rentable square foot of the Premises per month, subject to adjustment pursuant to Section 4 hereof.'
```

Each contains its value: `100%`, `45.79%`, `3%`, `$3.75 per rentable square
foot`. None is a bare label, and none is an adjacent row.

### Gate B outcome per run

| Run | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 428 | abort | abort | abort | abort | abort | abort | abort | abort | abort | abort |
| **429** | **pass** | **pass** | **pass** | **pass** | **pass** | **pass** | **pass** | **pass** | **pass** | **pass** |

**10/10 pass, 0 aborts.**

### Attachment correctness per run

Identical on all 10 runs, and non-vacuous this time (428's was vacuous — empty
input):

```
LP-02: ['base_rent', 'rent_adjustment_pct']
LP-07: ['tenant_share', 'building_share']
```

Exactly the declared dependencies, in declared order, every run.

### The confirming evidence: the model still echoed the label

This is the part that proves the fix is what changed the outcome, rather than
the model happening to behave differently today. The `elicited_target`
provenance recorded on every extracted parameter, across all 10 live runs:

```
10/10  tenant_share         <- "Target 1: Tenant's Share of Operating Expenses percentage"
10/10  building_share       <- "Target 2: Building's Share of Project Operating Expenses percentage"
10/10  rent_adjustment_pct  <- "Target 3: Rent Adjustment Percentage (annual escalation rate)"
10/10  base_rent            <- "Target 4: Base Rent amount stated in the key-terms block"
```

**40 of 40 target labels came back in the echoed form** — byte-for-byte the
strings the 428 probe recorded. Under pre-429 code every one of those 40 would
have missed the exact-string lookup and been discarded, reproducing 428's
0/10 exactly. The model-output variation is real, persistent, and now handled.

### Plain verdict

**YES — the parameter block is stable enough to wire into the live pipeline.**

10/10 extraction on all four parameters, byte-identical offsets and span text
across all ten runs, 10/10 Gate B pass, correct attachment every run, and
config-integrity clean. This is not "mostly stable"; there is zero variance in
the measured quantities.

Two honest limits on that verdict, neither of which 429 is entitled to close:

1. **One document.** This measures stability on the Atreca lease only. It does
   not validate the architecture and does not measure stability on unseen
   documents — the same caveat 428 carried.
2. **429 did not wire anything.** Per the instruction, wiring is a separately
   authorized step. Gate C passing removes the blocker that 428 raised; it is
   not itself authorization to proceed. 423 spec §8 gates Stage 5 work on
   Gates A–D passing *together*, which this step did not assess.

---

## 6. LP-path terminal-design note — tracked and DEFERRED, not a latent edge case

429 makes both paths raise-on-unresolvable **uniformly**. That uniformity is
deliberate for this step, but the two paths do not have the same terminal
answer, and 429 explicitly does not settle the second one.

**Parameter path — terminal, and correct.** The parameter set is small and
every entry is Gate-B-load-bearing. An unresolvable target there means a
declared dependency cannot be established, so a call-level abort is the right
final behavior. Nothing further is open.

**LP path (`resolve_elicited_spans`) — safer than before, but NOT settled.**
The uniform raise is strictly better than the pre-429 silent
mislabel-and-keep, which corrupted `elicited_by` provenance without any
signal, and it is correct FOR NOW. But whether the *terminal* LP-path behavior
should be:

- a **call-level abort** (what 429 ships), or
- a **record-level unresolvable-target error routed to Review Needed**,
  consistent with 423 spec §7's "a failed trace kills the trace, not the
  evidence"

is an **OPEN design question, deliberately deferred to a follow-on** (429b or
the wiring step). 429's whole point is the narrow fix; widening it to carry a
routing-doctrine decision would defeat that.

**Two things to record plainly:**

1. **The LP-path abort is now live** — `resolve_elicited_spans` is on the live
   LP path, and it will now raise where it previously kept a mislabeled
   record.
2. **It is UNTESTED by Gate C.** Gate C exercises the parameter path only
   (`extract_parameters` against `PARAMETER_TARGETS`). No Gate C run in this
   step called `resolve_elicited_spans` on the 32-LP element sets. Its
   unit-test coverage is real (see §4) but that is not the same as a measured
   live run.

This is a tracked, deferred decision — not an oversight and not a latent edge
case.

---

## 7. Scope fence — what was NOT touched

- `cam/core/` — untouched.
- Prompt (`element_elicitation.txt`), output schema, resolver
  (`resolve_span` / `lease_evidence_spans.py`), normalization profile,
  `PARAMETER_TARGETS`, `DEPENDENCY_MAP`, Gate B (`check_gate_b` /
  `enforce_gate_b`), attachment (`attach_parameters_to_lp_evidence`) — all
  unchanged. Confirmed by the config hashes matching 427/428 and by the diff.
- `lease_element_elicitation.py`: no function other than
  `resolve_elicited_spans` was edited; module docstring untouched.
- `lease_parameter_block.py`: no function other than `extract_parameters` was
  edited.
- No wiring into `lease_adapter.py` or `lease_coverage.py`. The 427 pipeline-
  seam tests (`test_lease_adapter_does_not_import_parameter_block`,
  `test_lease_coverage_does_not_import_parameter_block`) still pass, which is
  the mechanical proof that nothing was wired.

Full diff: 2 source files, +52 / −7 lines.

---

## Files Changed

- `build_log/429_chat_instruction.md` — sanctioned instruction (pre-existing on disk)
- `build_log/429_robust_target_resolution.md` — this file
- `cam/adapters/lease_review/lease_element_elicitation.py` — `UnresolvableTargetError`, `resolve_target_ordinal`, one line in `resolve_elicited_spans`
- `cam/adapters/lease_review/lease_parameter_block.py` — resolution/failure lines in `extract_parameters`
- `cam/adapters/lease_review/tests/test_429_target_resolution.py` — new, 18 tests
- `build_log/_429_gate_c_harness.py` — Gate C re-run harness
- `build_log/_429_gate_c_results.json` — raw Gate C results
