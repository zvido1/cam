# Step 525 — Instruction

**Received:** 2026-09-02, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 525. Raise the router timeout. Then run a real lease.

Eight of nine real EDGAR leases have never been through the pipeline.
Atreca hit 308.8s against a 300s ceiling at Step 494 and has never
completed. The real corpus is 156-288KB against Atlas's 31KB.

PART A — before changing it, report
  1. Where is the 300s ceiling set, and what does it govern — a single
     provider call, a stage, or the whole pipeline? Quote it.
  2. Is it one timeout or several? Report every timeout on the path from
     job submission to result, with its value.
  3. What happens on expiry today — retry, fallback, or hard fail? Atreca
     produced no result at all, so establish whether the timeout kills the
     call, the stage, or the job.
  4. Is anything downstream depending on the ceiling — a Railway request
     timeout, an uvicorn setting, a client poll interval? A router timeout
     raised above a platform timeout achieves nothing.

PART B — raise it
Choose a value from evidence, not a round number. Atreca's 308.8s is one
observation on a 156KB document; the largest is everbridge at 288KB.
Report the arithmetic you used and what document size the new ceiling
supports.

State what it costs when a call genuinely hangs — a higher ceiling means a
stuck run occupies a worker for longer. Say whether that matters here.

PART C — run one
solidpower (209KB, industrial, CO, parses at 1 heading) — full-LP Mode C,
canonical, through run_mode_c.py. Verify the panel first.

REPORT
  - does it complete, and in what wall time
  - extraction: does the gate pass, and on which LPs does it fail
  - the locator: how many section_refs resolve, against Atlas's 99% and
    divall's 7.2%
  - LP-07, LP-12, LP-17, LP-27 — the seamed LPs. Do they get spans, or
    fall back?
  - assessment_status distribution, and the qualifier pass output
  - calls and cost

This is the first real executed lease through the pipeline. Report what
happens, not what should. If it fails, the failure is the finding.

Do NOT tune anything to make it complete.
