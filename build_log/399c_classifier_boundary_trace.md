# 399c — Classifier Boundary Trace: Harmful/Medium Item in Needs Review

**Date:** 2026-07-05  
**Type:** Read-only trace. No code changes. No pipeline changes.  
**Author:** Claude Code  
**Question:** Why does LP-16 Parking sit in NEEDS REVIEW despite `harmful` consequence, `medium` assessed materiality, and `hard_flag = true`?

---

## 1. Artifact inspected

**Run:** `lease_review_20260705_232259_443e33` (latest fresh run, 2026-07-05 19:41 UTC)  
**Artifact:** `results/lease_review_20260705_232259_443e33/tenant_0/pipeline_results.json`  
**Total coverage items:** 32

### LP-16 Parking — raw fields

| Field | Value |
|---|---|
| `issue_area_id` | `LP-16` |
| `coverage_state` | `partial` |
| `partial_class` | `partial_typical` |
| `materiality` (table/schema) | `low` |
| `requires_attention` | `True` |
| `exposure_source` | `schema` |
| `exposure_reason_code` | `schema_default` |
| `use_impact.use_consequence` | `harmful` |
| `use_impact.materiality` | `medium` |
| `use_impact.confidence` | `assert` |
| `use_impact.evaluator_agreement` | `3-0` |
| `review_priority_distance_signal.hard_flag` | `True` |
| `rpds.severity` | *(empty string)* |
| `rpds.reason` | `"Severe disagreement (epistemic conflict) combined with moderate consequence — escalated and flagged"` |
| `use_adjusted` | `False` |

---

## 2. Render path to the bucket assignment

`renderNavSidebar()` (line ~18369) → `renderNavSidebar()` overriding version (line ~18369) calls `classifyFindingType(a, 'c', { perspective })` for every `coverage_assessment` item → result determines which bucket array (`risk`, `reviewNeeded`, `improvement`, `addressed`) the item enters → those arrays are passed to `_navSectionWrap()` for rendering.

Same routing also runs in `_computeRiskCounts()` (line ~4696) for the Overview action summary. Both paths call the same `classifyFindingType`.

**Single source of truth:** `classifyFindingType` at line 18088.

---

## 3. Exact classifier branch for LP-16

Full trace through `classifyFindingType(lp16, 'c', { perspective })`:

**1. Synthesis/Mode A branches:** skipped — `finding._item_type` is not `'synthesis'`, mode is `'c'`.

**2. Mode C path entered (line 18137):**
```javascript
var state    = finding.coverage_state || '';  // → 'partial'
var pcls     = finding.partial_class  || '';  // → 'partial_typical'
var ui       = finding.use_impact;             // → { use_consequence:'harmful', materiality:'medium', ... }
var gap      = normalizeUseConsequence(ui);    // → 'harmful'
var mat      = ui && ui.materiality;           // → 'medium'
var uiActive = ui && ui.confidence !== 'no_evaluators'; // → true ('assert')
```

**3. `_consequenceBucket` inner IIFE:**

`state === 'covered' | not_applicable` → NO  
`state === 'potentially_unenforceable'` → NO  

matTier computation (line 18152):
```javascript
var matTier = (pcls === 'partial_material') ? 'HIGH'   // pcls='partial_typical' → NO
            : mat === 'high' ? 'HIGH'                  // mat='medium' → NO
            : mat === 'low'  ? 'LOW'                   // mat='medium' → NO
            : 'MEDIUM';                                // → MEDIUM
var isHighSev = (matTier === 'HIGH');                  // → false
```

`state === 'covered_unfavorable'` → NO  
`state === 'missing'` → NO  
`state === 'partial'` → YES (line 18176):
```javascript
if (pcls === 'partial_review') return 'improvement';   // pcls='partial_typical' → NO
if (pcls === 'partial_material') return sevTriage();   // pcls='partial_typical' → NO
return sevTriage();                                    // ← FALLS HERE
```

`sevTriage()`:
```javascript
function sevTriage() {
    if (isHighSev) return 'risk';  // isHighSev=false → NO
    return 'improvement';          // ← RETURNS 'improvement'
}
```

**`_consequenceBucket = 'improvement'`**

**4. hard_flag floor (lines 18192-18196):**
```javascript
var _rpds = finding.review_priority_distance_signal;
if (_rpds && _rpds.hard_flag === true           // true
    && (_consequenceBucket === 'improvement'    // true ← LP-16 hits this
        || _consequenceBucket === 'addressed')) {
    return 'review_needed';                     // ← FINAL BUCKET
}
```

**LP-16 routes to `review_needed` via the hard_flag floor.**

### The `harmful` consequence: not used

`gap` (= `'harmful'` from `use_impact.use_consequence`) is ONLY consulted in:
- `state === 'missing'`: if `gap === 'beneficial'` → addressed; if `mat === 'not_applicable'` → improvement
- Nowhere else in the partial path

