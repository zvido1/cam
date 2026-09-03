# Step 535 — Instruction

**Received:** 2026-09-03, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 535. Negation-aware matching. DESIGN, then build if it holds.

Step 534's baseline: 4 abort-causing applicability calls, 0 correct.
Every one fired inside a negation, a conditional, or an enumeration.
LP-20 corpus-wide: 65% of 23 hits are in that context, 14 of 23 literal
negations.

Three previous fixes narrowed clue lists per-LP. This survey says that is
the wrong layer — `exclusive use` IS the right phrase for an exclusivity
covenant, and it appears inside "not leased for the exclusive use of
tenants". No clue wording fixes that.

PART A — DESIGN, report before building

1. What would a negation-aware match look like? Consider a window before
   the hit for negating tokens (no, not, non-, without, except, other
   than, shall have no), and enumeration/exclusion context. State what you
   propose and its window size, and defend both.

2. What does it cost in RECALL? A matcher that misses a real exclusivity
   covenant because the sentence contains "not" elsewhere is worse than
   the current one. Report the false-negative risk against the four
   ground-truthed cases plus every TRUE positive in the corpus — the
   Step-534 screen found hits that are correct and must keep firing.

3. Is negation-awareness sufficient, or does the enumeration case need
   separate handling? "(xxxi) Fixed or percentage rent under any ground
   lease" is not a negation — it is an item in an exclusions list, and the
   negation is in the list's preamble, possibly hundreds of characters
   earlier.

4. Where does it apply? Every conditional LP, or only the ones measured?
   Applying it corpus-wide changes behaviour on LPs nobody has
   ground-truthed. Say which and defend it.

PART B — build only if A is clean, and measure against the survey
Report TP/FP/TN/FN across all nine real leases and the synthetics, per LP,
before and after. Step 495's method: ground truth by reading, and reject
any change that loses a true positive.

Do NOT change any clue list.
