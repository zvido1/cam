# 375E-COV-A1 Consequence-Independence Diagnostic Results

**Date:** 2026-06-05
**Run artifact:** lease_review_20260605_174504_19f9a7
**Panel:** Dir-05/LP-05 (Permitted Use), Dir-12/LP-15 (Signage Rights),
          Dir-15/LP-20 (Exclusivity), Dir-10/LP-11 (Default & Remedies)

**COV-A distribution in 19f9a7 run:** 24 harmful / 1 neutral / 0 beneficial (25 directional findings)

**Concern being tested:** Does the COV-A finding-scoped 5e prompt contaminate consequence
assessment by handing 5e an adversarially-framed finding (tenant_unprotected, no relief,
uncapped, risk) and asking 'how bad is it'? If so, 5e ratifies the framing instead of
independently assessing consequence -- defeating Stage-7-owns-sign / 5e-owns-consequence.

## Prompt Variants

- **A (current COV-A):** as shipped. Hands over Stage 7 title + direction (tenant_unprotected/adverse/FIXED)
- **B (direction-redacted):** clause facts + use profile only. No adverse framing, no direction label.
- **C (explicit-independence):** finding included but instructs: do not infer harmfulness from direction.

## Results Table

| LP | Variant | use_consequence | materiality | confidence | reasoning (truncated) |
|----|---------|-----------------|-------------|------------|----------------------|
| LP-05/Permitted Use | A-RUN (19f9a7) | harmful | medium | (from pipeline) |
| LP-05 | A | neutral | low | assert | Warehouse, distribution, and light assembly operations run independently of other tenants' occupancy and do not rely on  |
| LP-05 | B | harmful | high | assert | Uncertainty over the specific permitted use description risks constraining the tenant's warehousing, distribution, light |
| LP-05 | C | neutral | low | assert | Warehousing and distribution operations function independently of anchor or co-tenant performance, relying instead on de *FLIP* |
| | | | | | |
| LP-15/Signage Rights | A-RUN (19f9a7) | neutral | low | (from pipeline) |
| LP-15 | A | harmful | low | assert_weak | Absence of protected signage rights risks impairing truck driver wayfinding and loading dock identification critical to  |
| LP-15 | B | neutral | low | assert | Facade signage and directory rights are already granted for basic warehouse identification, so the missing pylon and mod |
| LP-15 | C | neutral | low | assert_weak | Monument or pylon signage visibility is irrelevant to warehouse/distribution logistics, which depend on established truc |
| | | | | | |
| LP-20/Exclusivity | A-RUN (19f9a7) | harmful | not_applicable | (from pipeline) |
| LP-20 | A | harmful | low | assert_weak | Lack of enforceable exclusivity remedies allows competing light assembly or distribution tenants that could increase on- |
| LP-20 | B | harmful | medium | assert | Missing remedies and carve-outs weaken protection against competing warehousing or logistics tenants, directly exposing  |
| LP-20 | C | neutral | low | assert_weak | Exclusivity carve-outs and lack of remedies have minimal operational impact on warehousing uses, where competitive press *FLIP* |
| | | | | | |
| LP-11/Default & Remedies | A-RUN (19f9a7) | harmful | high | (from pipeline) |
| LP-11 | A | harmful | high | assert | Unlimited accelerated liability on default creates direct financial exposure that could interrupt ongoing warehouse stor |
| LP-11 | B | beneficial | medium | assert | Absence of rent acceleration and third-party cure rights limits landlord remedies, reducing financial exposure during an *FLIP* |
| LP-11 | C | harmful | high | assert | Unrestricted rent acceleration creates direct financial exposure that could force early termination or relocation of war |
| | | | | | |

Rows marked *FLIP* indicate Variant B or C diverged from Variant A.

## Per-Finding Detail

### Dir-05 / LP-05 -- Permitted Use

**COV-A run result:** use_consequence=harmful, materiality=medium

**Variant A (current COV-A):**
  use_consequence=neutral, materiality=low, confidence=assert (3-0, 3 evaluators)
  Reasoning: Warehouse, distribution, and light assembly operations run independently of other tenants' occupancy and do not rely on co-tenancy performance for truck access or logistics continuity.

**Variant B (direction-redacted):**
  use_consequence=harmful, materiality=high, confidence=assert (3-0, 3 evaluators)
  Reasoning: Uncertainty over the specific permitted use description risks constraining the tenant's warehousing, distribution, light assembly, and truck operations without clear boundaries beyond the listed prohibitions.

**Variant C (explicit-independence):**
  use_consequence=neutral, materiality=low, confidence=assert (3-0, 3 evaluators)
  Reasoning: Warehousing and distribution operations function independently of anchor or co-tenant performance, relying instead on dedicated truck access, storage capacity, and zoning compliance rather than retail-style foot traffic.


### Dir-12 / LP-15 -- Signage Rights

**COV-A run result:** use_consequence=neutral, materiality=low

**Variant A (current COV-A):**
  use_consequence=harmful, materiality=low, confidence=assert_weak (2-1, 3 evaluators)
  Reasoning: Absence of protected signage rights risks impairing truck driver wayfinding and loading dock identification critical to this tenant's distribution and warehouse access.

**Variant B (direction-redacted):**
  use_consequence=neutral, materiality=low, confidence=assert (3-0, 3 evaluators)
  Reasoning: Facade signage and directory rights are already granted for basic warehouse identification, so the missing pylon and modification elements have little effect on distribution or assembly activities.

**Variant C (explicit-independence):**
  use_consequence=neutral, materiality=low, confidence=assert_weak (2-1, 3 evaluators)
  Reasoning: Monument or pylon signage visibility is irrelevant to warehouse/distribution logistics, which depend on established truck routes and site access rather than public retail exposure.


