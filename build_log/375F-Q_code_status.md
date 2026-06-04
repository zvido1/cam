# Step 375F-Q — Status: is `use_impact.use_reasoning` surfaced, or only the badge? (READ-ONLY)
**Date:** 2026-06-03  **Run:** `lease_review_20260604_033046_52adbf` (0604). **NO production change.**
**Verdict up front:** the use-driven reasoning is **shown prominently WHERE it exists** (Key Issues card
body, default-visible) — but it **exists for only 8 of 29 coverage LPs (28%)**; the other **21 (72%) have no
`use_impact` at all**, so there is no use-driven consequence to show. The gap is "**not computed for most**,"
not "computed-but-buried." Separately, the at-a-glance triage line and the Evidence view show only the bare
materiality label, never the reasoning.

## Q1 — Where `use_impact.use_reasoning` renders (grep `use_reasoning` in app.js)
| surface | renders use_reasoning? | line | prominence |
|---|---|---|---|
| **Key Issues main-panel card** (`renderCoveragePanel`→`buildItem`; tab `coverage`="Key Issues", app.js:8411-8420) | **YES** | **16655-16662** | **Card body, default-visible** (inline after the exposure statement, not behind an expand). Adverse → `⚠ Tenant-specific concern — <use_reasoning>`; favorable / neutral-low have their own labels. For LP-16 it shows the full "…truck and trailer staging areas critical for daily loading…" prose. |
| **Key Issues sidebar item** (`_navBuildUnifiedItem`, triage line) | **NO** | 18221-18228 | Shows bare `Consequence: High · Confidence: low · Disagreement: severe` (`_navCoverageTriageFields`, 18159-18173 — **no use_reasoning field**) + the headline summary. |
| **Evidence view LP block** (`_buildLpBlock`) | **NO** | 8067-8069 | Shows a bare `high impact` badge (`use_impact.materiality`); the reasoning prose is not rendered. |
| **`dominant_reason`** (risk-level helper) | partial | 5012 / 5015 | Includes use_reasoning ONLY for `favorable` / low-impact branches; the **adverse-high** branch (LP-16's case, 5049) returns a generic "Adverse coverage at viewer perspective" with **no** reasoning. |

So `use_reasoning` is **not** never-shown and **not** Audit-only: it renders **card-level on the Key Issues
card (16660)**. But the quick-scan surfaces a lawyer reads first — the **sidebar triage line** and the
**Evidence badge** — carry only the bare `Consequence: High` / `high impact` label.

## Q2 — `use_impact` field inventory: surfaced vs dropped
Fields present across the run: `gap_impact`, `materiality`, `confidence`, `evaluator_agreement`,
`use_reasoning`. Per field, lawyer-facing rendering:

| field | example (LP-16) | surfaced? |
|---|---|---|
| `materiality` | `"high"` | **YES** — "Consequence: High" (sidebar 18162/18222), "high impact" badge (Evidence 8068). |
| `use_reasoning` | "…truck and trailer staging areas critical for daily loading…" | **Partial** — Key Issues card body only (16660); NOT in sidebar/Evidence. |
| `gap_impact` | `"adverse"` | **Indirect** — selects the note label ("Tenant-specific concern" vs "Favorable") at 16658-16660; not shown as a value. |
| `confidence` | `"assert"` | **NO** — never rendered (internal). |
| `evaluator_agreement` | `"3-0"` | **NO** — the use_impact's own 3-0 is never shown (the card's "Disagreement" comes from `verdict_distance`, a different signal). |

So, echoing the `absence_adverse_to` pattern: **`confidence` and `evaluator_agreement` of the assessment are
computed and dropped**, and `use_reasoning` is computed but shown only on one of three surfaces.

## Q3 — Coverage: how many findings even HAVE use-driven reasoning? (the gap size)
Across **29 non-not-applicable** coverage LPs on 0604:
- **8 have populated `use_impact.use_reasoning`** (materiality: 4 high / 3 medium / 1 low) — the use-driven
  "brings it home" message exists and (being adverse) renders at 16660.
- **0** have `use_impact.materiality` present but no reasoning (when use_impact exists, reasoning exists too).
- **21 have NO `use_impact` at all** — the defaulted/floor path: `LP-01, 02, 04, 06, 07, 08, 09, 11, 13, 15,
  17, 18, 19, 21, 22, 24, 25, 27, 28, 29, 30`. These get a table/floor/default materiality with **no
  use-driven consequence prose** of any kind. (Includes Risk cards like **LP-27** — Risk via the
  `_HIGH_MATERIALITY_LPS` floor, with zero use-reasoning.)

**Gap: the use-driven consequence message is computed for ~28% of coverage LPs and absent for ~72%.** Where
present it is shown; where absent there is nothing to show — the dominant problem is non-computation, the
same Stage-5e coverage hole flagged in 374P/375E-PRE-Q.

## Q4 — Does CAM state the consequence of NOT addressing, in plain terms?
**Yes — via `exposure_statement`, for every finding (not only a High/Low label).** It is perspective-aware
consequence-of-inaction prose, shown card-level (`cv-item-stmt`, 16649) AND as the sidebar summary/headline:
- LP-16: *"Parking rights undefined or unprotected; tenant customers and employees may face parking
  restrictions without recourse."*
- LP-27: *"Tenant has no right to perform Landlord's obligations and recover the cost by offsetting rent.
  Tenant bears the cash-flow and operational risk if Landlord fails to act…"*
- LP-03: *"Term and renewal rights unclear; tenant may lose right to remain in premises or face holdover
  penalties."*

So consequence-of-inaction IS spelled out universally (`exposure_statement`), and `use_reasoning` adds a
**use-specific deepening** ("…critical for daily loading and distribution efficiency") for the 28% with an
assessment. The bare "Consequence: High" label is the at-a-glance triage chip, not the only consequence
signal — the prose layer exists.

## One-line verdict
**Computed-and-shown where it exists, but NOT computed for most:** `use_reasoning` renders prominently on the
Key Issues card body (16660) for the **8/29 (28%)** LPs that carry a Stage-5e `use_impact` — while the
**21/29 (72%)** without `use_impact` have no use-driven consequence at all, and the sidebar/Evidence quick
surfaces show only the bare materiality label. (Consequence-of-inaction prose itself exists universally via
`exposure_statement`; the use-SPECIFIC "brings it home" layer is the part missing for the majority.)

## Implication for 375E / a UI step
- The high-value fix is **coverage (compute `use_impact` for more LPs)**, not UI — 72% of LPs never get a
  use-driven assessment (the Stage-5e gate gap). That is where the "brings it home" message is missing.
- Secondary UI lift: carry `use_reasoning` (or a short form) onto the **sidebar triage line** and the
  **Evidence badge**, so the use-specific consequence isn't only on the full card; and consider surfacing the
  dropped `confidence` / `evaluator_agreement` of the assessment in Audit.

## Files referenced (read-only)
- app.js: 16655-16662 (`cv-use-impact-note`, use_reasoning), 16649 (`cv-item-stmt`, exposure_statement),
  18159-18173 + 18221-18228 (sidebar triage, bare label), 8067-8069 (Evidence "impact" badge), 5012/5015
  (dominant_reason), 8411-8420 (`coverage`="Key Issues" → renderCoveragePanel/buildItem).
- Data: `coverage_assessment[*].use_impact` in `lease_review_20260604_033046_52adbf`.

## Decisions Needed
None (diagnosis). Feeds 375E: prioritize closing the Stage-5e `use_impact` coverage gap (72% missing) over UI
re-surfacing; optionally lift `use_reasoning` onto the triage/Evidence quick surfaces.
