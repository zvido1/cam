# Diagnostic 372-WV — Within-model variance probe

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Diagnostic/build-decision gate. No code changes, no reruns of full pipeline.
**Base SHA:** `2e759c8` (372D2).

---

## SCOPE STATEMENT (verbatim as required)

This is **n=1 contract**. The within-model variance RATE does NOT generalize to other
leases and must NEVER be cited as a CAM property, in the patent record, or as a
characterization metric. What (weakly) generalizes is only the DIRECTION/binary:
"models are broadly self-consistent on lease-provision verdicts" vs "models are
individually unstable." This is a build-decision gate for whether self-consistency
sampling could ever have a job — nothing more. Do not let any number here become a
claimed statistic.

---

## Method note: stored runs as resamples (no new API calls needed)

Before running 75–180 new calls, the production prompt identity was verified:

**Step 305 evaluator prompt (`_build_user_prompt`) is byte-identical across all 6 runs
for 11 of 12 flipping LPs** (LP-19 differs in run W1 due to a different `tenant_text`
extraction — 1 of 6 runs). Governing law (NY), NS signals, and element schemas are also
identical across runs.

With `temperature=0.0`, identical inputs SHOULD produce identical outputs. They do NOT —
the per-evaluator verdicts (`evaluator_verdicts` in stored `element_verdicts`) differ
across runs for the same (LP, model) pair despite byte-identical prompts. This confirms
**API-level non-determinism at temperature=0.0** across all three providers.

Consequence: the 6 stored per-evaluator verdicts per (LP, model, element) ARE N=6
independent resamples of the same production call. No new API calls are needed and were
not made. The resamples are authentic (real production infrastructure, real timing
variance, real batching effects) rather than synthetic.

**Classification scale (adapted for N=6):**
- SELF-CONSISTENT: same verdict 6/6
- MOSTLY-STABLE: dominant verdict 5/6 (equivalent to 4-1 in N=5)
- UNSTABLE: dominant verdict ≤4/6 (equivalent to 3-2 or worse in N=5)

---

## Per-LP/element per-model N=6 verdict distributions

Format: `{verdict: count} cites=n/6 → CLASSIFICATION`

### LP-03 / `expiration_date` — "Expiration date or method to determine it is stated"
```
A (Sonnet):  {unclear: 6}                          cites=6/6 → SELF-CONSISTENT
B (GPT):     {missing: 4, unclear: 2}              cites=5/6 → UNSTABLE (4/2)
C (Grok):    {missing: 6}                          cites=0/6 → SELF-CONSISTENT
```
Cross-model: A says unclear (stable); C says missing (stable) — genuine disagreement.

### LP-05 / `specific_permitted_use` — "Specific permitted use description is stated"
```
A (Sonnet):  {unclear: 6}                          cites=6/6 → SELF-CONSISTENT
B (GPT):     {missing: 6}                          cites=6/6 → SELF-CONSISTENT
C (Grok):    {missing: 5, explicitly_present: 1}   cites=1/6 → MOSTLY-STABLE (5/6)
```
Cross-model: A says unclear; B+C say missing.

### LP-05 / `co_tenancy_anchor_dependency` — "Co-tenancy or anchor tenant dependency addressed"
```
A (Sonnet):  {missing: 6}                          cites=0/6 → SELF-CONSISTENT
B (GPT):     {missing: 6}                          cites=6/6 → SELF-CONSISTENT
C (Grok):    {missing: 3, covered_in_other_LP: 3}  cites=3/6 → UNSTABLE (3/3)
```

### LP-09 / `change_of_control_addressed` — "Change of control is addressed"
```
A (Sonnet):  {missing: 6}                          cites=0/6 → SELF-CONSISTENT
B (GPT):     {missing: 5, explicitly_present: 1}   cites=1/6 → MOSTLY-STABLE (5/6)
C (Grok):    {explicitly_present: 2, missing: 4}   cites=2/6 → UNSTABLE (4/2)
```
Note: A and B reference Section 15.2 in reasoning text even when verdict=missing
(interpretation split, not retrieval miss — confirmed 372D2).