For `state === 'partial'`, the routing uses **only** `partial_class` and `use_impact.materiality`. `use_consequence` is never read for a partial item. A `partial_typical / medium` finding lands at `improvement` regardless of whether the consequence is `harmful`, `neutral`, or `beneficial` — the only difference would come from `mat === 'high'` (→ RISK) or `pcls === 'partial_material'` (→ RISK).

---

## 4. Comparison set — all 32 items classified

Applied the same trace to all 32 items in the July 5 run:

### RISK (2 items)

| LP | state | pcls | uiMat | Why RISK |
|---|---|---|---|---|
| **LP-03** | partial | partial_typical | **high** | `mat=high → matTier=HIGH → sevTriage()→risk` |
| **LP-27** | partial | **partial_material** | — (no use_impact) | `pcls=partial_material → matTier=HIGH → sevTriage()→risk` |

**Only 2 of 32 items land in RISK.** Neither has `use_consequence=harmful` as the routing factor; LP-03 reaches RISK via `uiMat=high`, LP-27 via `pcls=partial_material`.

### NEEDS REVIEW (6 items)

| LP | state | pcls | uiMat | uiCon | hf | Route |
|---|---|---|---|---|---|---|
| LP-02 | partial | partial_typical | medium | harmful | T | improvement → hard_flag floor → review_needed |
| LP-05 | review_needed | — | medium | harmful | F | state=review_needed → review_needed (direct) |
| LP-14 | review_needed | — | medium | harmful | T | state=review_needed → review_needed (direct; hard_flag not 'improvement'/'addressed' → no effect) |
| **LP-16** | partial | partial_typical | medium | harmful | T | improvement → hard_flag floor → review_needed |
| LP-28 | review_needed | — | high | harmful | T | state=review_needed → review_needed (direct) |
| LP-32 | partial | partial_typical | medium | harmful | T | improvement → hard_flag floor → review_needed |

Note LP-28: `uiMat=high` AND `hf=true` AND `uiCon=harmful` — yet sits in NEEDS REVIEW because `state=review_needed` returns that bucket immediately (line 18181), before `matTier` is ever computed. The hard_flag floor only promotes `'improvement'/'addressed'` → it cannot promote an already-`review_needed` result to `risk`.

### IMPROVEMENT (20 items)

Includes LP-10: `partial / partial_typical / uiMat=medium / harmful / hf=False` → IMPROVEMENT (no hard_flag to promote it). LP-10 is the quietest harmful/medium item: no hard_flag, so it doesn't even get the floor. It sits in IMPROVEMENT, not NEEDS REVIEW.

### ADDRESSED (4 items)

LP-08, LP-12, LP-13, LP-23, LP-31 (various `covered`/`not_applicable`).

---

## 5. Why LP-16 is in NEEDS REVIEW

LP-16 is **following a general rule applied uniformly to all `partial_typical / uiMat=medium` items** — not specifically demoted. The routing is:

1. `partial_typical` + `uiMat=medium` → matTier=MEDIUM → not high severity → `improvement`
2. `hard_flag=true` promotes from `improvement` to `review_needed` (floor, not ceiling)
3. `harmful` consequence is architecturally invisible to the partial routing

LP-02 and LP-32 follow the identical path and land identically. LP-10 takes the same path but without a hard_flag — it stays in IMPROVEMENT. The hard_flag is the only thing distinguishing LP-16 from LP-10 at the bucket level.

There is **no run-to-run instability** in LP-16's classification for this run. `coverage_state=partial` and `partial_class=partial_typical` are stable fields (pipeline produces them from structured element assessment). The `uiMat=medium` is the Stage 5e output that determines the ceiling; it would need to be `high` for LP-16 to reach RISK.

The June 11 frozen run showed LP-16 with the same fields (partial, partial_typical, uiMat=medium, harmful, hf=true). LP-16 was in NEEDS REVIEW in that run too — consistent across runs.

---

## 6. Architectural interpretation

### Is this a classifier bug?

**No.** The classifier is operating correctly under its stated ontology:

- **RISK** = the classifier has high confidence of real exposure requiring action (`uiMat=high` → severe likely impact, OR `pcls=partial_material` → structural gap confirmed by element analysis, OR `potentially_unenforceable`).
- **NEEDS REVIEW** = the classifier has a coverage gap but is uncertain about severity (`review_needed` state = no coverage verdict produced), OR epistemic conflict (hard_flag) prevents confident risk assignment despite a coverage gap.
- **`harmful` consequence** = downstream consequence layer signal. It says "IF this gap bites the client, the direction is bad." It does NOT say "we are confident this gap is real and material." That confidence lives in `uiMat` and `pcls`.

