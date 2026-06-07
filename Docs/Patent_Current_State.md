# Patent Current State

**Purpose:** This is the orienting document for AI chats working on CAM.
Reading this gives you the full patent architecture without needing to
read all 20+ patent supplements. Parallels `CAM_Current_State.md`
(which orients to the build state); this orients to the patent state.

**Last updated:** 2026-06-07 (covering the 375/376 directional-governance arc: consequence-gated directional routing reduced to practice and shipped, sign demoted to diagnostic-only — Supplement #23. The future-patent-relevant item flagged in the 2026-06-04 note below has now been BUILT with a proof case and documented.)

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
   the inline `3 Evaluators` expand on Disputed rows.

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

---

## Patent Sentences (Most Quotable)

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

The action-type clarification of 2026-05-18 (including the Step 350
single-classifier source-of-truth point) is not currently a separate
supplement — it lives in this document under Output Classification →
Action-Type Clarification, with formal patent sentences captured under
Patent Sentences. If it merits independent supplement status later
(e.g., for prosecution structure), it can be lifted out without doctrine
change.

Architecture A Phase 2 (LP-layer verdict distance, Stage 5f confidence
capping, Steps 351–352) is documented in `build_log/351_chat_instruction.md`
and `build_log/351b_chat_instruction.md` (correction) but does not yet
have a standalone patent supplement. Patent sentences appear in this
document under "Architecture A Phase 2 + Supplement #21 Phases 2–4."
A standalone supplement should be written before the attorney conversation.

---

## Specification vs Reduction-to-Practice Status

Most supplements document architecture that is already implemented and
running in production. Supplement #21 was **specification-only** at the
time of writing (2026-05-17 evening) and graduated to **Phase 1 reduced
to practice** on 2026-05-18, with Phases 2–4 completing by 2026-05-21.

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
- **Architecture A Phase 2 standalone supplement** — LP-layer verdict
  distance (Steps 351–352) and Stage 5f confidence capping are reduced
  to practice but do not yet have a formal patent supplement. Patent
  sentences are captured in this document. Should be written before
  the attorney conversation.
- **Stage 5d formalization** — Step 302 spec exists. Multi-model
  consensus (≥2/3) required before enabling. Currently gated
  (`STAGE_5D_ENABLED = False`).

---

*This document is meant to be the single fastest way to orient a new
AI chat to the full CAM patent state. If you need depth on any specific
contribution, jump to the supplement listed in the Contribution Map.
All supplements are preserved verbatim on disk and in project knowledge —
this document does not replace them, it indexes them.*
