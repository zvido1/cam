# Patent Supplement — Governed Evidence Capture and Governed Evidence Selection

**Supplement #26**
**Date:** 2026-07-14
**Status:** MIXED — see §8. Conception documented and dated. Reduction to practice PARTIAL.
**Sources:** `build_log/421C_evidence_assignment_incident.md`; `build_log/422_code_status.md`; `build_log/422A_gate3_not_applicable_hygiene.md`; `build_log/422B_not_applicable_wiring.md`; `build_log/422C_wire_extraction_completeness_gate.md`; `build_log/422D_fix_canonicality_source.md`; `build_log/423_evidence_assignment_architecture_spec.md`; `build_log/423A_verified_evidence_span_substrate.md`

---

## 1. The Discovery

**A governed evaluator panel can be made to answer the wrong question by an ungoverned evidence layer, and CAM had no way to detect this.**

Step 421C established the following, by direct artifact inspection rather than inference:

The Atreca lease contains a key-terms table at character 1,994 of the source document. It specifies Tenant's Share of Operating Expenses of Building (100%), Building's Share of Project Operating Expenses (45.79%), and Rent Adjustment Percentage (3%). These are the quantitative parameters that determine the tenant's actual financial exposure under the Operating Expense and Rent Escalation provisions.

That table did not appear in any LP's extracted evidence context in **any** of the 101 known Gemini-primary pipeline runs, nor in **any** of the three Atlas `pipeline_results.json` files. When it appeared at all, it landed in LP-00 (Parties & Premises), which carries `identity_check: true` in the provision taxonomy and whose text is routed to an identity struct that no evaluator reads for coverage purposes.

The evaluators assessing LP-07 (Operating Expenses) had therefore never seen the percentage that quantifies the mechanism they were assessing. Not on the fixture. Not on the validation corpus. Not once.

**The failure was silent.** No gate fired. No confidence was reduced. No provenance field recorded an absence. The system produced a confident coverage verdict on a provision whose operative parameter had been structurally excluded from the evidence it reasoned over. Nothing in the architecture was capable of noticing.

### 1.1 The mechanism

The extraction layer asked a single model, in a single pass, to walk a list of 33 provision buckets and emit the text belonging to each. A generation performing that task does not repeat itself: once a clause is emitted into one bucket, it is not emitted into another.

This exclusivity is **emergent, not instructed.** No prompt directs it. No code enforces it. There is no `if already_assigned: skip` anywhere in the system. The partition is a property of the *task shape* — of asking one model to fill N buckets in one pass — not of any rule that could simply be removed.

Three failure classes follow, and they are distinct:

| Class | Instance | Cause |
|---|---|---|
| **Parameter class** | Key-terms table never reaches LP-07 or LP-02 | Cross-cutting parameters have no home in a per-provision partition |
| **Boundary-drift class** | LP-12 receives Landlord's Work access rights in one run and a Condition Precedent in another | Clause boundaries are redrawn per run; neither run captures both |
| **Verifiability class** | Nothing checks that the right text reached the right provision | Segmentation and selection are fused in one unreviewed model call |

### 1.2 What this cost

Three consequences, each recorded honestly:

**The numeric baselines from Steps 417, 419, and 420 are void as system-performance baselines.** They measured evaluator behavior over evidence contexts that were structurally incomplete on the provisions being measured. They remain valid as diagnostic artifacts. They are not measurements of the system.

**An evaluator was wrongly blamed.** Role C (Grok) was identified across Steps 417–420 as a high-variance evaluator producing anomalous `missing` verdicts on LP-07. Grok was **correct.** It was faithfully reporting on evidence it had been denied. The variance attributed to model instability was the correct response of a competent evaluator to an incomplete evidence context. *An ungoverned evidence layer does not merely produce wrong answers — it produces wrong diagnoses of the evaluators.*

**The attorney validation is scoped, not invalidated.** The three CRE attorneys' reactions to the output they reviewed are genuine professional reactions. But that output was produced without the LP-07 quantitative parameters in scope, so the panel cannot be cited as validation of CAM's Operating Expense coverage analysis specifically. The same scoping applies to LP-02 (the 3% rent adjustment parameter).

