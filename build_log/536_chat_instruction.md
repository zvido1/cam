# Step 536 — Instruction

**Received:** 2026-09-03, verbatim from Tzvi in conversation, transcribed to disk before
execution per CLAUDE.md Reporting Integrity Rule 7.

---

Step 536. Add retail/shopping-centre fixtures. Fetch and convert only.
No pipeline runs.

The corpus has nine real leases in which four LP concepts are UNIFORMLY
ABSENT — exclusivity (LP-20), guaranty (LP-21), percentage rent (LP-23),
early termination (LP-12). That has blocked three separate measurements:
Step 520's LP-07 clue survey, Step 535's negation rule, and the degrade
decision. Every change is measured only against negatives.

Fetch these, following the existing convert_leases.py and
edgar_corpus_manifest.json conventions — slug, tenant, landlord, address,
property_type, jurisdiction, effective_date, accession, exhibit, cik,
fixture_path, content_hash, source_url, licensing_note:

  1. data/1013488/000091205702011513/a2074533zex-10_18.htm
     BJ's Restaurant, Esplanade Shopping Center pad GROUND lease.
     TOC lists percentage rent and Exhibit I Exclusive Use Restrictions.
  2. data/852677/000113856002000007/ex1001lease.htm
     Shopping centre lease; exclusivity covenant with a remedy that
     includes termination, plus percentage rent.
  3. data/1807689/000117152020000235/ex6-4.htm
  4. data/1807689/000117152020000235/ex6-3.htm
     Shopping centre pair, 2020 filing, exclusivity covenant present.

THEN, before any run, report per document:
  - normalised character count
  - heading-index parse count, against Atlas 89, quanterix 14, divall 0
  - GROUND TRUTH BY READING for each of the four concepts: does the
    document contain an exclusivity covenant, a guaranty, a percentage-rent
    regime, an early-termination option? Quote the clause or state its
    absence. Do NOT use a substring proxy — Step 495's misclassified three
    of thirty-two in both directions.

The 2002 filings may convert badly. If HTML-to-text produces garbage,
report it and do not silently use it.

Do NOT run the pipeline. Do NOT change any clue list.
