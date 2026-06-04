# Step 375H — Status: Directional Recall Audit, Parts A + B (READ-ONLY; Part C keyed, pending)
**Date:** 2026-06-03  **Run:** `lease_review_20260604_033046_52adbf` (0604). **NO production change.** Part C
(synthetic fixtures, keyed) is written-but-not-here — it waits per the brief.

## ONE-LINE VERDICT
**The dominant bypass mechanism is a SCHEMA DEFECT** — the coverage rubric scores "present/covered" on
**topical element presence with no protective-direction check**, and the consent/approval elements have no
encoded reasonableness counterpart (a one-sided "sole discretion" clause satisfies them). It is
**architecturally confirmed (Part A) but only marginally live in THIS lease (Part B: 1 of 6 not-flagged LPs,
LP-09)**. Where the schema DOES encode polarity (LP-13 indemnity: `mutual_vs_one_way` / `landlord_indemnification_scope`),
the architecture detects balance correctly. Stage-7 gating is a contributing-but-secondary factor (it's the
schema's topical "covered" that lets one-sided clauses arrive at the gate already labeled covered).

---

## Part A — the deterministic mechanism (exact quotes + line numbers)

### A1. Stage-7 eligibility — is coverage-flag the sole gate? (lease_synthesis.py)
`_FLAGGED_STATES` (lines 30-35) and the gate in `_collect_flagged_lps` (line 883):
```python
_FLAGGED_STATES = frozenset({ "missing", "partial_material", "partial_typical", "review_needed" })
...
if state in _FLAGGED_STATES or pcls in {"partial_material", "partial_typical"}:   # line 883
```
plus a conflict path: `_FLAGGED_CONFLICT_SEVERITIES = frozenset({"HIGH", "MEDIUM"})` (line 36).
- **`covered`, `covered_unfavorable`, `not_applicable`, and `partial`+`partial_review` are NOT flagged** →
  they never enter directional review (Q2).
- **The only back-door is the conflict path** (an LP in a HIGH/MEDIUM `conflicts[]` entry). But conflicts are
  contradiction-detection, **not** one-sidedness, and on the 0604 run `conflicts = []` (zero) — so **for
  one-sidedness, coverage-flag is effectively the sole gate.** A present-but-one-sided `covered` clause with
  no conflict bypasses Stage 7 entirely.

### A2. Q2a/Q2b conflation — absent vs wrong-direction collapse into one `no` (CONFIRMED verbatim)
`_EVALUATOR_SYSTEM` (lines 253-269):
```
Q2a — DIRECTION: ...
   yes     = protection exists and runs toward the right party
   no      = protection runs toward the wrong party, or is absent          # line 256
...
MISMATCH FLAG: Raise mismatch_flag = true when EITHER:
   - Q2a = "no"  (wrong direction or absent)                                # line 268
```
**`absent` and `wrong-direction` are fused into a single Q2a = "no"** → `mismatch_flag`, with no field
separating them. (`q1_verdict = no_coverage_found` separately marks *absent*, but Q2a itself does not.)

### A3. Distinct output for absent / present-one-sided / present-disproportionate?
The output object (lines 235-245) has `q2a_verdict (yes|no|unclear)`, `q2b_verdict
(proportional|disproportionate|not_applicable)`, `mismatch_flag`, `directionality
(tenant_unprotected|landlord_unprotected|match)`, `exposed_party`.
- **(c) disproportionate IS distinguished** — `q2b = "disproportionate"` with `Q2a = "yes"` (lines 259-269).
- **(a) absent vs (b) present-one-sided are NOT distinguished** by the directional fields — both → `Q2a =
  "no"`. The only disambiguator is `q1_verdict` (absent = `no_coverage_found`), not Q2. And the
  candidate-generation trigger `_collect_directional_candidates` reads **only `mismatch_flag`** — which fuses
  all three. `directionality` carries the *direction* (who's exposed) but not *absent-vs-present*.

### A4. THE CRUCIAL ONE — what does "covered" / a "present" verdict MEAN?
**Answer: (i)/(iii) — TOPICAL element presence + schema-element satisfaction WITHOUT polarity/protective-direction
review.** The coverage-stage verdict semantics (lease_coverage_305.py, lines 190-196):
```
- explicitly_present: The element appears as literal or near-literal text. ...          # line 191
- implicitly_present: Same-LP text functionally satisfies the element ...               # line 192
```
"Present" = the expected ELEMENT (its topic) appears in the text — **no check on which party it favors.** The
schema elements then determine whether direction is checked at all:
- **Consent-type (LP-09 Subletting & Assignment) — NO protective-direction element:**
  - `assignment_requires_landlord_consent` (must_be_explicit) — *"Assignment requires landlord consent"* —
    landlord-control; a "sole discretion" clause **satisfies** it.
  - `consent_standard_supplied` — *"Consent standard is supplied by lease text or applicable default law"* —
    checks that **A standard exists**, not that it is **reasonable/tenant-protective**. There is **no element
    "consent not unreasonably withheld."** → topical presence only.
- **Approval-type (LP-10 Alterations & Improvements) — NO protective-direction element:**
  - `approval_threshold` — *"Threshold for required landlord approval is defined (dollar amount or scope)"* —
    *"all alterations require landlord consent, sole discretion"* **defines the scope** → satisfies. No element
    "approval not unreasonably withheld" / "tenant may make non-structural alterations without consent."
- **Counter-example (LP-13 Indemnification) — schema DOES encode polarity:** `mutual_vs_one_way` (adv=tenant),
  `landlord_indemnification_scope` (adv=tenant), `negligence_carveouts` (adv=tenant). So polarity **can** be
  checked — where the schema encodes a protective-direction element.

**Load-bearing conclusion:** because "present" = topical presence with no polarity check, and the
consent/approval LPs lack protective-direction elements, a present-but-one-sided clause scores **covered →
bypasses Stage 7**. **This is a SCHEMA defect**, not (primarily) a Stage-7 gating problem.

---

## Part B — live scan of the 0604 run (every NOT-flagged LP)
26 LPs flagged into Stage 7; **6 NOT flagged** (0 conflicts fired). Per-LP classification:

| LP | name | coverage_state | present landlord-favorable / one-sided lang? | classification |
|---|---|---|---|---|
| **LP-09** | Subletting & Assignment | covered | **YES** — consent required + `landlord_recapture_right` ("Landlord may recapture"), `unauthorized_transfer ... void`; consent has **no reasonableness element** | **SCHEMA DEFECT** |
| LP-08 | Insurance Requirements | covered | landlord-additional-insured, CGL minimum, **mutual** waiver of subrogation | NO credible bypass (standard insurance allocation) |
| LP-13 | Indemnification & Liability | covered | broad tenant→landlord indemnity (11.1) **BUT** reciprocal landlord→tenant indemnity (11.2), mutual consequential-damages exclusion (11.3), negligence carve-outs | NO credible bypass (genuinely mutual; schema polarity worked) |
| LP-12 | Early Termination | not_applicable | — | NO credible bypass (genuinely N/A) |
| LP-23 | Percentage Rent | not_applicable | — | NO credible bypass (genuinely N/A) |
| LP-31 | Co-Tenancy | not_applicable | — | NO credible bypass (genuinely N/A) |

### COUNT per classification (of 6 not-flagged)
- **SCHEMA defect: 1** (LP-09)
- EVALUATOR defect: **0**
- TRUE directionality gap: **0**
- NO credible bypass: **5** (LP-08, LP-12, LP-13, LP-23, LP-31)

### LP-09 detail (the one live bypass)
12 elements; **10 landlord-favorable / neutral, only 2 near-protective** (`affiliate_transfer_exception_defined`
adv=tenant; `consent_standard_supplied` adv=None). Run verdicts: consent-required (present), recapture
(present, *"Landlord may elect to recapture ... by written notice"*), void-on-unauthorized (present),
consent_standard_supplied (present — a standard exists), affiliate-exception (present). The 4 missing are all
landlord-favorable (favorable absences post-374Z). So LP-09 = a landlord-controlled assignment clause (consent
with no reasonableness requirement + recapture right) scoring **covered** and **never entering directional
review** — because the schema never asks "is consent unreasonably withholdable?"

### LP-13 detail (why it is NOT a bypass — the architecture working)
Citations: 11.1 tenant→landlord indemnity; **11.2 "Landlord shall defend, indemnify, and hold harmless
Tenant ... from any and all claims"** (genuine reciprocal); 11.3 *"Neither party shall be liable ...
consequential ..."* (mutual); negligence carve-out *"to the extent caused by Landlord's negligence."* The
schema's protective-direction elements (`mutual_vs_one_way`, `landlord_indemnification_scope`,
`negligence_carveouts`) were genuinely satisfied → balanced article → correctly covered. (Minor note:
`liability_cap` is satisfied by a *landlord*-favorable cap — topical satisfaction; a schema-precision quibble,
not a live one-sided bypass.)

### Favorable / neutral inspection
The run's `favorable_or_non_adverse_absences` (374Z) on the not-flagged set are landlord-control elements that
are *absent* (LP-08, LP-09) — correctly favorable to tenant, no concealment. The one-sidedness risk here is
in **present** landlord-favorable terms (LP-09 recapture/consent), captured above — not in the favorable
absences.

---

## Implementation OPTIONS (no change; different defects → different fixes; do NOT pre-pick)
1. **Schema element-polarity fix (targeted, addresses the Part-A root):** add protective-direction elements
   where missing — e.g. LP-09 "consent may not be unreasonably withheld / tenant affiliate transfers without
   consent", LP-10 "alterations approval not unreasonably withheld / non-structural alterations permitted
   without consent", and reciprocity elements for one-way-prone LPs. A one-sided clause then **fails** a
   protective element → not `covered` → flagged into Stage 7. LP-13 shows this pattern already works where
   encoded.
2. **Evaluator-prompt polarity annotation:** have the coverage evaluator tag a `present` verdict with
   protective-direction (favors-tenant / favors-landlord / neutral). Broader; risk of noise; doesn't fix the
   missing-element gap.
3. **Independent directional candidate path:** run Stage-7 Q2 directional review on ALL applicable LPs (not
   only flagged), so present-but-one-sided clauses get directional review regardless of coverage_state.
   Heaviest; the brief explicitly says **do not prejudge** this as the fix.
4. **Fixture-gated-only:** treat Part B's "1/6 live" as inconclusive on its own and gate any change on Part C
   synthetic fixtures (deliberately one-sided consent/access/alterations/remedies clauses) — per the brief's
   "do not let one lease exonerate the architecture."

**Leading read (not a decision):** Part A confirms a real SCHEMA root; Part B shows it is only marginally live
here (LP-09) and that the schema CAN check polarity where it encodes it (LP-13). So the targeted **schema fix
(1)**, **validated by Part C fixtures (4)**, is the most proportionate path; the all-LP directional path (3)
is the heavier alternative only if fixtures show schema fixes insufficient.

## Framing (separate workstream — three distinct directional problems)
(i) vote-count-as-severity [375E-DIR]; (ii) Pass-1 candidate-generation variance [375D-2 / recall
governance]; (iii) **coverage-gated bypass of adverse PRESENT terms [this audit]** = a SCHEMA-polarity recall
problem, NOT folded into 375E-DIR. External-use pause on Stage-7 directional Risk totals holds.

## Decisions Needed
1. Run Part C keyed fixtures (Code writes separately) before choosing option 1 vs 3.
2. Confirm the SCHEMA-polarity-element direction (option 1) as the leading hypothesis for the recall fix.
