# Step 375I — Part 1 Results (Static Artifact Read)

**Run:** lease_review_20260604_033046_52adbf  |  **Date run:** keyless; can be re-run at any time
**Q3 status:** NOT RUN — see `_375i_part2.py` (keyed)

---

## Q1 — POPULATED

**Eligibility rule** (`_should_assess` in `cam/adapters/lease_review/lease_use_impact.py`):
- `missing` → always eligible
- `review_needed` → always eligible
- `partial` → eligible iff ≥50% of `element_verdicts` are missing (not in `_PRESENT_VERDICTS`)
- `covered`, `not_applicable`, any other state → **never eligible**

**Counts (n=32 total):**

| Category | Count |
|---|---|
| Total LPs | 32 |
| Eligible (reach 5e) | 8 |
| Populated (`use_impact` present) | 8 |
| Eligible but empty | 0 |
| Gated out (never reach 5e) | 24 |

**Fill rate: 8/8 = 100%** of eligible LPs are populated.

Gated-out breakdown:
- [7 LPs] partial but 33% missing (threshold: ≥50%)
- [3 LPs] partial but 40% missing (threshold: ≥50%)
- [3 LPs] covered → _should_assess returns False
- [3 LPs] not_applicable → _should_assess returns False
- [2 LPs] partial but 20% missing (threshold: ≥50%)
- [2 LPs] partial but 14% missing (threshold: ≥50%)
- [1 LP] partial but 17% missing (threshold: ≥50%)
- [1 LP] partial but 25% missing (threshold: ≥50%)
- [1 LP] partial but 12% missing (threshold: ≥50%)
- [1 LP] partial but 45% missing (threshold: ≥50%)

**Proven claim:** All 8 eligible LPs have use_impact populated (100% fill on this run).

**Caveat:** Eligibility is sparse — 18 of 22 partial LPs are gated out because they fall below the 50% missing threshold. LP-22 (45% missing) and LP-04 (40% missing) are the closest misses. Sparsity is a structural property of the gate, not a reliability failure.

**Still unmeasured:** Whether the 50% threshold is correctly calibrated for the 375E anchor role.

---

## Q2 — ASSESSED vs FLOOR-DEFAULTED

**Provenance field:** `use_impact.confidence` encodes how each verdict was produced:
- `assert` / `assert_weak` / `context_dependent` → **genuine model assessment**
- `no_evaluators` → **floor default** (all evaluators failed, or no use_profile)

**Results for 8 populated LPs:**

| LP | State | materiality | confidence | agreement | classification |
|---|---|---|---|---|---|
| LP-03 | partial | high | assert | 3-0 | assessed |
| LP-05 | missing | medium | assert | 3-0 | assessed |
| LP-10 | partial | high | assert | 3-0 | assessed |
| LP-14 | review_needed | medium | assert | 3-0 | assessed |
| LP-16 | partial | high | assert | 3-0 | assessed |
| LP-20 | missing | low | assert_weak | 2-1 | assessed |
| LP-26 | review_needed | high | assert | 3-0 | assessed |
| LP-32 | partial | medium | assert | 3-0 | assessed |

**Proven claim:** All 8 populated records are genuine model assessments (confidence ∈ {assert, assert_weak}). Zero floor defaults in this run.

**The `or "moderate"` floor (lease_adapter.py:1006 + :1461):**
The floor is NOT in `lease_use_impact.py`. It lives downstream in the routing layer:
```python
_consequence = _ui.get("materiality") or "moderate"
```
This applies to all 24 LPs that never reached 5e (no `use_impact` key). Those LPs receive `consequence = "moderate"` (normalised to "medium" by `lease_verdict_distance.py`) in the verdict-distance routing calculation.

**Provenance gap:** No field in the artifact records that a consequence was floor-defaulted. The only signal is absence of the `use_impact` key. A reader cannot distinguish "never reached 5e" from "evaluated but low".

**Missing field:** `use_impact.materiality_source` (or `routing_consequence_source` on the coverage_assessment dict) — records assessed vs floor-defaulted consequence.

**Caveat:** The no_evaluators path exists in the code (all-fail or no-use_profile), but was not exercised in this run. Q3 stability replay will reveal whether re-runs ever trigger it via timeouts.

**Still unmeasured:** Whether floor defaults occur under real-world conditions (API timeouts, absent use_profile). This is a code-path gap, not a data gap.

---

## Q4 — AVAILABLE for recovered findings

**Gating map:**

| Coverage state | 5e gate |
|---|---|
| `missing` | **IN** — always eligible |
| `review_needed` | **IN** — always eligible |
| `partial` (≥50% missing) | **IN** — threshold met |
| `partial` (<50% missing) | **OUT** — threshold not met |
| `covered` | **OUT** — `_should_assess` returns False (hardcoded) |
| `not_applicable` | **OUT** — falls to default return False |

**Structural finding:**
`covered` is a hard structural gate. `_should_assess` returns `False` unconditionally for `covered` LPs. The 3 covered LPs in this run (LP-08, LP-09, LP-13) can **never** receive a 5e materiality assessment under the current code, regardless of how many times the pipeline runs.

The present-hostile-term recovery class from 375H targets LPs with `coverage_state="covered"` that contain landlord-adverse language. Under the current gating logic, those recovered findings would arrive at the routing layer **without a materiality value**. The `or "moderate"` floor in `lease_adapter.py` would then assign them `consequence = "moderate"`, not a use-context-assessed value.

**Widening needed for 375E-COV:**
Either (a) introduce a new state (e.g. `covered_adverse`) that `_should_assess` recognises,
or (b) widen `_should_assess` to pass `covered` LPs that carry a directional-adverse signal.
Without this widening, recovered findings have no materiality anchor for the 375E routing formula —
they will silently receive the "moderate" floor.

**Proven claim:** Hard structural gate confirmed from source read. This is not a data sparsity issue — it is a code path that does not exist.

**Caveat:** Q4 is a structural read only. It does not measure whether any of the 3 covered LPs are actually adverse — that is 375H's job.

**Still unmeasured:** How many additional LPs would qualify for 5e if the 50% threshold were lowered, or if `covered_adverse` were added as a new state.

---

## Q3 — STABLE (NOT RUN — keyed)

See `build_log/_375i_part2.py`. Run with keys from:
`C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env`
```powershell
cd "C:\Users\Owner\OneDrive\CAM"
python "build_log\_375i_part2.py"
python "build_log\_375i_part2.py" 10   # N=10 (matching 375D-2's K)
```