---

## 2. The Doctrinal Consequence

> **Guardrail #2 — "citation or it didn't happen" — is unenforceable if the evidence context itself is unverified.**

A citation to a clause that was not in the evaluator's evidence context is not a valid citation. CAM's central constraint on assertion has, until now, been enforced *downstream* of an ungoverned step. The framework governed the conclusion and left the premise unexamined.

The correction is not a patch. It is the recognition that **the evidentiary substrate must be governed with the same rigor as the evaluator panel** — and that CAM's own doctrine, applied one layer earlier, is the mechanism for doing so.

**Canonical formulation:**

> CAM governs not only the conclusions drawn, but the evidentiary substrate from which conclusions are drawn. It refuses to produce a clean verdict when the evidence required for that verdict is absent, unverified, or contested. Disagreement and provenance are preserved at the evidence-selection layer for the same reason they are preserved at the evaluator-verdict layer.

---

## 3. Contribution 1 — Separation of Segmentation from Selection

**The architectural insight, and the one from which the rest follows.**

The prior architecture fused two acts in one model call:

- **Segmentation** — cutting the document into addressable units. A *structural* act.
- **Selection** — deciding which units are relevant to which provision. A *judgment*.

Fusing them means the judgment is unreviewable, because the units over which it was made do not persist. There is nothing to disagree about, nothing to cite, nothing to audit. The model's partition *is* the answer, and it is the only artifact.

CAM separates them:

1. **Segment once.** Produce a set of addressable, hashed, source-verified spans. This layer performs **no provision assignment.** It does not know what a provision is.
2. **Select over the fixed span universe.** Relevance of span → provision is a judgment, and judgments are governed.
3. **Evaluate** over the resulting evidence set.

**Why this is the enabling move:** only once a common span universe exists can multiple evaluators be asked to *disagree about the same thing.* Three models each performing their own segmentation produce three incompatible partitions — there is no shared referent, and no governance is possible over the result. Separation of segmentation from selection is what makes evidence selection *governable at all.*

---

## 4. Contribution 2 — Governed Evidence Capture (Structural)

Evidence is addressed, not copied.

- **Canonical source.** The deterministic parser's output, hashed. One address space. Flat character offsets.
- **Evidence spans.** Offset-addressed references into that source, carrying `source_document_hash`, `canonical_text_hash`, `start_char`, `end_char`, `span_text`, `span_text_hash`, a declared and versioned `normalization_profile`, and a `verification_status`.
- **Hard invariant.** `normalize(canonical_text[start_char:end_char]) == normalize(span_text)`, or the span is not verified.
- **Models propose; code resolves.** The model returns **verbatim quotes**, never offsets. A model asked for a character offset produces a plausible number that points nowhere. Deterministic code locates the quote in the hashed source and assigns the offsets. **The offset is never a model claim.** It is a derived fact.
- **Three verification states.** `verified` (resolves uniquely) / `ambiguous` (resolves to more than one location; never silently promoted) / `unverified` (does not resolve; **fail-closed — may not reach canonical evaluation**).
- **Span identity includes the source hash.** A span whose `source_document_hash` does not match the current parse is invalid and is **never silently re-resolved.** Offsets are meaningless against a different parse; silent re-resolution would be span drift.

This is the third surface on which CAM's fail-closed doctrine now operates: evaluator identity (Step 414), extraction integrity (Step 421B), and now span verification.

---

## 5. Contribution 3 — Declared-Dependency Completeness Gating

**Agreement is not sufficiency.**

Key commercial terms are not "one provision's clause text." They are **document parameters** on which many provisions depend. CAM extracts them as a named, first-class structure — never as a provision — and declares, per provision, which parameters that provision's assessment requires:

```
LP-02 (Rent / Escalation)     depends_on: [base_rent, rent_adjustment_pct]
LP-07 (Operating Expenses)    depends_on: [tenant_share, building_share]
LP-03 (Term / Commencement)   depends_on: [commencement_date, term_length]
```

