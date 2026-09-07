# Step 580-2 — the attribution fix — COMPLETE

**Date:** 2026-09-06
**Instruction:** `build_log/580_chat_instruction.md` (580-2 section, written before execution, Rule 7)
**Brief:** `build_log/runs/580_attribution_fix/HANDOFF.md`

**Not pushed.** Deployment gets its own instruction, per the brief and the `ca68f2f` / `bea1787`
precedent. No schema edits. No pipeline behaviour changed — no verdict, no state, no count moves.

**Tests: 549 passed, 1 failed, 3 skipped.** The one failure is
`test_570d_fail_closed.py::test_production_schema_has_no_contradictory_flag_pairs`, red by design
since 570d-1 and unrelated to this change (it was red before it and is red after). The 9 new guards
in `test_580_attribution.py` all pass.

---

## What changed

**(a) The polarity field now reaches the verdict record.**
`lease_coverage_305.py` — `verdict_record` gains `"absence_adverse_to": element.get("absence_adverse_to")`.
One field, from the schema element already in scope. Until now it stopped there, and 374Z read it
only on the `missing` branch — which 579 measured as seeing 6 of 50 cases.

**(b) The count is annotated, not filtered.** `app.js` — `coveredCount` is untouched; a sibling
`_otherPartyCovered` drives a note. LP-11 now reads:

> **15 of 17 elements covered — 10 protect the landlord**

Each row the note is about carries a `protects landlord` tag beside its label, so the number is
checkable against the table rather than trusted.

**(c) A `Covered:` list is rendered**, beside the existing `Missing:` list, itemising every
present element with `→ landlord` on the ones that protect the other side.

Plus five CSS rules, deliberately quieter than `.cv-missing-item` — this is context, not a finding.

**Filtering was considered and rejected**, per 579 §6: three of the 38 are genuinely dual (payment
due date, late fee, CGL minimum), so subtracting would make the number wrong in a new way.
`test_count_is_annotated_not_filtered` exists specifically to fail if a later change subtracts,
because filtering looks like the more decisive fix and is not.

---

## Verified on device, and it caught a defect in my own fix

Loaded through the real user path on a clean load — navigate to `/results/{job_id}`, click the tab,
look. No manual `switchResultsTab`, which is how items 1 and 2 of 571-impl were wrongly reported.

**First pass found the tag was wrong.** It appeared on all 50 polarity-matched rows including
`missing` ones — *"Abandonment or vacating as event of default · protects landlord"* with a Missing
badge beside it. On an absent element the polarity means the opposite thing: its **absence** is
adverse to the landlord; it protects nobody. Gated to present-tier verdicts and a guard added.

**After the fix, both lenses, measured in the live DOM:**

```
                      row tags   Covered: items marked other-party   topics with a count note
tenant lens              37                  37                              14
landlord lens            65                  65                              27
                                            of 120 covered items total
```

Tags and list agree exactly on both lenses, and **0 tags on non-present rows**. The landlord figure
of 65 of 120 matches 579's independently computed mirror-case figure of 65 of 121 — different run,
same magnitude.

The clearest single artefact, landlord lens, LP-25 Condemnation:

> **6 of 7 elements covered — 6 protect the tenant**
> Covered: Lease termination right on total or material partial taking → tenant · Rent abatement
> or reduction on partial taking → tenant · Allocation of condemnation award → tenant · …

Six of six. Before this change that read "6 of 7 elements covered" and nothing else.

**Fixture:** two gitignored jobs under `RESULTS_DIR` — `attribcheck-tenant`, `attribcheck-landlord`
— built from the stored Butler run with `absence_adverse_to` injected from the schema, which is
exactly what (a) now writes (same source, same field, no transformation). **What the browser check
verifies is the frontend against the new contract. It does not verify the backend write** — that is
covered by `test_verdict_record_carries_absence_adverse_to` and by reading the line. Said plainly
so it is not read as more than it is.

