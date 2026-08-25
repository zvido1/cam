# Step 481 — Instruction

**Received:** 2026-08-24, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 481. Two fixes, both small, both testable.

PART A — LP-12's clue list
Add operative-language clues to LP-12's activation list, alongside the
negotiated-option jargon: "right to terminate", "terminate this lease",
"termination right", "may terminate", and whatever else a survey of the two
fixtures supports. Do NOT remove the existing clues.

Report the survey first — which phrases appear in Atlas and divall's actual
termination provisions — before choosing. Do not guess at market language.

Then re-run is_applicable offline against BOTH canonical texts and every
other fixture that parses. Report:
  - does LP-12 now come back applicable on Atlas and divall
  - does it flip any OTHER fixture, and is that flip correct
  - a clue list that fires on every lease is not a fix; report the
    distribution

PART B — a "not assessed" state
requires_attention is a membership test over coverage_state, and there is
no state meaning the LP was never assessed. not_applicable and the
unclear-routed LPs both emit False, indistinguishably from an LP with
genuinely nothing to report.

Report before implementing: what would break if not_applicable and
unclear-routed entries carried requires_attention: True? Which consumers
read it, which counters would move, and would it flood the report? If it
would, propose a third value or a separate field rather than overloading
the boolean.

Do NOT implement Part B this step. Part A only, then report both.