**Attachment is deterministic.** Code attaches the parameter's verified span to every dependent provision, on every run. The model is never asked to remember to include the tenant share in LP-07 — and therefore cannot forget.

**The gate:** every declared dependency must be satisfied by a verified span in the dependent provision's evidence context, or **the extraction is rejected and no analysis is produced.**

Two properties of this gate are load-bearing:

**It is keyed to declared dependencies, not to literal values.** The gate does not search for `"45.79%"`. That string is specific to one lease and worthless on the next. The rule — *every declared dependency has a verified span* — generalizes across documents.

**It is orthogonal to evaluator agreement.** Three evaluators can agree for the same wrong reason; correlated error is precisely the condition under which agreement stops being evidence. The gate checks *dependencies*, never *votes*. A unanimous evidence set that leaves `tenant_share` unattached to LP-07 still fails.

This is the check that would have caught the defect on day one, and its absence is why the defect survived 101 runs.

---

## 6. Contribution 4 — Panel-Governed Evidence Selection, with an Asymmetric Merge Rule

**This is the strongest claim in this supplement, and it is CAM's own doctrine applied one layer earlier than it has previously been applied.**

The frozen evaluator panel (A = Anthropic, B = OpenAI, C = XAI) votes on **span → provision relevance** over the fixed span universe. Each asserts, with a cited reason where contested. The segmenting model does not vote: **the model that creates the units does not also adjudicate what its own cuts mean.**

### 6.1 The merge rule inverts, and the inversion is principled

At the **verdict** layer, CAM's rule is: *the minority is never silenced.* A dissenting verdict is preserved; disagreement is not laundered into false consensus (Guardrails #1, #18).

At the **evidence** layer, the rule is: *minority relevance is never excluded.* If any selector asserts, with a surviving trace, that a span is relevant to a provision, the provision receives it. The merge is **cited union**, not majority.

**These are the same principle. The mechanics differ because the error costs differ:**

| Layer | Error of commission | Error of omission | Merge rule |
|---|---|---|---|
| **Verdict** | Asserting a finding that is wrong → one spurious flag, visible, correctable by the lawyer | Suppressing a finding that is right → **a real risk goes unmentioned** | Preserve the minority |
| **Evidence** | Including a span that is irrelevant → tokens and noise, visible, harmless | Excluding a span that is material → **a confident verdict built on a hole, invisible, unfalsifiable** | Include the minority |

In both cases, suppressing the minority manufactures false confidence. In both cases, the framework refuses. The *direction* of the protective action inverts because the asymmetry of harm inverts.

**Canonical formulation:**

> At the verdict layer, minority disagreement must not be laundered into false consensus. At the evidence layer, minority relevance must not be excluded from the evaluator's context. The merge rule differs because the error asymmetry differs: over-inclusion of evidence costs tokens and noise; omission of evidence produces a confident, unsupported, unfalsifiable verdict.

### 6.2 Cited, not bare

A bare vote — "2 of 3 selectors think this span is relevant to LP-07" — is a popularity number. It is uncheckable, and it is indistinguishable from a lucky guess.

CAM requires a **cited relevance assertion** for contested spans: *"this span is relevant to LP-07 because it supplies the Tenant's Share percentage that the LP-07 clause references but does not quantify."* That is falsifiable. It can be validated. It is evidence rather than a poll.

**Reason economics.** Unanimous inclusions require no reason — the information content is low and the cost is real. **Contested inclusions require a reason. Contested *withholdings* also require a reason** — a selector who excludes a span the others include is asserting something, and the dissent is as informative as the inclusion. The expensive path is spent precisely where the information is.

