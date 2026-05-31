# Step 370a — Directional Synthesis Completeness Guard

**Date:** 2026-05-29
**Author:** Claude Code
**Type:** Safety circuit breaker (containment), NOT a fix for the Pass-1 collapse.
**Base SHA:** `5529c1a` (after Step 370). Server SHA for runs: still `5f6fc35` code path + this change.

---

## BLUF

Implemented the Directional Synthesis Completeness Guard. When Stage 7 sees a **large
upstream flagged-LP set** paired with a **near-empty Pass-1 directional candidate set**,
it marks `directional_synthesis_status = "incomplete_low_candidate_anomaly"` and persists
a `directional_guard` block into `synthesis_meta`. The UI then refuses to let the thin/empty
directional section read as a clean "no one-sided terms" all-clear: it shows a **Needs
Review** banner at the top of the directional area and still renders whatever directional
findings were returned.

It does **not** fix the collapse (root cause → 370c), does **not** auto-heal/rerun, and
does **not** claim directional findings are mandatory. Thresholds (20 / 5) are
**provisional** — an emergency floor eyeballed from one lease's run set in Step 370,
pending 370c calibration.

All validation paths pass (simulated fire, no-fire on stored normal-run counts, boundaries,
`candidate_density` recorded, real `run_synthesis` skip-path wiring). app.js parses clean;
`app.js?v=445`.

---

## What changed

### `cam/adapters/lease_review/lease_synthesis.py` (adapter layer — NOT `cam/core/`)

1. **New pure helper** `_evaluate_directional_completeness_guard(flagged_lp_count,
   pass1_dir_candidate_count) -> (status, guard)`. No I/O, no side effects — so the
   simulated-fire test exercises the *real* decision code, not a copy. Module-level
   provisional thresholds:
   - `DIRECTIONAL_GUARD_HIGH_FLAGGED_LP_THRESHOLD = 20`
   - `DIRECTIONAL_GUARD_LOW_CANDIDATE_THRESHOLD = 5` (uses `<=`)
   Trigger condition: `flagged_lp_count >= 20 AND pass1_dir_candidate_count <= 5`.
   `candidate_density = pass1_dir_candidate_count / flagged_lp_count` is **recorded, never
   a trigger** (it informs 370c calibration).

2. **Wired into `run_synthesis` main return path** (after Pass-1 candidates + flagged_lps
   are known, before the return). On trigger it prints
   `[lease_synthesis] DIRECTIONAL COMPLETENESS GUARD TRIGGERED: ...` and the meta now
   carries `directional_synthesis_status` and `directional_guard`.

3. **Best-effort artifact pointers** added to `directional_guard` (wrapped in try/except,
   never breaks the pipeline). Honest about what isn't available yet:
   - `parse_status`: **populated** per Pass-1 role from `evaluator_outputs`
     (`completed` / `fallback_used` / `error`).
   - `execution_path`: `"unknown"` (no reliable web-vs-headless marker in cfg today; not
     invented).
   - `raw_response_paths`: `[]` and `request_hashes`: `[]` (Pass-1 raw responses / prompt
     hashes are not persisted to disk yet — left empty until 370c adds them).

4. **Skip path** (no flagged LPs) also emits `directional_synthesis_status="complete"` +
   a `directional_guard`, so the field is always present for the UI.

### `static/app.js` (`renderSynthesisPanel`)

