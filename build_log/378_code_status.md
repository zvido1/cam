# Step 378 — Code Status: Governance-Correctness Batch DEF-003 through DEF-008 + F8

**Date:** 2026-06-10
**Type:** GOVERNANCE-CORRECTNESS BATCH — authorized by Doctrine Ruling DEF-003/DEF-004 (defects.md)
**Pre-existing uncommitted changes:** same set as step 377 (config.py, build_log, finding doc, 2 untracked results). Not touched.
**DEF-009 / F7:** FENCED — not fixed in this batch. See "Fenced items" section.

---

## Files Changed

| File | Change | Key lines (post-edit) |
|------|--------|----------------------|
| `cam/adapters/lease_review/lease_finding_consequence.py` | DEF-003 support floor, DEF-004 materiality majority, DEF-005 materiality_source provenance, F8c split reasoning, F8d comment | `_merge_finding_verdicts` (major rewrite); copy-path attach (lines ~537–553); new-assessment attach (lines ~628–705) |
| `cam/adapters/lease_review/lease_verdict_distance.py` | DEF-006 unknown-verdict→unclear+log | `derive_verdict_distance` (lines ~44–70); added `import logging` at top |
| `cam/adapters/lease_review/lease_adapter.py` | DEF-007 api_calls_total increment (3 sites), F8e Stage 5f materiality default log (both modes) | Mode A Stage 5e ~+993; Mode A Stage 5f ~+1006; Mode C Stage 5e ~+1441; Mode C Stage 5f ~+1461; Mode C Stage 5e-F ~+1617 |
| `cam/adapters/lease_review/lease_p2pp_routing.py` | F8a fallthrough reason string, F8b parse-failure log | fallthrough `~line 201`; `_derive_mismatch_support` except branch `~line 64`; added `import logging` at top |
| `Docs/Patent_Current_State.md` | DEF-008 doc correction: STAGE_5D_ENABLED=True | lines ~888–900 |
| `Docs/CAM_Current_State.md` | DEF-008 doc correction: STAGE_5D_ENABLED=True | line ~1840 |
| `cam/adapters/lease_review/tests/test_378_governance_correctness.py` | NEW — unit tests for all 7 numbered acceptance checks + 3 bonus tests | new file |

---

## Implemented Rules per DEF

### DEF-003 / F1 — Consequence Support Floor

**`_merge_finding_verdicts` in `lease_finding_consequence.py`:**

Expected evaluator count = 3 (fixed lineup). All comparisons now use `_N_EXPECTED = 3`.

| Condition | confidence | consequence_support_label | evaluator_agreement |
|-----------|-----------|--------------------------|---------------------|
| 3 valid, all agree | `assert` | `full_assert` | `3-0` |
| 3 valid, 2 agree | `assert_weak` | `majority_assert` | `2-1` |
| 2 valid, both agree (1 failed) | `assert_duo` | `duo_assert` | `2-0-1f` |
| 1 valid (2 failed) | `insufficient_support` | `insufficient_support` | `1-0-2f` |
| 0 valid | `no_evaluators` | `no_evaluators` | `None` |
| 1-1-1 split | `context_dependent` | `split` | `1-1-1` |

**Provenance fields added to every merged verdict:**
- `expected_evaluator_count` (always 3)
- `valid_evaluator_count` (actual count of evaluators with valid output)
- `vote_distribution` (dict of consequence → count)
- `consequence_support_label` (see table)

**`"1-0"` and `"2-0"` agreement strings can no longer be produced.** Old code used `f"{len(consequences)}-0"` which produced `"1-0"` for 1 valid evaluator. Fixed by explicit case matching.

**Attach path (new-assessment, `assess_finding_consequence`):** `use_consequence_source = "assessed"` is now ONLY stamped when `support_label not in ("no_evaluators", "insufficient_support")`. A 1-valid-evaluator verdict stamps `use_consequence_source = "insufficient_consequence_support"`, which causes P2'' Rule 1a to fire → `review_needed/consequence_not_assessed`.

**P2'' fail-safe preserved:** insufficient/unparseable/missing consequence still routes Review Needed. Rule 1a guards on `csrc != "assessed"` — the new source strings (`"insufficient_consequence_support"`, `"no_majority_materiality"`) are all != "assessed" and fall through to review_needed.

### DEF-004 / F2 — Materiality Majority Merge

**`_merge_finding_verdicts` in `lease_finding_consequence.py`:**

Strict-min (`min(materialities, key=...)`) is REMOVED. Replaced with:
- **2+ majority** → majority value; minority preserved in `materiality_votes`
- **high↔low spread** → `materiality_disputed = True`
- **No-majority** (e.g. {high, medium, low}) → `materiality_source = "no_majority"`, `route_to_review_needed = True`

