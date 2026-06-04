# Step 375K — Direction-Axis Reconciliation Results

**Frozen run:** lease_review_20260604_033046_52adbf  |  **Keyless:** yes, no model calls
**stage7_direction source:** `pipeline_results.json` -> `cross_provision_findings[].directionality`
**stage5e_gap_impact source:** `pipeline_results.json` -> `coverage_assessment[].use_impact.gap_impact`
**gap_impact stability source:** `build_log/375I_q3_results.json` -> `per_lp_stability[].unique_gap_impact`
**materiality context source:** `build_log/375J_results.json`

---

## Doctrine (verbatim)

> 375K does not assume a permanent sign hierarchy. It tests candidate sign-hierarchy rules because 375J exposed a live contradiction between Stage 7 directional sign and Stage 5e gap_impact.
> 
> For production safety during the test, any Stage7<->5e sign conflict is treated as UNRESOLVED and cannot silently route as asserted Risk. The counterfactual may show how each candidate rule WOULD route it, but the diagnostic-safe bucket for an unresolved sign conflict is Needs Review.

---

## Per-finding classification table (26 directional findings)

Rules A/B/C = production candidates. Rules D/E = diagnostic baselines, NOT production candidates.

| Finding | LP | s7_dir | 5e_gi | 5e_stable | axis | A | B | C | D* | E* |
|---|---|---|---|---|---|---|---|---|---|---|
| Dir-01 | LP-01 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-02 | LP-02 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-03 | LP-03 | adverse | adverse | True | aligned | Risk | Risk | Risk | Risk | Risk |
| Dir-04 | LP-04 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-05 | LP-05 | adverse | favorable | True | CONFLICT | NR(conflict) | improvement | NR(conflict) | Risk | improvement |
| Dir-06 | LP-06 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-07 | LP-07 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-08 | LP-10 | adverse | adverse | False | aligned | Risk | Risk | Risk | Risk | Risk |
| Dir-09 | LP-11 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-10 | LP-14 | adverse | adverse | True | aligned | Risk | Risk | Risk | Risk | Risk |
| Dir-11 | LP-15 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-12 | LP-16 | adverse | adverse | True | aligned | Risk | Risk | Risk | Risk | Risk |
| Dir-13 | LP-17 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-14 | LP-18 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-15 | LP-19 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-16 | LP-20 | adverse | neutral | False | CONFLICT | NR(conflict) | low/addressed | NR(conflict) | low-mat | low/addressed |
| Dir-17 | LP-21 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-18 | LP-22 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-19 | LP-24 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-20 | LP-25 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-21 | LP-26 | adverse | adverse | True | aligned | Risk | Risk | Risk | Risk | Risk |
| Dir-22 | LP-27 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-23 | LP-28 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-24 | LP-29 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-25 | LP-30 | adverse | absent | n/a | no-5e | unassessed | unassessed | unassessed(C) | unassessed | unassessed(E) |
| Dir-26 | LP-32 | adverse | adverse | False | aligned | Risk | Risk | Risk | Risk | Risk |

\* D and E are diagnostic baselines. NOT production candidates.

Column key: Risk = actionable_material_risk | NR = Needs Review | unassessed = consequence_unassessed
  improvement = improvement_favorable (5e=favorable + assessed medium/high)
  unassessed(C) = no-alignment under Rule C | unassessed(E) = no-5e-sign under Rule E

---

## Q1 — Axis distribution

**Axis counts (n=26 directional findings):**

| Axis relation | Count | LPs |
|---|---|---|
| aligned | 6 | LP-03, LP-10, LP-14, LP-16, LP-26, LP-32 |
| sign_conflict | 2 | LP-05, LP-20 |
| missing_stage5e | 18 | (18 gated-out LPs) |
| ambiguous | 0 | — |

**Proven claim:** 2/26 directional findings have sign_conflict; 6/26 are aligned; 18/26 are missing_stage5e.
Sign conflict is real but not dominant — it affects 2 of the 8 eligible LPs (25% of the assessed set),
zero of the 18 gated-out LPs.

**Caveat:** n=1 lease; all 26 Stage 7 findings are adverse. A more balanced lease could show
higher conflict rates.

**Still unmeasured:** Sign-conflict rate for the 18 missing LPs after 375E-COV widens 5e.

---

## Q2 — Is LP-05 isolated or a pattern?

**2 conflicts out of 8 eligible (25%); but asymmetric evidentiary weight.**

- **LP-05** (adverse vs favorable): 5e gap_impact **STABLE** across all 10 Q3 replays → `[favorable]` only.
  Strong, reliable counter-signal. This is a genuine doctrinal conflict.
- **LP-20** (adverse vs neutral): 5e gap_impact **UNSTABLE** across Q3 replays (neutral×8, adverse×1,
  context_dependent×1). Weak, wobbling counter-signal. Cannot be asserted as clean conflict evidence.

**Proven claim:** LP-05 is not fully isolated but LP-20's conflict is weak evidence. The load-bearing
case is LP-05. A sign hierarchy must resolve LP-05; LP-20's conflict may dissolve once 5e instability
is addressed.

