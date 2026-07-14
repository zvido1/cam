# Step 423 — Evidence Assignment Architecture Spec

**Date:** 2026-07-14
**Status:** SPEC — design only. No code. No runs. No baselines.
**Author:** Chat
**Supersedes:** nothing. `build_log/422_evidence_assignment_architecture_spec.md` was referenced in `NEW_THREAD_PROMPT.md` but was never written. 423 is the first architecture spec after 421C.
**Depends on:** nothing. 422A/422B (NOT_APPLICABLE hygiene) are independent and may land before or after. This spec declares its contract with that state in §9; it is not gated on it.

---

## 0. One-paragraph summary

Evidence assignment is destructive and exclusive. One Gemini call both **segments** the lease and **selects** which text represents each of 33 LPs, in one pass, with no verification that the right text landed in the right place. Material clauses reach exactly one bucket or none; the key-terms table (Tenant's Share 100%, Building's Share 45.79%, Rent Adjustment 3%) has reached **zero** evaluators across 101 Gemini-primary pipeline runs and all 3 Atlas runs. This spec replaces LP-owned text blobs with an evidence-first model: the lease is the evidence store, addressed by offset into a hashed canonical source; LPs **cite into** it; assignment is many-to-many, non-destructive, and source-traceable. Segmentation is separated from selection. Selection is governed by the frozen A/B/C panel, not by a single model. Global commercial parameters attach to dependent LPs **by declared rule**, not by model discretion. A completeness gate rejects any extraction in which a declared dependency is unsatisfied.

---

## 1. Why the current architecture fails

### 1.1 The failure, precisely

Per `build_log/421C_evidence_assignment_incident.md` and `build_log/422_code_status.md`:

- The key-terms table sits at char 1,994 of the Atreca source. It defines Tenant's Share (LP-07), Rent Adjustment Percentage (LP-02), and the Base Term (LP-03).
- Under Gemini extraction it lands in LP-00 (modal hash: nowhere at all), and **never** in LP-07.
- LP-00 carries `identity_check: true`. Its text is routed to `parse_identity_block()`, which returns `raw_tenant` and `identity_warnings`. **No evaluator reads it.**
- Therefore: the evaluators assessing Operating Expenses have never seen the percentage that quantifies the tenant's exposure. On either document. In any run.

This is not "some evaluations have lower confidence." It is a structural evidence hole that the system was **incapable of noticing**.

### 1.2 Three distinct failure classes (do not conflate)

| Class | Example | Root cause |
|---|---|---|
| **Parameter class** | Key-terms table never reaches LP-07/LP-02 | Cross-cutting parameters have no home in a per-LP partition |
| **Boundary-drift class** | LP-12 gets Landlord's Work access in one run, the Condition Precedent in another | Gemini redraws clause boundaries per run; neither run captures both |
| **Verifiability class** | Nothing checks that Gemini put the right text in the right LP | Segmentation and selection are fused in one unreviewed call |

**A fix that addresses only the parameter class leaves boundary-drift live.** This is the single most important scoping decision in this spec, and it is the reason §4 and §5 ship together.

### 1.3 What is NOT the cause

- **Not evaluator instability.** Grok is exonerated: its LP-07 `missing` verdicts were correct reports on evidence it had been denied.
- **Not truncation.** 421B raised the ceiling 32k→65k. Post-ceiling, Gemini still omits the table.
- **Not a prompt bug.** `prompts/provision_extraction_single_doc.txt` never instructs exclusivity. There is no `if already_assigned: skip` anywhere in the codebase.

### 1.4 Exclusivity is emergent — and this matters

There is no exclusivity *rule* to remove. Exclusivity is what the **task shape** produces: a generation asked to walk a list of 33 buckets and emit text for each will not repeat itself. The partition is a property of one-pass bucket-filling, not of an instruction.

**Consequence: a prompt change is an empirical bet, not a cheap fix.** "Tell Gemini it may assign a clause to multiple LPs" may help; it may not; it will not be *checkable* either way. This spec does not rely on it. Any prompt adjustment is a supplement to the architecture below, never a substitute.

### 1.5 The primitive already exists one layer down

`lease_coverage.py` builds `all_lp_texts` — a map of every LP's `tenant_text` — and injects it into Step 305 element prompts (Step 307b, cross-LP text injection). **The element layer is already many-to-many.** Only extraction is destructive. This is a reduction-to-practice fact, relevant to §11.

---

## 2. Doctrine

> **Evidence belongs to the lease. LPs cite into it. Evidence is never consumed by assignment.**

Corollaries:

