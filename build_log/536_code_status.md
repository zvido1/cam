# Step 536 — Four retail fixtures added. Three true positives for LP-20, and one document that answers all four concepts.

**Date:** 2026-09-03 · **Instruction:** `build_log/536_chat_instruction.md`
**FETCH AND CONVERT ONLY. No pipeline runs, no clue list touched, not deployed.**
**All four converted cleanly — the 2002 filings did NOT produce garbage.**

---

# THE HEADLINE

**The uniform-absence deadlock is broken.** The corpus now contains **three genuine exclusivity
covenants** and **one genuine percentage-rent regime** — the concepts that were absent from all nine
prior leases and that blocked Steps 520, 535 and the degrade decision.

**And `carothers_bakers_bridge` answers all four concepts by itself**, with three true negatives that
carry heavy lexical presence. That is the document that can falsify a naive matcher *and* validate a
context-aware one.

---

# 1. CONVERSION QUALITY — CHECKED BEFORE TRUSTING

```
fixture                        chars   headings  printable  avg word  first line
bjs_esplanade_oxnard          178865      2        0.985      5.1     "ESPLANADE SHOPPING CENTER / SHOPPING CENTER PAD GROUND LEASE"
carothers_bakers_bridge       149786    213        0.991      5.2     "CAROTHERS at BAKERS BRIDGE, LLC, LANDLORD / THE BANK OF NASHVILLE, TENANT"
butler_crossing_outlot        242900      8        0.979      5.1     "Butler Outlot 5 Associates, L.L.C. / Fast Casual Concepts, Inc."
springfield_shoppes_DRAFT     255566    107        0.989      5.3     "DRAFT April 10, 2019 / SHOPPING CENTER LEASE"
```

**No garbage.** Printable ratios 0.979–0.991, average word length 5.1–5.3, coherent opening text. The
brief's concern about the 2002 filings did not materialise — both 2002 exhibits (`bjs`, `carothers`)
converted as cleanly as the 2019/2020 ones.

## Heading counts, against the baseline

```
carothers_bakers_bridge   213    <- HIGHEST of any document in the corpus
springfield_shoppes       107
Atlas (synthetic)          89
butler_crossing             8
bjs_esplanade               2
quanterix                  14
divall                      0
```

**`carothers` at 213 and `springfield` at 107 both exceed Atlas's 89.** The locator has never been
tested above 89 headings on a real document; it now can be.

**`bjs_esplanade` at 2 is the interesting counterpart** — a rich retail lease with almost no parseable
headings, which pairs with solidpower (1 heading) as a locator floor case.

---

# 2. GROUND TRUTH BY READING — ALL FOUR CONCEPTS, ALL FOUR DOCUMENTS

| document | LP-20 exclusivity | LP-23 percentage rent | LP-21 guaranty | LP-12 early termination |
|---|---|---|---|---|
| **bjs_esplanade_oxnard** | **YES** | **YES** | NO | NO |
| **carothers_bakers_bridge** | **YES** | **NO** (struck through) | **NO** (`NA`) | **NO** (option is renewal) |
| **butler_crossing_outlot** | **YES** | NO | **YES** | NO |
| springfield_shoppes_DRAFT | **NO** (mislabelled) | NO | form exhibit | NO |

## bjs_esplanade — exclusivity AND percentage rent, both real

> **§8.2 Exclusive Use.** *"Notwithstanding anything to the contrary set forth in the Lease, after the
> Date of Lease, Landlord shall not execute any lease for premises located within the Shopping Center
> to any other 'Competitive Store'..."*
> Lease Summary: *"Exclusive Use: (Section 8.2) The Landlord shall not lease space in the Shopping
> Center to another tenant whose primary business is the operation of a brewery restaurant."*

> **Percentage rent.** *"Five percent (5%) above $7,000,000.00 in Gross Sales each calendar year (the
> 'Gross Sales Breakpoint')"*, with §3.2.1 governing *"...pay any Percentage Rent until such time as
> Tenant's Gross Sales for each calendar year exceed the Gross Sales Breakpoint..."*

**The first genuine percentage-rent regime in the corpus.**

## carothers_bakers_bridge — THE VALUABLE ONE

**Exclusivity: YES, with the termination remedy the brief predicted:**
> **§2.8. Tenant Exclusive.** *"So long as Tenant is open and operating its business... Landlord
> covenants and agrees that during the Term hereof, no space in the Shopping Center will be leased or
> allowed to be leased for a full service financial institution as described in Section 1.8."*
> Remedy: *"...(ii) terminate this Lease, which right Tenant shall elect by delivering to Landlord
> further written notice..."*

**Percentage rent: NO — and it is lexically everywhere.**
> *"1.10 Percentage Rent (Section 5.4): **NA**"*
> *"Section 5.4. Percentage Rent. **This Section was lined through (deleted).**"*

**A percentage-rent section that was struck out in negotiation.** The phrase appears in the table of
contents, in the Basic Lease Provisions as `NA`, and in a section marked deleted. **A substring matcher
fires; the correct answer is not_applicable.**

**Guaranty: NO — same shape.**
> *"1.14 Guarantor(s): **NA**"*
> §28.13: *"In the event that there is a guarantor of this Lease, said guarantor shall have..."* — a
> conditional reference to a guarantor who does not exist.

**This is the everbridge LP-21 false-positive shape** — *"any such guarantor"* — but here with a known
answer.

