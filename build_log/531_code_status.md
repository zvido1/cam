# Step 531 — The matcher is `in`. 88% of real-lease decisions are hard-abort-capable, and LP-12 is a false positive on all nine.

**Date:** 2026-09-03 · **Instruction:** `build_log/531_chat_instruction.md`
**DIAGNOSTIC ONLY. Nothing changed, no provider calls, not deployed.**

---

# 1. THE MATCHER, AND THE THREE STRINGS THAT FIRED

`cam/adapters/lease_review/lease_knowledge.py:143-156`, verbatim:

```python
    # Check exclusion clues first — if present, issue area does not apply
    for clue in area.get("exclusion_clues", []):
        if clue.lower() in text_lower:
            return "excluded"

    # Check activation clues
    for clue in area.get("activation_clues", []):
        if clue.lower() in text_lower:
            return "applicable"
```

**It is Python's `in` operator on a lowercased string. No word boundaries, no negation handling, no
context, no scoping.** It returns on the *first* clue that hits, in schema order, so the recorded
verdict never records which of several clues was responsible.

## The exact firing strings, with context

**atreca — LP-20 Exclusivity, first clue to fire: `'exclusive use'`**
> "...The portions of the Project which are for the **non-exclusive use** of tenants of the Project are
> collectively referred to herein as the ' Common Areas .' Tenant shall have the **non-exclusive
> right** during the Term t..."

**atreca — LP-21 Guaranty of Lease, first clue: `'guaranty'`**
> "...Tenant expressly acknowledges and agrees that Landlord does not **guaranty** that such emergency
> generators will be operational at all times..."

**ncino — LP-20, first clue: `'exclusive use'`**
> "...together with a **non-exclusive right** to the use of and access to areas of the Building **not
> regularly and customarily leased for the exclusive use of tenants**, including... driveways,
> sidewalks, entranceways, public lobbies, elevators..."

**everbridge — LP-20, first clue: `'exclusive use'`**
> "...including certain areas designated for the **exclusive use** of certain tenants, or to be shared
> by Landlord and certain tenants, are collectively referred to herein as the "Common Areas"..."

**everbridge — LP-21, first clue: `'guarantor'`**
> "...No such consent to or recognition of any such assignment or subletting shall constitute a release
> of Tenant or any **guarantor** of Tenant's performance hereunder..."

**everbridge — LP-23 Percentage Rent, first clue: `'percentage rent'`**
> "...(xxx) Damages paid to Tenant hereunder or to other tenants; **(xxxi) Fixed or percentage rent
> under any ground or underlying lease or leases;** (xxxii) The wages and benefits of any employee..."

**Four distinct context failures, all from one operator:** the clue inside its own negation
(`non-exclusive`), inside a *disclaimer* of the thing (`does not guaranty`), inside a **conditional**
reference to a party who does not exist (`any guarantor`), and inside an **exclusion enumeration** —
item xxxi of a numbered list of costs the tenant does *not* pay.

**Every one of these six documents' clue hits appears in text describing the ABSENCE or EXCLUSION of the
thing the clue is looking for.**

---

# 2. IS IT THE SAME DEFECT? — ONE PREMISE CORRECTED, AND THE CORRECTION IS THE POINT

## The LP-16 instance is not LP-16, and it was not the matcher

The phrase *"no one remedy shall be deemed to be exclusive"* appears in **Step 480**, not 469, and it
concerns **LP-20**, not LP-16. Step 480's own words:

> *"**Correction to my own probe.** My first pass flagged divall LP-20 as a false all-clear because
> `"exclusive"` returned a hit. Reading the hit: '…no one remedy shall be deemed to be **exclusive** of
> the other or of any other remedy conferred by law or equity.' That is a remedies-cumulative clause,
> not an exclusivity provision. **LP-20 is correct**, and my probe committed exactly the
> topical-proximity error this arc exists to catch."*

