# Step 545 — The veto is deliberate and specified. The headline is not: it is a canned per-LP string that asserts absence about two LPs whose `elements_missing` is empty.

**Date:** 2026-09-03 · **Instruction:** `build_log/545_chat_instruction.md`
**DIAGNOSTIC + PROPOSAL. No code changed. Tests: 406 passed, 3 skipped, 12 subtests. Not deployed.**

---

# 0. THE FINDING THAT REFRAMES THE BRIEF

```
atlas(524) LP-26 Quiet Enjoyment      elements_found: 6   elements_missing: 0   []
           headline: "Quiet enjoyment covenant absent or undefined"
ex6-4      LP-25 Condemnation          elements_found: 6   elements_missing: 0   []
           headline: "Condemnation rights are undefined"
ex6-4      LP-11 Default & Remedies    elements_found: 15  elements_missing: 1
           missing: ['Third-party (mortgagee or guarantor) cure right on tenant default']
           headline: "Default and remedy framework absent or incomplete"
```

**Two of the three have an empty `elements_missing` list in the same record whose headline says the
provision is absent.** That is not a judgement call about state semantics; it is a flat contradiction
inside one object. **And the headline is not derived from that record at all** — §4.

---

# 1. `derive_lp_state`, IN FULL — AND THE VETO IS SPECIFIED, NOT INCIDENTAL

`cam/adapters/lease_review/lease_coverage_305.py:1096-1168`:

```python
def derive_lp_state(element_results: list[dict], elements_305: list[dict],
                    perspective: str = "tenant") -> str:
    if not element_results:
        return "review_needed"

    opposite = _OPPOSITE_PARTY.get((perspective or "tenant").lower())
    polarity_by_id = {e.get("element_id"): e.get("absence_adverse_to") for e in elements_305}

    def _is_favorable_absence(r: dict) -> bool:
        return (opposite is not None
                and r["verdict"] == "missing"
                and polarity_by_id.get(r["element_id"]) == opposite)

    high_severity_ids = {
        e["element_id"] for e in elements_305
        if e.get("absence_severity") == "high"
    }

    any_unclear = any(r["verdict"] == "unclear" for r in element_results)
    all_non_adverse = all(
        r["verdict"] in PRESENCE_VERDICTS or _is_favorable_absence(r)
        for r in element_results
    )
    missing_or_disputed = [
        r for r in element_results
        if r["verdict"] in ("missing", "disputed") and not _is_favorable_absence(r)
    ]
    high_severity_missing = any(r["element_id"] in high_severity_ids for r in missing_or_disputed)

    if any_unclear:
        return "review_needed"

    if all_non_adverse:
        return "covered"

    total = len(element_results)
    n_missing = len(missing_or_disputed)

    if high_severity_missing:
        if n_missing > total // 2:
            return "missing"
        return "partial"

    if n_missing > 0:
        return "partial"

    return "covered"
```

## Branch order and what each branch protects

| # | branch | protects against |
|---|---|---|
| 0 | `not element_results` → `review_needed` | Reporting a conclusion when no element was evaluated. Fail-closed. |
| 1 | `any_unclear` → `review_needed` | **Asserting an LP conclusion while any sub-question is unresolved.** |
| 2 | `all_non_adverse` → `covered` | Counting a *favorable* absence (a missing burden on this perspective) as a gap — Step 374Z. |
| 3 | `high_severity_missing` + majority missing → `missing` | Calling a substantively absent provision merely "partial". |
| 4 | `high_severity_missing` → `partial` | Calling an LP with a serious gap "covered". |
| 5 | `n_missing > 0` → `partial` | Any residual gap reaching `covered`. |
| 6 | else → `covered` | — |

**Branches 1 and 2 are order-dependent and the order is load-bearing:** an LP with six present
elements and one `unclear` satisfies neither `all_non_adverse` (unclear is not a presence verdict) nor
any missing branch, so without branch 1 it would fall to branch 6 and return `covered`. **The veto is
not merely first — without it these LPs return `covered`, which is the wrong answer.**

## Is it deliberate? Yes, and it is written down twice.

**`Docs/Step_305_Architecture.md:179`, §7 LP-state derivation:**

> *"One or more elements `unclear` at merge → `review_needed` (**overrides other states**)"*

**`Docs/Step_305_Architecture.md:228`:**

> *"Claim 7 (system-level abstention). Element-level `unclear` routes to `review_needed` at the LP
> level. The system declines to assert at the element layer when evidence is insufficient or evaluators
> disagree."*