**Early termination: NO.** §2.7 is *"Option to Extend Term"* — a renewal option, not an early-termination
right. **Another false-positive shape with ground truth.**

## butler_crossing_outlot — exclusivity and a real guaranty

> **A.13 Exclusive Use and Restricted Uses.** *"As a material inducement for Tenant to enter into this
> Lease, Landlord hereby agrees as follows: a. Landlord shall not lease, rent, occupy or permit any
> other premises in the Shopping Center to be occupied... for the operation of a single price point
> variety retail store ('Exclusive' or 'Exclusive Use')"*

> **Guaranty.** *"Guarantor hereby guarantees the full and prompt payment of rent and other leasehold
> charges required to be paid by Tenant pursuant to and under the Lease, together with the full
> performance and observance of all covenants..."*

**The first genuine guaranty in the corpus.** It also carries an *"Existing Exclusives"* schedule
listing other tenants' exclusive-use clauses — a second, different context in which the phrase appears.

## springfield_shoppes — TWO PROBLEMS, AND I RECOMMEND EXCLUDING IT

**1. It is a DRAFT, not an executed lease.** Header: *"DRAFT April 10, 2019"*. It carries form
annotations — *"Exhibit D Guaranty of Lease **[may be deleted]**"* — so it is a template with optional
clauses, not an agreement between identified parties. Landlord and tenant are not named.

**2. Its "EXCLUSIVE USE COVENANT" is not one.** Exhibit F, read in full:
> *"EXHIBIT F EXCLUSIVE USE COVENANT. 1. Notwithstanding anything in the Rules and Regulations... **Tenant
> shall not conduct any operations** within the Shopping Center for the following purposes: No portion
> of the Springfield Property shall be used for any: a. a manufacturer's or outlet center; or b. a
> store operated by a merchandise manufacturer selling at a discount..."*

**That is a restriction ON the tenant — prohibited uses — under a heading literally named "EXCLUSIVE
USE COVENANT".** It is the reverse of an exclusivity covenant.

**It is written to disk and recorded in the manifest with `_DRAFT` in its slug and the status in its
`work_scope_note`, but I recommend it not be used for measurement.** Ground truth on a draft form is
ground truth about a template, not a lease. **Its value, if any, is as a hard negative for the LP-20
heading case — and that is worth having, but only if labelled.**

---

# 3. WHAT THIS UNBLOCKS

| blocked question | now answerable because |
|---|---|
| Step 520 — LP-07 clue set | 3 more real leases, and 2 with heading structure above Atlas |
| Step 535 — negation rule | **3 true positives for LP-20** to test recall against, where the corpus had zero |
| the conditional degrade | `carothers` supplies a true negative for LP-21 and LP-23 **with lexical presence**, which is the exact case the degrade would act on |
| LP-20 subject-error (Step 535 survivor) | `carothers` §18.2 has *"Landlord shall have the exclusive right to use all or any part of the roof"* — the same Landlord-subject shape as everbridge, in a document that ALSO has a real tenant exclusive |

**`carothers_bakers_bridge` contains both the false-positive shape and the true positive for LP-20.**
A matcher must fire on §2.8 and not on §18.2, in the same document. **No existing fixture could pose
that test.**

---

# 4. WHAT WAS WRITTEN

```
05 Lease Analyzer/test_data/tenants/bjs_esplanade_oxnard_lease.txt        178,865 ch  sha 7dc741527366ea9c
05 Lease Analyzer/test_data/tenants/carothers_bakers_bridge_lease.txt     149,786 ch  sha 7a14b66d731a71ba
05 Lease Analyzer/test_data/tenants/butler_crossing_outlot_lease.txt      242,900 ch  sha 0e8df550ec6c7ff6
05 Lease Analyzer/test_data/tenants/springfield_shoppes_DRAFT_lease.txt   255,566 ch  sha f1460e2f9d18c049
05 Lease Analyzer/test_data/edgar_corpus_manifest.json                    8 -> 12 leases
```

Built with `build_edgar_corpus.py`'s own `_edgar_get`, `extract`, `build_header` and `content_hash`, so
the User-Agent, 0.15 s rate limit, cache and header format match the existing eight exactly. **The
eight existing fixtures were not touched** — I did not run the full builder, precisely to avoid
rewriting fixtures that prior measurements depend on.

Manifest entries carry every field the convention requires: slug, tenant, landlord, address,
property_type, jurisdiction, effective_date, accession, exhibit, cik, fixture_path, content_hash,
source_url, licensing_note.

---

# WHAT IS NOT ESTABLISHED

- **No pipeline was run.** Extraction, coverage, the gate and the matcher have never seen any of these
  four. Heading counts are from `_build_heading_index`; everything else is reading.
- **Ground truth covers the four named concepts only.** The other 29 LPs were not assessed on any of
  these documents.
- **`bjs_esplanade`'s effective date is blank in the filing** — *"entered into as of , 2001"*. I
  recorded `2001-01-01` as a placeholder; the true execution date is not in the exhibit.
- **`butler_crossing`'s tenant d.b.a. was truncated in extraction** (`Fast Casual Concepts, Inc.,
  a Pennsylvania corporation d.b.a "I..."`). The trade name is not captured in the manifest.
- **`springfield_shoppes_DRAFT` should not be used for measurement** without a decision. It is written
  and labelled, not silently included.
- **I did not verify that these four extract cleanly through the pipeline's own parser under load** —
  only that `parse_document` reads them and the heading index runs.
- **No clue list was changed and nothing was deployed.**
