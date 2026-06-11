# Step 383 — DEF-010a Live Recall Stability Results

Generated: 2026-06-11 12:19:21 UTC

## 1. Commit and Environment Confirmation

- Expected commit: `d134ef8`
- Actual HEAD: `d134ef8`
- Underpowered: False
- N runs completed: 10

### Non-goals verification
- `lease_verdict_distance.py` unchanged: `_PRESENCE_TIER` NOT present in that file (confirmed by grep)
- `_FLAGGED_STATES` unchanged: contains exactly `missing, partial_material, partial_typical, review_needed`
- DEF-010b not implemented: `covered` NOT in `_FLAGGED_STATES`
- Raw per-evaluator verdict provenance: preserved (verified from artifacts where available)
- No new lawyer-facing findings added
- No cam/core/ changes

## 2. Run Log

| Run | job_id | Status | Quality | API calls | Elapsed | Dir | CRX | Risk | RN | Imp |
|-----|--------|--------|---------|-----------|---------|-----|-----|------|----|-----|
| 1 | `81625_6a7716` | completed | unknown | 94 | 1501.0s | 27 | 6 | 14 | 2 | 11 |
| 2 | `25328_0774c7` | completed | clean | 94 | 1578.0s | 26 | 6 | 9 | 12 | 5 |
| 3 | `11252_a845ff` | completed | clean | 94 | 1556.3s | 26 | 7 | 14 | 3 | 9 |
| 4 | `13848_504920` | completed | clean | 94 | 1449.6s | 27 | 6 | 15 | 4 | 8 |
| 5 | `20258_23cbb9` | completed | clean | 93 | 1513.0s | 25 | 6 | 12 | 5 | 8 |
| 6 | `22811_109280` | completed | clean | 92 | 1506.5s | 24 | 6 | 11 | 4 | 9 |
| 7 | `02924_96c08c` | completed | clean | 94 | 1563.7s | 24 | 6 | 13 | 1 | 10 |
| 8 | `05528_f52761` | completed | clean | 94 | 1539.2s | 27 | 4 | 14 | 2 | 11 |
| 9 | `12107_66a036` | completed | clean | 94 | 1462.7s | 27 | 5 | 15 | 2 | 10 |
| 10 | `14530_9026f5` | completed | clean | 94 | 1497.7s | 27 | 7 | 6 | 16 | 5 |

## 3. LP-13 Spotlight (per run)

| Run | job_id | coverage_state | in_Stage7 | Per-eval labels (negligence_carveouts) | Merged | Hard case? |
|-----|--------|---------------|-----------|---------------------------------------|--------|------------|
| 1 | `6a7716` | `covered` | no | `explicitly_present / explicitly_present / implicitly_present` | `explicitly_present` | no |
| 2 | `0774c7` | `covered` | no | `implicitly_present / explicitly_present / implicitly_present` | `explicitly_present` | no |
| 3 | `a845ff` | `covered` | no | `implicitly_present / explicitly_present / covered_by_default_law` | `explicitly_present` | YES |
| 4 | `504920` | `covered` | no | `implicitly_present / explicitly_present / implicitly_present` | `explicitly_present` | no |
| 5 | `23cbb9` | `covered` | no | `explicitly_present / explicitly_present / implicitly_present` | `explicitly_present` | no |
| 6 | `109280` | `covered` | no | `explicitly_present / explicitly_present / implicitly_present` | `explicitly_present` | no |
| 7 | `96c08c` | `covered` | no | `explicitly_present / explicitly_present / explicitly_present` | `explicitly_present` | no |
| 8 | `f52761` | `covered` | no | `explicitly_present / explicitly_present / covered_by_default_law` | `explicitly_present` | no |
| 9 | `66a036` | `covered` | no | `implicitly_present / explicitly_present / implicitly_present` | `explicitly_present` | no |
| 10 | `9026f5` | `covered` | no | `implicitly_present / explicitly_present / implicitly_present` | `explicitly_present` | no |

### LP-13 hard-case definition
A run is a **hard case** if all evaluators returned presence-tier labels (`explicitly_present`, `implicitly_present`, `covered_by_default_law`, `covered_in_other_LP`) AND all labels were distinct (no single label repeated). Pre-DEF-010a, this produced a Counter split → no majority → `unclear`. DEF-010a collapses all presence-tier labels to `present_like` before the Counter, so all three count together → unanimous majority → expands to most-explicit label.

## 4. LP-13 Stability Verdict

- LP-13 coverage state distribution: {'covered': 10}
- LP-13 Stage 7 inclusion rate: 0/10
- LP-13 final finding rate: 0/10
- LP-13 Risk rate: 0/10
- **observed_stable_covered_across_runs: True**
- **hard_case_seen: True**

**LP-13 deterministically covered and not forwarded across all 10 runs.**
**Hard case confirmed: the scattered presence-tier pattern (all distinct) recurred in at least one run — DEF-010a actively corrected it.**

## 5. Other Spotlight Findings