**"overrides other states" is explicit and parenthesised.** The code implements the spec verbatim; it is
not an artefact of unclear being the easiest case.

**What the spec does NOT do is quantify it.** Two lines below the rule, §7 says:

> *"The exact thresholds (how many missing makes partial vs missing, what counts as 'most') are set in
> the build instruction with empirical validation against the existing T-fixture corpus."*

**Thresholds were anticipated for the missing/partial boundary and for nothing else.** The unclear
override was written as absolute and never revisited against a corpus. **So: the rule is deliberate;
its unquantified scope is unexamined.**

**One more thing the architecture already knew.** §8's schema pilot named five LPs as *"the ugly
cases"* — *"abstention-prone"* — and **LP-11, LP-22, LP-26 and LP-27 are four of the five.** Every
exemplar in this report is on that list. The architecture predicted where abstention would concentrate;
it did not predict what the report would then say about those LPs.

---

# 2. THE CENSUS — 6 RUNS, 192 LPs. IT IS A SPECTRUM.

```
TOTAL LPs across 6 runs: 192   review_needed: 32  (16.7%)
cause: {'unclear_veto': 19, 'disputed_critical_override': 11, 'no_elements': 2}
```

**19 of 32 are the unclear veto.** The other 13 are not: 11 come from the Supplement #21 Phase 3
override at `lease_coverage.py:571` (`elements_disputed_critical > 0`) and 2 from the empty-elements
branch. **Both of those are also disagreement-driven, and neither is the citation gate** (Step 544).

## Presence fraction among the 19 veto LPs — continuous, not bimodal

```
  ex6-4/butler     LP-11  present 15/17 = 88.2%  unclear=1  | Default and remedy framework absent or incomplete
  ex6-4/butler     LP-25  present  6/ 7 = 85.7%  unclear=1  | Condemnation rights are undefined
  atlas(524)       LP-26  present  6/ 7 = 85.7%  unclear=1  | Quiet enjoyment covenant absent or undefined
  atlas(522)       LP-26  present  6/ 7 = 85.7%  unclear=1  | Quiet enjoyment covenant absent or undefined
  solidpower(528)  LP-25  present  5/ 7 = 71.4%  unclear=1  | Condemnation rights are undefined
  solidpower(525)  LP-26  present  5/ 7 = 71.4%  unclear=1  | Quiet enjoyment covenant absent or undefined
  ex6-4/butler     LP-15  present  4/ 6 = 66.7%  unclear=1  | Signage rights undefined
  solidpower(528)  LP-01  present  4/ 6 = 66.7%  unclear=2  | Tenant's payment obligation and enforcement...
  divall(496)      LP-23  present  3/ 5 = 60.0%  unclear=2  | Percentage rent calculation, gross sales...
  ex6-4/butler     LP-22  present  5/11 = 45.5%  unclear=1  | Non-disturbance protection absent
  ex6-4/butler     LP-27  present  3/10 = 30.0%  unclear=1  | Landlord default remedies undefined
  ex6-4/butler     LP-02  present  1/ 4 = 25.0%  unclear=1  | No rent escalation cap
  solidpower(528)  LP-05  present  1/ 4 = 25.0%  unclear=1  | Use restrictions absent or undefined
  solidpower(525)  LP-05  present  1/ 4 = 25.0%  unclear=1  | Use restrictions absent or undefined
  divall(496)      LP-05  present  1/ 4 = 25.0%  unclear=1  | Use restrictions absent or undefined
  atlas(524)       LP-12  present  1/ 5 = 20.0%  unclear=1  | No early exit right
  ex6-4/butler     LP-20  present  0/ 7 =  0.0%  unclear=1  | Exclusivity protection absent or undefined
  solidpower(528)  LP-02  present  0/ 4 =  0.0%  unclear=1  | No rent escalation cap
  solidpower(525)  LP-02  present  0/ 4 =  0.0%  unclear=1  | No rent escalation cap
```

**0%, 20%, 25%, 25%, 25%, 30%, 45%, 60%, 67%, 67%, 71%, 71%, 86%, 86%, 86%, 88% — a spectrum with no
gap.** The brief's "four LPs at 1 unclear against 15+ agreed" is the top of a continuous distribution,
not a separate cluster.

**Which is decisive for the proposal: no threshold will cleanly separate the true cases from the false
ones.** A cutoff at 80% rescues LP-11/LP-25/LP-26 and leaves LP-15 at 67% — 4 of 6 present — still
narrated as *"Signage rights undefined"*. **The remedy has to be quantitative reporting, not a
reclassification cutoff.**

