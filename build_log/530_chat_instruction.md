# Step 530 — Instruction

**Received:** 2026-09-03, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 530. Fix Gemini usage reporting, then run one real lease end to end.

PART A — usage
_extract_usage reads resp.usage; Google provides usage_metadata. So every
Gemini token figure in Step 529 is raw_char_len / 4, an estimate, and the
headroom conclusion rests on it.

Fix it. Report the actual field names Google returns and map them to
whatever shape the other providers already use — do not invent a second
shape.

Then re-measure ONE document's real token count against the estimate.
Divall is cheapest at 59KB. Report estimated vs actual and the error.
If the estimate is materially off, say what that does to Step 529's
headroom arithmetic — the ceiling arrives past ~350KB on the estimated
slope, and a bad estimate moves it.

Do NOT re-run all nine.

PART B — one real lease, full pipeline
Nine real leases extract cleanly. NOTHING downstream of extraction has ever
run on one except divall, which took two attempts locally and has never
completed deployed. Coverage, the panel, the seam, the locator, the
qualifier pass and assessment_status are all Atlas-only measurements, and
Atlas is synthetic.

Pick ONE and say why. Consider: quanterix parses at 14 headings, the most
of any real lease, so the locator has its best chance there. Others parse
at 0-4. If you would pick differently, say so.

Full-LP Mode C, canonical, through run_mode_c.py. Verify the panel first.
Expect ~280s extraction plus coverage — report the total, since nobody
knows what a real lease costs end to end.

REPORT
  1. Completes or aborts. If it aborts, which LPs and why.
  2. Locator resolution rate, against Atlas 99% and divall 7.2%. At 14
     headings this is the first real test of whether the prefix works
     outside a synthetic document.
  3. The four seamed LPs — spans or fallback?
  4. assessment_status distribution across 33.
  5. The qualifier pass — any limitations found, any cross-referenced?
     Step 524 measured this on Atlas only, with Atlas-derived patterns.
  6. Calls, elapsed, and cost.
  7. Read the report as a lawyer would. Does it look like a review of THIS
     lease, or a template filled in? Say which findings look substantive
     and which look generic.

Item 7 is the point. Everything else is instrumentation.
