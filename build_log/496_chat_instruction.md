# Step 496 — Instruction

**Received:** 2026-08-30, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 496. Adopt C5 for LP-16. One change, then measure.

LP-16 activation_clues -> ['parking spaces','parking rights','garage',
'surface parking','unreserved parking','reserved parking']

Every clue demonstrably fires on at least 2 real positives; the four
responsible for all false positives are removed; C3/C4's four
never-firing clues are NOT adopted, per Rule 1.

Do NOT touch extraction status semantics. Step 495 C.3 establishes that is
a separate, more dangerous change needing its own authorization and arc.

RUN
  - divall, full-LP, canonical, through run_mode_c.py. Up to four attempts.
    THE QUESTION: does it complete? LP-07 still failed 1 of 4 at Step 494,
    so completion is not guaranteed even with LP-16 resolved.
  - one Atlas run. LP-16 is applicable there and must not flip.

REPORT
  1. divall: completes or aborts, and on which LPs.
  2. LP-16's entry on divall — not_applicable, zero element verdicts,
     and does the banner name it?
  3. LP-16 on Atlas: still applicable, verdict unchanged?
  4. LP-07/LP-12/LP-17/LP-27 on both against Step 491/494.
  5. Panel census, calls, elapsed. Verify the panel before spending.

Do NOT tune. If divall still aborts, report on which LP.
