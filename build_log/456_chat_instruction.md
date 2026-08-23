# Step 456 — Instruction

**Received:** 2026-08-22, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Park the span seam. Record only. No runs, no tuning, no seam changes,
no design decision.

Write build_log/FINDING_span_seam_citation_gap.md.

THE FINDING
Span evidence improved what evaluators could see and degraded whether they
were permitted to report it. On LP-27, A and C independently returned
explicitly_present at high confidence. Consensus was reached — B abstained,
was dropped, majority_count=2, the no_consensus branch did not fire. The
citation check then replaced the presence verdict with unclear because the
assembled evidence supplied no usable section_ref.

The failure occurred AFTER correct semantic evaluation. Quote both code
sites: the unclear-as-abstention filter at lease_coverage_305.py:907 and
the citation check at :991. Quote the three raw verdicts.

MECHANISM
The seam assembles verified clause bodies and strips source-location
metadata — deliberately, so synthetic span markers would not change what
evaluators read. That conflicts with the 305 contract, which requires a
section_ref for any presence verdict. Extraction buckets retain section
headings; span evidence is often mid-section fragments with nothing
truthfully nameable. 8 of 10 LP-27 elements suppressed to unclear with
citation_required_but_absent.

LP-07 CAVEAT — correct the earlier reading, do not smooth it
LP-07 survived the same gate, but NOT for a robust architectural reason.
Its evaluators supplied locator-shaped strings — "Paragraph 1",
"Proportionate Share definition" — that are not genuine section references.
Record explicitly that Chat's earlier explanation (that LP-07's span was a
definitional sentence evaluators could anchor) was WRONG. LP-07 does not
show that span assembly satisfies the citation contract; it shows some
evaluators manufacture plausible locator labels while others return None,
and the check only tests non-null.

SEPARATE DEFECT CLASS
A reported citation_quality=section_only, C reported section_and_quote,
both returned section_ref=None. A model-authored quality field positively
characterised properties the evidence object does not have. The
deterministic check correctly trusted the object over the description.

PROVIDER CONFOUND
~97% of role-B verdicts came from fallback gemini-2.5-pro after OpenAI
credits ran out six verdicts into each run; is_fallback=True, 191 of 197.
Does NOT explain the LP-27 mechanism, since A and C alone produced the
discarded majority. DOES contaminate every comparative quantity — the
moved-set count and LP-07 stability relative to baseline. No comparative
run is interpretable until the intended evaluator is available.
Operational observation: the router substituted another provider's model
for nearly an entire run, recorded the degradation, and allowed completion.

OPEN DESIGN QUESTION — record all three, choose none
  - derive a section locator deterministically from each verified span's
    canonical offsets
  - expose span identity/source metadata to the evaluator in a citable form
  - recognise that offset-resolved evidence already has stronger source
    verification than a model-supplied section_ref, and modify the citation
    requirement accordingly

PARK STATE
The seam is NOT rejected. It exposed a precise interface mismatch: the
upstream evidence layer knows exactly where the evidence came from; the
downstream evaluator is handed prose that has forgotten it, and is then
penalised for being unable to reconstruct it.

Also record: LP-12 gate tally now 10 aborts / 12 attempts this session,
blocking a third piece of work. Seam remains uncommitted,
SPAN_EVIDENCE_LPS={"LP-07","LP-27"}, rollback one edit.

Commit. Do not deploy.

---

## Discrepancy found on execution, recorded not resolved

The brief lists deterministic offset-derived locators as an OPEN option to record and not choose.
**Step 455 already implemented that option** in the uncommitted seam (`_HEADING_RE`,
`_build_heading_index`, `_locator_for_offset`, and the `[<locator>]` prefix in
`_assemble_span_evidence`), verified offline, never run.

Consequences for two statements in the brief, recorded in the finding's PARK STATE rather than
silently corrected:

- "rollback one edit" is no longer accurate — the working tree carries 141 uncommitted insertions,
  not just the flag line.
- Option 1 is not open-and-untouched; it is implemented-and-unmeasured.

No seam change was made in this step, per instruction.