1. **Segmentation ≠ selection.** The act of cutting the document into addressable units is structural and happens once. The act of deciding which units are relevant to which LP is a judgment, and judgments are governed.
2. **No model does its own bookkeeping.** Models propose text; deterministic code resolves, verifies, and attaches.
3. **Error asymmetry at the evidence layer is the inverse of the verdict layer.** At the verdict layer, minority disagreement must not be laundered into false consensus. At the evidence layer, minority *relevance* must not be excluded from the evaluator context. Over-inclusion costs tokens and noise; **omission produces a confident, unsupported, unfalsifiable verdict.** The merge rules differ because the error costs differ.
4. **A citation to text that was not in the evaluator's evidence context is not a citation.** Guardrail #2 ("citation or it didn't happen") is unenforceable unless the evidence context itself is verifiable.

---

## 3. Canonical source and evidence spans

### 3.1 Canonical source

The canonical source is **the output of the existing deterministic parser** (`lease_parser.parse_document`), hashed. One address space. Flat character offsets into that string.

```
source_document_hash : SHA-256 of canonical parsed text
canonical_text       : the addressable string
normalization_profile: "canonical_whitespace_v1" (declared, versioned)
```

**PDF/OCR is a known extension point, not designed here.** The current corpus is EDGAR `.txt`. Any future parser must be deterministic and hashable. Do not add a page/bbox address layer for a document class not currently ingested.

### 3.2 Evidence span

```
evidence_span_id      : EV-000123
source_document_hash  : <ties the span to a specific parse>
start_char            : 1994
end_char              : 2130
span_text             : "Tenant's Share of Operating Expenses of Building: 100% ..."
span_text_hash        : SHA-256[:16]
section_ref           : "Basic Lease Information / Key Terms"
normalization_profile : "canonical_whitespace_v1"
```

**Hard invariant:**

```
normalize(canonical_text[start_char:end_char]) == normalize(span_text)
```

or the span is **invalid** and must not enter any evidence set.

**Span identity includes `source_document_hash`.** A span whose hash does not match the current parse is invalid and is **never silently re-resolved**. Offsets are meaningless against a different parse; silent re-resolution would be span drift — the same bug family as everything else in this arc.

### 3.3 Why offsets, not "extracted text + section ref"

A section reference is too coarse to verify against. "Section 7" may contain several legally distinct things, may repeat, may be cross-referenced. A model can confidently name a section and hand back the wrong sentence, a paraphrase, or a version with the carve-out silently dropped — and nothing catches it. That is the current architecture.

An offset is checkable by code, deterministically, every run. It converts "did LP-07 receive the tenant share?" from an archaeology question into an assertion.

---

## 4. Layer 1 — Segmentation (Gemini proposes; code verifies)

**Role of Gemini: segmenter and span proposer. Nothing else.**

1. Gemini reads the canonical source and proposes spans as **verbatim quotes**, not offsets. (Models cannot count characters; asked for an offset, a model will produce a plausible number that points nowhere. Never accept a model-emitted offset.)
2. **Deterministic code resolves each quote against the hashed canonical source** and assigns offsets.

Three outcomes:

| Outcome | Condition | Handling |
|---|---|---|
| `verified` | quote matches exactly one location | span created |
| `ambiguous` | quote matches >1 location | disambiguate by nearest section anchor; if still ambiguous → `unverified` |
| `unverified` | no exact match | span **rejected**; not usable in canonical Stage 5 |

**`unverified` spans are fail-closed.** They do not reach evaluators. This is the same doctrine as the evaluator guard (414) and the extraction guard (421B), applied to a third surface.

**Segmentation produces no LP assignment.** Its only output is a set of addressable, verified spans — the *span universe*. The document is not cut into buckets. Nothing is consumed.

---

## 5. Layer 2 — Global parameter block (attached by rule)

### 5.1 The named parameter set

Key terms are **not one LP's clause text**. They are document parameters that many LPs depend on. They must be extracted as a first-class, **named** structure — never as a provision.

```
parameters:
  tenant_share            : "100%"          → span EV-000011
  building_share          : "45.79%"        → span EV-000011
  rent_adjustment_pct     : "3%"            → span EV-000011
  base_rent               : ...
  commencement_date       : ...
  premises_sqft           : ...
  term_length             : ...
  permitted_use           : ...
```

Each parameter carries a **verified span** and its value. Parameters with no verified span are `unresolved` and are reported, not silently absent.

### 5.2 The dependency map

The taxonomy declares, per LP, which parameters that LP's assessment depends on:

