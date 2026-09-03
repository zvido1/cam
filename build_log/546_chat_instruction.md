Step 546. Fix the headline and add resolution scope. No state change.

Two changes, both deterministic, no API calls, derive_lp_state untouched.

PART A — the headline
_build_schema_exposure's catch-all emits the LP's static exposure_statement
for review_needed, written for the absent case. Atlas LP-26 and ex6-4
LP-25 have elements_missing: [] and headlines saying the provision is
absent.

Add one branch before the catch-all for review_needed. It must consult the
record: present count, unresolved count, and elements_missing. A headline
must not assert absence when elements_missing is empty.

PART B — resolution scope
A deterministic annotation off element_verdicts alone. review_needed is
scope-free: 1-of-17 and 4-of-4 render identically. Surface the counts and
a label of the shape "REVIEW NEEDED — 1 OF 17 ELEMENTS UNRESOLVED".

PART C — the DOCX/PDF gap
element_verdicts appears zero times in either. Surface the resolution
counts and the unresolved label there — not the LP-level roll-up, which
Step_305_Architecture.md:39 forbids as a basis for state.

Also: the DOCX [GAP] marker is chosen by bucket, so LP-26 renders
"[GAP] … absent or undefined" with no Missing: line. Fix the marker
selection for review_needed with empty elements_missing.

VERIFY BY ARTEFACT on the Step-537 ex6-4 result and an Atlas result:
  - LP-26 and LP-11 headlines, before and after
  - the DOCX and PDF entries for both, before and after
  - confirm LP-20 at 0-of-7 still reads as genuinely absent — the bottom
    of the range is CORRECT and must not be softened by this change

Do NOT change derive_lp_state. Do NOT add a coverage_state.
