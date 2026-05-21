# Step 355 Code Status — Supplement #21 Phase 2: Element Criticality Annotations

**Date:** 2026-05-20
**SHA:** 550323d
**Status:** COMPLETE

---

## Final Distribution

| Level | Count | % of total |
|-------|-------|-----------|
| critical | 53 | 25.0% |
| important | 130 | 61.3% |
| supplementary | 29 | 13.7% |
| **TOTAL** | **212** | — |
| missing | 0 | — |

Distribution is within all three spec ranges:
- Critical: 20–35% ✓ (25.0%)
- Important: 50–65% ✓ (61.3%)
- Supplementary: 5–15% ✓ (13.7%)

`criticality` is the second key in every element dict (after `element_id`). Schema version: 2.2.0. Updated: 2026-05-20.

---

## Overrides Applied (19 total)

### Algorithm-based overrides (14 elements)

Elements where the algorithm produced `critical` but an override rule demoted it to `important`:

| Element ID | Override Rule | Reason |
|-----------|--------------|--------|
| LP-08.cgl_minimum | `absence_adverse_to == "landlord"` | Absence hurts landlord's insurance recovery, not tenant |
| LP-09.assignment_requires_landlord_consent | `absence_adverse_to == "landlord"` | Absence of consent requirement benefits tenant |
| LP-09.subletting_requires_landlord_consent | `absence_adverse_to == "landlord"` | Same |
| LP-11.default_definition_monetary | `absence_adverse_to == "landlord"` | Missing default definition limits landlord's enforcement |
| LP-11.default_definition_non_monetary | `absence_adverse_to == "landlord"` | Same |
| LP-11.landlord_right_to_terminate_lease | `absence_adverse_to == "landlord"` | Absence limits landlord remedies |
| LP-11.landlord_right_to_reenter_premises | `absence_adverse_to == "landlord"` | Same |
| LP-11.rent_acceleration_remedy | `absence_adverse_to == "landlord"` | Same |
| LP-13.tenant_indemnification_scope | `absence_adverse_to == "landlord"` | Narrow scope limits landlord's indemnification recovery |
| LP-19.service_interruption_remedies | `cross_LP_coverage` set | Coverage may exist via LP-14 / LP-26 |
| LP-21.guarantor_identity | `absence_adverse_to == "landlord"` | Absence limits landlord's guaranty enforcement |
| LP-21.guarantee_scope | `absence_adverse_to == "landlord"` | Same |
| LP-22.lease_subordinate_to_mortgages | `absence_adverse_to == "landlord"` | Without subordination, landlord's financing is harder |
| LP-22.tenant_attornment_to_successor | `absence_adverse_to == "landlord"` | Absence benefits tenant (continuity risk is landlord's) |

### Force overrides — spec IDs → actual element IDs (5 elements)

| Spec ID | Actual element ID matched | Change |
|---------|--------------------------|--------|
| LP-04.security_deposit_amount | LP-04.deposit_amount | already critical (algorithm agrees) |
| LP-11.cure_period_tenant | LP-11.cure_period_non_monetary | important → **critical** |
| LP-22.snda_obligation_exists | LP-22.landlord_obligation_obtain_snda_existing_lenders | important → **critical** |
| LP-27.right_to_cure_notice | LP-27.notice_required_to_landlord | important → **critical** |
| LP-32.pre_existing_contamination_carve_out | LP-32.landlord_pre_existing_representations | already critical (algorithm agrees) |

---

## LP-by-LP Criticality (6 key LPs)

### LP-01 (Rent & Payment Terms)
| Element | Criticality |
|---------|------------|
| LP-01.base_rent_amount | **critical** |
| LP-01.payment_due_date | important |
| LP-01.late_payment_fee | important |
| LP-01.grace_period | **critical** |
| LP-01.accepted_payment_methods | supplementary |
| LP-01.additional_rent_definition | important |

### LP-02 (Rent Escalation)
| Element | Criticality |
|---------|------------|
| LP-02.annual_increase_mechanism | **critical** |
| LP-02.effective_date_of_first_escalation | important |
| LP-02.escalation_cap | **critical** |
| LP-02.calculation_methodology | important |

### LP-11 (Tenant Default & Landlord Remedies)
| Element | Criticality |
|---------|------------|
| LP-11.default_definition_monetary | important |
| LP-11.default_definition_non_monetary | important |
| LP-11.default_definition_tenant_insolvency | important |
| LP-11.cure_period_monetary | important |
| LP-11.cure_period_non_monetary | **critical** (forced) |
| LP-11.notice_required_to_trigger_cure_period | **critical** |
| LP-11.landlord_right_to_terminate_lease | important |
| LP-11.landlord_right_to_reenter_premises | important |
| LP-11.rent_acceleration_remedy | important |
| LP-11.damages_calculation_and_mitigation | important |
| LP-11.reletting_rights_and_obligations | important |
| LP-11.self_help_landlord_cure | important |
| LP-11.common_law_remedies_preserved | important |
| LP-11.remedies_cumulative_not_exclusive | important |
| LP-11.abandonment_default | important |
| LP-11.diligent_pursuit_extension | **critical** |
| LP-11.mortgagee_guarantor_cure_right | important |

### LP-22 (SNDA)
| Element | Criticality |
|---------|------------|
| LP-22.lease_subordinate_to_mortgages | important |
| LP-22.subordination_scope_includes_future_mortgages | important |
| LP-22.subordination_mechanism_self_executing | important |
| LP-22.tenant_executes_subordination_documents_on_request | important |
| LP-22.non_disturbance_protection_for_tenant | **critical** |
| LP-22.non_disturbance_source_is_binding | **critical** |
| LP-22.non_disturbance_obligation_for_future_lenders | important |
| LP-22.tenant_attornment_to_successor | important |
| LP-22.attornment_mechanism_self_executing | supplementary |
| LP-22.snda_execution_timing_and_default_consequence | important |
| LP-22.landlord_obligation_obtain_snda_existing_lenders | **critical** (forced) |

### LP-27 (Landlord Default & Tenant Remedies)
| Element | Criticality |
|---------|------------|
| LP-27.landlord_default_definition | **critical** |
| LP-27.notice_required_to_landlord | **critical** (forced) |
| LP-27.cure_period_for_landlord | important |
| LP-27.tenant_self_help_and_offset | important |
| LP-27.tenant_right_to_terminate | important |
| LP-27.tenant_right_to_damages | important |
| LP-27.tenant_right_to_specific_performance | supplementary |
| LP-27.lender_notice_and_cure_right | important |
| LP-27.common_law_remedies_preserved | important |
| LP-27.remedies_cumulative_not_exclusive | important |

### LP-32 (Hazardous Materials)
| Element | Criticality |
|---------|------------|
| LP-32.hazmat_definition | **critical** |
| LP-32.de_minimis_carveout | **critical** |
| LP-32.prohibition_on_hazmat | important |
| LP-32.tenant_remediation_obligation | important |
| LP-32.landlord_pre_existing_representations | **critical** (confirmed by algorithm) |
| LP-32.tenant_testing_right | important |
| LP-32.notification_requirement | important |
| LP-32.survival_after_expiration | important |

---

## Pipeline Changes (`lease_coverage_305.py`)

### Change A — criticality pass-through (line ~764-771)

```python
criticality = element.get("criticality", "important")  # Phase 2 pass-through

verdict_record = {
    "element_id": element_id,
    "criticality": criticality,  # Phase 2 pass-through
    "element_label": element_label,
    "verdict": merged["verdict"],
    ...
}
```

### Change B — dispute counters (lines ~758-791, ~874-875)

Initialization:
```python
elements_disputed_critical = 0   # Step 355: Phase 2 criticality counters
elements_disputed_important = 0  # Step 355: Phase 2 criticality counters
```

Increment in disputed branch:
```python
elif merged["verdict"] == "disputed":
    elements_disputed.append(element_label)
    if criticality == "critical":        # Step 355
        elements_disputed_critical += 1
    elif criticality == "important":
        elements_disputed_important += 1
```

LP output dict additions:
```python
"elements_disputed_critical": elements_disputed_critical,   # Step 355 Phase 2
"elements_disputed_important": elements_disputed_important, # Step 355 Phase 2
```

---

## Live Run Validation

Live T-10 run NOT performed (would require Railway deploy + full run). Static validation confirms:
- All 212 elements have criticality field ✓
- Field is second key in every element dict ✓
- Schema 2.2.0 ✓
- Pipeline syntax-checked clean ✓
- New counters initialized and incremented correctly ✓

Phase 3 routing not implemented in this step.

---

## Decisions Needed

None. Phase 3 implementation is a separate step.