**`{high, high, low}` → merged = `"high"` (majority), not `"low"` (rejected strict-min).**

**No-majority path in attach loop:** when `route_to_review_needed = True`, the attach loop overrides `use_consequence_source = "no_majority_materiality"` — which is not `"assessed"` — causing P2'' Rule 1a to route `review_needed`. (PINNED: do NOT select minimum; do NOT let Code choose.)

**New provenance fields on findings:** `materiality_votes`, `materiality_support`, `materiality_agreement`, `materiality_disputed`, `materiality_source` (tracked independently of consequence provenance).

### DEF-005 / F3 — materiality_source Masquerade Fixed

**Copy path (`already_assessed_pairs` loop):**
Old: `f["materiality"] = ui.get("materiality", "low")` then always `f["materiality_source"] = "assessed"`.
New: checks `_lp_mat in _VALID_MATERIALITY`. If valid → `materiality_source = "assessed"`. If missing/invalid → `materiality = "low"`, `materiality_source = "defaulted_low"`.

**New-assessment path (attach loop):**
`materiality_source` is now taken from `verdict.get("materiality_source")` (which carries the merge-computed provenance: `"assessed"`, `"no_valid_materiality"`, `"no_majority"`, etc.) rather than always stamping `"assessed"` because consequence was valid.

### DEF-006 / F4 — Unknown Verdict Hardening

**`derive_verdict_distance` in `lease_verdict_distance.py`:**

Old: `if r1 is None or r2 is None: return 0` (silent distance-0 = apparent agreement).
New: unknown verdicts resolve to `VERDICT_RANK["unclear"]` (rank 3) plus a `logger.warning()` naming the unknown string.

- `"explicitly_present"` (0) vs unknown → distance 3 (was 0)
- unknown vs unknown → distance 0 (both rank 3, genuinely same tier)
- unknown vs `"missing"` (5) → distance 2 (was 0)

**Log message includes file, function, and a "vocabulary drift?" prompt.** Added `import logging` at top of file.

### DEF-007 / F5 — API Call Accounting

**Three sites added in `lease_adapter.py`:**

1. **Mode A Stage 5e** (line ~993): `total_api_calls += 3` after `assess_use_impact()` succeeds.
2. **Mode C Stage 5e** (line ~1441): `total_api_calls += 3` after `assess_use_impact()` succeeds.
3. **Mode C Stage 5e-F** (line ~1617): `total_api_calls += 3` when `newly_assessed > 0` (model batch was run; skips increment if no new assessments needed).

`assess_use_impact()` and `assess_finding_consequence()` both run one 3-evaluator parallel batch; the fixed +3 matches that structure. Fallback calls within an evaluator's own chain use the same 3-slot; +3 is conservative-correct.

### DEF-008 / F6 — Docs Corrected

**`Docs/Patent_Current_State.md`:** Pending Items entry updated from "Currently gated (`STAGE_5D_ENABLED = False`)" to "ENABLED as of Step 303 (variance acceptance test passed 2026-05-04)" with the product-behavior cascade note.

**`Docs/CAM_Current_State.md`:** Pending Items entry updated from "gated (`STAGE_5D_ENABLED = False`)" to "ENABLED (`STAGE_5D_ENABLED = True` since Step 303, 2026-05-04)" with product-behavior cascade note.

**Code is unchanged.** `lease_use_aware_coverage.py` already had `STAGE_5D_ENABLED = True`.

### F8 — Smaller Backend Items

**F8a:** `lease_p2pp_routing.py` fallthrough (assessed + unrecognized value) now returns `"unrecognized_consequence_value"` instead of the false `"consequence_not_assessed"`. Added `import logging` and `_logger` at top of file.

**F8b:** `_derive_mismatch_support` parse-failure `except` branch now emits `_logger.warning()` with the unparseable string, the finding_id, and a format-drift note. Previously silent.