| LP | Appearances | Buckets | Consequence | Materiality | Stable? |
|----|-------------|---------|-------------|-------------|---------|
| LP-02 | 10/10 | ['review_needed', 'risk'] | ['harmful'] | ['medium'] | False |
| LP-03 | 8/10 | ['review_needed', 'risk'] | ['harmful'] | ['high', 'medium'] | False |
| LP-09 | 8/10 | ['improvement', 'review_needed'] | ['beneficial', 'context_dependent', 'neutral'] | ['low', 'medium'] | False |
| LP-16 | 10/10 | ['risk'] | ['harmful'] | ['high', 'medium'] | True |
| LP-18 | 10/10 | ['improvement', 'review_needed', 'risk'] | ['beneficial', 'context_dependent', 'harmful'] | ['low', 'medium'] | False |
| LP-19 | 8/10 | ['improvement', 'review_needed', 'risk'] | ['beneficial', 'context_dependent', 'harmful', 'neutral'] | ['high', 'medium', 'not_applicable'] | False |
| LP-25 | 10/10 | ['review_needed', 'risk'] | ['context_dependent', 'harmful'] | ['high', 'low', 'medium'] | False |
| LP-26 | 8/10 | ['improvement', 'review_needed', 'risk'] | ['beneficial', 'context_dependent', 'harmful', 'neutral'] | ['high', 'low'] | False |

### Material risk disappearances
- LP-03: 8/10 | buckets: ['review_needed', 'risk'] | consequence: ['harmful'] | materiality: ['high', 'medium']
- LP-19: 8/10 | buckets: ['improvement', 'review_needed', 'risk'] | consequence: ['beneficial', 'context_dependent', 'harmful', 'neutral'] | materiality: ['high', 'medium', 'not_applicable']
- LP-26: 8/10 | buckets: ['improvement', 'review_needed', 'risk'] | consequence: ['beneficial', 'context_dependent', 'harmful', 'neutral'] | materiality: ['high', 'low']

## 6. Metrics Tables

### Candidate Recall Stability
- Unique directional finding identities: 27
- Findings in all 10 runs: 22 — ['LP-01', 'LP-02', 'LP-04', 'LP-05', 'LP-06', 'LP-07', 'LP-10', 'LP-11', 'LP-14', 'LP-15', 'LP-16', 'LP-18', 'LP-20', 'LP-21', 'LP-22', 'LP-24', 'LP-25', 'LP-27', 'LP-28', 'LP-29', 'LP-30', 'LP-32']
- Findings in only 1 run: 0 — []
- Risk findings in all 10 runs: 4 — ['LP-10', 'LP-14', 'LP-16', 'LP-32']
- Harmful high/medium findings in all 10 runs: 15 — ['LP-02', 'LP-05', 'LP-06', 'LP-07', 'LP-10', 'LP-14', 'LP-16', 'LP-18', 'LP-21', 'LP-22', 'LP-25', 'LP-27', 'LP-28', 'LP-29', 'LP-32']

### Bucket Stability
- Findings with stable bucket: 7
- Findings flipping Risk ↔ non-Risk: 14 — ['LP-02', 'LP-03', 'LP-05', 'LP-06', 'LP-07', 'LP-18', 'LP-19', 'LP-21', 'LP-22', 'LP-25', 'LP-26', 'LP-27', 'LP-28', 'LP-29']

### Per-Finding Detail Table

