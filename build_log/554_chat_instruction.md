Step 554. broken_xref: prose with no record behind it. DIAGNOSTIC, no fix.

Step 547 established broken_xref is a different defect from review_needed
and partial. Those emitted prose contradicting the record; this emits prose
where there is no record at all. All seven carry zero element verdicts, and
_build_scope_exposure returns None on total_elements == 0, so the Step-546
treatment cannot help them.

The example on file: "Landlord may enter premises without notice, at any
time" with nothing behind it.

1. What is broken_xref, and what produces it? Quote the state's definition
   and every site that sets it. Is it one cause or several?

2. Why zero element verdicts? Report whether the panel ran and produced
   nothing, or never ran. Those are different and the fix differs.

3. Report all seven across the six runs: LP, document, the headline
   emitted, and what the document actually says about that provision.
   Ground truth by reading -- is the prose true of the lease, false, or
   unverifiable?

4. Where does the prose come from? Step 545 traced review_needed's to the
   static exposure_statement via the catch-all. Is broken_xref the same
   path, or its own?

5. What should a reader see for a provision the system could not evaluate?
   assessment_status already exists -- do these carry not_assessed, and if
   so does the reader see it? A headline asserting a specific landlord
   right, backed by nothing, is worse than silence.

Do NOT fix. Report the measurement.