---

## One thing found while verifying, not fixed and not mine to fix here

On the landlord fixture the **KEY ISSUES header read "Perspective: Tenant" while the results-page
pill read "Analyzed from landlord perspective"** — two resolvers on one screen disagreeing.

`app.js:13719-13734` resolves the header from `pr.perspective` and, when absent, from the most
common `coverage_assessment[].exposure_perspective`. 577 established `perspective` is **not** a
top-level key in the stored result, so the fallback always runs.

**This is a fixture artefact, not a live defect** — I served a tenant-run result under a landlord
job, which a real run never does, because the exposure layer runs under the job's lens. But the
divergence being *possible* is exactly what 577 §3.3 predicted, and it is a real path the moment a
stored result is re-viewed under a different lens. It strengthens 577's recommendation to write
`perspective` to the top level, which remains the cheapest item in that queue.

---

## What this does not fix — stated because it must not be mistaken for a solution

**Annotation makes the misattribution visible. It does not make the element list less
landlord-framed.** LP-11 still asks 17 questions written from the landlord's side (574); this
change tells a tenant that clearly rather than fixing it. A reader now sees "10 of these 15 protect
the other party" and that is an honest sentence about a question set that should not have been
10-for-15 in the first place.

**The repair is the derivation work on the remaining 29 topics** (574–576), and 578's directional
phrasing, which changes what is asked rather than how the answer is labelled. This is the smaller
of the two jobs and it is the one that was safe to do today.

**Nor does it recover `covered_unfavorable`** (580-1). That remains a separate decision with its own
measurement.

---

## The recurring pattern, written down

At Tzvi's direction: `Docs/Design_Note_Display_Failures_Diagnosed_As_Logic_2026_09_06.md`.

Three instances — the `covered_unfavorable` removal (580-1), the disclosure banners (`bea1787`),
and the retained-but-unrendered dissent (571-impl item 1). The note records the shape, why it
recurs in this system specifically, what to check before changing a detector because its output
looks wrong, and where it predicts the next instance is. **Flagging the location for a decision:**
`Docs/` is largely Chat's, and this is a builder-side observation — say if it belongs elsewhere.

This step's own first on-device pass is a fourth instance in miniature, in the other direction: I
wrote a display that asserted something false, and only looking at it caught that.

---

## Files

```
cam/adapters/lease_review/lease_coverage_305.py            (modified — 580-2(a), one field)
05 Lease Analyzer/static/app.js                            (modified — 580-2(b) and (c))
05 Lease Analyzer/static/style.css                         (modified — 5 rules)
cam/adapters/lease_review/tests/test_580_attribution.py    (new, 9 guards)
Docs/Design_Note_Display_Failures_Diagnosed_As_Logic_2026_09_06.md   (new)
build_log/580_chat_instruction.md                          (modified — 580-2 section appended)
build_log/580-2_code_status.md                             (new, this file)
build_log/runs/580_attribution_fix/make_attrib_fixture.py  (new, the verification fixture builder)
```

No schema change. Version numbers not touched — `stamp_asset_versions` content-hashes at serve time.

## Decisions needed

1. **Deployment is a separate instruction.** This is a defect in what a user reads, in the same
   class as `ca68f2f` and `bea1787`, and on that precedent it ships alone with its effect written
   down. It is not bundled with 570d-1 or the other undeployed items.
2. **The design note's home.** `Docs/` follows the `Design_Note_Structural_Addressing_2026_07_14.md`
   precedent, but the directory is largely Chat's.
3. **`perspective` as a top-level stored field** is now recommended by three steps (577, 578, and
   the artefact above). It is one field and it is the prerequisite for the rerun diff telling a lens
   change from a real change.
4. **The `Covered:` list is long on some topics** — 17 items on LP-11. It is collapsed behind
   nothing today, unlike the element table. Worth a look on a real screen before it ships.
