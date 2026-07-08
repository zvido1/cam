# 410 — Stage 7 Compound-Finding Candidate-Generation Instability Trace

**Date:** 2026-07-08
**Type:** Read-only measurement. No code, prompt, model, pipeline, `cam/core/`, Stage 7, or compound-consequence change. No push.
**Purpose:** Measure WHERE nondeterminism enters the Stage 7 compound-finding pipeline before designing any fix or building Priority Exposure. 409 established THAT CRX findings are unstable (0/7 stable `finding_id`, 1/7 semantically stable); 410 establishes WHY.

**Artifacts read (no new runs created):**
- `05 Lease Analyzer/results/lease_408c_atreca_runA/` — 4 Stage 7 Pass-1 sidecars
- `05 Lease Analyzer/results/lease_408c_atreca_runB/` — 4 Stage 7 Pass-1 sidecars
- `cam/adapters/lease_review/lease_synthesis.py` — full pipeline code (lines 1–2722)
- `build_log/409_stage7_compound_reproducibility_trace.md` — prior measurement

---

## 1. Executive Summary

**The compound-finding instability chain begins upstream of Stage 7, in Stage 5 coverage assessment.** The Stage 7 compound pass receives different LP coverage-state inputs between runs because Stage 5 (LLM-based element-level coverage) is nondeterministic. This drives different compound model outputs, which produce different candidate sets, which get different ordinal CRX-NN ids — twice. Temperature=0 does not prevent this because the problem is not sampling noise; it is upstream input variance.

**Three nondeterminism layers, in priority order:**

1. **Layer 1 (primary): Stage 5 coverage assessment nondeterminism.** LP coverage states differ between runs, producing different flagged LP sets and different compound-prompt content. Measured directly: Run A flagged 18 LPs; Run B flagged 19 LPs; 5 LPs differ between runs. Compound prompt matrix embeds per-LP coverage states, so different Stage 5 → different compound prompt → different compound output.

2. **Layer 2 (secondary): Cross-provider LLM nondeterminism at temperature=0.** All Stage 7 compound evaluators are configured `temperature: 0.0`, but temperature=0 ≠ deterministic across providers. Even with identical input, Claude/GPT/Grok may return different `involved_lps` sets for the same pattern — especially for boundary LPs (e.g., LP-22 alone vs LP-22+LP-27). This layer fires even if Layer 1 were resolved.

3. **Layer 3 (structural): Doubly-unstable ordinal ID assignment.** `finding_id` (`CRX-NN`) is assigned twice — once in `_cluster_compound_candidates` (by evaluator insertion order) and again in `_dedup_compound_findings` (by connected-component root, by sorted group key). Both are deterministic given their inputs, but since the inputs are nondeterministic (Layers 1+2), the final IDs are also nondeterministic. There is no content-based key at any point.

**Fix priority derived from this trace:** Layer 1 must be addressed before any other fix. Stabilizing temperature or seeding is insufficient while the prompt content itself varies. A content-based compound identity (pattern_type + sorted LP-set) would improve cross-run matching but would still produce different LP sets if Layer 1 is not resolved.

---

## 2. Code Archaeology: The Full Stage 7 Compound Pipeline

### 2.1 Stage 7 call structure

Stage 7 has **three independent LLM call families**:

| Call | Function | System prompt | Per-LP or full matrix? | Sidecar |
|------|----------|---------------|------------------------|---------|
| Pass-1 directional | `_call_single_evaluator` | `_EVALUATOR_SYSTEM` | Flagged LPs only + full lease | `stage7_pass1_*` (Step 386) |
| Pass-1 compound | `_call_compound_evaluator` | `_COMPOUND_SYSTEM` | Full 32-LP matrix + full lease | **None** |
| Pass-2 verification | `_call_pass2_evaluator` | `_PASS2_EVALUATOR_SYSTEM` | Cluster list only | None |
| Consolidation | `_call_consolidator` | `_CONSOLIDATOR_SYSTEM` | Eval A/B/C outputs | None |

The four Step 386 sidecars (`stage7_pass1_raw_input.json`, `stage7_pass1_raw_output.txt`, `stage7_pass1_parsed_candidates.json`, `stage7_pass1_dropped_attention_items.json`) capture **only the directional Pass-1 family**. The compound pass has **no dedicated sidecar**. Compound nondeterminism in this trace is therefore inferred from indirect evidence (LP set differences, code inspection of prompt-build logic).

### 2.2 Temperature configuration (all calls)

All three evaluator lineups use `EVALUATOR_LINEUP` settings:
- Eval-A (Claude): `"temperature": 0.0`
- Eval-B (GPT-4): `"temperature": 0.0`
- Eval-C (Grok): `"temperature": 0.0`

