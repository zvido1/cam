# Step 533 — Instruction

**Received:** 2026-09-03, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 533. Fix the GATE_ABORT message. Frontend only, no pipeline change.

app.js:5489 and :14393 map every GATE_ABORT to "Not a commercial lease".
Four causes reach that branch; two mean our extractor failed. everbridge
logged is_lease=True four times and its user was told it is not a lease.

1. Enumerate all four causes that raise GATE_ABORT, with the payload each
   carries. Report what the frontend can distinguish from the response
   today — if the causes are not distinguishable, that is the first thing
   to fix and it is a backend change.

2. Only lease_gate.py:100 — the classifier's own verdict — may say the
   document is not a commercial lease. Every other cause must say what
   actually happened, and must not blame the document.

   Propose the wording for each. The completeness-gate case should name
   the issue areas with no evidence, which the payload already carries per
   Steps 476-478.

3. VERIFY BY EXERCISE, not by reading. Drive each of the four causes and
   quote what the user sees. Six steps in this arc have caught defects a
   static read missed, and Step 522 recorded this surface as untested.

4. Report whether the same conflation exists anywhere else — the DOCX and
   PDF annotators, the batch summary, the API error body. Step 477's
   census found nine consumers; check them.

Do NOT change the gate, the matcher, or extraction. Message only.