### LP-09 / `use_restrictions_bind_transferee` — "Use restrictions bind assignee/subtenant"
```
A (Sonnet):  {covered_in_other_LP: 6}              cites=6/6 → SELF-CONSISTENT
B (GPT):     {implicitly_present: 4, covered_in_other_LP: 2} cites=6/6 → UNSTABLE (4/2)
C (Grok):    {missing: 5, covered_in_other_LP: 1}  cites=1/6 → MOSTLY-STABLE (5/6)
```
Cross-model: A=covered_in_other_LP (stable), C=missing (mostly stable), B varies.

### LP-13 / `negligence_carveouts` — "Carve-outs for indemnitee's own negligence are addressed"
```
A (Sonnet):  {explicitly_present: 5, implicitly_present: 1}          cites=6/6 → MOSTLY-STABLE
B (GPT):     {implicitly_present: 5, covered_by_default_law: 1}       cites=6/6 → MOSTLY-STABLE
C (Grok):    {explicitly_present: 4, covered_by_default_law: 1, implicitly_present: 1} cites=5/6 → UNSTABLE (4/1/1)
```
All three find Section 11.2 (presence verdicts only). Instability is in which sub-class
of presence (explicit/implicit/default-law), not in whether the clause is found.

### LP-16 / `parking_cost` — "Parking cost is addressed"
```
A (Sonnet):  {implicitly_present: 6}               cites=6/6 → SELF-CONSISTENT
B (GPT):     {explicitly_present: 4, unclear: 1, implicitly_present: 1} cites=6/6 → UNSTABLE (4/1/1)
C (Grok):    {missing: 6}                          cites=0/6 → SELF-CONSISTENT
```
Cross-model: A says implicitly_present; C says missing — opposite stables. B varies.

### LP-19 / `installation_connection_costs` — "Responsibility for utility installation costs defined"
*(Note: LP-19 has different tenant_text in W1; W1 prompt differs from H1-H3.)*
```
A (Sonnet):  {implicitly_present: 5, unclear: 1}   cites=6/6 → MOSTLY-STABLE
B (GPT):     {implicitly_present: 5, unclear: 1}   cites=6/6 → MOSTLY-STABLE
C (Grok):    {missing: 5, implicitly_present: 1}   cites=1/6 → MOSTLY-STABLE
```
Cross-model: A+B ≈ implicitly_present; C ≈ missing.

### LP-19 / `utility_upgrade_costs` — "Responsibility for utility upgrade costs addressed"
```
A (Sonnet):  {implicitly_present: 3, unclear: 2, missing: 1} cites=5/6 → UNSTABLE (3/2/1)
B (GPT):     {missing: 6}                          cites=2/6 → SELF-CONSISTENT
C (Grok):    {missing: 5, unclear: 1}              cites=1/6 → MOSTLY-STABLE
```
Three distinct verdicts from A across 6 runs.

### LP-20 / `competing_use_definition` — "Definition of 'competing use' provided"
```
A (Sonnet):  {explicitly_present: 5, missing: 1}   cites=5/6 → MOSTLY-STABLE
B (GPT):     {explicitly_present: 6}               cites=6/6 → SELF-CONSISTENT
C (Grok):    {explicitly_present: 6}               cites=6/6 → SELF-CONSISTENT
```

