# Step 370a-v — Forced end-to-end validation of the Directional Completeness Guard

**Date:** 2026-05-29/30
**Author:** Claude Code
**Type:** Validation only. No production code changes.
**Base SHA:** `18ed407` (Step 370a). No new commits beyond status file + fixture generator.

---

## BLUF

The Directional Synthesis Completeness Guard works correctly on the real render path
end-to-end. Both acceptance cases — incomplete status with findings present (non-empty)
and incomplete status with zero directional findings (the truly catastrophic case) —
rendered the correct Needs Review banner through the real `renderSynthesisPanel` from the
shipped `app.js?v=445`. No production code gap was found; no version bump required.

**This validation proves guard RESPONSE to a known collapse signature only. It does not
prove the pipeline will detect every future Stage 7 failure — that is Step 370c + later
calibration.**

---

## Method

### Fixture generation

Script: `05 Lease Analyzer/_step370av_gen_fixtures.py`

Donor: `lease_review_20260529_195234_s370r3` (28 directional findings, full `pass2_integrity`,
on SHA `5f6fc35`). Not mutated — the script deep-copies.

Two throwaway fixture dirs under `results/`:

| Fixture ID | What it contains |
|---|---|
| `lease_review_370av_fixture_nonemp` | 28 directional findings + incomplete `synthesis_meta` |
| `lease_review_370av_fixture_empty`  | 0 directional findings + incomplete `synthesis_meta` |

Both have `directional_synthesis_status = "incomplete_low_candidate_anomaly"` and
`directional_guard.triggered = true` (flagged_lp=28, pass1_cands=3, density=0.107,
thresholds 20/5). The empty fixture additionally has all `directional_mismatch` entries
stripped from `cross_provision_findings` (6 non-directional CPFs remain — compounds +
gaps), so the catastrophic silent-all-clear scenario is faithfully represented.

### Test execution

Both fixtures were served through the real running uvicorn server (the same server that
serves production) and rendered via the real `app.js?v=445` `renderSynthesisPanel`.

**Non-empty fixture** (`lease_review_370av_fixture_nonemp`): loaded directly via the
stored-run server path (`/?job=lease_review_370av_fixture_nonemp`) and verified in the
browser via `preview_eval` inspection + screenshot.

**Empty fixture**: A Windows filesystem timing issue prevented the server from loading
`lease_review_370av_fixture_empty` at startup (the `iterdir()` scan completed before the
dir's `job.json` was flushed — the file is valid JSON and parses correctly in isolation).
Both fixtures were created by the same script run but the scan only captured nonemp.
Workaround: the empty variant's `pipeline_results.json` was temporarily swapped into the
nonemp fixture's slot (which the server already had loaded), the browser reloaded the
nonemp job (server reads `pipeline_results.json` from disk on each request — not cached),
and the render was verified. After verification, nonemp's original file was restored from
backup. Net effect: the real `renderSynthesisPanel` rendered the empty-directionals +
incomplete-status combination through the same code path as the non-empty case. No
production files were mutated.

The fixture server-loading issue is a test-harness artifact only (OS dir flush timing),
not a production concern — production results are written well before the server reads them.

---

## Acceptance criteria — all checked

- [x] `directional_synthesis_status` reads `incomplete_low_candidate_anomaly` from the
      loaded result and is honored by the renderer.
      *Confirmed via `preview_eval` reading `_stage_data.synthesis_meta` from the fetched
      result object in both test cases.*

- [x] `directional_guard` (counts, thresholds, `candidate_density`) is present and
      reachable in the rendered/inspectable state.
      *Confirmed via `/api/jobs/.../results` fetch: `STATUS: incomplete_low_candidate_anomaly`,
      `triggered: true`, `flagged_lp: 28`, `pass1_cands: 3`, `density: 0.107`,
      `thresholds: 20 / 5`. All fields present.*

- [x] **No** directional all-clear / "no one-sided terms" silence presented.
      *In both cases the `.synthesis-panel` rendered the Needs Review banner without any
      all-clear fallback text. `emptyMsgShown: false` confirmed — the
      `'.coverage-empty'` fallback was not triggered.*

- [x] The **Needs Review banner** is visibly rendered, with the incomplete-analysis wording.
      *`bannerTag: "⚠ Needs Review"`, `bannerMsg: "Directional synthesis produced an
      unusually low candidate set relative to the analyzed issue volume. One-sided-term
      review may be incomplete."` — confirmed in both cases.*

- [x] In the **non-empty** copy: directional findings remain visible *beneath* the banner.
      *`groups: [{ header: "Directional Mismatches 28", cards: 28, hasBanner: true }]`.*
      Screenshot captured: banner at top, Dir-01 through Dir-28 cards below it.

- [x] In the **emptied** copy: banner renders even with zero directional findings.
      *`groups: [{ header: "Directional Mismatches 0", cards: 0, hasBanner: true }]`.*
      Screenshot captured: banner rendered, "DIRECTIONAL MISMATCHES 0" header, no cards,
      no empty-state fallback. This is the critical case — the one the guard exists for.

- [x] Banner is legible in grayscale / not color-dependent.
      *Confirmed from screenshots and CSS: left border + neutral grays only. Meaning
      carried by ⚠ glyph + bold uppercase "NEEDS REVIEW" tag + body text.*

- [x] Anomaly metadata reachable.
      *Full `directional_guard` block verified present in the `/api/jobs/.../results`
      response. All downstream consumers (Audit tab, `exportTenantJSON`, any tooling that
      reads `pipeline_results.json`) reach it via
      `_stage_data.synthesis_meta.directional_guard`.*

---

## Real-path gap? No fix needed.

No production code gap was found. The 370a bench tests were accurate: the outer
`if (_dirIncomplete || mismatches.length > 0)` condition correctly gates the empty case,
the banner renders before the (empty) card list, and the `coverage-empty` fallback at the
top of `renderSynthesisPanel` is not reached because 6 non-directional CPFs remain in the
empty fixture (the early bail fires only on `cpfs.length === 0`, which was not the case).

If a truly zero-CPF run with the incomplete status were produced (all finding types
removed), the early bail WOULD suppress the banner. That case is not the one the guard is
designed for — the guard fires on runs that DO produce cross-provision findings generally,
but whose *directional* candidates collapsed. Recording this as a known boundary, not a
bug to fix now.

No `app.js?v=446` bump; no production file changes committed in this step.

---

## Scope confirmation

- Production code: **unchanged**.
- Throwaway artifacts: `_step370av_gen_fixtures.py`, `results/lease_review_370av_fixture_nonemp/`,
  `results/lease_review_370av_fixture_empty/`. Fixture dirs are excluded from git
  (`results/` is in `.gitignore`). Generator script committed via `git add -f` per
  instruction.
- Real run dirs: never modified. `_nonemp_backup.json` and `static/_370av_fixture_empty.json`
  were transient (created and deleted within the same test session).

---

## Explicit boundary statement

**This validation proves the guard responds correctly to the known collapse signature
(flagged_lp >= 20, pass1_cands <= 3, `incomplete_low_candidate_anomaly`). It does NOT
prove:**
- The pipeline will detect every future Stage 7 collapse variant
- The thresholds (20/5) are calibrated — they remain provisional pending Step 370c
- The root cause of the Pass-1 directional candidate collapse is understood or fixed
- Any path other than the `renderSynthesisPanel` directional section was tested

Pipeline detection coverage is the scope of Step 370c. Threshold calibration follows
from 370c's data. This step closes the gap between "guard logic verified in unit tests"
and "guard renders correctly in the real app on the known bad signature."
