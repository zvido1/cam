# Step 421C — Evidence-Assignment Architecture Incident Report

**Date:** 2026-07-13
**Status:** COMPLETE — read-only, no code changes, no baseline run
**Related steps:** 417, 419, 420, 421B, 422

---

## 1. Executive Summary

Steps 417, 419, and 420 were designated as Stage 5 baseline measurements for the CAM pipeline. This report documents why those baselines are **diagnostically useful but not valid coverage-assessment baselines**. The root cause is not evaluator nondeterminism, not temperature instability, and not a scoring bug. It is a fundamental property of the extraction architecture: **Gemini's evidence-assignment is destructive and exclusive**.

The ceiling fix in 421B (token limit 32k → 65k) was necessary and correct — it stopped Gemini from silently truncating. But the ceiling fix revealed a deeper problem it cannot solve. Post-ceiling extractions show that Gemini partitions the Atreca lease into disjoint LP buckets and material content — tenant protections, quantitative parameters, conditional clauses — either lands in one bucket or is dropped. Evaluators never see what wasn't assigned to their LP.

The consequence is not "some evaluations have lower confidence." The consequence is **evidence incompleteness**: an evaluator working from the extracted context is asked to assess whether a protection is present or absent, but may be missing the very clause that defines or bounds that protection. The baseline runs measured evaluator behavior on incomplete and nondeterministically varying evidence contexts. They cannot be valid coverage baselines for those provisions.

**What survives:** the evaluator panel identity and behavior (414), config integrity (416), fallback integrity (421B guard), and the extraction ceiling fix are all valid and durable. The problem is upstream of the evaluators — in how evidence reaches them.

---

## 2. The New Finding (Evidence-Assignment Failures, Confirmed)

### 2a. LP-07 — Operating Expenses: Exclusions and Cap Absent 80% of the Time

The Atreca lease contains an Operating Expense Exclusions list (what is NOT charged to tenant) and a Controllable Expenses Cap (typically 5% annual cap on controllable items). These are the provisions that determine whether the tenant's operating expense exposure is bounded or unbounded — directly relevant to any LP-07 coverage assessment.

In N=10 Gemini extractions post-ceiling fix:
- **Modal hash `f7f64b5c` (8/10 runs, 11,492 LP-07 chars):** Includes the full Operating Expenses definition, the Exclusions list, the Controllable Expenses Cap, and the Annual Reconciliation mechanism.
- **Minor hash `d3e62ead` (2/10 runs, 7,115 LP-07 chars):** Both hashes share the same 573-char opening. Minor ends at `"...referred to herein as 'Rent.'"` — a grammatical sentence boundary, not a truncation artifact. The Exclusions, Cap, and Reconciliation are absent.

An evaluator working from the minor hash's LP-07 context sees what Operating Expenses include but not what they exclude. The Controllable Expenses Cap — the primary tenant protection against runaway CAM charges — is invisible. This is not a scoring issue; it is a missing evidence issue.

### 2b. LP-12 — Delivery / Acceptance: Different Clauses Assigned Across Runs

Both hashes share 1,561 chars of LP-12 (the Delivery obligations and 120-day termination right). Then they diverge on *which clause comes next*:

- **Modal `f7f64b5c`:** "Tenant acknowledges and agrees that following the Commencement Date, Landlord may require access to portions of the Premises in order to complete Landlord's Work..." — Landlord's Work access rights and tenant obligations during construction.
- **Minor `d3e62ead`:** "Notwithstanding anything to the contrary contained in this Lease, Tenant and Landlord acknowledge and agree that the effectiveness of this Lease shall be subject to the following condition precedent ('Condition Precedent'): Landlord shall have entered into a lease termination agreement..." — a condition precedent tying lease effectiveness to the prior tenant vacating.

These are structurally different clauses with different legal consequences. The Condition Precedent (minor hash) is a significant tenant protection: if the prior tenant does not vacate, the lease does not become effective. The Landlord's Work access rights (modal hash) impose obligations on the tenant during construction. An evaluator assessing LP-12 coverage from one hash would not see the material from the other. The two hashes are not "the same content, more or less" — they are different sections of the lease assigned to LP-12 by different Gemini runs.

