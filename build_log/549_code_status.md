# Step 549 — The deploy is live and every presentation change is visible. Three things differ from the local figures, and two of them are defects I shipped.

**Date:** 2026-09-03 · **Instruction:** `build_log/549_chat_instruction.md`
**Job `lease_review_20260903_200838_80c9fa`, `run_quality: clean`, 1,388s wall. Result and server-generated PDF persisted to `build_log/runs/549_deployed_butler_crossing/`.**

---

# 0. THE THREE DIFFERENCES

1. **LP-20 is softened. It reads *"1 of 7 elements unresolved"* where Step 537 gave `NO ELEMENTS
   FOUND`.** The trigger is a panel move — one element flipped to `explicitly_present` — but the
   headline my Step-546 branch writes **drops the five absent elements entirely**. The statement below
   it names them; the headline does not. **This is a regression I introduced.**
2. **LP-11 and LP-25 print the canned absence prose again**, through the half of `partial` that Step 547
   deliberately left alone. *"Default and remedy framework absent or incomplete"* on **16 of 17 elements
   present**. **The fix covered the wrong half of `partial`.**
3. **20 of 26 findings could not be anchored** — Step 543 measured 4, against a substitute carrier.
   Only **6 sticky notes** exist in a 159-page artefact.

Everything else reproduced.

---

# 1. THE SERVICE — UP, FRESHLY BOOTED, `unhealthy` FROM SDK DRIFT ONLY

```
started_at 2026-09-03T19:42:28Z   checked_at 19:42:43Z   elapsed 15.1s
status: "unhealthy"    error: null
```

**All seven models listed, callable, and served as requested. No `raw_error`, no `is_fallback`.**

```
anthropic  claude-sonnet-4-6          panel A primary       callable served=claude-sonnet-4-6   1.08s
anthropic  claude-haiku-4-5-20251001  panel A own-fallback  callable                            0.46s
openai     gpt-5.5                    panel B primary       callable served=gpt-5.5             2.43s
xai        grok-4.3                   panel C primary       callable served=grok-4.3            2.13s
google     gemini-3.1-pro-preview     extractor primary     callable                            2.84s
google     gemini-2.5-pro             shared fallback pool  callable                            2.60s
anthropic  claude-haiku-4-5-20251001  document gate         callable                            0.64s
```

`status: unhealthy` is driven **entirely** by two SDK alerts against `deps.manifest.json`:

```
google-api-python-client   expected 2.199.0, installed 2.200.0
google-genai               expected 2.20.0,  installed 2.22.0
```

**11 of 13 packages match the manifest exactly.** The manifest was generated from production on
2026-08-31 while status was `healthy`, and its own header explains why this fires now:
*"Railway re-resolves dependencies on every push."* **This push did not touch `requirements.txt`** —
which pins ranges (`google-genai>=2.0.0,<3.0.0`) — **but the act of deploying re-resolved them.** Step
514's mechanism working as designed.

**The deployed extractor therefore ran `google-genai` 2.22.0. My 427 local tests ran against 2.20.0.**
The extraction reproduced byte-for-byte anyway (§2), so the drift had no observable effect here.

*(`curl` cannot reach this host from the project shell — Windows schannel fails revocation checking with
`CRYPT_E_NO_REVOCATION_CHECK`. All requests went through Python `urllib`. Not a service problem.)*

---

# 2. THE RUN

## Meta — the document is identical, the run is clean

```
                                 Step 537 (local)          Step 549 (deployed)
mode                             analyze                   analyze
source_document_hash             0e8df550ec6c7ff6...       0e8df550ec6c7ff6...   IDENTICAL
extraction_model                 gemini-3.1-pro-preview    gemini-3.1-pro-preview
extraction_fallback_used         False                     False
extraction_finish_reason         FinishReason.STOP         FinishReason.STOP
extraction_parse_repaired        False                     False
extraction_completeness_failed   False                     False
run_degraded                     False                     False
fallback_events                  0                         0
coverage entries                 32                        32
api_calls_total                  90                        91
elapsed_sec                      2339.29                   897.23
```

**The extracted-text hash is identical**, so the panel saw the same document. `panel_substituted: False`,
`run_quality: clean`, `report_incomplete: False`.

**Wall clock 1,388s against `elapsed_sec` 897s — a 491-second gap**, the same unaccounted-time pattern
Step 491 recorded (`elapsed_sec` 745.6s vs harness 1238.4s, ~493s). Unexplained then, unexplained now.

## The top line — five categories, live, from the deployed PDF

> *"3 issue area(s) require attention, 8 worth reviewing, 18 substantially addressed with minor gaps,
> 2 NOT ASSESSED, 1 covered."*

Against **Step 537's "27 covered"**. The 18 partials are named as partials, `not_assessed` sits beside
the line and not inside it, and `covered` is 1 — LP-09, which the panel moved to `covered` this run.

## Panel movement — 12 of 32