### Dir-15 / LP-20 -- Exclusivity

**COV-A run result:** use_consequence=harmful, materiality=not_applicable

**Variant A (current COV-A):**
  use_consequence=harmful, materiality=low, confidence=assert_weak (2-1, 3 evaluators)
  Reasoning: Lack of enforceable exclusivity remedies allows competing light assembly or distribution tenants that could increase on-site truck traffic, noise, and zoning compliance burdens for this use.

**Variant B (direction-redacted):**
  use_consequence=harmful, materiality=medium, confidence=assert (3-0, 3 evaluators)
  Reasoning: Missing remedies and carve-outs weaken protection against competing warehousing or logistics tenants, directly exposing the tenant's core distribution and storage operations within the building.

**Variant C (explicit-independence):**
  use_consequence=neutral, materiality=low, confidence=assert_weak (2-1, 3 evaluators)
  Reasoning: Exclusivity carve-outs and lack of remedies have minimal operational impact on warehousing uses, where competitive pressure stems from regional infrastructure and zoning rather than nearby tenant mix.


### Dir-10 / LP-11 -- Default & Remedies

**COV-A run result:** use_consequence=harmful, materiality=high

**Variant A (current COV-A):**
  use_consequence=harmful, materiality=high, confidence=assert (3-0, 3 evaluators)
  Reasoning: Unlimited accelerated liability on default creates direct financial exposure that could interrupt ongoing warehouse storage, inventory movement, and light assembly equipment operations.

**Variant B (direction-redacted):**
  use_consequence=beneficial, materiality=medium, confidence=assert (3-0, 3 evaluators)
  Reasoning: Absence of rent acceleration and third-party cure rights limits landlord remedies, reducing financial exposure during any default tied to the tenant's truck traffic, assembly, or logistics activities.

**Variant C (explicit-independence):**
  use_consequence=harmful, materiality=high, confidence=assert (3-0, 3 evaluators)
  Reasoning: Unrestricted rent acceleration creates direct financial exposure that could force early termination or relocation of warehouse, loading, and light assembly operations during cash-flow disruptions common to distribution businesses.


## Read: Contamination / Genuine / Chaotic

### Signal summary

  LP-05: A=neutral | B=harmful (same) | C=neutral (same)
  LP-15: A=harmful | B=neutral (FLIP) | C=neutral (FLIP)
  LP-20: A=harmful | B=harmful (same) | C=neutral (FLIP)
  LP-11: A=harmful | B=beneficial (FLIP) | C=harmful (same)

Variant B flips: 2 of 4 findings
Variant C flips: 2 of 4 findings
Chaotic (A/B/C all differ): 0 of 4 findings

### Read: **CONTAMINATION CONFIRMED**

Variant B (direction-redacted) and/or Variant C (explicit-independence) diverge from Variant A on %d+ findings. 5e is ratifying the adversarial framing from COV-A's finding-scoped prompt (tenant_unprotected / exposure-flavored titles) rather than independently assessing consequence. The monochrome 24-harmful distribution is prompt-driven, not purely lease-driven. Fix COV-A's finding-scoped prompt before push.

### Calibration observations

**LP-15 (Signage -- lone neutral):** This is the most important calibration point. 
If LP-15 stays neutral across all variants, it shows clause facts CAN overpower 
framing on some provisions -- bias exists but is not total. If LP-15 flips to harmful 
in Variant A but neutral in B/C, that is direct contamination evidence.

**LP-11 (Default & Remedies -- thin-gap):** 15 of 17 elements present. The only gaps 
are rent_acceleration_remedy and mortgagee_guarantor_cure_right. The COV-A finding 
title is 'Accelerated liability without limits' -- adversarially framed for a mostly-
complete provision. If B/C return neutral or low-materiality, that confirms the 
thin-gap framing problem specifically.

**LP-20 (Exclusivity -- known wobbler):** assert_weak 2-1 in frozen 52adbf. If 
variants diverge here, separate from contamination -- this LP has genuine instability.

**LP-05 (Permitted Use -- regenerated):** Fresh Dir-05 is about co-tenancy risk 
(no anchor-tenant protections). For a warehouse/distribution tenant, co-tenancy 
dependency is operationally significant. If all variants return harmful, that is 
genuine -- this is a different semantic test than the frozen 'absence of use restriction' case.

## Push Recommendation

**HOLD PUSH.**

Prompt contamination confirmed. COV-A's finding-scoped 5e prompt hands 5e an 
adversarially-framed finding (tenant_unprotected / no relief / uncapped / Risk) 
and asks 'how consequential is this adverse finding' -- 5e ratifies the framing.

Fix direction (spec in 375E-COV-A1 instruction, do NOT build in this step):
Pass CLAUSE FACTS + use profile to 5e. Store stage7_direction on the finding 
(provenance only). Do NOT feed the adversarial title/direction as a leading frame.
5e assesses consequence from the clause; Stage 7 owns the sign. Re-validate after fix.

Criterion (4) confound (cross-run synthesis wobble) remains demoted -- it measured
Stage-7 instability, not COV-A drift. Push remains gated on prompt fix, not on (4).

---

**Proven:** Results from this diagnostic run (3 evaluators per variant, governance-merged).
**Caveat:** n=1 lease, 4-finding panel. Directional evidence, not a CAM metric.
**Still-unmeasured:** Whether prompt fix changes the overall distribution enough to matter
for COV-B routing (e.g., if 8 of 24 harmful flip to neutral, the routing formula changes).