**Caveat / Still unmeasured:** see Q1.

---

## Q3 — Risk/NR counts under each rule

Current baseline: 26/26 directional findings → Risk (3-0 verified, all adverse, ASSERT_SIGNAL).

| Rule | Label | Risk | Not-Risk | Key changes vs current |
|---|---|---|---|---|
| A | Stage7-sign-primary (PROD) | 6 | 20 | LP-05/20 → NR(conflict); 18 missing → unassessed |
| B | 5e-sign-primary (PROD) | 6 | 20 | LP-05 → improvement_favorable; LP-20 → low-mat; 18 missing → unassessed |
| C | conflict-abstention (PROD) | 6 | 20 | LP-05/20 → NR(conflict); 18 missing → unassessed(no-align) |
| D* | Stage7-only baseline | 7 | 19 | 18 missing → unassessed; LP-20 → low-mat; LP-05 still Risk |
| E* | 5e-only baseline | 6 | 20 | LP-05 → improvement; LP-20 → low-mat; 18 missing → unassessed(no-5e-sign) |

\* D and E are diagnostic baselines, NOT production candidates.

Key distinction: **Rule B routes LP-05 to improvement_favorable** (5e=favorable + medium assessed),
while **Rules A and C route LP-05 to Needs Review** (sign conflict surfaced, not silently resolved).
This is the central production-candidate difference on this lease.

**Proven claim:** vs current (26/26 Risk): Rule A: 6 Risk (aligned adverse + assessed medium/high), 2 Needs-Review (sign_conflict: LP-05/20), 18 consequence_unassessed (missing_stage5e, no silent floor). Rule B: 5 Risk (aligned adverse + assessed medium/high; LP-05 excluded as favorable-5e), LP-05 -> improvement_favorable (5e=favorable + medium assessed), LP-20 -> low_materiality (assessed_low), 18 consequence_unassessed. Rule C: 6 Risk (aligned + both aligned adverse), 2 Needs-Review (sign_conflict), 18 consequence_unassessed_no_alignment (missing-one-axis). Rule D (diagnostic): 6 Risk (all adverse Stage7 + assessed medium/high), LP-20 -> low_materiality, 18 consequence_unassessed -- reproduces 375J Q1/Q6 exactly. Rule E (diagnostic): 5 Risk (5e-adverse + assessed medium/high; LP-05/20 excluded as non-adverse in 5e), 18 consequence_unassessed_no_5e_sign (no 5e -> no sign under Rule E). Key finding: A/B/C all correctly exclude LP-05 from silent Risk (A/C via conflict->NR, B via 5e-favorable->not-adverse). The 18 missing_stage5e findings are consistently unroutable under any source-aware rule until 375E-COV widens coverage.

**Caveat:** All rule changes vs current are on the 18 missing_stage5e LPs (already exposed in 375J Q5) plus 2 sign_conflict LPs. The meaningful NEW finding from 375K is the fate of LP-05: under Rule B it routes to improvement_favorable (5e=favorable, medium assessed) rather than Needs Review. Under Rules A and C it routes to needs_review_sign_conflict. A/B/C differ on whether a stable favorable-5e signal is strong enough to override Stage7 or merely flag a conflict.

**Still unmeasured:** How these counts change after 375E-COV widens 5e: the 18 missing_stage5e could split into aligned + conflict + ambiguous, changing the Rule A/B/C risk counts substantially.

---

## Q4 — Do conflict cases share a cause?

Both conflicts share the same ROOT STRUCTURE:
> Stage 7 assesses **generic directional protection** (is there a provision protecting the tenant?).
> Stage 5e assesses **use-aware consequence** (does the gap actually hurt THIS tenant?).
> They are measuring different axes, not the same axis.

**LP-05 — cause: `favorable_absence`**
Stage 7: *"Tenant has no co-tenancy or operation protections. Tenant use rights lack operational safeguards while Landlord enforces use restrictions via default remedies."*
Stage 5e: *"Sparse permitted use language prevents landlord from restricting truck access, light assembly, or storage activities, maximizing operational flexibility for this industrial tenant."*
Analysis: Stage 7 sees "tenant_unprotected" — no explicit co-tenancy or operational protection clause.
Stage 5e sees that for a warehousing tenant, the absence of a strict permitted-use clause is
**favorable** — the landlord cannot restrict operations never explicitly permitted.
The absence of a conventionally-protective clause benefits this specific tenant.

**LP-20 — cause: `use_specific_override`**
Stage 7: *"Tenant has no defined remedies for breach. Tenant exclusivity right lacks enforcement mechanism while Landlord makes representation but faces no explicit penalty."*
Stage 5e: *"Exclusivity gaps have little effect on standard warehousing operations that do not rely on protection from neighboring competitive uses."*
Analysis: Stage 7 generically flags exclusivity enforcement gaps as adverse. Stage 5e recognizes
that for a standard warehousing tenant, exclusivity enforcement matters little — their core
operations do not depend on exclusive use rights. Compounded by 5e's own instability on LP-20.