```
LP-03  Lease Term & Renewal      ('review_needed',5,0) -> ('review_needed',4,0)
LP-09  Subletting & Assignment   ('partial',9,0)       -> ('covered',10,0)
LP-11  Default & Remedies        ('review_needed',15,1)-> ('partial',16,1)
LP-16  Parking                   ('partial',4,2)       -> ('partial',3,2)
LP-17  Dispute Resolution        ('partial',4,1)       -> ('partial',5,0)
LP-19  Utilities                 ('partial',4,0)       -> ('partial',5,0)
LP-20  Exclusivity               ('review_needed',0,5) -> ('review_needed',1,5)
LP-22  SNDA                      ('review_needed',5,1) -> ('review_needed',5,2)
LP-24  Damage & Destruction      ('partial',4,3)       -> ('review_needed',4,1)
LP-25  Condemnation              ('review_needed',6,0) -> ('partial',6,1)
LP-26  Quiet Enjoyment           ('partial',5,1)       -> ('partial',5,0)
LP-27  Landlord Default          ('review_needed',3,4) -> ('review_needed',2,4)
```

**12 of 32, against Step 491's 13 of 32 across three runs of identical configuration.** Within the
measured band — **with one caveat that matters: Step 491 measured Atlas, not butler_crossing.** No
run-to-run variance figure exists for this document; this is the first repeat of it, so "within
variance" is an inference from a different lease, not a measurement of this one.

---

# 3. LP-20 — SOFTENED. THE PANEL MOVED, AND MY HEADLINE MADE IT WORSE.

**The brief's check was "still NO ELEMENTS FOUND, still genuinely absent, not softened." It is not.**

## What the panel did

```
                              Step 537     Step 549 (deployed)
LP-20.exclusive_use_scope     missing      missing        C/B/A all missing
LP-20.existing_tenant_carveouts missing    missing        C/B/A all missing
LP-20.incidental_use_carveouts  missing    missing        C/B/A all missing
LP-20.radius_restriction      disputed     explicitly_present   C/B/A ALL explicitly_present
LP-20.competing_use_definition  unclear    unclear        C=unclear B=present A=unclear
LP-20.exclusivity_duration    missing      missing        C/B/A all missing
LP-20.remedies_for_violation   missing     missing        C/B/A all missing
```

**One element moved: `radius_restriction`, from a 2-1 split to unanimous `explicitly_present`.** Five of
seven elements are still unanimously missing and `elements_missing` still carries all five.

## What the code then did — correctly, at each step, to a bad end

`settled_present` went 0 → 1. So **Step 538's zero-elements guard correctly did not fire** (an element
*is* present), and **Step 546's scope branch correctly did fire** (`settled_present > 0`). Display moved
from `NO ELEMENTS FOUND / needs_attention / ✕` to `REVIEW NEEDED — 1 OF 7 ELEMENTS UNRESOLVED /
worth_reviewing / ○`.

## The artefact, quoted from the deployed PDF

```
LP-20 Exclusivity -- 1 of 7 elements unresolved
Missing: Specific exclusive use scope is defined (protected business activities), Carve-outs for
existing tenants at the center are addressed, Carve-outs for ancillary or incidental use by other
tenants are addressed, Duration of exclusivity is defined (full term or limited period), Remedies
for landlord violation of exclusivity are defined
1 of 7 expected elements are confirmed present and 5 absent. 1 element unresolved (evaluators
split): Definition of 'competing use' is provided.
```

**The statement is correct — "and 5 absent" is there, exactly as the Step-546 polarity work intended.
The HEADLINE is not.** *"1 of 7 elements unresolved"* reports the smallest of the three numbers and
**silently drops the five absences**, and the headline is what the header line, the checklist and the
cover summary render.

**The old headline was TRUE on this record.** A retail tenant with no exclusive-use scope, no
carve-outs, no duration and no remedies is accurately described by *"Exclusivity protection absent or
undefined"*. My branch replaced it because one element out of seven turned up.

**The defect is the guard, not the panel.** `settled_present == 0` is a knife-edge: a single element
flipping moves an LP from "absent" to "unresolved". **The guard should be about whether absence
dominates** — when `elements_missing` is non-empty, the headline must carry the absent count, and when
absences outnumber present elements the absence framing is still the truthful one. **Not fixed here;
this step is verification.**

---

# 4. LP-11 AND LP-25 — THE CANNED ABSENCE PROSE IS BACK, THROUGH THE OTHER HALF OF `partial`

```
LP-11 Default & Remedies -- Default and remedy framework absent or incomplete
Missing: Third-party (mortgagee or guarantor) cure right on tenant default
Default and remedy framework absent or incomplete; landlord enforcement position significantly weakened
        present 16/17   unresolved 0   elements_missing 1   reason_code schema_default

LP-25 Condemnation / Eminent Domain -- Condemnation rights are undefined
Missing: Definition of total taking vs material partial taking is provided
Condemnation rights are undefined; tenant may receive no portion of the condemnation award...
        present 6/7     unresolved 0   elements_missing 1   reason_code schema_default
```

**Both were `review_needed` at Step 537 and both moved to `partial` this run.** A `partial` with a
non-empty adverse-missing list matches `if state == "partial" and missing:` — the pre-existing branch —
and gets the LP's static schema string.

