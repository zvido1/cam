# Step 375M — Code Status: `gap_impact` → `use_consequence` Rename/Revalue

**Date:** 2026-06-05  **Mode:** Behavior-preserving refactor + validation replay.
**External-use pause:** still in force. 375M does not lift it.
**DEPLOY GATE:** commit is local. Do NOT push until Tzvi reads 0-drift result and approves.

---

## What was built

| File | What changed |
|---|---|
| `cam/adapters/lease_review/lease_use_impact.py` | Producer: renamed field + revalued vocabulary |
| `05 Lease Analyzer/static/app.js` | Added `normalizeUseConsequence()`; updated 8 consumers |
| `05 Lease Analyzer/_step371_variance.py` | Added `_normalize_use_consequence()`; updated 3 references |
| `05 Lease Analyzer/_step372_decomp.py` | Added `_normalize_use_consequence()`; updated 3 references |
| `build_log/_375j_counterfactual.py` | Added normalizer shim |
| `build_log/_375k_sign_reconcile.py` | Added normalizer + `_uc_to_sign()`; updated `_axis_relation`, `rule_B`, `rule_E`, `_conflict_cause` |
| NEW `build_log/_375m_validate.py` | Validation harness — ran and passed |
| NEW `build_log/375M_validation_result.json` | Machine-readable validation output |
| NEW `build_log/375M_results.md` | Human-readable results + before/after comparison |
| NEW `build_log/375M_code_status.md` | This file |

**READ-ONLY of production route logic honored:** no `_should_assess` change, no cam/core/ edits,
no 375E-DIR implementation, no routing logic changed (only string label comparisons updated).

---

## Normalizer location and contract

**JavaScript:** `normalizeUseConsequence(ui)` — standalone function added to
`05 Lease Analyzer/static/app.js` immediately before `deriveProvisionRiskLevel` (~line 4983).

```javascript
function normalizeUseConsequence(ui) {
    if (!ui) return null;
    if (ui.use_consequence !== undefined && ui.use_consequence !== null) return ui.use_consequence;
    var legacy = ui.gap_impact;
    if (legacy === 'favorable') return 'beneficial';
    if (legacy === 'adverse')   return 'harmful';
    return legacy || null;
}
```

**Python:** `_normalize_use_consequence(ui)` — defined at module top in each Python consumer
(`_step371_variance.py`, `_step372_decomp.py`, `_375j_counterfactual.py`, `_375k_sign_reconcile.py`).

Same contract:
- If `use_consequence` key present → return it
- Else map `gap_impact`: `favorable`→`beneficial`, `adverse`→`harmful`, others unchanged
- If both absent → return `None`

---

## Single-field write confirmed

`lease_use_impact.py` writes ONLY `use_consequence`. Grep confirms no `"gap_impact"` key in any
output dict in the file post-edit:

Fallback dicts (no_evaluators, no_use_profile, no_valid_verdict) all use `"use_consequence"`.
`_merge_verdicts()` output dict: `"use_consequence": gap_impact` (the local variable holds the
normalized value; the dict key is the new field name).

**No dual-write.** The field `gap_impact` will not appear in any new artifact.

---

## Consumer call sites updated (all 12)

| # | File | Line (approx) | What changed |
|---|---|---|---|
| 1 | app.js | ~5010 | `ui.gap_impact === 'favorable'` → `_uc === 'beneficial'` (via `normalizeUseConsequence`) |
| 2 | app.js | ~5014 | `ui.gap_impact === 'neutral'` → `_uc === 'neutral'` |
| 3 | app.js | ~5056-5063 | review_needed routing: `gap_impact === 'adverse'/'favorable'/'neutral'` → `_uc2 === 'harmful'/'beneficial'/'neutral'` |
| 4 | app.js | ~16220 | suppress advisor button: `gap_impact === 'favorable'` → `normalizeUseConsequence === 'beneficial'` |
| 5 | app.js | ~16302 | `_isUseImpactFavorable`: `gap_impact === 'favorable'` → `normalizeUseConsequence === 'beneficial'` |
| 6 | app.js | ~16643 | CSS class: `gap_impact === 'favorable'/'adverse'` → `_ciGap === 'beneficial'/'harmful'` |
| 7 | app.js | ~17718 | sidebar skip: `gap_impact === 'favorable'` → `_uiGap === 'beneficial'` |
| 8 | app.js | ~18107 | classifyFindingType: `gap === 'favorable'` → `gap === 'beneficial'` |
| 9 | _step371_variance.py | 30 (now ~40) | `action_bucket()` skip: `gap_impact == "favorable"` → normalizer |
| 10 | _step371_variance.py | 66 (now ~76) | `governed_fields()`: key `"use_impact.gap_impact"` → `"use_impact.use_consequence"` |
| 11 | _step372_decomp.py | 36 (now ~46) | `action_bucket()` skip: normalizer |
| 12 | _step372_decomp.py | 106 (now ~116) | `CHAIN_LAYERS`: key + lambda updated |

---

## Validation outcomes

All 4 validations passed (run: `python build_log\_375m_validate.py`):

| Check | Result |
|---|---|
| 375J: 0 bucket drift events | **PASS** |
| 375J: current_bucket counts match (32 risk / 0 others) | **PASS** |
| 375K: 0 bucket/axis drift events across 26 × 5 = 130 slots | **PASS** |
| Legacy compat: 7 normalize() test cases | **PASS** |
| LP-05 specific (normalized=beneficial, axis=sign_conflict, A/B/C buckets match) | **PASS** |

**Final verdict: 0 routing drift. Rename/revalue is behavior-preserving.**

---

## Queue after 375M

1. **DEPLOY GATE**: push to `main` (Railway redeploy) — requires Tzvi's approval after reading 0-drift result.
2. **375E-COV** — widen `_should_assess` past 8/32 + add `use_consequence_source`
   (assessed | defaulted_floor | not_eligible | absent). Now safe to widen — vocabulary is clean.
3. **375E-DIR** — routing formula consuming COV fields. LP-05 = beneficial-position, not Risk.
4. **375E-COV implementation** (keyed).
5. **375E-DIR implementation** — not production-enabled until COV exists.
6. **375H-C** keyed fixture matrix. DEPLOYMENT TRAP unchanged.

---

## Decisions needed from Tzvi

1. Approve push to `main` after reading `375M_results.md` and confirming the 0-drift result.
2. Confirm queue order for post-deploy steps.
