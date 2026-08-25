# Step 483 — Instruction

**Received:** 2026-08-24, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 483. Gate: evidence present anywhere. DIAGNOSTIC FIRST, no fix.

LP-12 is now correctly applicable, so an empty LP-12 extraction is fatal.
Predicted Atlas abort ~72%, divall unprocessable. But §13.2 is present in
LP-24's tenant_text on 6 of 6 extraction-only runs (Step 463) — the
evidence exists in the extraction output; only the bucketing dropped it.

Establish, offline from the 18 persisted extraction runs plus the divall
extractions:

1. For every LP that fails the completeness gate across all persisted
   extractions: does the text that LP needs appear in ANOTHER LP's
   tenant_text in the same extraction? Report per LP per run —
   present-elsewhere vs genuinely absent.

   Use the same needle discipline as Step 463: phrases verified unique in
   the canonical text, not topic words.

2. How would a gate that passes when the needed text is present anywhere
   in the extraction behave across those runs? Report the abort rate,
   against the current predicted ~72% on Atlas and 100% on divall.

3. What would such a gate KEY ON? It cannot use per-LP needles — those
   were hand-picked for two provisions. State honestly whether a general
   rule exists, or whether this only works when you already know which
   clause you are looking for. If the latter, say so plainly; that is a
   finding, not a failure.

4. Would the seam make this moot? LP-07 and LP-27 already source evidence
   from spans rather than buckets. If LP-12 were seamed, would elicitation
   find §13.2 regardless of bucketing? Step 471 measured LP-12 elicitation
   returning 7 verified termination triggers. Report whether seaming LP-12
   would bypass the gate problem entirely, and what it would cost.

Report. Change nothing.
