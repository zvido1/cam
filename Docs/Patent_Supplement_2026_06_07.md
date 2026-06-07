# CAM Patent Supplement — June 7, 2026

**Purpose:** Documents the directional governance redesign — the recognition that evaluator agreement on the *direction* of a contract imbalance (which party a clause disfavors) is a verification-support signal, not a consequence-severity signal, and must not by itself determine whether CAM asserts Risk. Establishes consequence-gated directional routing: directional findings are routed to action-type buckets by assessed use-consequence, materiality, consequence provenance, and mismatch support — with directional sign demoted to a diagnostic-only output that cannot move an action bucket. Reduces to practice the "four-output directional governance redesign" that `Patent_Current_State.md` (build-state note, 2026-06-04) identified as future-patent-relevant and explicitly deferred until built with a proof case. That condition is now satisfied.

**Relationship to prior supplements:**
- `Patent_Supplement_2026_05_15b.md` introduces ordinal verdict distance and the principle that verification support and legal consequence are orthogonal governed outputs at the LP layer. This supplement establishes the same orthogonality at the **document-level directional decomposition path** (Stage 7 cross-provision synthesis), and identifies a specific failure mode in which the two axes had been collapsed.
- `Patent_Supplement_2026_05_17.md` (Supplement #21) establishes that three-dimensional governance operates "at every layer where the analyzed object decomposes into independent sub-criteria," and reconciles a new routing rule with the action-type doctrine rather than contradicting it (its Section 2.5). The directional routing rule introduced here is the same kind of move at the directional layer: a direct application of the action-type doctrine, reconciled in Section 4 below with Guardrail #9.
- `Patent_Supplement_2026_05_15c.md` introduces the four epistemic states (Risk / Improvement / Review Needed / Addressed) as action-type categories, not confidence levels. The routing in Section 3 is governed by that doctrine.
- `Patent_Supplement_2026_05_14.md` and `_05_15.md` introduce Stage 5e use-aware consequence assessment (the A/C principle: same gap, different materiality by tenant use). The consequence axis that governs directional routing here is the finding-scoped instantiation of that assessment.

**Architectural context:** Implemented in the Lease Analyzer adapter (`cam/adapters/lease_review/`). The shared epistemic core (`cam/core/`) is git-verifiably unchanged (Guardrail #5). The directional routing logic lives in a new adapter-layer module (`lease_p2pp_routing.py`); the Stage 7 synthesis fields that previously drove routing (`directionality`, vote-derived `severity`) are preserved for display and audit but are no longer read by the router. Reduced to practice and shipped to main (`8bd4267`, with the companion auditability fix `ba26ed8`) on 2026-06-07.

---

## 1. The Operational Discovery (the directional path collapsed verification into severity, on two axes)

### 1.1 The diagnosis

A deep directional-instability investigation (recorded across the 375 series in `CAM_Current_State.md`) established that the document-level directional synthesis path converted **evaluator agreement count directly into legal severity, and then into Risk routing**. A finding confirmed by all three evaluators (3-0) was mapped to HIGH severity and routed to Risk; the routing was driven by *how many evaluators confirmed the mismatch existed* and *which direction the mismatch pointed*, not by *how harmful the underlying term actually was* to this client.

This is a category error of exactly the kind the framework's six-concept ontology forbids: unanimity measures verification support, not consequence. It is the directional-path analogue of the LP-layer and element-layer principle already in the patent record — that verdict agreement and legal consequence are orthogonal and must not be collapsed.

The investigation surfaced a second, compounding problem specific to the directional path: the directional **sign** itself (which party a clause disfavors — `tenant_unprotected` vs `landlord_unprotected`) was *also* being set by verification mechanics rather than by clause content. On byte-identical input, the sign of findings flipped wholesale run-to-run, because the substantive direction was taken from the first evaluator that happened to confirm the mismatch, and which evaluator confirms first varies between runs. Across three distinct leases tested, the directional sign came back uniform within each run and tracked the **run's perspective parameter** (tenant-perspective run → findings uniformly `tenant_unprotected`; landlord-perspective run → uniformly `landlord_unprotected`), not the actual balance of each clause. The sign was perspective-coupled and non-discriminating.

### 1.2 Why this is the wrong output for CAM

Two independent signals — agreement count and directional sign — were each doing work they were not epistemically entitled to do. Agreement count was determining severity; sign was contributing to routing while encoding run perspective rather than clause balance. The result was a Risk classification that could be asserted on the strength of "three evaluators agree this leans against the tenant" without any governed determination that the leaning actually harms the tenant.

---

## 2. The Canonical Example (fb6529 LP-24)

The failure mode and its repair are both visible in a single finding from a tenant-perspective run of the Atlas Meridian warehouse lease (run `fb6529`), finding Dir-18, implicating LP-24 (Damage & Destruction).

**The finding (real and unambiguous):** All three evaluators independently confirmed a directional mismatch, exposed party = tenant, 3-0. The specific gap: the lease references insurance proceeds as a *condition* to the landlord's repair obligation (Section 13.1, "provided that insurance proceeds are sufficient") but contains no language on how those proceeds are disposed if the lease *terminates* early following casualty.

**Old routing (sign/vote path):** 3-0 confirmation + `tenant_unprotected` directionality → verified adverse → **Risk**. The consequence layer was not consulted. The classification rested entirely on agreement count and sign.

**New routing (consequence-gated):** The finding-scoped consequence assessment rated the use-consequence `context_dependent` — because whether this gap actually harms the tenant depends on a fact not contained in the casualty clause: whether the tenant has made capital improvements that would be left uncompensated. The finding routes to **Review Needed**, not Risk.

**Why `context_dependent` is the correct, grounded verdict (not a soft hedge):** The contingency is established by the lease document itself, across provisions:
- LP-10 Section 8.4 contemplates tenant improvements at the tenant's sole cost — establishing that tenant capital investment is a recognized contractual reality, not a hypothetical.
- LP-10 leaves the ownership/disposition of those improvements unresolved at termination.
- LP-25 Section 14.1 separately grants the tenant a claim to a separate award for trade fixtures in condemnation — demonstrating the lease *can* protect tenant-installed value in an analogous scenario.
- LP-24's casualty/termination path is silent on insurance proceeds for that same tenant investment.

So the harm is **not established as present** (it depends on whether this tenant invested and whether casualty-and-termination occurs), but the contingency is **real and lease-grounded**. The correct lawyer action is therefore neither "negotiate now" (Risk) nor "no action" — it is "inspect manually: confirm with the client whether they have improvement investment exposed." That is Review Needed by definition.

**The principle, in canonical form:**

> **Agreement on direction is not agreement on harm.** Unanimous evaluator agreement that a clause leans against a party establishes that a directional mismatch exists and which way it points; it does not establish that the mismatch harms the client. CAM routes directional findings to action-type buckets by assessed consequence, not by agreement count or directional sign.

---

## 3. The Specification

### 3.1 Five separated outputs at the directional decomposition path

The directional path produces governed outputs that are kept distinct rather than collapsed into a single "severity → Risk" mapping:

| Output | Meaning | Role in routing |
|---|---|---|
| **directional verification** (confirmation count / support) | How many evaluators confirmed the mismatch and how strongly | Verification support — NOT severity |
| **directional sign** | Which party the mismatch disfavors | **Diagnostic-only — does not route** |
| **use-consequence** | Whether the gap is harmful / beneficial / neutral / context-dependent for *this* client's use | Routing axis |
| **materiality** | How significant for this client's core operations (high / medium / low / not-applicable) | Routing axis |
| **recommended action** | The action-type bucket (Risk / Review Needed / Improvement / Addressed) | The governed output |

Consequence provenance (`consequence_source`: assessed / defaulted / absent / not-eligible) and mismatch support (adequate / weak / singleton / inadequate) are additional governing inputs to the recommended-action output.

### 3.2 Consequence-gated routing (the recommended-action rule)

The directional finding routes by strict precedence — provenance and support are checked first, so the framework never asserts an action category from unsupported or unassessed evidence:

```
1. Provenance/support guardrail (outranks all consequence labels):
   consequence not assessed   → Review Needed
   mismatch support inadequate → Review Needed
2. context_dependent consequence → Review Needed
3. harmful + high/medium materiality (assessed, adequately supported) → Risk
4. beneficial consequence → Improvement (favorable position)
5. neutral consequence → Improvement (no protective action) [locked convention]
6. harmful + low materiality → Improvement (low-materiality directional issue)
```

The Risk bucket is reached only by an **assessed, adequately-supported, harmful, materially-significant** consequence. Directional sign and verification count appear nowhere in the routing conditions.

### 3.3 Sign is demoted to a diagnostic-only output

Directional sign is computed and emitted on every finding — it may be displayed, audited, and measured — but it carries an explicit `routing_use = diagnostic_only` marker and **cannot promote a finding to Risk or demote a finding to Review Needed**. Reintroducing sign as a routing signal requires a separate repair-and-validation step demonstrating that sign is no longer perspective-coupled and carries independent clause-balance information.

### 3.4 Why demoting a signal *strengthens* the governance claim

This is the patent-relevant pivot. CAM is not "use every signal that sounds epistemic." CAM is "govern assertions on signals that are actually reliable, and preserve unreliable signals without pretending they are decisive." The framework detected that a governance input (directional sign) had stopped governing — that it had become perspective-coupled and non-discriminating — and refused to let it route, while continuing to compute and surface it for audit. The capacity to detect that a governance signal has degraded, and to demote it without discarding it, is itself a governance property: it is the system enforcing its own constraint that assertion rests only on reliable evidence.

---

## 4. Doctrinal Reconciliation — Consequence-Uncertainty vs Confidence-Uncertainty (refines Guardrail #9, does not contradict it)

Guardrail #9 and the action-type doctrine establish that **Risk can be a low-confidence finding**: a `potentially_unenforceable` clause may route to Risk even though CAM is not confident the clause actually fails, because the *consequence if it does fail* warrants protective action under uncertainty. A superficial reading of the directional routing above — where a *context_dependent* consequence routes *away* from Risk into Review Needed — appears to contradict this. It does not. The reconciliation rests on distinguishing two different axes of uncertainty:

- **Confidence uncertainty** is uncertainty about whether the contested reading is *correct* — whether the clause fails, whether the provision is truly absent. The consequence, *if* the adverse reading holds, is clear. Guardrail #9 governs this case: high consequence under confidence-uncertainty still routes to Risk, because protective action is warranted even though CAM is not sure the problem is real.

- **Consequence uncertainty** is uncertainty about whether the (confirmed) situation *harms this client at all* — the gap is established, but its consequence is genuinely contingent on facts outside the document. The action category itself is indeterminate: CAM cannot say whether the correct action is "negotiate" (Risk), "tighten drafting" (Improvement), or "no action" (Addressed), because that depends on a client fact CAM does not have.

LP-24 is the consequence-uncertainty case: the directional gap is confirmed 3-0 (no confidence uncertainty about its existence), but whether it harms the tenant depends on whether the tenant has exposed capital investment — a fact the lease frames but does not resolve. The action category is indeterminate, and the action-type doctrine assigns indeterminate-action-category findings to Review Needed.

The two cases are consistent under a single rule: **the bucket is determined by which lawyer action is correct.** When the action *would be* protective if a contested reading holds, that is Risk under uncertainty (Guardrail #9). When CAM cannot determine which action is correct because the consequence itself is genuinely contingent, that is Review Needed. Confidence-uncertain-but-consequence-clear stays Risk; consequence-genuinely-uncertain routes Review Needed. This refines Guardrail #9 by naming the axis it operates on, and adds the complementary case the directional path made visible.

This framing rules out two interpretations that would weaken the framework:
- "Route confirmed directional mismatches to Risk because three evaluators agree." This collapses verification support into severity — the exact category error Section 1 identifies. Agreement establishes the mismatch exists, not that it harms.
- "Route context_dependent findings to Improvement because the gap might not matter." This treats Improvement as a soft Risk and conceals the unresolved consequence question. Improvement means substantive protection is believed to exist and the action is drafting; a finding whose consequence is genuinely undetermined has no such belief established. It is Review Needed.

---

## 5. What the Framework Refuses To Do

CAM does not:
1. **Route a directional finding to Risk on agreement count.** Unanimous confirmation is verification support, not severity.
2. **Route a directional finding to Risk on directional sign.** Sign is diagnostic-only; a perspective-coupled signal cannot determine an action category.
3. **Assert an action category from unassessed consequence or inadequate support.** The provenance/support guardrail outranks all consequence labels — a favorable-looking value text cannot route to no-action when consequence was never assessed.
4. **Launder a consequence-uncertain finding into Improvement.** Genuinely undetermined consequence routes to Review Needed, not to a softer bucket.
5. **Discard a degraded governance signal silently.** Sign is demoted with an explicit diagnostic marker and remains in the audit trail; the degradation is detectable, not erased.

What CAM does:
1. Computes use-consequence, materiality, provenance, and support as the governing inputs to the directional action-type output.
2. Routes by consequence under strict provenance-first precedence.
3. Demotes directional sign to diagnostic-only and records `routing_use = diagnostic_only` on every directional finding.
4. Persists the consequence assessment's reasoning, confidence, and agreement alongside the verdict, so an `assessed` consequence is auditable rather than a bare stamp (companion auditability fix, Section 7).

---

## 6. Reduction to Practice

**Shipped to main 2026-06-07.** New adapter module `cam/adapters/lease_review/lease_p2pp_routing.py` (`classify_directional_p2pp`, `apply_p2pp_routing`), wired in `lease_adapter.py` after the finding-scoped consequence stage; the frontend classifier reads the consequence-gated bucket first. Six validation gates passed before push, including: a static audit confirming no routing path reads sign/directionality/agreement-count; a replay confirming the only behavioral change vs the prior path was the single LP-24 Risk→Review Needed transition (every other finding unchanged); a sign-inertness matrix confirming that mutating only the directional-sign fields leaves bucket and reason unchanged; and a consequence/provenance/support matrix confirming the provenance guardrail outranks every consequence label. The shared epistemic core was not modified.

The LP-24 transition was held for explicit verification before push: a three-column comparison (pre-existing production route / prior provisional policy / new route) established that the change was a genuine Risk→Review Needed demotion, and the consequence-uncertainty was then grounded in the lease text (Section 2) rather than accepted on reconstructed reasoning. This spec-to-proof-to-push discipline is itself on the record in `build_log/376h_*.md`.

---

## 7. Companion Auditability Fix (not a separate claim)

A companion fix (committed `ba26ed8`) persists the consequence assessment's reasoning, confidence, and evaluator-agreement fields onto each directional finding. The consequence stage already computed these; the attach step had been dropping them before they reached the stored artifact. The fix carries them through, so a consequence labeled `assessed` is backed by inspectable reasoning rather than an unauditable stamp. This is **reduction-to-practice / strengthened auditability of the governance described here**, not an independent contribution: it makes the consequence-gated routing auditable, which is a property the routing claim already implies.

---

## 8. Scope Discipline

The mechanism described here is the patent contribution: the separation of verification support, directional sign, consequence, materiality, and recommended action into distinct governed outputs at the directional decomposition path, and consequence-gated routing with sign demoted to diagnostic-only. The empirical validation to date is limited (a small number of leases; consequence-axis generalization characterized on two distinct leases; one audited mechanism artifact on a landlord-perspective run). Consistent with the standing protocol, **these counts are directional characterization, not patent proof, and are not claimed as empirical generality.** LP-24 is offered as an illustrative proof case demonstrating the mechanism and its grounding, not as a statistical result. Cross-contract and cross-perspective breadth validation remains future work and is not claimed here.

---

## 9. Relationship to Existing Claims

This supplement does not propose new independent claims. It strengthens reduction-to-practice and disclosure for:
- **The verification-vs-consequence orthogonality** (Supplement 15b) — now instantiated at the directional decomposition path, completing the "operates at every layer of decomposition" disclosure (LP layer, element layer, and now document-level directional layer).
- **The action-type doctrine** (Supplement 15c; Guardrail #9) — refined by the confidence-uncertainty vs consequence-uncertainty distinction (Section 4), which names the axis Guardrail #9 operates on and adds the complementary Review Needed case.
- **Directional mismatch detection** (Supplement 13b, the original LP-27 directional finding) — the directional output is now governed by the same action-type discipline as coverage and compound findings, rather than routed by sign/vote.
- **Domain-agnostic applicability** — the verification-vs-consequence separation is layer-general and domain-general; the directional instantiation is one more layer, not a lease-specific heuristic.

---

## 10. Patent Sentences Established by This Supplement

1. *"Agreement on direction is not agreement on harm. Unanimous evaluator agreement that a clause leans against a party establishes that a directional mismatch exists and which way it points; it does not establish that the mismatch harms the client. CAM routes directional findings to action-type buckets by assessed consequence, not by agreement count or directional sign."*

2. *"At the directional decomposition path, CAM separates five governed outputs that prior art and CAM's own earlier implementation had collapsed: directional verification support, directional sign, use-consequence, materiality, and recommended action. Verification support measures how strongly evaluators confirm a mismatch; it is not severity. Directional sign indicates which party is disfavored; it is diagnostic-only and does not determine the action category."*

3. *"CAM detected that a governance input had ceased to govern — directional sign had become coupled to the run's perspective parameter rather than to clause balance — and demoted it to a diagnostic-only output that cannot promote a finding to Risk or demote it to Review Needed, while continuing to compute and surface it for audit. The capacity to detect a degraded governance signal and demote it without discarding it is itself a governance property."*

4. *"CAM distinguishes confidence-uncertainty from consequence-uncertainty. A finding whose contested reading is uncertain but whose consequence-if-true is clear may route to Risk under uncertainty, because protective action is warranted. A finding whose existence is confirmed but whose consequence to the client is genuinely contingent on facts outside the document routes to Review Needed, because the correct lawyer action is itself indeterminate. The bucket is determined by which action is correct, not by epistemic confidence in the underlying fact."*

5. *"Consequence-gated directional routing checks provenance and support before consequence: a finding whose consequence was never assessed, or whose mismatch support is inadequate, routes to Review Needed regardless of how favorable or adverse its value text appears. The framework refuses to assert an action category from unsupported or unassessed evidence."*

---

## 11. Canonical Example for the Inventory

**fb6529 LP-24 (No insurance-proceeds disposition on early termination).** A 3-0 unanimous directional mismatch (tenant-disfavored) that the prior sign/vote path routed to Risk, and that consequence-gated routing routes to Review Needed because the use-consequence is genuinely `context_dependent` — grounded in the lease's own cross-provision structure (LP-10 §8.4 tenant-improvement framework at tenant's sole cost; unresolved improvement disposition at termination; LP-25 §14.1 trade-fixture protection in condemnation; LP-24 silence on insurance proceeds for that investment). Demonstrates: (a) agreement on direction is not agreement on harm; (b) the confidence-uncertainty vs consequence-uncertainty distinction; (c) consequence grounded in document text rather than reconstructed; (d) the Risk→Review Needed demotion as a correct, intentional, documented behavioral change.

---

*End of supplement.*
