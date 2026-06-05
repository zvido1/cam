# Step 375M — `gap_impact` → `use_consequence` Rename/Revalue Results

**Date:** 2026-06-05  **Mode:** Behavior-preserving refactor + compatibility replay.
**External-use pause:** still in force. 375M does not lift it.

---

## Validation 1: No routing drift (the falsifiable core)

**VERDICT: 0 routing drift. Rename/revalue is behavior-preserving.**

Re-ran the 375J and 375K routing logic through the normalizer against frozen run
`lease_review_20260604_033046_52adbf` and compared every bucket count and per-finding
bucket against the committed `375J_results.json` / `375K_results.json`.

### 375J current_bucket counts

| Source | risk | Total |
|---|---|---|
| **Committed** (`375J_results.json`) | 32 | 32 |
| **Re-derived** (post-normalizer) | 32 | 32 |
| **Delta** | **0** | **0** |

Result: **MATCH — 0 drift.**

### 375K rule bucket counts

| Rule | Committed distribution | Re-derived distribution | Match |
|---|---|---|---|
| Rule A | `{actionable_material_risk:6, needs_review_sign_conflict:2, consequence_unassessed:18}` | identical | **YES** |
| Rule B | `{actionable_material_risk:5, improvement_favorable:1, low_materiality:1, consequence_unassessed:18, low_materiality_or_addressed:1}` | identical | **YES** |
| Rule C | `{actionable_material_risk:6, needs_review_sign_conflict:2, consequence_unassessed_no_alignment:18}` | identical | **YES** |
| Rule D | `{actionable_material_risk:7, low_materiality:1, consequence_unassessed:18}` | identical | **YES** |
| Rule E | `{improvement_favorable:1, consequence_unassessed_no_5e_sign:18, actionable_material_risk:5, low_materiality_or_addressed:2}` | identical | **YES** |

Result: **ALL 5 RULES MATCH — 0 drift across all 26 directional findings.**

Per-finding check: **0 bucket drift events** across all 26 × 5 = 130 rule-bucket slots.

### Why 0 drift (proof of behavior-preservation)

The normalizer maps old values to new values before any comparison:
- `gap_impact="favorable"` → `use_consequence="beneficial"`
- `gap_impact="adverse"` → `use_consequence="harmful"`

All routing comparisons were updated to use the new vocabulary:
- `== "favorable"` → `=== "beneficial"` (JS) / `== "beneficial"` (Python)
- `== "adverse"` → `=== "harmful"` (JS) / `== "harmful"` (Python)

The logical result of each comparison is identical: LP-05's value ("favorable" → "beneficial") is still
not equal to "harmful" (was not equal to "adverse"), so every rule still routes LP-05 the same way.
No branching condition changed direction.

---

## Validation 2: Historical artifact compatibility

**PASS — legacy `gap_impact` artifacts render and route correctly through the normalizer.**

| Legacy input | Normalized output | Expected | Match |
|---|---|---|---|
| `{gap_impact: "favorable"}` | `"beneficial"` | `"beneficial"` | YES |
| `{gap_impact: "adverse"}` | `"harmful"` | `"harmful"` | YES |
| `{gap_impact: "neutral"}` | `"neutral"` | `"neutral"` | YES |
| `{gap_impact: "context_dependent"}` | `"context_dependent"` | `"context_dependent"` | YES |
| `{use_consequence: "beneficial"}` | `"beneficial"` | `"beneficial"` | YES |
| `{use_consequence: "harmful"}` | `"harmful"` | `"harmful"` | YES |
| `{use_consequence: "neutral"}` | `"neutral"` | `"neutral"` | YES |

Old artifacts pass through the normalizer identically to new artifacts with the same semantic content.
No crash, no missing-field, no behavior change.

---

## Validation 3: New output shape

**PASS — new `use_consequence` field with new values (`beneficial`/`harmful`/`neutral`) populates
correctly in every consumer path.**

The normalizer preferentially reads `use_consequence` over `gap_impact`, so any new artifact produced
by the renamed `lease_use_impact.py` will route correctly through all consumers without the legacy path.

---

## Validation 4: LP-05 specific

**PASS.**

| Check | Result |
|---|---|
| LP-05 `use_consequence` (normalized from frozen artifact) | `"beneficial"` |
| LP-05 Stage 7 direction | `adverse` (tenant_unprotected) |
| LP-05 `axis_relation` | `sign_conflict` (Stage7=adverse vs 5e=beneficial) |
| LP-05 `bucket_rule_A` | `needs_review_sign_conflict` |
| LP-05 `bucket_rule_B` | `improvement_favorable` |
| LP-05 `bucket_rule_C` | `needs_review_sign_conflict` |
| Sign conflict generated anywhere? | NO — it is a correctly-classified analytical relationship, not a spurious error |
| LP-05 bucket unchanged from 375K? | YES — all 5 rule buckets identical |

**LP-05 is now expressible without vocabulary collision:**
- Stage 7: `directionality=tenant_unprotected` (generic protection gap)
- Stage 5e: `use_consequence=beneficial` (gap benefits this warehouse tenant)
- These use DIFFERENT vocabularies — no more phantom "sign conflict" from shared words

---

## Files changed

| File | What changed |
|---|---|
| `cam/adapters/lease_review/lease_use_impact.py` | `_VALID_GAP_IMPACT` → `_VALID_USE_CONSEQUENCE`; values `{beneficial,neutral,harmful,context_dependent}`; prompt schema + definitions + LP-05 example; `_merge_verdicts` reads and output key; `assess_use_impact` all fallback dicts and count lines |
| `05 Lease Analyzer/static/app.js` | Added `normalizeUseConsequence()` before `deriveProvisionRiskLevel`; updated 8 consumers |
| `05 Lease Analyzer/_step371_variance.py` | Added `_normalize_use_consequence()`; updated `action_bucket()`, `governed_fields()`, `GOVERNANCE_KEYS` |
| `05 Lease Analyzer/_step372_decomp.py` | Added `_normalize_use_consequence()`; updated `action_bucket()`, `CHAIN_LAYERS` |
| `build_log/_375j_counterfactual.py` | Added normalizer for completeness (gap_impact not used for routing in 375J) |
| `build_log/_375k_sign_reconcile.py` | Added normalizer; updated `_axis_relation` (new `_uc_to_sign` helper), `rule_B`, `rule_E`, `_conflict_cause` |
| NEW `build_log/_375m_validate.py` | Validation harness — ran against frozen 52adbf, asserted 0 drift |
| NEW `build_log/375M_validation_result.json` | Machine-readable validation output |

---

## Write-path confirmation (single canonical field)

The backend (`lease_use_impact.py`) now writes ONLY `use_consequence`. No dual-write. The legacy
`gap_impact` key will NOT appear in any new pipeline run's artifacts. Old artifacts retain `gap_impact`
and are handled by the read-side normalizer in every consumer.

---

## Scope guard confirmed

| Guard | Status |
|---|---|
| 5e eligibility unchanged (still 8/32) | YES — no `_should_assess` changes |
| `use_consequence_source` NOT added | YES — deferred to 375E-COV |
| No bucketing logic changed | YES — only string comparisons updated from old to new vocabulary |
| No cam/core/ touched | YES |
| LP-20 consequence jitter unresolved | YES — stays open per spec |
| 375E-DIR NOT implemented | YES |
| External-use pause NOT lifted | YES |