**And the bottom of the range is correct as it stands.** LP-20 at 0/7 and LP-02 at 0/4 genuinely are
absent; `review_needed` and an absence headline are both right there. **Any change must not disturb
them.**

---

# 3. WHAT THE STATE SHOULD BE — KEEP `review_needed`. ADD SCOPE, NOT A STATE.

**The state is not the defect.** Something *is* unresolved on all 19, and the spec's abstention
principle is sound: with `LP-25.total_vs_partial_taking` split
`['missing','explicitly_present','unclear']`, the system genuinely does not know. **`covered` would be a
lie in the other direction.**

**The defect is that `review_needed` is scope-free.** It reports *that* something is unresolved and
never *how much*. 1-of-17 and 4-of-4 render identically.

## Do not add a coverage_state

`coverage_state` is read by `_resolve_display`, `resolve_sections`, exposure routing, materiality,
`_classify_partial`, both annotators, the report generator, the summary generator and `app.js`. **Step
522 established what a new bucket costs:** the web consumers are if/else-if chains over
`risk`/`review_needed`/`improvement`, and an unrecognised value makes entries *vanish*. A new state has
that blast radius plus the exposure and materiality tables.

## Do not add a third axis either — the axes already exist, and a third would collide

```
assessment_status : was it judged?          assessed | not_assessed
coverage_state    : what was concluded?     covered | partial | missing | review_needed | ...
```

**The missing quantity is not a third question, it is the resolution of the second one.** So:

## Proposal — `resolution`, a deterministic annotation on the assessment, no state change

Derived from `element_verdicts` alone. **Zero API calls, zero new evidence, no verdict touched:**

```json
"resolution": {
  "total_elements": 17,
  "unresolved_elements": 1,
  "settled_present": 15,
  "settled_absent": 1,
  "unresolved_labels": ["Third-party (mortgagee or guarantor) cure right on tenant default"],
  "unresolved_reasons": {"no_consensus": 1}
}
```

**Wording, everywhere the LP is named.** Keep the state and the bucket; make the label carry the scope:

```
now       REVIEW NEEDED
proposed  REVIEW NEEDED — 1 OF 17 ELEMENTS UNRESOLVED
```

**LP-20 is unaffected in substance** — `0 settled_present`, and Step 538's evidence guard already routes
it to `NO ELEMENTS FOUND`, ahead of any review label.

**This is annotation-only, in the shape Step 524 used for the qualifier cross-reference**, and it does
not require touching `derive_lp_state` — which the brief forbids and which I did not touch.

---

# 4. THE HEADLINE — IT IS A STATIC PER-LP STRING, AND IT NEVER READS THE RECORD

## Where it comes from

**`review_needed` can never reach the model path.** `lease_exposure.py:71`:

```python
_MODEL_STATES = {"covered_unfavorable", "ambiguous", "potentially_unenforceable"}
```

and `:529-533`:

```python
        if state in _MODEL_STATES:
            use_model = True
        elif materiality == "high" and state in ("partial", "missing"):
            use_model = True
```

**`review_needed` is in neither.** Measured: **all 32 review_needed LPs across the six runs carry
`exposure_source: "schema"`. Not one is `model`.**

So `_build_schema_exposure` runs, and `review_needed` matches none of its four branches
(`covered`, `not_applicable`, `partial`, `missing`) — it falls to the catch-all, `:201`:

```python
    stmt = schema_statement or f"{name}: {state}."
    return _shape(stmt, missing[:2])
```

`schema_statement` is the LP's **static `exposure_statement` from the knowledge schema**, and the
headline is `extract_headline()` of it:

```
LP-26  "Quiet enjoyment covenant absent or undefined; tenant's right to undisturbed possession
        depends on state law..."                    -> 'Quiet enjoyment covenant absent or undefined'
LP-11  "Default and remedy framework absent or incomplete; landlord enforcement position
        significantly weakened"                     -> 'Default and remedy framework absent or incomplete'
LP-25  "Condemnation rights are undefined; tenant may receive no portion of the condemnation
        award..."                                   -> 'Condemnation rights are undefined'
```

**These strings are keyed to the LP id and nothing else.** They are written for the absent case — the
only case the catch-all was ever expected to serve — and they are emitted verbatim regardless of the 6
or 15 elements the panel confirmed. **The headline does not disagree with the record; it never consults
it.**

## Can it be made truthful without changing the state? Yes — one branch, no state change, no model call.

Insert an explicit `review_needed` branch in `_build_schema_exposure` **before** the catch-all,
composing from `element_verdicts`:

```
LP-11:  headline  "1 of 17 elements unresolved"
        statement "15 of 17 expected elements are confirmed present. One is unresolved:
                   third-party (mortgagee or guarantor) cure right on tenant default —
                   evaluators did not reach consensus."
LP-26:  headline  "1 of 7 elements unresolved"
        statement "All 7 expected elements are confirmed present; constructive eviction
                   coverage is unresolved — evaluators did not reach consensus."
LP-20:  headline  "Exclusivity protection absent or undefined"      (unchanged — 0 of 7 present)
```

**The state stays `review_needed`, the bucket stays `worth_reviewing`, no verdict moves, and the
schema strings stay in place for the LPs they are true about.** The branch reads data the record
already carries.

## One further falsity in the same line, named but out of this step's scope

The DOCX callout header is built at `lease_docx_annotator.py:557`:

```python
        lines = [f"[GAP] {pid} {pname} — {headline} ({mat_label} materiality)"]
```

and the `Missing:` line at `:562` is emitted **only when `elements_missing` is non-empty**. **So LP-26
and LP-25 render as `[GAP] … absent or undefined` with no missing element listed at all** — the marker
asserts a gap the record does not contain. **Fixing the headline does not fix `[GAP]`**; the marker is
chosen by bucket, and that is a display change I am not proposing here.

---

# 5. `per_evaluator_lp_verdicts` — NO. SURFACE THE COUNTS INSTEAD.

## First, a correction to the premise: the web screen already shows the detail

```
element_verdicts   in app.js : 12 sites
evaluator_verdicts in app.js : 17 sites
```

plus a `dispute_signal` note and badge rendering *"Critical dispute — majority verdict withheld … Baseline
verdict: <state>"*. **A reader on the web screen can already open an LP and see every element and every
evaluator.**

**The exports cannot.** `element_verdicts` appears **zero times** in `lease_report_generator.py`, both
annotators, and `summary_generator.py`. **The gap is the DOCX and PDF, not the product as a whole** —
and those are the artefacts a lawyer marks up.

## Why not `per_evaluator_lp_verdicts` specifically

It is written at `lease_coverage.py:623` and read only by `05 Lease Analyzer/_step372_decomp.py`, an
analysis script. **Putting it on a reader surface would place three evaluator LP-level verdicts beside
the merged state and invite the reader to count votes** — which is precisely what the architecture
forbids, `Docs/Step_305_Architecture.md:39`:

> *"Final LP coverage state is derived deterministically from per-element evaluator outputs, not from
> raw regex signals, not from exposure text, and **not from a direct LP-state vote**."*

**A reader who sees "C: explicitly_present, A: explicitly_present, B: explicitly_present" next to
"REVIEW NEEDED" will conclude the system contradicted its own panel.** It did not — the panel agreed at
LP level and split on one sub-element, and the LP-level roll-up is a derived convenience, not the
evidence.

## What to surface instead

**The `resolution` counts from §3, and the unresolved element's label.** That answers the reader's
actual question — *what is unresolved, and how much is settled* — without exposing a vote that the
architecture says is not the basis of the state. **It is the same information, at the layer where the
system actually decided.**

---

# WHAT IS NOT ESTABLISHED

- **Nothing was built.** `derive_lp_state` was not touched, per the brief. §3 and §4 are proposals; no
  code implements them.
- **I did not judge whether the individual `unclear` verdicts are correct.** LP-26's
  `['covered_in_other_LP','unclear','unclear']` and LP-25's `['missing','explicitly_present','unclear']`
  may or may not be reasonable disagreements — that needs the clause text, not a census. **If they are
  wrong, the abstention is spurious and the right fix is upstream of everything in this report.**
- **The proposed wording is not tested against a reader.** *"1 of 17 elements unresolved"* is more
  truthful than *"absent or incomplete"*; whether it is more *useful* to a lawyer is untested.
- **The `[GAP]` marker on LP-25/LP-26 stays false under this proposal.** Named in §4, not solved.
- **Six runs on four documents, 192 LPs.** The 16.7% review_needed rate and the shape of the spectrum
  are this corpus's; quanterix, everbridge, ncino and atreca have no completed runs.
- **`_classify_materiality` remains unexamined** — all three exemplars are `materiality: low`, including
  a quiet-enjoyment covenant and a 17-element default framework. Flagged since Step 539, still not
  this step's subject.
- **I did not measure how many `partial` or `missing` LPs carry a schema headline that misstates their
  record.** The catch-all is only reached by `review_needed`, but the `partial` and `missing` branches
  also emit static schema strings, and I checked only the review_needed path.
