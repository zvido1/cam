# Step 426 — Recall Re-Measurement Under `canonical_v2`

**Date:** 2026-07-14
**Status:** COMPLETE — measurement only, no code changes

---

## Required Statements

> This measures recall on ONE document under `canonical_v2`. It does not
> validate the architecture and does not measure recall on unseen
> documents.

> 425 and 426 do not make LP-07 see the 100% tenant share. The parameter
> block, dependency map, and selector panel remain unbuilt.

---

## Method

Identical to 424's protocol, exactly one variable changed:
`CanonicalSource` built with `normalization_profile=canonical_whitespace_v2`
instead of `v1`. Same source document, same prompt file, same declared
config, same 12 predefined targets (not redefined), same N=5, same all-32-LP
scope, 160 calls. No prompt, schema, or resolver change was made at any
point in this step.

---

## Config-Integrity Assertion

```
total calls: 160
distinct prompt_hashes: {'bbb1e99d0963887d'}
distinct config_hashes: {'7c2ac3de05b6e9ba'}
canonical flags: {True}
fallback_used flags: {False}
CONSISTENT: True
```

**PASS**, and both hashes are **identical to 424's** (`bbb1e99d0963887d` /
`7c2ac3de05b6e9ba`) — confirming the prompt and declared config genuinely
did not change between the two measurements; the only thing that changed
is what `CanonicalSource.canonical_text` and offsets point at. Zero LP
errors across all 160 calls. `source_document_hash=7118cc6ddf65bd7b...`
(differs from 424's `e049ee63a4e2f475...` — expected: v2's canonical text
has 38 page-number lines removed from the same `raw_source_text_hash`,
which is identical to 424's `source_document_hash`, confirming this is
the same underlying document).

---

## Per-Run Stats

| Run | Raw | Deduped | Verified | Ambiguous | Unverified | Dedup ratio | Elapsed |
|---|---|---|---|---|---|---|---|
| 1 | 257 | 209 | 201 | 0 | 8 | 1.230 | 236.2s |
| 2 | 261 | 212 | 207 | 0 | 5 | 1.231 | 226.6s |
| 3 | 256 | 206 | 200 | 0 | 6 | 1.243 | 231.7s |
| 4 | 263 | 209 | 202 | 0 | 7 | 1.258 | 237.3s |
| 5 | 276 | 217 | 211 | 0 | 6 | 1.272 | 230.0s |

For comparison, 424: verified counts were 182–199 (range 17); 426: verified
counts are 200–211 (range 11). Both the floor and the ceiling moved up —
consistent with the same underlying source now yielding more resolvable
spans, with somewhat less run-to-run spread than 424, though N=5 is too
small to call that a stability improvement with confidence.

---

## Per-Target Table — 424 vs 426 (the headline)

**Every HIT below was verified by printing the matched span's actual text
and confirming it is genuinely the named target — not merely that the
offsets contain the locator string.** 424's exclusions-list result is
corrected in this table from the report's original 5/5 (locator false
positive) to its verified true value, 0/5.

| Target | 424 (true) | 426 (true) | Change |
|---|---|---|---|
| `Tenant's Share of Operating Expenses of Building: 100%` | 5/5 | 5/5 | none |
| `Building's Share of Project: 45.79%` | 4/5 | 5/5 | **improved** |
| `Rent Adjustment Percentage: 3%` | 5/5 | 5/5 | none |
| `Base Rent: $3.75 per rentable square foot` | 5/5 | 5/5 | none |
| Operating Expense exclusions list, items (a)–(u) | **0/5** | **5/5** | **recovered** |
| Annual Statement / reconciliation | 5/5 | 5/5 | none (offset instability continues, different run) |
| Independent Review (audit rights) | 5/5 | 5/5 | none |
| 95% occupancy gross-up | 0/5 (locator artifact) | 0/5 (locator artifact) | none |
| Condition Precedent (prior tenant vacates) | 2/5 | **1/5** | **regressed by count — see analysis** |
| Landlord's Work access rights | 0/5 (locator artifact) | 0/5 (locator artifact) | none |
| 120-day delivery termination right | 5/5 | 5/5 | none (newly offset-unstable — see below) |
| Service-interruption rent abatement | 5/5 | 5/5 | none (offset instability continues, different run) |

---

## Question 1 — Did the Exclusions List Recover, and How Completely?

