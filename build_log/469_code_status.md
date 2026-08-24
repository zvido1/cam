# Step 469 Part A — the TBD default-law escape hatch: census

**Date:** 2026-08-23 · **Instruction:** `build_log/469_chat_instruction.md`
**DIAGNOSTIC ONLY.** No fix, no runs, nothing changed. Schema census plus counts over the four
persisted runs (`s457_r1`, `s457_r3`, `s468_r1`, `s468_r2`).

---

## The answer to the framing question

**It is not LP-27 element 7 only. It is a population — and the placeholder is not the exception, it is
the entire category.**

**Every single jurisdiction-dependent element in the schema is unfilled: 18 of 18. Zero are
populated.**

## Q1 — Elements resting on an unfilled placeholder: 18, across 4 LPs

| LP | element_id | block shape |
|---|---|---|
| LP-09 | `LP-09.consent_standard_supplied` | list |
| LP-09 | `LP-09.tenant_remains_liable_after_transfer` | list |
| LP-09 | `LP-09.unauthorized_transfer_consequences` | list |
| LP-11 | `LP-11.common_law_remedies_preserved` | list |
| LP-11 | `LP-11.damages_calculation_and_mitigation` | list |
| LP-11 | `LP-11.reletting_rights_and_obligations` | list |
| LP-11 | `LP-11.remedies_cumulative_not_exclusive` | list |
| LP-26 | `LP-26.constructive_eviction_addressed` | dict |
| LP-26 | `LP-26.free_from_landlord_disturbance` | dict |
| LP-26 | `LP-26.free_from_third_party_claims_through_landlord` | dict |
| LP-26 | `LP-26.quiet_enjoyment_covenant_present` | dict |
| LP-26 | `LP-26.remedies_for_breach_of_quiet_enjoyment` | dict |
| LP-26 | `LP-26.scope_peaceful_possession` | dict |
| **LP-27** | **`LP-27.common_law_remedies_preserved`** | dict |
| **LP-27** | **`LP-27.remedies_cumulative_not_exclusive`** | dict |
| **LP-27** | **`LP-27.tenant_right_to_damages`** | dict |
| **LP-27** | **`LP-27.tenant_right_to_specific_performance`** | dict |
| **LP-27** | **`LP-27.tenant_right_to_terminate`** | dict |

Two encodings, both unfilled — 7 as a bare list, 11 as a dict:

```json
"default_law_jurisdiction_dependent": ["TBD_BY_ATTORNEY_REVIEW"]

"default_law_jurisdiction_dependent": {
    "applies_in": ["TBD_BY_ATTORNEY_REVIEW"],
    "modified_in": ["TBD_BY_ATTORNEY_REVIEW"],
    "requires_explicit_grant_in": ["TBD_BY_ATTORNEY_REVIEW"]
}
```

**Five of LP-27's ten elements carry this route — including BOTH false positives**, elements 6
(`tenant_right_to_damages`) and 7 (`tenant_right_to_specific_performance`).

## Q2 — Truthy `default_law_covers`: 37 of 212 elements

| category | count |
|---|---|
| `False` | 175 |
| **flat `True`** — no jurisdiction qualifier at all | **19** |
| **`"jurisdiction-dependent"`, unfilled placeholder** | **18** |
| `"jurisdiction-dependent"`, genuinely populated | **0** |

So of the 37 elements where a `covered_by_default_law` verdict is permitted, **18 are permitted on a
qualification nobody ever supplied.** The other 19 are flat assertions carrying no jurisdiction
qualification to leave unfilled — a different question, not the one asked here.

## Q3 — `_normalize_verdict` checks TRUTHINESS ONLY

`lease_coverage_305.py:821-825`:

```python
    # Enforce schema constraints
    if v == "implicitly_present" and not element.get("implicit_coverage_acceptable", False):
        return "unclear"
    if v == "covered_by_default_law" and not element.get("default_law_covers", False):
        return "unclear"
```

