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

---

## N=10 Extraction Probe — Hash Distribution and LP Variance

### Hash distribution (N=10, all succeeded, no repair fired)

| Hash | Count | LP chars |
|------|-------|----------|
| `f7f64b5c4b08b55c` | **8/10** | 127,480 |
| `d3e62ead1670adb8` | 2/10 | 115,495 |

Note: This reverses the N=5 finding (4/5 d3e62ead, 1/5 f7f64b5c). Over N=15 combined: f7f64b5c = 9 runs, d3e62ead = 6. The modal is unstable across sample sets — neither hash is clearly "the Gemini answer."

### Per-LP stability

**Stable (20/33):** LP-01, LP-02, LP-04, LP-06, LP-09, LP-11, LP-13, LP-14, LP-16, LP-18, LP-20 (stub), LP-21 (stub), LP-22, LP-23 (stub), LP-25, LP-26, LP-29, LP-30, LP-31 (stub), LP-32

**Material variance (6/33):** LP-00, LP-03, LP-05, LP-07, LP-12, LP-28

**Cosmetic/tiny (7/33):** LP-08, LP-10, LP-15, LP-17, LP-19, LP-24, LP-27

### What Gemini is varying — exact content

The variance is not random character noise. Gemini makes different **start/stop extraction decisions** for each of the 6 variable LPs.

#### LP-07 — Operating Expenses (+4,377 chars in modal)

Both hashes share the same 573-char opening (the Annual Estimate payment mechanism). Then they diverge:

- **Modal `f7f64b5c` (11,492 chars):** Extracts the full Operating Expenses definition including:
  - The Operating Expenses definition (all items in scope: Taxes, capital repairs, Common Area Amenities, parking, etc.)
  - **Operating Expense Exclusions** — the carve-out list, items (a) through (u), specifying what is NOT charged to tenant
  - **Annual Statement / reconciliation mechanism** — the year-end true-up
  - **Independent Review (audit rights)** — tenant's right to audit Landlord's books, with cost-shifting if overpayment exceeds 5%
  - **95% occupancy gross-up** — Operating Expenses computed as though the Building were 95% occupied
  - The `"Tenant's Share"` definition and the Rent definition tying together Base Rent + Operating Expenses

> **[CORRECTED 2026-07-14 — FABRICATED CLAIM REMOVED]**
>
> The original version of this section listed a **"Controllable Expenses Cap — capping annual increases on controllable items at typically 5%"** among the LP-07 contents.
>
> **No such clause exists in the Atreca lease.** Section 5 was read end-to-end against the source on 2026-07-14: it contains the Operating Expenses definition, the exclusions list (a)–(u), the Annual Statement reconciliation, the Independent Review audit rights, the 95% gross-up, and the Tenant's Share definition. There is no cap on Operating Expenses of any kind. Tenant's Share is 100%; the landlord (Alexandria) conceded no cap in this triple-net lab lease.
>
> **Mechanism:** the word *"typically"* is the fingerprint. This was not a description of an extraction artifact — it was a description of what an Operating Expenses section *usually contains in commercial leases generally*, written from priors and formatted as an observation. The claim was inferred, not read.
>
> **Propagation:** this sentence was inherited by `421C_evidence_assignment_incident.md` §2a (where "typically" was dropped and it became a flat assertion, then escalated to "the primary tenant protection against runaway CAM charges"), and from there into `Docs/Patent_Supplement_2026_07_14.md` §11. All three have been corrected.
>
> **Why it survived:** it was bundled in a list with two true items (exclusions, reconciliation); it was exactly the shape a CRE lawyer would expect adjacent to an exclusions list; and no one read the source. Everyone read the report about the source.
>
> **Standing rule (now in CLAUDE.md):** a claim about what a document contains requires a verbatim quote and a location, or it must be marked unverified. Characterizing content without quoting it is where fabrication enters.

