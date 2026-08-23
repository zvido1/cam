# Step 455 — Status: deterministic span locators

**Instruction:** `build_log/455_chat_instruction.md`
**Date:** 2026-08-22
**Status:** COMPLETE for the named objective (locator derivation implemented and verified offline).
**NOT DONE, deferred by instruction:** the clean rerun. No provider calls were made this step.
**Not committed. Not deployed. OpenAI account untouched.**

---

## Withdrawn: my own rationale for selecting LP-27

**This retracts the reasoning given when LP-27 was chosen over LP-22.** I argued LP-27's evidence was
scattered across Sections 5.1, 6.3, 13.3, 8.2, 18.1 and 21.1 while its extraction bucket held only
Section 5.1, making it the LP best served by cross-article span evidence. **That was wrong on the
facts, and I did not check it before spending two runs.**

Extraction's LP-27 bucket (1272 chars) already contained the landlord-default material in full:

```
... In addition, if Landlord fails to perform any material obligation under this Lease and such
failure continues uncured for thirty (30) days after written notice from Tenant specifying the
nature of such failure, Tenant shall have the right to draw upon the Security Deposit as a setoff
against damages, and if such failure continues for an additional thirty (30) days, Tenant may
terminate this Lease upon written notice to Landlord. These rights are in addition to any other
remedies available to Tenant at law or in equity.
```

And the span path did **not** return scattered evidence. Resolving the actual offsets of the spans
LP-27 was handed in both runs:

```
seam2lp_r4  7 spans -> Section 5.1 x6, Section 11.2 x1
seam2lp_r5  8 spans -> Section 5.1 x6, Section 11.2 x2
```

Sections 6.3, 13.3, 8.2, 18.1 and 21.1 do not appear. **LP-27 was never a case of destructive
exclusive assignment losing material** — the bucket had it. The span path delivered a fragmented
subset of the same section plus one new one.

**Consequence for interpretation:** the two-run experiment did not test whether span evidence beats
extraction on scattered material. It tested citability, and answered that decisively. The
`FINDING_span_evidence_not_citable.md` conclusions stand; the scatter premise does not.

## What changed

One file, `cam/adapters/lease_review/lease_coverage.py`, still uncommitted:

- `_HEADING_RE` — line-anchored (`re.MULTILINE`, `^`) match for `Section N[.N...]` and `ARTICLE X`.
- `_build_heading_index(canonical_text)` — ascending `[(offset, label)]`.
- `_locator_for_offset(index, offset)` — nearest preceding heading, or `None`.
- `_assemble_span_evidence` — prepends `[<locator>]` above each verified span, records the locator on
  the span record as `section_ref`, counts located vs bare, and logs a WARNING when any span is
  emitted bare.

Nothing else was touched. No schema change: `section_ref` is a field 423A already declares.

## The trap this had to avoid

A naive backward scan for `Section N.N.` fabricates deterministically. The Atlas definitions block
contains inline cross-references of identical form:

```
"Landlord's Work" shall have the meaning set forth in Section 8.3. "Permitted Use" shall mean ...
```

That match sits at offset 1613; the Proportionate Share definition begins at 1738. An unanchored
scan therefore tags **the single clause this entire arc is about** as `Section 8.3`, when it lives in
`Section 1.2. Definitions` (offset 879). That would be strictly worse than the status quo: a
machine-generated locator the citation gate cannot distinguish from a real one.

Line-anchoring separates them. Newlines survive canonicalization (277 in the Atlas canonical text).
Of 70 `Section N.N.` matches, 65 are line-start headings and 5 are cross-references — offsets 1053,
1613, 2092, 22989, 24021 — and all 5 are excluded.

## Verification — RUN, offline, zero provider calls

Executed against the real functions and stored span offsets:

```
canonical hash da9b5655c5cab382 | headings indexed: 89
cross-reference offsets present in index: []          (required: [])
Proportionate Share span (offset 1738) -> 'Section 1.2'  (required: 'Section 1.2')
```

Assembled output, LP-07 (5 verified spans, 5 located):

```
[Section 1.2]
"Proportionate Share" shall mean 22.4%, representing the ratio of the rentable area of the Demised
Premises to the total rentable area of the Building.

[Section 3.3]
CAM Charges shall include all costs and expenses incurred by Landlord in operating, maintaining, ...
```

LP-12 (7 verified spans, 7 located): `5.1, 13.2, 13.3, 14.1, 14.2, 15.3, 17.2`.

LP-27's actual collapsed spans, re-resolved: **7/7** (r4) and **8/8** (r5) located.

**Total: every span in every stored set resolves. 0 bare.**

## Test suite — RUN

```
350 passed, 2 failed in 3.27s
FAILED test_423a_evidence_span_substrate.py::TestSeamStandaloneAndUninvasive::
       test_module_not_imported_by_live_stage5_pipeline_files
FAILED test_423c_element_guided_elicitation.py::TestPipelineSeam::
       test_no_live_pipeline_file_imports_elicitation_module
```

Both assert `assertNotIn("lease_element_elicitation", src)` against `lease_coverage.py` — they encode
"the 423 stack must not be wired into the pipeline." The seam wires it, so they fail by design. **They
were already failing before this step**; the import they detect is the seam's, added in the prior
session, not this step's locator code.

These are the layering tests named in `FINDING_evidence_architecture_unwired.md` §5 as unable to
detect disconnection. They are now the tests that must be rewritten before the seam can ever be
committed — from "nothing imports this" to "the seam, and only the seam, imports this." **Not done
here; the seam is not being committed.**

## What is NOT established

- **Whether the locator fixes anything.** No pipeline run. Whether LP-27's elements return to
  presence verdicts, and whether LP-07 stops depending on invented labels, is unmeasured.
- **Generalisation beyond Atlas.** The heading regex assumes `Section N.N.` / `ARTICLE X` at line
  start. Atlas is a clean `.txt` fixture. Whether PDF-extracted leases preserve line structure, or
  use these heading forms at all, is untested. A lease that fails both would produce bare spans —
  logged as a WARNING, degrading to today's behaviour rather than fabricating.
- **`ARTICLE` fallback quality.** A span between an ARTICLE heading and its first Section resolves to
  the article. No such span occurred in the stored sets, so this path is unexercised.
- **The gate abort rate** (10/12 this session) is untouched and will dominate the cost of any rerun.
  Which LP trips it was not recoverable from the logs.
