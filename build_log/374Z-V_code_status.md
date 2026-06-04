# Step 374Z-V — Status: verify 374Z on the fresh post-deploy run (READ-ONLY)
**Date:** 2026-06-03  **Mode:** read-only verification. **No production change.** Run verified:
`results/lease_review_20260604_033046_52adbf/tenant_0/pipeline_results.json` (deployed SHA 609af43).
Same lease as the 030920 baseline — `atlas_meridian_warehouse_lease.txt`, identical text SHA `fbf5f362ae10`,
pipeline_version 1.0.0. Script: `build_log/_374zv_verify.py`.

## VERDICT
**The 374Z-specific behavior is verified and correct on the live deployed pipeline. The Action-Summary
COUNT prediction (Risk 20 / NeedsReview 24 / Improvement 15 / Addressed 2) does NOT match the live run
(Risk 36 / NeedsReview 4 / Improvement 17 / Addressed 3) — but the divergence is caused by full-pipeline
re-run NONDETERMINISM in stages 374Z never touched (dominated by the synthesis stage), NOT by 374Z.** The
count prediction cannot be cleanly tested on a fresh run; it is only valid as a deterministic recompute on
frozen verdicts (already done in 374Z: ΔRisk=0, ΔPriority=0). Flagged below, not rationalized.

---

## 1. LP-08 — MATCHES prediction (partial→covered, Improvement→Addressed)
- `coverage_state = covered`, `partial_class = None`, `materiality = low` → **bucket = Addressed**. ✓
- `elements_missing = []`; the sole missing element (`LP-08.certificate_delivery`, a landlord-protective
  insurance certificate, `absence_adverse_to = landlord`) is now in `favorable_or_non_adverse_absences`. ✓
- `exposure_headline = "Insurance Requirements is addressed and consistent with…"` — no gap narration. ✓

## 2. LP-27 — MATCHES prediction (stays partial→Risk; lender absence reframed)
- `coverage_state = partial`, `partial_class = partial_material`, `materiality = high` → **bucket = Risk**. ✓
- `elements_missing = ["Tenant may perform landlord's obligation and offset against rent"]` — the self-help/
  offset tenant protection (adverse) is **still in elements_missing**. ✓
- `favorable_or_non_adverse_absences = [LP-27.lender_notice_and_cure_right, adverse_to=landlord, sev=low,
  cross_LP_coverage=["LP-22"]]` — lender-cure moved to the favorable slot **with the SNDA dependency
  caveat**, and is **NOT in elements_missing**. ✓
- `exposure_headline = "No self-help rent offset"` — **"lender cure delay" is GONE**; no narration of the
  lender absence as a tenant gap. ✓ (Was "No self-help; lender cure delay" on 030920.)

## 3. Action Summary counts — DIVERGENCE (flagged; cause = re-run nondeterminism, not 374Z)
Recomputed with the 374P bucket logic (which reproduces production counts — it reproduces the 030920
baseline exactly):

| run | Risk | NeedsReview | Improvement | Addressed | PriorityRisks |
|---|---|---|---|---|---|
| 030920 baseline | 20 | 24 | 16 | 1 | 16 |
| **0604 FRESH (live)** | **36** | **4** | **17** | **3** | **31** |
| 374Z prediction | 20 | 24 | 15 | 2 | 16 |

**This does NOT match the prediction. Root cause is NOT 374Z** — evidence:
- **Synthesis stage swung hard (untouched by 374Z).** `cross_provision_findings` severity went from
  **HIGH 16 / MEDIUM 16 / LOW 1** (030920) to **HIGH 30 / MEDIUM 2** (fresh). Synthesis-Risk therefore
  jumped ~+14 and PriorityRisks +15 — this alone explains most of Risk 20→36 and PR 16→31. 374Z modified
  only `lease_coverage_305.py` / `lease_coverage.py` / `lease_exposure.py`; the synthesis stage
  (`lease_synthesis.py`) is untouched, so it cannot be a 374Z effect.
- **Coverage state drifted on 7/32 LPs**, of which only 2 are 374Z transitions; the other 5 are run variance:
  - LP-08 `partial→covered` — **374Z** (favorable absence). ✓
  - LP-09 `review_needed→covered` — **374Z-assisted** (all 4 missing are landlord-polarity; the 030920
    `review_needed` came from an `unclear` element that resolved this run). Correct per C3 (no tenant gap).
  - LP-16/LP-19/LP-22/LP-28/LP-32 `review_needed→partial` — **run variance** (these are NOT a 374Z
    transition type; their 030920 `review_needed` came from `unclear`/dispute that resolved differently).
    The collapse of these 5 review items is the main driver of NeedsReview 24→4.