**F8c:** On a genuine 1-1-1 split, `use_reasoning` is now `None` (no adopter for the synthesized `"context_dependent"` verdict). Old code fell back to `reasonings[0]` (first evaluator's reasoning regardless of their verdict). Split reasoning null is now tested explicitly.

**F8d:** `_call_finding_evaluator` now has a decision comment in the `_try()` function explaining why provider-claim is retained on failure (evaluator independence: prevents two roles from using the same provider, which would defeat 3-way independence). The failed-call claim is intentional. Comment is ~10 lines; no code change.

**F8e:** Both Mode A and Mode C Stage 5f blocks now log when `_ui.get("materiality")` is absent (triggering the `or "moderate"` default). Direction is still conservative; default is now provenance-tagged in the log. No routing change.

---

## Test Results

**Test file:** `cam/adapters/lease_review/tests/test_378_governance_correctness.py`
**Runner:** `python -m cam.adapters.lease_review.tests.test_378_governance_correctness`

| # | Test | Result |
|---|------|--------|
| 1 | One valid evaluator: not assert, not full assessed, cannot route Risk on consequence alone | **PASS** |
| 2 | Two valid agreeing evaluators: not mislabeled 3/3; provenance records 2 valid | **PASS** |
| 3 | {high,high,low} materiality: merged = high not low; minority preserved; disputed=True | **PASS** |
| 4 | {high,medium,low} materiality: routes Review Needed, not minimum | **PASS** |
| 5 | No valid materiality values: source is not "assessed" | **PASS** |
| 6 | Unknown verdict string: not distance 0 / perfect agreement; DEF-006 log fires | **PASS** |
| 7 | P2'' fail-safe paths still go Review Needed, not Risk (5 sub-cases + 1 positive control) | **PASS** |
| Bonus | F8a: unrecognized consequence value → "unrecognized_consequence_value" reason | **PASS** |
| Bonus | True 3/3 unanimous → "assert" / "full_assert" / "3-0" | **PASS** |
| Bonus | F8c: 1-1-1 split → null reasoning, not misattributed | **PASS** |

**Total: 10/10 PASS. Zero failures.**

---

## Routing Impact

| Area | Lawyer-visible? | Change |
|------|----------------|--------|
| DEF-003 F1 | **YES** | Findings with 1 valid evaluator now route Review Needed instead of potentially Risk. Requires 2 of 3 evaluators to fail, so normal runs unaffected; evaluator-failure runs now govern correctly. |
| DEF-004 F2 | **YES** | {high,high,low} findings now route per majority (high → possible Risk) rather than minority low (Improvement). The correct direction. No-majority {high,medium,low} findings now route Review Needed. |
| DEF-005 F3 | Audit trail only | `materiality_source` field accuracy improved; bucket routing unchanged (defaulted-low was already routing to Improvement correctly). |
| DEF-006 F4 | Latent / not currently reachable | Unknown verdicts now produce non-zero distances. Stage 305 normalizer still prevents unknowns from reaching this function in production. |
| DEF-007 F5 | No | Telemetry/cost accounting only. |
| DEF-008 F6 | No (doc only) | Docs corrected. |
| F8a | Audit trail only | Reason string accuracy; bucket unchanged (still review_needed). |
| F8b | Audit only | Silent parse failure now logs. |
| F8c | Audit trail only | Split reasoning now null instead of misattributed. |
| F8d | No code change | Comment added. |
| F8e | No | Logging added for silent default. |

---

## Fenced Items

### DEF-009 / F7 — FENCED (not fixed in this batch)

**Status:** Landlord-perspective consequence output remains unvalidated while the prompt is tenant-hardwired.

The `_FINDING_SYSTEM_PROMPT` in `lease_finding_consequence.py` and `_SYSTEM_PROMPT` in `lease_use_impact.py` are both written entirely in tenant terms ("THIS tenant's core business operations"). The user prompt injects `PERSPECTIVE: LANDLORD` for landlord runs, creating a conflict.

This was not fixed here because:
1. Prompt redesign requires its own keyed regression (separate validation run)
2. The batch brief explicitly fences F7
3. DEF-009 is open, located, and accurately described in `build_log/defects.md`

**Claim: Do NOT treat landlord-perspective directional consequence output as validated until DEF-009 is resolved.**

### DEF-002 — NOT touched

UI overhaul (Key Issues tally consolidation). Scope guard respected.

---

## Known Limitations of This Batch

1. **`assess_use_impact()` and `assess_finding_consequence()` do not return API call counts.** The +3 increment is based on the known 3-evaluator-per-batch structure. If fallback chains fire (a second model call per role), the actual count is higher. A future improvement would have these functions return their call count in meta. The current fix is accurate for the baseline case and conservative (does not overcount).

2. **`consequence_support_label` = `"duo_assert"` vs `confidence` = `"assert_duo"` naming inconsistency.** Minor — both refer to the 2-valid-agree case. Can be normalized in a future cleanup step if needed.

3. **No-majority materiality (DEF-004) stores `materiality = "low"` defensively.** The routing gate (`use_consequence_source = "no_majority_materiality"`) correctly prevents this default from causing routing harm. The stored value is audit-visible but not lawyer-visible.

---

*Step 378 complete. No code was changed in `cam/core/`. P2'' was not redesigned.*