```
LP-02 (Rent/Escalation)      depends_on: [base_rent, rent_adjustment_pct]
LP-07 (Operating Expenses)   depends_on: [tenant_share, building_share]
LP-03 (Term/Commencement)    depends_on: [commencement_date, term_length]
LP-05 (Permitted Use)        depends_on: [permitted_use]
...
```

### 5.3 Attachment is deterministic

**Code attaches parameter spans to dependent LPs. No model discretion. Every run.** The model is never asked to remember to include the tenant share in LP-07 — so it cannot forget.

This is what makes the completeness gate (§8) *enforceable* rather than merely *violable-and-detected*. Offsets alone would let you prove the table never reached LP-07 — beautifully hashed evidence of the identical failure. The dependency map is what makes it **arrive**.

### 5.4 LP-00 collision

LP-00 (`identity_check: true`) routes to `parse_identity_block()`, whose output no evaluator reads. **The parameter block must never be filed into LP-00.** LP-00 remains identity/metadata. Parameters are a separate structure with a separate lifecycle. Identity metadata and commercial parameters are different concepts and must not share a container.

---

## 6. Layer 3 — Panel-governed selection

### 6.1 The panel

The frozen evaluator panel (A = claude-sonnet-4-6, B = gpt-5.5, C = grok-4.3) votes **span → LP relevance** over the fixed span universe from §4.

**Gemini is not a selector.** It segments; it does not also get a governance vote on what its own cuts mean. The model that creates the span universe must not also adjudicate the relevance of the units it created.

**The selectors do not re-extract.** They vote over span IDs. There is no second segmentation, no competing partition, no text to reconcile. This is why §4 must land first: without a common addressable span universe, three models "selecting evidence" produces three incompatible partitions and reintroduces the drift being eliminated.

### 6.2 Cited union merge

```
A span enters LP-X's evidence set if at least ONE selector asserts relevance
with a trace that survives validation.
```

**Union, not majority** — per the error asymmetry (§2.3). A span wrongly included costs tokens. A span wrongly withheld produced this entire incident.

**Cited, not bare** — a bare vote is a popularity number: uncheckable, and indistinguishable from a lucky guess. A cited assertion is falsifiable.

### 6.3 When reasons are required

| Case | Reason required? |
|---|---|
| Unanimous inclusion (3/3) | No — cheap path |
| Contested inclusion (1/3, 2/3) | **Yes — the asserting selector must justify** |
| Contested *withholding* (a selector excludes a span the others include) | **Yes — the dissent is as informative as the inclusion** |

This focuses the expensive path exactly where the information is.

**But: unanimity is never a substitute for a satisfied dependency.** Three models can agree for the same wrong reason — correlated error is precisely when agreement stops being evidence. The completeness gate (§8) checks *declared dependencies*, not *votes*. A unanimous span set that leaves `tenant_share` unattached to LP-07 still fails.

### 6.4 Selector support is provenance, not an exclusion rule

Record per span-LP pair: `selector_support: 1/3 | 2/3 | 3/3` and the cited reasons. This is an audit field and a signal for review routing. **It never removes evidence.**

### 6.5 Correlated blind-spot risk (named, mitigated, not solved)

Reusing the verdict panel as the selection panel creates a real risk: if Claude selects the evidence and Claude also evaluates it, a systematic blind spot is invisible — Claude never sees what it did not pick.

**Mitigation:** union merge happens *before* evaluation. **No role ever evaluates only its own selected evidence.** If Grok alone flags a span for LP-07, Claude and GPT both see it at evaluation time. The minority selector is not silenced.

**Residual risk, stated:** all three could share an omission. An independent selector lineup would be cleaner but creates a new frozen panel, new validation burden, new cost, and another surface for declared-state ≠ actual-state. Not built now. Revisit if shared omissions are observed.

**Model-count constraint:** there are not enough independent frontier models to staff a separate selector panel without degrading it. Reuse is a resource fact, not only a design preference.

---

## 7. Layer 4 — Trace validation

Split by what can be decided deterministically:

### 7.1 Structural validation → CODE (not a model)

- Does every cited span resolve to real text at its offsets in the hashed source?
- Does `normalize(canonical_text[start:end]) == normalize(span_text)`?
- Does every declared parameter dependency have an attached verified span?
- Did every non-unanimous assertion carry a non-empty reason?
- Does every span's `source_document_hash` match the current parse?

**These are not judgments. They must not be delegated to a model.** Handing a deterministic check to an LLM converts a certain answer into a probabilistic one. This is what makes the gate a gate.

### 7.2 Responsiveness validation → GEMINI (narrow, non-discretionary)

