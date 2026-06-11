# Step 384 — Material-Risk Cluster Check
**Date:** 2026-06-11  
**Inputs:** 10 `pipeline_results.json` files from Step 383 checkpoint  
**Scope:** Read-only. No new model calls. No code changes.

---

## Table 1 — Per-Run Summary

| Run | Job (6) | Risk | RN | Imp | Total Dir | LP-03 | LP-19 | LP-26 |
|-----|---------|------|----|-----|-----------|-------|-------|-------|
| 1  | 6a7716 | 14 | 2  | 11 | 27 | ✓ risk/harmful/high | ✓ improvement/neutral/N-A | ✓ risk/harmful/high |
| 2  | 0774c7 |  9 | 12 |  5 | 26 | ✓ risk/harmful/high | **ABSENT** | ✓ improvement/neutral/low |
| 3  | a845ff | 14 |  3 |  9 | 26 | ✓ risk/harmful/high | ✓ review_needed/context_dep/med | ✓ risk/harmful/high |
| 4  | 504920 | 15 |  4 |  8 | 27 | ✓ risk/harmful/high | ✓ improvement/beneficial/high | ✓ risk/harmful/high |
| 5  | 23cbb9 | 12 |  5 |  8 | 25 | ✓ risk/harmful/high | **ABSENT** | **ABSENT** |
| 6  | 109280 | 11 |  4 |  9 | 24 | **ABSENT** | ✓ risk/harmful/high | **ABSENT** |
| 7  | 96c08c | 13 |  1 | 10 | 24 | **ABSENT** | ✓ risk/harmful/med | ✓ improvement/neutral/low |
| 8  | f52761 | 14 |  2 | 11 | 27 | ✓ risk/harmful/med ⚠ | ✓ review_needed/context_dep/high | ✓ improvement/beneficial/high |
| 9  | 66a036 | 15 |  2 | 10 | 27 | ✓ risk/harmful/high | ✓ review_needed/context_dep/high | ✓ risk/harmful/high |
| 10 | 9026f5 |  6 | 16 |  5 | 27 | ✓ ↓review_needed/harmful/high | ✓ review_needed/context_dep/high | ✓ review_needed/context_dep/low |

⚠ = consequence_confidence degraded to `assert_weak`, evaluator agreement 2-1  
↓ = finding present but downgraded (routing_reason: `mismatch_support_insufficient`)

**Outlier runs by bucket tally:** Run 2 (Risk=9, RN=12) and Run 10 (Risk=6, RN=16).

---

## Table 2 — Disappearance Clustering

### Step 1: Disappearance runs per finding (determined independently)

| Finding | Absent in runs |
|---------|---------------|
| LP-03   | {6, 7}        |
| LP-19   | {2, 5}        |
| LP-26   | {5, 6}        |

### Step 2: Intersection analysis

| Pair | Shared absence runs | Interpretation |
|------|--------------------|-|
| LP-03 ∩ LP-19 | ∅ (none) | Disappearances do not coincide |
| LP-03 ∩ LP-26 | {6} | Both absent in Run 6 only |
| LP-19 ∩ LP-26 | {5} | Both absent in Run 5 only |
| LP-03 ∩ LP-19 ∩ LP-26 | ∅ | No run loses all three |

**Coincidence with outlier runs (2, 10):**

| Run | Outlier? | LP-03 | LP-19 | LP-26 |
|-----|----------|-------|-------|-------|
| 2   | YES (RN=12) | present/risk | **ABSENT** | present/improvement (neutral) |
| 5   | no (Risk=12) | present/risk | **ABSENT** | **ABSENT** |
| 6   | no (Risk=11) | **ABSENT** | present/risk | **ABSENT** |
| 7   | no (Risk=13) | **ABSENT** | present/risk | present/improvement (neutral) |
| 10  | YES (RN=16) | present/↓review_needed | present/review_needed | present/review_needed |

**Conclusion:** The disappearances do NOT cluster in the outlier runs. Run 10 (worst outlier) loses no findings outright — it degrades them from risk→review_needed via `mismatch_support_insufficient`. The true absences occur in near-median runs (5, 6, 7). Only LP-19 disappears once in an outlier run (Run 2); LP-03 and LP-26 vanish exclusively in normal-performance runs.

---

## Table 3 — Field-Level Cause Per Finding

### LP-03: Commencement date uncertainty (Dir-03 in most runs)

**When present:** consequence=`harmful`, consequence_confidence=`assert`, evaluator_agreement=`3-0` (7 of 8 present runs). Materiality=`high`. Finding ID=`Dir-03`. Routing: `assessed_harmful_material_consequence → risk`. Maximally stable when generated.

**When absent (runs 6, 7):** Dir-03 finding slot exists in both runs but contains a *different* finding (`LP-04 / context_dependent / review_needed` in both). LP-03's coverage_state falls to `partial, requires_attention=True`. LP-03 does not appear as any finding under any other ID in runs 6 or 7 — confirmed by scanning all 24 findings in each run for LP-03 in `implicated_lps`.