Reads `pr._stage_data.synthesis_meta` (fallback `pr.synthesis_meta`). When
`directional_synthesis_status === "incomplete_low_candidate_anomaly"`:
- renders the directional group **even if `mismatches.length === 0`** (so the empty set
  can't pass as an all-clear),
- prepends a Needs Review banner (`.cpf-dir-incomplete`, `role="alert"`):
  > ⚠ Needs Review — Directional synthesis produced an unusually low candidate set
  > relative to the analyzed issue volume. One-sided-term review may be incomplete.
- still renders any directional findings that *were* returned (nothing hidden).
When status is `complete`/absent, behavior is unchanged.

### `static/style.css`

`.cpf-dir-incomplete` / `-tag` / `-msg`. **Grayscale-legible**: meaning carried by the ⚠
glyph + bold uppercase tag + body text, not hue — survives monochrome / colorblind viewing
(left border + neutral grays only).

### `static/index.html`

`app.js?v=444` → **`app.js?v=445`**.

---

## Doctrine note (must not be overclaimed)

The logged `reason_code` is `low_pass1_candidate_count_with_high_flagged_lp_volume`. This is
**not** "a lease with >20 flagged LPs must have >5 one-sided terms." It is: *for a run with
a large upstream issue set, a near-empty Pass-1 directional candidate set is anomalous
enough that CAM will not present a clean directional conclusion without review.* Same CAM
doctrine as elsewhere — surface and flag the anomaly rather than wash it away. The point is
the doctrine, not the number.

---

## No auto-heal (confirmed)

Pass-1 is **not** rerun and the collapsed result is **not** silently replaced. The collapse
remains visible and persisted (that visibility is exactly what let Step 370 find it). An
*audited* rerun retaining both results is a possible later step, not this one.

---

## Validation

### 1. Simulated FIRE — `(flagged_lp=28, pass1_dir_candidates=3)`
```
status      : incomplete_low_candidate_anomaly
triggered   : True
reason_code : low_pass1_candidate_count_with_high_flagged_lp_volume
density     : 0.10714285714285714   (recorded, not a trigger)
```
Matches the real collapsed run `222051` (28 flagged / 3 candidates) — it *would* now fire.

### 2. No-FIRE — stored normal-run counts
- `s370r1` (29 / 28) → `complete`, `triggered=False`, density ≈ 0.966
- `222051`-style normal (28 / 28) → `complete`
- `s370r2` (28 / 26) → `complete`
The stored normal runs (≈28 candidates) do not trip the guard.

### 3. Boundaries
`(20,5)` → fire · `(19,5)` → no-fire · `(20,6)` → no-fire. (`>=20` and `<=5` exactly.)

### 4. `candidate_density` recorded on every path (fire, no-fire, skip) and never a trigger.

### 5. Real `run_synthesis` wiring (no API calls) — skip path
Called `run_synthesis(coverage_assessment=[], conflicts=[])` → early return carries
`directional_synthesis_status="complete"` and the full `directional_guard` block in `meta`.
Proves the helper is wired into the actual function's `synthesis_meta`, not just unit-tested
in isolation.

### 6. UI / static
`node --check static/app.js` → **OK**. `app.js?v=445` confirmed in index.html. Banner
gating is a single equality on the persisted `directional_synthesis_status`.

### Persisted `directional_guard` shape (FIRE example; pointers added by caller)
```json
{
  "triggered": true,
  "reason_code": "low_pass1_candidate_count_with_high_flagged_lp_volume",
  "flagged_lp_count": 28,
  "pass1_directional_candidate_count": 3,
  "candidate_density": 0.10714285714285714,
  "high_flagged_lp_threshold": 20,
  "low_candidate_threshold": 5,
  "execution_path": "unknown",
  "raw_response_paths": [],
  "request_hashes": [],
  "parse_status": [ {"role": "A", "completed": true, "fallback_used": false, "error": null}, ... ]
}
```

### Not live-verified (by design, matches the instruction's own validation plan)
- **Live banner render** and **live main-path fire**: the collapse is intermittent and
  cannot be triggered on demand, and the UI banner only renders for a result whose stored
  `synthesis_meta` carries the incomplete status (no stored run has it — they predate this
  field). Per instruction validation item (3), live fire is **opportunistic during 370c**:
  when a run collapses live, confirm the guard fires, the banner renders, and
  `directional_guard` + counts persist. The decision logic, the real-function meta wiring
  (skip path), and the banner-gating branch are all verified offline.

---

## Thresholds are PROVISIONAL

`20` / `5` are an **emergency floor**, not a calibrated model — eyeballed from a small run
set on a single lease (Atlas) in Step 370. `<=5` is used because there is no reason to trust
5 over 4 when the normal candidate count is ≈28. **Recalibrate once 370c provides a
defensible baseline**; `candidate_density` is being recorded on every run to inform that.

---

## Scope / exclusions (as instructed)

- No `cam/core/` changes. `lease_synthesis.py` is adapter layer.
- **No changes** to Pass-1 candidate generation, Pass-2 matching, consolidation, action
  buckets, or confidence governance. No attempt to fix the collapse itself.
- **No `directional_eligible_lps` concept** — explicitly out of scope.
- Pre-existing uncommitted `05 Lease Analyzer/app/config.py` (Step 369 reload-trigger
  comment) left untouched — not part of this step.

## Reload caveat

`uvicorn --reload` watches only `05 Lease Analyzer/`. The guard logic lives in
`cam/adapters/lease_review/lease_synthesis.py` (outside that tree), so **the reloader will
not pick it up on its own.** Before any keyed run, fully restart uvicorn (or touch a file in
`05 Lease Analyzer/`) so the server isn't running stale synthesis code. The static edits
(app.js/index.html/style.css) are served fresh on hard-refresh given the `?v=445` bump.

## Files changed

- `cam/adapters/lease_review/lease_synthesis.py` — guard helper + wiring + meta persistence
- `static/app.js` — incomplete-state banner in directional area (`renderSynthesisPanel`)
- `static/style.css` — `.cpf-dir-incomplete*` (grayscale-legible)
- `static/index.html` — `app.js?v=445`