- **374Z's only count effect IS present** (LP-08 Improvement→Addressed) but is swamped by the above.

**Honest conclusion:** the count prediction assumed the fresh run's verdicts equal 030920's (it was computed
by a deterministic recompute on frozen verdicts). The live pipeline is nondeterministic, so absolute counts
between two runs of the same lease are not comparable. The count prediction is **unverifiable on a fresh run**
and should be considered verified only via the frozen-verdict recompute (374Z exit criteria: ΔRisk=0,
ΔPriority=0). I am NOT claiming the live counts confirm 374Z — they neither confirm nor refute it.

### Separate flag (NOT 374Z): synthesis-severity instability
The synthesis severity distribution swinging HIGH 16→30 on a re-run of the **same lease** is a large
run-to-run instability worth its own investigation (it dominates the Risk/Priority headline and is
independent of 374Z). Recommending a separate look; out of scope here.

## 4. Favorable-slot inventory (first live look — surfacing-decision input)
**11 elements across 6 LPs, ALL `absence_adverse_to = landlord` (zero tenant-polarity — correct):**

| LP | element | sev | cross_LP_coverage (dependency caveat) |
|---|---|---|---|
| LP-08 | certificate_delivery | low | — |
| LP-09 | change_of_control_addressed | medium | — |
| LP-09 | tenant_remains_liable_after_transfer | high | **[LP-11]** |
| LP-09 | transfer_profit_sharing | low | — |
| LP-09 | required_transfer_documentation | low | — |
| LP-10 | lien_discharge | medium | — |
| LP-11 | **rent_acceleration_remedy** | high | — |
| LP-22 | subordination_mechanism_self_executing | low | — |
| LP-22 | tenant_executes_subordination_documents_on_request | medium | — |
| LP-22 | snda_execution_timing_and_default_consequence | low | **[LP-11]** |
| LP-27 | lender_notice_and_cure_right | low | **[LP-22]** |

- The **rent_acceleration landmine element (LP-11)** correctly sits in the favorable slot (a landlord remedy
  whose absence helps the tenant) — it is NOT a tenant gap and did NOT drive Risk. ✓
- Cross-LP caveats are retained where present (LP-09→LP-11, LP-22→LP-11, LP-27→LP-22) for the later
  favorable-position surfacing decision.

## 5. Risk-drop sanity — PASS (no genuine adverse finding lost)
- 030920 coverage-Risk LPs: {LP-03, LP-27}. Fresh coverage-Risk LPs: {LP-03, LP-10, LP-16, LP-27}.
- **DROPPED out of Risk: NONE.** No LP that was Risk on 030920 left Risk on the fresh run. ✓
- ADDED to Risk (fresh): LP-10, LP-16 — both **run variance, not 374Z**: LP-10 stayed `partial` (its Risk is
  driven by new adverse missing elements — "ownership of improvements", "removal obligation" — different
  verdicts this run; its favorable `lien_discharge` correctly did NOT drive Risk); LP-16 went
  `review_needed→partial` (variance) on new adverse parking elements. Neither involves a favorable absence
  being mis-scored.
- Every favorable-slot element across all LPs is landlord-polarity — **no tenant-adverse element was
  mis-routed into a favorable slot** (verified against the schema).

---

## Does the LIVE run match the 374Y-Q C3 prediction?
- **374Z mechanism (the actual subject of this verification): YES, fully.** LP-08 covered/Addressed; LP-27
  stays Risk with lender reframed to favorable + "lender cure delay" gone; favorable slot populated correctly
  (all landlord-polarity, caveats retained); no genuine adverse finding lost.
- **Absolute Action-Summary counts: NO** — but the divergence is attributable to full-pipeline re-run
  nondeterminism (dominantly the untouched synthesis stage; secondarily 5 `review_needed→partial` coverage
  flips from verdict variance), NOT to 374Z. The count prediction is only meaningful as a frozen-verdict
  recompute, which passed in 374Z.

## Recommendation (input, not decision)
1. Treat the 374Z deployment as **verified at the mechanism level** (per-LP behavior on the live pipeline).
2. Do NOT treat the live count mismatch as a 374Z regression; the clean count check is the deterministic
   recompute (done). If absolute-count regression-testing on fresh runs is desired, it requires
   verdict-frozen replay or many-run averaging — a fresh single run can't isolate it.
3. **Separately investigate** the synthesis-severity instability (HIGH 16→30 on a same-lease re-run) — it
   dominates the Risk headline and is independent of polarity / 374Z.

## Decisions Needed
- None for 374Z itself (mechanism verified). Open: (a) whether to investigate synthesis-severity
  instability as its own item; (b) the deferred favorable-position surfacing decision, now with 11 live
  favorable-slot entries as input.
