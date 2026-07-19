# Step 431A — Decision Document: Parameter Identity, Requirement Rule, and Uncertain-Applicability Behavior

**Author:** Chat instance
**Date:** 2026-07-19
**Type:** DECISION DOCUMENT — **RATIFIED 2026-07-19 by Tzvi.** Decision cells in §8 are filled. Not a Claude Code handoff. Authorizes no implementation.
**Ratified direction (one line):** Models judge meaning (via the §6 Selector Panel); code governs the judgment's grounding, completeness, and visibility. The parameter block becomes a consumer of governed panel output, not the authority on semantic identity. Next build = narrowly-scoped Step 431 governed evidence-selection spec (Path B).
**Blocks:** full Step 431 is now unblocked to draft against the ratified decisions below, under the hard scope fence in §9.
**Sources read this session (not from memory):** `build_log/430_gate_b_cross_lease.md`; `cam/adapters/lease_review/lease_parameter_block.py` (427/429 state); `build_log/423_evidence_assignment_architecture_spec.md` §5, §8, §9; `Docs/Patent_Supplement_2026_07_14.md` (Supplement #26) §1, §5, §7, §11.

---

## 0. The two statements that hold regardless of every choice below

**Ratified formulation (the division of labor):**

> Models judge meaning. Code verifies evidence grounding, trace integrity, declared completeness, and governance behavior. CAM exposes disagreement and uncertainty rather than representing semantic judgment as deterministic fact.

"Models propose, code verifies" remains literally true for span *location* (code resolves the quote against the hashed source). For *meaning* — charge basis, applicability, concept match — the correct formulation is **models judge; CAM governs the judgment.** Code never verifies meaning; it verifies the conditions under which a semantic judgment may be relied upon.

**Ratified warning (the boundary that must not be blurred):**

> Governed selection is the mechanism for determining concept relevance; it is not proof that the selected concept is semantically correct. Panel agreement raises confidence and makes the decision auditable, but shared semantic error remains possible. Parameter identity refinement and governed selection reduce concept-substitution risk; they do not eliminate it.

This preserves Supplement #26 §7's structural-vs-semantic verifiability boundary: CAM may claim source-traceable, complete, non-destructive evidence assignment; it may **not** claim perfect semantic selection. 430 is a worked example of the §7 gap, not a fix for it. Both statements are repeated in the §8 decision summary.

This is the guardrail against mistaking a cleaner ontology for semantic verification. 430 already demonstrated the failure it names: even a perfectly declared `base_rent` dependency was satisfied by a verified span containing no rent. A per-profile map and a charge-basis-typed parameter would not, by themselves, have caught it. Nothing in 431A closes semantic verifiability — Supplement #26 §7 states that boundary is OPEN, and it stays open after 431A.

*(This paragraph is repeated verbatim in §8, the decision summary.)*

---

## 1. The decision being made

431A settles three things, and only these three, for the **four existing parameters** (`tenant_share`, `building_share`, `rent_adjustment_pct`, `base_rent`) — nothing broader:

1. **Parameter identity** — is `tenant_share` one parameter, a structured parameter with a required charge-basis, or several parameters split by charge-basis? And what happens when the basis is combined or unclear?
2. **Requirement rule** — what establishes that a parameter is *required* for a given LP, and how is that determined (deterministically / by extraction state / by governed selection / a combination)?
3. **Uncertain-applicability behavior** — when it cannot be determined whether a parameter applies, what does the system do?

Once ratified, full Step 431 measures the right objects. Until ratified, Track 1 (value-presence) would be measuring against an ontology 430 has already shown to be underspecified, and any such measurement could be obsolete before it is finished.

---

## 2. Why Step 430 makes this decision necessary

430 ran the 427/429 parameter block through Gate B on Atreca (built-on) and Atlas (unseen), N=5 each. Verbatim results:

- **Atreca:** Gate B pass 5/5; all four parameters resolved to offset-stable verified spans each carrying its value.
- **Atlas:** Gate B degraded 5/5, failing only `(LP-07, building_share)` — and that miss is `absent_by_structure` (Atlas contains the string "Operating Expenses" **zero** times in 31,755 chars). Gate B correctly refused it. No `present_but_missed` on either lease; **429 did not regress.**

The finding that forces 431A is not the failure — it is the two Atlas parameters that **passed and were wrong**:

- `tenant_share` resolved 5/5, stably, to Atlas's `"Proportionate Share" shall mean 22.4%, representing the ratio of the rentable area...` — which Atlas §3.3 applies to **Real Estate Taxes and CAM Charges**, not an operating-expense split. Verified span, green gate, **wrong concept.**
- `base_rent` resolved 5/5, stably, to `"Base Rent" shall mean the annual rent payable as set forth in Section 3.1.` — a definitional stub with **no monetary value at all**; the real $18.50/rsf schedule sits ~3,200 chars away, uncaptured. Verified span, green gate, **no value.**

The `tenant_share` failure is the load-bearing one for 431A: it happened **because the parameter name does not say "of what."** `tenant_share` is silently doing four possible jobs — share of operating expenses, of CAM, of taxes, or a combined proportionate-share mechanism — and Atlas proved those are not interchangeable. A validity contract written against the current name would validate an underspecified ontology.

---

## 3. Locked constraints (not up for decision in 431A)

These are fixed; the three decisions below must respect them.

- **Gate B is not amended in 431A.** It stays keyed to declared dependency names + `span.verification_status` (427 design). Whatever validity mechanism the decisions imply lives *before* or *beside* Gate B, never inside it.
- **No lease-specific literals** in any gate or contract (427 doctrine; Supplement #26 §5: "the gate does not search for `45.79%`"). A per-parameter-*type* contract is permitted; a per-lease value is not.
- **Scope is the four existing parameters.** 431A does not open a general lease-parameter taxonomy. `commencement_date`, `term_length`, `premises_sqft`, etc. (named in the spec/supplement but not implemented) are out of scope.
- **No `cam/core/` change** (Guardrail #5). All of this is adapter-layer.
- **No wiring authorization.** 431A does not make wiring safe and does not authorize it. Wiring stays blocked behind Gates A–D on both leases (423 §8).
- **Semantic verifiability stays OPEN** (Supplement #26 §7; §0 above).

---

## 4. Question 1 — Parameter identity

**Does `tenant_share` remain a single parameter, become structured by charge-basis, or split into separate parameters by charge-basis? And what happens when the basis is combined or unclear?**

### Options

**1-A. Keep as-is (single flat `tenant_share`).**
No structural change; the name stays semantically overloaded.

**1-B. Structured parameter with a required `charge_basis` field.**
One parameter, but it carries a typed basis:
```
proportionate_share
  charge_basis: operating_expenses | CAM | taxes | combined | unclear
  value: <pct>
  span: <EvidenceSpan>
```
The dependency `LP-07 depends_on [tenant_share, building_share]` becomes something like `depends_on [share(basis=operating_expenses), ...]`.

**1-C. Split into separate named parameters by basis.**
`tenant_share_opex`, `tenant_share_cam`, `tenant_share_tax`, etc. — each its own name in `PARAMETER_TARGETS` and the dependency map.

**Sub-question (all options must answer):** what is recorded when a lease's share is explicitly *combined* (one percentage covering opex+CAM+taxes together, as many NNN leases write it) or *unclear* (a bare "Proportionate Share" with no stated basis, like Atlas)?

### Advantages

- **1-A:** zero code churn; smallest patent-description delta; keeps the four-name map the supplement already describes.
- **1-B:** captures the basis distinction 430 exposed *without* multiplying parameter names; `combined`/`unclear` are first-class values, so Atlas's bare 22.4% can be honestly recorded as `charge_basis=unclear` rather than silently accepted as opex share; one attachment site per LP unchanged.
- **1-C:** most explicit; each basis is independently requirable and independently measurable; a dependency map can demand `tenant_share_opex` for LP-07 and never be satisfied by a tax share.

### Failure modes

- **1-A:** does nothing about the 430 finding — the next lease with a differently-based share re-triggers the exact concept substitution. Rejected-looking, but listed honestly: it is the "do nothing to identity" baseline.
- **1-B:** the `unclear` value is a trap if downstream treats `unclear` as satisfying a dependency — it must not; `unclear` has to route to the same unsatisfied/Review-Needed path as absent, or 1-B silently reintroduces the Atlas pass. Also: who assigns `charge_basis`? If a model assigns it, that is a new semantic model output (a new surface for the same failure family, Supplement #26 §7) — this bleeds into Track 2 and must be named, not hidden.
- **1-C:** name multiplication — four parameters can become a dozen; the dependency map grows; and a lease that genuinely has one combined share now fails to satisfy any single-basis dependency unless a `combined` parameter also exists. Risk of the map becoming lease-shaped by the back door.

### Patent-description implications (flag only — not claim language)

- Supplement #26 §5 describes the dependency map with the **literal example** `LP-07 depends_on: [tenant_share, building_share]`, and §1/§11 name "Tenant's Share of Operating Expenses" as *the* canonical parameter-class example. The parameter *names* are therefore part of the described embodiment.
- **1-B and 1-C refine that embodiment; they do not contradict a claim.** The claimed mechanism (§5) is "declared-dependency completeness gating, keyed to declared dependencies not literals" — that survives any of the three options. Adding `charge_basis` makes the *example* more precise.
- **430 is arguably new reduction-to-practice evidence for §7's already-stated OPEN semantic boundary**, not a contradiction of the supplement. Framing 431A's outcome as "sharpening the described parameter embodiment + a worked example of the §7 semantic-verifiability gap" is likely the cleaner prosecution posture than presenting it as a correction — but **that framing is an attorney call, and the technical identity decision (1-A/B/C) comes first regardless.**
- Whichever option is chosen, a patent supplement is owed per the standing protocol (full supplement + `Patent_Current_State.md` update in the same session) — but only *after* the technical decision, and only if it changes the described embodiment (1-B/1-C do; 1-A does not).

---

## 5. Question 2 — Requirement rule

**What establishes that a parameter is *required* for an LP, and how is that determined?**

### Options

**2-A. Global dependency map (current state).**
One `DEPENDENCY_MAP` for every lease. LP-07 always requires the share parameter(s). *This is what produced the Atlas result* — LP-07 required `building_share`, Atlas has none, Gate B failed it as out-of-scope.

**2-B. Map keyed to document-type label.**
Separate maps for "warehouse" / "office" / "retail" / etc.

**2-C. Map keyed to versioned schema profile + demonstrated provision applicability** *(GPT's recommendation, and mine).*
A parameter is required for an LP when (i) the active versioned analysis/schema profile declares the dependency AND (ii) the provision is demonstrably applicable to *this* document (the LP is present/applicable, not `NOT_APPLICABLE`). The requirement is not read off the document's marketing label but off whether the machinery the parameter quantifies is actually present.

### Advantages

- **2-A:** simplest; one map to reason about; fully deterministic.
- **2-B:** crude but easy; "warehouse ⇒ don't require opex share" would have made Atlas pass cleanly.
- **2-C:** correct-by-construction — a warehouse lease that *does* carry opex machinery still gets the dependency required; an office lease that omits it doesn't. Ties requirement to the §9 `NOT_APPLICABLE` contract already in the spec (an LP that is `NOT_APPLICABLE` is exempt from Gate B for parameters it doesn't declare). Deterministic and auditable if applicability is deterministic.

### Failure modes

- **2-A:** every non-Atreca-shaped lease is either forced to satisfy Atreca's dependencies or fails Gate B as "out of scope" — the map never transfers. This is the wiring-blocker #1 from 430 §6.
- **2-B:** the elegant trap GPT named — a warehouse lease *can* contain operating-expense machinery and a retail lease *can* omit it; keying to the label mis-declares both. Do not adopt without understanding this.
- **2-C:** pushes the hard question onto **"demonstrated provision applicability"** — how is applicability determined? Deterministically (text clues, current `is_applicable`)? By extraction state (`NOT_APPLICABLE` status)? By governed selection (the unbuilt §6 panel)? Each has a different reliability and a different build cost. **2-C is only as sound as its applicability signal**, and that signal is itself a decision (see the sub-question in §6).

### Patent-description implications (flag only)

- The spec (§5.2) and supplement (§5) present the dependency map as a flat per-LP declaration. **2-C refines "when a dependency applies" and connects it to the §9 `NOT_APPLICABLE` contract** — this is within the described architecture, not outside it. 2-B (document-type keying) is *not* described and is the weakest fit to the "keyed to declared dependencies, generalizes across documents" language in §5. No claim turns on this, but 2-C is the most consistent with the existing record.

---

## 6. Question 3 — Uncertain-applicability behavior

**When the system cannot determine whether a parameter applies to a document, what does it do?** (This is Atlas's bare 22.4% and any `charge_basis=unclear` case.)

### Options

**3-A. Uncertainty blocks canonical certification.**
If applicability is unknown, the run cannot be canonically certified — fail-closed, same doctrine as unverified spans.

**3-B. Uncertainty creates an explicit unresolved dependency routed to Review Needed.**
The dependency is neither silently satisfied nor silently dropped; it is marked unresolved and surfaced for human attention. (Mirrors the §7 "a failed trace kills the trace, not the evidence → Review Needed" doctrine.)

**3-C. Provisional attachment while explicitly unsatisfied.**
The nearest candidate span may be attached for context, but the dependency is flagged `unsatisfied/provisional` and cannot count toward Gate B satisfaction.

### The thing every option must forbid

**The system must never silently choose the nearest profile / nearest span and treat it as satisfied.** That is exactly what happened to Atlas's `tenant_share` (nearest span = 22.4%, silently accepted). Whatever is chosen, "silently pick the closest thing and go green" is off the table. This is the non-negotiable floor beneath all three options.

### Advantages / failure modes

- **3-A** (block) — safest; but on a lease where *one* parameter is uncertain, blocking the whole canonical run may be heavier than warranted (cf. the 429b LP-path abort-vs-Review-Needed tension already on the horizon — same shape of question).
- **3-B** (Review Needed) — most consistent with existing CAM doctrine; surfaces the uncertainty to the lawyer rather than deciding it; does not over-block. Needs a real Review-Needed surface to route to.
- **3-C** (provisional) — most flexible, most dangerous: "attached but unsatisfied" is precisely the state that got misread once already; only safe if every downstream consumer treats `provisional` as `unsatisfied` without exception.

---

## 7. What every option leaves unresolved

Regardless of how 1/2/3 are decided, these remain open and are **not** closed by 431A:

- **Concept correctness** (§0). The wrong verified percentage can still be selected after the correct dependency is declared. Atlas can contain several percentages in the same expense family; declaring the dependency correctly does not choose among them. → Step 431 Track 2 investigation.
- **Value presence** as a mechanism. Even the cheap, buildable check (`base_rent` must carry a value) is not specified here — 431A only fixes the *identities* that check will be written against. → Step 431 Track 1.
- **Where applicability is determined** (Q2's dependency). If 2-C is chosen, the applicability-signal decision (deterministic / extraction-state / governed-selection) is partly deferred into Track 3's measurement.
- **The 429b LP-path terminal-behavior decision** (abort vs Review-Needed) is a structurally identical question already on the horizon; whatever is decided in Q3 should be checked for consistency with it, but 431A does not merge them.

---

## 8. Decision summary + ratified decisions

**Repeat of §0, statement 1 (division of labor):** Models judge meaning. Code verifies evidence grounding, trace integrity, declared completeness, and governance behavior. CAM exposes disagreement and uncertainty rather than representing semantic judgment as deterministic fact.

**Repeat of §0, statement 2 (the boundary):** Governed selection is the mechanism for determining concept relevance; it is not proof that the selected concept is semantically correct. Panel agreement raises confidence and makes the decision auditable, but shared semantic error remains possible. Parameter identity refinement and governed selection reduce concept-substitution risk; they do not eliminate it.

**RATIFIED 2026-07-19 by Tzvi.** Cells are filled with the ratified decisions, not defaults.

| # | Decision | **RATIFIED ANSWER** |
|---|---|---|
| Q1 | Parameter identity | **Structured identity.** Keep the existing logical parameter family (`tenant_share` etc.); add a governed semantic qualifier such as `charge_basis`. Do NOT explode into a general parameter taxonomy or dozens of per-basis names. The §6 Selector Panel judges the applicable charge basis from cited evidence; code records and governs that judgment, it does not independently determine the meaning. |
| Q1′ | Combined / unclear basis | **Confirmed: unclear ≠ satisfied.** A `combined` or `unclear` basis is recorded as such and routes to unresolved; it never silently counts as satisfying an operating-expense (or any specific-basis) dependency. |
| Q2 | Requirement rule | **Schema-declares-possible, panel-determines-actual.** The versioned schema profile declares which dependency relationships MAY apply. The §6 Selector Panel determines whether the contractual mechanism ACTUALLY applies in this document and which spans support it. Document type may inform the judgment but cannot control it. Applicability must be supported by cited evidence and preserved reasoning. |
| Q2′ | Applicability signal | **Governed selection** (the §6 Selector Panel), backed by the versioned schema profile — not a document-type label, not a bare deterministic text clue. Cited evidence + preserved reasoning are required. |
| Q3 | Uncertain applicability | **Uncertainty cannot produce clean certification.** Preserve all candidate evidence; preserve competing judgments and cited reasons; route unresolved applicability or concept identity to Review Needed. A merely source-verified span does NOT satisfy the dependency. Gate B stays unchanged — it consumes the governed result, it does not adjudicate semantics. |
| Q3′ | Floor | **Confirmed.** Never silently pick the nearest span and mark it satisfied. Non-negotiable. |

**Open routing dependency this creates (named, not resolved here):** Q3's "route to Review Needed" now has THREE consumers pointing at a Review-Needed surface that does not yet concretely exist on the parameter/selection path — (i) uncertain applicability/concept identity (this document), (ii) panel disagreement from the §6 selector once built, and (iii) the structurally identical 429b LP-path terminal-behavior decision (abort vs Review-Needed) already on the horizon. "Route to Review Needed" is only a real answer if a Review-Needed target exists. Step 431 must name this surface as a required dependency (whether it builds it or stubs it), or it will be written assuming a routing target that isn't there. This is flagged, not solved, in 431A.

---

## 9. Downstream consequences for full Step 431 (Path B — ratified)

The ratifications collapse the earlier "three separate tracks" plan. Because meaning is now determined by the **§6 Selector Panel** and code only governs that judgment, concept-correctness is no longer a separate open investigation — it is the panel's job. The parameter block becomes a **consumer and materializer of governed panel output**, not the authority that decides semantic identity. Continuing to "finish" the standalone deterministic parameter block first would be building a cathedral around a hole: 428 (evidence lost through an ungoverned mapping assumption) and 430 (source-verified evidence given the wrong semantic identity, green gate) are both the missing judgment layer.

**Therefore the next specification is Step 431: Governed Evidence Selection for Parameter Identity, Applicability, and Concept Matching.** It is still a spec-and-measurement step — no wiring, Gate B untouched, `cam/core/` untouched, live pipeline unwired.

### What survives from the old Track 1 (value-presence)

The cheap deterministic value-presence check survives, but as a **subordinate rule inside the selection architecture**, not a standalone track. Worked example (Atlas `base_rent`): the definition stub `"Base Rent" shall mean the annual rent payable as set forth in Section 3.1.` remains valid source evidence — code may mark it `operative_value_present: false`; it cannot by itself satisfy the `base_rent` dependency; it must NOT be deleted (the cross-reference may help the panel locate the operative §3.1 schedule); the panel may select the definition sentence, the schedule, or both, with cited reasons. This is "a failed trace kills the trace, not the evidence" (Supplement #26 §7): the code check stops a value-less stub from masquerading as a completed parameter without pretending the stub is irrelevant.

### HARD SCOPE FENCE for Step 431 (non-negotiable)

Step 431 must **not** become the general §6 Selector Panel master specification. It is scoped to exactly four **forcing cases**, drawn from observed failures:

1. Charge-basis assignment for `tenant_share` (Atlas 22.4% opex-vs-tax/CAM).
2. Provision/dependency applicability (does the mechanism actually apply in *this* document).
3. Base Rent definition stub vs. operative value-bearing schedule (Atlas `base_rent`).
4. Contractual percentage vs. hedged/narrative percentage (Atlas's "approximately 3% per annum" aside vs. Atreca's `Rent Adjustment Percentage: 3%`).

**Stop-test (this is the enforceable form of "minimum reusable mechanism"):** Step 431 may define reusable selector mechanism **only where a *second* of the four forcing cases actually requires it.** Anything required by just one case stays case-local. Anything required by *none* of the four is out of scope by definition. This converts "minimum reusable" from a judgment call into a checkable rule and is the specific guard against the four-case spec metastasizing into the full panel one commit at a time. Explicitly OUT of 431's scope: the full generalized trace-validation architecture, every correlated-blind-spot mitigation, every evidence type, and any evidence-selection concern not exercised by one of the four cases.

**Build sequence:** prove the selector mechanism against the four observed failures → measure it → widen only after the evidence supports widening. Incremental against real failures, never speccing the whole panel up front.

### Naming (fixed now to prevent a doctrine collision)

Do **not** call this "Layer 3." "Layer 3" already denotes materiality/routing in the directional-governance architecture; reusing it for evidence selection will eventually let someone port the wrong doctrine into the wrong layer. Use **Evidence Selection Layer**, **§6 Selector Panel**, or **423 Evidence-Assignment Layer 3** (only with the architecture qualifier explicit).

### Patent-timeline context (context, NOT authorization)

The §6 selector panel is "the strongest claim" in Supplement #26. Because it is now the next build, and an attorney conversation is owed before September with a non-provisional targeting ~November:

- Step 431's specification and forcing-case measurements should be preserved as **potential reduction-to-practice evidence** for Supplement #26's governed-evidence-selection contribution.
- The technical results should be written so counsel can cleanly distinguish **conception**, **partial reduction to practice**, and **still-unbuilt generalization**.
- This does **not** expand Step 431's engineering scope and does **not** authorize patent drafting. It is a note to write 431's results legibly, nothing more.

---

## 10. Explicit non-authorization

431A authorizes **no implementation.** No code, no validator, no schema change, no dependency-map edit, no `PARAMETER_TARGETS` edit, no Gate B change, no wiring, no patent-claim language, and no Claude Code handoff. The decisions in §8 are ratified; **acting on them is not.** Full Step 431 — itself still a spec-and-measurement step, not a wiring step, and bounded by the §9 scope fence — is the next artifact to draft. Any patent supplement owed by the Q1 structured-identity decision is written after the technical spec, per the standing protocol (full supplement + `Patent_Current_State.md` in the same session), and its claim framing is an attorney matter.

---

*Decision document. Decisions in §8 RATIFIED 2026-07-19 by Tzvi. Next artifact: narrowly-scoped Step 431 governed evidence-selection spec, under the §9 scope fence. No implementation authorized.*