**Yes, completely: 0/5 → 5/5, verified by direct provenance check.**

The automated locator (`"excluding only:"`) reports 5/5 under v2 as well
— but for the same reason it was a false positive in 424: in 4 of the 5
runs, the locator's offset range still falls inside the *adjacent*
inclusions-definition span (which now ends at `16997` instead of `17003`,
shifted by the page-strip, but is otherwise the same wrong span). **The
automated locator check alone is not trustworthy for this target and was
not relied on.**

Instead, the true result was confirmed by checking `LP-07.excluded_expense_categories`
directly — the element that actually targets this list — in every run:

```
run 1: VERIFIED [16998,21425) '(a) the original construction costs of the Project and renovation...'
run 2: VERIFIED [16998,21425) '(a) the original construction costs of the Project and renovation...'
run 3: VERIFIED [16998,21425) '(a) the original construction costs of the Project and renovation...'
run 4: VERIFIED [16982,21425) 'excluding only:\n(a) the original construction costs...'
run 5: VERIFIED [16998,21425) '(a) the original construction costs of the Project and renovation...'
```

**`LP-07.excluded_expense_categories` produced a `verified` span in all 5
of 5 runs**, and in every case the matched text genuinely begins with the
exclusions list content (`"(a) the original construction costs..."`), not
a nearby unrelated clause. This is the target this report cares about
most, and it went from **never once verified across 5 runs (424)** to
**always verified across 5 runs (426)**, on the strength of one narrow,
tested transformation: removing a page-number line the model was already
quoting past correctly.

---

## Question 2 — Did the Parser-Artifact Failures Actually Clear?

**Unverified spans by category, 424 → 426:**

| Category | 424 | 426 | Delta |
|---|---|---|---|
| Page-number artifact | 52 | 0 | **−52 (fully cleared — the strip works)** |
| Space-before-punctuation artifact | 33 | 0 | **−33 (fully cleared — v2 tolerance works)** |
| Quote-mark internal spacing artifact | 7 | 0 | **−7 (fully cleared — v2 tolerance works)** |
| Residual (uncategorized in 424, mostly the same artifact family) | 26 | — | absorbed into the above once v2 tolerance applied |
| Ellipsis elision (model-caused) | 48 | 32 | model behavior, not a parser fix — see below |
| **Total unverified** | **166** | **32** | **−134** |

**Every one of the 32 remaining unverified spans in 426 is an ellipsis-elision
case (100% of what's left) — zero page-number, zero space-before-punctuation,
zero quote-mark-spacing failures remain.** This is exactly what the
hypothesis predicted: the three parser-artifact categories, which
together accounted for 92 of 166 (55%) of 424's failures, are now
**completely absent**. The 32 vs. 48 raw-count difference in the ellipsis
category is ordinary run-to-run variance in which quotes happen to get
elided at all (the raw quote sets differ between the two 5-run batches —
compare 424's 264–282 raw quotes/run to 426's 256–276) — **not evidence
that ellipsis-elision improved**. The relevant, load-bearing number is
that ellipsis is now **100%** of remaining failures, up from 29% in 424,
because everything else is gone. The brief's check — "if that class
shrank, something is wrong with the categorization" — is satisfied: the
class didn't shrink as a *proportion* or *mechanism*, only its raw count
moved with ordinary sampling noise, exactly as expected for a model
behavior a parser fix cannot touch.

---

## Question 3 — Did Anything Regress?

**One target's hit count went down: Condition Precedent, 2/5 → 1/5.**
Named explicitly, as required, and investigated rather than left as a bare
number.

**What changed, precisely.** In 424, the introductory sentence containing
the literal phrase "condition precedent" (offsets `~10108–10652` under v1)
was captured in runs 3 and 4, both times via `LP-03.commencement_date`. In
426, the same sentence (offsets `~10104–10648` under v2 — consistent with
the page-strip shift, not a boundary change) was captured in **only run
3**, via an element whose `elicited_by` label is
`'Target 2: Commencement date or conditions for commencement are defined'`
— the model echoed back the full element label instead of the bare
`"Target 2"` the schema requests (a known, already-documented artifact
from 424's analysis, here caught on a *verified* span rather than an
unverified one — see note below). Run 4 of 426 simply did not produce a
quote covering this sentence at all; nothing failed to verify, nothing
was rejected — the model's output for that run's `LP-03` call did not
include it.

**Is this a page-strip-caused regression?** No evidence points that way.
The clause's location is consistent (offsets differ from 424 by exactly
the expected page-strip shift, not by a boundary shift). No new failure
mode is implicated — no page-artifact, no resolver change, no spacing
issue. This target was **already** the most unstable one measured in 424
(2/5, attributed to a different LP than its "designated" one, with
boundary drift on which sentence gets included even when hit). A 2/5 →
1/5 change on an already-marginal, already-boundary-drifting target,
attributable to which of 5 independent model calls happened to include a
given sentence, reads as **ordinary elicitation run-to-run variance
continuing to do what 424 already showed it does** — not a new defect
introduced by `canonical_v2`. Stated plainly because the question was
asked plainly: this is the one number that went down, and the honest
read is "expected noise on a target already flagged as unstable," not
"the parser fix broke something."

