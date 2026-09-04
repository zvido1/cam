Step 562. Fix the schema headline fallback properly. Not per-case.

THE DEFECT, now observed on three documents
When an LP's exposure comes from the schema path rather than the model
path, _build_schema_exposure's catch-all emits the LP's static
exposure_statement (or risk_if_missing for broken_xref and missing),
written for the ABSENT case -- regardless of what the panel actually found.

Steps 546 and 547 fixed this for review_needed and partial by adding
branches before the catch-all. Step 558 found it live again on solidpower
LP-16 (broken_xref, medium materiality). Step 561 found albireo LP-05:
elements found and reported correctly in the body, headline says "absent
or undefined".

Fixing it per-state is why it keeps returning. Fix the catch-all.

1. Report every path into _build_schema_exposure: which coverage_states
   reach it, which materiality levels, which source field each reads
   (exposure_statement vs risk_if_missing), and which have a branch
   before the catch-all today. Step 556 established broken_xref and
   missing read risk_if_missing and everything else reads
   exposure_statement -- confirm that still holds.

2. THE RULE: a headline must never assert absence when the record shows
   presence. Propose a single guard at the catch-all that consults the
   record -- settled_present, elements_missing, total_elements -- and
   applies to every state, rather than a fourth per-state branch.

   The existing review_needed and partial branches should either fold into
   it or be shown to be doing something the general rule cannot.

3. What should the headline say when the schema string is unusable? Step
   546's answer was resolution scope ("1 of 17 elements unresolved").
   State whether that generalises or whether some states need different
   wording, and say which.

4. LP-20 at 0-of-7 must still read as genuinely absent. That is the best
   finding this project has produced and the guard must not soften it.
   settled_present == 0 was the Step-546 invariant; confirm it still holds
   under a general rule.

5. Separately: ncino reports 8 not_assessed where 6 were assessed. Report
   what sets assessment_status on those six and why it disagrees with the
   record. Do not fix it in this step if it is a different mechanism --
   report and say so.

VERIFY BY ARTEFACT across albireo LP-05, solidpower LP-16, ex6-4 LP-20 and
one Atlas run: quote the headline and the DOCX entry before and after.
Confirm no model-path headline changes.

Do NOT change derive_lp_state. Do NOT add a coverage_state.