### 2c. The Key-Terms Table: Quantitative Parameters Missing from Evaluators in All Known Runs

The Atreca lease contains a one-page key-terms table at character 1,994 in the source document. This table specifies:
- **Tenant's Share of Operating Expenses of Building: 100%**
- **Building's Share of Project Operating Expenses: 45.79%**
- **Rent Adjustment Percentage: 3%**

These numbers determine the tenant's actual exposure under the Operating Expense and Rent escalation provisions — the quantitative spine of the financial terms.

Confirmed search results:
- **101 Gemini-primary pipeline result files searched:** 0 hits for "45.79" or "Tenant's Share" in any LP's `tenant_text` across any run.
- **3 Atlas pipeline result files searched (lease_20260419_201646, lease_20260419_202420, lease_20260420_001026):** 0 hits for "45.79" or "100%" or "Tenant's Share" in any LP.
- **N=10 Atreca post-ceiling probe:** Table present in LP-00 of the minor hash `d3e62ead` only (2/10 runs). Absent from LP-00 in modal `f7f64b5c` (8/10 runs). Absent from LP-07 in both hashes in all runs.

The only confirmed case where the table appeared in LP-07 was the `418c` run — and that run used gpt-5.5 as the fallback extractor, not Gemini. Under Gemini-primary extraction across all known runs, the key-terms table has never appeared in LP-07. When it appears at all, it lands in LP-00 — the Parties & Premises provision, which has `identity_check: true` in the taxonomy and is not evaluated for coverage.

**The table reaching LP-00 is not a partial win.** LP-00 is the identity confirmation step, not a coverage-assessed provision. Content assigned to LP-00 is read by no evaluator for coverage purposes. The table's quantitative parameters — the 100% tenant share and 45.79% building share that determine the financial exposure under LP-07's Operating Expense clause — have not reached the evaluators in any Gemini-primary pipeline run, including all Atlas runs.

### 2d. Grok Exonerated

Steps 417 through 420 identified Grok (Role C) as a high-variance evaluator on LP-07, flagging "missing" verdicts inconsistently and diverging from Roles A and B. This finding appeared anomalous given that grok-4.3 is capable of nuanced assessments on other provisions.

The source of Grok's LP-07 "missing" verdicts is now clear: **Grok was correct.** The Operating Expense quantitative parameters — the 100% tenant share, 45.79% building share — were never in Grok's evidence context for LP-07 under Gemini extraction. An evaluator asked to assess whether the tenant's operating expense share and exposure are adequately protected cannot give a confident "present" verdict if the share percentage itself is absent from the evidence. Grok's "missing" verdicts on LP-07 reflect evidence incompleteness, not evaluator instability. The earlier attribution of LP-07 variance to Grok evaluator behavior was based on an incorrect model of what evidence Grok was working from.

---

## 3. Why Prior Baselines Are Void

### 3a. What 417/419/420 Measured

Steps 417, 419, and 420 measured evaluator panel behavior — how A, B, and C respond to the evidence they receive. The measurements were conducted carefully, with proper identity freezing (414) and, for 419/420, post-ceiling extractions. The per-LP frequency distributions, per-role flip counts, and variance source classifications in those runs are accurate descriptions of what happened.

**The problem is not measurement error. The problem is that the object being measured was not what the measurements were intended to characterize.**

A "Stage 5 coverage baseline" should measure whether the evaluator panel correctly assesses coverage for the provisions in a real lease. For that measurement to be valid, the evaluators must have access to the material provisions for each LP. If the evidence assignment leaves out the Controllable Expenses Cap from LP-07 in 2 out of 10 runs, and leaves out the quantitative parameters defining tenant exposure in all runs, then the evaluator panel's LP-07 verdicts cannot constitute a coverage baseline for the Operating Expenses provision. They are instead a baseline for evaluator behavior under the specific (and incomplete) evidence that Gemini happened to assign to LP-07.

### 3b. Atlas Lease Check

The attorney validation runs used Atlas lease results. The Atlas check above (3 pipeline result files) confirms that the key-terms table was not present in any LP's extracted content in those runs. The financial parameters that define Operating Expense exposure — Tenant's Share 100%, Building's Share 45.79% — were absent from the evaluators' evidence context in the Atlas validation runs as well.

