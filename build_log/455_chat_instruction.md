# Step 455 — Instruction

**Received:** 2026-08-22, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Do not run a third replicate, and do not commit this seam as-is.

The two landed runs already answered the question we were trying to answer. LP-27 stopped wobbling
when fed span evidence, but it stopped wobbling for the wrong reason: the better evidence lost its
source-addressable structure, so the deterministic citation requirement converted correct evaluator
readings into `unclear`.

That makes the next smallest fix clearer than before:

Keep the span path, but make assembled span evidence citable.

Not "make the model better at inventing `section_ref`." LP-07 shows why that would be poisonous. It
currently survives because B and C manufacture things like `"Paragraph 1"` or
`"Proportionate Share definition"`, while LP-27's evaluators more honestly return `None`. The system
is rewarding fabricated locators.

The assembled evidence should carry the source locator deterministically from the resolved canonical
span. Conceptually, instead of handing 305:

```text
[1] if Landlord fails to perform any material obligation...
```

hand it something like:

```text
[Section 5.1]
if Landlord fails to perform any material obligation...
```

or whatever exact section identity the canonical offset belongs to. The model should cite a locator
it was actually given, not reverse-engineer one from clause prose.

That is now the narrow seam defect. The evidence acquisition itself worked: LP-27's relevant material
became stable enough that both successful runs were identical across all ten elements. What failed
was evidence presentation/provenance between the span layer and 305.

I would therefore leave `lease_coverage.py` uncommitted, keep the two-run result as the diagnostic,
and make one minimal change to the span assembler: preserve or prepend deterministic section/source
locator metadata for each verified span. Then rerun LP-07 and LP-27 when GPT-5.5 is available again.
You only need a couple of clean runs to see whether:

* LP-27 remains stable without collapsing to `unclear`;
* LP-07 no longer depends on invented section labels;
* the Proportionate Share definition still reaches LP-07 reliably.

The 10/12 gate-abort rate and exhausted OpenAI credits make further calls right now actively
low-value. Another degraded replicate would mostly demonstrate that the degraded setup remains
degraded, a discovery humanity can probably survive without.

So the state is:

423C/span acquisition: promising.
Exclusive extraction monopoly: successfully bypassed.
Span-to-305 assembly: defective because it strips citation structure.
Next move: preserve deterministic locators, then rerun clean.

That is still a small evidence-layer repair, not a new architecture. should i fix open ai and run
again?

---

**Follow-up, after Code advised sequencing (locator first, credits second) and reported the
cross-reference trap:**

so what now?

---

## Scope as executed

1. Record the two-run diagnostic as a finding.
2. Populate `section_ref` deterministically on resolved spans; prepend it in the seam's assembler.
3. Verify OFFLINE against stored span offsets. No provider calls.
4. Do NOT run the pipeline. Do NOT commit the seam. Do NOT deploy. Do NOT touch the OpenAI account.
