# Step 524 — Instruction

**Received:** 2026-08-31, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 524. Build the qualifier cross-reference pass. Report alongside,
do not widen the panel's evidence.

Per Step 523's recommendation. The constraint that makes this safe: the
panel's evidence does NOT change, so precision on previously-clean elements
cannot regress. Verify that rather than assume it.

1. Build the pass. State what it keys on and defend it — the Step-523
   measurement found 6 of 8 Atlas limitation clauses already retrieved to
   OTHER LPs, so say whether you are cross-referencing existing retrieval
   or running a new one, and why.

2. The output is an ANNOTATION, not a verdict. It must be visibly
   distinguishable from a panel finding on every surface. It cannot use
   assessment_status — that field is about the panel's judgment of an
   element, and this is text the panel never saw. Propose its own marker
   and say where it renders.

3. VERIFY PRECISION IS UNCHANGED. One Atlas run. Every element verdict on
   every LP must match the Step-522 baseline exactly. Any movement is the
   finding and stops the step — Step 466's regression landed on element 4,
   which was not the target of that change.

4. VERIFY BY ARTEFACT. Generate a DOCX and PDF and quote what a reader
   sees for: a finding with a qualifier attached, a finding without one,
   and the qualifier's own entry if it has one. A reader must be able to
   tell an annotation from a verdict without knowing the schema.

5. RECORD THE GENERALITY LIMIT explicitly, in the code and the status.
   Atlas's cap is 239 characters from the finding. State what the pass
   does when a limitation is not adjacent, and that this is unmeasured
   beyond one document — divall parses at zero headings and the synthetic
   corpus derives from one template.

Do NOT deploy.
