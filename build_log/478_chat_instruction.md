# Step 478 — Instruction

**Received:** 2026-08-24, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 478. Applicability-aware gate. Degrade only where applicability
permits it.

Step 477 established the gate does real work on 6 of 7 divall failures —
LP-07/LP-16 applicable, LP-17 required, LP-30/31/32 unclear. For those,
lease_coverage_305 instructs the panel to "Return verdict 'missing' for
every element", asserting silence when extraction failed. LP-12 is the only
one where applicability independently rules the area not_applicable, so its
output is the same either way.

THE CHANGE
The gate's abort/degrade decision consults is_applicable(provision_id,
document_text) — schema plus document text only, no extraction dependency.

  applicability required or applicable  -> ABORT as before
  applicability not_applicable          -> DEGRADE and continue
  applicability unclear                 -> state which you chose and WHY,
                                           and make it the flag's default
                                           only if you can defend it

The unclear case is the judgment call. Report your reasoning before the
diff; do not just pick.

Keep everything from 476/477 — markers, aggregate, banner — on the degrade
path.

TEST
  - Atlas: does the LP-12 case still degrade and continue? Same banner,
    same LP-07 flip, same LP-27 table?
  - divall: does it now ABORT rather than degrade, and on which LPs? It
    should, since six of seven are applicable/required/unclear.
  - the seven remaining presentation consumers from Step 477's census:
    list them, and say for each whether it would present a degraded report
    as complete. Do not fix them.

Do NOT deploy. Report and stop.
