# Step 554 — The cause is one word. `reserved` matches "Certain Rights **Reserved** By Landlord", and the lease says the opposite of the headline.

**Date:** 2026-09-04 · **Instruction:** `build_log/554_chat_instruction.md`
**DIAGNOSTIC. No code changed. Not deployed.**

---

# 0. THE HEADLINE FINDING

`cam/adapters/lease_review/lease_negative_space.py:34`:

```python
_RESERVED_PATTERN = re.compile(
    r"\b(intentionally\s+omitted|intentionally\s+left\s+blank|reserved|"
    r"this\s+section\s+intentionally|omitted\s+intentionally)\b",
    re.IGNORECASE,
)
```

**A bare `reserved` alternative.** It fires on solidpower LP-29 at the section heading:

```
23. Certain Rights Reserved By Landlord . Provided that such actions shall not materially
interfere with Tenant's use and quiet enjoyment of the Premises, Landlord shall have the
following rights:
```

**"Rights reserved to Landlord" is not "this section is reserved".** The detector cannot tell them
apart, the LP short-circuits to `broken_xref` before the panel runs, and the report emits a canned
sentence about a 2,793-character provision nobody read.

---

# 1. WHAT `broken_xref` IS — TWO CAUSES, AND ONLY ONE HAS EVER FIRED

**Definition**, from Step 539's state table (`build_log/539_code_status.md`):

> *"`broken_xref` — A section exists but points at something absent or reserved. The lease is internally
> incomplete."*

**Signal definition**, `lease_negative_space.py:11-12`:

> *"`reserved_or_omitted` — section marked Reserved / Intentionally Omitted"*
> *"`broken_xref` — cross-reference to a section/exhibit not found in document"*

## Two set sites, both in `lease_coverage.py`

**Cause A — `lease_coverage.py:467`, the reserved/omitted short-circuit:**

```python
        reserved_signals = [s for s in ns if s["signal_type"] == "reserved_or_omitted"]
        if reserved_signals:
            _a = _build_assessment(
                pid=pid, area=area, coverage_state="broken_xref",
                evidence_summary="Section or subsection explicitly marked as omitted or reserved",
                elements_found=[], elements_missing=get_expected_elements(pid),
                assessment_status="not_assessed",
            )
            ...
            continue
```

**Cause B — `lease_coverage.py:498`, no tenant text plus xref/exhibit signals:**

```python
                xref_signals = [s for s in ns if s["signal_type"] in ("broken_xref", "missing_exhibit")]
                state = "broken_xref" if xref_signals else "missing"
```

**It is two causes, and across all six runs only Cause A has ever fired.** Every one of the seven
carries `evidence_summary: "Section or subsection explicitly marked as omitted or reserved"`. **Cause B
has zero observations**, so nothing in this report describes it.

**Both sites already set `assessment_status="not_assessed"` explicitly** (Step 522), and both assert
`elements_missing=get_expected_elements(pid)` — every expected element declared missing with no
evaluator involved.

---

# 2. THE PANEL NEVER RAN. IT DID NOT RUN AND RETURN NOTHING.

Both sites `continue` **before** the Step-305 panel is reached. Measured on all seven:

```
element_verdicts  : 0
coverage_method   : None          <- not "step_305_per_element"
fallback_used     : None          <- not False; the field was never set
```

**`coverage_method` is `None`, not `step_305_per_element`.** A panel that ran and produced nothing would
set the method and record `fallback_used: False`. **These LPs never reached an evaluator**, which is why
`_build_scope_exposure` returns `None` on them and the Step-546 treatment cannot help: there is no
record to compose from.

**And the provisions are not empty.** `tenant_text` lengths: 1380, 5199, 2793, 2793, 3053, 178, 52.
**The text was extracted and is sitting on the record — it was simply never evaluated.**

---

# 3. ALL SEVEN, WITH GROUND TRUTH READ FROM THE DOCUMENT

## FALSE — 3 of 7 (2 distinct provisions)

### solidpower LP-29 Right of Entry (both the 525 and 528 runs)

> **Headline:** *"Landlord may enter premises without notice, at any time, for any purpose — disrupting
> tenant's business operations, exposing confidential business information…"*

**The lease, verbatim from `tenant_text`:**