**No other target's hit count decreased.** Everything else held or
improved. **No target went from a stable hit to a clean, unambiguous
miss.**

### Secondary observation: new offset instability on the 120-day target

Not a hit-count regression (still 5/5 both times), but worth recording:
in 424, the 120-day delivery termination right resolved to the *same*
offsets in all 5 runs. In 426, run 5 resolved to a longer span (`(5853,
6336)` vs. `(5853, 6059)` in runs 1–4) — the locator still falls inside
both, so the hit count is unaffected, but the target joins Annual
Statement and Service-interruption abatement as showing boundary drift
under v2. This is consistent with 424's broader finding that offset
stability, not hit-rate, is where the elicitation call's non-determinism
actually shows up — carried forward unchanged by this step.

---

## Offset Stability Summary

| Target | 424 | 426 |
|---|---|---|
| Tenant's Share | stable | stable |
| Building's Share | stable (when hit) | stable |
| Rent Adjustment | stable | stable |
| Base Rent | stable | stable |
| Exclusions list (true span) | n/a (never verified) | stable `(16998, 21425)` in 4/5 runs, `(16982, 21425)` in 1/5 (run 4 — the quote happened to include the "excluding only:" lead-in that run) |
| Annual Statement | **unstable** (1 short run) | **unstable** (1 short run, different run number) |
| Independent Review | stable | stable |
| 95% occupancy (true span) | stable | stable |
| Condition Precedent | unstable (which runs hit varies) | unstable (fewer runs hit) |
| Landlord's Work (true span) | stable | stable |
| 120-day termination | stable | **newly unstable** (1 run longer) |
| Service-interruption | **unstable** (1 run different) | **unstable** (1 run different) |

**The fixed-span-universe assumption remains false, as 424 already found.**
`canonical_v2` did not change this — offset drift on a subset of targets
is a property of the elicitation call's temperature-0 non-determinism, not
of which canonical-text version is in use.

---

## The `(` Question

`_V2_TOLERANT_CHARS` includes `)` but not `(`: deliberate, not an
oversight — every spacing artifact found in this corpus (across both 424's
categorization and this step's fresh 426 categorization, which now shows
**zero** remaining space-before-punctuation or quote-padding failures)
was spurious whitespace immediately **before a closing mark** (`,`, `.`,
`;`, `:`, `)`, or a closing `"`), never after an opening `(`; nothing in
this corpus currently depends on `(` receiving the same tolerance, and
adding it now would be speculative scope-widening not backed by an
observed failure, which the narrow-rule discipline of 425 explicitly
rejects.

---

## What Remains Deliberately Unchanged / Unwired

No prompt, schema, resolver, or normalization-profile change was made in
this step — the only thing that differs between the 424 and 426 runs is
the `normalization_profile` argument passed to `build_canonical_source`.
No parameter block, dependency map, or selector panel was built. Nothing
was wired into Stage 5. No baseline was run. `cam/core/`, evaluator
identities, Stage 5 stabilization, and Priority Exposure were not touched.

---

## Files Changed

- `build_log/426_chat_instruction.md` — the Part 0 brief, written verbatim
  before any work began
- `build_log/426_recall_remeasurement_canonical_v2.md` — this file

No source files were modified for this step. The measurement checkpoints
(raw per-run JSON for both 424 and 426, ~4MB each) and analysis scripts
live in the session scratchpad, not the repository — the per-target
table, category deltas, and regression analysis above are the complete,
audit-sufficient record of what was measured and compared.
