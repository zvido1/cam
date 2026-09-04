Step 559. Run the untried real leases. One at a time, report between each.

Nine real leases. Five have completed the full pipeline -- Atlas (synthetic),
divall, quanterix, solidpower, ex6-4. Everbridge and ncino abort on the
applicability matcher. Four have never been past extraction:

  albireo_10postoffice            176KB
  bokf_oklahoma_tower             201KB
  atreca_industrial_rd_sancarlos  216KB
  atreca_eastjamie_southsf        156KB

Run them in that order, smallest first. Verify the panel before each.
Full-LP Mode C, canonical, through run_mode_c.py, persisted.

REPORT AFTER EACH, then stop and wait:
  1. Completes or aborts. If it aborts, which LPs, which cause, and
     whether it is the applicability matcher -- everbridge and ncino both
     abort there and a third instance would make it a pattern rather than
     two documents.
  2. Any headline asserting something the document contradicts. That is
     the class this arc has been closing and it is the only thing worth
     interrupting for.
  3. The four seamed LPs -- spans or fallback.
  4. Summary top line, five categories.
  5. assessment_status distribution and any broken_xref, with what
     triggered it.
  6. Locator resolution rate and heading count.
  7. Calls, elapsed.
  8. Read the report as a lawyer would. Substantive or generic?

STOP AFTER ANY ABORT. Do not proceed to the next document -- an abort is a
finding and running three more on top of it buries it.

Do NOT fix anything. Do NOT tune. If something looks wrong, report it and
stop.