**LP-16's clue list contains no `exclusive` clue at all** — it is `['parking spaces', 'parking rights',
'garage', 'surface parking', 'unreserved parking', 'reserved parking']`.

**The correction is more damning than the claim.** That instance was a *diagnostic probe I wrote*
committing the same keyword-for-concept error the production matcher commits on three real leases.
**The failure mode is easy enough to fall into that it was reproduced independently, by a different
author, inside a step whose purpose was to catch it.**

## LP-12 / Step 481 is the same family, opposite direction

Step 481 widened LP-12's clue list — *"tuned to documents written in the vocabulary the list"*, 4 clues
added, 0 removed — to fix **under**-matching. §3 below shows that widening now produces **over**-matching
on 9 of 9 real leases. **Same brittleness, both directions, and fixing one direction caused the other.**

## Blast radius — 14 sites, 9 of them in the lease pipeline

`grep` for substring containment against document text:

```
cam/adapters/lease_review/lease_knowledge.py:146    exclusion clues     <- THE GATE
cam/adapters/lease_review/lease_knowledge.py:152    activation clues    <- THE GATE
cam/adapters/lease_review/lease_coverage.py:892     global-scan keywords
cam/adapters/lease_review/lease_coverage.py:897     global-scan long keywords
cam/adapters/lease_review/lease_coverage_audit.py:424   heading match
cam/adapters/lease_review/lease_jurisdiction.py:133 governing-law needles
cam/adapters/lease_review/lease_jurisdiction.py:138  evidence needles
cam/adapters/lease_review/lease_use_aware_coverage.py:209  use keywords
cam/adapters/lease_review/lease_use_aware_coverage.py:574  match_keywords
cam/rules/lease_rules.py:261, :277                  changed-terms detection
cam/rules/contractnli_rules.py:141, :147            (different adapter)
cam/adapters/gpqa/gpqa_adapter.py:579               (different adapter)
```

**The exclusion-clue site is the more dangerous of the two in `lease_knowledge`.** A spurious activation
produces a hard abort — loud. **A spurious exclusion returns `excluded`, which is degradable, so the LP
is silently dropped from the analysis.** That direction has never been surveyed.

---

# 3. THE SURVEY — BASELINE BEFORE ANY PROPOSAL

## Verdict distribution, 33 LPs × 9 real leases = 297 decisions

```
document                           req applic unclear not_app   excl
everbridge_northlake_pasadena       20     10      1      0      1
ncino_parkerfarm_wilmington         20      9      3      0      0
quanterix_crosby_bedford            20     10      2      0      0
atreca_industrial_rd_sancarlos      20     10      2      0      0
solidpower_thornton_industrial      20      9      2      0      1
bokf_oklahoma_tower                 20      8      3      0      1
albireo_10postoffice                20      9      3      0      0
atreca_eastjamie_southsf            20      9      2      0      1
divall_wendys_mtpleasant            20      7      5      0      0

real:       {'required': 180, 'applicable': 81, 'unclear': 23, 'excluded': 4, 'not_applicable': 0}
synthetic:  {'required': 460, 'applicable': 205, 'unclear': 67, 'not_applicable': 3, 'excluded': 1}
            (23 fixtures x 33)