- **Minor `d3e62ead` (7,115 chars):** Extracts the same opening, the beginning of the Operating Expenses definition (items in scope), then ends at `"ses or that varies with occupancy or use. Base Rent, Tenant's Share of Operating Expenses and all other amounts payable by Tenant to Landlord hereunder are collectively referred to herein as 'Rent.'"` — this is a sentence boundary, not a truncation, but it cuts off before the exclusions, the reconciliation mechanism, and the audit rights.

**Legal consequence:** An evaluator working from d3e62ead LP-07 sees what Operating Expenses include but not what they exclude. The exclusions list, the Annual Statement reconciliation, and the Independent Review audit rights are absent from d3e62ead. These are the provisions that bound and police the tenant's operating expense exposure — the exact terms that determine coverage risk. **This finding stands. Only the fabricated cap has been removed from it.**

#### LP-12 — Delivery / Acceptance of Premises (+3,959 chars in modal)

Both hashes share 1,561 chars (the Delivery obligations and 120-day termination right). Then they diverge:

- **Modal `f7f64b5c`:** After the termination right provision, continues with: "Tenant acknowledges and agrees that following the Commencement Date, Landlord may require access to portions of the Premises in order to complete Landlord's Work..." (Landlord's Work access rights, tenant's obligations during construction, disclaimer clause).

- **Minor `d3e62ead`:** After the termination right provision, continues with: "Notwithstanding anything to the contrary contained in this Lease, Tenant and Landlord acknowledge and agree that the effectiveness of this Lease shall be subject to the following condition precedent ('Condition Precedent'): Landlord shall have entered into a lease termination agreement..." — a condition precedent tied to the existing tenant vacating.

**Legal consequence:** These are different substantive sections of the lease routed to LP-12 in different runs. The minor hash captures the Condition Precedent (lease effectiveness depends on prior tenant vacating) — a significant tenant protection. The modal captures the Landlord's Work access rights — a potential burden on tenant. They're not the same clause, and an evaluator working from one would not see the other.

#### LP-28 — Use / Compliance (+3,722 chars in modal)

Both share the Section 7 Use clause (ADA, Legal Requirements). Modal continues with compliance obligations including:
- Landlord's responsibility for Common Area compliance as of Commencement Date
- Future compliance costs allocation between landlord/tenant
- ADA specialist disclosure (California Civil Code 1938(a))
- Miscellaneous provisions including attorney's fees, integration clause

Minor truncates after the basic Use clause. Legal consequence: landlord compliance obligations and cost allocation between parties (Operating Expense vs. tenant direct cost) are absent from the minor hash.

#### LP-03 — Commencement Date / Term (+904 chars in modal)

Both share the Base Term definition (835 Industrial Lease cross-reference). Modal continues with Landlord's Work access provisions and the acknowledgment/delivery confirmation mechanism. Minor stops at the same depth as modal but without the Landlord's Work section.

#### LP-05 — Permitted Use (+205 chars in modal)

Modal includes the page-1 "Permitted Use: Research and development laboratory, related office..." definition from the key-terms table before the Section 7 clause. Minor starts directly at Section 7. The permitted use definition is a key boundary on what tenant may do with the space.

#### LP-00 — Parties & Premises (−1,186 chars in modal; minor has MORE)

Unusual: the minor hash d3e62ead has 1,186 more chars in LP-00. Modal ends at 990 chars (the identifying parties, Building, Premises, Project description). Minor continues with: Rent Adjustment Percentage (3%), Base Term definition (the 835 Industrial Lease cross-reference), and the full Base Term expiration mechanics. These are key quantitative terms: the 3% annual rent adjustment is absent from the modal hash's LP-00.

---

### Decision 3 — LP-07 percentage table: confirmed finding

**The table is in LP-00, not LP-07, under Gemini extraction.**

- The key-terms table (Tenant's Share 100%, Building's Share 45.79%, Rent Adjustment 3%) is at char 1,994 in the source document.
- In the `d3e62ead` extraction (minor hash), LP-00 contains this table in full (confirmed above — 2,176 chars including "Tenant's Share of Operating Expenses of Building: 100%" and "Building's Share of Project: 45.79%").
- In the `f7f64b5c` extraction (modal hash), LP-00 is only 990 chars and does NOT include the table — it stops at the Project description.