This means the attorney validation was conducted using CAM output produced from evaluations in which the quantitative parameters governing operating expense exposure were not in scope. The validation findings remain the lawyers' genuine assessments of the CAM output they were given. But the output they assessed was produced from incomplete evidence. Any coverage verdict on LP-07 from those runs reflects evaluator assessment of the Operating Expenses mechanism without the share percentages that quantify the mechanism's effect on this tenant.

**This does not invalidate the attorneys' assessments as such.** Their reactions to what they saw were genuine. It does mean that the attorney validation cannot be cited as validation of CAM's Operating Expense coverage analysis, because CAM was not assessing Operating Expense coverage with the operative parameters in scope.

### 3c. Scope of the Void

The voidness is specific, not total. Steps 417/419/420 remain valid as:
- Measurements of evaluator panel variance on the Atreca fixture (diagnostically useful for characterizing the noise floor)
- Confirmation that the 421B ceiling fix eliminated the repair-fired truncation artifact
- Confirmation that identity freezing (414) and config integrity (416) are functioning

They are not valid as:
- Coverage baselines for any of the 6 materially varying LPs (LP-00, LP-03, LP-05, LP-07, LP-12, LP-28)
- Reproducibility claims for LP-07 Operating Expenses or LP-12 Delivery specifically
- The foundation for Step 423 policy resimulation

---

## 4. Architectural Root Cause: Destructive Exclusive Assignment

The extraction step assigns each section of the lease to exactly one LP bucket. The assignment is exclusive: once a clause is routed to LP-00, it does not appear in LP-07; once a clause is routed to LP-12's run-2 bucket, it does not appear in LP-12's run-1 bucket. The assignment is also destructive: material not assigned to any LP bucket, or assigned to an unscored LP (like LP-00), is permanently outside the scope of all downstream evaluations.

This "one bucket per clause" design is a natural first-pass extraction architecture. It becomes an evidence-integrity problem when:

1. **A single clause is material to multiple provisions.** The key-terms table defines Tenant's Share (LP-07 relevance), the Rent Adjustment Percentage (LP-02 relevance), and the Base Term (LP-03 relevance) in one place. Assigning it to one bucket means the other buckets don't see it.

2. **Clause boundaries are ambiguous or lease-section-crossing.** Gemini must decide where the LP-12 content ends. In different runs it draws the boundary after different clauses — one run captures the Condition Precedent, another captures the Landlord's Work access rights. Neither run captures both.

3. **LP-00 is a sink for identity-check content.** When Gemini assigns the key-terms table to LP-00 (Parties & Premises), it goes into a provision that is not evaluated for coverage. The content is not malformed or missing from the extraction — it is routed to a bucket that the pipeline does not score.

The root cause is the many-to-one assignment doctrine implicit in the current extraction design: many lease clauses can be relevant to a given LP, but the extraction assigns each clause to at most one LP. In a well-drafted lease with clear section headers that map cleanly to the taxonomy, this works acceptably. In a lease with cross-cutting key-terms tables and ambiguous section boundaries, it systematically misroutes material content.

---

## 5. Immediate Architecture Implications

### 5a. Non-Exclusive Assignment

The fix is not "better prompting of the current extraction." Asking Gemini more carefully to assign the Operating Expense share percentages to LP-07 would produce a different one-time routing, but the same nondeterminism and the same many-to-one assignment problem will recur on the next run and the next lease.

The durable fix is **non-exclusive assignment**: a clause can be assigned to multiple LP buckets when it is material to more than one. This is architecturally more expensive (larger total evidence per LP, more tokens, more evaluator calls per LP) but it is the only way to guarantee that a clause relevant to multiple provisions reaches all of them.

Non-exclusive assignment does not require the evaluators to see the full lease. It requires the extraction to route cross-cutting content to all LPs where it is material — the key-terms table should appear in LP-00, LP-02, LP-07 (and any other LP for which the quantitative parameters define the scope of obligation). This is a fundamentally different extraction doctrine from the current "one bucket per clause" design.

### 5b. Global Key-Terms Context

