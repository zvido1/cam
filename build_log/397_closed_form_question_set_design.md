# Step 397 — Closed-Form Directional Question-Set Design (Paper Half)

Date: 2026-06-13
Status: PAPER / DESIGN ONLY. No model calls, no code, no harness run, no schema change, no stack touch. Freeze-safe. Lawyer-independent for the DESIGN half; the WORLD-question half (are these true findings) stays gated behind the lawyer panel and is explicitly NOT decided here.
Inputs (artifacts, not memory): `389_closed_form_directional_prototype_RESULTS.md`, `391_axis2_tightening_RESULTS.md`, the §8.3 absence census (`393`/`394a`/`394c` + Supplement #24 §9/§9b), `parked_strategic_ideas.md` (closed-form refinement section).
Purpose: do the "design the question set, then validate it on paper against known cases" work the parked-ideas file calls for. Two deliverables: (A) a closed-form question for the one known finding shape that has NO home in the four live axes — the §8.3 absence trap; (B) an on-paper forcing-test of the existing + proposed question set against four known findings.

---

## 0. What already exists (the artifact this extends)

`lease_closed_form_directional.py` (RTP, Steps 389/391) implements four closed-form directional axes, each a closed-answer question with a separate reason field, routed structurally (Guard 3: the router reads only `axis_id`/`question_id`/`answer`, never `reason`/`citations`):

- **Axis 1 — same-risk parallel.** Does a specifically-named parallel obligation/event carry the same risk treated differently elsewhere? (modifier-only; does not alone create a candidate)
- **Axis 2 — obligation-without-remedy.** Q-A: does a specific tenant obligation depend on a specific *named* landlord-side condition failing? Q-A-confirmed (Step 391 tightening): are all four components named — specific obligation, specific named landlord condition (not a category), specific tenant consequence, missing remedy? Q-B: adequate remedy if condition fails? Candidate iff `q_a=yes AND q_a_confirmed∈{yes,unclear} AND q_b=no`.
- **Axis 3 — conditional-protection.** Is the tenant's protection conditioned on narrow triggers that create a disadvantage?
- **Axis 4 — unilateral-control.** Can the landlord unilaterally eliminate/determine the tenant's protection?

The decisive validation result: LP-11 (wish-list control) freeform 10/10 → closed-form 0/5 (the scalpel proof — the axes discriminate, they are not a reworded wish-list). LP-15 did NOT drop (5/5) and is the open materiality/world-question case for the lawyer panel.

These four axes are all **present-text** axes: each asks about a feature visible *in* a clause (an obligation, a condition, a control right). That is their shared blind spot.

---

## 1. The gap: the §8.3 absence shape has no closed-form home

The §8.3 Landlord's-Work / fixed-commencement trap (Supplement #24 §9) is a trap of **absence**: a fixed §3.1 rent obligation running "without abatement" from a fixed calendar date + a foreseeable §8.3 landlord delivery failure + **no paired relief anywhere in the document**. The census established (393/394a/394c) that this is real on Atlas (populated Exhibit B + rent fixed to a calendar date independent of buildout), clean-counter on Albireo (§3.1(C) day-for-day credit present), and that Atlas is currently a near-singleton.

The prototype already SHOWED the gap empirically without naming it. Step 389 §4: on LP-03, the closed-form axes surfaced a candidate 5/5 — but the models found the *renewal-option* issue (a present-text Axis-2/3/4 pattern), NOT the §8.3 commencement trap. The §8.3 trap did not surface through the four axes even though LP-03 was flagged, because **none of the four axes asks an absence question**. Axis 2 comes closest (obligation-without-remedy) but is structurally a *present-condition* question: its Q-A requires "a specific tenant obligation depends on a specific named landlord-side *condition*" — the §8.3 obligation depends on no condition at all; it runs flat regardless. The census confirmed this inverse-polarity mechanically (393): Axis-2 q_a tests an obligation LINKED TO a named failure; the §8.3 obligation runs REGARDLESS OF any landlord condition. Opposite shapes. Axis 2 cannot catch it without distortion.

So: the four axes are present-text; the §8.3 finding is absence; there is a known finding with no enumerated home. This is precisely the "homeless question" the parked file names. The design job is to give it one — as a fifth closed-form axis OR an Axis-2 absence-variant. The census left (b)-variant vs (c)-fifth-axis OPEN; this memo designs the QUESTION without prejudging which slot it occupies, because the question wording is the same either way and the slot is an implementation choice the lawyer-panel + second-lease evidence settles later.

---

## 2. Design — the closed-form absence question (Axis 5 / Axis-2-absence-variant)

The hard part, per the parked file, is **designing the choice axis** so the multiple-choice verdict carries the finding and the reason only explains it. The test: if the reason field is doing the real work, the axis is chosen badly. Applying that test to absence:

A naive absence axis — "is there a missing protection? [yes/no]" — FAILS the test immediately. It is the freeform wish-list in closed-form clothing; "is something missing" invites infinite yes, exactly the LP-11 failure mode. The fix is the same discipline that made Axis 2 work: require the absence to be **anchored to a specific foreseeable failure event and a specific unprotected obligation**, not floated as a general "could be better."

Proposed closed-form block (mirrors the Axis-2 four-component structure, inverted to absence):

> **Axis 5 — Obligation-running-against-foreseeable-failure (absence of paired relief).**
>
> **Q-A (trigger pairing):** Does the lease impose a specific, continuing tenant obligation (e.g. pay rent, vacate, perform) that begins or continues at a *fixed point* (a calendar date, or an automatic trigger) **independent of** whether a specific, foreseeable landlord performance has actually occurred? [yes / no / unclear] + reason.
>
> **Q-A-confirmed (four-component anchor — the anti-wish-list gate):** Can you name all four: (1) the specific tenant obligation; (2) the specific fixed trigger that starts it; (3) the specific foreseeable landlord performance whose *non-occurrence* the obligation ignores; (4) the specific adverse consequence to the tenant if that performance does not occur? [yes / no / unclear]. A "no" here structurally blocks the candidate (same as Axis-2 q_a_confirmed). Category language ("such as delays", "various landlord obligations") = no.
>
> **Q-B (relief search — the absence itself):** Searching the ENTIRE document, is there ANY paired relief for that specific failure — abatement, rent credit, delayed commencement, extension, termination right, or self-executing remedy? [yes / no / unclear] + reason citing where you looked. Candidate iff `q_a=yes AND q_a_confirmed∈{yes,unclear} AND q_b=no`.

Why this passes the three over-atomization tests from the parked file:
1. **One question each.** Q-A asks about the obligation/trigger pairing; Q-B asks about document-wide relief. Each is independently answerable.
2. **Closed, exhaustive, mutually-meaningful choices.** yes/no/unclear on each, with the candidate logic fixed.
3. **Preserves the unit of risk — this is the critical one.** The §8.3 trap is an INTERACTION (fixed obligation AND foreseeable failure AND no relief). Atomizing into "is rent fixed? yes" / "is there relief? no" as *unrelated* questions would scatter the trap across the seam — exactly the failure the parked file warns about. Axis 5 keeps them in ONE block bound by the four-component anchor: Q-A-confirmed forces the model to name the obligation AND the foreseeable failure AND the consequence *together*, so Q-B's relief search is scoped to *that specific paired failure*, not to relief-in-general. The seam is held inside the block.

Critical design property — **document-scope dependence (inherits the census precondition).** Q-B ("searching the ENTIRE document") is only valid if the entire document is in fact provided to the evaluator. The census fixed this: favorable/adverse absence is a false-finding generator on partial uploads exactly because Q-B cannot be answered honestly on a fragment. So Axis 5 carries a hard precondition: it MUST be gated by the scope-completeness state (full lease confirmed fed to evaluator). On a partial upload Axis 5 must return `not_assessable`, never `q_b=no`. This is the same not-assessed discipline as the NOT_ASSESSED sentinel (Supplement #25) and the document-scope precondition in Supplement #24 §9. Without it, Axis 5 is a false-trap factory.

Why the SLOT (fifth axis vs Axis-2 variant) stays open and doesn't block the design: the question text above is identical whether it's registered as `axis5` or as `axis2_absence_variant`. The only difference is bookkeeping in `compute_axis_supported_candidate()`. The census said two real data points (Atlas instance, Albireo counter) lean (b) Axis-2-variant; this memo neither confirms nor overrides that — it designs the question so EITHER slot can host it. Slot is decided by the lawyer panel + a populated-work warehouse counter-lease, per the 394c gating requirement.

---

## 3. The mandatory catch-all (the sanctioned home for wandering)

The parked file's catch-all principle applies directly and is part of the design, not an afterthought. Closed-form axes only catch what was ENUMERATED; the §8.3 gap is itself proof that enumeration is always incomplete (four axes shipped, a fifth shape was already known and homeless). So the design includes ONE sanctioned, structured catch-all field, asked once per LP after all axes:

> **Catch-all:** Any other specifically-identifiable tenant-adverse feature of this provision not captured by Axes 1–5? [yes / no] + if yes, name the specific clause text and the specific adverse consequence (no category language).

This is NOT freeform wandering — it is a designated, closed-gated home for the unenumerated, and it doubles as **instrumentation**: if the catch-all keeps surfacing the same shape across leases, that shape is the next axis to enumerate. (Design rule from the parked file: prefer "remove the slot where wandering lands" over "instruct don't wander" — but provide ONE structured slot so the unenumerated finding is captured rather than lost.) The catch-all answer must NOT be readable by the structural router as a candidate-creator without human review — it is a flag for schema-gap detection and lawyer review, not an auto-route. (Open design question for the build phase: whether a catch-all "yes" routes to Review Needed or only to an internal schema-gap log. Not decided here.)

---

## 4. On-paper forcing test (the cheap validation the parked file mandates)

The parked file: "VALIDATE THE QUESTION SET AGAINST KNOWN CASES BEFORE BUILDING (cheap, do it on paper first)." Take findings already known to exist and check whether the proposed closed-form questions would FORCE them to surface without freeform discovery. If a closed question can't be answered the surfacing way given the lease text, the question set is incomplete.

This is a PAPER reasoning exercise over the known clause facts, NOT a model run. It tests the QUESTION SET's completeness, not the world-truth of the findings (that stays with the lawyer).

### Case 1 — LP-03 §8.3 commencement trap (Atlas). The motivating case.
Known facts (from the census, grounded in Atlas text): §1.2 Commencement Date = fixed April 1 2026; §3.1 rent runs from that date "without abatement"; §8.3 landlord must complete a populated Exhibit B buildout before commencement; no relief anywhere if buildout is late.
- Axis 5 Q-A: "Does a continuing tenant obligation begin at a fixed point independent of whether a foreseeable landlord performance occurred?" → **YES** (rent, fixed April 1, independent of buildout completion). Forced by the text.
- Q-A-confirmed: name (1) pay base rent; (2) fixed April 1 commencement; (3) landlord completion of Exhibit B buildout; (4) tenant pays rent on space it cannot occupy/use. All four nameable → **YES**.
- Q-B: "Any paired relief document-wide?" → **NO** (census confirmed no abatement/credit/termination for late delivery anywhere). → **CANDIDATE FORCED.**
- **Verdict: the question set FORCES LP-03's §8.3 trap to surface every run.** This is the finding the four present-text axes MISSED in Step 389 (they found the renewal issue instead). Axis 5 closes that specific gap. PASS (design-completeness).

### Case 2 — LP-19 service interruption (Atlas). The contested case.
Known facts: §6.3 abatement gated on landlord fault + >5 business days + full untenantability; separately metered 24/7 tenant; shorter/no-fault/partial interruptions get no relief.
- Present-text axes already surface LP-19 5/5 (Step 389/391) via Axis 2 (remedy exists but conditioned) + Axis 3 (heavily conditioned) + Axis 4 (landlord's architect determines). So LP-19 is NOT homeless — it has a home in the existing axes.
- Does Axis 5 ALSO fire? Q-A: is there a fixed tenant obligation independent of a foreseeable landlord failure? Rent runs during a service interruption that doesn't meet the §6.3 threshold → arguably yes (rent obligation continues through a foreseeable utility failure). Q-A-confirmed: (1) pay rent; (2) continuous; (3) landlord-side service interruption under 5 days or partial; (4) tenant pays full rent during impaired operations. Nameable → yes. Q-B: any relief for *that* sub-threshold interruption? → NO (relief only above the threshold). → Axis 5 would ALSO flag LP-19.
- **Verdict: LP-19 surfaces through BOTH the present-text axes AND Axis 5 — but the ROUTING (Risk vs Review Needed) is the contested question, and that is the lawyer-panel question (B2 in Packet 02), NOT a question-set completeness question.** The question set is complete for LP-19 (it forces surfacing); whether it should route Risk or Review Needed is the world-question. PASS (completeness) with the routing flagged to the panel. NOTE: Axis 5 firing on LP-19 is a design watch-item — if Axis 5 fires on every conditioned-remedy provision, it may be too broad (the LP-15 problem one level over). The four-component anchor should prevent this (the "foreseeable landlord performance whose non-occurrence the obligation ignores" must be NAMED and SPECIFIC), but it needs the same empirical check Axis 2 got.

### Case 3 — LP-26 quiet enjoyment / SNDA (Atlas). The Axis-3/4 case.
Known facts: §18.1 quiet enjoyment conditioned on no default + subject to Superior Interests; §19.2 full SNDA only for existing lenders, "commercially reasonable efforts" for future ones.
- Present-text axes surface LP-26 5/5 (Step 389) via Axis 3 (protection conditioned) + Axis 4 (landlord unilateral). Home exists.
- Does Axis 5 fire? Q-A: fixed tenant obligation independent of foreseeable landlord failure? The future-lender non-disturbance gap is an absence, but it is not a *fixed tenant obligation running against a foreseeable failure* — it's a conditional protection. Q-A → likely NO (no fixed obligation triggered by a foreseeable landlord performance failure; the risk is a future lender's foreclosure disturbing possession, which is a conditional-protection shape, not an obligation-against-failure shape). → Axis 5 correctly does NOT fire; LP-26 stays in Axis 3/4.
- **Verdict: Axis 5 correctly does NOT claim LP-26 — it is genuinely an Axis-3/4 conditional-protection finding, not an absence-of-paired-relief finding. This is GOOD: it shows Axis 5 discriminates rather than absorbing every finding (the anti-LP-11 property for the new axis).** PASS (Axis 5 correctly silent; LP-26 home is Axis 3/4).

### Case 4 — §11.2 indemnification (Atlas). The parked-file's named test case.
Known facts (general Atlas indemnity shape): tenant indemnifies landlord broadly; question is whether the indemnity is reciprocal and whether it carves out landlord negligence.
- This is a present-text directional shape (is the indemnity reciprocal? is the remedy proportional?) → Axis 3 (conditional/asymmetric protection) and possibly Axis 1 (same-risk: does landlord indemnify tenant for the parallel risk?). Home exists in present-text axes.
- Axis 5? Q-A: fixed obligation against a foreseeable landlord failure? Indemnification is not obligation-against-delivery-failure; it's allocation of third-party-claim risk. Q-A → NO. Axis 5 correctly silent.
- **Verdict: §11.2 is an Axis-1/Axis-3 case; Axis 5 correctly does not fire. PASS** (Axis 5 silent; reinforces that Axis 5 is narrow, not a catch-all).

### Forcing-test summary

| Known finding | Present-text axes (1–4) | Axis 5 (absence) | Question-set forces surfacing? | World-question (lawyer) |
|---|---|---|---|---|
| LP-03 §8.3 commencement trap | MISS (find renewal instead) | **FIRES (forced)** | **YES — Axis 5 closes the gap** | is it a true risk? (panel) |
| LP-19 service interruption | fire (5/5) | also fires | YES (already homed; Axis 5 redundant-but-consistent) | Risk vs Review Needed? (panel B2) |
| LP-26 quiet enjoyment | fire (5/5) | correctly silent | YES (Axis 3/4 home) | Risk vs Review Needed? (panel C2) |
| §11.2 indemnification | fire (Axis 1/3) | correctly silent | YES (Axis 1/3 home) | reciprocity materiality? (panel) |

**Design-completeness verdict: the question set, WITH Axis 5 added, forces all four known findings to surface, and Axis 5 fires on exactly the one case the four present-text axes missed (LP-03 §8.3) while staying correctly silent on the two cases that are genuinely present-text (LP-26, §11.2).** That selective silence is the Axis-5 analogue of the LP-11 scalpel proof: a new axis earns its place only if it discriminates, and on paper it does — it does not absorb LP-26 or §11.2 just because they involve "something the tenant lacks."

The one watch-item: Axis 5 also fires on LP-19. That is not necessarily wrong (a sub-threshold service interruption IS an obligation running against a foreseeable failure with no paired relief), but it means Axis 5 and the present-text axes can BOTH claim a provision. The build must decide whether double-claiming is fine (more supporting axes = stronger candidate) or whether Axis 5 should yield to Axis 2/3 when they already fire. Provisional design call: **double-claiming is fine** — supporting_axes is already a list (Step 389 LP-26 carries axis1_modifier alongside its real axes), so Axis 5 simply joins the list; it does not need to arbitrate. Flag for build-phase confirmation.

---

## 5. What this memo decided and what it explicitly did NOT

DECIDED (design, lawyer-independent):
- The §8.3 absence shape gets a closed-form home: Axis 5, a four-component anchored obligation-against-foreseeable-failure question with a document-wide relief search, gated by scope-completeness (returns not_assessable on partial uploads).
- The question is designed so it occupies either slot (fifth axis or Axis-2 absence-variant) without rewording — slot choice deferred to lawyer panel + second populated-work warehouse lease.
- A mandatory structured catch-all field is part of the design, doubling as schema-gap instrumentation.
- On paper, the augmented question set FORCES all four known findings to surface and Axis 5 discriminates correctly (fires on LP-03, silent on LP-26/§11.2).

NOT DECIDED (gated, not in this memo's authority):
- Whether LP-03 §8.3 / LP-19 / LP-26 are TRUE risks or appropriate non-findings — the world-question, lawyer panel (Packet 02 B2/C2 + a §8.3 item).
- The Risk-vs-Review-Needed ROUTING for any contested finding — Layer-3 materiality, lawyer-gated.
- Whether Axis 5 is registered as a fifth axis or an Axis-2 variant — needs the panel + the populated-work warehouse counter-lease (394c gating requirement).
- Any build. This is paper. No code, no harness, no schema file touched.

NON-GOALS honored: no model calls, no pipeline run, no code, no schema change, no stack touch, no DEF-002 movement (DEF-002 stays blocked exactly as Step 389 §10 left it). This memo: `build_log/397_closed_form_question_set_design.md` (local, not pushed).

---

## 6. If/when this is built (named next steps, not authorized here)

1. Lawyer panel answers the world-question for LP-03 §8.3 (true trap or over-eager?) — folds into the existing §8.3 packet alongside Packet 02 B/C.
2. IF panel confirms LP-03 §8.3 is a true risk → implement Axis 5 in `lease_closed_form_directional.py` (mirrors the Axis-2 block structure; adds `axis5` + `axis5_qa_confirmed` + `axis5_qb` to the JSON template and `compute_axis_supported_candidate()`), gated by scope-completeness.
3. Run the existing N=5 closed-form harness with Axis 5 added; confirm LP-03 surfaces the §8.3 trap (not just the renewal issue) and Axis 5 stays silent on LP-26/§11.2 (the live version of this paper test).
4. Second populated-work lease (warehouse, fixed-date rent, populated Exhibit B) to settle fifth-axis-vs-Axis-2-variant — the 394c gating requirement.
5. Catch-all routing decision (Review Needed vs internal schema-gap log only).

Each step has a clean stopping seam; none is authorized by this memo.