LP-16 has assessed `uiMat=medium`: the model assessed consequence materiality as medium — not high. The classifier trusts that. `medium` materiality + `partial_typical` (not a confirmed full gap) → below the RISK threshold. The `harmful` consequence direction is noted (and now surfaced via the Step 400 provenance chips) but does not override the severity tier.

### Does this show run-to-run instability?

**No for LP-16.** Both runs show the same classification. The instability identified in prior sessions was in `use_consequence` values (LP-05 flipping `context_dependent`→`harmful`), not in LP-16.

### Does this show harmful-consequence items can sit outside RISK?

**Yes — and it's structural, not accidental.**

Three distinct paths for harmful items outside RISK in this run:
1. `partial_typical + uiMat=medium + hf=True` → NEEDS REVIEW (LP-02, LP-16, LP-32)
2. `partial_typical + uiMat=medium + hf=False` → IMPROVEMENT (LP-10) — harmful and not even in NEEDS REVIEW
3. `review_needed + uiMat=high + hf=True` → NEEDS REVIEW (LP-28) — high assessed materiality, still outside RISK

LP-10 is the most striking case: `harmful / medium` with no hard_flag sits in **IMPROVEMENT**. A risk-first UI shows 2 items in RISK and suggests a "fairly clean" lease — while 4 items with harmful assessed consequence sit in NEEDS REVIEW and IMPROVEMENT.

### Does this strengthen the case for a Priority Exposure surface?

**Yes — this is the strongest live evidence so far.**

The RISK bucket for this run contains:
- LP-03: harmful/high — correctly in RISK
- LP-27: partial_material, **no use_impact at all** — structurally flagged by element analysis, consequence unknown

Six items with `use_consequence=harmful` sit outside RISK. A lawyer who opens the sidebar, sees `RISK (2)`, and proceeds efficiently will miss LP-02, LP-10, LP-16, LP-28, LP-32 — all of which have assessed harmful consequence. The current ordering delivers a structurally clean story that is consequence-misleading.

The fix is **not** to redefine RISK (that would conflate confidence and consequence). The fix is a cross-bucket Priority Exposure surface sorted by consequence × confidence — a separate UI layer that answers "what can hurt this client?" without requiring RISK to mean two things at once.

---

## 7. Recommendation

**No build. Record as evidence only.**

The classifier is correct under current ontology. This trace confirms the architectural seam, not a bug:

> **RISK is confidence-first. NEEDS REVIEW holds epistemic caution. Harmful consequence is orthogonal to both. A consequence-led Priority Exposure surface must eventually sit above the action buckets — not inside them.**

Specific future steps this trace supports (not authorized here):

1. **Priority Exposure surface (pipeline-gated):** cross-bucket list of findings sorted by `use_impact.materiality` × `use_consequence`. Precondition: assessed-consequence coverage must be broader than 7/32 before leading the UI with it.
2. **`harmful` consequence in `partial` routing (architecture decision):** If Tzvi decides `harmful + medium` should reach RISK, the rule change is: in `sevTriage()`, substitute `mat === 'medium' && gap === 'harmful'` → `'HIGH'`. That is a routing change with a product judgment call attached; it should not happen without explicit instruction.
3. **LP-10 (harmful/medium/no-hard_flag in IMPROVEMENT):** quietest case. Currently not even surfaced with a hard_flag. Worth noting as the tail that falls below any floor.

---

## Comparison table (key items this run)

| LP | state | pcls | uiMat | uiCon | hf | Final bucket | Path |
|---|---|---|---|---|---|---|---|
| LP-03 | partial | partial_typical | **high** | harmful | F | **RISK** | matTier=HIGH→sevTriage→risk |
| LP-27 | partial | **partial_material** | — | — | F | **RISK** | pcls=partial_material→HIGH→risk |
| LP-28 | review_needed | — | high | harmful | T | NEEDS REVIEW | state=review_needed (direct) |
| LP-14 | review_needed | — | medium | harmful | T | NEEDS REVIEW | state=review_needed (direct) |
| LP-05 | review_needed | — | medium | harmful | F | NEEDS REVIEW | state=review_needed (direct) |
| **LP-16** | partial | partial_typical | **medium** | harmful | T | **NEEDS REVIEW** | MEDIUM→improvement→hf floor |
| LP-02 | partial | partial_typical | medium | harmful | T | NEEDS REVIEW | MEDIUM→improvement→hf floor |
| LP-32 | partial | partial_typical | medium | harmful | T | NEEDS REVIEW | MEDIUM→improvement→hf floor |
| LP-10 | partial | partial_typical | medium | harmful | **F** | **IMPROVEMENT** | MEDIUM→improvement (no floor) |
| LP-20 | missing | — | low | neutral | F | IMPROVEMENT | LOW→sevTriage→improvement |
