# Step 430 — Gate B cross-lease measurement (Atreca + Atlas)

**Date:** 2026-07-19
**Status:** COMPLETE — read-only measurement, no source file modified, nothing wired
**Instruction:** `build_log/430_chat_instruction.md` (confirmed present on disk, read in full before any code)
**Harness:** `build_log/run_430_gate_b_cross_lease.py` · **Raw results:** `build_log/430_gate_b_cross_lease_sidecar.json`

> This is a two-lease diagnostic. It does not establish system performance and
> does not validate the architecture. No baseline is established or cited.

---

## Headline verdict

| Lease | Gate B (report mode, N=5) | Failing (LP, dependency) pairs |
|---|---|---|
| **Atreca** (built on) | **pass — 5/5 runs** | none |
| **Atlas** (never seen) | **degraded — 5/5 runs** | `(LP-07, building_share)` — and only that |

**Answer to the first question this step was meant to settle:** Atlas's
`building_share` miss is **`absent_by_structure`** — the healthy classification.
**There is no `present_but_missed` result anywhere in this measurement, on
either lease.** 429 did not regress.

**But the headline is not the whole finding, and the rest of it is worse news
than a clean failure would have been.** Atlas's `tenant_share` and `base_rent`
did **not** fail — they resolved 5/5 to verified spans that Gate B accepted,
and **both are wrong in ways Gate B is structurally unable to see**:

- `tenant_share` resolved to Atlas's **"Proportionate Share" (22.4%)** — a
  different concept from the operating-expense split it declares.
- `base_rent` resolved to a **definitional stub containing no rent amount at
  all**.

Gate B counts both as satisfied. That is the real finding of 430.

---

## 1. Configuration integrity

| | prompt_hash | config_hash | canonical | fallback_used |
|---|---|---|---|---|
| Atreca (5 runs) | `bbb1e99d0963887d` | `7c2ac3de05b6e9ba` | `True` | `False` |
| Atlas (5 runs) | `bbb1e99d0963887d` | `7c2ac3de05b6e9ba` | `True` | `False` |

**PASS.** Single-valued across all 5 runs of each lease, identical **between**
the two leases (as expected — prompt and config do not vary by document), and
identical to the hashes recorded in 427, 428 and 429. The prompt, schema,
resolver, and declared config were not touched by this step.

Document identity:

```
Atreca: source_document_hash = 7118cc6ddf65bd7b09f436071f02c431bacc14b2a7c66bb9f84f8335ded0b03b
        canonical_text length = 160145   (raw parsed = 160244)
Atlas:  source_document_hash = da9b5655c5cab382577f139a1884625d81f42b2610a146042018026dc28d2b71
        canonical_text length = 31755    (raw parsed = 31755)
```

Atreca's hash matches 426/429 exactly, confirming same document, same
`canonical_whitespace_v2` profile.

---

## 2. Atreca — per parameter (N=5)

| Parameter | Rate | Offsets (all 5 runs) | Distinct texts | Verbatim span text |
|---|---|---|---|---|
| `tenant_share` | **5/5** | `[1942, 1996)` | 1 | `Tenant's Share of Operating Expenses of Building: 100%` |
| `building_share` | **5/5** | `[1997, 2032)` | 1 | `Building's Share of Project: 45.79%` |
| `rent_adjustment_pct` | **5/5** | `[2097, 2127)` | 1 | `Rent Adjustment Percentage: 3%` |
| `base_rent` | **5/5** | `[1695, 1815)` | 1 | `Base Rent:\n$3.75 per rentable square foot of the Premises per month, subject to adjustment pursuant to Section 4 hereof.` |

Offset-stable and text-stable on every parameter. **These offsets are
byte-identical to the ones 429's Gate C recorded** — the same four spans at the
same four positions, now reproduced in a separate harness on a separate day.

Every Atreca span carries its value (checked by regex over the span text, not
by eye): `100%`, `45.79%`, `3%`, `$3.75`.

Gate B: `pass` on all 5 runs, zero failures.

---

## 3. Atlas — per parameter (N=5)

| Parameter | Rate | Offsets | Classification | Verbatim span text / probe evidence |
|---|---|---|---|---|
| `tenant_share` | **5/5** | `[1738, 1889)` | resolved — **but concept-substituted, see §5** | `"Proportionate Share" shall mean 22.4%, representing the ratio of the rentable area of the Demised Premises to the total rentable area of the Building.` |
| `building_share` | **0/5** | — | **`absent_by_structure`** | declared needles probed: `["Building's Share of Project Operating Expenses percentage", "Building's Share of Project"]` → **0 hits**; harness aliases `["Building's Share", "Project Operating Expenses", "Building's Proportionate Share"]` → **0 hits** |
| `rent_adjustment_pct` | **5/5** | `[4248, 4327)` | resolved — but an approximation, see §5 | `The above schedule reflects an annual escalation of approximately 3% per annum.` |
| `base_rent` | **5/5** | `[990, 1065)` | resolved — **but value-less, see §5** | `"Base Rent" shall mean the annual rent payable as set forth in Section 3.1.` |