`not element.get("default_law_covers", False)`. The value `"jurisdiction-dependent"` is a non-empty
string, therefore truthy, therefore the guard does not fire. **The code never inspects
`default_law_jurisdiction_dependent` at all** — no reference to it exists in `lease_coverage_305.py`.
The distinction between "default law covers this" and "default law may cover this depending on a
jurisdiction analysis nobody has done" is invisible to the enforcement layer.

## Q4 — `covered_by_default_law` IS presence-tier

`lease_coverage_305.py:52-57`:

```python
PRESENCE_VERDICTS = frozenset({
    "explicitly_present",
    "implicitly_present",
    "covered_by_default_law",
    "covered_in_other_LP",
})
```

and again in the DEF-010a tier at `:71-76`, with `_PRESENCE_TIER_EXPANSION_RANK` ranking it 3 (last).
So it counts toward a presence majority and **is not a dissent**.

## Q5 — Observed usage across all 33 LPs

| run | merged `covered_by_default_law` | per-evaluator | per-evaluator on a TBD element |
|---|---|---|---|
| s457_r1 (baseline) | 0 | 7 | **1** |
| s457_r3 (baseline) | 0 | 5 | 0 |
| s468_r1 (entailment) | 1 | 9 | **1** |
| s468_r2 (entailment) | 0 | 9 | **3** |

TBD-backed per-evaluator votes observed: `LP-26.constructive_eviction_addressed` (r457_1, r468_2),
`LP-27.tenant_right_to_specific_performance` (r468_1, r468_2),
`LP-09.tenant_remains_liable_after_transfer` (r468_2).

The remainder — `LP-17.claims_time_limit`, `LP-32.notification_requirement`,
`LP-32.survival_after_expiration`, `LP-13.negligence_carveouts` — sit on flat `True` elements and are
legitimately permitted. **The route is used on both populations; only the TBD one is unsound.**

**No TBD-backed verdict became the merged verdict in any of the four runs.** But that understates the
effect, and the LP-27 element 7 case shows why.

### The real harm: it converts a dissent into unanimity

On element 7, B rejected the textual basis outright — *"the general phrase does not expressly identify
specific performance or injunctive relief"* — and then returned `covered_by_default_law` rather than
`missing`. Because that verdict is presence-tier, **all three evaluators landed in the presence tier,
so no dissent was recorded and the merge reported `implicitly_present` at high confidence.**

**CORRECTED at Step 470** — the original text here said the merge would have been a presence majority
with a recorded dissent. That was asserted without quoting the code path and is wrong. A **disputed
gate** at `lease_coverage_305.py:994` returns `disputed` on any presence/missing split, before the
majority is honoured. Simulated over the stored verdicts: had B returned `missing`, element 7 merges
to **`disputed` / `distant_split_presence_missing` / low confidence** in both runs.

**So the TBD route converted a `disputed` low-confidence outcome into `implicitly_present` at high
confidence.** The harm is larger than first recorded. See `470_code_status.md`.

That is the same class of harm recorded in `FINDING_context_widening_regression.md` §5 for element 7's
stabilisation: the answer stays wrong and the indicator that something is wrong disappears.

## Recorded, not fixed

Per instruction, no fix. For whoever takes it: the minimal change is that `_normalize_verdict` should
treat `"jurisdiction-dependent"` as satisfied only when the jurisdiction analysis is actually present
and names the governing law in scope — which would currently disqualify **all 18**, since none is
filled in. That is a behaviour change across 4 LPs and needs its own measurement, not a quiet patch.

## What is NOT established

- Whether the 18 elements are *substantively* wrong to allow default-law coverage. The finding is that
  the qualification is unfilled, not that the underlying legal claim is false.
- Whether other schemas beyond `retail_lease_knowledge.json` carry the same pattern. Only this one was
  censused; it is the file `load_expected_elements_by_lp()` and the 305 path both read.
- Frequency at scale. Four runs on one fixture; TBD-backed votes appeared 5 times in 30 evaluator-runs
  of the affected elements.
- Whether the flat-`True` 19 are correctly marked. Out of scope here.
