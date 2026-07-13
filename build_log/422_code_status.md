# Step 422 — Clean-Extraction Frozen-Panel Baseline

**Date:** 2026-07-13
**Status:** STOPPED — hard rejection gates triggered, material diff found
**Step:** 422 (Part 1 = 421B commit, done; Part 2 = this report)

---

## Part 1 — Commit 421B Artifacts

Completed in prior session. Commits on main:
- `25517e5` — 421B extraction integrity guard implementation (10 new tests, 421B_extraction_integrity.md)
- `3770e68` — 421B follow-up report (ceiling probe, named runs audit, cam/core/ analysis)

---

## Part 2 — Clean-Extraction Quality Check + Diff

### Method

Harness ran up to 10 Gemini extractions (`gemini-3.1-pro-preview`, `canonical=True`, 65k ceiling) on the Atreca document, targeting both post-ceiling hashes from the N=5 probe. Both were captured in 2 attempts (total ~405 seconds).

**Document:** `atreca_eastjamie_southsf_lease.txt`
**Source hash:** `e049ee63a4e2f475`
**Provisions:** 33 (LP-00 through LP-32)

---

### Extraction Results

| Attempt | Hash | LP chars | Elapsed | Repair fired? |
|---------|------|----------|---------|---------------|
| 1 | `f7f64b5c4b08b55c` | 127,480 | 209.6s | No |
| 2 | `d3e62ead1670adb8` | 115,495 | 195.2s | No |

---

### Hard Rejection Gates — Both Hashes Fail

#### `f7f64b5c4b08b55c` (outlier, 127,480 LP chars)

| Gate | Result |
|------|--------|
| Gate 1 — Repair fired | PASS (not fired) |
| Gate 2 — Ceiling headroom | PASS (41,886 est tokens, 64.4% of 65k) |
| Gate 3 — Stub provisions | **FAIL — 4 stubs** |
| Gate 4 — LP-07 table | **WARN — ABSENT** (len=11,492, no "100%", no "45.79%") |
| Gate 5 — Provision count | PASS (33) |
| **Overall** | **REJECT** |

#### `d3e62ead1670adb8` (modal 4/5, 115,495 LP chars)

| Gate | Result |
|------|--------|
| Gate 1 — Repair fired | PASS (not fired) |
| Gate 2 — Ceiling headroom | PASS (37,948 est tokens, 58.4% of 65k) |
| Gate 3 — Stub provisions | **FAIL — 4 stubs** |
| Gate 4 — LP-07 table | **WARN — ABSENT** (len=7,115, no "100%", no "45.79%") |
| Gate 5 — Provision count | PASS (33) |
| **Overall** | **REJECT** |

**Both hashes rejected.** Gate 3 (no stub provisions) is a hard gate. 4 stub provisions present in every extraction captured.

---

### Diff — Material (STOP condition)

**Delta:** `f7f64b5c` is 11,985 chars larger than `d3e62ead` (127,480 vs 115,495).

| LP | f7f64b5c chars | d3e62ead chars | Delta | Classification |
|----|----------------|----------------|-------|----------------|
| LP-00 | 990 | 2,176 | +1,186 | **MATERIAL** — "percent" keyword in d3e62ead extra |
| LP-03 | 4,311 | 3,407 | -904 | **MATERIAL** — "provided", "however" in f7f64b5c extra |
| LP-05 | 3,021 | 2,816 | -205 | **MATERIAL** — "cap" keyword in f7f64b5c extra |
| LP-07 | 11,492 | 7,115 | -4,377 | **MATERIAL** — "except", "notwithstanding", "unless", "percent" in f7f64b5c extra |
| LP-08 | 6,526 | 6,530 | +4 | cosmetic |
| LP-10 | 9,563 | 9,568 | +5 | cosmetic |
| LP-12 | 7,103 | 3,144 | -3,959 | **MATERIAL** — "except", "provided", "however", "notwithstanding", "unless", "subject to", "excluding" in f7f64b5c extra |
| LP-15 | 2,658 | 2,659 | +1 | cosmetic |
| LP-17 | 621 | 601 | -20 | cosmetic |
| LP-19 | 6,381 | 6,384 | +3 | cosmetic |
| LP-24 | 5,090 | 5,092 | +2 | cosmetic |
| LP-27 | 1,774 | 1,775 | +1 | cosmetic |
| LP-28 | 8,404 | 4,682 | -3,722 | **MATERIAL** — "provided" conditional language in f7f64b5c extra |

**Material differences: 6 LPs** (LP-00, LP-03, LP-05, LP-07, LP-12, LP-28)
**Cosmetic differences: 7 LPs**

Decision rule: Difference is material → STOP.

---

### LP-07 Findings (Operating Expenses)

Both hashes have LP-07 present (non-stub) but the LP-07 percentage table is absent from both:
- `f7f64b5c`: LP-07 = 11,492 chars, no "100%", no "45.79%"
- `d3e62ead`: LP-07 = 7,115 chars, no "100%", no "45.79%"

The percentage table was the specific sentinel used in Step 419 to confirm LP-07 completeness. Its absence in both post-ceiling extractions is a new finding. LP-07 in the new ceiling runs is not truncated (the ceil fix worked — no repair fired), but the table may be in a part of the lease that Gemini is extracting differently, or the table itself is described differently in what Gemini summarizes.

