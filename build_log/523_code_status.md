# Step 523 — Design. Don't make the panel see it. Tell the reader it didn't.

**Date:** 2026-08-31 · **Instruction:** `build_log/523_chat_instruction.md`
**DESIGN ONLY. Nothing built, no provider calls, not deployed.**

---

# 0. THE BRIEF'S PREMISES — ALL CONFIRMED

First step in this arc where every stated fact holds. Verified against the document and the code:

```
Section 11.3 starts at 15490          ARTICLE 12 starts at 15748
Section 11.2 starts at 14905          15251 falls inside 11.2, mid-clause (b)
SECTION_EXPANDED_SPAN_LPS: set = set()          (lease_coverage.py:76 — rolled back)
```

> **Section 11.3. Limitation of Liability.** "Neither party shall be liable to the other for any
> consequential, indirect, punitive, or special damages arising under this Lease. Landlord's liability
> shall be limited to Landlord's interest in the Building and Land."

**The structural claim holds too.** LP-27's ten `expected_elements_305`, read in full: landlord default
defined; written notice; cure period; offset against rent; termination; monetary damages; specific
performance; lender notice; common-law remedies preserved; remedies cumulative. **None describes a
limitation, cap, waiver, or exculpation.**

And the qualifier bears on **three** of them, not one: §11.3 caps damages (element 6), and a
consequential-damages waiver cuts directly against "common law and equitable remedies are preserved"
(9) and "remedies are cumulative and not exclusive" (10). **The clause the panel could not see is
contrary evidence for three elements it marked present.**

The Step-466 regression is confirmed with its numbers: element 4 moved `MIS → disputed`, reason
`distant_split_presence_missing`, confidence `low`, **identical in both runs — a stable regression,
not noise**, n=2.

---

# 1. Q1 — CO-RETRIEVAL IS VIABLE BUT INHERITS THE DEFECT, AND ITS RISK IS WORSE THAN IT LOOKS

It is a context-widening direction, so it inherits Step 467's inference. But the inheritance is
sharper than "more context is risky."

**Step 466's regression was caused by topically ADJACENT material** — §5.1's security-deposit prose
sitting next to a self-help element. Evaluator A read "draw upon the Security Deposit as a setoff" as
offset-against-rent. **§11.3 is not adjacent-but-irrelevant; it is contrary.** That looks safer and is
not, because the seduction runs in the other direction:

> *"Landlord's liability shall be limited to Landlord's interest in the Building and Land"*

**presupposes that Landlord has liability.** Handed to a panel weighing element 6 — "Tenant has right
to monetary damages" — that sentence is readable as *confirmation* that a damages remedy exists. The
clause that should qualify the finding can strengthen it. **Co-retrieval could make element 6 worse
while aiming to fix it**, and element 6 is already the element in question.

## How you would know before spending runs

Step 467 established the section boundary offline before paying for it. The same discipline applies
and is cheap:

**A zero-call precheck.** Co-retrieval is deterministic given a rule ("the section following the last
retrieved span"). So for every seamed LP on every fixture, compute the exact text that would be added,
then check it for **near-miss language against the currently-clean elements** — the same shape that
caught element 4. That cannot prove the absence of a regression, but it locates where one would land
and costs nothing.

**And then the measurement must be the Step-466 one**: precision over previously-clean elements, not
"did §11.3 arrive." Element 4 was not the target of that change and is where the damage landed.

---

# 2. Q2 — YES, AND THE PLUMBING IS ALREADY BUILT AND INERT

**Two facts from the code make this the strong answer.**

## 2.1 The elicitor already reads the whole document

`lease_element_elicitation.py:259`:

```python
def elicit_spans_for_targets(tenant_text, elements, canonical=True, ...):
    """The model receives a neutral, ordinal target list built from each
    element's `element_label`/`synonyms` — never `element_id`, never an LP
    identifier."""
```

**It is handed the full `tenant_text` already.** §11.3 is not out of reach — it was never asked for.
The targets are *neutral ordinal strings*; the mechanism is agnostic to what they describe. **A
limitation-shaped target list slots into the existing call with no change to the elicitation
contract.**

Targets would be written per remedy-family, not per element:
*a clause excluding consequential, indirect, punitive or special damages · a clause capping a party's
liability to a stated amount or to its interest in the property · an exculpation or non-recourse clause
· a clause making a stated remedy exclusive · a waiver of a remedy otherwise available.*

## 2.2 An alongside channel already exists — and nothing reads it

`lease_coverage.py:336` attaches to every assessment:

```python
assessment["span_evidence_records"] = [
    {"evidence_span_id", "start_char", "end_char", "section_ref",
     "elicited_by", "verification_status", "span_text"} ...
]
```

Its own comment says *"Verdicts are not read from this field; it is provenance only."*

**`grep` for consumers across `cam/` and `05 Lease Analyzer/` returns nothing.** No report surface, no
API field, no `app.js` reference. **The channel that carries evidence alongside a finding without
entering what the panel judges is already built, already populated with offsets and quotes, and
entirely invisible to the reader.** The missing half is a consumer — which is the exact lesson of
Steps 521 and 522.

## 2.3 The property that decides it

Co-retrieval's precision cost must be *measured*, and measurement is the thing this arc keeps finding
insufficient. A separate pass whose output never enters `tenant_text` or `span_evidence` has a
different status:

**The panel's input is byte-identical, so precision over previously-clean elements is unchanged by
construction, not by measurement.** Nothing needs to be established about element 4, because element 4
sees exactly what it saw before.

That is the only lever in this arc that does not have to be paid for in precision.

**Cost: one additional elicitation call per document** — limitations are document-level, so the pass is
not per-LP. Against ~97 calls per run, roughly 1%.

## 2.4 The honest limit

This is a **retrieval** judgment ("does this passage match this description"), not the **entailment**
judgment Step 468 ruled out as a class. The distinction matters and I am not eliding it: the retrieval
model can still be wrong. But its failure modes are asymmetric —

- **A miss leaves us exactly where we are today.** It fails safe.
- **A false positive costs reader noise, never a wrong verdict**, because it cannot reach the verdict.

Neither failure mode can move an element's coverage state. That is a property of the wiring, not of the
model's reliability.

---

# 3. Q3 — `assessment_status` HAS NO ROLE HERE, AND THIS NEEDS ITS OWN MARKER

**LP-27 *was* assessed.** The panel ran, ten elements, three evaluators, `coverage_method =
step_305_per_element`. `assessment_status = "assessed"` is correct and must stay correct.

The new fact is different: *the judgment was reached without material that bears on it.* Overloading
`assessment_status` to carry it would put two facts in one field — the defect Steps 521 and 522 were
spent removing. **A field answering "was this judged" must not also answer "was it judged on
everything relevant."**

Proposed, on the assessment, beside `span_evidence_records`:

```
unweighed_qualifiers: [
  { section_ref, start_char, end_char, span_text,
    qualifier_kind: "damages_cap" | "exclusive_remedy" | "exculpation" | "waiver",
    linked_elements: [6, 9, 10],
    link_basis: "subject" | "document_wide",
    distance_chars: 239 }
]
```

**The wording must not assert that the qualifier limits the finding.** The panel did not judge it and
neither did we. It asserts three things, all of which are verifiable: the clause exists at these
offsets, it was not in the evidence for this finding, and it concerns the same subject. **Anything
stronger would be a second unvoted verdict — the R4/R5 shape from Step 521.**

---

# 4. Q4 — THE SMALLEST THING, AND I AGREE IT IS WORTH MORE

One line on the LP entry, beneath the finding, in the surfaces Step 522 established:

> **Not weighed — §11.3 Limitation of Liability.** *"Neither party shall be liable to the other for any
> consequential, indirect, punitive, or special damages arising under this Lease. Landlord's liability
> shall be limited to Landlord's interest in the Building and Land."* This clause was not part of the
> evidence for this finding and was not weighed by the evaluators.

No verdict change. No confidence change. No new bucket.

**The brief's suspicion is right, and I would go further: this is better than making the panel see
it.** A lawyer reading "monetary damages: explicitly present" next to a verbatim damages cap resolves
the interaction in seconds — that is the reasoning they are actually good at. Making the panel see it
costs a measured precision regression (Step 466) and buys a judgment we have less reason to trust than
the reader's. **Handing over the clause is strictly better than handing over a conclusion about it.**

It also inverts the arc's failure mode. Every defect from Step 487 onward has been *a system reporting
a judgment it did not make*. This reports **an absence it did make** — the one thing the current output
has never done. Step 460 named it: *"nothing in the current output marks its absence."*

---

# 5. Q5 — GENERALITY: THE RETRIEVAL DOES NOT DEPEND ON PROXIMITY; THE LINKING MUST NOT EITHER

**Retrieval is document-wide and proximity-free by construction** — the elicitor already receives the
whole document (§2.1). A cap in a miscellaneous article, an exculpation clause, or an SNDA is retrieved
the same way as one 239 characters downstream. Atlas's proximity is a coincidence of this fixture and
**must not become a design assumption**; a "scan the next section" rule would work on Atlas and fail on
the general case while appearing to work.

**Linking must be by subject, not distance.** Because targets are written per remedy-family, a
retrieved damages cap attaches to the damages elements wherever it sits. `distance_chars` is *reported*
as an attribute — useful to a reader — and is **never** a linking criterion.

**When subject-linking is not confident, report at document level rather than dropping:**

> *"This lease contains a limitation-of-liability clause at §11.3 that was not weighed in any
> individual finding."*

**Never drop on low confidence.** Silently discarding a qualifier we retrieved would recreate the exact
defect — a clause that bears on the finding, absent from the output, unmarked.

**Where it genuinely fails:** a qualifier that is neither near nor subject-matched — a definition that
narrows "Landlord" to exclude successors, say, or a cap expressed only in an SNDA the lease
incorporates by reference. This proposal does not reach those, and I am not claiming it does.
Incorporation by reference is out of scope entirely: the document does not contain the text.

---

# RECOMMENDATION

**Take Q2 and Q4. Do not take Q1.**

1. **A second, non-element-driven elicitation pass** for limitations and carve-outs, over the full
   document, one call per document.
2. **Output to `unweighed_qualifiers` on the assessment — never into `tenant_text` or `span_evidence`.**
   The panel's input stays byte-identical.
3. **A "Not weighed" line** on the Step-522 surfaces, quoting the clause and asserting only its
   existence and its absence from the evidence.
4. **Do not pursue co-retrieval.** It carries a measured precision cost, and its risk on element 6 runs
   the wrong way — a liability cap presupposes liability.
5. **Wire the consumer for `span_evidence_records` at the same time.** It has carried offsets and quotes
   on every assessment for several steps and nothing has ever displayed it. A second inert provenance
   channel would be a worse outcome than none.

**This is a disclosure fix, not a correctness fix, and I want that on the record.** LP-27 element 6 will
still read "explicitly present, high confidence." The verdict does not change. Given that Steps 467 and
468 ruled out the two correctness directions, disclosure is what remains — and Steps 521/522 built the
surfaces that can carry it.

---

# WHAT THIS DOES NOT ESTABLISH

- **Nothing was built, run, or measured.** No provider calls. The one-call cost estimate is arithmetic
  against the existing per-LP batching, not a measurement.
- **Whether a limitation-targeted elicitation pass actually retrieves §11.3 is untested.** The claim is
  that it *can* — the elicitor sees the text — not that it *will*.
- **The precision-is-unchanged property is architectural, and only as good as the wiring.** If any
  future consumer folds `unweighed_qualifiers` back into `tenant_text`, the guarantee is void. It
  should carry a comment saying so.
- **The retrieval model's recall is unknown**, so the false-negative rate is unknown. It fails safe, but
  "fails safe" is not "works."
- **`unweighed_qualifiers` would be a fourth provenance channel** on the assessment
  (`element_verdicts`, `span_evidence_records`, `evaluator_meta`). Two of those are already inert.
- **Step 467 has no status file** — only `build_log/467_chat_instruction.md`. Its result is recorded in
  the Step-466 status and in the 460 evidence file, both of which I read; there is no separate 467
  record to check against.
