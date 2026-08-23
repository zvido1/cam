# Step 466 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 466. Section-expanded spans, LP-27 only. MEASUREMENT.
Side track — nothing in the patent plan depends on this.

CHANGE
In _assemble_span_evidence, expand each verified span to its CONTAINING
SECTION rather than the isolated clause body. Use the existing line-anchored
heading index (_build_heading_index) to find the section boundaries: from
the heading preceding the span's start_char, to the next heading.

The locator prefix stays as it is — it already names the containing section,
so the prefix and the text now agree rather than the prefix labelling a
fragment.

Gate this behind its own flag, separate from SPAN_EVIDENCE_LPS, so it can
be turned off in one edit. Name it plainly.

Do NOT change the element list. Do NOT add a retrieval pass. Do NOT touch
LP-07's configuration or any other LP.

RUN
Two runs, LP-27 only seamed, clean panel. Verify gpt-5.5 is serving before
spending them.

THE QUESTION
Does Section 11.3 now reach the panel, and does it change how damages are
reported?

Report for LP-27:
  - is 11.3's text present in the assembled evidence, quoted
  - element 6 (monetary damages) verdict, and what the evaluators cite
  - element 7 (specific performance) verdict
  - all 10 elements: found / missing / unclear, and the merge reasons
  - do any evaluators reference the liability cap in their reasoning
  - assembled text length, span count, call count, elapsed

Also report what the expansion COSTS: how much larger is the evidence, and
does the LP-27 result change on any element that was previously clean.

Do NOT tune the expansion to improve the result. Report whichever way it
lands.

---

## Two reading decisions, made explicitly

**1. `SPAN_EVIDENCE_LPS` left UNCHANGED at `{"LP-07", "LP-27"}`.** The brief says "two runs, LP-27
only seamed" and also "do NOT touch LP-07's configuration" — removing LP-07 from the seam set would
itself be touching its configuration. Kept as-is because (a) it preserves the Step-457 baseline as a
controlled comparison in which *only* the expansion differs, and (b) `all_lp_texts` injects each
seamed LP's text as cross-LP context, so changing LP-07's seaming would perturb LP-27's prompt and
confound the measurement. **The new expansion flag lists LP-27 alone**, which is what "LP-27 only"
governs here.

**2. Each distinct containing section is emitted ONCE.** Six of LP-27's eight verified spans fall
inside Section 5.1. Expanding "each verified span to its containing section" literally would emit
§5.1 six times. Distinct sections are emitted once each, in offset order.