This is the auditor lineage (Supplement #24) applied to evidence: *an assertion does not survive on the strength of the answer alone; its trace must hold.* The selection layer is not a vote. It is a **constrained assertion** — which is the name of the method.

### 6.3 Trace validation, and what may kill what

Structural checks are performed by **code**, not by a model: does the span resolve; does the invariant hold; is the dependency satisfied; is a reason present where required. These are not judgments and must never be delegated to a model, because handing a deterministic check to an LLM converts a certain answer into a probabilistic one.

A model may check only **responsiveness** — does a stated reason actually address the span it cites and the provision it claims relevance to? This is a far thinner judgment than relevance.

**The asymmetry that protects the architecture:**

> **A failed trace kills the TRACE, not the EVIDENCE.**

A span whose reason fails responsiveness validation routes to **Review Needed**. It is not silently dropped. A validator may invalidate a *justification*; it may never invalidate *evidence*. Were it able to remove spans, it would be a single ungoverned model holding veto power over the panel's output — an *arbiter* rather than a *selector*, and a worse failure than the one being fixed.

### 6.4 Correlated blind spots (named, mitigated, not solved)

Reusing the verdict panel as the selection panel creates a real risk: if a model selects the evidence and also evaluates it, a systematic blind spot is invisible — it never sees what it did not pick.

**Mitigation:** union merge occurs *before* evaluation. **No role ever evaluates only the evidence it selected.** If C alone flags a span for LP-07, A and B both see it at evaluation time. The minority selector is not silenced downstream.

**Residual risk, stated:** all three may share an omission. An independent selector lineup would be cleaner but creates a second frozen panel, a second validation burden, and another surface on which declared state may diverge from actual state. It is not built. It is revisited if shared omissions are observed.

---

## 7. Structural vs Semantic Verifiability — the Boundary, Stated Plainly

**Do not blur this. The claim scope depends on which is being asserted.**

**Structural verifiability — closed by this architecture:**
- Every span cited by a provision exists verbatim in the hashed canonical source at its claimed offsets.
- Every declared parameter dependency is satisfied by a verified span, or the run is rejected.
- Every evaluator's evidence context is enumerable, hashable, and attributable to a specific source parse.
- No evaluator reasons over evidence that cannot be traced to the document.

**Semantic verifiability — scoped, and OPEN:**
- Whether the segmenter proposed the *right* spans.
- Whether the panel selected the *right* spans for each provision.
- Whether a stated reason, though responsive, is *true*.

**A responsive reason can still be wrong.** The trace validator catches reasons that fail to address their span. It does not catch reasons that are plausible, well-formed, on-topic, and false. This is a new model output and therefore a new surface for the same failure family this project has been tracking. It is recorded here rather than discovered later.

**What CAM may claim after this architecture is built:**

> The evidence context presented to each evaluator is complete against a declared parameter set, source-traceable to a hashed canonical document, and non-destructively assigned.

**What CAM may NOT claim:**

> That the semantic selection is correct.

Panel-governed selection with cited traces *raises the cost* of a shared semantic error and *makes it auditable*. It does not eliminate it. A claim to perfect semantic evidence assignment would be false, and a supplement that blurred the two would be worse than one that left the second honestly open.

---

## 8. Implementation Status — Precise

**Read this section before citing anything in this supplement.**

| Component | Status | Evidence |
|---|---|---|
| Evaluator identity freezing, fail-closed fallback | ✅ **RTP** | Step 414; 52 tests |
| Evaluator config integrity assertion | ✅ **RTP** | Step 416; 32 tests |
| Extraction integrity guard; fail-closed on primary failure; evidence hashes | ✅ **RTP** | Step 421B; 10 tests |
| `NOT_APPLICABLE` distinguished from evidence failure (schema) | ✅ **RTP** | Step 422A |
| `NOT_APPLICABLE` wired end-to-end through coverage | ✅ **RTP** | Step 422B; 23 tests |
| Completeness gate wired into live pipeline; canonical mode aborts before evaluation on missing required evidence | ✅ **RTP** | Step 422C; 8 tests; spy test confirms Stage 5 never invoked |
| Canonicality recorded explicitly, not inferred | ✅ **RTP** | Step 422D; 10 tests |
| **Verified evidence-span substrate** (canonical hashed source; offset addressing; three-state verification; fail-closed on unverified) | ✅ **RTP — module built and tested; NOT wired into the live pipeline** | Step 423A; 19 tests; `lease_evidence_spans.py` |
| LP-blind span proposal layer | 🔨 **IN BUILD** | Step 423B |
| Global parameter block + declared dependency map | 📐 **DESIGNED, NOT BUILT** | 423 spec §5 |
| Panel-governed selection; cited union merge | 📐 **DESIGNED, NOT BUILT** | 423 spec §6 |
| Trace validation (structural / responsiveness split) | 📐 **DESIGNED, NOT BUILT** | 423 spec §7 |
| Completeness gate on declared dependencies (Gate B) | 📐 **DESIGNED, NOT BUILT** | 423 spec §8 |

**Total test suite: 229 passing as of Step 423A.**

**Critical status statements — do not soften these:**

1. **The defect is not yet fixed.** LP-07's evaluators still cannot see the 100% tenant share. Steps 422A–D make the failure *loud* rather than *silent* — a precondition for trusting any future measurement, not a substitute for one.

2. **No performance baseline exists, and none may be cited.** Steps 417/419/420 are void as system baselines. No replacement has been measured, and none may be measured until the evidence-assignment architecture is corrected and Gates A–D pass on both Atreca and Atlas.

3. **Conception is documented and dated.** The 421C incident report (2026-07-13) and the 423 architecture specification (2026-07-14) are on disk, committed, and predate implementation of the layers they describe. The architecture was designed in advance and articulated as a phased plan — the same spec-then-build sequencing established for Supplement #21.

4. **Reduction to practice is partial and phased.** The structural substrate is built. The governance layers above it are designed. This supplement documents conception in full and RTP where it exists, and says which is which in every case.

---

## 9. Relation to the Existing Record

**This extends existing doctrine; it does not contradict it.**

- **Guardrail #2 (citation or it didn't happen)** — extended upstream. The citation requirement is vacuous unless the evidence context is verifiable.
- **Guardrail #1 / #18 (minority never silenced; the valid minority trace)** — the merge asymmetry of §6.1 is these guardrails applied at a new layer, with the direction of protection inverted by the inversion of error cost. Same principle, second instantiation.
- **Supplement #24 (auditor lineage; validity gate before routing)** — the cited-trace requirement on contested spans is the auditor doctrine applied to evidence selection. An assertion survives because its trace holds, not because it was made.
- **Supplement #05-12 (cross-LP text injection, `all_lp_texts`, Step 307b)** — **already reduced to practice at the element layer.** The element layer has been many-to-many since Step 307b. Non-exclusive assignment at the extraction layer is the corresponding claim at the extraction layer. The primitive existed one layer down; the extraction layer was the only destructive step in the pipeline.
- **Guardrail #5 (`cam/core/` untouched)** — preserved. All of this is adapter-layer.

---

## 10. Patent Sentences

> "CAM governs not only the conclusions drawn by its evaluator panel, but the evidentiary substrate from which those conclusions are drawn. A governed panel reasoning over an ungoverned evidence layer can be made to answer the wrong question with full confidence and no detectable failure — and the framework will attribute the resulting variance to its evaluators rather than to the evidence they were denied."

> "The act of cutting a document into addressable units and the act of judging which units are relevant to which question are structurally distinct. The first is mechanical and is performed once; the second is a judgment and is therefore governed. Fusing them in a single model call renders the judgment unreviewable, because the units over which it was made do not survive it."

> "Evidence belongs to the document; provisions cite into it. Evidence is not consumed by assignment. The same source span may support any number of provisions simultaneously, because relevance is not a partition."

> "At the verdict layer, minority disagreement must not be laundered into false consensus. At the evidence layer, minority relevance must not be excluded from the evaluator's context. These are the same principle: suppressing the minority manufactures false confidence. The mechanics invert because the error costs invert — over-inclusion of evidence costs tokens; omission of evidence produces a confident, unsupported, unfalsifiable verdict."

> "Evidence sufficiency is checked against a declared dependency map, never against evaluator agreement. Three evaluators may agree for the same wrong reason; correlated error is precisely the condition under which agreement ceases to be evidence. Agreement is not sufficiency."

> "The model proposes verbatim quotations; deterministic code resolves them against a hashed canonical source and assigns the offsets. The offset is therefore never a model claim but a derived fact — and a proposed quotation that does not resolve to the source is not evidence, and does not reach an evaluator."

> "A failed trace kills the trace, not the evidence. A validator may invalidate a justification; it may never invalidate the underlying evidence. Were it able to, it would be a single ungoverned model holding veto power over a governed panel — an arbiter rather than a selector, and a worse failure than the one it was introduced to correct."

> "A responsive reason can still be wrong. CAM closes structural verifiability — every span an evaluator reasons over is traceable to a specific hashed parse of the source document, and every declared dependency is satisfied or the analysis is refused. It does not close semantic verifiability, and it does not claim to."

---

## 11. Canonical Examples

| Example | Demonstrates |
|---|---|
| **The Atreca key-terms table (char 1,994; Tenant's Share 100%, Building's Share 45.79%, Rent Adjustment 3%)** | The parameter class of evidence failure. Zero hits across 101 Gemini-primary runs and 3 Atlas runs. Routed to LP-00 (`identity_check: true`), whose text no evaluator reads for coverage. The evaluators assessing Operating Expenses never saw the percentage that quantifies the exposure. **A governed panel answering the wrong question, silently.** |
| **Grok's LP-07 `missing` verdicts (Steps 417–420 → exonerated 421C)** | An ungoverned evidence layer does not merely produce wrong answers — **it produces wrong diagnoses of the evaluators.** Role C was correct; it was reporting faithfully on evidence it had been denied. Variance attributed to model instability was a competent evaluator's correct response to an incomplete context. |
| **LP-12 boundary drift (Landlord's Work access rights vs. Condition Precedent)** | The boundary-drift class, distinct from the parameter class. Different runs route *substantively different clauses* to the same provision; neither run captures both. **Demonstrates why a parameter-block fix alone is insufficient** — it addresses one failure class and leaves the other live. |
| **The fabricated "Controllable Expenses Cap" (2026-07-14)** | **The reporting layer is a model output too.** An analysis step, asked what differed between two extractions, described what an Operating Expenses section *usually contains in commercial leases generally* — including a Controllable Expenses Cap that **does not exist in this lease** — and formatted the inference as an observation. The claim hardened across three documents (build report → incident report → this supplement) because it travelled bundled with two true items and had the *shape* a CRE lawyer expects. It was caught only when the source was finally read. **The rule CAM imposes on its extractor — propose a verbatim quote or it is not evidence — had never been imposed on CAM's own analysis of its artifacts.** Structural verifiability must extend to every layer that makes claims about a document, including the human-facing one. |
| **`all_lp_texts` / cross-LP injection (Step 307b, Supplement #05-12)** | The many-to-many primitive was **already reduced to practice one layer down**, at the element layer. Extraction was the sole destructive step in the pipeline. |

---

## 12. Open Questions for the Patent Attorney

1. **Is governed evidence selection a distinct claimable contribution, or a dependent claim on the evaluator-panel architecture?** The asymmetric merge rule (§6.1) is the strongest candidate for independent claim status — it is a specific, non-obvious governance mechanism with an articulated principled basis, not an implementation detail.

2. **Does the structural/semantic verifiability boundary (§7) strengthen or weaken scope?** Stating plainly what CAM does *not* verify is honest and, we believe, strengthens the claim by making it precise. Confirm this is also the right prosecution posture.

3. **Detectability.** Panel-governed evidence selection is observable in output provenance (selector support, cited reasons per span). Is that a meaningful infringement-detection surface?

4. **The three-way fail-closed pattern** (evaluator identity 414 / extraction integrity 421B / span verification 423A) is one doctrine on three surfaces. Is it claimable as a general property — *the framework refuses to assert when any layer of its own substrate is compromised* — or must each be claimed separately?

5. **Prior art.** The closest families are RAG retrieval, ensemble/self-consistency, and LLM-as-judge. None, to our knowledge, govern *which evidence reaches the evaluators* with a multi-evaluator panel, a union merge, and a declared-dependency completeness gate. This needs a proper search.

---

*Supplement #26. Conception documented 2026-07-13/14. Reduction to practice partial — see §8. No performance baseline exists and none may be cited.*