**First changed field:** Candidate not generated / not confirmed. The commencement-ambiguity claim was not extracted or not confirmed by Stage 4 evaluators in these two runs. The finding is not present anywhere in the run (not re-keyed, not mis-attributed to another LP). The sequential finding-ID `Dir-03` happening to belong to a different finding in runs 6–7 is coincidental (IDs are assigned in generation order).

Run 8 shows a partial-stability warning: `assert_weak` 2-1 materiality=`medium` instead of the usual 3-0 high. The finding is still generated and still routes to risk, but evaluator confidence is softer.

**Cause classification:** Candidate generation miss (Stage 3/4). The finding is absent entirely, not present under a different bucket or LP.

---

### LP-19: Service interruption relief / utility remedies (finding_id varies)

**When present:** Consequence, confidence, materiality, finding ID, and vote distribution all vary substantially run to run.

| Run | Finding ID | Consequence | Conf | Vote distribution | Bucket |
|-----|-----------|-------------|------|-------------------|--------|
| 1   | Dir-16 | neutral | assert_weak | {neutral:2, beneficial:1} | improvement |
| 3   | Dir-15 | context_dependent | context_dependent | {beneficial:1, harmful:1, cd:1} | review_needed |
| 4   | Dir-16 | beneficial | assert_weak | {beneficial:2, neutral:1} | improvement |
| 6   | Dir-14 | harmful | assert | {harmful:3} | risk |
| 7   | Dir-13 | harmful | assert_weak | {cd:1, harmful:2} | risk |
| 8   | Dir-16 | context_dependent | context_dependent | {beneficial:1, harmful:1, cd:1} | review_needed |
| 9   | Dir-16 | context_dependent | context_dependent | {beneficial:1, harmful:1, cd:1} | review_needed |
| 10  | Dir-16 | context_dependent | context_dependent | {beneficial:1, harmful:1} | review_needed |

**When absent (runs 2, 5):** No utility / service interruption finding appears anywhere in either run's directional list. Coverage_state=`partial/requires_attention=True`.

**First changed field:** Consequence and vote_distribution — the evaluators genuinely disagree about whether LP-19's service interruption gap is harmful (no broader utility remedies; tenant bears full risk) or beneficial/neutral (tenant separately metered, gap is irrelevant to their actual operations). Four distinct finding IDs (Dir-13 through Dir-16) across 8 present runs; same underlying clause area, different claim framing. The generation miss in runs 2 and 5 is layered on top of an already unstable finding.

**Cause classification:** Consequence nondeterminism — evaluator votes on `use_consequence` produce a three-way split (1:1:1 harmful/beneficial/context_dependent) in 5 of 8 present runs; the remaining 3 runs produce a majority (2:1 or 3:0) by chance. The absent-in-2-runs behavior is a secondary symptom; the primary instability is that the consequence assessment is genuinely unresolved. Cannot separate generation miss from consequence-gated upstream suppression without deeper stage-level instrumentation.

---

### LP-26: Quiet enjoyment — conditional / no full non-disturbance

**When present:** Consequence, materiality, and finding ID vary substantially.

| Run | Finding ID | Consequence | Conf | Vote distribution | Bucket |
|-----|-----------|-------------|------|-------------------|--------|
| 1   | Dir-22 | harmful | assert | {} (3-0) | risk |
| 2   | Dir-21 | neutral | assert_duo | {neutral:2} (2-0-1f) | improvement |
| 3   | Dir-21 | harmful | assert | {} (3-0) | risk |
| 4   | Dir-22 | harmful | assert | {} (3-0) | risk |
| 7   | Dir-19 | neutral | assert | {neutral:3} | improvement |
| 8   | Dir-22 | beneficial | assert_weak | {neutral:1, beneficial:2} | improvement |
| 9   | Dir-22 | harmful | assert | {} (3-0) | risk |
| 10  | Dir-22 | context_dependent | context_dependent | {neutral:1, beneficial:1} | review_needed |

**When absent (runs 5, 6):** No quiet enjoyment / non-disturbance / subordination-without-SNDA finding appears under LP-26 or otherwise in either run. Run 5 has `Dir-18: LP-22 / Subordination without protections / risk/harmful` (related but distinct LP), confirming the quiet-enjoyment-specific element was not generated. Coverage_state=`review_needed/partial` in both.

