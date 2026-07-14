# Design Note — Structural Addressing: Extent Is a Structural Fact, Not a Model Judgment

**Date:** 2026-07-14
**Status:** DESIGN NOTE — thesis recorded, NOT built, NOT measured. Nothing here is reduced to practice.
**Sources:** `build_log/424_segmentation_recall_measurement.md`; `build_log/425_canonical_source_normalization_v2.md`; `build_log/426_recall_remeasurement_canonical_v2.md`

---

## 1. Why this note exists

Steps 424 and 426 measured element-guided span elicitation on the Atreca lease, N=5, 32 LPs, 160 calls each. Step 425 removed the parser's page-number artifacts in between.

The result was decisive. **Parser-artifact failures went to zero.** Of 166 unverified spans in 424, 92 (55%) were typographic artifacts in the canonical source; after 425, all three of those categories are **completely absent**.

What remains is a single failure class, and it is not a parser problem:

| Failure class | 424 | 426 | Cause |
|---|---|---|---|
| Page-number artifact | 52 | **0** | parser (fixed, 425) |
| Space-before-punctuation | 33 | **0** | parser (tolerated in matching profile, 425) |
| Quote-mark spacing | 7 | **0** | parser (tolerated in matching profile, 425) |
| **Ellipsis elision** | 48 | **32** | **model behavior — untouched, and now 100% of what remains** |

The model is instructed to quote verbatim. Asked for the Operating Expense exclusions list — 1,700 characters, items (a) through (u) — it instead writes `"...capital expenditures [...] free rent and construction allowances..."`, eliding the middle. The resolver correctly refuses: the omitted text is not whitespace.

**No parser fix touches this. No prompt fix reliably touches this either.** It is a predictable consequence of asking a language model to reproduce a long passage character-for-character.

---

## 2. The thesis

> **The ellipsis class and the boundary-drift class are the same problem wearing two hats. In both, the model is being asked to determine EXTENT — where a span begins and ends — which is a structural fact about the document, not a judgment the model should ever have been asked to make.**

**Ellipsis elision** is extent-determination failing by *omission*: the model must reproduce every character between two boundaries and elects not to.

**Boundary drift** is extent-determination failing by *variance*: the same clause, quoted across runs at temperature 0, resolves to different offsets. Measured instances:

- **Condition Precedent** — 424: 2/5. 426: 1/5. The operative clause is verified every run; what varies is whether the *introductory sentence* ("Notwithstanding anything to the contrary...") is inside the span. The model redraws the boundary per run.
- **Annual Statement / reconciliation** — 5/5 both measurements, but one run in each resolves to a shorter span, ending mid-mechanism.
- **Service-interruption abatement** — 5/5 both, one run begins 59 characters earlier.
- **120-day termination right** — stable in 424; newly unstable in 426, one run resolving 277 characters longer.

Hit rate conceals this. A target can be found in every run and still have an unstable extent. **The span universe is not fixed** — a ~9% swing in verified span count across identical inputs at temperature 0 (424), unchanged by `canonical_v2` (426).

---

## 3. The proposed correction

CAM's existing doctrine (423 spec §4, Supplement #26 §4):

> The model proposes a verbatim quote. Code resolves it against the hashed canonical source and assigns the offsets. **An offset is never a model claim; it is a derived fact.**

The structural-addressing thesis pushes that one level up:

> **The model proposes a LOCATION. Code determines the EXTENT.**

Concretely: parse the document's section / subsection / item hierarchy and expose it as an addressable layer alongside the flat character offsets. The model then cites structurally — *"the exclusions are Section 5, items (a) through (u)"* — and code resolves that citation to a character span whose boundaries are **parse facts**, not per-run model choices.

**What this would fix, by construction:**

- **Ellipsis elision becomes impossible.** The model never reproduces the passage; it names it. There is nothing to elide.
- **Boundary drift disappears.** The extent of "the paragraph beginning *Notwithstanding anything to the contrary*" is a property of the parse, identical on every run. The model is no longer drawing the boundary, so the boundary cannot move.
- **Long spans stop being fragile.** A 22-item enumerated list is exactly as easy to cite as a single sentence.

This is the same principle that already governs offsets, applied to the one remaining thing the model is still being asked to determine about the document's shape.

---

## 4. Why this is NOT being built now

Three reasons, recorded so the deferral is a decision rather than a drift.

**It does not block the current fix.** The four page-1 parameters the dependency map requires — Tenant's Share 100%, Building's Share 45.79%, Rent Adjustment 3%, Base Rent — verify at **5/5 with byte-stable offsets** in both measurements. They are short, discrete, labelled rows. They are the *cleanest* objects in the corpus and are entirely untouched by the ellipsis class. The parameter block and dependency map (Step 427) can be built on the substrate exactly as it stands.

**Generalization is unproven and the failure mode would be silent.** Atreca is an SEC HTML filing: tagged, clean, structure genuinely recoverable. Most commercial leases are PDFs, frequently scanned, frequently amended by rider. Section numbering in the wild is inconsistent (`5.`, `5(a)`, `5.1`, roman numerals, exhibits restarting at 1). A structure parser that works on Atreca and fails on lease #4 is **worse than none**, because it will fail *silently* — the precise failure shape this project has spent three weeks correcting.

**It introduces a new class of unverifiable claim.** The current guarantee is airtight and mechanical: a span is `verified` if and only if the raw characters at its offsets match the proposed quote. If code begins *inferring* "this text is Section 5(b)," that inference can be wrong, and the offset invariant does not cover it. Structural addressing therefore requires a **structural-verification layer of its own** — and that is a new surface for the same bug class CAM exists to govern. It must be designed with the same rigor, not bolted on.

---

## 5. What would have to be true before building it

- A structure parser whose output is **verifiable**, not merely plausible — the structural claim needs an invariant as hard as the offset invariant.
- Measured on **more than one document**, and specifically on at least one PDF-sourced lease, before any claim of generality.
- A stated hypothesis and a measurement, per standing protocol: **does ellipsis elision go to zero, and does boundary drift go to zero?** Both are directly measurable against the existing 424/426 instrument.
- An explicit decision on the fallback: what happens when structure is *not* recoverable? The verbatim-quote path must remain, and the system must know which path it used. (Silent substitution is this project's recurring bug class; a structural path that silently degrades to a verbatim path would be a textbook instance.)

---

## 6. Patent relevance

Potentially significant, and recorded here to date the conception.

Supplement #26 claims that CAM governs the **evidentiary substrate**, not merely the conclusions — and that an offset is a derived fact rather than a model claim. The structural-addressing thesis extends the same reasoning to **extent**, and identifies a specific, measured failure mode (ellipsis elision; boundary drift) that follows directly from asking a generative model to determine a structural property of a document.

The generalized claim would be:

> Any property of a document that is structurally determinable must be determined by deterministic code, never by the generative model — even when the model is capable of reporting it correctly most of the time. The model's role is to *locate*; the system's role is to *resolve*. Where the model is asked to determine extent, it will elide long passages and redraw boundaries across runs, and both failures are invisible to a verifier that checks only whether the text it received matches the source.

That is a stronger and more general statement than "models propose quotes, code resolves offsets," and it subsumes it.

**Not yet claimed. Not yet built. Not yet measured.** Recorded 2026-07-14 so that conception is dated and the reasoning survives.

---

*Design note. No code. No measurement. Nothing here may be cited as reduced to practice.*