| LP | Rate | Buckets | Consequence | Materiality | Stable | Ever Risk | Material Risk Candidate |
|----|------|---------|-------------|-------------|--------|-----------|------------------------|
| LP-01 | 10/10 | ['improvement', 'review_needed'] | ['context_dependent', 'neutral'] | ['low'] | False | False | False |
| LP-02 | 10/10 | ['review_needed', 'risk'] | ['harmful'] | ['medium'] | False | True | True |
| LP-03 | 8/10 | ['review_needed', 'risk'] | ['harmful'] | ['high', 'medium'] | False | True | True |
| LP-04 | 10/10 | ['review_needed'] | ['context_dependent'] | ['low', 'medium'] | True | False | False |
| LP-05 | 10/10 | ['improvement', 'review_needed', 'risk'] | ['beneficial', 'harmful'] | ['medium'] | False | True | True |
| LP-06 | 10/10 | ['review_needed', 'risk'] | ['context_dependent', 'harmful'] | ['high', 'low', 'medium'] | False | True | True |
| LP-07 | 10/10 | ['review_needed', 'risk'] | ['context_dependent', 'harmful'] | ['high', 'low', 'medium'] | False | True | True |
| LP-09 | 8/10 | ['improvement', 'review_needed'] | ['beneficial', 'context_dependent', 'neutral'] | ['low', 'medium'] | False | False | False |
| LP-10 | 10/10 | ['risk'] | ['harmful'] | ['high', 'medium'] | True | True | True |
| LP-11 | 10/10 | ['improvement', 'review_needed'] | ['beneficial', 'context_dependent'] | ['high', 'low', 'medium'] | False | False | False |
| LP-14 | 10/10 | ['risk'] | ['harmful'] | ['medium'] | True | True | True |
| LP-15 | 10/10 | ['improvement'] | ['neutral'] | ['low'] | True | False | False |
| LP-16 | 10/10 | ['risk'] | ['harmful'] | ['high', 'medium'] | True | True | True |
| LP-17 | 8/10 | ['improvement', 'review_needed'] | ['context_dependent', 'neutral'] | ['low'] | False | False | False |
| LP-18 | 10/10 | ['improvement', 'review_needed', 'risk'] | ['beneficial', 'context_dependent', 'harmful'] | ['low', 'medium'] | False | True | True |
| LP-19 | 8/10 | ['improvement', 'review_needed', 'risk'] | ['beneficial', 'context_dependent', 'harmful', 'neutral'] | ['high', 'medium', 'not_applicable'] | False | True | True |
| LP-20 | 10/10 | ['improvement'] | ['harmful', 'neutral'] | ['low', 'not_applicable'] | True | False | False |
| LP-21 | 10/10 | ['review_needed', 'risk'] | ['context_dependent', 'harmful'] | ['high', 'low', 'medium'] | False | True | True |
| LP-22 | 10/10 | ['improvement', 'review_needed', 'risk'] | ['beneficial', 'harmful', 'neutral'] | ['high', 'low'] | False | True | True |
| LP-24 | 10/10 | ['improvement', 'review_needed'] | ['neutral'] | ['low'] | False | False | False |
| LP-25 | 10/10 | ['review_needed', 'risk'] | ['context_dependent', 'harmful'] | ['high', 'low', 'medium'] | False | True | True |
| LP-26 | 8/10 | ['improvement', 'review_needed', 'risk'] | ['beneficial', 'context_dependent', 'harmful', 'neutral'] | ['high', 'low'] | False | True | True |
| LP-27 | 10/10 | ['review_needed', 'risk'] | ['context_dependent', 'harmful'] | ['high', 'low', 'medium'] | False | True | True |
| LP-28 | 10/10 | ['improvement', 'review_needed', 'risk'] | ['context_dependent', 'harmful', 'neutral'] | ['high', 'medium'] | False | True | True |
| LP-29 | 10/10 | ['review_needed', 'risk'] | ['context_dependent', 'harmful'] | ['low', 'medium'] | False | True | True |
| LP-30 | 10/10 | ['improvement', 'review_needed'] | ['context_dependent', 'harmful', 'neutral'] | ['low'] | False | False | False |
| LP-32 | 10/10 | ['risk'] | ['harmful'] | ['high', 'medium'] | True | True | True |

## 7. Variance Classification

| LP | Variance type | Field |
|-----|---------------|-------|
| LP-01 | consequence_changed | use_consequence direction changed |
| LP-02 | mismatch_support_changed | evaluator verdict variance |
| LP-03 | candidate_absent | not generated in all runs |
| LP-05 | consequence_changed | use_consequence direction changed |
| LP-06 | consequence_changed | use_consequence direction changed |
| LP-07 | consequence_changed | use_consequence direction changed |
| LP-09 | candidate_absent | not generated in all runs |
| LP-11 | consequence_changed | use_consequence direction changed |
| LP-17 | candidate_absent | not generated in all runs |
| LP-18 | consequence_changed | use_consequence direction changed |
| LP-19 | candidate_absent | not generated in all runs |
| LP-21 | consequence_changed | use_consequence direction changed |
| LP-22 | consequence_changed | use_consequence direction changed |
| LP-24 | mismatch_support_changed | evaluator verdict variance |
| LP-25 | consequence_changed | use_consequence direction changed |
| LP-26 | candidate_absent | not generated in all runs |
| LP-27 | consequence_changed | use_consequence direction changed |
| LP-28 | consequence_changed | use_consequence direction changed |
| LP-29 | consequence_changed | use_consequence direction changed |
| LP-30 | consequence_changed | use_consequence direction changed |

## 8. Interpretation

**Case B**: DEF-010a validated (LP-13 deterministic or not a recall issue), but other material harmful Risk findings still flicker. Push d134ef8 (fix itself is safe), but DEF-002 remains blocked by broader recall instability.

- push_d134ef8: True
- def002_blocked: True

### LP-13 hard-case caveat
**hard_case_seen = True.** The scattered all-present-tier no-majority pattern (e.g. EP / CD / IP) recurred at least once in this sample. DEF-010a actively resolved it, producing a deterministic `covered` outcome in that run. The live recall test DID re-test the original failure mode.

## 9. Non-goals Verification
1. `lease_verdict_distance.py` unchanged: grep confirms `_PRESENCE_TIER` does NOT appear in that file.
2. `_FLAGGED_STATES` unchanged: confirmed as `{{missing, partial_material, partial_typical, review_needed}}`.
3. DEF-010b not implemented: `covered` NOT added to `_FLAGGED_STATES` (verified from source).
4. Raw per-evaluator verdict provenance: preserved — `evaluator_verdicts[]` still shows original A/B/C labels.
5. No new lawyer-facing findings added: only coverage normalization changed in DEF-010a.
6. No cam/core/ changes: DEF-010a change is in `lease_coverage_305.py` only.