> *"23. Certain Rights Reserved By Landlord . **Provided that such actions shall not materially
> interfere with Tenant's use and quiet enjoyment of the Premises**, Landlord shall have the following
> rights:"*
>
> *"(a) Building Operations … to enter upon the Premises (**after giving Tenant reasonable notice
> thereof, which may be oral notice, except in cases of real or apparent emergency**, in which case no
> notice shall be required)…"*
>
> *"(c) Repairs and Maintenance . To enter the Premises **at all reasonable hours**…"*
>
> *"(d) Prospective Purchasers and Lenders . To enter the Premises at all reasonable hours … **with one
> (1) days prior notice**…"*
>
> *"(e) Prospective Tenants . **At any time during the last nine (9) months of the Term** … with one (1)
> days prior notice…"*

**All three of the headline's assertions are false.** *Without notice* — the lease requires reasonable
notice and one day's notice for showings. *At any time* — entry is limited to reasonable hours, and the
prospective-tenant right is confined to the last nine months. *For any purpose* — five enumerated
purposes under an overriding non-interference proviso. **Trigger word: `'Reserved'`, in the heading.**

### divall LP-01 Rent & Payment Terms

> **Headline:** *"No enforceable rent obligation"*

**The lease, verbatim:**

> *"3.1 One Time Fixed Rental Charge . **Intentionally Omitted** .
> 3.2 Base Rent . **During the Term, Tenant covenants and agrees to pay to Landlord, in advance on the
> first da…**"*

**One sub-clause is omitted and the very next line establishes base rent.** The trigger is real; the
inference from it is not. **A sub-clause marked omitted was read as the whole LP being absent.**

## TRUE — 3 of 7

| LP | trigger, verbatim | headline | verdict |
|---|---|---|---|
| ex6-4 LP-23 Percentage Rent | *"(b) Percentage Rent : [intentionally omitted]"* | *"Percentage rent obligations unenforceable or undefined"* | **true** — the provision genuinely is omitted |
| divall LP-02 Rent Escalation | *"1.15 Fixed Rent Increases: Intentionally Omitted / 1.16 Lease Years to which Fixed Rent Increases Apply: Intentionally Omitted"* | *"Rent frozen at initial amount for entire term"* | **true**, though "frozen" is an inference beyond the text |
| divall LP-21 Guaranty | *"ADDENDUM A / PERSONAL GUARANTY - Intentionally Omitted"* | *"**If a guaranty was negotiated,** landlord has no enforceable third-party recourse…"* | **true, and the only hedged one** |

**LP-21 is the shape the others should have.** Its schema string opens with a conditional, so it
describes a consequence without asserting a fact about the document.

## UNVERIFIABLE — 1 of 7

**solidpower(528) LP-07 CAM.** Headline *"Tenant may owe undefined share of all building operating
expenses with no audit protection."* **`_RESERVED_PATTERN` does not match its stored `tenant_text` at
all** — I re-ran the detector against the 5,199-character record and got no match. The signal fired on
the extraction-stage provision text, which is not what the assessment stored, so **I cannot reproduce
the trigger and cannot judge the prose. Marked unverifiable rather than guessed.**

## Tally

```
FALSE        3  (solidpower LP-29 x2, divall LP-01)
TRUE         3  (ex6-4 LP-23, divall LP-02, divall LP-21)
UNVERIFIABLE 1  (solidpower LP-07)
```

**The two false provisions are the two where the trigger word appears in ordinary lease English**
(`Reserved` in a heading; an omitted sub-clause beside a present one). **The three true ones are all
`intentionally omitted` standing alone as the entire clause.**

---

# 4. THE PROSE — THE SAME CATCH-ALL AS `review_needed`

**Same path, not its own.** `broken_xref` matches none of `_build_schema_exposure`'s branches
(`covered`, `not_applicable`, `partial`+missing, `missing`, and the Step-546/547 scope branch, which
declines on `total_elements == 0`), so it falls to:

```python
    stmt = schema_statement or f"{name}: {state}."
    return _shape(stmt, missing[:2])
```

**Measured: all seven carry `exposure_source: schema`, `exposure_reason_code: schema_default`.**

It also cannot reach the model path. `_classify_materiality` at `lease_exposure.py:121`:

```python
    if state == "broken_xref":
        return "medium"
```

`broken_xref` is not in `_MODEL_STATES`, and the high-materiality branch admits only `partial`/`missing`
— so **medium materiality guarantees the schema path**, and every one of the seven is
`materiality: medium, requires_attention: True`.

