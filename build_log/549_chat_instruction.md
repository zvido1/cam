Step 549. Verify the deploy. One run.

Nothing has executed against this build. All Step-548 figures come from
calling functions on stored results.

1. Confirm the Railway build completed and the service is up. Request
   /api/provider-health authenticated: report status, the per-model set,
   and the SDK versions against the committed manifest.

2. One butler_crossing (ex6-4) run through the DEPLOYED app, full-LP
   Mode C, canonical. Verify the panel first.

   THE COMPARISON: this is the same document as Step 537, so every panel
   verdict should be reproducible within known variance and every
   presentation change should be visible.

   Report:
   - the summary top line. Expect five categories. Against Step 537's
     "27 covered".
   - LP-20: still NO ELEMENTS FOUND, still genuinely absent, not softened
   - LP-11, LP-25, LP-26: headlines reporting resolution scope rather
     than asserting absence
   - export findings admitted and rendered, against Step 537
   - any LP whose verdict moved, and whether it is within the run-to-run
     variance measured at Steps 491 and 537

3. Generate the DOCX and PDF from the deployed result and quote page one
   plus the LP-20 and LP-26 entries. Five steps in this arc caught defects
   that only appeared in the artefact.

If anything differs from the local figures, that is the finding.