**Step 547 §2 said this explicitly: *"a partial with a real gap keeps the branch above unchanged."*
That was the wrong call, and this run is the evidence.** The branch produces exactly the falsity Step
545 named: **16 of 17 elements confirmed present, headline says the framework is absent.** Step 547
fixed the 19 partials with *no* gap and left the ones *with* a gap, and a single missing element out of
seventeen is enough to trigger prose written for total absence.

**The correct scope is: any state whose record shows most elements present must not inherit prose
written for absence — `review_needed`, `partial` with an empty missing list, and `partial` with a small
one.** Only the third is still broken.

---

# 5. WHAT REPRODUCED EXACTLY

**LP-26 Quiet Enjoyment** — the Step-547 `partial_scope` path, working as designed:

```
LP-26 Quiet Enjoyment -- 2 of 7 elements unresolved
5 of 7 expected elements are confirmed present. 2 elements unresolved (evaluators split): Remedies
for breach of quiet enjoyment are specified or cross-covered; Constructive eviction is acknowledged
or addressed in the lease.
        present 5/7   unresolved 2   elements_missing 0   reason_code partial_scope
```

**The Step-545 headline "Quiet enjoyment covenant absent or undefined" is gone, on a live run.**
LP-05 and LP-06 likewise: *"1 of 4 elements unresolved"*, *"1 of 5 elements unresolved"*.

**The `[REVIEW]` marker and the export scope lines are live**, quoted from a sticky note in the deployed
PDF:

```
[REVIEW] LP-26 Quiet Enjoyment -- 2 of 7 elements unresolved (LOW materiality)

Resolved: 5 of 7 expected elements confirmed present.
Unresolved (2): Remedies for breach of quiet enjoyment are specified or cross-covered; Constructive
eviction is acknowledged or addressed in the lease

5 of 7 expected elements are confirmed present. 2 elements unresolved (evaluators split): ...
```

**Steps 522 and 524 are visible too** — the "NOT ASSESSED" count in the top line, and "NOT WEIGHED"
blocks quoting the qualifier cross-reference. Both `not_assessed` entries are LP-12 and LP-23.

---

# 6. THE EXPORT — AND A DROP RATE FIVE TIMES WHAT STEP 543 MEASURED

```
admitted (ANNOTATED_BUCKETS)   537: 30    549: 29    (LP-09 left, now `covered`)
of which state == missing       —          3         LP-14, LP-28, LP-31: no clause to anchor
attempted                       —         26
rendered as sticky notes        —          6         3 [GAP] + 3 [REVIEW]
anchor drops                    —        *20*
```

The accounting closes: **26 attempted − 20 dropped = 6 rendered**, and the artefact contains exactly 6
callout annotations across 159 pages.

**Step 543's reader-facing note is live and it is the first thing under "Findings" on page one:**

> *"Note: 20 finding(s) below could not be placed beside a clause in the marked-up document and appear
> in this summary only: LP-01, LP-02, LP-03, LP-06, LP-07, LP-08, LP-10, LP-11, LP-13, LP-15, LP-17,
> LP-18, LP-20, LP-21, LP-22, LP-24, LP-25, LP-27, LP-29, LP-30."*

**Step 543 measured 4 drops and flagged the number as carrier-specific**, because the ex6-4 fixture is
`.txt` and that test used `T-04_subtle.docx` as a stand-in. **The real figure on the real document is 20
of 26 — 77%.** The note is doing its job and nothing is lost to a reader, but **the margin now carries
under a quarter of the findings**, and LP-20 is among the twenty with no callout at all.

`annotation_reports.pdf` is on the persisted result with every drop recorded — the Step-543 contract,
working on a production run.

---

# WHAT IS NOT ESTABLISHED

- **Neither defect in §3 or §4 is fixed.** This step was verification. Both need their own brief.
- **One run.** Everything about panel movement rests on a single deployed run against a single local
  run of the same document. **12 of 32 is compared to Step 491's 13 of 32 measured on Atlas** — a
  different document, three runs, all local. There is no run-to-run variance measurement for
  butler_crossing.
- **I cannot separate deploy effects from run variance.** The deployed environment differs from local on
  `google-genai` (2.22.0 vs 2.20.0) and `google-api-python-client`. The extraction hash is identical, so
  the extractor produced the same text — but the panel differences could be sampling, environment, or
  both, and one run cannot tell them apart.
- **No DOCX was generated.** The deployed job produces the annotated **PDF** only for this path
  (`annotated_path` names a `.pdf`, and `annotation_reports` carries a `pdf` key and no `docx` key). §3
  of the brief asked for both; **the DOCX side of the deployed pipeline is unexercised and I did not
  fabricate one by running the annotator locally.**
- **The 491-second gap between wall clock (1,388s) and `elapsed_sec` (897s) is unexplained**, as at
  Step 491.
- **`_classify_materiality` is untouched** — LP-26 quiet enjoyment still reads "(LOW materiality)".
- **The web screen was not opened.** Only the API and the generated PDF were inspected.