**Step 545's diagnosis transfers exactly: a static per-LP string keyed to the LP id and nothing else.**
The difference Step 547 named still holds — for `review_needed` the string contradicted a record; here
there is no record for it to contradict.

**An encoding defect, noticed in passing:** solidpower LP-29's stored statement contains `ג€”` where an
em-dash belongs — a UTF-8 sequence decoded through a Hebrew codepage. It is in the persisted result, not
only in my terminal.

---

# 5. WHAT A READER SEES — THE EXPORTS CONTAIN IT; THE WEB PROBABLY DOES NOT

**`assessment_status: not_assessed` is set on 4 of 7.** The three divall entries carry `None` because
that run predates Step 522, and `_resolve_display` fail-closes them to
`ASSESSMENT STATUS NOT RECORDED` — the intended behaviour.

**All seven resolve to the `not_assessed` bucket, which is not in `ANNOTATED_BUCKETS`, so none gets a
margin callout.**

## The export suppresses the prose. Verified in the deployed artefact.

From the Step-549 production PDF, the section a reader actually sees:

> **Not Assessed**
> *The following provisions were NOT evaluated. They are not findings and they are not clean bills of
> health — no judgment was reached about them, so their absence from the sections above means nothing
> was checked, not that nothing was wrong.*
> **LP-23 Percentage Rent  [NOT ASSESSED]**
> *No evaluation was performed for this provision.*

```
'Percentage rent obligations unenforceable or undefined' present in the 159-page PDF: False
'LP-23' occurrences: 1
```

**The headline appears nowhere in the artefact.** The DOCX block is the same shape
(`lease_docx_annotator.py:455-464` renders id, name and label only). **Step 522 already contains this
damage in the exports** — the prose is generated and persisted, and no export renders it.

## The web screen is the exposure, and I did not open it

`app.js:18203`:

```javascript
        var _astatus = finding.assessment_status || 'unset';
        if (_astatus !== 'assessed') return 'review_needed';
```

and `app.js:17247`:

```javascript
    const headline = (a.exposure_headline || _deriveHeadlineFromExposure(stmt)).trim();
```

**`assessment_status` appears exactly once in 18,000+ lines of `app.js`, and its only effect is to route
the item into the ordinary `review_needed` bucket** — where the LP row renders `exposure_headline` like
any finding. On that path solidpower LP-29 would read *"Landlord may enter premises without notice, at
any time…"* under **Needs Review**, presented as a finding rather than as an absence.

**This is a code trace, not an observation. I did not open the page.** Step 522's own comment at
`app.js:18198` says the same thing about itself — *"the per-LP label does not yet say WHICH kind of
review; that needs the web surface exercised, which this step did not do."* **It still has not been.**

## The brief's judgement, tested

*"A headline asserting a specific landlord right, backed by nothing, is worse than silence."* **On the
evidence, yes — and the export layer already agrees.** Its *"No evaluation was performed for this
provision"* is exactly the silence the brief argues for, and it is what a lawyer reading the marked-up
lease gets today. **The remaining exposure is one surface and one line of JavaScript.**

---

# WHAT IS NOT ESTABLISHED

- **Nothing was fixed**, per the brief.
- **The web surface was not exercised.** §5's claim that the false headline renders on screen is traced
  through `app.js`, not observed. **It is the one thing in this report I could have checked and did
  not.**
- **solidpower LP-07 is unverifiable** — the stored `tenant_text` does not match `_RESERVED_PATTERN`, so
  I could not reproduce its trigger or judge its prose. §3.
- **The negative-space signals on the record carry an empty `excerpt`** in every one of the seven, so the
  matched text is not persisted. **I recovered the trigger words by re-running the detector against
  `tenant_text`**, which worked for six of seven and is why the seventh is unverifiable. The signal's
  own `match.group(0)` is captured at `lease_negative_space.py:206` but does not survive into the
  assessment.
- **Cause B has never been observed.** Everything here describes Cause A; the no-tenant-text path may
  behave differently and is unmeasured.
- **Six runs, four documents.** Whether `reserved`-in-a-heading is common across leases generally is not
  measured — it appeared in one of four documents here, twice.
- **I did not check the other `_RESERVED_PATTERN` alternatives for the same weakness.**
  `intentionally omitted` is specific enough to be safe on this evidence, but I tested it on three
  instances, not systematically.
- **The `ג€”` mojibake was not traced to its source** — schema file, extraction, or serialisation.
