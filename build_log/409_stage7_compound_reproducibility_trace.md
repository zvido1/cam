# 409 — Stage 7 Compound-Finding Reproducibility Trace

**Date:** 2026-07-08
**Type:** Read-only measurement. No code, prompt, model, pipeline, `cam/core/`, Stage 7, or compound-consequence change. No push.
**Purpose:** Before any Priority Exposure work, measure whether Stage 7 compound (CRX) findings are reproducible enough to rank. 408C proved compound consequence CAN be assessed and is not laundering Stage 7 framing (CRX returned `beneficial`). 408C also surfaced compound-consequence churn tied to Stage 7 instability. 409 measures that instability directly.

**Artifacts compared (both local, from 408C):**
- Run A: `05 Lease Analyzer/results/lease_408c_atreca_runA/pipeline_results.json` (1.35 MB)
- Run B: `05 Lease Analyzer/results/lease_408c_atreca_runB/pipeline_results.json` (1.35 MB)
- Same lease (Atreca EX-10.18), same pipeline, same code, back-to-back. Canonical `cross_provision_findings` where `finding_type == "compound_risk"` extracted from each (tail-slice + brace-match; files exceed the ~1MB MCP whole-read cap).

**Preflight note:** local-only state confirmed last session (`main...origin/main [ahead 21]`, 408C = `450f52d`, unpushed). The four dirty `_code_status.md` files and the two untracked `_389_results/`/`_391_results/` dirs were NOT touched by this trace; the `git diff` on those four files still awaits review but does not affect this read.

---

## 1. Executive summary

**Stage 7 compound findings are NOT reproducible enough to rank. `finding_id` is a per-run label, not a stable identity.** Both runs produced exactly 7 CRX findings, but **zero of the seven `finding_id`s point at the same finding across runs** — every CRX-01..07 has a different `implicated_lps` set in Run A vs Run B. Matching identity-agnostically (by LP set), **only ONE finding is reproducible**: the LP-22/LP-26 subordination trap (Run A CRX-06 = Run B CRX-01, exact LP-set match, same pattern, `beneficial` both runs). The other six findings do not have an exact cross-run twin; they shift implicated LPs, split, merge, or re-scope.

