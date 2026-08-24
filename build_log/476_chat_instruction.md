# Step 476 — Instruction

**Received:** 2026-08-24, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 476. Stop failing the job on a gate abort. Return a degraded result.

THE DEFECT
Production has no gate retry. One extraction completeness abort ends the
job and hands the user the raw internal message, Detail: Python-dict
fragment included. Measured: 0 of 4 deployed Atlas attempts completed, all
LP-12, ~40% local completion rate. Roughly three in five production runs on
this fixture end in hard failure with no output.

THE CHANGE
lease_adapter.py already has the path — around :1395 the non-canonical
branch marks the run degraded, sets run_degraded and
extraction_completeness_failed, and continues. Currently only reachable
with canonical=False.

Make the CANONICAL path continue too, marked degraded, instead of raising.
Requirements:

  - the result must carry, unmissably: run_degraded, the failed LP list,
    and a human-readable statement that the report is incomplete and not
    valid for legal analysis
  - that statement must reach the SUMMARY block, not only run_metadata —
    the summary is what a reader sees first, and Step 461 recorded a
    counter improving while an answer got worse
  - the failed LPs must be identifiable in the coverage output, not just
    in metadata
  - do NOT silently substitute anything, do NOT retry, do NOT change the
    gate's criteria

Gate it behind a flag so the old raise-on-abort behaviour is one edit away.

TEST
Local full-LP Atlas Mode C, same config as Step 468. Run until you get BOTH
outcomes: one run where the gate would have aborted, and one where it
passes cleanly.

Report:
  - on the degraded run: what the user sees. Quote the summary block and
    the degraded markers verbatim. Is it obvious the report is incomplete?
  - LP-12's coverage entry on the degraded run — what does an LP with zero
    evidence produce downstream? Does it fail, produce a spurious verdict,
    or is it marked?
  - LP-07 and LP-27 on the degraded run — do they behave as in Step 468?
    This is the first look at the seam on a run that would previously have
    died.
  - anything downstream that assumed the gate never lets an incomplete
    extraction through

Do NOT deploy. Report and stop.