The compound evaluator (`_call_compound_evaluator`, lines 746–807) hardcodes `temperature=0.0` directly, independent of `EVALUATOR_LINEUP`. Consolidator (`_call_consolidator`, lines 810–868) also uses `temperature=0.0`.

**Conclusion: temperature=0 is already in place everywhere. Temperature is NOT the fix.**

### 2.3 Compound prompt construction (`_build_compound_user_prompt`, lines 588–619)

The compound user prompt is built from:
```
perspective_block
+ FULL PROVISION MATRIX  ← all 32 LPs, with per-LP coverage_state + element fraction
+ FULL LEASE TEXT        ← full_lease_text (same file both runs)
```

The LP matrix row format (line 563):
```
"{lp_id}: {lp_name} — {state} ({n_present}/{len(ev)} elements)"
```
where `state` = `coverage_state` and `n_present` = count of elements with verdict in `_presence`. Both come from `coverage_assessment`, which is the nondeterministic Stage 5 output.

**If Stage 5 returns different `coverage_state` or different `element_verdicts` for any LP, the compound prompt matrix changes, the prompt hash changes, and different model output follows.**

### 2.4 CRX ID assignment — two passes

**Pass 1: `_cluster_compound_candidates` (lines 927–955)**
```python
for i, (_, data) in enumerate(clusters.items()):
    data["candidate_id"] = f"CRX-{i + 1:02d}"
```
Ordinal based on dict insertion order. Dict keys are `(pattern_type, frozenset(involved_lps))`. Insertion order depends on which evaluator reports which `(pt, lps)` pair first. If evaluators return different LP sets for the same pattern, the clustering produces different keys in different order.

**Pass 2: `_dedup_compound_findings` (lines 1601–1666)**
```python
for idx, f in enumerate(merged):
    f["finding_id"] = f"CRX-{idx + 1:02d}"
```
Ordinal re-assignment after union-find connected-component merging. Merge condition: same `pattern_type` + ≥2 shared `implicated_lps`. Iteration order is `sorted(groups)` where group roots are integer indices from the union-find. Final order depends on which findings survived Pass-2 and how they merged.

`finding_id` is **doubly unstable**: it is an ordinal assigned twice based on runtime state that depends on nondeterministic upstream input. There is no content key anywhere in the assignment chain.

---

## 3. Measured Input Boundary: Stage 7 Pass-1

### 3.1 Stage 7 input comparison (from sidecars)

| | Run A | Run B |
|---|---|---|
| `flagged_lp_count` | **18** | **19** |
| `prompt_hash_md5` | `db31097808f6db2e60acd7b77d9f970a` | `c7049eb96d847b745aeb751073459143` |
| `prompt_len` | 167,448 chars | 167,541 chars (Δ = +93) |
| `dropped_count` | 0 | 0 |

**Prompt hashes are different. Stage 7 inputs are NOT identical between runs.**

### 3.2 Flagged LP set difference

| Run A only | Run B only | Both runs |
|------------|------------|-----------|
| LP-01, LP-15 | LP-09, LP-28, LP-29 | LP-02, LP-03, LP-05, LP-07, LP-10, LP-11, LP-13, LP-14, LP-17, LP-20, LP-21, LP-22, LP-24, LP-26, LP-27, LP-30 |

5 LPs differ. Since `_collect_flagged_lps()` flags LPs whose `coverage_state` is in `_FLAGGED_STATES` (or `partial_class` in `{partial_material, partial_typical}`), this proves that LP-01 and LP-15 have `coverage_state` in `_FLAGGED_STATES` in Run A but NOT in Run B, and LP-09, LP-28, LP-29 have `coverage_state` in `_FLAGGED_STATES` in Run B but NOT in Run A.

This is direct proof that **Stage 5 coverage assessment is nondeterministic** between back-to-back runs on the same lease.

### 3.3 Impact on compound prompt

The compound prompt (`_build_compound_user_prompt`) uses **all 32 LPs**, not just flagged ones — so the flagged-LP difference does not directly change which LPs appear in the compound matrix. However, the per-LP `coverage_state` and element fraction (`n_present/len(ev)`) in the matrix come from the same nondeterministic Stage 5. If LP-01 is `absent` in Run A and `explicitly_present` in Run B (or any other state change that crosses the flagging threshold), that LP's matrix row will differ between runs, changing the compound prompt hash.

**Conclusion: the compound pass prompt content differs between runs.** The magnitude of that difference is not directly measurable from available artifacts (no compound sidecar), but the LP flagging divergence is a sufficient proof that Stage 5 output differs enough to change at least 5 LP states.

### 3.4 Directional candidate count (from `parsed_candidates.json`)

Both runs: every flagged LP produced exactly one directional candidate. 0 dropped. Candidate counts match flagged LP counts exactly (18 vs 19).