**First changed field:** Consequence and vote_distribution — evaluators split between "harmful" (tenant could be disturbed by lenders; no full non-disturbance) and "neutral/beneficial" (partial quiet enjoyment is market standard; tenant's operations not actually at risk). In 4 of 8 present runs, the 3-evaluator vote produces harmful (bucket=risk). In the other 4, it produces neutral, beneficial, or split (bucket=improvement/review_needed). Three different finding IDs appear (Dir-19, Dir-21, Dir-22), confirming different framings of the same clause area. The two true absences in runs 5–6 are likely the same instability (consequence-dependent upstream suppression) rather than an independent generation failure.

**Cause classification:** Consequence nondeterminism (same as LP-19). The underlying clause is genuinely ambiguous: partial quiet enjoyment protection is present, and whether that is harmful depends on the tenant's exposure profile. Evaluator polarity reverses across runs.

---

## Verdict: Case A/B MIXED

### Clustered component (partial)

Runs 5 and 6 are adjacent and each loses two of the three target findings (LP-19+LP-26 in Run 5; LP-03+LP-26 in Run 6). Run 6 is also the only run where both LP-03 and LP-26 are simultaneously absent. This partial co-absence in adjacent runs is notable but does not constitute a strong cluster: the three findings disappear via different mechanisms (see below) and the co-absence sets have empty three-way intersection.

The outlier runs (2 and 10) do NOT drive the disappearances. Run 10 degrades but does not lose the three findings. Run 2 loses only LP-19.

### Independent component (dominant)

| Finding | Disappears in | Mechanism | Correlation with outlier runs |
|---------|--------------|-----------|-------------------------------|
| LP-03 | {6, 7} | Candidate not generated (Stage 3/4 miss). Rock-stable when present (3-0 harmful/high). | None — runs 6, 7 are normal-performing |
| LP-19 | {2, 5} | Consequence nondeterminism — evaluators split 1:1:1 across polarity in most runs; generation miss in 2 runs is secondary symptom | Run 2 is an outlier; Run 5 is not |
| LP-26 | {5, 6} | Consequence nondeterminism — evaluators split harmful/neutral/beneficial; finding generation appears consequence-gated | Neither run 5 nor 6 is an outlier |

**LP-03 is an independent, mechanism-distinct disappearance.** When generated it is maximally confident; when not generated it is completely absent with no trace. This points to Stage 3/4 candidate extraction or confirmation failing silently for the commencement ambiguity claim in those two runs.

**LP-19 and LP-26 share the same root mechanism** (consequence nondeterminism) but disappear in different runs with no shared outlier cause. They form a "same-mechanism-but-independent-instance" pair rather than a true cluster.

---

## Output Recommendation

### DEF-002 status
**Remains blocked.** All three of LP-03, LP-19, LP-26 show instability that must be resolved before external validation is meaningful. A closed-lease test run would show the same disappearance pattern.

### Next workstreams

**Workstream 1 — LP-03 generation trace (highest priority for code diagnostic)**  
LP-03 (commencement date uncertainty) is rock-stable when generated but simply absent in 2 runs. No consequence instability, no polarity reversal. Pure Stage 3/4 candidate extraction or Stage 4 confirmation miss. Next step: instrument Stage 3 candidate list and Stage 4 per-evaluator decisions for the commencement clause in runs 6 and 7 to identify where the finding drops. This is the most tractable code bug of the three.

**Workstream 2 — LP-19 and LP-26 legal-substance calibration (Joshua question before code fix)**  
Both LP-19 and LP-26 show genuine evaluator polarity reversal (harmful ↔ beneficial/neutral). Before treating this as a code bug, the underlying legal question must be settled:

- **LP-19 (service interruption relief):** Is the absence of broader utility remedies harmful to *this tenant* (24/7 warehouse + light assembly, separately metered power), or is the tenant's separate metering arrangement sufficient such that the gap is neutral or even beneficial? The evaluator split reflects a genuine legal ambiguity about whether the clause gap has real-world bite. → **Joshua question.**

- **LP-26 (quiet enjoyment):** Is the absence of a full non-disturbance / SNDA provision harmful (tenant could be disturbed by lenders), or is partial quiet enjoyment (conditioned on not being in default) market-standard and sufficient? Evaluator polarity fully reverses across runs. → **Joshua question.**

If Joshua confirms LP-19 should be harmful for this tenant profile, then consequence-assessment stability for that finding becomes a code target (e.g. stronger consequence-prompt anchoring or consequence-override logic). If he confirms ambiguity is appropriate, the system is not broken — it is correctly waffling on a genuinely ambiguous clause, and the display logic (not the assessment) may need adjustment.

**Workstream 3 — Whole-run softness trace (separate, lower priority)**  
Runs 2 and 10 show broad Risk→Review Needed movement (mismatch_support_insufficient routing for many findings). This is independent of the three disappearances above. The root cause is likely Stage 7 evaluator support being weaker in those runs (1/3 evaluator mismatch confirmation rather than 2/3 or 3/3). A separate diagnostic for Stage 7 support stability is warranted but is not blocking relative to workstreams 1 and 2.

### Priority order
1. LP-03 generation trace (Stage 3/4, pure code)
2. Joshua calibration for LP-19 and LP-26 (legal substance first, then code)
3. Whole-run softness trace (Stage 7 mismatch support, lowest urgency)