**DOCTRINAL IMPLICATION:** `gap_impact` may need to be **demoted from a sign/direction field to a
consequence-context field**, or split into `gap_direction` (what the gap does to tenant protection)
and `gap_materiality_in_use` (how much it matters for this use). Treating `gap_impact` as a sign
field when it was designed as a materiality/use-consequence field is the likely source of the conflict
— a schema/doctrine finding for 375E-DIR, not a 375K code change.

**Proven claim:** Both conflicts share the same root structure: Stage 7 assesses GENERIC DIRECTIONAL PROTECTION (is there a provision protecting the tenant?), while Stage 5e assesses USE-AWARE CONSEQUENCE (does the gap actually hurt THIS tenant?). They are measuring different axes, not the same axis. LP-05 cause = favorable_absence (a missing restriction benefits this tenant). LP-20 cause = use_specific_override (a missing protection matters little for this use). DOCTRINAL IMPLICATION: gap_impact may need to be demoted from a sign/direction field to a consequence-context field, or split into gap_direction (what the gap does to tenant protection) and gap_materiality_in_use (how much it matters for this use). Treating gap_impact as a sign field when it was designed as a materiality/use-consequence field is the likely source of the conflict -- a schema/doctrine finding for 375E-DIR, not a 375K code change.

**Caveat:** n=2 conflict cases, n=1 lease. The cause classification is a hypothesis, not a proven taxonomy. LP-20's cause classification is tentative given 5e's own instability on that LP.

**Still unmeasured:** Whether the favorable_absence and use_specific_override patterns appear systematically across leases, or whether this lease's warehouse-specific profile makes them atypically common. Whether gap_impact can be cleanly demoted/split without breaking the existing 5e evaluation framework.

---

## Q5 — Stability of 5e gap_impact in conflict cases

| LP | 5e gap_impact | Stable? | Q3 unique values | Evidentiary weight |
|---|---|---|---|---|
| LP-05 | favorable | **YES** | [favorable] | STRONG — reliable counter-signal across all 10 replays |
| LP-20 | neutral | **NO** | ['adverse', 'context_dependent', 'neutral'] | WEAK — wobbling signal; cannot be asserted cleanly |

**Proven claim:** The two conflicts have asymmetric evidence quality.
LP-05's stable favorable signal is substantive doctrinal evidence.
LP-20's unstable neutral signal may not reflect a genuine disagreement.

**Caveat / Still unmeasured:** see Q4.

---

## Q6 — Rule D sanity check: reproduces 375J Q6?

**PASS — Rule D reproduces 375J Q6's 0-divergence result exactly.**

375J Q6 reference: *"direction gate not exercised by this n=1 artifact. Non-divergence proves
the lease was too one-sided to stress the sign axis, NOT that direction is decorative."*

Rule D (Stage7-only) routes all 8 eligible LPs identically to 375J Policy B with Stage 7 direction:
LP-03/05/10/14/16/26/32 → actionable_material_risk; LP-20 → low_materiality.
0 divergences between Rule D and 375J Policy E (direction-ignored), confirming the port is correct.

**CRITICAL NEW FINDING — Rule E vs Rule D:**
When 5e is the sign axis (Rule E), **LP-05 diverges**: Rule D → Risk (Stage7=adverse), Rule E →
improvement_favorable (5e=favorable). This confirms that when 5e is the sign axis, the direction
gate IS exercised — exactly the divergence 375J noted was absent under Stage 7 direction.

375J Q6's non-divergence was a property of the Stage7-direction axis. It was not a property
of the lease or the doctrine. The direction gate is load-bearing when 5e is the sign axis.

**Proven claim:** Rule D = faithful port of 375J Q6 Stage7-direction baseline. SANITY CHECK PASSES.

**Caveat / Still unmeasured:** see Q6 in results JSON.

---

## Decision summary

| Finding | Implication |
|---|---|
| Q1: 2/26 sign_conflict | Not dominant but not isolated. LP-05 is load-bearing. |
| Q2: LP-05 stable, LP-20 unstable | Sign hierarchy must handle asymmetric evidence quality. |
| Q3: A/C routes LP-05 to NR; B routes to improvement | Key production-candidate difference. |
| Q4: favorable_absence + use_specific_override | gap_impact is a consequence field, not a sign field. Consider demotion/split in 375E-DIR schema. |
| Q5: LP-05 stable evidence; LP-20 weak evidence | Any rule giving LP-20 conflict weight ≈ LP-05 weight is miscalibrated. |
| Q6: Rule D = 375J Q6 exactly (PASS). Rule E exposes LP-05 divergence. | Direction gate IS load-bearing when 5e is sign axis. Non-divergence was an axis artifact. |

**Diagnostic-safe interim:** any Stage7<->5e sign conflict → Needs Review.
Routing as asserted Risk on a sign conflict silently resolves the disagreement in the system's favor.