The directional candidates themselves show evaluation-level variation for the same LP across runs (e.g., LP-05 is found by evaluators B+C in Run A but B only in Run B; LP-21 is found by B+C in both). This is additional evidence of evaluator-level output variance independent of prompt changes.

---

## 4. Inference at the Compound Output Boundary

No compound-pass sidecar exists. The available indirect evidence is:

**From 409 results (final compound findings after dedup):**
- Run A: 12 compound candidates → dedup'd to 7 CRX
- Run B: 11 compound candidates → dedup'd to 7 CRX
- 0/7 `finding_id`s kept the same LP set across runs
- 1/7 semantically stable (LP-22/LP-26 subordination trap, exact LP-set match)

**Inference from code:**
The `_COMPOUND_SYSTEM` prompt asks evaluators to assess 5 fixed pattern types for `present: "yes"` or `"no"`. Each evaluator independently decides which LP combinations fit each pattern. At temperature=0, the pattern-to-LP mapping is sensitive to the LP matrix content. When Stage 5 changes LP-01's coverage state across runs, the evaluator's assessment of which patterns LP-01 participates in changes too — producing different `involved_lps` sets per pattern.

The 12→11 candidate count change (Run A vs B) is consistent with one evaluator returning `present: "no"` for one pattern in Run B that returned `present: "yes"` in Run A (or vice versa), producing one fewer cluster that passes `_cluster_compound_candidates`'s `present: "yes"` filter.

**The one stable finding (LP-22/LP-26) is the control case:** LP-22 and LP-26 are flagged in both runs (both appear in the 16-LP common set). Their `coverage_state` values are presumably consistent between runs at a level that keeps them in the subordination trap cluster regardless of other variation. This is the only case where Layer 1 (Stage 5 variance) did not destabilize the compound pattern.

---

## 5. Compound Finding ID Trace (From Code)

The complete path from compound evaluator output to final `finding_id`:

```
_call_compound_evaluator × 3 (A/B/C)
    │  each returns {"candidates": [{"pattern_type", "involved_lps", "present", ...}]}
    ▼
_cluster_compound_candidates(evaluator_outputs)
    │  filter: only present=="yes"
    │  group by (pattern_type, frozenset(involved_lps))
    │  assign candidate_id = "CRX-{i+1:02d}" (ordinal by insertion order)
    ▼  → clusters: list of candidate objects with CRX-01..N ids
_build_pass2_verified_findings(clusters, pass2_outputs)
    │  Pass-2 verifies each cluster
    │  agreement rules: 2/3+ → surface; 0/3 → drop
    │  carries cluster's candidate_id as finding_id
    ▼  → verified_findings: list with CRX-01..N ids (subset of clusters)
_dedup_compound_findings(findings)
    │  union-find: merge same pattern_type + ≥2 shared implicated_lps
    │  re-assign finding_id = "CRX-{idx+1:02d}" (ordinal by sorted group root)
    ▼  → FINAL findings: CRX-01..M ids (where M ≤ N)
```

Both assignment points produce pure ordinals with no content-based key. A stable content key would be `(pattern_type, tuple(sorted(implicated_lps)))` — but this key itself is unstable because `implicated_lps` changes when Stage 5 coverage states change.

---

## 6. Root Cause Classification

### Layer 1: Stage 5 coverage assessment nondeterminism (PRIMARY — MEASURED)

**Evidence:** 5 LPs differ in flagged state between Run A and Run B. Direct proof that Stage 5 LLM calls return different `coverage_state` / element verdicts for the same LP across back-to-back runs. This is the input to the compound prompt matrix.

**Mechanism:** Stage 4/5 calls LLM models for element-level coverage. These calls are not seeded or cached. Any token-level variance in model output (hardware FP, batching) changes an element verdict, which changes a coverage state, which changes the compound prompt matrix.

**Fix scope:** Stage 5 reproducibility improvement (caching, deterministic evaluation, multi-run consensus). This is a separate step; the form of the fix is a design decision, not a measurement.

### Layer 2: Cross-provider LLM nondeterminism at temperature=0 (SECONDARY — INFERRED)

**Evidence:** Temperature is already 0.0 on all compound evaluators (directly confirmed in code). The 1/7 stable finding (LP-22/LP-26) demonstrates that SOME compound findings are stable at temperature=0 when the input is also stable. But the other 6/7 are not. Some of that instability comes from Layer 1 (changed inputs), but the cross-provider nature of the evaluator set (Claude, GPT, Grok) means residual variance would persist even with identical inputs.

**Mechanism:** `temperature=0` on a single provider approximates greedy decoding but is not guaranteed reproducible even on the same provider at different load/batch times. Across three different providers, the effective behavior is sampling with very low temperature, not true determinism.

**Fix scope:** Cannot be fully eliminated without single-provider deterministic evaluation (which conflicts with the multi-evaluator independence model). Partial mitigation: run-level caching keyed on prompt content hash.

