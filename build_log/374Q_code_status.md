# Step 374Q — Status: relabel-only containment (PROVISIONAL), NO count/routing/logic change
**Date:** 2026-06-03  **Version:** app.js v461 → **v462** (index.html `?v=462`).
**Scope:** lawyer-facing WORDING/RELABEL only. No change to `hard_flag`, escalation, bucket routing,
the rollup/tie-break/ladder, the `or "moderate"` default, Risk/Needs-Review/Priority-Risks TOTALS, or
how confidence is computed. Authorized by the 374P exit criteria (C2+C3 ≈ C4 pass all three).

---

## What changed (all in `05 Lease Analyzer/static/app.js`)

### 1. Display-only provenance helper (new)
`_lpProvenanceFlags374Q(finding)` + `_camRoll374Q` / `_camSeverity374Q` / `_CAM_VERDICT_RANK_374Q`
mirror `build_log/_374p_recompute.py` EXACTLY (same RANK, pessimistic/optimistic plurality rollup with
tie-break, severity bands). Returns two display-only flags derived from the finding's own
`element_verdicts` + `use_impact` (no new backend field needed — the raw data is already in the render
payload):
- `tieDerivedSevere` — production severity is `severe` but the SAME per-evaluator verdicts rolled
  *optimistically* are NOT severe → the "severe" disagreement is a pessimistic-tie-break artifact.
- `consequenceDefaulted` — `use_impact` absent (defaulted-moderate) or `materiality` empty (not assessed).

Changes NO count/routing/flag — used only to pick a truthful label and withhold unsupported wording.

### 2. `_reviewSubtypeOf` — withhold "conflicting reading" for artifact-based findings
A coverage LP floored to Needs Review by the 373C hard_flag (`hard_flag === true && state !== 'review_needed'`)
**stays in Needs Review** but is routed to its TRUTHFUL subtype instead of `conflicting_reading`:
- `consequenceDefaulted` → **`consequence_not_assessed`** (transparent; no implied assessed consequence)
- else `tieDerivedSevere` (assessed) → **`coverage_question`** (real coverage basis, not a supported conflict)
- else → **`conflicting_reading`** (genuine, non-artifactual disagreement — preserved)

The finding is NOT dropped and NOT moved out of Needs Review — only its subtype label changes.

### 3. Action Summary subtype line — new transparent part
`_computeRiskCounts.reviewSub` gains `consequenceNotAssessed`; the Needs-Review subtype line now reads
`… coverage question(s) · N consequence not assessed · possible one-sided term(s) · conflicting reading(s)`.
The four subtypes still SUM to the (unchanged) Needs Review total.

### 4. Sidebar — new "Consequence Not Assessed" sub-header
Split out from Coverage Questions and from the withheld "Conflicting Reading" group. Mirrors the shared
`_reviewSubtypeOf` classifier (single source). Needs Review section total unchanged.

### 5. "Confidence capped at low" dropped for tie-derived severe banners
In the LP-level severe header (`cv-lp-sev-header-severe`), the `Confidence capped at <x>.` clause is now
withheld when `tieDerivedSevere === true` (the cap rode in on the same tie-break artifact, per 374P). For
genuine low-confidence severe signals (`tieDerivedSevere === false`) the cap note is KEPT. Wording only —
confidence is not recomputed. (The moderate-branch cap note is unchanged; `tie_derived_severe` is a
severe-only flag.)

### 6. Version bump
`index.html`: `app.js?v=461` → `app.js?v=462`.

---

## Validation (real `_reviewSubtypeOf` extracted from v462, run against both pipeline JSONs)

Review-bucket hard_flag-floored items (LP-28/LP-32 are risk-bucket Priority Risks → `_reviewSubtypeOf`
never called on them, so they're untouched):

| run | conflicting_reading | consequence_not_assessed | coverage_question (relabeled) | per-LP |
|---|---|---|---|---|
| 030920 | **0** | 1 | 0 | LP-06 → consequence_not_assessed |
| 181402 | **2** | 1 | 1 | LP-02/LP-20 → conflicting_reading; LP-06 → consequence_not_assessed; LP-16 → coverage_question |

- **conflicting_reading: 030920 → 0, 181402 → 2 = exactly {LP-02, LP-20}** (the genuine, `unique_plurality`,
  assessed ones). MATCHES the 374Q target.
- De-labeled artifact findings (incl. LP-06) **remain IN Needs Review** under a truthful subtype — none dropped.
- **Needs Review TOTAL unchanged** (030920 = 24, 181402 = 12): every floored item stays in the review
  bucket; only the subtype label moves (conflicting → consequence_not_assessed / coverage_question).
- **Risk + Priority Risks totals UNCHANGED.** `classifyFindingType` / `isPriorityReview` untouched; LP-28/LP-32
  stay in Priority Risks (they are risk-bucket; their only 374Q effect is the wording-only banner drop).
- **LP-06 defaulted consequence** now shows "consequence not assessed" transparently, not an implied value.
- **Evidence trail intact** — no finding removed from any bucket or from the element-level evidence.
- `node --check "05 Lease Analyzer/static/app.js"` → clean.

CONFIRM: Priority Risks untouched — LP-28/LP-32 still present (their basis question is the next recompute,
374R-Q, NOT this step).

## Provisional marker
This containment is **PROVISIONAL**, pending calibration across more contracts (n=2 today). Marked
in-code at the helper and at each relabel/banner site (`Step 374Q (PROVISIONAL)`).

## Out of scope / not done (as instructed)
- No Priority-Risks change (LP-28/LP-32 basis = next recompute 374R-Q).
- No change to hard_flag / escalation / routing / counts / Priority designation / taxonomy / rollup /
  tie-break / ladder / `or "moderate"` default. The provenance flags are derived display-side only.
- Provenance plumbing wording is NOT placed on the Action Summary; the executive surface shows only
  outcome wording ("consequence not assessed", withheld "conflicting reading"). Detailed derivation
  stays in Evidence/Audit.

## Decisions Needed
None.
