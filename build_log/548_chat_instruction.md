Step 548. Push. Branch only.

1. Preflight per CLAUDE.md: fetch, unpushed count, every commit touching
   "05 Lease Analyzer/" or "cam/", secret scan on the diff, tests against
   HEAD. This is a Railway deploy.

2. Confirm the flag state that goes live:
   SPAN_EVIDENCE_ENABLED, SPAN_EVIDENCE_LPS, SECTION_EXPANDED_SPAN_LPS,
   ENTAILMENT_TEST_LPS, GATE_ABORT_RETURNS_DEGRADED,
   DEGRADABLE_APPLICABILITY.

3. State plainly what changes for a user, since eleven commits is a lot to
   deploy blind:
   - the summary top line: three categories plus not_assessed beside it,
     from one shared helper across six sites
   - exports: what the filter now admits, and how many findings a typical
     report gains
   - 46 headlines that asserted absence against their own records now
     report resolution scope instead
   - the DOCX [REVIEW] marker replacing [GAP] where there is no adverse
     missing element
   - anything else deployable I have not listed

4. State what does NOT change and could be mistaken for a regression:
   LP-20 at 0-of-7 still reads as genuinely absent; model-path headlines
   are untouched; no coverage_state was added; derive_lp_state is
   unmodified.

5. Push branch only. NOT --follow-tags. Both sanction tags stay local.

HALT before pushing if anything in 1-3 is unexpected.
