# Step 531 — Instruction

**Received:** 2026-09-03, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 531. The applicability matcher. DIAGNOSTIC, no fix.

Three real leases abort with "Not a commercial lease": atreca, ncino,
everbridge. The matcher fires inside `non-exclusive`, inside a conditional,
and inside an exclusion enumeration.

1. Quote the matcher and the exact string that fired for each of the
   three. Is it substring matching without word boundaries, or something
   else? Show the surrounding text so the false positive is legible.

2. Is this the SAME defect as LP-16's `"exclusive"` clue firing on
   "no one remedy shall be deemed to be exclusive" (Step 469), and LP-12's
   negotiated-option jargon missing operative language (Step 481)? If so,
   say how many places in the codebase now use this matching style, not
   just the three you know about.

3. Survey it, Step 495's method. Across all nine real leases and the
   synthetics: does the gate accept or reject each, and is each decision
   correct? Ground truth by reading, not a proxy — Step 495's automated
   proxy misclassified three of thirty-two in both directions.

   Report the baseline BEFORE proposing anything. A matcher that accepts
   everything is as wrong as one that rejects real leases.

4. What does the user see, verbatim? If the message says the document is
   not a commercial lease when the document plainly is, that wording is
   part of the defect.

Do NOT fix. Report the survey and the blast radius.