Gemini's only other role: does a stated reason **actually address** the span it cites and the LP it claims relevance to? This is *responsiveness*, not *correctness* — a much thinner judgment.

**Critical asymmetry:**

> **A failed trace kills the TRACE, not the EVIDENCE.**

A span with a non-responsive reason routes to **Review Needed**. It is **not silently dropped**. Gemini may invalidate a justification; it may never invalidate evidence. Omission is fatal; over-inclusion is cheap. If Gemini could remove spans, it would be a single ungoverned model with veto power over the panel's output — an *arbiter* rather than a *selector*, which is worse than what we have now.

### 7.3 Stated limitation

> **A responsive reason can still be wrong.**

The trace validator catches reasons that do not address their span. It does **not** catch reasons that are plausible, well-formed, on-topic, and false. This is a new model output and therefore a new surface for the same bug family this project has been chasing all year. It is recorded here so it is not discovered as Step 440.

---

## 8. Acceptance protocol (hard gates)

**No baseline, no Stage 5 stabilization, and no Priority Exposure work until ALL of the following pass, on BOTH Atreca and Atlas.**

### Gate A — Structural integrity
- Every span in every LP evidence set is `verified` against the hashed canonical source.
- Zero `unverified` spans reach any evaluator.
- Every span's `source_document_hash` matches the run's parse.

### Gate B — Completeness (THE GATE THAT WOULD HAVE CAUGHT THIS)
- **Every declared parameter dependency is satisfied by a verified span in the dependent LP's evidence context, or the extraction is REJECTED.**
- Specifically: `tenant_share` and `building_share` present in LP-07's context; `rent_adjustment_pct` present in LP-02's context.
- **Keyed to declared dependencies, NOT to literal strings.** The gate must not grep for `"45.79%"` — that value is Atreca-specific and worthless on the next lease. The rule is "every declared dependency has a verified span," which generalizes.

### Gate C — Assignment stability (the boundary-drift class)
- Across N≥5 runs, the LP-12 class does not flip between substantively different clauses.
- Both the Condition Precedent **and** the Landlord's Work access rights are present in LP-12's evidence set, because both are relevant and evidence is not consumed.
- Material span-set variance across runs is reported, not averaged away.

### Gate D — Regression
- Full test suite green (94/94 at time of writing, plus new tests).

**Stability was never the problem. Completeness was.** A stable, reproducible, hash-identical extraction that omits the tenant share is not an improvement over an unstable one. Gate C without Gate B is a trap.

---

## 9. Contract with NOT_APPLICABLE (422A/422B)

An LP may legitimately have no evidence. That state must be distinguishable from evidence failure — that is 422A/422B's job, not this spec's.

The contract 423 assumes:

- An LP marked `NOT_APPLICABLE` is **exempt from Gate B** for parameters it does not declare.
- An LP that is **not** `NOT_APPLICABLE` and has an unsatisfied declared dependency **fails Gate B**. No exceptions.
- `NOT_APPLICABLE` must never be derivable from "no span was selected." Absence of selection is not evidence of inapplicability — that inversion is exactly how a silent evidence hole becomes a confident finding.

Once spans are addressable, this gets simpler: "no span was proposed for LP-23" and "spans exist but none selected" become distinguishable, which they currently are not. That is a **future simplification**, not a prerequisite.

---

## 10. Alternatives considered and rejected

### 10.1 Give evaluators the full lease — REJECTED as the canonical architecture

The intuitive move: skip the span machinery, put the whole lease in every evaluator's context. If LP-07's evaluators had the full lease, they would have had the table.

**Rejected for three reasons:**

1. **It destroys the audit trail.** If a verdict is formed over the whole document, the system cannot say which evidence supported it, which was considered and rejected, or whether a required parameter was used at all. That collapses CAM into ordinary ungoverned LLM review — "the model read it and formed a view" — which is precisely the behavior CAM exists to replace. It would fix an evidence-*completeness* bug by discarding evidence *governance*. That is the one trade this project cannot make.

2. **It does not make completeness checkable.** The current failure was silent because nothing could mechanically ask "did LP-07 receive the tenant share?" Full-lease context makes that failure *less likely*, not *more observable*. There would be no gate, no rejection, no proof — only hope.

3. **Availability is not attention.** A model holding 130k chars does not reliably use all of them. Long-context recall degrades, especially for a single table row on page 1 when the question concerns a clause on page 40. Expect the bug to reproduce at a lower rate with **worse** diagnosability. That is a governance downgrade.

**Canonical rule:** evaluator verdicts must be formed over a **named, bounded, source-traceable** evidence set. The set may be broad. It must be enumerable, hashable, and auditable.