An alternative or complement to full non-exclusive assignment is a **global key-terms context**: a structured representation of the document's quantitative spine (parties, shares, percentages, dates) that is provided as a prefix to every LP's evidence context. This would not replace LP-level extraction but would ensure that the parameters defining "100% tenant share" or "3% annual escalation" are in scope for every evaluator on every LP without requiring the full clause text to be re-routed.

This is a less expensive option than full non-exclusive assignment but covers a narrower class of evidence-incompleteness failures. Cross-cutting key-terms tables would be handled; ambiguous clause-boundary routing (the LP-12 finding) would not.

### 5c. What Cannot Be Fixed by Evaluator-Side Changes

The evidence incompleteness found in this incident is not addressable by:
- Increasing the number of evaluators
- Raising the panel consensus threshold
- Changing evaluator temperature or sampling parameters
- Adding more detailed scoring rubrics
- Changing the LP-07 prompt to ask more specifically about share percentages

All of these operate downstream of evidence assignment. An evaluator cannot find what is not in its context. The ceiling fix (421B) was necessary but insufficient: it ensured Gemini is not truncating, but Gemini can now produce a full 127,480-char extraction in which the key-terms table is still absent from LP-07 — not because of truncation, but because it was assigned to LP-00.

---

## 6. What Not to Do

**Do not freeze either post-ceiling hash as a baseline.** The two post-ceiling hashes (`d3e62ead`, `f7f64b5c`) differ by 6 material LPs. Freezing either as "the Gemini extraction" would import nondeterministic evidence-assignment choices into all downstream evaluations.

**Do not run the N=10 panel baseline on the current extraction architecture.** The purpose of the panel baseline is to characterize evaluator variance on a stable evidence context. The evidence context is not stable (6/33 LPs vary materially across Gemini runs). Running the panel on varying evidence would measure the convolution of evaluator variance and evidence variance — an unmeasurable mixture.

**Do not build Stage 5 stabilization on the current evidence-assignment architecture.** Stabilization measures operating on the evaluator panel or scoring layer cannot compensate for evidence incompleteness upstream. A stable evaluator panel consistently wrong about LP-07 because the Exclusions list is missing is not a better result than an unstable panel.

**Do not implement extraction caching.** Caching would freeze one instance of the nondeterministic evidence assignment and make the incompleteness persistent across all future evaluations on that document.

**Do not change cam/core/, prompts, evaluator identities, or scoring logic.** This incident is an extraction architecture finding. It does not implicate the evaluator governance framework, which continues to function correctly on the evidence it receives.

---

## 7. What Still Survives

The following findings and implementations from the prior arc are valid, durable, and unaffected by this incident:

- **414 — Evaluator identity freezing.** The three-role frozen panel (A=Anthropic/Claude, B=OpenAI/GPT, C=XAI/Grok) with fail-closed fallback integrity is correctly implemented and does not need revision.

- **415/416 — Config integrity.** `_check_generation_integrity()` correctly asserts that declared generation parameters match outbound API payloads. The gpt-5.5 temperature=1 constraint is correctly documented. This layer is independent of evidence assignment.

- **421B — Extraction integrity guard.** `ExtractionIntegrityError`, the canonical fail-closed guard, the 32k→65k ceiling increase, evidence hashes, and the stub-provision guard are all correct and necessary. The ceiling increase confirmed that the prior `ab80aafe` hash was an artifact of deterministic truncation, not Gemini's natural output. The guard infrastructure is the right foundation for the next architecture step.

- **The evidence hash infrastructure (421B).** `source_document_hash`, `extraction_output_hash`, and per-LP `tenant_text_hash` are the right audit primitives. They will become more important, not less, as the extraction architecture evolves — they are what allow a pipeline run to be attributed to a specific evidence context.

- **The Gate 3 rescoping decision (422, Decision 1).** The industrial known-absent set `{LP-20, LP-21, LP-23, LP-31}` is correctly identified. The latent `NOT_APPLICABLE` vs `extraction-failed` distinction in the `AMBIGUOUS` schema state is a real issue that Gate 3 rescoping should address.

- **The N=10 probe data (422).** The 10 extraction runs and their hashes are valid measurement data. The hash distribution (f7f64b5c=8/10, d3e62ead=2/10) accurately characterizes Gemini's behavior on this document at the current extraction ceiling. The LP-level diff is a reliable record of what differs and where.

