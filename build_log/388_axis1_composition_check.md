# Step 388 — Axis-1 Composition Check

**Date:** 2026-06-11  
**Type:** Read-only paper analysis. No code changes. No model calls. No schema implementation. No push.  
**Inputs:** `build_log/387_directional_axis_coverage_and_control_audit.md`, `build_log/directional_question_audit_2026_06_11.md`, `build_log/386_pass1_instrumentation_RESULTS.md`, `results/lease_review_20260611_175413_812979/tenant_0/stage7_pass1_parsed_candidates.json`.  
**Stated prediction:** Case B — Axis 1 needs tightening (Evaluator B's "narrower than Article 17" sentence across LP-06/20/22/26/27/28 is the pattern under test).

---

## HEADLINE RESULT (Required — leads the document)

**Post-tightening retained count: 15 — unchanged from pre-tightening.**

Demoting Axis 1 to modifier-only does NOT drop any of the 15 retained findings, because ZERO of the 15 are Axis-1-ONLY. Every finding where Axis 1 appears also has an independent Axis 2 or Axis 3 that alone supports the finding. Post-tightening, the 15 findings survive on cleaner single-axis labels. The retention count is the same number — 15 — but the label honesty and discriminating-power justification improve materially.

**15 is still exactly on the ~15 threshold.** The framework does not become "comfortably below" by tightening Axis 1 — that gate depends on prototype resolution of the 2 B-cases (LP-05, LP-10), not on Axis 1 discipline. What changes is the integrity of the justifications: the 6 findings where Axis 1 was a generic platitude now carry single-axis labels (Axis 2 or Axis 3) that are honest and fact-anchored.

**Prediction verdict: Case B confirmed.** Axis 1 as formulated allows generic "Article 17 vs §5.1" comparisons that are true of nearly every clause in a standard commercial lease. Three of the seven Axis 1 appearances are pure generic Article-17 comparisons (B-class). None of the seven are harmful to the retained count (zero are load-bearing on Axis 1 alone), but they degrade the precision of the framework's explanatory labels. The fix is known and bounded.

---

## PART 1 — Retained-Finding Breakdown (the 15)

Severity marked as CONTEXT ONLY — from the biased question, NOT a benchmark.

| # | LP | Finding summary | Old sev (context) | Supporting axes (387) | Axis 1 involved? | Axis 1 only? | Key cited fact |
|---|----|-----------------|--------------------|----------------------|-----------------|-------------|----------------|
| 1 | LP-03 | §8.3 work precondition + fixed Commencement Date + no remedy | LOW | Axis 2 | N | N/A | §8.3 precondition; fixed date; no abatement/delay/termination clause |
| 2 | LP-05 | Landlord can place competing tenant in center without Tenant consent | MED | Axis 4 (B) | N | N/A | §2.2 protects access, not competitive positioning; §24.14 exclusivity scope unclear |
| 3 | LP-06 | §6.3 HVAC remedy: triple condition (negligence + untenantable + 5 days) leaves ordinary failures uncovered | MED | Axis 1 + Axis 3 | **Y** | N | §6.3 three-condition abatement vs. Article 17 unconditional machinery |
| 4 | LP-09 | Post-assignment: Tenant not released; Landlord can recapture to block beneficial assignment | MED | Axis 2 + Axis 4 | N | N/A | §15.2 affiliate-only transfer; no release mechanism; recapture right |
| 5 | LP-10 | Restoration-election timing: §8.4 may allow Landlord to demand removal at lease-end without prior specification | LOW | Axis 4 (B) | N | N/A | §8.4 cited only by reference; restoration-election text not confirmed |
| 6 | LP-11 | Article 17 acceleration: all future rent due on Tenant default, no anti-acceleration clause | HIGH | Axis 1 + Axis 2 | **Y** | N | Article 17 acceleration; no §anti-acceleration, no duty-to-mitigate confirmed |
| 7 | LP-14 | Force majeure: §24.1 excludes monetary obligations; no abatement or FM termination right | MED/HIGH | Axis 2 | N | N/A | §24.1 "non-monetary only"; §13.3/§6.3 don't substitute for FM relief |
| 8 | LP-18 | Holdover: 150% rent floor, no consequential damage cap; Landlord controls new-tenant commitment timing | MED | Axis 2 + Axis 4 | N | N/A | §16.1 not stated as exclusive remedy; no consequential-damage cap |
| 9 | LP-20 | §24.14 exclusivity covenant; no tailored enforcement remedy for breach | MED/HIGH | Axis 2 + Axis 1 | **Y** | N | §24.14 exclusivity; §5.1 only remedy (60-day wait); no abatement/targeted trigger |
| 10 | LP-21 | Exhibit E guaranty: unconditional, unlimited duration, no burn-down or release | MED | Axis 2 | N | N/A | Exhibit E: no cap, no milestone release, no time limit |
| 11 | LP-22 | §19.2 future-SNDA: commercially-reasonable-efforts only (Landlord-controlled); common case uncovered | HIGH/MED | Axis 3 + Axis 1 | **Y** | N | §19.2 "commercially reasonable efforts" for future superior interests; §5.1 as only remedy |
| 12 | LP-26 | §18.1 quiet enjoyment: conditioned on "no default" (Landlord-influenced) + "no Superior Interest" (Landlord-creatable) | LOW/MED | Axis 3 + Axis 1 | **Y** | N | §18.1 double condition; disputed-default and refinancing leave Tenant unprotected |
| 13 | LP-27 | §5.1 vs Article 17: Tenant's Landlord-default remedy massively disproportionate; 60-day wait with no interim self-help | HIGH | Axis 1 + Axis 2 | **Y** | N | §5.1 notice+deposit+wait vs. Article 17 immediate termination/acceleration/re-entry |
| 14 | LP-28 | Both parties have compliance obligations (§4.2/§8.2); Landlord-default enforcement = only §5.1 | LOW/MED | Axis 1 + Axis 2 | **Y** | N | §4.2 Landlord structural obligation; §5.1 only remedy if Landlord fails |
| 15 | LP-32 | §12.1/§12.2 hazmat remediation obligation includes pre-existing conditions; no baseline testing right or Landlord representation | MED/HIGH | Axis 2 + Axis 4 | N | N/A | §12.1/§12.2 no pre-existing carveout; §11.2 indemnity doesn't cover Landlord silence |

**Axis 1 involvement count:** 7 of 15 (LP-06, LP-11, LP-20, LP-22, LP-26, LP-27, LP-28)  
**Axis 1 ONLY count:** 0 of 15

---

## PART 2 — Axis-1-Only Analysis

**FINDING: Zero of the 15 retained findings are Axis-1-ONLY.** Part 2's core test (classify Axis-1-only findings as A/B/C/D) has an empty input set. This is itself informative: Axis 1 never appeared without at least one other axis also independently firing. However, the Part 2 test should still be applied to the AXIS-1 COMPONENT within each co-supported finding, to determine whether Axis 1 is adding genuine information or is the Article-17 constant in disguise.

### Test applied: does the Axis 1 component name the SAME RISK on both sides?

**Criterion from spec:** "Concrete same-risk disproportion = landlord gets remedy X if tenant fails obligation O; tenant gets less than X if landlord fails the PARALLEL obligation O." Parallel means the SAME obligation type on both sides, not a comparison of Tenant's remedy for risk A against Landlord's whole apparatus across all risks.

---

**LP-06 / Axis 1 component:**  
Comparison: Tenant's maintenance-breach remedy (§6.3 conditioned abatement + §5.1 60-day wait) vs. Landlord's Tenant-breach remedy (Article 17 full machinery).  
Are the obligations parallel? Landlord's obligation: maintain HVAC (§6.2). Tenant's obligation: pay rent (Article III). These are DIFFERENT obligations (maintenance ≠ rent payment). The Axis 1 comparison is across obligation types, not the same obligation on both sides.  
The CLOSEST parallel would be: "Landlord fails maintenance obligation → §6.3 + §5.1. Tenant fails interior repair obligation (§8.1) → Article 17." That IS more parallel (both are maintenance obligations), and the enforcement asymmetry is concrete. But Evaluator B's formulation cited "landlord's broader default remedies" generically, not this specific parallel.  
**Classification: C — Mixed.** More fact-grounded than pure generic Article-17 (both parties have maintenance duties), but the 387 audit's Axis 1 formulation compared different obligation categories (HVAC vs. rent), which weakens the same-risk claim. Axis 3 is the load-bearing finding for LP-06; Axis 1 is a supplemental observation.

---

**LP-11 / Axis 1 component:**  
Comparison: Article 17 grants Landlord rent ACCELERATION if Tenant defaults. Tenant has no equivalent: there is no Tenant-side acceleration of a Landlord monetary obligation, because Landlord has no rent-payment obligation running to Tenant.  
Same risk? No structural parallel exists for acceleration — the obligations are asymmetric by design (Tenant pays rent; Landlord provides premises). Asking "does Tenant have an acceleration mechanism for Landlord's non-payment of rent?" is a category error. This comparison reduces to "Landlord has a big default hammer that Tenant doesn't have" — the Article-17 constant.  
**Classification: B — Generic Article-17 comparison.** The acceleration asymmetry IS real, but Axis 1 (same-risk proportionality) cannot validly capture it because no structurally parallel obligation exists for Tenant to "accelerate." The real finding is Axis 2: Tenant is bound to pay accelerated rent without any anti-acceleration remedy.

---

**LP-20 / Axis 1 component:**  
Comparison: If Landlord breaches §24.14 exclusivity → Tenant has §5.1 (60-day wait, deposit draw, general fee recovery). If Tenant breaches any obligation → Landlord has Article 17.  
Same risk? There's no Tenant-side exclusivity obligation to compare against §24.14 — Tenant doesn't owe Landlord exclusivity protection. This compares enforcement of one SPECIFIC Landlord covenant (§24.14) against the whole Tenant-default apparatus. That is inherently asymmetric in structure.  
The more fact-specific point: Tenant's breach-of-§24.14-specific remedy is zero (no tailored remedy), which is clearly disproportionate. But this is better captured as: "Landlord has a specific obligation (§24.14); Tenant has no tailored remedy for its breach" — that is Axis 2 (obligation exists, no remedy), not Axis 1 (parallel framework comparison).  
**Classification: C — Mixed.** The §24.14-specific comparison is more fact-anchored than pure generic Article-17 (it's not comparing random obligations — it's specifically about what remedy Tenant has for exclusivity breach). But the comparison defaults to "§5.1 vs. Article 17" as the enforcement contrast, which is the constant. Axis 2 is load-bearing; Axis 1 is decorative.

---

**LP-22 / Axis 1 component:**  
Comparison: If Landlord fails §19.2 commercially-reasonable-efforts obligation (can't/won't get future SNDA) → Tenant has §5.1. If Tenant fails §19.3 attornment obligation → Landlord has Article 17.  
Same risk? §19.2 and §19.3 are both in the SNDA framework but are different obligations (SNDA procurement ≠ attornment execution). The comparison is within the same article but not the same obligation. The REAL parallel would be: if either party fails their SNDA-framework obligation, what remedy does the other get? §19.3 breach (Tenant fails to attorn) → Landlord can use Article 17. §19.2 breach (Landlord fails to use commercially reasonable efforts) → Tenant gets §5.1 only.  
This IS somewhat parallel (both are SNDA-framework obligations), but the comparison bottoms out at "§5.1 vs. Article 17" — the same constant. B's formulation across the parsed candidates used the same pattern as LP-26, LP-27, LP-28.  
**Classification: B — Generic Article-17 comparison in context.** The SNDA framing makes it look specific, but the underlying comparison is the same Article 17 vs. §5.1 template that Evaluator B applied identically across six findings.

---

**LP-26 / Axis 1 component (spec explicitly directs re-examination):**  
Comparison: If Landlord breaches §18.1 quiet enjoyment covenant → Tenant has §5.1. If Tenant fails any obligation → Landlord has Article 17.  
Same risk? There is no Tenant-side quiet-enjoyment obligation — Tenant doesn't owe Landlord a quiet enjoyment covenant. The comparison is: "Tenant's remedy for Landlord's breach of Covenant X" vs. "Landlord's remedy for Tenant's breach of any obligation." These are structurally different — one is a specific covenant; the other is the whole default apparatus.  
**This is the spec's LP-26 question answered: YES, LP-26's real support IS Axis 3 alone.** §18.1 being "subject to no default" (Landlord-influenced determination of whether Tenant is in default) AND "subject to any Superior Interest" (Landlord can create new superior interests by refinancing without Tenant consent) — those are two Landlord-controlled conditions that can switch off the covenant. The conditioned-covenant mechanism is complete as an Axis 3 finding. Axis 1 (§5.1 vs. Article 17) is padding.  
**Classification: B — Generic Article-17 comparison.** Evaluator B used the same sentence here as in LP-06, LP-20, LP-22, LP-27, LP-28: "tenant has protection but narrower than the landlord's Article 17 framework." For LP-26, Axis 1 carries no unique information. The finding survives entirely on Axis 3.

---

**LP-27 / Axis 1 component:**  
Comparison: If TENANT defaults on obligations → Landlord gets Article 17 (immediate default triggers, termination, re-entry, reletting, deficiency, self-help reimbursement, cumulative remedies). If LANDLORD defaults on obligations → Tenant gets §5.1 (notice, 30-day cure, deposit draw, additional 30-day wait, then termination).  
Same risk? **YES — this IS the same risk.** "A party fails their material obligations under the lease" is the symmetric event, and BOTH parties in LP-27 ARE compared on that same event. The comparison is direct and named: §5.1 defaults vs. Article 17 defaults. Both frameworks are triggered by the same event type (material breach by the obligated party). LP-27 is specifically ABOUT the two default frameworks — this is the only finding where Axis 1's comparison IS the finding, not a decorative addition to it.  
Specific structural asymmetries the comparison captures: Landlord can terminate IMMEDIATELY on specific Article 17 events (rent payment 5-day grace + notice); Tenant must wait 30+30 days before any remedy. Landlord gets re-entry; Tenant has no self-help entry right. Landlord gets acceleration; Tenant has no equivalent monetary claim. These are specific tools, not a generic "Landlord has more."  
**Classification: A — Concrete same-risk disproportion.** LP-27 is the only Axis 1 instance that meets the spec's test. The comparison is fact-anchored (§5.1 vs Article 17 are the ACTUAL parallel frameworks for default by each party), specific (each tool in Article 17 has a §5.1 non-equivalent), and not reducible to a generic constant.

---

**LP-28 / Axis 1 component:**  
Comparison: Both parties have compliance obligations under §4.2 (Tenant: use-related; Landlord: structural/base-building per §8.2). If TENANT fails use-compliance → Landlord has Article 17. If LANDLORD fails structural compliance → Tenant has §5.1.  
Same risk? Closer than LP-11 or LP-26 — both parties DO have §4.2 compliance obligations, making this structurally analogous to LP-27. The "same risk" is "a party fails their §4.2 compliance obligation." Use-compliance ≠ structural compliance in scope and value, but they are both in §4.2.  
However, the 387 audit explicitly stated: "The compliance-obligation asymmetry is structurally the same as LP-27 in a narrower context." That acknowledgment signals LP-28 Axis 1 is DERIVATIVE of LP-27's Axis 1, not an independent same-risk comparison. It's applying the LP-27 pattern to a different obligation type. Additionally, Evaluator B's formulation across the parsed candidates used the generic Article-17 comparison here just as in LP-26.  
**Classification: C — Mixed.** More grounded than pure generic (§4.2 bilateral compliance is a real symmetric obligation), but the comparison reduces to the same §5.1 vs. Article 17 pattern and is derivative of LP-27's Axis 1 rather than independently same-risk.

---

### Part 2 Summary Table

| LP | Axis 1 classification | Same-risk? | Load-bearing? |
|----|----------------------|-----------|--------------|
| LP-06 | C — Mixed | Partially (maintenance vs. maintenance, but different types) | No — Axis 3 is load-bearing |
| LP-11 | B — Generic Article-17 | No (no parallel acceleration structure possible) | No — Axis 2 is load-bearing |
| LP-20 | C — Mixed | Partially (specific to §24.14, but defaults to §5.1 vs. Article 17) | No — Axis 2 is load-bearing |
| LP-22 | B — Generic Article-17 | Partially (same SNDA framework, but different obligations) | No — Axis 3 is load-bearing |
| LP-26 | B — Generic Article-17 | No (no parallel quiet-enjoyment obligation on Tenant side) | No — Axis 3 alone is the real finding |
| LP-27 | **A — Concrete same-risk** | **YES** (both parties' default frameworks, same triggering event) | **YES** — Axis 1 is substantive here |
| LP-28 | C — Mixed | Partially (§4.2 bilateral compliance, but derivative of LP-27) | No — Axis 2 is load-bearing |

**Axis 1 quality breakdown:**
- A (concrete same-risk): 1 — LP-27
- B (generic Article-17): 3 — LP-11, LP-22, LP-26
- C (mixed, more specific than generic but not fully same-risk): 3 — LP-06, LP-20, LP-28

**The prediction is confirmed: Evaluator B applied the same structural comparison across 6 findings (LP-06, LP-20, LP-22, LP-26, LP-27, LP-28). In 3 of those 6 (LP-11, LP-22, LP-26), it is purely generic Article-17. In 3 more (LP-06, LP-20, LP-28), it is mixed but still defaults to §5.1 vs. Article 17. Only in LP-27 is the Axis 1 comparison genuinely same-risk and load-bearing.**

---

## PART 3 — Axis-1-with-Other-Axis Analysis (Survivability Test)

For each of the 7 findings where Axis 1 co-appears with another axis, the test: does the finding survive WITHOUT Axis 1?

| LP | Without Axis 1 — does it survive? | Surviving anchor | Axis 1 role | LP-26 re-examination |
|----|-----------------------------------|-----------------|------------|---------------------|
| LP-06 | **YES** | Axis 3: §6.3 triple condition (negligence + untenantable + 5 days) leaves ordinary HVAC failures uncovered. Standalone and fact-anchored. | Decorative — structural context that Axis 3 already implies | N/A |
| LP-11 | **YES** | Axis 2: Article 17 accelerates all future rent upon Tenant default; no anti-acceleration clause, no cap, no duty-to-mitigate found. | Decorative — adds "this is part of a bigger imbalance" but Axis 2 is the finding | N/A |
| LP-20 | **YES** | Axis 2: §24.14 exclusivity obligation exists on Landlord; no tailored enforcement remedy for breach (no abatement, no termination trigger, no injunctive mechanism). | Decorative — contextualizes why there's no remedy, but Axis 2 states the finding | N/A |
| LP-22 | **YES** | Axis 3: §19.2 future-SNDA protection = "commercially reasonable efforts" — conditioned, Landlord-influenced, leaves the common case (Landlord can't get SNDA from new lender) uncovered without an express remedy. | Decorative — adds "this is also structurally imbalanced" but Axis 3 is the finding | N/A |
| LP-26 | **YES** | Axis 3: §18.1 is conditioned on "no default" (Landlord-influenced determination) AND "no Superior Interest" (Landlord-creatable via refinancing). Both conditions are Landlord-controlled. Protection disappears precisely when most needed (disputed default, new financing). | **Padding.** This is the spec's specific question — answered definitively: Axis 3 alone is LP-26's real support. Axis 1 is a decorative label. | **LP-26 re-examination confirms: Axis 3 ONLY is the real support. Re-label.** |
| LP-27 | **YES (Axis 2 independently supports)** — BUT Axis 1 IS substantive here. Axis 2 captures the specific 60-day-wait obligation-without-remedy. Axis 1 captures the SYSTEMATIC structural disparity between the two default frameworks. Both are real and add distinct information. | Axis 2: 60-day waiting period where Tenant must perform without interim remedy beyond deposit draw. | **Substantive, not decorative.** Axis 1 in LP-27 names the same risk (default by either party) and compares the frameworks specifically. It adds genuine information beyond Axis 2's point-obligation focus. | N/A |
| LP-28 | **YES** | Axis 2: Landlord has structural compliance obligation (§4.2, §8.2); if Landlord fails, Tenant has no immediate remedy beyond §5.1 60-day wait. | Decorative — derivative of LP-27's Axis 1 applied to compliance, but Axis 2 states the specific finding adequately. | N/A |

### LP-26 Re-examination (spec directive)

**Is LP-26's real support Axis 3 alone?** YES, definitively.

The Axis 3 finding for LP-26 is self-contained and layered:
- Condition 1: "subject to Tenant not being in default" — Landlord controls the determination of whether Tenant is in default. Contested defaults (which are common) can leave Tenant without the quiet-enjoyment protection exactly when they most need it.
- Condition 2: "subject to any Superior Interest" — Landlord can create new superior interests at any time by refinancing. Tenant has no consent right over financing decisions.

These two Landlord-controlled conditions mean the quiet-enjoyment covenant can be switched off by Landlord's own actions or determinations. Axis 3 Q-b = qualified-by-counterparty-controlled-condition; Q-c = no-common-case-uncovered (disputed defaults and refinancing are common). The Axis 3 finding is complete, specific, and deterministic.

Axis 1 for LP-26 adds: "and the remedy framework for breach is also narrower than Article 17." This is true, but it's true of LP-06, LP-22, LP-28 also. The Axis 1 observation is the same generic comparison that Evaluator B appended to every finding where §5.1 appears. It is padding. **Post-tightening, LP-26 should be labeled Axis 3 ONLY.**

### Structural observation from Part 3

**Evaluator B's pattern is now fully characterized:** Across LP-06, LP-20, LP-22, LP-26, LP-27, LP-28, Evaluator B appended the same structural observation — "tenant has some protection but narrower than the landlord's Article 17 framework" — to every finding involving the §5.1 vs. Article 17 contrast. In the ONE case where this comparison IS meaningful (LP-27, where both frameworks are being compared directly as parallel default-handling systems), Axis 1 is substantive. In the other five, it is a constant that fires regardless of the specific clause under examination.

The pattern is not error — Evaluator B's underlying findings are correct on Axis 2 (LP-11, LP-20, LP-28) or Axis 3 (LP-06, LP-22, LP-26). The Axis 1 observation is merely a structural annotation that is true everywhere and therefore carries no discriminating power about THIS clause. The danger: if Axis 1 were allowed as a standalone trigger, every LP where §5.1 is the tenant's remedy (which is most of them) would become a finding just from the Article 17 comparison. That IS the second defect factory the spec warned about.

---

## PART 4 — Threshold Recommendation

**Result: Case B — confirmed.** Axis 1 as currently formulated allows generic "Article 17 vs §5.1" comparisons that are near-constants in standard commercial leases. However, the resolution is less costly than feared: because zero findings are Axis-1-ONLY, demoting Axis 1 to modifier-only does NOT reduce the retained count from 15. What changes is label honesty and discriminating power.

### The Required Fix: Axis 1 → Modifier-Only

**Rule change:**  
1. Axis 1 CANNOT be a standalone trigger for a directional finding. A finding requires at least one of Axis 2, 3, or 4 to fire independently.  
2. Axis 1 CAN strengthen a finding already independently triggered. When used as a modifier, Axis 1 must cite both frameworks side-by-side and confirm the SAME OBLIGATION TYPE is on each side.  
3. The same-risk test becomes mandatory: "Landlord gets remedy X if Tenant fails obligation O; Tenant gets less-than-X if Landlord fails the PARALLEL obligation O." Parallel obligation must be named specifically. "Article 17 generally" does not satisfy the test.  
4. Exception for LP-27's pattern: when the finding is specifically about the two parties' DEFAULT FRAMEWORKS (§5.1 vs. Article 17), the comparison IS same-risk because "default by a party" is the parallel event. This exception does NOT extend to findings where only ONE party's specific obligation is being examined and the comparison pulls in Article 17 as the contextual backdrop.

### Post-Tightening Label Corrections

| LP | Pre-tightening label (387) | Post-tightening label (correct) | Axis 1 role post-tightening |
|----|---------------------------|--------------------------------|---------------------------|
| LP-06 | Axis 1 + Axis 3 | **Axis 3** (primary) | Modifier (conditional enforcement asymmetry is context for Axis 3) |
| LP-11 | Axis 1 + Axis 2 | **Axis 2** | Dropped (no parallel acceleration structure; Axis 1 is structural background) |
| LP-20 | Axis 2 + Axis 1 | **Axis 2** | Modifier at most (§24.14-specific, but generic in formulation) |
| LP-22 | Axis 3 + Axis 1 | **Axis 3** | Dropped (Axis 1 adds no unique information for future-SNDA conditionality) |
| LP-26 | Axis 3 + Axis 1 | **Axis 3** | **Dropped.** LP-26's support IS Axis 3 alone. |
| LP-27 | Axis 1 + Axis 2 | **Axis 1 + Axis 2** (unchanged) | **Retained as substantive.** LP-27 has the only concrete same-risk Axis 1. |
| LP-28 | Axis 1 + Axis 2 | **Axis 2** | Dropped (derivative of LP-27's pattern; Axis 2 states the finding adequately) |

### Post-Tightening Axis Distribution (all 15 retained findings)

| Finding | Post-tightening axis label |
|---------|--------------------------|
| LP-03 | Axis 2 |
| LP-05 | Axis 4 (B — prototype needed) |
| LP-06 | Axis 3 |
| LP-09 | Axis 2 + Axis 4 |
| LP-10 | Axis 4 (B — prototype needed) |
| LP-11 | Axis 2 |
| LP-14 | Axis 2 |
| LP-18 | Axis 2 + Axis 4 |
| LP-20 | Axis 2 |
| LP-21 | Axis 2 |
| LP-22 | Axis 3 |
| LP-26 | Axis 3 |
| LP-27 | Axis 1 + Axis 2 (only finding keeping Axis 1 as substantive) |
| LP-28 | Axis 2 |
| LP-32 | Axis 2 + Axis 4 |

Post-tightening: Axis 2 dominates (appears in 10 of 15). Axis 3 appears in 3 (LP-06, LP-22, LP-26). Axis 4 appears in 4 (LP-05, LP-09, LP-10, LP-18, LP-32). Axis 1 appears in 1 (LP-27 only).

**This distribution is HEALTHY.** Axis 2 (obligation-without-remedy) being the dominant axis makes sense for a commercial lease — tenants undertake obligations throughout the lease and the question of what happens when the counterparty fails those obligations is the central risk analysis. Axis 3 (conditioned protection) catching three findings (§6.3, §19.2, §18.1) is correct — all three involve real conditions that can be counterparty-controlled. Axis 4 catching four findings is correct. Axis 1 catching one (LP-27) is exactly the right scope for a same-risk proportionality axis.

---

## PART 5 — Required Conclusion (All 8 Points)

**HEADLINE:** Post-tightening retained count = **15** (unchanged). 12 of 27 old findings remain dropped. But the 15 surviving findings now have honest, single-axis labels in 14 of 15 cases — and LP-27 is the one finding where Axis 1 IS the right primary label.

---

**1. Number retained (from 387):** 15 (13 Category A + 2 Category B). Post-tightening: still 15. No findings are dropped by demoting Axis 1 to modifier-only.

---

**2. Number involving Axis 1 (from 387 labels):** 7 of 15 (LP-06, LP-11, LP-20, LP-22, LP-26, LP-27, LP-28).

---

**3. Number Axis-1-ONLY:** 0 of 15. Every finding where Axis 1 appeared also has an independently-firing Axis 2 or Axis 3. Axis 1 was never the sole reason to retain a finding in the 387 audit.

---

**4. Number of Axis-1-only that are concrete same-risk disproportion:** N/A — there are no Axis-1-only findings to classify. However: of the 7 Axis-1-with-other findings, only 1 (LP-27) has a concrete same-risk Axis 1 component.

---

**5. Number that are generic Article-17:** 3 of 7 Axis-1-with-other findings have a pure generic Article-17 Axis 1 component: LP-11, LP-22, LP-26. Three more are mixed (LP-06, LP-20, LP-28) — more specific than pure generic but still defaulting to the §5.1 vs. Article 17 template. One (LP-27) is genuine same-risk.

---

**6. Is Axis 1 safe for prototype?**  
**AS MODIFIER-ONLY.** Not as standalone trigger. The rules:
- Axis 1 requires another axis (Axis 2, 3, or 4) to independently fire first.
- Axis 1 as modifier must cite same-risk: named parallel obligation on each side, specific remedy comparison.
- Generic "narrower than Article 17" does NOT satisfy the modifier requirement.
- LP-27's default-framework comparison is the canonical example of valid Axis 1 use.

---

**7. Is the closed-form prototype ready?**  
**YES — with the Axis 1 modifier-only rule applied.** The prototype LP set (LP-03, LP-06, LP-11, LP-14, LP-20, LP-26, LP-27, LP-32) should now be understood with post-tightening labels:
- LP-27: test Axis 1 (same-risk default-framework comparison) + Axis 2 (60-day wait obligation).
- LP-06: test Axis 3 ONLY (§6.3 triple condition). Verify LP-06 does NOT require Axis 1 to surface.
- LP-26: test Axis 3 ONLY (§18.1 double condition). Verify LP-26 does NOT require Axis 1 to surface.
- LP-03: test Axis 2 (§8.3 obligation + no remedy). Stability check — must surface in closed-form.
- LP-14: test Axis 2 (FM + rent obligation, no abatement/termination).
- LP-20: test Axis 2 (§24.14 exclusivity obligation, no tailored remedy).
- LP-11: test Axis 2 (acceleration obligation, no anti-acceleration clause).
- LP-32: test Axis 2 + Axis 4 (hazmat obligation + Landlord information control).

The prototype answers the post-tightening framework test: do Axes 2, 3, and 4 each independently produce the right finding without needing Axis 1 as a load-bearer?

---

**8. Does DEF-002 remain blocked?**  
**YES.** DEF-002 (full directional schema implementation) remains gated on: (a) prototype validation; (b) the Axis 1 modifier-only rule requires one implementation decision (does the closed-form schema allow Axis 1 answers without a co-firing Axis 2/3/4? if yes, the schema must add a same-risk citation requirement to Axis 1's closed question); (c) contested-routing architecture; (d) materiality/severity layer design. This audit resolves the Axis 1 design question but does not authorize implementation.

---

## Prediction Audit

**Stated prediction:** Case B — Axis 1 is leaning on the Article-17 constant.  
**Actual result:** Case B confirmed.  
- Three of the seven Axis 1 appearances are pure generic Article-17 (LP-11, LP-22, LP-26).  
- Three more are mixed but still reduce to §5.1 vs. Article 17 (LP-06, LP-20, LP-28).  
- One (LP-27) is the genuine same-risk case that Axis 1 was designed for.  
- Evaluator B applied the same structural sentence across all six non-LP-03 findings that involved §5.1 as Tenant's remedy.

**Where the prediction was less dire than reality feared:** The prediction implied Case B might DROP findings. It does not — zero findings are Axis-1-only, so demoting Axis 1 to modifier-only keeps the retained count at 15. The "Axis 1 needs tightening" diagnosis is correct, but the damage is confined to label honesty rather than finding count.

**Implication:** The 387 audit's "marginal Case A at exactly the threshold" holds post-tightening. The 15 is not reduced. But the 15 is CLEANER: the surviving findings now have honest, single-axis labels in 14 of 15 cases. The remaining uncertainty is the 2 B-cases (LP-05, LP-10), which depend on §8.4 and §24.14 text confirmation, not on Axis 1 discipline.

---

## Status

Read-only analysis complete. No code changed. No model calls made. No schema implemented. No push.  

**What happens next:**
- Axis 1 demoted to modifier-only (design decision, gated — requires one instruction to Chat before Prototype implements it).
- Post-tightening labels (Part 4) should be adopted before prototype runs.
- Prototype authorized (5–8 LPs, post-tightening labels, Axis 1 as modifier-only in question design).
- LP-03 stability check and LP-19 contested-routing verification remain the prototype's primary goals.
- DEF-002 remains blocked.