### 10.2 Full-lease as segmentation-completeness backstop — RETAINED, secondary

The panel can only vote on spans that exist. If the segmenter never proposed a span, no selector can rescue it.

A full-document pass may therefore audit the **span universe**: *"Here is the lease. Here are the spans proposed. Is material text unproposed?"* Its output is a claim about **coverage of the span universe** — never a verdict about the lease.

**Demoted, deliberately.** Once panel selection exists, a single full-lease auditor asking "is anything missing?" is just one more ungoverned model opinion — the same failure class, relocated. It is a **backstop for segmentation completeness**, not the primary mechanism of evidence assignment.

### 10.3 Prompt-only fix — REJECTED
See §1.4. There is no exclusivity rule to remove; exclusivity is produced by the task shape. A prompt change is unverifiable and unenforceable.

### 10.4 Freeze one extraction hash — REJECTED
Per 421C §6. Freezing either post-ceiling hash imports one run's nondeterministic assignment choices into all downstream evaluation, permanently. Caching does the same thing and makes the incompleteness durable.

### 10.5 Bounded neighborhood expansion — DEFERRED, not rejected
Evaluators could receive assigned spans **plus** a declared neighborhood (containing section, cross-referenced definitions, adjacent carve-outs). This stays governed: the set remains named, addressed, and hashed. It is a **width knob to tune empirically after 423 lands**, not part of the initial architecture.

---

## 11. Patent framing

**The finding does not weaken the claim. It extends it.**

CAM's contribution is governed assertion over a frozen evaluator panel with structured evidentiary constraints. 421C establishes that **the evidentiary input to the panel must be governed with the same rigor as the panel itself**. Governed evidence capture is the natural extension of "citation or it didn't happen" (Guardrail #2) from the evaluator layer to the extraction layer.

**What is novel here — and it is not the hashing:**

1. **Separation of segmentation from selection.** The unit-creation act and the relevance-judgment act are distinct, and only the second is a judgment requiring governance.
2. **Panel-governed evidence selection.** Multiple independent selectors assert span→LP relevance with cited traces; disagreement is preserved as provenance; the merge is union because the error asymmetry inverts at this layer. This is CAM's own doctrine applied one layer earlier than it has been applied before.
3. **Declared-dependency completeness gating.** Evidence sufficiency is checked against a declared dependency map, not against agreement. **Agreement is not sufficiency.**
4. **The asymmetric merge rule itself.** Minority relevance is *included* at the evidence layer for the same reason minority verdicts are *preserved* at the verdict layer: in both cases, suppressing the minority manufactures false confidence. The mechanics differ because the error costs differ. This is one principle, two instantiations.

**Reduction-to-practice already in the record:** cross-LP text injection at the element layer (Supplement #05-12, `all_lp_texts`, Step 307b). Non-exclusive assignment at the extraction layer is the corresponding claim at the extraction layer.

**What CAM will be able to assert after 423:**
> The evidence context presented to each evaluator is complete against a declared parameter set, source-traceable to a hashed canonical document, and non-destructively assigned.

**What CAM will NOT be able to assert after 423 — state this plainly, do not blur it:**
> That the semantic selection is correct. The panel may agree on the wrong spans. A responsive reason may be false. Structural verifiability is closed; semantic verifiability is scoped and open.

Blurring those two in a section that *sounds* resolved is worse than leaving the second open, because the patent framing turns on which one is being claimed.

---

## 12. What is explicitly out of scope

- Any `cam/core/` change, including the `response_schema` question (422 Decision 2). That requires separate authorization and must not ride in on a spec.
- Model swaps. A=claude-sonnet-4-6, B=gpt-5.5, C=grok-4.3 stay frozen; the swap question was settled empirically.
- Any pipeline run, baseline, or benchmark.
- Priority Exposure, Stage 5 stabilization, canonical CRX identity keys — all remain blocked behind Gate B and Gate C.
- PDF/OCR address layers.
- An independent selector panel (see §6.5).

---

## 13. Implementation sequence (for a future step — NOT authorized here)

Implementation may be phased. **Acceptance may not.** No baseline is trusted until Gates A–D pass together; shipping the parameter fix alone and declaring victory leaves boundary-drift live and puts us back here in a month.

1. Canonical source + span resolution + structural verification (§3, §4)
2. Parameter extraction + dependency map + rule-based attachment (§5)
3. Panel-governed selection + cited union merge (§6)
4. Trace validation, structural then responsiveness (§7)
5. Gates A–D (§8)
6. Only then: re-baseline

---

*Spec only. No code written. No runs executed. No baselines established.*