**Consequence of this for the churn debate (settles 408C's open question):** the 4/7-style compound-consequence "churn" observed in 408C is **upstream Stage 7 identity/input churn, NOT 408C consequence-layer instability.** When the CRX object's `implicated_lps` changes between runs, the consequence follows a genuinely different input — that is correct behavior, not a defect in the compound prompt/merge. On the one finding whose input WAS stable (LP-22/LP-26), the consequence was stable too (`beneficial` both runs). So 408C is exonerated; the blocker is one layer up.

**Verdict: Priority Exposure must wait for Stage 7 compound-identity reproducibility work.** You cannot rank "biggest traps first" when the traps themselves are re-drawn each run and the ids that would anchor a ranking are noise.

---

## 2. Inputs / artifacts compared

Both runs: 7 compound findings, ids CRX-01..CRX-07, all with `assessment_scope="finding_compound"` and `compound_consequence_source` populated (408C is live and assessing — confirmed). All 7/7 assessed both runs, 0 `not_assessed`. (Note: this "7 CRX both runs" differs from the older 407 run-A's 6 CRX read in 408A — Stage 7 count itself is not fixed run-to-run; here it happened to be 7 both times.)

---

## 3. Per-run CRX inventory

**Run A:**

| id | implicated_lps | pattern | sev | agr | compound_use_consequence | materiality |
|----|----------------|---------|-----|-----|--------------------------|-------------|
| CRX-01 | LP-01,11,17,27 | directional_asymmetry | HIGH | 3-0 | harmful | medium |
| CRX-02 | LP-11,27 | lever_elimination | MED | 3-0 | harmful | high |
| CRX-03 | LP-22,27 | subordination_trap | HIGH | 2-1 | harmful | medium |
| CRX-04 | LP-06,14,19,24,27 | cascading_no_remedy | HIGH | 3-0 | harmful | high |
| CRX-05 | LP-01,07,17,27 | lever_elimination | MED | 3-0 | harmful | medium |
| CRX-06 | LP-22,26 | subordination_trap | HIGH | 3-0 | **beneficial** | medium |
| CRX-07 | LP-06,14,19,24,27,29 | operational_dead_end | MED | 3-0 | harmful | high |

**Run B:**

| id | implicated_lps | pattern | sev | agr | compound_use_consequence | materiality |
|----|----------------|---------|-----|-----|--------------------------|-------------|
| CRX-01 | LP-22,26 | subordination_trap | HIGH | 3-0 | **beneficial** | high |
| CRX-02 | LP-01,11,27 | directional_asymmetry | HIGH | 3-0 | harmful | medium |
| CRX-03 | LP-01,17,26,27 | lever_elimination | MED | 3-0 | harmful | low |
| CRX-04 | LP-07,27 | lever_elimination | MED | 3-0 | harmful | high |
| CRX-05 | LP-22 | subordination_trap | HIGH | 3-0 | **context_dependent** | high |
| CRX-06 | LP-01,11,14,19,24,27,29 | cascading_no_remedy | HIGH | 3-0 | harmful | high |
| CRX-07 | LP-01,06,14,19,24,27,29 | operational_dead_end | MED | 3-0 | **context_dependent** | high |

Consequence distribution: Run A = 6 harmful / 1 beneficial. Run B = 4 harmful / 2 context_dependent / 1 beneficial.

---

## 4. Cross-run matching table (by LP-set Jaccard, identity-agnostic)

| Run A | LP set | best Run B match | LP set | LP-Jaccard | pattern match |
|-------|--------|------------------|--------|------------|---------------|
| CRX-01 | 01,11,17,27 | CRX-02 | 01,11,27 | 0.75 | ✓ |
| CRX-02 | 11,27 | CRX-02 | 01,11,27 | 0.67 | ✗ |
| CRX-03 | 22,27 | CRX-05 | 22 | 0.50 | ✓ |
| CRX-04 | 06,14,19,24,27 | CRX-07 | 01,06,14,19,24,27,29 | 0.71 | ✗ |
| CRX-05 | 01,07,17,27 | CRX-03 | 01,17,26,27 | 0.60 | ✓ |
| **CRX-06** | **22,26** | **CRX-01** | **22,26** | **1.00** | **✓** |
| CRX-07 | 06,14,19,24,27,29 | CRX-07 | 01,06,14,19,24,27,29 | 0.86 | ✓ |

**Exact LP-set match across runs: 1 of 7** (CRX-06↔CRX-01, LP-22/26). Every other finding's best match is a partial-overlap neighbor, not a twin — LP sets grow, shrink, or swap members.

---

## 5. Stable vs changed CRX identities

- **Stable identity (same finding_id → same LP set): 0 of 7.** `finding_id` fails as a cross-run key completely.
- **Semantically stable (same LP set + pattern, regardless of id): 1 of 7** — the LP-22/26 subordination trap (renumbered CRX-06→CRX-01).
- **Near-stable (Jaccard ≥ 0.85): 1 more** — the LP-06/14/19/24/27(/29) operational cluster (CRX-07→CRX-07), but Run B added LP-01, so not exact.
- **Merged/split/re-scoped: the remaining 5** — e.g. Run A's separate CRX-04 (cascading, 5 LPs) and CRX-07 (operational, 6 LPs) partly re-collect into Run B's CRX-06 (cascading, 7 LPs incl. LP-11) and CRX-07 (operational, 7 LPs incl. LP-01). LP membership migrates across findings between runs.

**LP-27 participation:** 6 CRX in Run A, 5 CRX in Run B — and not the same 5/6. The many-to-many exercised in 408A is real but its shape is itself run-dependent.

---

## 6. Consequence churn vs Stage 7 churn classification

**Classification: upstream Stage 7 churn, NOT consequence-layer churn.**

The one controlled comparison available — the finding whose input was identical across runs — shows the consequence layer is stable:
- LP-22/26 subordination trap: Run A CRX-06 = `beneficial`/medium/majority_assert/3-0; Run B CRX-01 = `beneficial`/high/majority_assert/3-0. **Same consequence direction, same support pattern.** Materiality nudged medium→high (a within-tolerance move on a genuinely borderline call), direction identical.

Every other apparent "flip" is attached to a CRX whose `implicated_lps` changed — i.e. the evaluator was asked about a different clause set, so a different answer is correct, not churn. Example: Run B's CRX-05 (`context_dependent`) is LP-22 ALONE; Run A had no LP-22-alone finding — it's a newly-scoped object, not a flip of an existing one.

**This directly settles 408C's open attribution.** The 408C report's 4/7 value churn was correctly diagnosed there as upstream: it is Stage 7 re-drawing the findings, and 408C's consequence layer faithfully following the changed input. 408C is not the instability source. On stable input, 408C is stable.

---

## 7. Is `finding_id` a stable cross-run key?

**No. Unambiguously no.** 0/7 findings keep the same LP set under the same id. `CRX-01` means "One-sided remedies framework (LP-01/11/17/27)" in Run A and "Subordination without non-disturbance (LP-22/26)" in Run B — different findings, opposite consequences (harmful vs beneficial). Any downstream system that joins, ranks, caches, or displays compound findings by `finding_id` across runs will mismatch. `finding_id` is a within-run ordinal only.

If a stable key is ever needed, the least-unstable candidate observed is the **(pattern_type, normalized LP-set)** tuple — but even that is fragile because LP sets themselves migrate. There is no reliable compound-finding identity today.

---

## 8. Are compound findings reproducible enough for Priority Exposure?

**No.** Priority Exposure ("biggest traps first") requires that "a trap" be a stable object with a stable severity/consequence so it can hold a rank across runs. On this evidence:
- The set of traps changes run-to-run (different LP groupings, merges/splits).
- The id that would anchor a rank is noise.
- Consequence direction is stable *only* where the underlying finding is stable, which is 1/7 here.

Ranking on this substrate would produce a "top traps" list that reshuffles every run — a ladder on wet tile. The consequence layer (408C) is ready; the thing being ranked is not.

**Nuance worth keeping:** the *aggregate signal* is more stable than the *per-finding identity*. Both runs agree there is a cluster of harmful enforcement/remedy-asymmetry traps around LP-01/11/27 and LP-06/14/19/24/27, and both independently flag the LP-22/26 subordination structure as NOT harmful (beneficial). So a coarse, cluster-level exposure summary might survive where a precise ranked list would not. That is a design option for later, not a green light now.

---

## 9. Recommendation

**Do not build Priority Exposure yet. The next blocker is Stage 7 compound-finding identity/reproducibility, upstream of 408C.** Concretely, the next measurement/design questions (for a future step, spec fresh):

1. **Why does Stage 7 re-draw compound findings run-to-run?** Pass-1 candidate generation is the likely source (the `stage7_pass1_parsed_candidates.json` sidecars differ between runs). Is it prompt nondeterminism, evaluator sampling, or a genuine ambiguity in which LPs "belong" to a compound pattern? Measure before fixing — same discipline as 404.
2. **Can Stage 7 emit a stable compound identity?** e.g. canonicalize a finding by its (pattern_type, sorted LP-set) and dedupe/merge within a run, then test whether that canonical key reproduces across runs.
3. **Is a cluster-level exposure summary reproducible even when per-finding identity is not?** The aggregate agreement in §8 suggests maybe. If so, the first lawyer-facing compound surface might be cluster-level ("this lease has a remedy-asymmetry cluster and a subordination structure"), not a ranked per-CRX list.

**408C itself needs no rework** — it correctly assesses whatever Stage 7 hands it, stays populate/record-only, and is stable on stable input. Leave it as-is. The widened-5e default stays off. No Priority Exposure. No push.

---

## Interpretation discipline

Two runs, one lease (Atreca), same code back-to-back — a reproducibility probe, N=2, DIRECTIONAL. Not a metric, not promoted, not patent record. The finding is about Stage 7 compound-finding *identity* stability, measured from existing 408C artifacts; no new runs were created. The single stable finding (LP-22/26) is one data point of within-run-to-run agreement, not proof of general stability. External-use pause on directional totals remains in force.

*Trace artifact: Step 409. Read-only.*
