# Step 459 — Instruction

**Received:** 2026-08-23, verbatim from Tzvi in conversation, transcribed to disk before execution
per CLAUDE.md Reporting Integrity Rule 7.

---

Step 459. Update the state docs. No code changes, no runs, no deploy.

Docs/CAM_Current_State.md's 2026-08-20 frontier block is now superseded in
its operative conclusion. It says direction 3 is "the architecture exists
and is unwired" and names the seam as the work. The seam is now built,
measured and committed at 134998b.

PREPEND a new 2026-08-21 block. The doc is newest-first with dated blocks.

Record, in this order:

RESOLVED SINCE THE 08-20 BLOCK
  - The 423 stack is wired for LP-07 and LP-27 at lease_coverage.py.
    Committed 134998b, NOT deployed, NOT extended beyond that LP set.
  - LP-07's false finding is fixed and measured. "Tenant's proportionate
    share calculation method is defined" moved from elements_missing to
    elements_found and held 3/3 across three seam runs, with 22.4% present
    in the evidence every time. The evidence got SMALLER and more correct:
    2,636 chars from the extraction bucket to ~1,565-1,887 from five
    verified spans.
  - A second defect was found and fixed en route: span assembly stripped
    source-location metadata, so the 305 citation gate suppressed correct
    verdicts as citation_required_but_absent. LP-27 was 0/1 found with 8
    elements suppressed. The Step-455 deterministic locator prefix, derived
    from each verified span's canonical offsets, resolved it: LP-27 now
    8/1 found, zero suppressions, across two clean-panel runs.
  - LP-07's evaluators now cite 'Section 1.2' unanimously — the supplied
    locator. Five prior runs produced None, 'Paragraph 1', 'Para. 1',
    'Proportionate Share definition'. 81 of 82 non-null citations match a
    supplied locator; the one exception is a cross-LP reference on the
    single element with no supporting span.

STILL OPEN, and record all five
  1. PRECISION, unasked. Whether the spans are the RIGHT evidence for those
     elements is not established. LP-27's spans resolve to §5.1 and §11.2
     only, and §11.2 is an indemnity clause. This is the mirror of the LP-12
     seven-spans observation: exclusive assignment loses evidence,
     non-exclusive assignment may flood it.
  2. LP-12 extraction gate. Now MEASURED, not inherited — the untruncated
     exception names it. 14 aborts in 18 full-pipeline attempts this arc,
     blocking verification work four separate times.
  3. Two layering tests fail by design. State the distinction Code
     established: they assert coverage must not import the 423 stack, which
     is a not-yet-connected precondition, NOT a direction constraint. The
     genuine direction checks still pass. They should be deliberately
     retired, not made green.
  4. span_evidence_records is dead — assigned twice, read nowhere. Span
     provenance evaporates at the seam, so nothing downstream can audit
     which spans produced a verdict. Two comments are stale: "LP-07 ONLY"
     and "one edit is the whole rollback".
  5. Whether to extend the seam to the remaining 31 LPs, and at what call
     cost. Measured at +1 to +2 calls per seamed LP.

ALSO UPDATE Docs/Patent_Current_State.md, briefly: the 2026-08-20 bound on
Step 447's cand_04 / tenant_share reading stands unchanged. Add that the
extraction-layer defect it rests on now has a demonstrated fix in the
coverage path, which does NOT alter the frozen L1 measurement and does not
narrow the bound.

Then commit both. Do NOT push. Do NOT deploy.

---

## Two deviations on execution, both for accuracy

1. **Block dated 2026-08-23, not 2026-08-21.** The doc is newest-first and dated by block; the arc
   ran 2026-08-21 → 2026-08-23 (`035613c` and `ae89e36` on 08-21, `d5eb4ff`/`c380942` on 08-22,
   `f3f1246`/`134998b` on 08-23). Dating the block 08-21 would date it before the commits it records.
   Arc span noted inside the block.

2. **Call-cost figure corrected in open item 5.** The brief states "+1 to +2 calls per seamed LP".
   Measured `api_calls_total`: no seam 92; one seamed LP 93/93/94; two seamed LPs 94/94 (clean panel)
   and 91/91 (degraded panel, fallbacks alter the count). That is **~+1 call per seamed LP**, matching
   one elicitation call per LP, with ±1 run-to-run variation. "+1 to +2 per LP" would overstate a
   33-LP extrapolation by roughly double, and item 5 is a cost decision, so the measured figure is
   recorded with the raw counts.
