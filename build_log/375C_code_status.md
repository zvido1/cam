# Step 375C — Status: Pass-2 integrity tripwire (PROVISIONAL correctness repair)
**Date:** 2026-06-03  **Version:** app.js v464 → **v465**. **Scope:** the HISTORICAL unusable-output failure
mode ONLY (375-R). **NOT** the current GPT-5.4 semantic-flip question (those are clean valid verdicts, gated
on the keyed replay / two-output redesign). No change to the line-1936 vote-count map, clean valid splits, or
compound findings.

## Governing rule implemented
A missing / malformed / truncated / unmatched / empty Pass-2 role output is **NOT a negative vote.** It must
not silently function as non-confirmation (375-R: Role A's empty directional output silently demoted findings
out of Risk as if an evaluator disagreed, suppressing directional Risk to 0).

## The change — `cam/adapters/lease_review/lease_synthesis.py` (`_build_pass2_directional_findings`)
Per directional finding, a role whose Pass-2 output was unusable for that candidate is detected via the
EXISTING `_NO_OBJECT` sentinel (which already fires on empty/unmatched/truncated/format-drift output — Role
A's empty output makes A `_NO_OBJECT` for every candidate). When any role is `_NO_OBJECT`:
1. **`verification_incomplete = True`** — a DISTINCT state, not a vote and not a severity.
2. **`severity = "VERIFICATION_INCOMPLETE"`** — overrides the HIGH/MED/LOW result *after* the line-1936 map
   runs (the map itself is unchanged). The finding is no longer silently shown as a deflated severity.
3. **No fake tally:** the unusable role's `evaluator_verdicts[role] = "not_assessed"` (distinct from a
   genuine `"unclear"`), and `evaluator_agreement` reports the **usable** roles only
   (`{usable_confirmed}-{usable_other}`) — so a 2-of-3-usable result reads "2 confirmed, 0 disagreed + 1
   incomplete", **never "2-1 disagreement."** A finding that would be 3-0 with all roles usable is surfaced
   as verification_incomplete, not demoted to "2-1 MEDIUM / not-Risk."
4. **Raw cause preserved for Audit/Evidence:** `verification_incomplete_roles` + `verification_incomplete_cause`
   (per-role `{completed, model, n_objects, dir_object_count, empty_directional_output}`).
- Clean findings additionally carry `verification_incomplete: False` (additive; no behavior change).
- The `confirmed == 0` governed-rejection path is unchanged (out of scope).

## UI — `05 Lease Analyzer/static/app.js` (`_buildCpfDetail`, v465)
A finding with `verification_incomplete` (or `severity === 'VERIFICATION_INCOMPLETE'`) renders a distinct
**"⚠ Verification incomplete"** badge (with the incomplete-role + raw-cause tooltip) instead of a raw
severity label. Directional routing is by `evaluator_agreement` (vote tally), so an incomplete finding
surfaces in Needs Review with the explicit incomplete state — **not** silently as a resolved non-Risk. No
current finding carries the flag, so **no current display changes**.

## Validation (`cam/adapters/lease_review/tests/test_pass2_tripwire_375c.py` — 6/6 PASS)
Drives the REAL modified builder with each run's stored `pass2_raw` as `pass2_outputs` (no provider keys, no
pipeline re-run):
- **CURRENT-code pair (030920, 0604) — integrity clean: 0 findings change state** (28 and 26 directional, all
  `verification_incomplete=False`). **Tripwire does NOT fire on clean integrity** → proves it is scoped to the
  failure mode, not the semantic flips. ✓
- **HISTORICAL A-empty runs (s370r1, 370c_H1): all 28 directional findings → `verification_incomplete`**, with
  `evaluator_verdicts[A]="not_assessed"`, `severity="VERIFICATION_INCOMPLETE"`, `verification_incomplete_cause[A]
  .empty_directional_output=True`, and an honest usable tally (`2-0` / `1-1`) — **never silently MEDIUM/2-1 and
  never silently dropped to 0-Risk.** Audit cause present. ✓
- **Control — all-usable 3-0:** stays `severity=HIGH`, `agreement=3-0`, `verification_incomplete=False` (line-1936
  map untouched). ✓
- **Control — clean valid 2-1 (all usable, B=no_mismatch):** stays `MEDIUM` / `2-1`, `verification_incomplete=False`
  — the current GPT-5.4 semantic-split case is **untouched** (scope guard). ✓
- **Compound findings:** unchanged (the tripwire lives only in the directional builder; compound is a separate
  path — the stable control). ✓
- `py_compile` clean; `node --check` clean.

## CONFIRM (scope discipline)
- The line-1936 `HIGH/MEDIUM/LOW = confirmed-vote-count` map is **NOT modified** (only overridden to the
  distinct state for unusable-output findings).
- The current GPT-5.4 semantic-flip behavior is **NOT touched** (clean 3-usable splits unchanged) — that
  remains the gated two-output redesign + keyed replay (375D).
- No change to Risk COUNTING beyond: an incomplete-verification finding is no longer silently a resolved
  non-Risk; it has the distinct `verification_incomplete` display state. No materiality claim is invented.

## Provisional marker
PROVISIONAL — narrow integrity tripwire pending the keyed Stage-7 replay (375D) and the directional
two-output (materiality vs verification) architecture decision. External demo / Joshua use of Risk / Priority
/ Stage-7 directional totals remains **PAUSED** (this repair removes a silent-suppression failure mode; it
does not validate the directional Risk headline, which still depends on the unresolved semantic-flip work).

## Decisions Needed
None for this step. (Next: 375D keyed replay — GPT-5.4 Pass-2 reproducibility + the two-output decision.)
