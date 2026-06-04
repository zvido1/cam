# Step 375I — Code Status: Stage 5e Completeness & Stability Audit

**Date:** 2026-06-04  **Mode:** Part 1 WRITTEN + SELF-RUN (keyless). Part 2 WRITTEN, NOT RUN (keyed).
**External-use pause:** still in force; this step is measurement-only.

---

## What was built

| File | What it does | Key |
|---|---|---|
| `build_log/_375i_part1.py` | Keyless static audit: Q1/Q2/Q4 from frozen artifact | none |
| `build_log/_375i_part2.py` | Keyed stability replay: Q3 (N=10 runs of 5e) | required |
| `build_log/375I_results.json` | Q1/Q2/Q4 answers (machine-readable) | — |
| `build_log/375I_results.md` | Q1/Q2/Q4 answers (human-readable) | — |
| `build_log/375I_q3_results.json` | Q3 stability output (written by Part 2 after Tzvi runs) | — |

**READ-ONLY honored:** No edits to `lease_use_impact.py`, `lease_adapter.py`, or any file under `cam/core/`.
No routing change. No schema change.

---

## Q3 harness execution path

**DIRECT ADAPTER** — `_375i_part2.py` calls `assess_use_impact()` from
`cam.adapters.lease_review.lease_use_impact` directly. No Flask server start needed.
PYTHONPATH is set to the CAM root automatically inside the script.

To run (keyed machine):
```powershell
cd "C:\Users\Owner\OneDrive\CAM"
git pull
python "build_log\_375i_part2.py"        # N=10 (default — matches 375D-2 K=10)
python "build_log\_375i_part2.py" 5      # lighter N=5 if cost is a concern
```
Keys load from `C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env`. `DISABLE_OPENROUTER=1` is
set automatically.

---

## 375D-2's N

375D-2 Track A used **K = 10** repeats per condition (the per-condition repeat count; stated in the 375D-2
instruction as "≥10 repeats each" and confirmed in the 375D-2 code status as "K=10"). 375D-2 Track B used
N=5 as its default replay count.

**375I Part 2 uses N=10** (matching Track A's K, the higher of the two) as the default.
The script accepts an optional argument to lower it: `python _375i_part2.py 5`.

---

## Part 1 results summary (self-checked, no keys)

### Q1 — POPULATED
- **8/8 eligible LPs are populated (100% fill rate)** on the frozen run.
- Eligibility rule: `missing` → always; `review_needed` → always; `partial` → only if ≥50% of
  `element_verdicts` are missing (not in `_PRESENT_VERDICTS`); `covered` / `not_applicable` → never.
- Breakdown of the 24 gated-out LPs:
  - 18 partials gated out by the <50% threshold (the closest misses: LP-22 at 45%, LP-04 at 40%)
  - 3 covered (LP-08, LP-09, LP-13)
  - 3 not_applicable (LP-12, LP-23, LP-31)
- **Proven claim:** 100% fill on eligible LPs. **Caveat:** eligibility is structurally sparse — only 8 of 32
  LPs ever reach 5e under the current gate. 18 partials are below threshold.

### Q2 — ASSESSED vs FLOOR-DEFAULTED
- **All 8 populated records are genuine model assessments** (`confidence` ∈ {`assert`, `assert_weak`}).
- Zero `no_evaluators` floor defaults in this run.
- **Provenance IS recorded** via the `confidence` + `evaluator_agreement` fields in each `use_impact` dict.

**The `or "moderate"` floor lives downstream in routing, not in 5e:**
`cam/adapters/lease_review/lease_adapter.py:1006` and `:1461`:
```python
_consequence = _ui.get("materiality") or "moderate"
```
This floor applies to the **24 gated-out LPs** that have no `use_impact`. They receive
`consequence = "moderate"` (normalised to "medium" by `lease_verdict_distance.py`) in the
verdict-distance routing calculation. This floor is **NOT recorded in the artifact** — the
absence of the `use_impact` key is the only signal.

**Provenance gap / missing field:** `use_impact.materiality_source` (or `routing_consequence_source` on the
coverage_assessment dict) — no field currently distinguishes "never reached 5e" from
"evaluated and returned low". A reader of the artifact cannot tell which 24 LPs received the floor.

### Q4 — AVAILABLE for recovered findings
- `covered` is a **hard structural gate** in `_should_assess`. LP-08, LP-09, LP-13 (covered in this run)
  can never receive 5e materiality under current code.
- **Structural gap:** present-hostile-term findings from 375H repair that land on currently-`covered` LPs
  will arrive at routing **without materiality**, receiving the `"moderate"` floor instead of a
  use-context-assessed value.
- **375E-COV widening needed:** either add `covered_adverse` as a new state that `_should_assess`
  recognises, or widen it to pass `covered` LPs carrying a directional-adverse signal.

### Q3 — NOT RUN (Tzvi runs keyed)
See `_375i_part2.py`. The routing-relevant metric — whether any LP crosses a materiality bucket that
changes its Risk routing under the 375E design — is the central question. **Either answer is valid:**
- 0 crossings → materiality can anchor the 375E redesign.
- Any crossing → redesign must not rely on 5e materiality as-is.

---

## Decisions needed
1. Tzvi runs `_375i_part2.py` (keyed) and commits `375I_q3_results.json`.
2. Chat reads the Q3 results and issues the 375I materiality fitness verdict:
   - **Fit** → unblocks 375E-DIR routing counterfactual with materiality as anchor.
   - **Wobbles like the vote** → anchor must move; 375E-DIR routing formula stays unlocked.
   - **Sparse / provenance gap** → 375E-COV (widen 5e + add `materiality_source` field) precedes build.
3. The structural gap found in Q4 (covered LPs gated out) is **independent of Q3's answer** —
   375E-COV needs the `_should_assess` widening regardless.
