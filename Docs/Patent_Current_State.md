# Patent Current State

**Purpose:** This is the orienting document for AI chats working on CAM.
Reading this gives you the full patent architecture without needing to
read all 20+ patent supplements. Parallels `CAM_Current_State.md`
(which orients to the build state); this orients to the patent state.

**Last updated:** 2026-07-13 (attorney-validation scope annotation — evidence-assignment incident, Step 421C. Prior: 2026-07-12 — evaluator config boundary, two-story contamination, assertion scope, Steps 416b + 417 spec. Prior: 2026-07-08 — evaluator fallback integrity and frozen-stack provenance, Steps 411–412; 413 design spec written. Prior: 2026-06-13 (Supplement #25 Architecture A Phase 2 written + indexed; Step 397 closed-form question-set design; attorney question bundle assembled.) Prior: 2026-06-12 (cross-domain auditor / governance lineage; three-layer directional governance architecture; refined minority doctrine — Supplement #24.)

> **Candidate note (2026-07-13) — attorney-validation scope annotation: evidence-assignment architecture incident (Step 421C).**
>
> **Finding.** The Atreca lease contains a key-terms table at character 1,994 specifying Tenant's Share of Operating Expenses (100%), Building's Share of Project Operating Expenses (45.79%), and Rent Adjustment Percentage (3%). Step 421C confirmed that this table did not appear in any LP's extracted `tenant_text` in any of the 101 known Gemini-primary pipeline runs, nor in any of the 3 Atlas pipeline_results.json files (lease_20260419_201646, lease_20260419_202420, lease_20260420_001026). When the table appears in a Gemini extraction, it lands in LP-00 (Parties & Premises), which has `identity_check: true` in the provision taxonomy and is not evaluated for coverage. In the modal Gemini hash (f7f64b5c, 8/10 post-ceiling runs) it does not appear in any LP at all.
>
> **Scope of attorney validation.** The external CRE attorney review (Phase 1, n=3, R1/R2/R3) assessed CAM output produced from these pipeline runs. The attorneys' reactions to what they saw are genuine professional reactions to the output they reviewed. This annotation scopes what those reactions validate:
>
> - **Coverage assessments on LP-07 (Operating Expenses) specifically are not validated.** The evaluators assessing LP-07 did not have the 100% tenant share or 45.79% building share parameters in scope. A finding of "present" or "missing" on the Operating Expense tenant-share mechanism was made without the quantitative parameters that define the mechanism's effect on this tenant.
>
> - **Coverage assessments on other provisions are not affected by this annotation**, except for LP-02 (Rent Escalation, 3% parameter) where the same cross-LP dependency exists. All other validated findings were produced from evidence contexts not known to be missing material provisions.
>
> - **The "citation or it didn't happen" principle (Guardrail #2) applies upstream.** A citation to a clause that was not in the evaluator's evidence context is not a valid citation for the purposes of coverage assertion. The evidence-assignment architecture must be governed with the same rigor as the evaluator panel.
>
> **Patent framing.** The governed evidence capture requirement — ensuring completeness and non-destructive assignment of evidence to evaluators — is a natural extension of Guardrail #2 to the extraction layer, and of the cross-LP text injection architecture already reduced to practice at the element layer (Supplement #05-12). Non-exclusive assignment and global key-terms context are the extraction-layer analogs of those evaluator-layer mechanisms. A full patent supplement on governed evidence capture will be written when the architecture is designed and reduced to practice (see `build_log/421C_evidence_assignment_incident.md`, Section 9).
>
> **Baseline status.** Steps 417, 419, 420 remain valid as evaluator-variance measurements but are not valid coverage baselines for the 6 materially varying LPs. Step 423 (policy resimulation) is blocked until a clean baseline with complete evidence contexts is established.

> **Candidate note (2026-07-12, updated) — evaluator config boundary: two-story contamination; assertion scope; variance measurement scoped (Steps 416b, 417 spec).**
>
> **Three clarifications to the 2026-07-12 config-integrity note below.**
>
> **1. Two distinct contamination stories, not one.** The 416 note described Role B operating at temperature=1 since 2026-03-18. This is accurate but conflates two structurally different situations:
>
> - **Story A — Role B primary (gpt-5.5):** gpt-5.5 was always at temperature=1 regardless of the adapter bug, because the model rejects non-default temperature at the API level. The broad guard happened to produce the correct effect (not transmitting temperature) for the wrong stated reason (the comment cited gpt-5.2, which is wrong). The 416 fix preserves this exception explicitly. **This is a standing capability constraint, not a contamination window that closes.** All runs using gpt-5.5 as Role B primary — from 2026-03-18 forward, and all future runs while gpt-5.5 is primary — have Role B at temperature=1.
>
> - **Story B — Role B own-chain fallback / Stage 7 B (gpt-5.4):** gpt-5.4 accepts temperature=0. The broad guard incorrectly dropped it. This is a genuine contamination window: **2026-03-18 through 2026-07-12** (commit `784efa7` through `a0fe4a3`). The 416 fix corrects this. Runs after `a0fe4a3` transmit temperature=0 on the gpt-5.4 path.
>
> **Patent framing consequence:** A paper citing evaluator-stack reproducibility should distinguish (a) identity-freezing, (b) config-integrity assertion, and (c) deterministic sampling capability as three separate properties. CAM governs (a) and (b). It does not govern (c) for Role B primary: gpt-5.5 cannot be temperature-pinned. The stronger and more accurate claim is that CAM governs disagreement and variance across a frozen evaluator panel, including a member that cannot be pinned to temperature=0. The panel produces governed output despite a stochastic evaluator — and Step 417 will measure how much residual variance remains.
>
> **2. Assertion scope is partial, not total.** `_check_generation_integrity()` covers the three parameters declared in evaluator config (temperature, max_tokens, reasoning_effort). It is complete over the declared set but not over the full provider parameter space. Parameters not declared on ModelTarget (top_p, top_k, penalties, seed, JSON mode) are not checked. This is the correct scope: asserting the absence of undeclared parameters would be vacuous. If future evaluator configs add parameters, they must be added to EVALUATOR_CRITICAL_PARAMS.
>
> **3. Step 417 (post-416 Stage 5 baseline) scoped.** The spec (`build_log/417_post_416_stage5_baseline_spec.md`) measures the irreducible residual Stage 5 wobble rate after 414/416. Required: N≥10 on the Atreca fixture, per-LP frequency distributions, per-role flip counts (A/B/C separated), variance source classification. This answers whether remaining instability is primarily attributable to Role B's temperature=1, or whether Role A/C also produce meaningful same-model variance at temperature=0. The measurement has not yet run.

> **Candidate note (2026-07-12, original) — evaluator request-configuration integrity (Step 416). Companion to the 411–412/413–414 identity-integrity arc.**
>
> **Separate invariant from identity integrity.** Step 414 (fallback integrity) guards evaluator identity — the right model answers in the right role, and substitution is auditable. Step 416 adds a second, orthogonal invariant: declared evaluator generation parameters must match the outbound provider payload, or the mismatch must be backed by a documented capability exception. These are distinct claims about the frozen stack:
> - Identity-frozen: A=Anthropic, B=OpenAI, C=XAI, with no silent cross-provider substitution.
> - Config-frozen: declared temperature=0 (or other generation parameters) actually transmitted to the provider.
>
> **Finding (Step 415–416):** The panel was identity-frozen after 414 but not config-frozen before 416. The OpenAI adapter (introduced 2026-03-18) dropped `temperature` from the payload for all gpt-5.x models via a broad `startswith("gpt-5")` guard. Role B was operating at provider-default temperature=1 rather than declared temperature=0 since that date.
>
> **Model capability finding (Step 416 probes, 2026-07-12):** gpt-5.5 (Role B primary) cannot accept temperature=0 — only temperature=1 (default) is accepted. This is a provider/model capability constraint, not an adapter defect. gpt-5.4 (Role B fallback / Stage 7 B) does accept temperature=0 and now transmits it. The frozen-stack temperature property therefore differs by model tier within the same role.
>
> **Patent relevance:** A paper claiming a "deterministic three-evaluator stack" or "temperature-zero evaluator panel" should scope that claim to the post-416 state and, for Role B primary (gpt-5.5), acknowledge the model capability constraint. The accurate characterization is: the panel is identity-frozen and config-integrity-asserted; Role B primary operates at provider-default temperature because the model's API does not support temperature=0; this is a documented exception, not a silent failure. Full supplement deferred to the broader evaluator-integrity supplement after 413/414/416 arc closes.

> **Candidate note (2026-07-08) — evaluator fallback integrity and frozen-stack provenance (Steps 411–412; 413 design spec written). Not a full supplement. Full supplement deferred until 413 implementation and validation.**
>
> **1. Provenance confirmed, worst-case silent laundering not observed.** Step 412 confirmed that `is_fallback`, `actual_model`, and `fallback_reason` are recorded at per-element, per-LP evaluator_meta, and LP-level lp_meta granularity. Step 372a already prevents verdict laundering (fallback verdicts are no longer emitted under the primary model's label). In the N=2 Atreca pair measured in Steps 411–412, no silent fallback was observed — both fallback instances had `is_fallback=True` correctly flagged and the actual (Gemini) model correctly attributed. This is a dataset observation, not proof silent fallback cannot occur; the provenance fields make fallback auditable going forward.
>
> **2. Role C structural weakness: empty own_chain after grok-3 retirement.** `EVALUATOR_C_FALLBACK = ("xai", "grok-4.3")` (same model as primary); `own_chain=[]` in EVALUATOR_LINEUP_305 (grok-3 retired 2026-05-15). A first Grok 4.3 failure has no same-provider retry and crosses model families directly to Gemini 2.5 Pro from the shared pool. Roles A and B each have one intra-family buffer (Haiku, GPT-5.4) before reaching the shared pool. Role C has no such buffer. A nominal A/B/C frozen stack can become A/B/Gemini for any LP where Grok 4.3 fails, unless canonical-mode rules prevent or explicitly mark it.
>
> **3. Config-drift class, not a Grok-specific quirk.** The root cause is a retirement event (grok-3 retired 2026-05-15) that left own_chain empty with no enforcement. Roles A and B inherit the same structural gap on the next relevant retirement (if claude-haiku-4-5-20251001 or gpt-5.4 are retired and own_chain is not repaired). Evaluator-stack integrity therefore depends on config that silently degrades on provider retirement. This is a lifecycle management gap, not a specific-model problem. The durable fix (Step 413 design spec) is a startup guard that refuses to run or warns loudly when any role's own_chain is empty without a declared justification, converting the failure mode from runtime-silent to startup-loud.
>
> **4. Patent relevance: evaluator identity is part of the claimed/reported method.** The method describes a three-evaluator frozen-stack evaluation (A=Anthropic, B=OpenAI, C=XAI). A run where role C is sometimes Gemini (Google) is not a clean frozen-stack run. Whether this matters for claim construction depends on the specific claim language ("configured to use" vs "using"; "substantially all" qualifiers); the conservative answer is that a canonical run for patent purposes must either enforce strict evaluator identity with fail-closed/abstain behavior, or explicitly mark cross-family fallback and exclude degraded runs from frozen-stack and reproducibility claims. Provenance fields make the fallback auditable; they do not themselves make the run canonical.
>
> **5. Frequency caveat and frequency-claim discipline.** The N=2 measurement (1 fallback event per run = 3.1% of LPs) is too small to characterize baseline Grok failure rate. "Zero silent fallbacks" is a dataset observation. Do not overclaim: the durable patent-relevant statement is that provenance fields make fallback auditable, not that silent fallback is impossible or that fallback rate is negligible. The material-impact finding (both measured fallbacks changed LP coverage state across the Stage 7 flagging threshold) is concrete and documented.
>
> **Full supplement deferred.** A full patent supplement covering the evaluator-stack integrity doctrine, retry architecture, canonical/product mode distinction, and the retirement-drift guard will be written after Step 413 is implemented and validated. The 413 design spec is at `build_log/413_fallback_integrity_design.md`.

> **Paper-arc note (2026-06-13, steps 396–397 + patent consolidation; all paper, freeze-safe, NO model calls, NO build).** Three deliverables, no new reduction-to-practice, patent contribution map essentially unchanged (one supplement FORMALIZED, not newly invented):
>
> - **Supplement #25 WRITTEN (Architecture A Phase 2).** `Patent_Supplement_2026_06_13.md`. This is the formalization of ALREADY-RTP'd work (LP-layer verdict distance + Stage 5f confidence cap, Steps 351/351b/352, 2026-05-19/20) that was owed a standalone supplement before the attorney conversation. Not a new invention — the second instantiation of Supplement #18's ordinal-distance governance (element-layer counterpart = Supplement #21), which converts #18's "operates at every layer" generality from one-instance-plus-assertion into two demonstrated instances. Key content: deliberate-gap rank scale (IP↔MI=4 severe, UN↔MI=2 moderate; a linear scale cannot produce both); consequence-coupled cap applied downstream of Stage 5e; NOT_ASSESSED sentinel ("never assessed" categorically distinct from "assessed and agreed"); confidence-cap and review-priority as separately-derived distance outputs. One honest open empirical item: a live 32-LP real-API T-10 severity distribution (core logic validated synthetically + via Atlas regression). Indexed in Supplement Index (#25), Contribution Map, and the pending-item flipped to WRITTEN.
>
> - **Step 397 — closed-form question-set design (paper half; `build_log/397_closed_form_question_set_design.md`).** Designed **Axis 5** to give the §8.3 absence trap a closed-form home, because the four RTP'd present-text axes (same-risk / obligation-without-remedy / conditional-protection / unilateral-control) structurally cannot grip an ABSENCE shape — confirmed empirically in Step 389 (closed-form flagged LP-03 5/5 but found the renewal issue, NOT the §8.3 trap). Axis 5 = four-component-anchored "obligation running against a foreseeable landlord failure, with no paired relief document-wide," gated by scope-completeness (returns not_assessable on partial uploads — same discipline as the NOT_ASSESSED sentinel). On-paper forcing-test against four known findings: Axis 5 FIRES on LP-03 §8.3 (closes the gap the four axes miss), stays correctly SILENT on LP-26 (conditional-protection) and §11.2 (indemnity) — the discrimination property, the Axis-5 analogue of the LP-11 scalpel proof. The fifth-axis-vs-Axis-2-variant SLOT stays open (question text is slot-agnostic; decided later by lawyer panel + a populated-work warehouse counter-lease). **This is the closest-to-buildable concrete instance of recall governance (Future Patent Item B / Bundle D3) — "the framework guarantees the question is structurally ASKED rather than relying on a model to volunteer it."** NOT built; NOT a patent contribution yet; world-question (is LP-03 §8.3 a true risk) stays lawyer-panel-gated.
>
> - **Attorney Question Bundle assembled (`Docs/Attorney_Question_Bundle.md`).** Consolidated, theme-grouped, grounded question list for the PATENT-attorney claim-scope conversation (target before Sept). Updates the June-9 review's Part 4 list + the four parked-strategic items (each logged as "attorney question, not a build") + today's new questions (Axis-5 as recall-governance proof case; three-layer architecture claimability; Layer-2 build-vs-describe). Six starred load-bearing questions: support map / detectability / §101 posture / prior-art / public-disclosure-foreign-filing / second-domain-build-or-not. Explicitly distinguishes the PATENT attorney (claim scope, this bundle) from the CRE-attorney PANEL (is-the-finding-correct, Packet 02) — different person, different conversation.
>
> **Binding-constraint reminder (unchanged and now sharper):** external validation is still at ZERO; the June-9 review named it the largest project risk. This arc added three more internal documents to a deep pile. The next high-value move is NOT more paper — it is the EDGAR mini-corpus (startable alone, no lawyer) or getting one lease in front of one lawyer. Discipline for next session: do not let upstream paper become a place to live.
>
> **Build-state note (2026-06-12, cross-domain auditor arc — steps 389–392B):** the build advanced
> through the closed-form directional prototype (389), Axis-2 tightening (391), and a cross-domain
> auditor lineage investigation (392A) plus a paper test of a light trace auditor against real lease
> traces (392B). **One new patent contribution arose: Supplement #24.** It is best characterized as
> **reduction-to-practice + refinement of the already-described "Optional Auditor Capability" (§7 of
> the generalized-framework Technical Overview)**, NOT a from-scratch new claim. Summary of patent
> relevance:
>
> - **Cross-domain auditor lineage (392A).** The auditor role — an independent check on reasoning
>   QUALITY that can invalidate/withhold a finding even under evaluator agreement, distinct from the
>   votes — is reduced to practice across FOUR benchmark domains with increasing sophistication:
>   FEVER (standalone process audit) → GPQA (audit + adversarial unanimity-challenge falsification) →
>   SciFact (audit flag + rule library + withhold + conviction test, with a DOCUMENTED over-withhold
>   failure, RULE-SF-002) → ContractNLI (audit + elimination + model-diversified governance, with a
>   QUANTIFIED precision/recall tradeoff: CCA 80.4%→83.2%, Withheld 17→33, many correct findings
>   withheld). The measured recall COST is itself part of the record. This is the patent-relevant
>   asset and it strengthens the domain-generality claim. The lease analyzer is the FIFTH domain
>   instance and the only one lacking the layer.
>
> - **Three-layer directional governance architecture (392B).** The directional pipeline decomposes
>   into Layer 1 axis discipline (closed-form questions decide what gets asked) / Layer 2 trace
>   auditor (decides whether the answer is validly reasoned) / Layer 3 materiality-routing (decides
>   whether valid answers warrant protective action). The auditor SITS BEFORE routing and is
>   forbidden from judging materiality. New Guardrail #17.
>
> - **Refined minority doctrine.** A lone evaluator survives because its trace is VALID (specific,
>   cited, no smuggled assumption), not merely because it produced a finding. This REFINES Supplement
>   #15-b ("minority never silenced") — the audit-trail preservation guarantee is unchanged; a
>   validity gate is added in front of the routing decision. New Guardrail #18.
>
> - **LP-15 boundary case (canonical).** LP-15 migrated, across the 390→391 tightenings, from an
>   auditor-validity problem (390 hypothetical "such as" trace — killable by a light auditor) to a
>   MATERIALITY problem (391 specific cited $10M/$5M + negligence/gross-negligence trace — passes the
>   auditor by design; B/C judge it immaterial = genuine 1-vs-2 materiality split). LP-15 is now a
>   Layer-3 materiality/routing case, not a Layer-2 auditor-validity failure — possibly a
>   correctly-surfaced contested finding mislabeled as a wish-list control.
>
> - **Lease-domain porting constraint.** Port the LIGHT FEVER-style trace-compliance auditor; do NOT
>   port the heavy SciFact/ContractNLI withhold/elimination machinery, because over-withhold suppresses
>   CORRECT findings and in a legal tool a withheld correct Risk finding is the unforgivable failure.
>
> - **Open Layer-1 item (§8.3).** The §8.3 Landlord's-Work / fixed-commencement trap remains
>   unsurfaced — a trap of ABSENCE (fixed rent obligation, missing abatement remedy), a different
>   shape than the four present-text axes. This is a Layer-1 axis-completeness question (is it Axis-2
>   not triggering, an Axis-2 absence-of-remedy variant, or a fifth axis?), paper/design work,
>   SEPARATE from the auditor and NOT something the auditor can or should compensate for.
>
> Net: the contribution map and supplement index ARE updated by this arc (Supplement #24 added).
> Two new guardrails (#17 three-layer architecture; #18 refined minority validity gate). All
> quantitative lease findings remain single-lease (Atlas), DIRECTIONAL, and OUT of the patent record
> except as example/validation context; the cross-domain auditor evidence is the reduced-to-practice
> patent asset. Layer 2 (light auditor) is designed + paper-validated but NOT built; Layer 3
> (materiality/routing) is open and blocks DEF-002. Architecture A Phase 2 standalone supplement is
> still owed (unchanged).
>
> - **§8.3 absence-trap Layer-1 census (Step 393; paper/read-only, NO build, NO model calls).**
>   The §8.3 Landlord's-Work / fixed-commencement trap is a trap of ABSENCE (fixed §3.1 rent
>   obligation "without abatement" + foreseeable §8.3 delivery failure + no paired relief anywhere)
>   that the four PRESENT-TEXT axes cannot grip. Design-option (a) "Axis-2 already covers it, just
>   not triggering" is ELIMINATED: Axis-2 q_a tests an obligation LINKED TO a named landlord
>   failure, while the §8.3 obligation runs REGARDLESS OF any landlord condition — inverse polarity,
>   confirmed mechanically against the prompt text. An absence-evidence contract v0 is fixed with
>   Element 2 drawn NARROW (counterparty PERFORMANCE FAILURE only; no-fault external events excluded)
>   to keep the first test case clean. Three candidate families are kept separate: (1)
>   performance-failure absence-of-relief (the §8.3/LP-01 shape; build target = Axis-2 absence
>   variant), (2) no-fault loss-allocation (the LP-14/force-majeure shape; parked fifth-axis
>   CANDIDATE, NOT in v0), (3) interim-relief gap (the §5.1 cure-window cluster across ~8 LPs; tagged
>   PARTIAL — termination is relief but not INTERIM relief). On Atlas the performance-failure shape
>   is a NEAR-SINGLETON (LP-01 only). **(b) Axis-2 variant vs (c) fifth axis stays OPEN** — one lease
>   cannot settle it, and the count is downstream of two definitional forks (Element-2 scope;
>   relief-adequacy "ever" vs "interim") that a second lease + Layer-3 calibration must pin down.
>   Build-lean provisionally (b). Document-scope precondition (full lease IS fed to every evaluator,
>   confirmed in code; not-assessable/scope-incomplete state becomes MANDATORY before production and
>   for multi-document packages). Full detail in Supplement #24 §9; source
>   `build_log/393_absence_census_RESULTS.md` (local commit `c95ad56`, not pushed).
>
> - **§8.3 second-lease census + corpus scan (Step 394a; paper/read-only, NO model calls; local
>   commit `06a5817`).** Ran the same narrowed absence contract v0 statically on a SECOND lease
>   (T-10, retail, placeholder Exhibit B) plus a boundary-control census on T-08 (force-majeure-heavy).
>   **Result — T-10 is INDETERMINATE on the §8.3 recurrence question, NOT a counter-instance:** T-10's
>   Landlord's-Work structural hooks exist (§1.1(j), §2.1 "if any," Exhibit B) but Exhibit B is an
>   unpopulated bracketed placeholder and the Commencement Date is a circular cross-reference (not a
>   fixed calendar date), so the landlord performance failure is not foreseeable-from-text and CANNOT
>   be scored a confident YES. 0 v0-YES across 24 assessable LPs (15 PARTIAL / 9 NO / 8 NA). **T-08
>   boundary HOLDS:** robust §16.3 FM rent abatement (full/proportionate) → LP-14 = NO; the no-fault
>   family stays cleanly outside v0. **Corpus-scan headline (the load-bearing finding): Atlas is the
>   ONLY fixture in the entire ~22-file test corpus with a POPULATED Exhibit B** ("4 dock levelers,
>   HVAC upgrades, LED lighting, 400A/480V electrical"); every other fixture (T-01..T-16, T-10-NY,
>   templates) has a placeholder or no Exhibit B. **Interpretive consequence (recorded with strict
>   wording discipline): ZERO CLEANLY-MEASURABLE CROSS-LEASE RECURRENCE INSTANCES CURRENTLY EXIST —
>   NOT "zero instances exist."** Atlas IS a clean, grounded instance (populated Exhibit B + rent
>   fixed to a calendar date independent of buildout = Element 2 grounded, not assumed); what is
>   missing is a SECOND clean instance. The (b)-vs-(c) call stays OPEN but the build-lean toward (b)
>   Axis-2 absence variant is REINFORCED — not because the pattern is weak (it is well-grounded on
>   Atlas) but because no available second fixture can EXERCISE it, so a fifth-axis claim would be
>   premature on evidence AVAILABILITY, not evidence-against. **Gating requirement to revisit (c):**
>   an EXECUTED commercial/retail lease with a populated, specific Landlord's-Work exhibit — template
>   fixtures cannot test it. Full detail in Supplement #24 §9; source
>   `build_log/394a_second_lease_census_RESULTS.md`.
>
> - **§8.3 FIRST REAL external populated-work lease — Albireo census (Step 394c; paper/read-only, NO
>   model calls; durable fixture committed locally, not pushed).** Obtained and censused the first
>   REAL, EXTERNAL, POPULATED-Landlord's-Work lease — the Albireo Pharma / SHIGO 10 PO Owner LLC office
>   lease (10 Post Office Square, Boston MA; executed; SEC Exhibit 10.1; 2017-02-07). This satisfies the
>   394a gating requirement (executed lease with a specific populated Landlord's-Work exhibit) that no
>   corpus fixture except Atlas could meet — Exhibit C Work Letter (10 enumerated construction items)
>   + Exhibit E Building Finish Specifications (3 pages) + Exhibit D Concept Plan (Dyer Brown
>   Architects), MORE populated than Atlas. Durable fixture at
>   `05 Lease Analyzer/test_data/tenants/albireo_10postoffice_lease.txt`, regenerable via
>   `build_log/build_albireo_fixture.py` from the SEC HTML (self-verifies 6 load-bearing clauses;
>   verification passed 2026-06-12). **Result — Albireo is a clean NO on the §8.3 absence shape, and a
>   NO for the MOST INFORMATIVE reason: it CONTAINS exactly the paired relief whose ABSENCE defines the
>   Atlas trap, in three layers** — (1) Commencement tied to delivery (§1: rent runs from the LATER of
>   Target Date or Substantial Completion + possession, so the tenant structurally cannot owe rent on
>   undelivered space — inverse of Atlas's fixed calendar date); (2) express §3.1(C) day-for-day Base
>   Rent credit for late delivery past the April 1 outside date, stacked on the 2-month Rent Abatement;
>   (3) §7.1/§14/§15 abatement corroborating comprehensive rent-relief drafting. **The §34 wrinkle
>   (design lesson): Albireo has an aggressive Independent-Covenants / no-setoff clause (§34, §6.1) —
>   the KIND of clause that in Atlas would BE the trap — yet it does NOT create the §8.3 shape, because
>   §3.1(C) is a carved-out, self-executing rent CREDIT that coexists with the no-setoff regime.
>   Design consequence for the Axis-2 absence-variant diagnostic: do NOT infer the §8.3 shape from an
>   aggressive no-setoff clause alone; check whether a carved-out self-executing delivery remedy
>   coexists.** **Interpretive consequence (strict wording discipline): ZERO CLEANLY-MEASURABLE
>   CROSS-LEASE RECURRENCE INSTANCES OF THE §8.3 ABSENCE SHAPE CURRENTLY EXIST — NOT "zero instances
>   exist."** The honest tally is now Atlas = one clean ABSENCE instance, Albireo = one clean
>   PAIRED-RELIEF COUNTER-instance, T-10 = indeterminate. **(b)-vs-(c) stays OPEN, but the (b) Axis-2
>   variant lean is REINFORCED on EVIDENCE now (not just availability):** the first lease that CAN
>   exercise the hook lands on the counter-shape for a substantive reason (a well-drafted commercial
>   lease includes the delivery remedy as a matter of course), making the Atlas gap look IDIOSYNCRATIC
>   rather than recurrent. Caveats kept honest: Albireo is OFFICE vs Atlas WAREHOUSE (not a perfect
>   structural twin); one counter-instance no more proves (b) than one instance proved (c) — two real
>   data points now point the same way. **Gating requirement to revisit (c) is now sharper:** a
>   populated-work lease with fixed-date rent AND no delivery-failure relief (a populated-work WAREHOUSE
>   counter-or-confirming lease would be the strongest next data point). Full detail in Supplement #24
>   §9b; source `build_log/394c_second_real_lease_census_RESULTS.md`.
>
> - **⚠ DOCUMENTATION HAZARD — LP-ID dual numbering (read before cross-referencing any "LP-NN").**
>   The closed-form directional prototype harness (Steps 389–392B) uses LP IDs that DO NOT match
>   `cam/adapters/lease_review/lease_provision_taxonomy.py`. The collision is PARTIAL, not total —
>   the dangerous kind: prototype LP-03 (Lease Term & Renewal) and LP-26 (Quiet Enjoyment) COINCIDE
>   with the taxonomy entries of the same number, but prototype LP-11 ("Rent Acceleration" → taxonomy
>   LP-11 is "Default & Remedies"), LP-15 ("Insurance" → taxonomy LP-08; taxonomy LP-15 is "Signage"),
>   and LP-19 ("Casualty" → taxonomy LP-24; taxonomy LP-19 is "Utilities") DO NOT. Prototype LP-27
>   ("Default and Remedies") RESOLVED to taxonomy LP-27 (Landlord Default & Tenant Remedies) by cited
>   clause content (§17.3 vs §5.1), NOT to label-similar taxonomy LP-11. A reader who spot-checks
>   LP-03/LP-26, sees them line up, and trusts the rest is wrong on four of six. The prototype numbering is internally consistent
>   across 389/390/391/392B, so NO finding is invalidated — but EVERY "LP-NN" in Supplement #24, its
>   canonical examples (LP-11 scalpel proof, LP-15 390→391 migration, LP-27 same-risk Axis-1), and the
>   directional-arc RESULTS docs is a PROTOTYPE ID. **Canonical crosswalk:
>   `Docs/LP_ID_Crosswalk_Directional_Prototype_to_Taxonomy.md`** (created 2026-06-12; documentation
>   containment only — no harness renumbering). **Standing rule:** directional-method docs from Steps
>   389–393 use prototype LP IDs unless explicitly marked "taxonomy LP-NN"; attorney-facing and
>   patent-facing summaries must cite BOTH prototype and taxonomy ID (e.g. "prototype LP-15 = taxonomy
>   LP-08 Insurance") until the harness is reconciled.
>
> - **Action ontology vNext — Leverage / Client Advantage axis + negative-space symmetry (Steps 395 / 395b; paper/design only, NO model calls, NO build, NO schema change, NO UI). DESIGN RESULT, not a patent contribution yet.** Two paper memos established that the finding object probably has TWO orthogonal dimensions, not one: **(1) protective disposition** (Risk / Improvement / Review Needed / Addressed / Standard — the existing axis, "what protects the client from harm?") and **(2) advantage disposition** (Leverage / Neutral — new, "what does the client hold that helps them?"). The decisive structural fact: the two are NOT mutually exclusive — the same clause can be Risk AND Leverage (e.g. a self-help termination right with a trap cure window) — so Leverage cannot be a fifth sibling bucket in a one-label-per-finding scheme; it is an orthogonal axis. "Favorable" is REJECTED as a label (sentiment, not action); "Leverage / Client Advantage" passes the action-test ("assert this / use this in negotiation"). **Negative-space symmetry (the spine):** the §8.3 absence machinery is one half of a general operator — *detect legally material absence, route it by who the absence favors or harms.* Adverse absence (missing protection that HARMS the client) is the §8.3/LP-01 shape already in the record; favorable absence (missing restriction / counterparty remedy / cap / consent right that HELPS the client) is the same four-element contract with the beneficiary reversed. Same engine, sign flip. It inherits the SAME document-scope discipline: favorable absence is a false-LEVERAGE generator on partial uploads exactly as adverse absence is a false-TRAP generator. **395b census result (Atlas + Albireo, capped, paper):** present-text leverage RECURS robustly on both leases (Atlas audit-teeth §3.4, exclusivity §24.14, security-deposit self-help §5.1; Albireo uncapped delivery credit §3.1(C)); favorable absence is REAL but DRAFTING-DEPENDENT — one clean instance on loosely-drafted Atlas (§15.2 permitted-transfer carve-out escapes §15.3 recapture), essentially NONE on tightly-drafted Albireo (a meticulous lease has little favorable absence for the same reason it has little adverse absence). **Sharpest evidence of the symmetry:** the Albireo §3.1(C) delivery credit is the SAME clause that scored as Atlas's adverse-absence counter-instance in §9b — present in Albireo it is tenant LEVERAGE, absent in Atlas it is tenant RISK. One clause, two axes, opposite leases. **Decision: AXIS WARRANTED** (present-text half robust; favorable-absence half real but thin, rides alongside the §8.3 adverse work under shared scope discipline + "needs a second clean instance" gating). One element needs lawyer calibration: WHICH leverage is material enough to surface (the advantage-axis analogue of the Layer-3 materiality question) — a future leverage-edition blind packet, distinct from the §8.3 packet. **Consequence for DEF-010: bucket-stability work must NOT harden around the single (protective) axis** — diagnose protective-axis variance now (paper, 383/386 artifacts), but do not build routing governance that assumes one axis, because the object model is becoming two-dimensional. Counterparty-Leverage parked as the v0-excluded mirror category. NOT a build authorization; NOT yet a patent contribution — earns its own supplement only IF adopted and built with a proof case. Full detail: `build_log/395_action_ontology_vnext_leverage_negative_space.md` and `build_log/395b_favorable_absence_census_RESULTS.md` (local, not pushed).

> **Build-state note (2026-06-10, recall-stability arc — steps 377–385):** the build advanced
> through a governance-correctness batch and a recall-variance investigation. **No new patent
> claims arose. The patent contributions below are unchanged.** Summary of patent relevance:
>
> - **Step 378 (`6990434`, shipped):** governance-correctness fixes (DEF-003 consequence support
>   floor; DEF-004 materiality majority-merge replacing strict-min, with no-majority routing to
>   Review Needed; DEF-005–009). These are RTP / correctness hardening of EXISTING claims (the
>   support-gated assertion and orthogonal-confidence/review doctrines), NOT new contributions. The
>   DEF-004 pin — "a one-evaluator materiality minority must not silently demote a two-evaluator
>   majority; no-majority materiality cannot assert an action bucket and routes to Review Needed" —
>   is an instance of the existing preserve-disagreement / support-gated-assertion doctrine, not a
>   new claim. Validated live (Dir-18, Dir-21) on the post-push repeatability check.
>
> - **DEF-010a (`d134ef8`, shipped):** Stage 305 coverage consensus now normalizes the four
>   present-like verdict labels to one tier for the EXISTENCE-consensus computation only, while
>   preserving the exact mechanism labels for audit and leaving the verdict-distance ladder
>   unchanged. This is implementation hygiene / RTP — it corrects a merge that conflated
>   mechanism-disagreement with existence-disagreement. NOT itself a new claim. BUT it surfaced a
>   genuine future-patent item (see below).
>
> - **FUTURE PATENT ITEM A — two-axis coverage model (existence vs mechanism).** Flagged, NOT built,
>   NOT a contribution yet. The insight: a single coverage verdict token carries TWO orthogonal
>   questions — EXISTENCE (is the protection present?) and MECHANISM (explicit / implicit /
>   default-law / cross-LP). Prior art (ensemble agreement, conformal/selective prediction,
>   LLM-as-judge) computes agreement on a single token; the novel move is computing consensus
>   PER AXIS because the axes have DIFFERENT governance consequences (existence-disagreement gates
>   inclusion; mechanism-disagreement modulates confidence and triggers jurisdiction/default-law
>   warnings). Same evaluators, two independent consensus computations, two distinct downstream
>   consequences. This is the same preserve-disagreement principle as the sign demotion (Supp #23)
>   and materiality-provenance (378) — a third occurrence, which strengthens it as an architectural
>   pattern. Full write-up in `build_log/parked_strategic_ideas.md`. **ACTION: attorney question at
>   claim-scope finalization ("is the existence/mechanism separation a distinct claimable
>   contribution, and does building it strengthen scope vs describing it?"), NOT a build during the
>   current arc. Write a supplement only IF/WHEN built with a proof case.**
>
> - **FUTURE PATENT ITEM B — candidate-completeness / recall governance.** Flagged, NOT built.
>   The 380–384 investigation produced hard evidence (LP-13, then LP-03) that the framework's
>   governance only governs candidates that EXIST — a material, high-confidence finding can
>   intermittently fail to be GENERATED upstream of all the assertion governance. CAM's existing
>   claims are precision-side (WHEN to assert); recall-side governance (did the candidate get
>   generated at all) is currently thin. A candidate-completeness / union-candidate-generation
>   governance layer would be a distinct contribution that closes the most obvious attack on the
>   framework ("you govern beautifully over whatever you happened to notice"). **ACTION: attorney
>   question; supplement only IF/WHEN built with a proof case. Do not inflate into a claim before it
>   exists.**
>
> - **LIVE VALIDATION OF EXISTING DOCTRINE (non-deliberation, Supp #22) — potential evidence, not a
>   new claim.** The 384 finding that LP-19 and LP-26 show persistent 1:1:1 evaluator splits on
>   use_consequence (harmful/beneficial/context_dependent) across runs may be genuine interpretive
>   ambiguity, not nondeterminism noise. IF a fixed-fee CRE-lawyer micro-panel splits the same way
>   on those clauses, that is LIVE EVIDENCE that CAM's preserved disagreement is CALIBRATED to
>   genuine professional disagreement — i.e. CAM is uncertain exactly where competent humans are
>   uncertain. This would SUPPORT (not extend) the deliberate-non-deliberation claim (Supp #22) with
>   a concrete lease example. The lawyer-calibration design deliberately uses a PANEL distribution,
>   not a single oracle, because "is this clause contested" is a question a single expert cannot
>   answer. All such findings remain n=1/n=2-contract, DIRECTIONAL, OUT of the patent record except
>   as limited example/validation context. See `CAM_Current_State.md` (2026-06-10 frontier) and
>   `build_log/defects.md` (DEF-010 through DEF-012).
>
> Net: the patent contribution map and supplement index are UNCHANGED by this arc. Two future items
> (A, B) are parked as attorney questions. One existing doctrine (Supp #22) has a pending live
> validation path. Architecture A Phase 2 standalone supplement is still owed (unchanged from prior
> notes).

**Last updated (prior):** 2026-06-07 (covering the 375/376 directional-governance arc: consequence-gated directional routing reduced to practice and shipped, sign demoted to diagnostic-only — Supplement #23. The future-patent-relevant item flagged in the 2026-06-04 note below has now been BUILT with a proof case and documented.)

> **Build-state note (2026-06-02):** the build has since advanced through the full 372 integrity chain (evaluator-identity auditability, budget prevention/observability, cross-stage fallback visibility, disagreement-citation surfacing), validated live on two clean 3-real-model runs — see `CAM_Current_State.md`. **No new patent claims arose from that work.** It is reduction-to-practice / strengthened auditability of EXISTING claims, plus n=1-contract characterization findings (kept DIRECTIONAL and deliberately OUT of the patent record). The patent contributions below are unchanged. One *future* patent-relevant item was identified but NOT built and NOT proven necessary: boundary-fragile / conditional-compound-risk (instability metadata propagated as conditional candidate status) — write a supplement IF and WHEN it is built and a proof case exists, not before.
>
> **Build-state note (2026-06-04, Steps 373–375):** build advanced through Overview redesign, the absence-polarity sign-error fix (374Z), the Pass-2 integrity tripwire (375C), the Client Impact block (375G), and a deep directional-instability investigation (375-R / 375D / 375D-2 / 375H). **No new patent claims arose; the patent contributions below are unchanged.** These are (a) RTP / strengthened auditability of EXISTING claims, and (b) VALIDATION EVIDENCE that established doctrine is necessary — specifically, live measurement showed the directional synthesis path collapses verification-strength into legal severity (`3-0→HIGH→Risk`), which is exactly the failure 15b's six-concept ontology predicts when two concepts are conflated; and frozen-input replay showed evaluator disagreement is intrinsic and not removable by re-prompting/batching, which supports (does not extend) the preserve-disagreement claim. All quantitative findings are n=1-contract, kept DIRECTIONAL and OUT of the patent record. TWO *future* patent-relevant items identified but NOT built and NOT proven — write supplements only IF/WHEN built with a proof case: (1) the four-output directional governance redesign (directional_verdict / verification_strength / materiality / action — separating verification support from legal materiality at the directional decomposition path; design doc at build_log/375E_architecture_doc.md, routing policy NOT yet locked); (2) one-sidedness as an INDEPENDENT contract-position property (arising from missing protections OR present hostile language OR disproportionate remedies OR cross-clause interaction) rather than a subtype of coverage gap — currently a code-confirmed but n=1 schema-recall finding (375H), explicitly NOT yet a contribution. See `CAM_Current_State.md` for full detail.
>
> **Build-state note (2026-06-07, the 375/376 directional arc closed + shipped):** future-item (1) above — the directional governance redesign separating verification support from consequence at the directional decomposition path — has now been BUILT, validated with a proof case (fb6529 LP-24), and shipped to main (`8bd4267`; companion auditability fix `ba26ed8`). It is documented in **Supplement #23 (2026-06-07)**: consequence-gated directional routing with directional sign demoted to a diagnostic-only output that cannot move an action bucket. The routing policy IS now locked (P2'' as shipped), superseding the "routing policy NOT yet locked" caveat in the 06-04 note. Item (2) (one-sidedness as an independent contract-position property, 375H) remains code-confirmed but NOT yet a contribution — the present-but-one-sided coverage-bypass schema repair (375H-C) is not built. DEF-001 (consequence-reasoning persistence) is auditability strengthening of Supplement #23, not a separate claim. All quantitative findings remain n=1/n=2-contract, DIRECTIONAL, OUT of the patent record except as limited example context.

---

## Standing Protocol

**When a new patent insight is documented:**
1. Write a full supplement (`Patent_Supplement_YYYY_MM_DD*.md`) as always
2. Update this file (`Patent_Current_State.md`) in the same session:
   - Add the contribution to the Contribution Map under the appropriate topic
   - Add the supplement to the Supplement Index
   - Add any new patent sentences to the Patent Sentences section
   - Add any new canonical examples to the Canonical Examples Inventory
   - Update any architectural descriptions that changed

These two files are always updated together. The supplement is the full
record; this file is the index and orientation. Neither replaces the other.

---

## CAM in One Paragraph

CAM (Constrained Assertion Method) is a framework for governing **when**
AI systems are allowed to assert conclusions. The patent's central claim
is not "use multiple models" or "preserve disagreement" in isolation —
it is the integrated architecture that governs assertion behavior using
structured evidentiary constraints, multi-evaluator consensus thresholds,
explicit abstention pathways, and full audit reconstructability. CAM
operates at five granularities (per-assertion, per-LP, per-element,
per-document, across time) and produces output classified by lawyer
action type (Risk / Improvement / Review Needed / Addressed). The lease
domain is the first validation instance; the architecture is general.

---

## The Architecture

### Two Orthogonal Governance Layers

**Run-time governance** (within a single analysis):
- Vote count across evaluators
- Verdict distance (ordinal semantic distance between disagreeing verdicts)
- Use-specific consequence (use-aware materiality)
- → Two outputs: **confidence** + **review priority** (orthogonal)

**Temporal governance** (across time):
- Drift from validated baselines
- Evaluator behavior change
- Variance pattern shift
- → Two outputs: **calibration confidence** + **calibration alerts**

### The Three-Layer Directional Governance Architecture (Supplement #24, 2026-06-12)

The directional analysis pipeline decomposes into three distinct
governance layers, each answering a different question. They must not
collapse back into one undifferentiated "is this risky?" decision.

- **Layer 1 — Axis discipline (what gets asked).** Closed-form directional
  questions across four domain-general axes (proportionality;
  obligation-without-remedy; conditional-protection; unilateral-control)
  replace freeform "is this one-sided?" prompts. Reduced to practice in the
  closed-form prototype (Steps 389–391). Decisive discrimination evidence:
  LP-11 freeform 10/10 → closed-form 0/5 (the scalpel proof).
- **Layer 2 — Trace auditor (whether the answer is valid).** A light
  FEVER-style trace-compliance auditor that invalidates traces relying on
  unstated/hypothetical assumptions (UNSUPPORTED_INFERENCE /
  HIDDEN_ASSUMPTION) and preserves specific-and-cited traces. Checks
  reasoning VALIDITY only; forbidden from judging materiality. Designed and
  paper-validated against real Step 391 traces; NOT built.
- **Layer 3 — Materiality / routing (whether valid answers matter).**
  Decides whether a validly-reasoned finding routes to Risk, Review Needed,
  or Improvement, and whether a lone valid-but-low-materiality trace forces
  a candidate. Needs a lawyer-panel calibration input (disagreement-spread
  measurement, never an oracle). Open; blocks DEF-002.

Pipeline order: evaluator produces a closed-form axis answer → auditor
checks trace validity → invalid traces discarded/marked → valid traces
proceed to materiality/routing → lone valid minority traces preserved but
may route to Review Needed/Improvement rather than Risk. The auditor SITS
BEFORE routing. This is reduction-to-practice + refinement of the §7
"Optional Auditor Capability" of the generalized-framework Technical
Overview, demonstrated across four domains (FEVER/GPQA/SciFact/ContractNLI)
with measured precision/recall tradeoffs. See Guardrail #17.

### Run-Time Governance Operates At Every Layer of Decomposition

The three-dimensional governance described above is not specific to
LP-level merge — it applies independently at every layer where the
analyzed object decomposes into independent sub-criteria evaluated by
multiple evaluators. At present, two layers are specified and fully
reduced to practice:

- **LP layer:** Three evaluators each produce one verdict per LP across
  a six-rung coverage ordinal. Ordinal verdict distance is computed
  across evaluator pairs for every LP. Stage 5f applies a confidence
  cap derived from the distance × consequence matrix. Two independent
  governance signals: verdict distance (epistemic, tenant-agnostic) and
  LP consequence (use-aware, per-run). These are orthogonal — distance
  caps the confidence ceiling; consequence governs review priority
  escalation. Architecture A Phase 2 reduced LP-layer verdict distance
  to practice in Steps 351–352 (`lease_verdict_distance.py`,
  `verdict_distance` field written to every LP in `pipeline_results.json`,
  `NOT_ASSESSED_SENTINEL` for LPs that skip Stage 305). Stage 5f shipped
  same steps as an inline confidence-capping pass in `lease_adapter.py`.

- **Element layer:** Three evaluators each produce one verdict per
  element within an LP across a four-rung element ordinal (Present /
  Implicit Present / Review Needed / Missing). The element layer adds
  a propagation rule: element-level dispute on a rubric-critical element
  routes the parent LP to Review Needed regardless of LP-level majority.
  All four phases are fully reduced to practice as of 2026-05-18–21:
  Phase 1 (Disputed verdict in merge output) — Steps 349/349b/349c,
  2026-05-18. Phase 2 (212-element criticality annotations via derivation
  algorithm) — Step 355, 2026-05-20. Phase 3 (`dispute_signal`
  propagation: element-Disputed-on-critical → LP-level `review_needed`,
  `coverage_state_baseline` preserved) — Step 356, 2026-05-20. Phase 4
  (amber `◈ Disputed` chip on sidebar cards with disputed elements) —
  Step 358, 2026-05-21.

Distance thresholds and distribution gates are calibrated per layer to
the semantic ladder applicable at that layer.

### Output Classification — The Action-Type Doctrine

**This is load-bearing.** The bucket tells the lawyer **what to do**.
Confidence tells the lawyer **how strongly CAM supports the underlying
assessment**. Those are not the same thing.

| Bucket | Lawyer action | Confidence relationship |
|---|---|---|
| **Risk** | negotiate / protect / push back | may be high-confidence or low-confidence, but consequence warrants protective action |
| **Improvement** | clarify / tighten | protection likely exists; drafting could be cleaner |
| **Review Needed** | inspect manually | CAM cannot safely classify the action category |
| **Addressed** | no action | no meaningful concern surfaced |

#### Canonical formulation

> Risk, Improvement, Review Needed, and Addressed are action-type
> categories, not confidence levels.
>
> **Risk** means the recommended lawyer action is to negotiate, push back,
> or protect the client against substantive exposure. A Risk finding may
> have high or low confidence; confidence is displayed separately.
>
> **Improvement** means substantive protection is believed to exist, but
> the drafting could be clarified or tightened.
>
> **Review Needed** means CAM cannot safely determine the correct action
> category and the lawyer should inspect manually.
>
> **Addressed** means no meaningful action is recommended.
>
> Confidence and review priority remain separate governed outputs. Low
> confidence does not automatically imply high review priority, and high
> confidence does not automatically imply high severity. Consequence
> governs escalation independently of epistemic certainty.

#### What this rules out

- ❌ "Risk = we're confident there's a problem." This collapses bucket
  and confidence into one axis. A `potentially_unenforceable` clause may
  be Risk because the consequence warrants protection, even though CAM
  is not confident the clause actually fails.
- ❌ "Improvement = low-severity Risk." Improvement is a different
  action type, not a softer Risk. Substantive protection is believed to
  exist; the work is drafting.
- ❌ "Review Needed = low-confidence finding." Review Needed is
  specifically where CAM cannot determine the action type. A finding
  can be low-confidence and still confidently Risk (negotiate it) or
  confidently Improvement (tighten it).
- ❌ "Disputed elements should route to Risk." A Disputed element on a
  critical rubric criterion means CAM cannot safely determine the action
  category for the parent LP — that's Review Needed by definition
  (Supplement #21 Section 2.5). Phase 3 is fully reduced to practice
  as of Step 356 (2026-05-20): `elements_disputed_critical > 0` now
  routes the parent LP to `coverage_state = review_needed` automatically,
  with `coverage_state_baseline` preserved for audit.

#### Action-Type Clarification (added 2026-05-18)

Risk, Improvement, Review Needed, and Addressed are action-type
categories, not confidence levels and not leverage predictions. A Risk
finding means the appropriate lawyer action is protective: negotiate,
push back, preserve rights, request a revision, or consciously accept
the exposure. This includes coverage gaps, compound risks, and
directional mismatches, even though those subtypes may call for
different legal strategies and may carry different levels of negotiating
leverage.

Improvement is not a softened Risk category and must not be used as a
padded cell for uncomfortable or uncertain findings. A finding routes to
Improvement only when substantive protection is believed to exist and
the recommended action is drafting clarification, tightening, or making
an implicit protection more explicit. If CAM is uncertain whether
protection exists, or if the consequence of the contested reading is
material, the finding remains Risk or Review Needed according to the
governance rules.

Review Needed means CAM cannot safely determine the correct action
category and the lawyer should inspect manually. Addressed means no
meaningful action is recommended. Confidence and review priority remain
separate governed outputs: confidence controls how strongly CAM may
assert the underlying assessment, while consequence and action type
govern escalation.

#### Risk subtypes (UI-level structural distinction)

Risk is a single action-type bucket, but findings within Risk vary in
the underlying form of exposure they describe. CAM surfaces these as
sub-buckets in the sidebar to preserve the structural distinction
without splintering the doctrine:

- **Coverage Gap** (RISK → GAPS / COVERAGE): protection is absent; the
  recommended action is to add the missing protection.
- **Compound Risk** (RISK → COMPOUND): exposure emerges from the
  interaction of multiple provisions; the recommended action is to
  address the cross-provision interaction rather than any single clause.
- **Directional Imbalance** (RISK → DIRECTIONAL): protection exists but
  is structurally tilted against the perspective party; the recommended
  action is to rebalance the existing clause, or consciously accept the
  imbalance where leverage does not permit revision.

All three classify as Risk because the lawyer action is protective in
each case. They differ in the form of protective action and typically in
negotiating leverage. The framework does not classify by leverage —
leverage is not a CAM-level property — but it preserves subtype so the
UI can present the structural difference without conflating action with
fixability.

#### Single source of truth for action-type classification (Step 350)

After Step 350 (2026-05-18, `d7ae297`), the Coverage Snapshot on the
Overview tab routes through the same `classifyFindingType()` function
that the sidebar uses. The two surfaces tell the same story by
construction, not by coincidence. A future widget added to the Overview
tab should also use this classifier rather than reinvent bucketing
rules — that's the only way to keep the action-type doctrine consistent
across the product surface.

#### Closing

This is the doctrine established by Supplement 2026-05-15-c
("Risk vs Improvement as action-type categories") and Supplement
2026-05-15-b (confidence and review priority as orthogonal governed
outputs), refined 2026-05-18 to make the "padded cell" guardrail
explicit and to articulate Risk subtypes without subdividing the
action-type ontology. It is enforced in production code (Step 347 series
shipped the bucket architecture; Step 348 corrected `coverage_state ===
'review_needed'` to route to the Review Needed bucket regardless of
severity; Steps 349/349b/349c shipped Supplement #21 Phase 1
end-to-end — backend Disputed verdict, amber UI badge, and inline
`3 Evaluators` access path preserving the minority evaluator's
reasoning in every Disputed row; Step 350 unified the Coverage Snapshot
on the Overview tab with the sidebar's action-type taxonomy).

### The Semantic Verdict Ladder (Stage 305)

Six verdicts form an ordered ladder, not equal categories:

```
explicitly_present     rank 0  ← strongest coverage claim
implicitly_present     rank 1  ← inferred within LP
covered_in_other_LP    rank 2  ← cross-reference coverage
covered_by_default_law rank 2  ← background law applies
unclear                rank 3  ← evaluator cannot determine
                       (rank 4 deliberately unoccupied — see below)
missing                rank 5  ← confidently absent
```

Verdict distance table (ordinal):
- explicit↔implicit = 1 (minor — mechanism ambiguity)
- implicit↔unclear = 2 (moderate)
- unclear↔missing = 2 (moderate)
- **implicit↔missing = 4 (severe)**
- **explicit↔missing = 5 (severe — epistemic rupture)**

The gap at rank 4 is **intentional and load-bearing**. `missing` is a
confident negative claim, not "very unclear." The gap preserves
`unclear↔missing = 2` (moderate) while `implicit↔missing = 4` (severe).
Without the gap, `implicit↔missing` would be 3 — understating the
severity of an evaluator confidently claiming a provision is absent when
another confidently claims it is covered by inference.

**IP↔MI distance is 4, not 3.** An earlier version of the Appendix A
table in `build_log/351_chat_instruction.md` listed it as 3; the code
(`lease_verdict_distance.py`) was correct throughout. Corrected in
`build_log/351b_chat_instruction.md` and this document (2026-05-21).

The Phase 1 distance gate (shipped Step 349) fires when active per-element
verdicts span both presence-verdicts and `missing` — i.e. the most distant
ordinal pair. The merged verdict is recorded as `disputed` rather than
the majority winner. Adjacent disagreements (e.g. `explicitly_present` vs
`implicitly_present`) keep their majority resolution with confidence
modulation.

### Five Granularities of Governed Assertion

| Granularity | Where | What it governs |
|---|---|---|
| Per-assertion | Mode A deviation pipeline | Individual contract deviation findings |
| Per-LP | Stage 5c/5d coverage + verdict distance | Whether each LP issue area is addressed; confidence cap from distance × consequence |
| Per-element | Stage 305 within LPs | 212 elements across 32 LPs, citation required; criticality-gated dispute propagation |
| Per-document | Stage 7 synthesis | Cross-provision compound and directional findings |
| Across time | Calibration governance | Stability of all of the above against baselines |

---

## Contribution Map (by Topic, Not Date)

Use this to find which supplement to read for deep-dives. All supplements
are in `Docs/Patent_Supplement_2026_MM_DD*.md`.

### Foundation & Reduction-to-Practice
- **Chunked multi-pass extraction; non-standard provision discovery** — 03-22
- **Coverage & Gaps layer (Phase 5); schema-driven domain knowledge** — 04-14
- **Human benchmark validation; deterministic schema extension** — 04-19
- **Mode C single-document analysis as configuration-as-mode** — 04-24
- **Within-domain task generality; 558-type cross-contract taxonomy** — 04-28

### Compositional Governance
- **Cross-provision conflict detection (CR-01, CR-04, CR-09)** — 05-03
- **Jurisdiction-aware escalation (NY rules)** — 05-03
- **Compositional sequenced adapter engines (T-10-NY worked example)** — 05-03
- **Per-LP extraction routing knobs; misroute guard** — 05-04
- **Three-layer perspective-aware governance architecture** — 05-04
- **Use-archetype layer (third declared-external-context dimension)** — 05-04-b
- **Three-axis compositional governance** — 05-04-b

### Multi-Evaluator Architecture
- **Pattern 2 variance test (3/4/0 → Stage 5d gating)** — 05-04-b
- **Step 303 multi-evaluator merge (assert_strong/assert_weak/abstain/rejected)** — 05-05
- **Variance acceptance test (5 runs proving stable governance)** — 05-05
- **Cross-pipeline symmetry (Mode A and Mode C both demonstrate Claim 7)** — 05-05
- **Step 304a chain iteration with degrade-to-archetype-only** — 05-05-b
- **Framework self-validation pattern at three layers** — 05-05-b

### Per-Element Architecture
- **Detector boundary preservation (Steps 305a/b/c)** — 05-10
- **Step 305 full expansion (212 elements × 32 LPs)** — 05-12
- **Citation-or-it-didn't-happen rule** — 05-12
- **Cross-LP text injection (zero additional API calls)** — 05-12
- **§21.9 canonical example (3/3 distinction non-disturbance ≠ cure right)** — 05-13
- **Evaluator agreement patterns as evidence quality signal** — 05-13

### Document-Level Synthesis
- **Stage 7 cross-provision synthesis (Q1/Q2/Q3 questions)** — 05-13-b
- **Directional mismatch detection (LP-27, Beitel, 3/3 unanimous)** — 05-13-b
- **Five-pattern compound risk taxonomy; two-pass architecture** — 05-13-c
- **Four 3/3 unanimous compound risk findings on Beitel** — 05-13-c
- **Consequence-gated directional routing; sign demoted to diagnostic-only; agreement is not harm** — 06-07
- **Confidence-uncertainty vs consequence-uncertainty (refines Guardrail #9)** — 06-07
- **Detecting and demoting a degraded governance signal as a governance property** — 06-07

### Cross-Domain Auditor & Three-Layer Directional Governance (Supplement #24, 2026-06-12)
- **Auditor as a recurring cross-domain CAM mechanism (FEVER/GPQA/SciFact/ContractNLI), increasing sophistication** — 06-12
- **Measured precision/recall tradeoff of the governance layer; documented over-withhold failure (RULE-SF-002; ContractNLI [OK]→[WH])** — 06-12
- **Three-layer directional architecture: axis discipline / trace auditor / materiality-routing** — 06-12
- **Light trace-compliance auditor checks reasoning VALIDITY, not legal MATERIALITY; sits before routing** — 06-12
- **Refined minority doctrine: lone evaluator survives if its TRACE is valid, not because it produced a finding** — 06-12
- **Lease porting constraint: port the LIGHT auditor; do NOT port heavy withhold/elimination (over-withhold = unforgivable in legal review)** — 06-12
- **Reduction-to-practice + refinement of §7 Optional Auditor Capability (generalized-framework Technical Overview)** — 06-12

### Risk + Use-Aware
- **Coverage state ≠ risk level (Risk Map derivation rules)** — 05-14
- **Compound confidence capping (min of evaluator + weakest LP)** — 05-14
- **LP-27 capping (no Atlas compound finding reaches Verified)** — 05-14
- **Stage 5e: use-aware provision impact assessment** — 05-14
- **The A/C principle (same gap, different materiality by tenant use)** — 05-14
- **Stage 5e operational validation; Step 345 extended to review_needed** — 05-15

### Conceptual Architecture
- **Ordinal verdict distance (six-rung semantic ladder)** — 05-15-b
- **Three-dimensional run-time governance** — 05-15-b
- **Minority never silenced; confidence ≠ review priority** — 05-15-b
- **Risk vs Improvement as action-type categories** — 05-15-c
- **Four epistemic states (Risk / Improvement / Review Needed / Addressed)** — 05-15-c
- **Two Improvement pathways with operational importance gate** — 05-15-c
- **Default-law reliance as provenance, not Improvement** — 05-15-c
- **Temporal governance / calibration drift** — 05-15-d
- **Four-way distinction: Variance / Drift / Regression / Evolution** — 05-15-d
- **Drift becomes itself a governance signal** — 05-15-d
- **Action-type clarification: Risk subtypes; Improvement is not a padded cell** — 05-18
- **Single classifier source of truth across UI surfaces (Step 350 RTP)** — 05-18

### Element-Level Merge Governance (Phases 1–4 fully reduced to practice 2026-05-18–21)
- **Element-level verdict distance + distribution gates on per-element merge** — 05-17 (Phase 1 shipped Step 349)
- **`Disputed` as a structured merge output distinct from majority winner** — 05-17 (Phase 1 shipped Steps 349/349b)
- **Element criticality derivation algorithm (supplementary/important/critical from schema fields)** — 05-17 spec; **✅ Phase 2 RTP Step 355, 2026-05-20**
- **212-element criticality annotations applied to schema v2.2.0** — **✅ Phase 2 RTP Step 355, 2026-05-20**
- **`dispute_signal` propagation from element layer to LP layer** — 05-17 spec; **✅ Phase 3 RTP Step 356, 2026-05-20**
- **`coverage_state_baseline` preserved separately from Phase 3 override** — **✅ Phase 3 RTP Step 356, 2026-05-20**
- **`◈ Disputed` amber chip on sidebar cards with disputed elements** — 05-17 spec; **✅ Phase 4 RTP Step 358, 2026-05-21**
- **Three-dimensional governance operates per-layer (LP and element)** — 05-17
- **Minority evaluator reasoning preserved in-place at the element row** — 05-17 (shipped Step 349c)
- **LP-14 Rent Abatement Force Majeure canonical example** — 05-17 (validated end-to-end 2026-05-18)

### LP-Level Verdict Distance (Architecture A Phase 2, RTP 2026-05-19)
- **`lease_verdict_distance.py` module: distance computation at LP layer** — Steps 351–352
- **Six-rung ordinal ladder with deliberate gap at rank 4** — Steps 351–352 (corrected table in 351b)
- **`verdict_distance` field written to every LP in `pipeline_results.json`** — Steps 351–352
- **Stage 5f: confidence cap from distance × consequence matrix** — Steps 351–352
- **`NOT_ASSESSED_SENTINEL`: governance signal for LPs that skip Stage 305** — Steps 351–352
- **Two independent governance signals: verdict distance (epistemic) + LP consequence (use-aware)** — Steps 351–352

### Deliberate Non-Deliberation (Supplement #22, 2026-05-21)
- **Architectural decision: no deliberation rounds in document-interpretation domains** — 05-21
- **Distinction from fact-retrieval domains (where ground-truth exists and disagreement is noise)** — 05-21
- **Conformity pressure in LLMs: deliberation manufactures consensus that masks genuine ambiguity** — 05-21
- **Targeted citation check for distance-5 only (described and deferred)** — 05-21

---

## Critical Guardrails

These principles emerged through development and must be preserved in
any implementation. Do not allow them to soften over time.

1. **The minority evaluator is never silenced.** Their verdict and
   reasoning are always preserved in the audit trail regardless of
   majority outcomes. Only confidence and review priority are modulated.
   This guarantee applies at every decomposition layer — confirmed
   end-to-end at the element layer 2026-05-18 with Step 349c restoring
   the inline `3 Evaluators` expand on Disputed rows. (Refined by
   Guardrail #18: the audit-trail preservation is unconditional, but
   FORCING a downstream candidate requires the minority's trace to pass
   the validity gate.)

2. **Citation or it didn't happen.** Even majority consensus cannot
   produce an assertion of presence without a valid citation. This
   constraint overrides voting.

3. **An Improvement is not a low-severity risk.** It is a drafting-quality
   opportunity where substantive protection is already believed to exist.
   Allowing this distinction to soften collapses the ontology.

4. **Calibration governance detects, surfaces, alerts — never auto-heals.**
   No auto-retraining, no auto-mutation of thresholds, no auto-rewriting
   of prompts. Human decides.

5. **`cam/core/` epistemic logic has never been modified since Phase 1
   extraction (2026-02-13).** All extensions are adapter-layer. This is
   the foundation of the domain-agnostic applicability argument.

6. **Missing is never gray.** Gray means not applicable. Missing means
   absent but applicable. Collapsing the two suppresses genuine coverage gaps.

7. **Coverage state ≠ risk level.** A covered provision can be RED on
   the Risk Map (canonical example: LP-22 in Atlas).

8. **Maximally-distant element-level dissent is never resolved by majority
   vote.** When per-element evaluator verdicts split on a substantively
   distant ordinal pair (canonical example: Present vs Missing), the merged
   element label is `Disputed`, not the majority winner. The framework
   refuses to assert a single substantive verdict when the underlying
   disagreement spans non-adjacent verdict states. Enforced in production
   code as of Step 349 (2026-05-18).

9. **The bucket tells the lawyer what to do; confidence tells the lawyer
   how strongly CAM supports the assessment.** These are separate axes
   and must not be collapsed. Risk is an action category (negotiate /
   protect), not a confidence statement. Review Needed is the category
   for findings CAM cannot safely classify, not the category for
   low-confidence findings. A `potentially_unenforceable` clause can be
   Risk with low confidence; a `partial_review` clause can be Improvement
   with high confidence. Any phrasing — in docs, in UI, in prompts —
   that defines Risk as "CAM is confident there is a problem" is wrong
   and must be corrected. The bucket is action-type. Period.

10. **Improvement is not a padded cell.** Do not classify a finding as
    Improvement merely because it is ambiguous, low-confidence,
    low-leverage, or awkward to present as Risk. A finding routes to
    Improvement only when substantive protection is believed to exist
    and the recommended action is drafting clarification or tightening.
    Where CAM is uncertain whether protection exists, or where the
    consequence of the contested reading is material, the finding
    remains Risk or Review Needed. This guardrail prevents the slow
    laundering of difficult findings into a softer bucket — a
    particularly insidious failure mode because it preserves the
    appearance of taxonomy while corrupting it from inside.

11. **Risk subtypes are presentation, not classification.** Coverage
    Gap, Compound Risk, and Directional Imbalance are all Risk. The
    framework surfaces the subtype in the sidebar so the UI can carry
    structural information without subdividing the action-type ontology.
    Leverage, negotiability, and "fixability" are not CAM-level
    properties — they are downstream of the lawyer's judgment and the
    deal's context. The framework does not classify by leverage; it
    classifies by recommended protective action.

12. **Single classifier source of truth.** All UI surfaces that
    categorize findings into action-type buckets must route through
    `classifyFindingType()`. As of Step 350 (2026-05-18) the Coverage
    Snapshot on the Overview tab and the sidebar both use this
    classifier — they tell the same story by construction. A future
    widget that reinvents bucketing rules will silently drift from the
    doctrine; this guardrail prevents that.

13. **Disagreement is signal in document-interpretation domains.**
    CAM does not implement deliberation rounds. In fact-retrieval
    domains, evaluator disagreement is noise obscuring a ground-truth
    answer; deliberation helps convergence and is appropriate. In
    document-interpretation domains, evaluator disagreement reflects
    genuine interpretive ambiguity in the text — collapsing it through
    deliberation would manufacture consensus that masks real risk.
    CAM governs on disagreement rather than resolving it.

14. **Verdict distance is tenant-agnostic; consequence is use-aware.
    Do not conflate.** Distance caps the confidence ceiling; consequence
    governs review priority escalation. These are two separate lookup
    tables producing two orthogonal outputs. Collapsing them destroys
    the orthogonality guarantee.

15. **Agreement on direction is not agreement on harm; directional sign
    does not route.** At the directional decomposition path, evaluator
    agreement count is verification support, not severity, and directional
    sign (which party a clause disfavors) is a diagnostic-only output that
    cannot promote a finding to Risk or demote it to Review Needed.
    Directional findings route to action-type buckets by assessed
    use-consequence, materiality, consequence provenance, and mismatch
    support — never by vote count or sign. Sign was demoted because it was
    measured to be perspective-coupled (it encoded the run's perspective
    parameter, not clause balance); reintroducing it as a router requires a
    separate repair-and-validation step. Demoting a degraded governance
    signal — while continuing to compute and surface it for audit — is
    itself a governance property, not a weakening of the framework.
    (Supplement #23, 2026-06-07; shipped `8bd4267`.)

16. **Confidence-uncertainty and consequence-uncertainty route
    differently; this refines Guardrail #9, it does not contradict it.**
    Guardrail #9 establishes that a finding can be Risk with low
    confidence — uncertainty about whether the contested reading is
    *correct* does not bar Risk, because protective action is warranted
    when the consequence-if-true is clear. That is *confidence*
    uncertainty. Separately, when a finding's existence is confirmed but
    its *consequence to the client* is genuinely contingent on facts
    outside the document (*consequence* uncertainty), the correct lawyer
    action is itself indeterminate and the finding routes to Review
    Needed. The unifying rule is unchanged: the bucket is determined by
    which lawyer action is correct. Confidence-uncertain-but-
    consequence-clear stays Risk; consequence-genuinely-uncertain routes
    Review Needed. Do not collapse the two axes of uncertainty. Canonical
    example: fb6529 LP-24 (Supplement #23, 2026-06-07).

17. **The three directional governance layers must not collapse into one
    "is this risky?" decision.** Layer 1 (axis discipline) decides WHAT
    gets asked — closed-form directional questions. Layer 2 (trace auditor)
    decides whether the ANSWER IS VALID — whether the reasoning is specific
    and cited or smuggles an unstated assumption. Layer 3 (materiality /
    routing) decides whether VALID ANSWERS MATTER — Risk vs Review Needed
    vs Improvement. The auditor SITS BEFORE routing and is structurally
    FORBIDDEN from judging materiality; it must never be asked to compensate
    for an unasked question (an axis-completeness gap is a Layer-1 problem,
    not an auditor problem). Collapsing the layers reproduces the original
    "is this one-sided? → yes → Risk" wish-list failure. (Supplement #24,
    2026-06-12; Layer 1 RTP Steps 389–391; Layer 2 designed + paper-
    validated, not built; Layer 3 open, blocks DEF-002.)

18. **A lone evaluator survives if its trace is VALID, not because it
    produced a finding.** This refines Guardrail #1, it does not contradict
    it. The minority's verdict and reasoning are preserved in the audit
    trail UNCONDITIONALLY (Guardrail #1 unchanged). But for a lone
    evaluator's finding to FORCE a downstream candidate, its reasoning
    trace must pass the Layer-2 validity gate — specific, cited, free of
    smuggled assumptions. A lone evaluator with a sound cited trace survives
    (LP-27, where Eval-C dissents); a lone evaluator with an unsupported
    "such as ... may not be met" trace does not force a candidate (LP-15 at
    Step 390). Valid minority traces are preserved as SIGNAL but do NOT
    automatically force Risk — materiality and agreement govern the bucket.
    The minority is protected when it is WELL-REASONED, not merely when it
    is PRESENT. The auditor does not silence by headcount; it checks the
    minority's reasoning. (Supplement #24, 2026-06-12.)

---

## Patent Sentences (Most Quotable)

### From 2026-06-12 — Cross-Domain Auditor; Three-Layer Directional Governance (Supplement #24)

> "CAM employs an independent auditor that validates reasoning-trace
> compliance against a declared domain standard, capable of invalidating
> findings even under evaluator consensus. This capability is reduced to
> practice across four independent domains with increasing sophistication —
> standalone process audit (FEVER), adversarial falsification of unanimous
> answers (GPQA), rule-library and conviction testing (SciFact), and
> model-diversified auditing with a quantified precision/recall tradeoff
> (ContractNLI) — establishing the auditor as a recurring cross-domain
> governance mechanism rather than a single-domain feature."

> "The auditor's recall cost is measured, not hand-waved: in the heavier
> domain instances the governance layer is shown to withhold findings that
> were correct, and that withholding rate is recorded alongside the
> precision gain. CAM therefore governs the precision/recall tradeoff with
> measurement, rather than blindly maximizing precision — and in a
> legal-review instance deliberately ports only the light trace-compliance
> auditor, because withholding a correct risk finding is a more costly error
> than surfacing a spurious one."

> "CAM's directional analysis decomposes into three independent governance
> layers: axis discipline determines which closed-form questions are asked;
> an independent trace auditor determines whether an evaluator's answer is
> validly reasoned; and materiality routing determines whether a
> validly-reasoned finding warrants protective action. The auditor sits
> before routing and is forbidden from judging materiality. Collapsing these
> three layers into a single 'is this risky?' decision destroys the
> architecture."

> "A lone evaluator's finding survives because its reasoning trace is valid —
> specific, cited, and free of smuggled assumptions — not because it produced
> a finding or is prominent in the output. This refines the
> minority-never-silenced guarantee: the minority is preserved in the audit
> trail unconditionally, but it forces a downstream candidate only when its
> trace passes the validity gate. The minority is protected when it is
> well-reasoned, not merely when it is present."

> "A single finding can migrate between governance layers: when an
> over-firing evaluator's reasoning is tightened from a hypothetical category
> to specific cited textual facts, the same finding moves from an
> auditor-validity problem the auditor can kill, to a materiality dispute
> among valid traces the auditor must, by design, refuse to adjudicate. The
> auditor is validated for its purpose precisely because it correctly
> declines to perform the materiality layer's function."

### From 2026-05-21 — Deliberate Non-Deliberation (Supplement #22)

> "CAM does not implement deliberation rounds because in document
> interpretation domains, evaluator disagreement has positive signal value
> — it reflects the interpretive ambiguity of the underlying text. This
> is architecturally distinct from fact-retrieval domains where a ground-
> truth answer exists and disagreement is noise. CAM governs on disagreement
> rather than resolving it."

> "The non-deliberation principle rests on the recognition that large
> language models exhibit conformity pressure when shown peer reasoning:
> a minority evaluator presented with majority verdicts will disproportionately
> revise toward the majority regardless of whether the revision reflects
> genuine reconsideration. Deliberation therefore risks manufacturing
> consensus that masks genuine ambiguity."

> "A targeted citation check — distinct from full deliberation — is described
> for the maximum-distance case (explicitly_present vs missing) only. In this
> case, the minority evaluator is shown only the textual citation identified
> by majority evaluators, without their reasoning or verdict, and asked to
> re-evaluate. If the minority revises, the correction is recorded with
> reduced confidence ceiling. If the minority maintains its verdict, the
> original Phase 3 governance applies. This preserves the distinction between
> reading errors (correctable) and interpretive conflict (signal to preserve)."

> "The architectural choice to preserve evaluator disagreement rather than
> resolve it through deliberation is itself a governance decision: CAM asserts
> that in ambiguous-document domains, the risk of suppressing a genuine
> interpretive signal is greater than the risk of surfacing a spurious one,
> because the cost of missing a real ambiguity in a commercial lease
> (potential loss of rights, unexpected liability) exceeds the cost of
> flagging a resolved one (one additional lawyer review)."

### From 2026-05-19–21 — Architecture A Phase 2 + Supplement #21 Phases 2–4 (Steps 351–358)

> "CAM computes ordinal verdict distance at the LP layer independently of
> the element layer: three evaluators' LP-level verdicts are compared
> pairwise across the six-rung coverage ordinal, and the maximum pairwise
> distance governs the confidence ceiling for that LP's assertion. Distance
> and use-specific consequence are orthogonal governance signals — distance
> caps the ceiling; consequence governs escalation. Collapsing them would
> destroy the orthogonality guarantee."

> "The deliberate gap at ordinal rank 4 — with `unclear` at rank 3 and
> `missing` at rank 5 — is architecturally intentional. `missing` is a
> confident negative claim, not 'very unclear.' The gap ensures that
> `implicit↔missing` distance is 4 (severe) rather than 3, correctly
> representing the epistemic severity of one evaluator confidently finding
> coverage and another confidently finding absence."

> "Stage 5f applies a confidence cap derived from a distance × consequence
> matrix. Severe distance (4 or 5) hard-caps confidence to a low ceiling
> regardless of consequence level. Moderate distance differentiates by
> consequence. The cap is applied after all other evaluator signals, as
> the final output gate before LP results reach the UI."

> "CAM uses element criticality as a propagation gate: when any element
> with criticality `critical` carries a `Disputed` merged verdict, the
> parent LP's `coverage_state` is overridden to `review_needed` regardless
> of LP-level majority. The pre-override majority reading is preserved as
> `coverage_state_baseline` for audit. Elements with criticality `important`
> or `supplementary` do not trigger LP-level propagation."

> "Element criticality is derived deterministically from the schema's
> existing fields — `absence_severity`, `must_be_explicit`,
> `default_law_covers`, `implicit_coverage_acceptable` — via a
> hierarchical classification algorithm with a defined override mechanism
> for elements requiring manual assignment. Criticality is a schema-level
> annotation that travel through every analysis run without requiring
> model inference."

> "The dispute propagation rule produces a distinct governance output
> from LP-level consensus. An LP can have all three evaluators agree on
> LP-level coverage while still being routed to Review Needed because
> element-level evaluation produced a Disputed verdict on a critical
> element. These are independent governance paths operating at different
> decomposition layers."

### From 2026-05-18 (Action-Type Clarification + Step 350)

> "Risk is defined by recommended protective action, not by leverage.
> Coverage gaps, compound risks, and directional mismatches may all
> classify as Risk, but the UI preserves their subtype because they
> imply different lawyer actions: add missing protection, address
> cross-provision exposure, or rebalance/accept one-sided terms."

> "Improvement is not a softened Risk category and must not be used as
> a padded cell for uncomfortable or uncertain findings. A finding
> routes to Improvement only when substantive protection is believed
> to exist and the recommended action is drafting clarification,
> tightening, or making an implicit protection more explicit. Where
> CAM is uncertain whether protection exists, or where the consequence
> of the contested reading is material, the finding remains Risk or
> Review Needed."

> "All UI surfaces that present action-type categorization route through
> a single classifier function, ensuring that the Coverage Snapshot,
> the sidebar, and any future bucket-displaying widget tell the same
> story by construction. The action-type doctrine is enforced at the
> classifier layer, not by parallel duplicate logic per surface."

### From 2026-05-17 (Supplement #21 spec, Phase 1 RTP 2026-05-18)

> "CAM treats element-level evaluator dissent as a governed signal that
> propagates to the assertion bucket: when verdicts split on a substantively
> distant ordinal pair (e.g., Present vs Missing), the merged status is
> recorded as Disputed rather than resolved by majority vote. The minority
> evaluator's reasoning is preserved verbatim, and the parent assertion is
> classified as Review Needed regardless of majority verdict."

> "CAM distinguishes the assertion 'this provision is covered' from the
> meta-assertion 'CAM is confident enough to make this assertion.' Where
> evaluators disagree on the underlying coverage classification with
> maximal ordinal distance, the second assertion fails even if the first
> achieves majority — and the framework reports this gap rather than
> smoothing it."

> "The ordinal verdict distance framework operates at every layer of CAM's
> coverage decomposition: per-LP between independent LP-level evaluators,
> and per-element between independent element-level evaluators within a
> single LP. The framework specifies distance thresholds and distribution
> gates at each layer independently, calibrated to the semantic ladder
> applicable at that layer."

> "CAM uses element criticality as a propagation gate: a Disputed element
> on a rubric-critical or rubric-important criterion propagates a dispute
> signal to the parent LP's bucket classifier; a Disputed element on a
> rubric-informational criterion does not."

> "Where current art merges evaluator outputs by majority vote and either
> surfaces or suppresses the resulting disagreement as metadata, CAM treats
> the act of merging itself as a governed operation. The framework refuses
> to produce a single substantive merged verdict when the underlying
> disagreement spans non-adjacent verdict states, and instead produces a
> structured Disputed label whose treatment in downstream classification
> is itself specified by the framework."

> "CAM's output buckets are action-type categories, not confidence
> levels. The Risk bucket designates findings for which the recommended
> lawyer action is to negotiate, push back, or protect — regardless of
> whether CAM is highly confident the exposure is real or only that the
> consequence is high enough that protective action is warranted under
> uncertainty. The framework displays confidence as a separate governed
> output."

### From 2026-05-15 contributions

> "CAM treats evaluator disagreement as an ordinal governance signal whose
> severity depends on semantic distance between verdict states, not merely
> evaluator count."

> "Adjacent verdict disagreement often reflects mechanism ambiguity; distant
> verdict disagreement reflects substantive epistemic conflict."

> "CAM governs assertion confidence as a function of evaluator consensus
> count, semantic distance between disagreeing verdict states, and
> use-specific consequence of the contested reading. The minority evaluator
> is preserved in the audit trail regardless — only assertion confidence
> and review priority are modulated."

> "Confidence and review priority are separate governed outputs. Low
> confidence does not imply high review priority; consequence governs
> escalation independently of epistemic certainty."

> "An Improvement is not a low-severity risk. It is a drafting-quality
> opportunity where substantive protection is already believed to exist."

> "CAM distinguishes substantive risk findings from drafting-improvement
> findings by evaluating semantic distance between structured evaluator
> verdicts together with use-specific consequence."

> "CAM governs not only assertion confidence within a single evaluation
> run, but also temporal stability of evaluator behavior across validated
> baselines. Divergence from historical governance patterns becomes itself
> a governed signal."

### From earlier contributions

> "Citation or it didn't happen: if 2/3 evaluators say 'present' but
> neither provides a valid citation, the merged verdict drops to 'unclear'
> regardless of majority. This is a constraint on assertion, not a vote."
*(2026-05-12)*

> "Most multi-evaluator architectures collapse disagreement into a single
> answer. CAM's four-outcome merge preserves the disagreement structure:
> 1/3 escalations are recorded as abstentions with full dissenter reasoning,
> distinct from 0/3 silent rejection."
*(2026-05-05)*

> "CAM's value proposition is not 'smart answers.' It is governed assertion
> behavior. If the governance behavior drifts, the entire epistemic
> contract changes."
*(2026-05-15-d)*

> "What started as a lease analyzer is now structured legal cognition
> modeling with governed assertion behavior at both the analysis level
> and the system level. The lease domain is the first validation domain,
> not the invention."
*(2026-05-15-d)*

---

## Canonical Examples Inventory

These examples recur across supplements and form the strongest narrative
anchors for prosecution:

| Example | Demonstrates | Primary Supplement |
|---------|--------------|---------------------|
| §21.9 non-disturbance vs. mortgagee cure right | 3/3 distinction between superficially related legal concepts | 05-13 |
| Nadine benchmark §21.9 curation-vs-coverage | CAM preserves; humans curate | 04-19 |
| Pattern 2 variance (3/4/0 → stable governance) | Multi-evaluator resolves single-evaluator wobble | 05-05 |
| LP-27 directionality (Beitel) | Document-level directional mismatch, 3/3 unanimous | 05-13-b |
| LP-27+LP-14+LP-24 compound risk (Beitel) | Cross-provision compound finding | 05-13-b |
| Four CRX findings on Beitel (CRX-01–04) | Two-pass compound risk, 3/3 unanimous each | 05-13-c |
| LP-22 covered but RED (Atlas) | Coverage state ≠ risk level | 05-14 |
| LP-05 favorable for logistics (Atlas) | Use-aware impact assessment | 05-14 / 05-15 |
| T-10-NY compositional chain | Stage 5b → Stage 5c composition | 05-03 |
| Step 247 deterministic extension | Schema change → 20/24 corpus flip, T-16 correctly retained | 04-19 |
| **LP-14 Rent Abatement Force Majeure (Atlas)** | **Element-level 2v1 dissent on maximally-distant verdict pair (Present vs Missing). Spec written 2026-05-17; Phase 1 RTP shipped 2026-05-18 (Steps 349/349b/349c). Production behavior validated end-to-end: amber `Disputed (2v1)` label in Coverage & Gaps STATUS column; `3 Evaluators` expand opens to show all three verdicts and reasoning verbatim. The minority evaluator (Claude — Missing) is preserved side-by-side with the majority (Grok, GPT-5.5 — Present Sec 24.1). Merge refuses to pick a winner.** | **05-17** |
| **`potentially_unenforceable` as Risk under uncertainty** | **Action-type doctrine: Risk bucket includes findings where CAM is not confident the underlying issue is real, but the consequence is high enough that protective action is warranted under uncertainty. Rules out "Risk = confident problem" framing.** | **05-15-c / 05-17** |
| **Directional Imbalance as Risk subtype, not Improvement** | **Action-type clarification: a directional mismatch (e.g., asymmetric default remedies favoring landlord) is Risk because the recommended action is protective (negotiate / rebalance / consciously accept) — regardless of whether the imbalance is industry-standard and negotiation leverage is low. The framework refuses to launder lower-leverage findings into Improvement.** | **05-18** |
| **Coverage Snapshot 5-bucket reconciliation (Step 350)** | **Single-classifier source of truth: the Overview tab Coverage Snapshot now routes through the same `classifyFindingType()` that the sidebar uses. Pre-Step 350, the Snapshot used legacy 3-bucket labels (covered / need attention / not applicable) that summed to 7 of 32 LPs — silently dropping 25 LPs. Post-Step 350, the Snapshot shows five action-type buckets that sum to 32. Validated 2026-05-18: 4 Risk + 4 Review Needed + 19 Improvement + 2 Addressed + 3 N/A = 32, with Risk count matching sidebar's RISK → GAPS / COVERAGE sub-bucket exactly.** | **05-18** |
| **LP-14, LP-22, LP-27, LP-28 Phase 3 propagation (Atlas Meridian)** | **`elements_disputed_critical > 0` → `coverage_state = review_needed`. All four had baseline `partial` overridden. LP-09 had 3 disputed elements but Phase 3 did NOT fire (all were `important` tier — correct). Validated 2026-05-21 (job `lease_review_20260521_010256_e43bad`).** | **05-17 / Steps 355–358** |
| **fb6529 LP-24 (no insurance-proceeds disposition on early termination)** | **Directional governance: a 3-0 unanimous tenant-disfavored mismatch that the old sign/vote path routed to Risk, and consequence-gated routing routes to Review Needed because use-consequence is genuinely `context_dependent` — grounded in the lease's cross-provision structure (LP-10 §8.4 tenant-improvement framework; unresolved improvement disposition at termination; LP-25 §14.1 trade-fixture protection; LP-24 silence on insurance proceeds for that investment). Demonstrates: agreement on direction is not agreement on harm; confidence-uncertainty vs consequence-uncertainty; consequence grounded in document text not reconstructed; Risk→Review Needed as a correct, documented, intentional demotion.** | **06-07** |
| **LP-11 Rent Acceleration scalpel proof (Atlas)** | **Layer-1 axis discipline DISCRIMINATES rather than rewording a wish-list: a finding the freeform system flagged 10/10 runs is rejected by the closed-form axes 0/5 runs. Proves the closed-form mechanism is a scalpel, not a differently-worded wish-list generator.** | **06-12** |
| **LP-15 390→391 layer migration (Atlas)** | **The boundary between the trace auditor and materiality routing. At Step 390, Eval-A's LP-15 trace relied on a hypothetical category ("such as ... may not be met") — a light auditor INVALIDATES it (Layer 2 kill). At Step 391, after tightening, Eval-A's trace cites specific facts ($10M/$5M umbrella; negligence/gross-negligence indemnity; conditional §10.3 subrogation waiver) — the auditor PRESERVES it by design. The finding MIGRATED from a Layer-2 auditor-validity problem to a Layer-3 materiality problem (B/C judge the cited asymmetries immaterial = genuine 1-vs-2 materiality split). Demonstrates: the three layers are distinct; the auditor checks validity not materiality; LP-15 is a materiality/routing case, possibly mislabeled as a control.** | **06-12** |
| **LP-27 same-risk Axis-1 with Eval-C dissent (Atlas)** | **Refined minority doctrine: Eval-A and Eval-B cite a specific same-risk parallel (§17.3 landlord self-help cure vs §5.1 tenant security-deposit setoff for the same triggering event); Eval-C returns all-no. The lone-ish valid cited trace survives the auditor by REASONING QUALITY, not headcount. The minority is protected when well-reasoned, not merely when present.** | **06-12** |
| **FEVER / GPQA / SciFact / ContractNLI auditor lineage** | **The auditor as a recurring cross-domain CAM mechanism with increasing sophistication and a measured precision/recall tradeoff (ContractNLI CCA 80.4%→83.2%, Withheld 17→33) plus a documented over-withhold failure (SciFact RULE-SF-002 suppressing correct NEIs). Establishes domain-generality of the auditor and the measured recall cost of heavy governance — the warning against porting heavy withhold/elimination machinery into legal review.** | **06-12** |

---

## Supplement Index (Chronological)

For deep-dives. Each supplement is preserved verbatim on disk and in
project knowledge.

| # | Date | Title |
|---|------|-------|
| 1 | 2026-03-22 | Chunked Extraction, Non-Standard Provision Discovery, Coverage Audit |
| 2 | 2026-04-14 | Coverage & Gaps Layer (Phase 5) |
| 3 | 2026-04-19 | Human-Reviewer Benchmark Evidence |
| 4 | 2026-04-24 | Mode C — Configuration-as-Mode |
| 5 | 2026-04-28 | Architectural Generality, Cross-Contract Taxonomy, Cross-Model Audit |
| 6 | 2026-05-03 | Compositional Governance, Conflict Detection, Jurisdiction-Aware Strictness |
| 7 | 2026-05-04 | Extractor Calibration, Three-Layer Perspective Architecture |
| 8 | 2026-05-04-b | Pattern 2 Variance Test, Use-Archetype Layer |
| 9 | 2026-05-05 | Multi-Evaluator Stage 5d Call 2 with Deterministic Merge |
| 10 | 2026-05-05-b | Chain Iteration with Degrade-to-Archetype-Only |
| 11 | 2026-05-10 | Detector Boundary Preservation |
| 12 | 2026-05-12 | Per-Element Multi-Evaluator Coverage, Cross-LP Injection |
| 13 | 2026-05-13 | Cross-LP Governed Evaluation, Evaluator Agreement as Evidence Quality |
| 14 | 2026-05-13-b | Stage 7 Cross-Provision Synthesis |
| 15 | 2026-05-13-c | Stage 7 Two-Pass Compound Risk Milestone Validation |
| 16 | 2026-05-14 | Risk Map, Compound Confidence Capping, Stage 5e |
| 17 | 2026-05-15 | Stage 5e Operational Validation; Coverage Certainty ≠ Risk Consequence |
| 18 | 2026-05-15-b | Ordinal Verdict Distance; Three-Dimensional Governance |
| 19 | 2026-05-15-c | Risk vs Improvement Action-Type Ontology |
| 20 | 2026-05-15-d | Temporal Governance / Calibration Drift |
| **21** | **2026-05-17** | **Element-Level Merge Governance; Per-Element Verdict Distance and Dispute Propagation — Phases 1–4 fully RTP 2026-05-18–21 (Steps 349/349b/349c/355/356/358)** |
| **22** | **2026-05-21** | **Deliberate Non-Deliberation; Targeted Citation Check (Deferred)** |
| **23** | **2026-06-07** | **Consequence-Gated Directional Routing; Sign Demoted to Diagnostic-Only; Confidence-Uncertainty vs Consequence-Uncertainty (shipped `8bd4267` / `ba26ed8`)** |
| **24** | **2026-06-12** | **Cross-Domain Auditor / Governance Lineage; Three-Layer Directional Governance Architecture; Refined Minority Doctrine (RTP + refinement of §7 Optional Auditor Capability; FEVER/GPQA/SciFact/ContractNLI; Layer 2 designed + paper-validated not built; Layer 3 open)** |
| **25** | **2026-06-13** | **Architecture A Phase 2: Verdict Distance and Confidence Capping at the LP Layer (formalizes Steps 351/351b/352 RTP; second instantiation of Supplement #18 ordinal-distance governance; deliberate-gap rank scale; consequence-coupled Stage 5f cap; NOT_ASSESSED sentinel)** |

The action-type clarification of 2026-05-18 (including the Step 350
single-classifier source-of-truth point) is not currently a separate
supplement — it lives in this document under Output Classification →
Action-Type Clarification, with formal patent sentences captured under
Patent Sentences. If it merits independent supplement status later
(e.g., for prosecution structure), it can be lifted out without doctrine
change.

Architecture A Phase 2 (LP-layer verdict distance, Stage 5f confidence
capping, Steps 351–352) is documented in `build_log/351_chat_instruction.md`
and `build_log/351b_chat_instruction.md` (correction), and now has a
standalone patent supplement: `Patent_Supplement_2026_06_13.md` (written
2026-06-13). Patent sentences also appear in this document under
"Architecture A Phase 2 + Supplement #21 Phases 2–4."

---

## Specification vs Reduction-to-Practice Status

Most supplements document architecture that is already implemented and
running in production. Supplement #21 was **specification-only** at the
time of writing (2026-05-17 evening) and graduated to **Phase 1 reduced
to practice** on 2026-05-18, with Phases 2–4 completing by 2026-05-21.

Supplement #24 (2026-06-12) is a MIXED status: the cross-domain auditor
evidence (FEVER/GPQA/SciFact/ContractNLI) is REDUCED TO PRACTICE benchmark
work; Layer 1 (closed-form axis discipline) is REDUCED TO PRACTICE in the
lease prototype (Steps 389–391, local commits `0ff3cc2`/`c709b74`, not
pushed); Layer 2 (light trace auditor) is DESIGNED + PAPER-VALIDATED
against real Step 391 traces but NOT BUILT; Layer 3 (materiality/routing)
is OPEN and blocks DEF-002. The §8.3 absence-trap axis-completeness
question is paper/design work, separate from the auditor.

### Phase 1 RTP Timeline (Supplement #21 + companion work)

The full sequence from operational discovery to end-to-end validation
unfolded in under 24 hours, and is on the record in the build_log:

| Date / Time (approx) | Event | Artifact |
|---|---|---|
| 2026-05-17 ~3 PM | Operational discovery on LP-14 Force Majeure rent-abatement element. 2v1 Claude(Missing) vs GPT+Grok(Present). Merge picked majority, contradicting CAM's "withhold when uncertain" doctrine. | Conversation transcript, screenshot |
| 2026-05-17 evening | `Patent_Supplement_2026_05_17.md` written. Full specification of element-level merge governance: distance gate, criticality gate, LP-bucket propagation, action-type doctrinal basis. **Specification-only**, no code change. 5 patent sentences. | `Docs/Patent_Supplement_2026_05_17.md` |
| 2026-05-18 ~9 AM | **Step 349** — `merge_element_verdicts()` returns `verdict: "disputed"` when active verdicts span presence and missing. `derive_lp_state()` treats disputed as missing (conservative). `assess_coverage_305()` tracks `elements_disputed`. | git `e40f41b` |
| 2026-05-18 ~10 AM | **Step 349b** — UI surface: amber `Disputed (2v1)` badge in Coverage & Gaps STATUS column and CAM Audit Trail merged column. | git `f609fe0` |
| 2026-05-18 ~10:30 AM | **Step 349c** — UI fix: restored `3 Evaluators` expand button on Disputed rows after Step 349b inadvertently suppressed it. Minority-never-silenced guarantee restored at the bucket layer. | git `f004bd8` |
| 2026-05-18 ~11 AM | **Fresh validation run** `lease_review_20260518_132711_bb9440`. Gate fired on 18 disputed elements across 13 LPs (10% of total elements ≈ meaningful signal volume). LP-14 canonical case validated end-to-end. LP-05 and LP-20 flipped from covered/partial to missing due to conservative treatment (correct per spec). | `pipeline_results.json` |
| 2026-05-18 afternoon | **Action-type clarification** added to Output Classification section: directionals stay Risk; Improvement is not a padded cell; Risk subtypes are presentation, not classification. New Guardrails 10 and 11. | This document |
| 2026-05-18 afternoon | **Step 350** — Coverage Snapshot reconciliation. `renderModeCAISummaryBar()` rewritten to tally all 32 LPs via `classifyFindingType()` into five action-type buckets. Replaces 3-bucket legacy widget that was silently dropping ~25 LPs. New Guardrail 12 (single classifier source of truth) added. | git `d7ae297` |
| 2026-05-18 afternoon | **Snapshot validation** — 4 Risk + 4 Review Needed + 19 Improvement + 2 Addressed + 3 N/A = 32. Snapshot Risk count reconciles with sidebar's RISK → GAPS / COVERAGE sub-bucket exactly. | UI screenshot |
| 2026-05-20 | **Step 355** — Phase 2 RTP: 212-element criticality annotations applied to schema v2.2.0. Derivation algorithm from schema fields; 19 manual overrides. | git |
| 2026-05-20 | **Step 356** — Phase 3 RTP: `dispute_signal` propagation wired. `elements_disputed_critical > 0` → `coverage_state = review_needed`; `coverage_state_baseline` preserved. | git |
| 2026-05-21 | **Step 358** — Phase 4 RTP: `◈ Disputed` amber chip on sidebar cards with `elements_disputed > 0`. | git `86517ae` |
| 2026-05-21 | **Validation** (job `lease_review_20260521_010256_e43bad`, Atlas Meridian): Phase 3 fired on LP-14, LP-22, LP-27, LP-28. LP-09 (3 disputed elements, all `important`) correctly did not fire. | `pipeline_results.json` |

### Why this sequencing matters for prosecution

The supplement was written **before** any code change, and committed to
disk on 2026-05-17. The first reduction-to-practice commit (`e40f41b`)
landed the following morning. This establishes:

1. The governance behavior is a **designed property** of the framework,
   not an accident of post-hoc cleanup.
2. The architectural commitment was made **in advance** of implementation
   and articulated as a multi-phase plan. All four phases shipped within
   four days of the original specification — a tight spec-to-RTP cadence
   that demonstrates the framework was architecturally ready to absorb
   the addition.
3. The 24-hour spec-to-Phase-1-RTP cadence demonstrates that the framework
   was ready to absorb the architectural addition — `cam/core/` was not
   touched; the element-merge logic lives in the adapter layer; the
   action-type doctrine made the bucket routing implications obvious.
   This is evidence of the framework's compositional structure, not just
   a feature add.
4. Step 350 (same-day as Phase 1) demonstrates that the action-type
   doctrine, once codified, propagates consistently to other surfaces
   of the product without re-litigation — the Overview tab's Coverage
   Snapshot adopted the sidebar's classifier wholesale rather than
   re-implementing a parallel bucket scheme. Single source of truth,
   by design.

### Operative status by phase

| Phase | Description | Status |
|---|---|---|
| 1 | `disputed` as merge output + UI surface + minority-access affordance | ✅ RTP 2026-05-18 (Steps 349/349b/349c) |
| 2 | Element criticality annotations on LP rubrics (212 elements, derivation algorithm) | ✅ RTP 2026-05-20 (Step 355) |
| 3 | `dispute_signal` propagation: element-Disputed-on-critical → LP-level Review Needed; `coverage_state_baseline` preserved | ✅ RTP 2026-05-20 (Step 356) |
| 4 | `◈ Disputed` amber chip on sidebar cards with disputed elements | ✅ RTP 2026-05-21 (Step 358) |

### Companion RTP from same week

Step 348 (2026-05-17, post-Supplement-21) shipped the bucket-routing
correction for `coverage_state === 'review_needed'`: items in this state
now route to the Review Needed bucket regardless of severity, per
Guardrail #9. The Review Needed bucket went from 0 items to 4 on the
Atlas validation run (and 4–5 on subsequent fresh runs), confirming
the bucket is now operative as the action-type doctrine requires.

Step 350 (2026-05-18) shipped the Coverage Snapshot reconciliation,
moving the Overview tab onto the same action-type classifier the sidebar
uses. Validation: five badges sum to 32; Snapshot Risk count exactly
matches the sidebar's RISK → GAPS / COVERAGE sub-bucket count.

Steps 351–352 (2026-05-19) shipped Architecture A Phase 2: LP-layer
verdict distance computation (`lease_verdict_distance.py`), Stage 5f
confidence cap, and `verdict_distance` field written to every LP.
IP↔MI distance corrected to 4 in 351b (table error; code was correct).

---

## Pending Items

- **Patent non-provisional conversion** — ~$40K, 9-month window from
  provisional filing, decision pending
- **Joshua's next lease run** — no longer treated as a blocking dependency
  (the specific warehouse deal fell through 2026-05-17; future leases
  are still welcome external validators)
- **Architecture A Phase 2 standalone supplement** — ✅ WRITTEN
  2026-06-13 (`Patent_Supplement_2026_06_13.md`). Formalizes LP-layer
  verdict distance (Steps 351/351b/352) and Stage 5f confidence capping
  as the second reduced-to-practice instantiation of the Supplement #18
  ordinal-distance governance (element-layer counterpart is Supplement
  #21). One empirical item remains open and is noted honestly in the
  supplement: a live 32-LP real-API T-10 severity distribution (core
  logic validated synthetically + via Atlas regression).
- **Supplement #24 open layers** — Layer 2 (light trace-compliance
  auditor) is designed + paper-validated but NOT built; Layer 3
  (materiality/routing) is open and blocks DEF-002. The §8.3 absence-trap
  axis-completeness question (Layer 1) is paper/design work, separate from
  the auditor. Attorney question: is the existence/mechanism separation
  (Future Item A) and the three-layer auditor architecture each a distinct
  claimable contribution, and does building Layer 2 strengthen scope vs
  describing it as reduced-to-practice across four benchmark domains?
- **Stage 5d formalization** — Step 302 spec exists. Multi-model
  consensus (≥2/3) required before enabling. **ENABLED** as of Step 303
  (variance acceptance test passed 2026-05-04, 5 runs ±1 stable;
  `STAGE_5D_ENABLED = True` in `lease_use_aware_coverage.py`).
  Confirmed product-behavior note: if Stage 5d skips (generic or absent
  permitted-use clause), no use_profile is generated, Stage 5e-F runs
  keyless, and P2'' Rule 1a routes ALL directional findings to
  review_needed/consequence_not_assessed. A lease with a generic
  permitted-use clause produces zero directional Risk by construction.
  (DEF-008 doc correction, 2026-06-10)

---

*This document is meant to be the single fastest way to orient a new
AI chat to the full CAM patent state. If you need depth on any specific
contribution, jump to the supplement listed in the Contribution Map.
All supplements are preserved verbatim on disk and in project knowledge —
this document does not replace them, it indexes them.*
