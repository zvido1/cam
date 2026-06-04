# Step 375K — Code Status: Direction-Axis Reconciliation

**Date:** 2026-06-04  **Mode:** KEYLESS — no model calls, arithmetic over frozen artifacts.
**External-use pause:** still in force. 375K does not lift it.

---

## What was built

| File | What it does |
|---|---|
| `build_log/_375k_sign_reconcile.py` | Harness: loads 3 frozen inputs, classifies axis agreement, replays rules A–E |
| `build_log/375K_results.json` | Machine-readable: 26 per-finding records + Q1–Q6 answers |
| `build_log/375K_results.md` | Human-readable: per-finding table + 6 Q/A blocks + doctrine verbatim |

**READ-ONLY honored:** No edits to any production file, no routing change, no cam/core/, no Stage 5e edits.

---

## Keyless confirmation

This step is entirely keyless. Total model calls: **0**.
The harness loads three frozen JSON files, applies Python routing functions, and writes results.

---

## Frozen file sources for each axis

| Axis | Frozen file | Field path |
|---|---|---|
| `stage7_direction` | `05 Lease Analyzer/results/lease_review_20260604_033046_52adbf/tenant_0/pipeline_results.json` | `cross_provision_findings[].directionality` → mapped: `tenant_unprotected` = adverse |
| `stage5e_gap_impact` | same pipeline_results.json | `coverage_assessment[lp_id].use_impact.gap_impact` |
| `gap_impact stability flag` | `build_log/375I_q3_results.json` | `per_lp_stability[lp_id].unique_gap_impact` → stable if len == 1 |
| `materiality context` | `build_log/375J_results.json` | per-finding `materiality_source` + `materiality_distribution` |

---

## Rule D sanity check: reproduces 375J Q6?

**PASS — confirmed.**

375J Q6 result: *"direction gate not exercised by this n=1 artifact. Non-divergence proves the lease
was too one-sided to stress the sign axis, NOT that direction is decorative."*

Rule D (Stage7-only, ignores 5e gap_impact for sign) routes the 8 eligible LPs:
- LP-03/05/10/14/16/26/32 → `actionable_material_risk` (Stage7=adverse + assessed medium/high)
- LP-20 → `low_materiality` (Stage7=adverse + assessed low)

This is identical to 375J Policy B applied with Stage 7 direction. 375J Q6 compared Policy E
(direction-ignored) vs Policy B (adverse-gated) and found 0 divergences for eligible LPs.
Rule D produces the same routing as 375J Policy B, so the sanity check confirms the port is faithful.

**Rule E exposes the new finding:** LP-05 diverges between Rule D (→ Risk) and Rule E (→ improvement_favorable)
because Rule E uses 5e gap_impact (= favorable) as the sign. This confirms what 375J's Q6 noted:
the direction gate IS exercised when 5e is the sign axis. Non-divergence in 375J was an
axis-choice artifact, not a doctrinal property.

---

## Key numerical results

| Q | Result |
|---|---|
| Q1: axis distribution | 6 aligned / 2 sign_conflict / 18 missing_stage5e / 0 ambiguous |
| Q2: isolation | LP-05 not isolated (2/8 = 25%) but LP-20's conflict is weak (5e unstable) |
| Q3: rule counts | A/B/C: 6 Risk each; D: 7 Risk (LP-05 adversely staged7); E: 6 Risk |
| Q4: conflict causes | LP-05 = favorable_absence; LP-20 = use_specific_override; gap_impact is a consequence field, not a sign field |
| Q5: 5e stability in conflicts | LP-05 stable (strong evidence); LP-20 unstable (weak evidence) |
| Q6: Rule D sanity | PASS — reproduces 375J Q6 exactly; Rule E exposes LP-05 divergence |

---

## Doctrine paragraph (verbatim, as required)

> 375K does not assume a permanent sign hierarchy. It tests candidate sign-hierarchy rules because 375J
> exposed a live contradiction between Stage 7 directional sign and Stage 5e gap_impact.
>
> For production safety during the test, any Stage7<->5e sign conflict is treated as UNRESOLVED and cannot
> silently route as asserted Risk. The counterfactual may show how each candidate rule WOULD route it, but
> the diagnostic-safe bucket for an unresolved sign conflict is Needs Review.

---

## Key doctrinal finding (record for 375E-DIR)

`gap_impact` in Stage 5e was designed as a **use-aware materiality/consequence field**
("does the gap hurt THIS tenant?"), not as a sign/direction field.
Treating it as a competing sign field creates structural conflicts with Stage 7's direction assessment
("is there a gap in the protection regardless of use?").

Resolution options for 375E-DIR to evaluate:
1. **Demote gap_impact to consequence-context only** — never used as a routing sign; Stage 7 direction governs sign (Rule A).
2. **Split gap_impact** into `gap_direction` (protection gap polarity) and `gap_materiality_in_use` (use consequence). Allow `gap_direction` to serve as the sign axis (Rule B) when assessed.
3. **Require alignment** to assert adverse sign (Rule C); conflict → Needs Review, displayed but not routed as Risk.

This is a schema/doctrine decision for 375E-DIR, not a 375K code change.

---

## Queue (confirmed by 375K)

1. **375E-COV spec** — widen `_should_assess` past 8/32 + add provenance fields on BOTH axes:
   `materiality_source`, `materiality_value`, `materiality_tier_collapsed` AND
   `sign_source`, `sign_value`, `sign_conflict`, `routing_consequence_source`.
   LP-05 proves sign provenance is needed, not just materiality provenance.
2. **375E-DIR spec** — routing formula consuming COV fields + the 375K sign rule.
   Must resolve: which rule governs the adverse gate (A/B/C)?
   Candidate: Policy B+C from 375J + Rule A or C from 375K (source-strict + conflict-abstention).
3. **375E-COV implementation** (keyed).
4. **375E-DIR implementation** — NOT production-enabled until COV exists.
5. **375H-C** keyed fixture matrix → direction-sensitive schema repair.
   DEPLOYMENT TRAP unchanged.

---

## Decisions needed from Chat

1. Which sign-hierarchy rule (A, B, or C) to adopt for 375E-DIR — driven by Q4 cause analysis:
   if gap_impact is a consequence field, Rule A (Stage7-sign-primary) is the cleanest;
   if gap_impact should serve as a sign axis, split-schema (pre-req for Rule B) or abstention (Rule C).
2. Confirm the doctrinal finding: gap_impact demotion/split is a 375E-DIR schema decision.
3. Confirm queue order: 375E-COV spec → 375E-DIR spec → 375E-COV implementation → 375E-DIR implementation.