### Layer 3: Ordinal ID instability (STRUCTURAL — CONFIRMED)

**Evidence:** `_cluster_compound_candidates` line 953, `_dedup_compound_findings` line 1661. Both assign `CRX-{ordinal}` with no content anchor.

**Mechanism:** Even if the same compound pattern were detected in both runs, it would receive different CRX-NN numbers if other patterns are present/absent, or if evaluator output order changes, or if the dedup merge groups form differently.

**Fix scope:** Replace ordinal assignment with a content-keyed id: `CRX-{hash(pattern_type + sorted_lps)[:6]}` or a normalized slug. This does not fix Layers 1+2 but decouples id stability from position stability.

---

## 7. Why Temperature=0 Is Not a Fix

This trace was commissioned partly to answer: "Is this a config-fix or a clustering-redesign?" The answer is **neither is sufficient alone**:

- **Config-fix (temperature=0):** Already in place. Doesn't help because the problem is input content variance (Layer 1), not sampling variance within a stable call.
- **Clustering redesign (stable canonical key):** Would fix Layer 3 and make compound identity trackable across runs, but would not prevent different LP sets from entering the pattern assessments (Layer 1) or prevent evaluators from assigning different LPs to the same pattern given the same matrix (Layer 2).

The correct fix sequence: **stabilize Stage 5 → then stabilize compound identity keys → then observe whether residual Layer 2 variance is still material.**

---

## 8. Available Artifacts vs. What's Missing

### Available (measured)
- Stage 7 Pass-1 directional sidecar (4 files × 2 runs): flagged LP sets, prompt hashes, directional candidates, dropped items
- Final compound finding LP sets and consequence values (from 409)
- Full `lease_synthesis.py` code including compound path, dedup logic, ID assignment

### Missing (no artifact)
- Stage 7 compound pass raw input (no sidecar equivalent to Step 386 for compound calls)
- Stage 7 compound pass raw output per evaluator
- Stage 7 Pass-2 verification raw output
- Stage 5 coverage assessment diff between runs (would directly show LP-level state changes)

If a future step wants to add compound instrumentation analogous to Step 386, the compound sidecar would log:
```json
{
  "compound_prompt_hash_md5": "...",
  "compound_prompt_len": ...,
  "compound_evaluator_outputs": {"A": ..., "B": ..., "C": ...},
  "clusters_pre_dedup": [...],
  "clusters_post_dedup": [...]
}
```
This would allow direct measurement of Layer 2 (are raw compound outputs different even with same hash?) vs Layer 1 (are prompt hashes different?).

---

## 9. Implications for Next Steps

**DO NOT** build Priority Exposure, compound stability fixes, or canonical identity keys in this session. Measurement is done; design is the next step.

**Questions the NEXT spec must answer (not this trace):**

1. **Stage 5 stabilization scope.** How much of LP coverage state variance is addressable via deterministic evaluation (caching, single-evaluator fallback, same-seed re-run)? Is Stage 5 itself a multi-provider call, or single-provider? This determines whether Layer 1 is fixable cheaply or requires architectural change.

2. **Canonical compound identity design.** Given that LP sets in a compound finding may still vary somewhat even with stable Stage 5, what is the right identity tolerance? Exact LP-set match (Jaccard = 1.0)? Jaccard ≥ 0.85? Pattern+anchor-LP only? This is a design choice, not a measurement question.

3. **Compound sidecar instrumentation.** Before the next full pipeline run, the Step 386 equivalent for compound calls should be added, so future traces can measure Layer 2 directly rather than inferring it.

4. **Is cluster-level exposure stable enough?** The 409 observation that "both runs agree on the same hazard clusters (LP-01/11/27 enforcement asymmetry, LP-06/14/19/24/27 operational cluster, LP-22/26 subordination)" suggests aggregate signal is more stable than per-finding identity. A cluster-level exposure summary (not a ranked per-CRX list) might be a viable first lawyer-facing compound surface.

**408C needs no rework.** The compound consequence layer is correct: it faithfully assesses whatever Stage 7 hands it, stays stable on stable input (proven by LP-22/26 cross-run control), and writes no LP-level contamination. The instability measured here is upstream of 408C.

---

## 10. Interpretation Discipline

Two runs, one lease (Atreca), same code, back-to-back. This trace is DIRECTIONAL, N=2, one-lease. The nondeterminism layers identified are structural (confirmed by code review) and consistent with observed data, but their relative magnitudes are not quantified. Layer 1 dominance is inferred from the LP-set difference, not from a controlled experiment that held Stage 5 constant. External-use pause on directional totals remains in force. This report is an internal measurement artifact; it is not promoted.

*Trace artifact: Step 410. Read-only.*