All three resolved parameters are offset-stable and text-stable across all 5
runs (one distinct offset pair and one distinct span text each). Gate B:
`degraded` on all 5 runs, failing only `(LP-07, building_share)`.

### Probe evidence for `building_share = absent_by_structure`

Deterministic substring counts against Atlas's canonical text (code-side, not
model judgment, re-verified independently of the harness):

```
count("Operating Expenses")            = 0
count("Building's Share")              = 0
count("Tenant's Share of Operating")   = 0
count("Proportionate Share")           = 3
count("Base Rent")                     = 13
```

**Atlas contains the string "Operating Expenses" zero times in its entire
31,755-character text.** The concept `building_share` declares — a building's
share of *project operating expenses* — does not exist in this lease in any
form, under any declared label or harness alias. The miss is a true fact about
the document.

(Probe normalization unified curly/straight quotes and case before matching, so
an apostrophe variant could not produce a false `absent_by_structure`. Both
fixtures were separately confirmed to use straight apostrophes only, so this
was defensive and changed nothing.)

---

## 4. Atreca result — stated plainly

Gate B passes on Atreca, 5/5, with all four declared dependencies satisfied by
verified, offset-stable spans that each carry their value. LP-02 receives
`[base_rent, rent_adjustment_pct]`; LP-07 receives `[tenant_share,
building_share]`. This reproduces 429's Gate C independently and confirms the
429 target-resolution fix holds.

---

## 5. Atlas result — stated plainly, and separated from the above

Three distinct things happened on Atlas. They must not be collapsed.

### (a) `building_share` — Gate B is working correctly

`building_share` is unsatisfiable on Atlas because the concept is genuinely
absent (zero occurrences of "Operating Expenses"). Gate B detected exactly that
and refused to certify LP-07, on all 5 runs, naming precisely the one
dependency that failed and no others.

**This is Gate B functioning as designed.** It is a fail-closed gate correctly
reporting that a declared dependency cannot be satisfied by this document. The
finding is not a bug — it is that **the dependency map is Atreca-shaped and
does not transfer unchanged to a differently-structured (warehouse,
single-proportionate-share) lease.**

This is sharply distinct from a `present_but_missed` result, which would mean
the concept was in the text and the machinery failed to find it — a 429
regression. **No parameter on either lease classified `present_but_missed`.**

### (b) `tenant_share` — resolved, stable, and conceptually wrong

This is the finding that neither anticipated bucket covers, and it is the
important one.

`tenant_share` declares `element_label = "Tenant's Share of Operating Expenses
percentage"`. On Atlas it resolved 5/5, stably, to:

> `"Proportionate Share" shall mean 22.4%, representing the ratio of the rentable area of the Demised Premises to the total rentable area of the Building.`

Atlas's own text defines what that 22.4% is used for (§3.3, verbatim):

> `Tenant shall pay to Landlord, as Additional Rent, Tenant's Proportionate Share of: (i) Real Estate Taxes for each calendar year during the Term; and (ii) Common Area Maintenance charges ("CAM Charges")...`

It is a **rentable-area ratio applied to Real Estate Taxes and CAM Charges** —
not a tenant's share of operating expenses, a concept this lease does not
contain. The elicitor was asked for one concept and returned the nearest
available different one, and the resolver verified it because the quote is
genuinely present in the document.

