# Step 431 Part A — Governed Evidence Selection: Specification (v5)

**Author:** Chat instance
**Date:** 2026-07-19
**Type:** SPECIFICATION (Part A of 2). Design only. No code, no runs, no model calls. Authorizes nothing. **RATIFIED 2026-07-19 by Tzvi** (string/diff check passed: rename complete across §6.2/§6.3/§7; both v5 micro-edits present; `relevance_ok` threaded; `completeness_provenance` typed). Committed `e702bf0`.
**Revision:** v5 (final) — surgical edits on the third-review's remaining three trapdoors (architecture declared stable by the reviewer; v4's 13 pieces are settled and not reopened), plus two diff-only micro-edits from the v5 verification: empty `field_support` now invalidates a field (§4.5), and the stale §6.2 `unsatisfied_no_value` branch is now completeness-gated. Changes: (1) `parameter_family_relevance` carried through merge/agreement/comparison/certification with a `relevance_ok` gate — minority relevance retains but does not certify; (2) `completeness_provenance` is now a TYPED record (§6.4), Part B must set `status: not_established`; (3) field-addressed citations (`field_support`) with field-level grounding-failure invalidation (§4.5), including empty-support, not a confidence haircut. Plus wording: `applicable_not_qualified` → `applicable_no_supplied_candidate_qualified`; §11.2 mechanism-vs-correctness sentence. **RATIFIED — string/diff check passed.**
**Gates:** Part B (the real-panel measurement instruction) is NOT written until Part A is ratified.
**Ratified inputs:** `build_log/431A_decision_document.md` §8.
**Sources read this session:** `cam/adapters/lease_review/lease_coverage_305.py` (full); `lease_parameter_block.py` (427/429); `lease_evidence_spans.py` (423A/425); `423_evidence_assignment_architecture_spec.md` §4/§6/§7; `Patent_Supplement_2026_07_14.md` (#26) §3/§6/§7; `430_gate_b_cross_lease.md`; config-integrity record (415/416).

**Governing doctrine (the through-line):**
> **The panel judges candidates. The policy certifies parameters. Context supports the judgment. Completeness limits every negative claim.**

---

## 0. What this specifies, and the two sentences that bound it

Minimum reusable governed-selection mechanism for the four forcing cases from 430 — no more. Evidence Selection Layer (§6 Selector Panel), NOT the general selector master spec. The 431A stop-test governs: mechanism defined only where a *second* forcing case requires it; one-case needs stay case-local; no-case needs are out.

**Division of labor (ratified, verbatim):** Models judge meaning. Code verifies evidence grounding, trace integrity, declared completeness, and governance behavior. CAM exposes disagreement and uncertainty rather than representing semantic judgment as deterministic fact.

**The boundary (ratified, verbatim):** Governed selection is the mechanism for determining concept relevance; it is not proof that the selected concept is semantically correct. Panel agreement raises confidence and makes the decision auditable, but shared semantic error remains possible. Parameter identity refinement and governed selection reduce concept-substitution risk; they do not eliminate it.

**The spine (load-bearing):**
> **The panel judges candidates. The policy certifies parameters.** A parameter is satisfied only when one coherent single candidate simultaneously meets every required condition. No parameter attribute may be assembled by borrowing one property from one candidate and another property from a different candidate. (Multi-span joint satisfaction — e.g. a definition plus its operative schedule — is NOT in the active path for 431; it is a deferred, measurement-triggered open question, §8.6.)

---

## 1. The problem (grounded in 430)

430: the current parameter block resolves spans that are stably verified yet **semantically wrong** (Atlas `tenant_share` → 22.4% tax/CAM ratio, not an opex share) or **value-less** (Atlas `base_rent` → definition stub, no figure). Both passed Gate B, which reads names + `verification_status` only. The missing capability is a governed judgment, before Gate B, that classifies each candidate's semantic identity, contractual role, and local support, compares the classification to the schema requirement, and certifies a parameter only from a coherent candidate — with disagreement and incomplete-scope preserved and routed, never silently passed.

---

## 2. Position in the pipeline

```
canonical source (423A/425, hashed, v2)
        │
        ▼
candidate span universe (elicitation 429): verified, offset-stable spans.
Per-parameter candidate set is multi-candidate (§3.1). NO new segmentation.
        │
        ├── deterministic context envelope per candidate (§3.2) — mechanical,
        │   identical for A/B/C, source-addressed, no retrieval
        ▼
┌───────────────────────────────────────────────────────────┐
│  EVIDENCE SELECTION LAYER (this spec)                       │
│                                                            │
│  per evaluator × candidate  → blind classification (§4)    │
│        ↓  merge panel judgments PER CANDIDATE              │
│  candidate_semantic_result (§5)                            │
│        ↓  compare each candidate's identity to requirement │
│  parameter_candidate_comparison (§6)                       │
│        ↓  certify from a COHERENT SINGLE candidate only        │
│  parameter_certification_state (§6, deferred policy)       │
│                                                            │
│  + cited-union retention keyed to blind relevance (§5.1)   │
│  + deterministic checks: value_token_present; every cited  │
│    quote resolves to source (§4.4, §6)                     │
└───────────────────────────────────────────────────────────┘
        │
        ├── certified → materialize Parameter → Gate B (UNCHANGED)
        └── unresolved/review → record governed result → SHORT-CIRCUIT
                                 before Gate B (§7)
```

Placement: between the span universe and the parameter block; no re-segmentation, no canonical-source mutation. Gate B is downstream and unchanged; it never receives a semantically-unresolved parameter (§7).

---

## 3. Candidate spans and interpretive context

### 3.1 Multi-candidate provisioning (required by cases 1, 3, 4)
Fixed, provisioned candidate set per parameter = the verified spans elicitation proposed for that parameter's targets, including competing candidates the panel must choose between (base_rent: stub AND operative schedule as separate primary candidates; tenant_share: 22.4% span AND any genuine opex-share span). No new segmentation, ranking, or discovery. A never-proposed needed candidate is a **finding Part B reports**, not something the mechanism repairs.

**Measurement honesty (to Part B, stated here):** seeding known-correct/known-wrong candidates measures **governed selection over a provisioned set with local context** — NOT candidate-generation recall or document-wide linked-clause discovery. Part B states this prominently.

### 3.2 Deterministic context envelope (bounded answer to "a span can't be judged in isolation")
A candidate span (Atlas's 22.4%) doesn't reveal on its own that §3.3 applies it to tax/CAM. Each candidate gets a **deterministic, versioned context envelope** generated before the panel call — NOT a semantic retrieval call (an ungoverned retriever in front of the governed panel = 421C with better docs).

```
context_envelope: source_document_hash, primary_start_char, primary_end_char,
  context_start_char, context_end_char, boundary_method, max_context_chars,
  context_policy_version, truncated_left, truncated_right
```
Rules (mechanical, no model discretion): generated before the call; identical for A/B/C; derived only from canonical offsets; expand span → containing block → adjacent complete blocks until fixed budget; record truncation. Block-aligned **only where the parser deterministically provides boundaries** — otherwise a fixed char window with truncation flags (no heading heuristics). **Never expanded by parameter type, expected basis, or model request.** The envelope solves *interpretation around a candidate*, NOT *finding distant competing candidates* — do not enlarge an envelope to swallow a candidate 3,000 chars away; that's §3.1's job.

**Parser dependency (unverified this session):** whether `lease_parser` yields reliable block boundaries is not confirmed. The envelope is written to degrade to a fixed char window if not; envelope sufficiency is a Part B measurement (§8).

### 3.3 Evidence and context stay distinct
The envelope interprets the candidate; it does not become evidence by being shown. Preserved: `candidate_span_id`, `context_envelope_id`, `candidate_citations[]`, `context_citations[]`. Every cited quote — candidate or context — must resolve verbatim to the canonical source (code checks existence; the model judges meaning). All candidates/envelopes enumerable + hashed. Unverified/ambiguous spans never enter as candidates (423A §4).

---

## 4. The per-candidate judgment (blind classification; parameter-type-specific)

Each frozen A/B/C evaluator, independently, for each (candidate + envelope) × parameter, returns a blind classification. Lineup = existing `EVALUATOR_LINEUP_305`. Part B mirrors `_call_single_evaluator_305`'s call/fallback/provenance shape; does not modify it.

**Configuration claim (corrected, v3):** the lineup is **identity-frozen and configuration-integrity-asserted** (414/416), NOT uniformly temperature-zero. Roles A and C transmit temperature 0; **Role B primary (gpt-5.5) cannot be sent temperature 0 (or any non-default temperature) — it runs at provider-default temperature 1 under a documented capability exception (415/416), logged, not silent.** Part A claims no deterministic sampling; reproducibility is "identity-frozen, config-integrity-asserted, observed over N runs," not "temp 0 → deterministic."

### 4.1 Blind classification output (per candidate × parameter)

Common fields (every parameter):
```
candidate_span_id, context_envelope_id
parameter_family_relevance: relevant | not_relevant | unclear      # §5.1 — inclusion judgment; NOT basis-match
candidate_support_state: supports_mechanism | does_not_support_mechanism
                       | insufficient_context | unclear            # LOCAL to candidate+envelope; §6/§4.3
text_role: operative_term | definition | narrative | unclear
value_completeness: self_contained | cross_reference_only | no_value | unclear
candidate_citations[], context_citations[]                        # each citation has an id + verbatim quote
field_support:                                                     # review #3 — which citation grounds which field
  parameter_family_relevance: { candidate_citation_ids[], context_citation_ids[] }
  candidate_support_state:    { candidate_citation_ids[], context_citation_ids[] }
  charge_basis_components:     { candidate_citation_ids[], context_citation_ids[] }
  charge_scope:               { candidate_citation_ids[], context_citation_ids[] }
  text_role:                  { candidate_citation_ids[], context_citation_ids[] }
  value_completeness:         { candidate_citation_ids[], context_citation_ids[] }
reason (1-3 sentences grounding each field in cited quotes)
confidence: high | medium | low
```

Parameter-type-specific semantic dimensions (dimensions that don't apply use `not_applicable`, which is NOT `none`). **Enums are CLOSED** — no `...`; where a forcing case needs an out-of-set value, use `other` + a free-text `other_basis_description` (never an open list Claude Code could extend into a general taxonomy):
```
tenant_share / building_share:
   charge_basis_components: subset of [operating_expenses, CAM, taxes, insurance, other] | none | unclear
   other_basis_description: <free text, only when 'other' present>
   charge_scope: building | project | premises | other | unclear
   other_scope_description: <free text, only when 'other' present>
base_rent:
   charge_basis_components: not_applicable          # basis is not a meaningful attribute of base rent
   (text_role + value_completeness + value-token shape carry it)
rent_adjustment_pct:
   charge_basis_components: not_applicable
   (text_role + value_completeness carry it; adjustment-subject only if a forcing case needs it — it does not, so omitted)
```
`none` = "the model found no basis"; `not_applicable` = "basis is not a meaningful attribute of this parameter"; `other` = "a basis outside the closed set, described in the free-text field." Three different states, never merged.

### 4.2 The two-part structure (blind, then compared — anti-gaming)
Part 1 (this section): the panel **classifies blindly.** The prompt states the concept-family neutrally ("classify what charge basis, if any, this span establishes and what its contractual role is") and **never names the desired basis, never shows a template value, never says 'find an operating-expense share.'**
Part 2 (§6, code): **compare** the returned `charge_basis_components`/`charge_scope`/`text_role`/`value_completeness` against the schema-declared requirement. The model classified; the mechanism decides match. Do not prime classification with the desired answer.

### 4.3 Absence requires completeness
`candidate_support_state` is a claim about the supplied candidate + envelope ONLY. If the clause establishing applicability could lie outside the envelope, the answer is `insufficient_context`, never `does_not_support_mechanism` promoted to document-level absence. Document-wide `not_applicable` is a separate state (§6) that **cannot** be established from bounded candidate envelopes without independent candidate-scope completeness provenance. "None of my candidates show it" ≠ "it isn't in the lease" (Supplement #26 completeness ≠ selection).

### 4.4 What code does NOT ask a model
Deterministic: does the span + every cited quote resolve verbatim to the hashed source (423A); does the candidate contain a value token of the right *shape* (`value_token_present`, §6); is a reason present where required (structural).

### 4.5 Field-grounding failure invalidates the field, not just its confidence (review #3)
Because `field_support` (§4.1) maps each semantic field to the specific citations that ground it, code can enforce grounding at field granularity — matching Step 305's discipline, which *downgrades* an uncited presence assertion rather than merely docking confidence:
- **Every substantive semantic-field judgment must identify at least one supporting citation in that field's `field_support`, unless the field value is deterministically fixed by the schema as `not_applicable`.** An **empty** support mapping (no citation ids at all), OR a mapping in which **no cited quote resolves**, invalidates that evaluator's judgment on the field — downgraded to `unclear`/`not_assessable`. (This closes the vacuous-pass shortcut: a field asserting `charge_basis_components: [taxes]` with empty `field_support` is not a grounded judgment and does not count.)
- If a citation required to ground a semantic-field judgment (listed in that field's `field_support`) does **not** resolve verbatim against the canonical source, **that evaluator's judgment on that field is invalidated — downgraded to `unclear`/`not_assessable` — not preserved as a substantive judgment with merely reduced confidence.**
- Consequence for agreement: a field cannot remain `unanimous` (§5.2) on the strength of a quote that does not exist in the source, or on no quote at all. If a field's grounding is empty or failed for an evaluator, that evaluator no longer counts as a substantive vote on that field.
- The raw failed quote **stays in the audit artifact as an unverified trace** — it does not enter `semantic_support_spans` (§7.1) and it does not support certification. Failed trace kills the trace, not the evidence; the candidate span itself (separately source-verified) is untouched.

---

## 5. Per-candidate merge, and cited-union retention

### 5.1 Cited-union retention — keyed to blind relevance (now a real mechanism)
A candidate enters the parameter's `retained_evidence` if **≥1** panelist marks `parameter_family_relevance: relevant` **with a grounded, source-resolving reason.** This is the inclusion judgment — relevance to the *family* (is this genuinely evidence about the tenant-share question), NOT whether it matches the required basis. Consequences:
- A wrong-basis share (Atlas 22.4%) is **relevant evidence to the share family** and is retained — while still failing the dependency at certification (§6). Retention ≠ satisfaction.
- **Contested inclusion** (1/3, 2/3 relevant) and **contested withholding** (a panelist marks `not_relevant` where others include) are real structured events, recorded with cited reasons as provenance, never collapsed to a number, never used to drop evidence. Minority relevance is never excluded (Supplement #26 §6.1 asymmetry: omission fatal, over-inclusion cheap).

Without this field the design would be a classifier over a pre-retained ledger, not the asymmetric selection mechanism #26 §6 describes. This field is what instantiates the claim.

### 5.2 `candidate_semantic_result` — per candidate, panel-merged (meaning not decided by code)
For **each candidate**, merge the three panelists' blind classifications into one candidate-level result, preserving disagreement:
```
candidate_semantic_result:
  candidate_span_id
  parameter_family_relevance: relevant | not_relevant | DISPUTED | unclear
  charge_basis_components: <agreed set | DISPUTED | not_applicable | unclear>
  charge_scope: <agreed | DISPUTED | unclear>
  text_role: <agreed | DISPUTED | unclear>
  value_completeness: <agreed | DISPUTED | unclear>
  candidate_support_state: <agreed | DISPUTED | insufficient_context | unclear>
  agreement_by_field:                       # PER-FIELD, not one global label
    parameter_family_relevance: unanimous | majority_with_dissent | split | unclear | not_assessable
    charge_basis_components: unanimous | majority_with_dissent | split | unclear | not_assessable
    charge_scope:            unanimous | majority_with_dissent | split | unclear | not_assessable
    text_role:              unanimous | majority_with_dissent | split | unclear | not_assessable
    value_completeness:     unanimous | majority_with_dissent | split | unclear | not_assessable
    candidate_support_state: unanimous | majority_with_dissent | split | unclear | not_assessable
  per_panelist[]  (full cited judgments, always preserved)
```
**Agreement is recorded PER FIELD, not as one global label** — and `parameter_family_relevance` is one of those fields (added v5, review #1). Retention (§5.1) and certification (§6) consume relevance differently: **minority relevance RETAINS evidence (§5.1); it does NOT independently CERTIFY the parameter (§6.1 `relevance_ok`).** A candidate that one panelist called relevant and two called not-relevant stays in the cited union AND is blocked from `satisfied` while relevance is non-unanimous — the asymmetry made precise. A candidate can be unanimous on basis, `majority_with_dissent` on role, and `split` on value simultaneously — a single label would erase that, and the deferred threshold decision (§6.3, §8.1) would then be "2/3 on *what*?", unanswerable. `majority_with_dissent` is recorded, never `resolved` — majority semantics are not preloaded beneath the deferred threshold. The certification policy (§6) decides what each field's agreement permits; the merge does not.

---

## 6. Parameter-level comparison and certification (policy certifies; never launders across candidates)

### 6.1 `parameter_candidate_comparison`
For **each candidate** in the parameter's retained set, code compares that candidate's `candidate_semantic_result` against the schema requirement, and attaches the deterministic checks — **all evaluated on the SAME candidate:**
```
per candidate:
  relevance_ok: parameter_family_relevance == relevant                # review #1 (v5)
  basis_match: match | mismatch | not_applicable | undeterminable   # its components/scope vs required
  text_role_ok: <text_role in allowed roles for this parameter>     # e.g. base_rent requires operative_term
  value_ok: value_token_present(this candidate) AND value_completeness == self_contained
  support_ok: candidate_support_state == supports_mechanism
  agreement_by_field (carried from §5.2)
```

### 6.2 `applicability_match` (does the concept apply) separated from `qualification` (does THIS candidate satisfy)
The review's circularity fix: applicability must not be derived from full qualification, or the stub can never establish that Base Rent *is a mechanism in this lease* even though it plainly can. Two distinct questions:
```
applicability_match:   applicable | not_applicable | not_assessable | unclear   # does the concept/mechanism apply in this doc
candidate_qualification (per candidate): qualified | not_qualified            # does THIS candidate carry identity+role+value+support to satisfy
```
- **A candidate can establish `applicability_match = applicable` WITHOUT being `qualified`.** Atlas's Base Rent definition stub establishes that a base-rent mechanism *applies* in this lease (positive applicability) while being `not_qualified` to *satisfy* the parameter (no self-contained value). **Applicable-but-not-qualified is a real, distinct, expected state.** Without established completeness it routes to `applicable_no_supplied_candidate_qualified` or `review_needed_no_qualifying_candidate`, never `not_applicable`. Only when `completeness_provenance.status == established` (§6.4) may the certification policy emit a terminal `unsatisfied_no_value`.
- Applicability is established by a candidate whose *identity/support* fit the concept (basis/scope/support-ok for shares; text_role naming the concept for base_rent) — NOT by also requiring value_ok. Requiring value_ok for applicability is the circle; it is forbidden.
- **`applicability_match = not_applicable` (document-wide absence) may be asserted ONLY with candidate-scope completeness provenance.** Absent that provenance a negative is `not_assessable`, never `not_applicable`. Part B may prove Atlas's 22.4% does not *satisfy* the opex dependency; it may not thereby prove the opex mechanism is *absent from the whole lease* (the 421C distinction).

### 6.3 Certification — coherent-single-candidate rule (anti-laundering; completeness on every negative)
```
parameter_certification_state = certification_policy(
    per_candidate_comparisons,      # §6.1 — each candidate evaluated whole
    applicability_match,            # §6.2 — document-level, completeness-gated
    per_candidate_qualification,    # §6.2
    agreement_by_field,             # §5.2, per candidate
    completeness_provenance,        # TYPED record (§6.4) — only status:established permits a terminal negative
    policy_version
)
→ satisfied
  | applicable_no_supplied_candidate_qualified   # concept applies; no SUPPLIED candidate qualifies (not a document-level claim)
  | review_needed_no_qualifying_candidate        # the normal negative on a provisioned set
  | review_needed_disagreement
  | review_needed_incomplete_scope
  | review_needed_uncertain
  | unsatisfied_wrong_basis                       # TERMINAL — completeness_provenance REQUIRED
  | unsatisfied_no_value                          # TERMINAL — completeness_provenance REQUIRED
  | unsatisfied_not_applicable                    # TERMINAL — completeness_provenance REQUIRED
```
**Invariants Part A fixes now (threshold deferred; these are not):**
- **`satisfied` requires ONE SINGLE candidate** for which relevance_ok AND basis_match=match AND text_role_ok AND value_ok AND support_ok all hold **together, on that same candidate**, with `applicability_match = applicable`. **No cross-candidate assembly:** matching basis on candidate A plus a value token on candidate B does NOT satisfy. **Relevance is required, not just retained:** a candidate two panelists called `not_relevant` cannot certify even if its other fields line up — minority relevance keeps evidence available (§5.1), it does not certify (review #1). Under the no-implicit-majority rule, non-unanimous `parameter_family_relevance` routes to `review_needed_disagreement`.
- **No active multi-span bundle in 431.** The v3 "declared base_rent bundle" is REMOVED from the active path. A single self-contained schedule candidate may satisfy base_rent on its own; the definition stub stays *retained* (§5.1) but can never satisfy. If NO single candidate qualifies alone, the outcome is `review_needed_no_qualifying_candidate` and Part B **reports** "no coherent single candidate; a governed multi-span relationship may be required" — it does NOT compose one. Rationale: the forcing case has proven the stub is *inadequate*; it has NOT proven the operative schedule *cannot stand alone*. Do not build the relationship mechanism until Part B shows it is needed (measure before build). Deferred to §8.6.
- **Completeness discipline on EVERY parameter-level negative, not just `not_applicable`.** A `unsatisfied_*` state is a claim *about the document* ("the document does not supply a right-basis / value-bearing parameter"). On a provisioned candidate set with a recall disclaimer (§3.1), the only honest terminal negative WITHOUT established completeness is `review_needed_no_qualifying_candidate` ("no supplied candidate qualified"). Any `unsatisfied_wrong_basis` / `unsatisfied_no_value` / `unsatisfied_not_applicable` — all of which assert something about the document as a whole — requires `completeness_provenance.status == established` (§6.4), or it is downgraded to `review_needed_no_qualifying_candidate`. This is the same discipline v3 applied only to `not_applicable`, now applied to every negative that speaks about the document, over a **typed** provenance record (review #2) rather than a truthy flag.
- **No implicit majority default.** `certification_policy` with an unset threshold does NOT fall back to "2/3 wins." Until a threshold is ratified (post-Part-B), any candidate whose relevant `agreement_by_field` entries are not `unanimous` routes to `review_needed_disagreement`. A future `threshold=None → 2` substitution is a defect, not a default.
- Part A defines the policy's **inputs and invariants**; Part B measures **distributions**; a later ratification chooses the **threshold**.

### 6.4 Typed `completeness_provenance` (review #2 — the guard on every document-level negative)
The single most load-bearing negative-claim guard cannot be a truthy flag — a harness that attaches `{"complete": true}` would then emit terminal negatives it has not earned ("software loves a boolean when nobody specified what reality must exist behind it"). It is a **typed record**, and only `status: established` under a declared method permits any `unsatisfied_*`:
```
completeness_provenance:
  status: established | not_established
  scope: parameter_candidate_universe          # completeness OF WHAT
  method                                       # how completeness was established (declared)
  source_document_hash
  candidate_generation_policy_version
  evidence_artifact_id                         # the artifact that established it
  limitations[]
```
**Locked rules:**
- Mere presence of the object does NOT count; only `status: established` under a declared `method` permits `unsatisfied_*`.
- **Part B MUST set `status: not_established`** unless it consumes an independently ratified completeness artifact — because Part B expressly does not measure candidate-generation recall (§3.1), so it *cannot* establish document-wide candidate completeness.
- A manually seeded or provisioned candidate set is **never document-complete** merely because all known forcing-case candidates were supplied. (Supplying the known candidates is not proving no others exist — the 421C error one level up.)
- Without established completeness, every no-qualifying-candidate result remains `review_needed_no_qualifying_candidate` — never a terminal `unsatisfied_*`.
This turns completeness from a ceremonial field into provenance, and makes the honest Part B result "no supplied candidate qualified; not certified" — not "the document definitively lacks a qualifying parameter."

---

## 7. Orchestration seam: Review-Needed vs unchanged Gate B (named per review #6)

The seam must be explicit or Part B invents one. Gate B stays unchanged (reads names + verification_status); it must never receive a semantically-unresolved parameter masquerading as structurally complete.

```
parameter_certification_state == satisfied
    → materialize the certified Parameter from the coherent single candidate, carrying a
      COMPLETE evidence package (§7.1 — NOT just the primary span)
    → invoke unchanged Gate B on it

parameter_certification_state is any review_needed_* / unsatisfied_* / applicable_no_supplied_candidate_qualified
    → record the governed result (per-candidate comparisons, per-field agreement, cited reasons)
    → SHORT-CIRCUIT before Gate B — the parameter is not presented to Gate B at all
```

### 7.1 The certified package must carry the relied-on context (per review #3 — the sharpest catch)
If the materialized Parameter carried only its primary span, the 430 defect would be reconstructed *after* a correct judgment: Atlas's 22.4% would flow downstream **without** the §3.3 clause that establishes it applies to tax/CAM — an efficient loop straight back to the bug this layer exists to fix. The certified package therefore carries:
```
certified_parameter_evidence:
  primary_candidate_span          # carries the VALUE; the span that qualified
  semantic_support_spans[]        # the context quotes the panel ACTUALLY relied on to
                                  # classify basis/scope/role, resolved from context_citations
                                  # to source-addressed EvidenceSpans (offset + hash)
  panel_judgment                  # the per-field result + per-panelist cited reasons
  applicability_match, completeness_provenance
```
**The distinction that keeps this from becoming bundling (§6.3):** the **primary carries the value**; **support spans carry provenance for the classification** — they explain *why* the basis/role judgment holds. **No property is ever borrowed from a support span to cure a deficient primary.** A primary that lacks a self-contained value is `not_qualified` (§6.2) and cannot be rescued by a support span that happens to contain a number — that would be the laundering §6.3 forbids. Support spans are read-only provenance, never value donors. Every `semantic_support_span` is a source-verified `EvidenceSpan` (423A invariant); a context citation that does not resolve is **dropped and, per §4.5, invalidates the field it was grounding** (the affected evaluator's judgment on that field downgrades to `unclear`/`not_assessable`) — the failed quote stays in the audit trail as an unverified trace but never enters `semantic_support_spans` and never supports certification. It does not silently vanish, and it does not survive as a substantive judgment with merely reduced confidence.

This is **future wiring behavior, not an authorization to build it now** — Part A defines the seam so Part B's harness models certified-vs-short-circuited and produces the complete-package shape, rather than inventing routing or shipping value-only parameters. The Review-Needed data state is first-class and carries full preserved provenance. Structurally the same question as the deferred **429b LP-path** decision (abort vs Review-Needed); one doctrine eventually; neither resolved here.

---

## 8. Open sub-questions Part A does NOT close
(Referenced elsewhere as §8.N by item number.)
1. **Basis-agreement threshold** (§6.3) — unanimous vs majority-with-dissent. Not picked; sub-unanimous → Review Needed; chosen after Part B shows real disagreement patterns.
2. **Envelope sufficiency** (§3.2) — a Part B measurement: how often the bounded envelope sufficed; which cases needed more; whether insufficiency clustered on distant cross-references; whether governed linked-span retrieval is justified. Linked-span retrieval **expressly deferred**, measurement-triggered only.
3. **Model-side responsiveness validation** (423 §7.2) — Part A uses only the deterministic half; deferred; no forcing case strictly needs it.
4. **Correlated blind spots** (#26 §6.4) — union-before-use + preserved disagreement (auditable, not impossible). OPEN.
5. **Candidate-generation recall** — explicitly NOT measured (§3.1).
6. **Multi-span joint satisfaction (deferred, measurement-triggered).** A parameter satisfied by two spans jointly — e.g. base_rent's definition naming the term + the operative schedule carrying the value — is NOT in 431's active path (§6.3). It is built only IF Part B shows a material case where no single candidate can stand alone AND a governed span-relationship is genuinely required. Even then it needs a governed relationship judgment (or a deterministic source-verified cross-reference link) — never an implicit OR across candidates. Deferred; general evidence composition remains OUT.

---

## 9. Canonical-measurement rule (degraded/fallback), refined per review

- **Panel identity is read from actual provider/model/config metadata, not blindly from `is_fallback`.** A same-model self-retry (Role C's grok-4.3 own-chain entry) may carry fallback metadata without changing panel identity — such a run is still the frozen A/B/C panel and stays canonical.
- **Operational abstention / cross-family substitution** (Role C → Gemini/Mistral shared pool; a role that abstained and produced no judgment) → run is **preserved as audit artifact, EXCLUDED from the canonical result.** A degraded A/B/Gemini run is not the frozen panel.
- **Semantic refusal is NOT operational failure.** A panelist returning `unclear` / `insufficient_context` / `not_assessable` on its primary model is governed uncertainty — **part of the mechanism being measured — and STAYS in the canonical set.** Excluding it would hide the exact behavior Part B exists to observe.
- Part B reports: N canonical runs (all-primary by real metadata, semantic refusals included), N degraded runs (which role/model substituted or abstained operationally), computing success criteria over the canonical set only.

---

## 10. Scope fence (stop-test, applied)

**In scope (≥1 forcing case; reusable where ≥2):** per-(candidate+envelope) blind classification (§4, all four); deterministic context envelope (§3.2, cases 1+2); cited-union retention keyed to blind relevance (§5.1, all four); per-candidate semantic merge with per-field `agreement_by_field` (§5.2, all four); parameter-candidate comparison + coherent-single-candidate certification (§6, all four); `applicability_match` vs `qualification` separation (§6.2, cases 2+3); certified package with materialized semantic-support spans (§7.1, cases 1+2); completeness-gated terminal negatives (§6.3, all four); `charge_basis_components`/`charge_scope` compare (cases 1+2); `text_role`/`value_completeness`/`value_token_present` (cases 3+4); multi-candidate provisioning (§3.1, cases 1/3/4); Review-Needed/Gate-B seam (§7, all four); canonical-measurement rule (§9, all four).

**Explicitly OUT:** general §6 selector master spec; governed linked-span retrieval (§8.2); model-side responsiveness validation (§8.3); correlated-blind-spot mitigation beyond union-before-use (§8.4); candidate-generation/discovery (§3.1); section-boundary heuristics beyond parser-deterministic (§3.2); **multi-span joint satisfaction / any evidence composition (§8.6);** any evidence type beyond spans; wiring; any `cam/core/` change; any Gate B change; the basis-agreement threshold (§8.1).

---

## 11. What Part B will do (preview only — not written until Part A is ratified)

Standalone read-only harness (430 discipline: imports, does not modify), reusing `EVALUATOR_LINEUP_305` + `_call_single_evaluator_305` shape (real frozen panel; ~4 cases × 2 leases × N runs × 3 evaluators); generates deterministic envelopes; exercises the four cases; reports per evaluator × (candidate+envelope) the full §4.1 blind classification + candidate/context citations + real metadata + source-verification + `value_token_present`; merges per-candidate (§5) then per-parameter (§6); computes success over the **canonical (all-primary, semantic-refusals-kept) set only** (§9); measures **envelope sufficiency** (§8.2); states **in large, unfashionable letters** that it measures governed selection over a provisioned candidate set with local context, NOT candidate-generation recall.

**These two headings are kept strictly separate (per review #7), because collapsing them measures agreement with our answer key instead of whether CAM governed the judgment honestly.**

### 11.1 Mechanism success criteria (the pass/fail — architectural properties only)
These are the test. They hold regardless of *which* semantic answer the panel reached:
- No unverified span or unresolved cited quote ever enters selection.
- **No parameter is certified by cross-candidate attribute assembly** (no laundering).
- **No property is borrowed from a semantic-support span to cure a deficient primary** (§7.1).
- Disagreement (per-field) is preserved and visible, and non-unanimous certification is blocked under the no-implicit-majority rule.
- Incomplete candidate scope blocks certification; **no terminal document-level negative (`unsatisfied_*`) is emitted without completeness provenance** — the normal negative is `review_needed_no_qualifying_candidate`.
- The certified package carries materialized semantic-support spans, not a value-only parameter (§7.1).
- A complete audit artifact reconstructs each decision: candidate vs context citations distinct, per-candidate comparisons visible, per-panelist cited reasons retained.
- No live pipeline file consumes the harness output.

### 11.2 Forcing-case outcome observations (the empirical result — NOT pass/fail)
These are *observed and reported*, never used to define success. If all three models make the same honest semantic mistake, the mechanism has still succeeded (§11.1) — that outcome is a finding about the models, recorded, not a test failure:
- How the panel classified Atlas's 22.4% (observed `charge_basis_components`, and whether `basis_match` came out `mismatch` against the opex requirement).
- Whether the panel distinguished the Atlas base_rent definition stub (`value_completeness: cross_reference_only`/`no_value`) from a value-bearing schedule candidate (`self_contained`), and whether any single candidate qualified alone.
- Whether the panel classified Atlas's "approximately 3% per annum" aside as `text_role: narrative` vs Atreca's operative `Rent Adjustment Percentage: 3%`.
- Whether Atreca's known-good parameters produced a qualifying single candidate and certified.

These observations are the forcing-case reduction-to-practice results; §11.1 defines the governed-mechanism claim (NOT a semantic-correctness claim). Do not conflate them.

**Claim bound:** reduction-to-practice of governed semantic selection on these four cases only — not general accuracy, not correctness across leases, not elimination of correlated error, not readiness to wire, not closure of the §7-of-#26 semantic boundary.

---

## 12. Explicit non-authorization

Part A authorizes **nothing** — no code, no harness, no model calls, no wiring, no `cam/core/` change, no Gate B change, no patent-claim language. It is a ratified design. **Part A is RATIFIED (2026-07-19); Part B (the measurement instruction) is therefore unblocked to draft** — but Part B is itself a review artifact and authorizes no execution until it is separately ratified. Wiring remains blocked behind Gates A–D on both leases (423 §8).

---

*Part A v5 (final) — governed evidence-selection specification. Design only. RATIFIED 2026-07-19 by Tzvi (committed e702bf0). Doctrine: the panel judges candidates; the policy certifies parameters; context supports the judgment; completeness limits every negative claim. Part B unblocked to draft; Part B execution separately gated.*
