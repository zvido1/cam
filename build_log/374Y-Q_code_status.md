# Step 374Y-Q — Status: systematic polarity recompute (READ-ONLY, MEASURE don't enforce)
**Date:** 2026-06-03  **Mode:** read-only analysis. **NO production file modified** — no
derive_lp_state / materiality / routing / schema edit; production byte-identical. Sidecar:
`build_log/_374yq_recompute.py` over existing run JSONs + the live schema. **n=2 → DIRECTIONAL ONLY.**

## Method + fidelity note
Replicated `derive_lp_state` (lease_coverage_305.py:843), `_classify_materiality` / `_classify_partial`
(lease_exposure.py:87/114, incl. `_HIGH_MATERIALITY_LPS={"LP-27"}` and the legacy element sets), and the
coverage action bucket. Polarity read from `issue_areas[*].expected_elements_305[*].absence_adverse_to`.
Candidates exclude selected-perspective-non-adverse **missing** elements from state/materiality scoring,
then re-derive. **Governance gate:** only LPs where my `derive_lp_state(all)` reproduces the stored
`coverage_state` are *governed by the missing-count path* and can move; LPs whose state comes from another
path (unclear/dispute/unenforceable) are reported separately and **cannot move** under any candidate
(excluding a missing element doesn't remove an `unclear`/dispute driver). Absolute Risk totals are not
re-asserted here (production is unchanged); the **deltas vs C1** are the measured signal.

## Candidates (tenant perspective)
- **C1** baseline — every missing element is a gap (current).
- **C2** perspective-aware — only `absence_adverse_to ∈ {tenant, both}` missing count; **opposite (landlord)
  AND null/ambiguous → non-adverse** (aggressive).
- **C3** context-conservative — exclude **landlord only**; `null`/contextual stay reviewable (don't
  auto-favorable the ambiguous).
- **C4** favorable-position — same exclusion as C3, plus opposite-polarity-only LPs may carry a
  favorable/Improvement annotation but never Risk-by-absence-alone.

---

## Per-run results (Δ vs C1)

### 030920 — governed LPs: 25 | non-governed (state via other path): LP-14, LP-22, LP-28, LP-32 (all review_needed)
| cand | ΔRisk | ΔPriority | genuine adverse lost | movements (governed) |
|---|---|---|---|---|
| C2 | **0** | **0** | **NONE** | LP-08 partial→covered (Impr→Addr, **landlord/FAVORABLE**); LP-01 partial→covered (Impr→Addr, **null/AMBIGUOUS**) |
| C3 | **0** | **0** | **NONE** | LP-08 partial→covered (Impr→Addr, landlord/FAVORABLE) |
| C4 | **0** | **0** | **NONE** | LP-08 partial→covered (Impr→Addr, landlord/FAVORABLE) |

### 181402 — governed LPs: 28 | non-governed: LP-14 (review_needed)
| cand | ΔRisk | ΔPriority | genuine adverse lost | movements (governed) |
|---|---|---|---|---|
| C2 | **0** | **0** | **NONE** | LP-08 partial→covered (Impr→Addr, **landlord/FAVORABLE**); LP-01 partial→covered (Impr→Addr, **null/AMBIGUOUS**) |
| C3 | **0** | **0** | **NONE** | LP-08 partial→covered (Impr→Addr, landlord/FAVORABLE) |
| C4 | **0** | **0** | **NONE** | LP-08 partial→covered (Impr→Addr, landlord/FAVORABLE) |

### Reading the table
- **No candidate changes Risk or Priority-Risks count, and none loses a genuine tenant-adverse finding**
  (lost = NONE everywhere) — the exit-criterion gate passes for all four at n=2.
- **C3 ≡ C4** on the live data (no LP became Risk solely from an opposite-polarity absence, so C4's extra
  guard never fires). The only C3/C4 movement is **LP-08**: its sole missing element is landlord-polarity
  (insurance certificate-delivery), so excluding it makes LP-08 **covered/Addressed** — a clean, correct
  favorable flip (it was Improvement, never Risk).
- **C2 differs from C3/C4 by exactly one LP: LP-01**, flipped on a **null/ambiguous** element
  (`accepted_payment_methods`, no polarity). This is the "riskier auto-flip" the brief warns about — C2
  silently calls an ambiguous absence favorable; C3/C4 keep it reviewable. The live data exercises this
  distinction, so it is not academic.
- **LP-27 never moves** under any candidate → stays `partial` / Risk via the missing self-help/offset
  (tenant-adverse, kept) + the `LP-27` materiality floor. Confirms 374W/374X.

---

## Scoping the 73 — live vs latent (per run)
Of the 73 schema elements with `absence_adverse_to != tenant`, the ones **actually missing** (live
contributors to a possibly-wrong coverage_state today):
- **030920:** 20 element-instances across LP-03/04/05/08/09/10/11/17/22/27/32 — **13 landlord** (LP-08
  certificate, LP-09×4, LP-10 lien_discharge, LP-11 rent_acceleration_remedy, LP-22×4, LP-27 lender,
  LP-32 survival) + **7 both** (LP-03 dates×3, LP-04 deposit, LP-05 permitted-use, LP-17 governing-law,
  LP-32 notification).
- **181402:** ~21 instances (same set + LP-02 effective-date `both`).
- The remaining ~53 non-tenant elements are **latent** (present or not assessed in these leases) — they are
  where coverage_state *would* misfire on other contracts but don't here.
- `both`-polarity live absences (LP-03/04/05/17, LP-32 notification) **correctly stay adverse** — absence
  adverse to both parties includes the tenant. They are NOT flip candidates; only **pure-landlord** live
  absences are, and of those only LP-08 is non-over-determined enough to flip state (the rest retain a
  tenant/both missing element or are non-governed → no movement).

## Null/ambiguous live missing (the C2-vs-C3 fault line)
- `LP-01.accepted_payment_methods` (adv=`null`) and `LP-17.claims_time_limit` (adv=`null`) — both runs.
- C2 treats these as non-adverse (LP-01 flips to covered); **C3/C4 keep them reviewable** (no flip). The
  schema otherwise has NO null `absence_adverse_to` outside these — every other element has a definite
  polarity, so the conservative/aggressive split is narrow but real.

## `_HIGH_MATERIALITY_ELEMENTS` / `_MEDIUM_MATERIALITY_ELEMENTS` opposite-polarity landmine
These hardcoded sets (lease_exposure.py:41-69) bump materiality by **label string**, polarity-blind. Mapping
each to the 305 schema:
- **The dangerous HIGH entries do NOT match any 305 element label → they cannot fire on 305 LPs:**
  `"rent acceleration on default"` and `"recapture right (landlord can terminate and lease directly)"` →
  **NO 305-LABEL MATCH**. So `LP-11.rent_acceleration_remedy` (landlord, high, **live-missing**) is **not**
  caught by the materiality bump — the landmine is **latent, defused only by a label mismatch**, not by
  design. ⚠️ If anyone later aligns these strings to the 305 labels, it becomes a live
  landlord-favorable → high-materiality → **Risk** false-positive. Flag for the fix.
- **Opposite/non-tenant-polarity entries that DO match 305 labels (all MEDIUM → at most Improvement, never
  Risk):** `"lien discharge or bond requirement"` → `LP-10.lien_discharge` (**landlord**);
  `"unamortized tenant improvement cost recovery"` → `LP-12.unamortized_ti_recovery` (**landlord**);
  `"waiver of subrogation"` → `LP-08.waiver_of_subrogation` (**both** — legitimately material to tenant).
  Net: the live materiality landmine today is Improvement-level on two landlord-polarity elements
  (lien_discharge, unamortized_ti) — it cannot, on its own, manufacture a Risk on these runs.

---

## Recommendation (INPUT to a decision — NOT the decision)
**C3 (context-conservative)** best fits "flip only clearly-favorable absences, keep ambiguous reviewable":
- It removes the genuinely-wrong tenant gaps (opposite-polarity landlord absences like LP-08) — converting
  them to covered/favorable — while **not** auto-favorabling `null`/contextual elements (LP-01/LP-17), which
  is where C2 over-reaches with no semantic basis.
- At n=2 it changes **no Risk/Priority count and loses no genuine adverse finding** (exit-criterion-clean),
  and **C4 is indistinguishable from C3** on this data (adopt C3; revisit C4's favorable-annotation only if
  a future contract produces a Risk-by-opposite-absence-alone case).
- The materiality-set landmine must be fixed **alongside** any state-wiring: at minimum prevent
  opposite-polarity elements from raising materiality, and decide intentionally about the
  `rent acceleration`/`recapture` strings (currently inert by label-mismatch, dangerous if "corrected").

### Caveats for the decision (do NOT enforce yet)
- **n=2 is directional.** Only LP-08 actually flips state on these two leases; LP-01 only under C2. NEEDS
  MORE CONTRACTS before enforcement — a later measured step (374Z) must clear 374P-style exit criteria
  (no genuine adverse finding lost; movements legally coherent; provisional; validated across more leases).
- Movements are concentrated in the **Improvement/Addressed** tiers (favorable absences were never Risk
  here), so the lawyer-facing Risk surface is unaffected at n=2 — the win is correctness of the
  covered/favorable classification and the (already-contained, 374X) exposure prose.
- Non-governed `review_needed` LPs (LP-14/22/28/32) are out of scope of the missing-count path; polarity
  wiring into `derive_lp_state` won't move them, but their dispute/unclear drivers should be separately
  audited for polarity in 374Z.

## Validation
- `_374yq_recompute.py` runs clean; governance gate isolates the missing-count-governed LPs; movements,
  ΔRisk/ΔPriority, lost-adverse, favorable-vs-ambiguous, live-vs-latent, and the materiality-set polarity
  map are all emitted and reproduced above.
- No production file modified (read-only).

## Decisions Needed
1. Adopt **C3** as the 374Z target policy (flip clearly-favorable/opposite-polarity absences; keep
   `null`/contextual reviewable)? — pending more contracts.
2. Decide the `_HIGH/_MEDIUM_MATERIALITY_ELEMENTS` polarity fix (and the inert-but-dangerous
   rent-acceleration/recapture strings) as part of the same measured step.
