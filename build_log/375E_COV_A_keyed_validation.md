# 375E-COV-A Keyed Validation Report

**Date:** 2026-06-05
**Run ID:** lease_review_20260604_033046_52adbf
**Artifact path:** C:\Users\Owner\OneDrive\CAM\05 Lease Analyzer\results\lease_review_20260604_033046_52adbf\tenant_0\pipeline_results.json
**Mode:** PRE-COV-A BASELINE (52adbf, pre-771f1ef)

> **BASELINE NOTICE:** This report was run against the frozen pre-COV-A artifact
> (52adbf, last modified 2026-06-03). COV-A fields are ABSENT by design -- this
> artifact predates commit 771f1ef. Sections below show the pre-COV-A state for
> context. **Verdict is HOLD until a fresh post-771f1ef keyed artifact is validated.**

> **Re-run command** (after Tzvi's local pipeline completes):
> ```
> python build_log/_375ecova_keyed_validate.py <path/to/fresh/pipeline_results.json>
> ```

## Verdict: HOLD

Baseline mode: running against pre-COV-A frozen artifact (52adbf). COV-A fields are absent by design -- this artifact predates commit 771f1ef. HOLD PUSH until fresh post-771f1ef keyed artifact is validated.

### Six Push Criteria

  [~] (1) use_consequence write-path correct (new LP use_impact has use_consequence key): N/A (baseline artifact)
  [~] (2) gap_impact absent from new LP use_impact records: N/A (baseline artifact)
  [~] (3) COV-A fields populated on all directional findings (use_consequence_source present): N/A (baseline artifact)
  [~] (4) routing/buckets do not empirically drift (routing fields unchanged on all 32 findings): N/A (baseline artifact)
  [~] (5) no major parse/no_evaluators failure across the 18 newly-admitted findings (>= 14/18 decisive): N/A (baseline artifact)
  [~] (6) CRX not falsely treated as LP-level assessed (compound_consequence_source = not_assessed only): N/A (baseline artifact)

---

## A. 375M Write-Path Closure

**Mode:** baseline (pre-375M artifact -- gap_impact present is EXPECTED)

- LPs with use_impact: 8
- Has gap_impact key: 8 (expected for pre-375M artifact)
- Has use_consequence key: 0 (expected: 0 for pre-375M artifact)

EXPECTED: frozen 52adbf artifact pre-dates a939b01 (375M deploy). gap_impact present is correct for this artifact. Fresh post-a939b01 artifact should have use_consequence only.

---

## B. COV-A Field Population

**Mode:** baseline -- COV-A fields ABSENT (expected for pre-COV-A artifact)

Directional findings: 26 (none have COV-A fields)
Compound findings: 6 (no compound_consequence_source yet)

---

## C. Empirical Routing-Drift Check

> **FRAMING:** The keyless 0-drift check was STRUCTURAL (additive-only field writes, 
> routing drift structurally impossible). This is the EMPIRICAL confirmation --
> routing fields compared field-by-field between fresh artifact and frozen 52adbf baseline.
> These are different claims; the structural argument does not prove empirical 0-drift.

**Mode:** baseline -- not applicable (no fresh artifact to compare against).

---

## D. Yield Table (Four Groups)

**Mode:** baseline -- only LP-scope use_impact shown for 8 already-assessed LPs.

### Group 1: Already-assessed 8 (LP-scope use_impact, copied in COV-A)

| Finding | LP | use_consequence | materiality | confidence |
|---------|-----|-----------------|-------------|------------|
| Dir-03 | LP-03 | harmful | high | assert |
| Dir-05 | LP-05 | beneficial | medium | assert |
| Dir-08 | LP-10 | harmful | high | assert |
| Dir-10 | LP-14 | harmful | medium | assert |
| Dir-12 | LP-16 | harmful | high | assert |
| Dir-16 | LP-20 | neutral | low | assert_weak |
| Dir-21 | LP-26 | harmful | high | assert |
| Dir-26 | LP-32 | harmful | medium | assert |

### Groups 2, 3, 4: PENDING -- keyed run required

---

## E. Thin-Gap Diagnostic (Design Signal)

> Thin-gap LPs: LP-01/11/24/25 (<20% element-gap %). These are admitted by G-cand
> (finding-triggered) but NOT by A33 threshold. Whether they assess DECISIVELY is a
> design signal for COV-B and the shelved A-rail, not a pass/fail gate.

PENDING -- keyed run required. Thin-gap LPs are LP-01/11/24/25 (<20% missing). Decisive = design signal that G-cand works on mostly-complete LPs. Abstain = evidence base for shelved A-rail and COV-B Needs-Review landing.

---

## F. LP-05 Sanity Check

**Mode:** baseline

LP-05 LP-scope use_impact: use_consequence=beneficial, materiality=medium
Dir-05 directionality: tenant_unprotected

Pre-COV-A: no finding-level use_consequence on Dir-05. LP-05 use_impact shows beneficial from LP-scope 5e. Fresh keyed artifact should show Dir-05 use_consequence=beneficial, stage7_direction=tenant_unprotected, no sign_conflict field.

---

## G. LP-20 Stability Watch (Record Only)

> LP-20 is a WATCH item, not a gate. Single run result does not prove stability.

- LP-scope use_impact: use_consequence=neutral, confidence=assert_weak
- LP-scope raw keys: ['gap_impact', 'materiality', 'use_reasoning', 'confidence', 'evaluator_agreement']

LP-20 is a WATCH item, not a pass/fail gate. Known: 2-1 assert_weak in frozen 52adbf. Record this run's value without resolving stability -- single keyed result does not prove stability.

---

## Summary Verdict: HOLD

Baseline mode: running against pre-COV-A frozen artifact (52adbf). COV-A fields are absent by design -- this artifact predates commit 771f1ef. HOLD PUSH until fresh post-771f1ef keyed artifact is validated.