**Gate B accepted it.** Gate B is keyed to declared dependency *names* and
`span.verification_status` only — by deliberate design (427: "never reads a
span's text or value"). That design is what makes it lease-general, and it is
also precisely what makes it blind here: a verified span for the *wrong
concept* is indistinguishable from a verified span for the right one.

This is not a resolution defect. The 429 machinery did its job perfectly —
5/5, byte-stable offsets. It is a **validity** gap sitting above resolution:
**Gate B measures that a dependency is satisfied, not that it is satisfied by
the right thing.**

### (c) `base_rent` — resolved to a span carrying no rent

`base_rent` resolved 5/5, stably, to Atlas's §1.2 definitional stub:

> `"Base Rent" shall mean the annual rent payable as set forth in Section 3.1.`

Checked by regex over the span text: **no monetary value and no percentage —
the span contains no number other than the cross-reference "3.1".** The actual
rent lives 3,200 characters away in the §3.1 schedule, which the span does not
reach:

> `Lease Year 1 (April 1, 2026 - March 31, 2027): $18.50 per rentable square foot per annum ($342,250.00 per annum; $28,520.83 per month)`

428's brief named this failure mode in advance: *"A span reading `Tenant's
Share of Operating Expenses of Building:` without `100%` is a FAILURE dressed
as a success, and it is exactly the kind of thing that would pass a naive
check."* On Atreca that warning was satisfied — every span carried its value.
**On Atlas, `base_rent` is that exact failure, and Gate B passed it.**

### (d) `rent_adjustment_pct` — resolved to a descriptive approximation

Softer, recorded for completeness. It resolved 5/5 to:

> `The above schedule reflects an annual escalation of approximately 3% per annum.`

This is a narrative aside describing a schedule, hedged with "approximately" —
not a contractual parameter of the kind Atreca's `Rent Adjustment Percentage:
3%` is. The number happens to be right. Whether a described approximation
should satisfy a declared parameter dependency is a judgment this measurement
does not make.

---

## 6. What this closes and what it does not

**Closes:** Gate B is validated as a *mechanism* on both leases. It correctly
certifies Atreca (4/4 satisfied) and correctly refuses Atlas's `building_share`
(genuinely absent), with stable, reproducible behavior across 5 runs each and
clean config integrity. 429's target-resolution fix reproduces independently and
did not regress on an unseen lease — no `present_but_missed` anywhere.

Worth noting as secondary evidence for 429's design: on Atreca the model
returned **echoed** target labels (`"Target 1: Tenant's Share of Operating
Expenses percentage"`), while on Atlas it returned **bare** ordinals
(`"Target 1"`). The output form varies by document, and the 429 ordinal parse
handled both without incident. Pre-429 exact-string code would have discarded
the entire Atreca run.

**Does NOT close — wiring remains blocked, now for two named reasons:**

1. **Gate B is not "passed on both leases" in the 423 §8 sense.** §8 requires
   the declared dependency to be *satisfied*; on Atlas `(LP-07,
   building_share)` is not, so LP-07 cannot be evaluated on this lease under
   the current map. The dependency map needs a per-document-type story before
   this is anything other than "Atlas is out of scope."
2. **New, and not on the pre-430 blocker list: Gate B satisfaction does not
   imply parameter validity.** Two of Atlas's three "satisfied" parameters are
   wrong — one concept-substituted, one value-less — and Gate B cannot detect
   either, because it reads names and verification status by design. Wiring the
   parameter block now would feed LP-02 a Base Rent parameter carrying no rent,
   with a verified span and a green gate, on any lease shaped like Atlas.

Point 2 is the same defect class 421C and 428 documented, one layer further
out: **the gate is working, and the thing it certifies is not the thing we
need it to certify.** In 428 correctly-located evidence was lost before the
gate; here incorrect evidence passes it. Both were invisible to "did the gate
pass."

---

## 7. Design questions surfaced — NOT answered here

Recorded as open decisions for a follow-on. 430 deliberately does not resolve
any of them.

1. **Global vs. per-document-type dependency map (423 spec §5.2).** Should
   `DEPENDENCY_MAP` be global, or keyed by document type, so a warehouse lease
   with a single "Proportionate Share" simply does not declare
   `tenant_share`/`building_share`? The §9 `NOT_APPLICABLE` contract is the
   natural home for "this lease type does not declare this dependency" — that
   is a lead, not a decision.
2. **Does a parameter need a validity check as well as a verification check?**
   Nothing currently asserts that a `base_rent` span contains a rent, or that a
   `tenant_share` span is about operating expenses. Adding one would move Gate B
   away from its deliberately lease-general, literal-free design — a real
   tension (427 doctrine: "never contains a lease-specific literal"), not an
   obvious win. Where such a check belongs, if anywhere, is undecided.
3. **Should concept-substitution be detectable at all at this layer,** or is it
   properly the selection panel's job (423 §6, unbuilt)?

---

## 8. Scope compliance

- **No file under `cam/` was modified.** `git status --porcelain cam/` returned
  empty before staging and after the run.
- `enforce_gate_b` was called in `canonical=False` (report) mode only, so
  Atlas's full failure structure was captured rather than aborting on first
  failure. `check_gate_b` (pure) supplied the per-pair table.
- The classification probe and the alias list are **harness-side only**. They
  read `PARAMETER_TARGETS` for declared labels/synonyms and do deterministic
  substring matching. No fuzzy or semantic matching was built. Nothing was
  written back into any source module.
- Nothing wired. No dependency map, `PARAMETER_TARGETS`, prompt, schema,
  resolver, normalization profile, or gate function was edited to make Atlas
  pass.
- The Atlas result was captured on the first execution and **not re-run,
  massaged, or reinterpreted**.

---

## Files Changed

- `build_log/430_chat_instruction.md` — sanctioned instruction (pre-existing)
- `build_log/run_430_gate_b_cross_lease.py` — read-only harness (new)
- `build_log/430_gate_b_cross_lease_sidecar.json` — raw N=5×2 results (new)
- `build_log/430_gate_b_cross_lease.md` — this report (new)

No source file under `cam/` was created, modified, or deleted.
