# Step 529 — Instruction

**Received:** 2026-09-02, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 529. Extraction-only survey across the real corpus. MEASUREMENT ONLY.
No fix, no coverage runs, no architectural change.

Truncation is now observable (Step 528). Run extraction ONLY — not the
full pipeline — against every real EDGAR lease that has not been measured:

  everbridge_northlake_pasadena   288KB  office     CA
  ncino_parkerfarm_wilmington     225KB  office     NC
  quanterix_crosby_bedford        221KB  lab        MA
  atreca_industrial_rd_sancarlos  212KB  lab        CA
  bokf_oklahoma_tower             201KB  office     OK
  albireo_10postoffice            176KB  ?          ?

Plus the three already attempted, for a complete table:
  solidpower  209KB  KNOWN truncated
  atreca_eastjamie  156KB  KNOWN 429
  divall  59KB  KNOWN clean, 33 provisions, 6041 tokens

Persist every result — Step 490's store, not ad hoc.

REPORT, one row per document:
  - completed / truncated / 429 / other failure
  - finish_reason and output token count
  - provisions emitted, of 33
  - truncation_repaired flag
  - normalised text length, and provisions-per-KB

THE QUESTION: what fraction of real executed leases can the current
single-call 33-provision extraction actually process?

Then the density check. Divall emitted 33 in 6,041 tokens at 59KB;
solidpower emitted 5 in 8,192 at 209KB. Report whether output tokens track
document size, provision count, or something else. If a small dense lease
truncates and a large sparse one does not, size is not the predictor and
the architecture question changes shape.

Also: does the 429 recur on atreca_eastjamie, and does it hit any other
document? Two occurrences on one document and none elsewhere is a
document-specific condition; three documents failing is a quota pattern.

Do NOT run coverage. Do NOT attempt a fix. Report the table.