- **The attorney validation findings as reported.** The lawyers' reactions to the CAM output they reviewed are genuine and are recorded accurately. The caveat is on the scope of what those reactions validate — they validate CAM's handling of the evidence contexts it had, not CAM's Operating Expense coverage analysis in the general sense.

---

## 8. Patent / Product Framing

The evidence-assignment incident is not a failure of the CAM governance framework — it is a finding about the boundary between extraction and evaluation that the framework needs to govern.

**The patent claim is not weakened by this finding.** CAM's contribution is governed assertion across a frozen evaluator panel with structured evidentiary constraints. The finding here is that the evidentiary input to that panel needs to be governed with the same rigor as the panel itself. That is an extension of the CAM doctrine, not a contradiction of it.

**The concept of governed evidence capture** — ensuring that the evidence presented to evaluators is complete, attributable, and not nondeterministically varying on material content — is a natural extension of the "citation or it didn't happen" principle (Guardrail #2) from the evaluator layer to the extraction layer. A citation to a clause that was not in the evaluator's evidence context is not a valid citation. The extraction architecture must support the citation guarantee.

**Non-exclusive assignment and global key-terms context** are the extraction-layer analogs of the evaluator-layer multi-instance evidence injection (cross-LP text injection, Supplement #05-12). The patent record already contains reduction-to-practice of cross-LP injection for element-level evidence. Non-exclusive assignment at the extraction layer is the corresponding claim at the extraction layer.

**The product framing:** CAM should be able to assert that when it finds a provision present or absent, the evaluators were working from a complete evidence context for that provision. Without non-exclusive assignment or global key-terms context, that assertion cannot be made for cross-cutting provisions. The commercial claim "CAM tells you whether the key tenant protections are present" requires that CAM actually had the key tenant protections in scope for each relevant evaluator call.

**Scope discipline:** The mechanism described (destructive exclusive assignment, evidence incompleteness) is general to any lease/contract pipeline that extracts by partitioning a document into provision buckets. The specific measurements (6/33 LPs varying, hash distribution, LP-07 exclusions absent 20% of runs) are Atreca-specific. The architecture implication is general; the severity on other documents is unknown until measured.

---

## 9. Recommended Next Step

Write `build_log/422_evidence_assignment_architecture_spec.md`.

This spec should address:

1. **Non-exclusive assignment design.** Define the extraction doctrine: what triggers a clause being assigned to multiple LP buckets, how duplicated content is represented in the extraction artifact (to avoid evaluator confusion about double-counting), and what the extraction output schema needs to support multi-LP assignment.

2. **Global key-terms context design.** Define the structure of a document-level key-terms block extracted independently of LP bucketing: quantitative parameters (shares, percentages, dates, dollar amounts), parties, and cross-referencing tables. Define where this block is injected (as a prefix to every LP evidence context, or as a separate evaluator step that populates a structured context object).

3. **Gate 3 rescoping implementation.** Code the Gate 3 fix: known-absent industrial set `{LP-20, LP-21, LP-23, LP-31}` allowed empty tenant_text; all others hard-fail. This is an immediate implementable fix that does not require the broader evidence-assignment redesign.

4. **Extraction baseline protocol.** Define what a clean extraction baseline looks like: zero stubs in non-known-absent provisions, key-terms table present in LP-07 and LP-02 contexts, zero repair fired, hash stable across N≥5 runs. This protocol gates the Step 422 frozen-panel baseline.

5. **Atlas validation annotation.** Add a caveat note to `Docs/Patent_Current_State.md` scoping the attorney validation: the lawyers' assessments are genuine; the Operating Expense coverage findings from those runs were produced without the LP-07 quantitative parameters in scope; attorney validation of LP-07 Operating Expense coverage specifically remains outstanding.

**The incident report is complete. No code changes were made. No baseline runs were executed. No data was pushed.**

---

*Report sources: build_log/421B_extraction_integrity.md, build_log/421B_followup.md, build_log/422_code_status.md (Step 422 investigation data). N=10 probe output. Atlas pipeline_results.json search (3 files). 101 Gemini-primary pipeline result file search.*