### LP-20 / `existing_tenant_carveouts` — "Carve-outs for existing tenants addressed"
*(Note: LP-20's bucket flip is Stage 5e driven — see below.)*
```
A (Sonnet):  {missing: 6}                          cites=1/6 → SELF-CONSISTENT
B (GPT):     {missing: 4, explicitly_present: 2}   cites=6/6 → UNSTABLE (4/2)
C (Grok):    {explicitly_present: 2, missing: 4}   cites=2/6 → UNSTABLE (4/2)
```

### LP-22 / `landlord_obligation_obtain_snda_existing_lenders`
```
A (Sonnet):  {explicitly_present: 6}               cites=6/6 → SELF-CONSISTENT
B (GPT):     {explicitly_present: 3, missing: 3}   cites=4/6 → UNSTABLE (3/3 — perfect split)
C (Grok):    {explicitly_present: 6}               cites=6/6 → SELF-CONSISTENT
```
B is 50/50. A and C are rock-solid on the same Section 19.2 cite. **Within-model B
drives this flip entirely.** When B says missing, it does NOT cite Section 19.2 (3 runs);
when it says explicitly_present, it cites Section 19.2 (3 runs). Same prompt, random result.

### LP-22 / `non_disturbance_source_is_binding`
```
A (Sonnet):  {explicitly_present: 6}               cites=6/6 → SELF-CONSISTENT
B (GPT):     {explicitly_present: 6}               cites=6/6 → SELF-CONSISTENT
C (Grok):    {explicitly_present: 5, missing: 1}   cites=5/6 → MOSTLY-STABLE
```

### LP-26 / `constructive_eviction_addressed`
```
A (Sonnet):  {missing: 3, unclear: 2, implicitly_present: 1} cites=1/6 → UNSTABLE (3/2/1)
B (GPT):     {unclear: 4, covered_by_default_law: 1, covered_in_other_LP: 1} cites=5/6 → UNSTABLE (4/1/1)
C (Grok):    {missing: 5, covered_in_other_LP: 1}  cites=1/6 → MOSTLY-STABLE
```
Both A and B are highly unstable with 3 distinct verdicts each.

### LP-26 / `remedies_for_breach_of_quiet_enjoyment`
```
A (Sonnet):  {covered_in_other_LP: 3, unclear: 2, implicitly_present: 1} cites=4/6 → UNSTABLE (3/2/1)
B (GPT):     {covered_in_other_LP: 6}              cites=6/6 → SELF-CONSISTENT
C (Grok):    {missing: 3, covered_in_other_LP: 3}  cites=3/6 → UNSTABLE (3/3)
```
Cross-model: B says covered_in_other_LP (stable); C says missing 50% of the time.

### LP-28 / `grandfathering_pre_existing`
```
A (Sonnet):  {missing: 6}                          cites=0/6 → SELF-CONSISTENT
B (GPT):     {missing: 5, explicitly_present: 1}   cites=2/6 → MOSTLY-STABLE
C (Grok):    {explicitly_present: 4, missing: 2}   cites=4/6 → UNSTABLE (4/2)
```
C is the driver: when C says explicitly_present (cites Section 4.2), merge is disputed;
when C says missing, all three agree and merge is missing.

### LP-29 / `emergency_entry` — "Emergency entry without advance notice permitted and defined"
```
A (Sonnet):  {explicitly_present: 6}               cites=6/6 → SELF-CONSISTENT
B (GPT):     {unclear: 6}                          cites=6/6 → SELF-CONSISTENT
C (Grok):    {explicitly_present: 4, implicitly_present: 2} cites=6/6 → UNSTABLE (4/2)
```
Cross-model: A says explicitly_present; B says unclear — both perfectly consistent but
opposite verdicts. Section 21.1's "(except in the case of emergency)" parenthetical is
found by A+C but B consistently returns unclear despite citing it.

### LP-32 / `de_minimis_carveout`
```
A (Sonnet):  {explicitly_present: 3, missing: 3}   cites=6/6 → UNSTABLE (3/3 — perfect split)
B (GPT):     {explicitly_present: 6}               cites=6/6 → SELF-CONSISTENT
C (Grok):    {explicitly_present: 6}               cites=6/6 → SELF-CONSISTENT
```
A is 50/50. B and C are rock-solid on Section 12.1. A READS the clause in every run
(all 6 cite Section 12.1) but flips between "this qualifies as a de minimis carveout"
(3×) and "this doesn't" (3×).

---

## Stability cell counts

Per-model across 18 element cells (some LPs have 2 flipping elements):

| | SELF-CONSISTENT (6/6) | MOSTLY-STABLE (5/6) | UNSTABLE (≤4/6) |
|---|---|---|---|
| **A (Sonnet)** | **10** | 3 | **5** |
| **B (GPT)** | **8** | 4 | **6** |
| **C (Grok)** | **5** | 6 | **7** |
| Total | **23/54** | 13/54 | **18/54** |

**Most unstable: C (Grok) — 7 UNSTABLE cells. Then B (GPT) — 6. Then A (Sonnet) — 5.**
No single model is uniquely reliable; all three show within-model non-determinism.

---

## Within/cross-model decomposition per LP

| LP | Driving element(s) | Decomposition |
|---|---|---|
| LP-03 | expiration_date | **BOTH** — B unstable (within-model); A=unclear vs C=missing (cross-model) |
| LP-05 | specific_permitted_use + co_tenancy | **BOTH** — A vs B+C on specific (cross-model); C unstable on co_tenancy (within-model) |
| LP-09 | change_of_control + use_restrictions | **BOTH** — C unstable on change_of_control (within); A/B/C all different stable answers on use_restrictions (cross) |
| LP-13 | negligence_carveouts | **WITHIN-MODEL** — C unstable on sub-class of presence (explicit/implicit/default_law); all three find the clause |
| LP-16 | parking_cost | **BOTH** — A=implicitly_present vs C=missing (cross-model); B unstable (within-model) |
| LP-19 | installation + upgrade | **BOTH** — A+B vs C on installation (cross); A unstable on upgrade (within) |
| LP-20 | *Stage 5e driven* | **Stage 5e non-determinism** — elements show within-model variance on existing_carveouts, but bucket flip is `use_impact.gap_impact` changing `not_applicable` ↔ `low` — this is Stage 5e, not element-level |
| LP-22 | landlord_obligation_snda | **WITHIN-MODEL** — B is 50/50 on the same Section 19.2; A and C stable at present |
| LP-26 | constructive_eviction + remedies | **BOTH** — A and B unstable on eviction (within); B=covered vs C=missing on remedies (cross + within C) |
| LP-28 | grandfathering | **WITHIN-MODEL** — C unstable (4 present/2 missing); A stable at missing |
| LP-29 | emergency_entry | **BOTH** — A=EP vs B=unclear (cross-model, both stable); C minor wobble (within) |
| LP-32 | de_minimis_carveout | **WITHIN-MODEL** — A is 50/50 despite finding and citing the clause both times |

**Headline counts (excluding LP-20 Stage 5e):**

| Decomposition | Count |
|---|---|
| WITHIN-MODEL only | **4** (LP-13, LP-22, LP-28, LP-32) |
| BOTH (within + cross) | **7** (LP-03, LP-05, LP-09, LP-16, LP-19, LP-26, LP-29) |
| CROSS-MODEL only | **0** |
| Stage 5e (element-stable, downstream flip) | **1** (LP-20) |

**0 of 12 flips are cross-model only. 11 of 12 have a within-model component.** Within-model non-determinism is present in all three models at temperature=0.0 on identical prompts.

---

## Notable specific findings (no interpretation — data only)

1. **LP-22 landord_obligation_snda / B (GPT)**: B is exactly 50/50 (3 explicitly_present, 3 missing) across 6 identical prompts. When B says missing, it does not cite Section 19.2. When B says explicitly_present, it cites Section 19.2. Same prompt, different outcome in alternating runs.

2. **LP-32 de_minimis / A (Sonnet)**: A cites Section 12.1 in all 6 runs (found the clause) but returns `explicitly_present` 3 times and `missing` 3 times. The clause text is stable; A's judgment of whether it qualifies is not.

3. **LP-13 negligence_carveouts**: All three models find Section 11.2 in every run (presence verdict every time). The instability is in sub-class only (explicit vs implicit vs default_law), not in whether protection exists. This is the softest instability in the set.

4. **LP-29 emergency_entry / B (GPT)**: B returns `unclear` with Section 21.1 citation in all 6 runs — perfectly consistent, but disagrees with A (explicitly_present, also perfectly consistent). The merge produces `unclear` because of B's consistent mild-doubt verdict.

5. **LP-20**: Element verdicts for `competing_use_definition` are mostly stable. The bucket flip is driven by Stage 5e `use_impact.gap_impact` flipping `not_applicable` ↔ `low` — a separate non-determinism source not captured by this element-level probe. Noted as distinct.

---

## Commit

Status file only. No code. Analysis script is the data extraction above (no new API calls
needed — stored runs serve as N=6 independent resamples).