**Search across 101 Gemini-primary pipeline result files: 0 hits for the table in any LP.**

This means LP-00 in the pipeline results either (a) doesn't include this content when going through Stage 5, (b) LP-00 is filtered out before evaluators (it's an `identity_check: true` provision), or (c) the table was never reaching evaluators in any pipeline run.

The 418c run that contained the table in LP-07 was confirmed to be gpt-5.5, not Gemini. So: **under Gemini extraction, the key-terms table has never appeared in LP-07. In most Gemini runs, it appears in LP-00 (which is identity-check only, not evaluated for coverage). In f7f64b5c (modal, 8/10), it doesn't appear in any LP at all.**

**Which LPs need the table values:**
- LP-07 (Operating Expenses): needs Tenant's Share (100%) — Gemini's LP-07 contains the clause defining Operating Expenses, which references "Tenant's Share" without quantifying it. The 100% figure is only in LP-00.
- LP-02 (Rent/Rent Escalation): needs Rent Adjustment Percentage (3%) — this appears in LP-00 (minor hash only) but not in LP-02 directly.
- LP-03 (Commencement Date): contains the Base Term definition which references the target date (August 1, 2019) — the target commencement date may be in the LP-03 text depending on hash.

---

## Schema Finding — Decision 1 Mechanism

The extraction schema has a `status` field with values: `FOUND_BOTH`, `TEMPLATE_ONLY`, `TENANT_ONLY`, `AMBIGUOUS`.

Stub provisions (LP-20, LP-21, LP-23, LP-31) return: `status=AMBIGUOUS`, `tenant_text=""`, `alignment_notes="No [X] found in the document."` The schema has no `NOT_APPLICABLE` state. Gemini uses `AMBIGUOUS` for both "provision genuinely absent from this lease type" and "couldn't determine if present."

Gate 3 rescoping mechanism (not yet implemented):
- Allow empty `tenant_text` when `provision_id` is in known-absent set for this lease type AND `alignment_notes` contains "not found" or similar language
- Hard-fail any provision NOT in the known-absent set with empty `tenant_text`
- Known-absent set for industrial/warehouse: `{LP-20, LP-21, LP-23, LP-31}`

The latent bug: an extraction failure on LP-07 would produce `status=AMBIGUOUS, tenant_text=""` — which the rescoped gate correctly rejects because LP-07 is not in the known-absent set.

---

## Step 423 (Policy Resimulation)

**Blocked pending 422.** Cannot rerun policy simulation until a clean baseline extraction is frozen.

---

## Action Required

This step is **STOPPED** pending Chat decisions on the 3 decisions above. Updated findings below.

**Decision 1 (stubs):** Mechanism confirmed. LP-20/21/23/31 correctly absent. Schema uses `AMBIGUOUS` as catch-all; no `NOT_APPLICABLE` state exists. Gate 3 rescope: allow known-absent set, hard-fail all others. Implementation ready when authorized.

**Decision 2 (freeze):** Do not freeze. N=10 confirms 2 hashes (8/10 vs 2/10), and the modal itself shifts across sample sets (was 4/5 d3e62ead in N=5, now 8/10 f7f64b5c in N=10). The 6 variable LPs contain material legal content that differs between runs: Operating Expense exclusions/cap (LP-07), Condition Precedent (LP-12), compliance cost allocation (LP-28). Freezing either hash chooses which legal protections the evaluators see.

**Decision 3 (table):** The key-terms table (100%/45.79%/3%) is in LP-00 under Gemini extraction (minor hash only; absent from LP-00 in modal). It has never appeared in LP-07 under any Gemini run. It appeared in LP-07 only under gpt-5.5 (418c). The values needed for operating expense and rent assessment are not reliably reaching any LP's tenant_text under Gemini.