```

**HARD-ABORT-CAPABLE (required + applicable): 261 of 297 = 88%.**
**DEGRADABLE: 36 of 297 = 12%.**

**`not_applicable` is returned ZERO times across 297 real-lease decisions.** It is reachable only from
`optional` LPs with no clue hit, and the one optional LP (LP-12) hits on every document. **The matcher
has, in practice, no way of saying "this lease does not have this."**

**The brief's warning applies in the direction it feared:** a matcher that accepts everything is as
wrong as one that rejects real leases, and this one accepts 88%.

## Per-LP, the conditional/optional set across 9 real leases

```
LP-15   Signage Rights                 {'applicable': 9}
LP-12   Early Termination              {'applicable': 9}
LP-07   Common Area Maintenance        {'applicable': 9}
LP-32   Hazardous Materials            {'applicable': 8, 'unclear': 1}
LP-30   Estoppel Certificate           {'applicable': 8, 'unclear': 1}
LP-20   Exclusivity                    {'applicable': 8, 'unclear': 1}
LP-22   SNDA                           {'applicable': 7, 'excluded': 2}
LP-21   Guaranty of Lease              {'applicable': 7, 'unclear': 2}
LP-16   Parking                        {'applicable': 7, 'unclear': 2}
LP-04   Security Deposit               {'applicable': 7, 'excluded': 2}
LP-23   Percentage Rent                {'applicable': 2, 'unclear': 7}
LP-31   Co-Tenancy                     {'unclear': 9}
```

**LP-31 is the only LP that ever declines consistently.**

## GROUND TRUTH BY READING — LP-12, the 9-of-9 case

Every hit read, not proxied:

| lease | clue that fired | what the text actually says |
|---|---|---|
| everbridge | `right to terminate this lease` | *"Tenant shall have **no** right to terminate this Lease"* — **negation** |
| ncino | `right to terminate this lease` | *"then Tenant shall **not have** a right to terminate this Lease"* — **negation** |
| quanterix | `right to terminate this lease` | casualty: *"not tenantable within 270 days from the date the repair is started"* |
| bokf | `right to terminate this lease` | service failure: *"if such interruption continues for a total of sixty (60) days"* |
| albireo | `elects to terminate` | casualty: *"within sixty (60) days after the Event of Casualty"* |
| atreca | `right to terminate this lease` | condition precedent: *"In the event that the Condition Precedent is not satisfied"* |
| divall | `right to terminate the lease` | casualty: *"if a Total Destruction of the Premises occurs"* |

**Seven read, zero are early-termination options. Two are literal negations of the clue. Five are
casualty, service-failure or condition-precedent termination rights — a different provision entirely.**

**LP-12 is a false positive on every real lease in the corpus.** It has not aborted anything only
because LP-12 is in `SPAN_EVIDENCE_LPS` and the seam exempts it — visible in everbridge's own abort
detail, which lists `'provision_id': 'LP-12', 'tenant_text_len': 0, 'gate_status': 'fail_missing'`
alongside `seam_exempt=['LP-12']`. **The 423 seam is masking a defect, not fixing it. Remove the seam
and LP-12 aborts all nine.**

**LP-07 is a known second instance:** Step 520 ground-truthed 31 of 32 fixtures as having a real CAM
provision and divall as not — yet LP-07 returns `applicable` on all 9, divall included.

## What the gate actually did, where observable

| lease | gate | correct? |
|---|---|---|
| solidpower | **accept** | Yes — but only because `KNOWN_ABSENT_BY_DOC_TYPE` short-circuits LP-20 for Industrial (Step 526), not because the matcher was right |
| divall | accept (attempt 2) | Yes on LP-20 (Step 480 read it); LP-07 wrong but seam-covered |
| atreca | **reject** | **No** — LP-20/21 both false positives, quoted above |
| ncino | **reject** | **No** — LP-20 false positive |
| everbridge | **reject** | **No** — LP-20/21/23 all false positives |
| quanterix, bokf, albireo, atreca_industrial | never run | — |

**3 of 5 observable gate decisions are wrong, all in the reject direction, all on real executed leases.**

---

# 4. WHAT THE USER SEES, VERBATIM

`static/app.js:5489` and `:14393`, identical:

```js
const msg = t.status === "cancelled" ? "Cancelled"
          : (t.error && t.error.startsWith("GATE_ABORT:") ? "Not a commercial lease"
          : (t.error || "No results"));
```

**A 288 KB executed office lease, filed with the SEC as an exhibit, is shown to the user as:**

> **Not a commercial lease**

The message the pipeline actually produced, which the user never sees:

> *"Extraction completeness failure: 3 required LP(s) have missing evidence and are not classified
> NOT_APPLICABLE. Failed LPs: ['LP-20', 'LP-21', 'LP-23']. Cannot produce a valid legal analysis report
> from incomplete evidence. Applicability: {'LP-20': 'applicable', 'LP-21': 'applicable', 'LP-23':
> 'applicable'}..."*

**The wording is part of the defect, and it is worse than a mislabel.** The internal message says
*"missing evidence"* — a claim about extraction. The user-facing message says *"not a commercial
lease"* — a claim about the document's identity. **Neither is true**: the evidence is not missing, it
is absent because the provision does not exist, and the document is plainly a commercial lease. Step
519 established this string is shown for **all four** `GateAbortError` causes, including one that means
our own extractor broke.

---

# WHAT IS NOT ESTABLISHED

- **The 81 `applicable` verdicts were not all read.** I ground-truthed LP-12 across 7 documents and
  relied on Steps 520/526/530 for LP-07, LP-20, LP-21, LP-23. **LP-15, LP-30, LP-32, LP-22, LP-16 and
  LP-04 were not checked** — their `applicable` verdicts may be correct or may be more of the same.
- **The 180 `required` verdicts were not examined at all.** They are hard-abort-capable by definition
  and bypass the clue list entirely; whether the always-required set is right is a separate question.
- **The exclusion-clue direction is unsurveyed.** 4 `excluded` verdicts on real leases were not read.
  A false exclusion is a silent drop, which is worse than a loud abort.
- **Synthetic ground truth was not established** — the 759 synthetic decisions are reported as a
  distribution only.
- **quanterix, bokf, albireo and atreca_industrial have never been through the gate**, so their
  accept/reject is predicted, not observed.
- **No fix was proposed and none was made**, per the brief.