Note: LP-07 at 7,115 chars (d3e62ead) vs 11,492 chars (f7f64b5c) — the 4,377-char difference in LP-07 includes carve-out and reconciliation language ("except", "notwithstanding", "unless") that is material to coverage assessment.

---

### Stub Provision Count and Identity

Both hashes have 4 stub provisions. Confirmed by a third extraction (also `d3e62ead1670adb8`):

| LP | Provision Name | Assessment |
|----|----------------|------------|
| LP-20 | Exclusivity | Retail/shopping center provision — not applicable to industrial subleases |
| LP-21 | Guaranty of Lease | Lease guaranty — absent in this sublease (not required for Atreca/industrial) |
| LP-23 | Percentage Rent | Retail provision (% of sales) — never present in industrial leases |
| LP-31 | Co-Tenancy | Retail provision (anchor tenant rights) — never present in industrial leases |

**Assessment: These are almost certainly expected-ABSENT provisions, not extraction failures.** LP-20 (Exclusivity), LP-23 (Percentage Rent), and LP-31 (Co-Tenancy) are retail shopping center provisions that have no counterpart in an industrial sublease. LP-21 (Guaranty of Lease) is absent because this lease does not include a guaranty rider.

Gemini returning empty `tenant_text` for these provisions is correct behavior. The `status` field for these provisions should be `TEMPLATE_ONLY` or `ABSENT` — they have no tenant text because the lease contains no such clause.

**Gate 3 as written is too strict for this document type.** The gate "zero stubs" is appropriate for mixed-use or retail leases but rejects a correct industrial-lease extraction. The gate should be amended to: "No stubs unless the LP is a known retail/guaranty provision confirmed absent in industrial leases."

If this interpretation is confirmed by Chat, both post-ceiling hashes pass all hard rejection gates once Gate 3 is scoped correctly.

---

### Freeze Decision

**FROZEN: None.** Both hashes rejected on Gate 3 (stubs) and the diff is material.

The N=10 frozen-panel baseline cannot proceed until:
1. The stub issue is resolved — are the 4 stubs expected ABSENT findings or extraction failures?
2. If extraction failures, a clean extraction with 0 stubs is needed
3. If expected ABSENT, Gate 3 needs to be adjusted to allow known-absent provisions
4. The diff between the two Gemini outputs needs a root cause — Gemini is producing materially different extractions on LP-03, LP-05, LP-07, LP-12, LP-28 across runs, suggesting genuine non-determinism in which sections it extracts

---

## Decisions Needed

### Decision 1 — Stub provisions: expected or extraction failure?

**Finding confirmed:** The 4 stubs are LP-20 (Exclusivity), LP-21 (Guaranty of Lease), LP-23 (Percentage Rent), LP-31 (Co-Tenancy). These are retail/guaranty provisions that should not appear in an industrial sublease. The extraction behavior is almost certainly correct.

**What Chat needs to confirm:** Is this interpretation right? If yes, Gate 3 should be scoped to "no stubs in non-retail provisions" for industrial leases. If confirmed, both `d3e62ead` and `f7f64b5c` pass all hard rejection gates.

This is the key decision that unblocks the freeze.

### Decision 2 — Material diff between hashes: response_schema or accept variability?

LP-07, LP-12, LP-28 differ by 3,700–4,400 chars between the two Gemini runs. These differences include carve-outs, reconciliation mechanisms, and conditional clauses that affect coverage scoring. Running the N=10 panel on `d3e62ead` vs `f7f64b5c` would produce different LP-level scores even if the evaluators were perfectly deterministic.

The `response_schema` change (3 lines in `cam/core/`, Approach B from Item 3 of 421B follow-up) would constrain Gemini's output to a fixed JSON schema, potentially reducing this variability. But it would not eliminate non-determinism in the extracted text itself.

**What Chat should decide:** (a) Accept the hash variability and freeze the modal hash as "representative" with a caveat note, or (b) authorize the `cam/core/` response_schema change and run another probe to see if it reduces LP-level variance, or (c) some other path.

### Decision 3 — Is the LP-07 table absence a new finding or a test assumption error?

The 419 baseline used `"100%"` and `"45.79%"` as LP-07 completeness sentinels. These figures may have appeared in the truncated `ab80aafe` extraction by coincidence of the truncation point, or the test assumption was wrong. The new extractions do not contain these strings even at 7,115–11,492 chars of LP-07 text.

**What Chat should clarify:** Was "100%" / "45.79%" actually in the original extraction artifact from Step 419, or was that an assumed sentinel that was never verified?

---

## Long-section LP lengths (both hashes)

| LP | f7f64b5c | d3e62ead |
|----|----------|----------|
| LP-05 | 3,021 | 2,816 |
| LP-07 | 11,492 | 7,115 |
| LP-10 | 9,563 | 9,568 |
| LP-14 | 914 | 914 |
| LP-22 | 1,848 | 1,848 |
| LP-26 | 264 | 264 |
| LP-27 | 1,774 | 1,775 |

LP-14, LP-22, LP-26, LP-27 are very short and consistent between hashes. LP-05 and LP-07 differ meaningfully. LP-10 is consistent.

---

## Step 423 (Policy Resimulation)

**Blocked pending 422.** Cannot rerun policy simulation until a clean baseline extraction is frozen.

---

## Action Required

This step is **STOPPED** pending Chat decisions on the 3 decisions above.

The panel run (N=10) and policy resimulation (Step 423) are blocked until a clean extraction with 0 true-failure stubs is achieved and frozen.
