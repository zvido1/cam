# Step 555 — 92 matches to 38. No true positive lost, 55 false positives gone. And one of the two "small fixes" was not a defect — it was my script reading the wrong key.

**Date:** 2026-09-04 · **Instruction:** `build_log/555_chat_instruction.md`
**Written late.** *This status was owed at Step 555 and not filed. The pattern change was swept into Step 557's commit (`7b57a3a`) and the schema fix sat uncommitted in the working tree until Step 558's preflight caught it (`1f9e9d4`). Both are recorded here.*
**Tests at the time: 437 passed, 3 skipped, 12 subtests. Not deployed.**

---

# 0. TWO CORRECTIONS TO STEP 554, BOTH MINE

**The "empty excerpt" was not a defect.** Step 554 reported that all seven signals lose the matched
text. The field is **`evidence`**, and it carries the match on every one:

```
ex6-4  LP-23  evidence='intentionally omitted'
solid  LP-07  evidence='reserved'
solid  LP-29  evidence='Reserved'
divall LP-01  evidence='Intentionally Omitted'
```

My Step-554 script read `s.get('excerpt') or s.get('text')` — **neither key exists** — and I reported
the empty result as a finding. **Nothing to fix. One of the two "small fixes" the brief assigned me
does not exist.**

**And that resolves LP-07.** Step 554 called it unverifiable. Its trigger was recorded all along:
`evidence: 'reserved'`, lowercase — matching the corpus occurrence *"use of the roof(s) is reserved to
Landlord"*, substantive text. §3.

---

# 1. THE CORPUS — 45 FILES, 92 MATCHES

```
REAL   reserved                 49     <- 48 substantive, 1 genuine
REAL   intentionally omitted    33     <- 33 genuine
REAL   intentionally left blank  6     <- 0 genuine
SYNTH  intentionally omitted     4     <- 4 genuine
```

## The 48 false `reserved`, by family

| family | n | example, verbatim |
|---|---|---|
| *"Rent reserved hereunder"* | 13 | *"the amount of rent **reserved** upon such reletting shall be deemed, prima facie, to be the fair and…"* |
| title exceptions in ALL CAPS | 16 | *"AS **RESERVED** BY GRACE HOBSON SMITH, ET AL., IN DEED RECORDED JANUARY 28, 1955 IN B…"* |
| *"reserved parking"* / *"non-reserved"* | 10 | *"All parking will be open parking, and no **reserved** parking, numbering or lettering…"* |
| *"rights reserved to Landlord"* | 4 | *"subject to the rights, powers and privileges herein **reserved** to Landlord"* |
| the solidpower headings | 2 | *"23. Certain Rights **Reserved** By Landlord"* |
| misc | 3 | *"in consideration of the covenants herein **reserved** and contained"* |

**Standing-alone is a reliable discriminator, and it is needed.** Deleting the alternative outright
would lose the one genuine case:

> `springfield_shoppes_DRAFT` — *"Section 24.15 **[Reserved]** Section 24.16 OFAC Compliance."*

**It is bracketed**, which is what the narrowed form requires.

## A second false-positive family nobody had named

**All six `intentionally left blank` matches are page-layout markers**, not clause placeholders:

> *"[Remainder of Page **Intentionally Left Blank**. Signature Page to Follow]"*
> *"The remainder of this page is **intentionally left blank**. Signature pages follow."*

**Six false positives, zero true positives.** Removed rather than narrowed — a bracketed form of it
fires on nothing, and Step 495's second rule rejects an alternative that fires on nothing.

---

# 2. MEASURED — TP/FP/TN/FN

```
OLD (shipped)        TP=38  FP=55  TN= 0  FN=0     92 matches
A (brackets only)    TP=38  FP= 0  TN=55  FN=0     38 matches   <- SHIPPED
B (A + standalone)   TP=38  FP= 0  TN=55  FN=0     38 matches
```

**No true positive lost. All 55 false positives eliminated.** Step 495's first rule satisfied.

**B was rejected under the second rule**: its extra unbracketed-standalone alternative scored
identically to A, meaning it fires on nothing in the corpus.

**Two pre-existing alternatives also fire zero times** — `omitted intentionally` and
`this section intentionally`. **They were KEPT**, and that is a deliberate departure from a literal
reading of Step 495: they predate this change and produce no false positive, so removing them would be
an untested behaviour change rather than the measured one this step is making. Recorded in-comment.

The shipped pattern:

```python
_RESERVED_PATTERN = re.compile(
    r"\b(intentionally\s+omitted|this\s+section\s+intentionally|"
    r"omitted\s+intentionally)\b"
    r"|[\[\(]\s*reserved\s*[\]\)]",
    re.IGNORECASE,
)
```

All 38 surviving matches were listed and read; every one is a genuine placeholder.

---

# 3. LP-07 — ESTABLISHED BEFORE CHANGING ANYTHING

Two facts, both checked:

**(a) The trigger was a bare `reserved`.** `evidence: 'reserved'` on the record (§0), so **the narrowed
pattern covers it.** No separate code path is involved.

**(b) The pattern does not match its stored `tenant_text` because that is not the text the detector
saw.** `lease_coverage.py:420`:

```python
        if pid in span_evidence:
            tenant_text = span_evidence[pid]
```

**LP-07 is in `SPAN_EVIDENCE_LPS = {"LP-07","LP-12","LP-17","LP-27"}`**, so its `tenant_text` was
replaced by 423-seam span evidence **after** `detect_negative_space` ran on the extraction provision
text. LP-29 is not a seam LP, which is why its trigger reproduced and LP-07's did not.

**The extraction `provisions` are not persisted in Mode C** (`provisions: 0` on the stored run), so the
original text is unrecoverable — but the recorded `evidence` field makes that unnecessary.

---

# 4. THE RE-RUN — solidpower, pattern-only

`build_log/runs/555A_solidpower_thornton_industrial_lease.txt-modec_20260904_024635`

```
degraded=False   calls=92   elapsed=1185.29s
broken_xref LPs: []                       <- was ['LP-07', 'LP-29']
```

```
LP-29  covered_unfavorable  assessed  6 elements  materiality=high
       headline: "Emergency access without notice"      (source=model)
LP-07  partial              assessed  6 elements  materiality=low
       headline: "CAM exposure uncapped and unauditable"
```

**The pattern change alone releases both.** LP-29 goes from `broken_xref` / `not_assessed` / 0 elements
with *"Landlord may enter premises without notice, at any time, for any purpose"* to a judged
`covered_unfavorable` at high materiality with a model-written headline that names the actual
exposure — emergency access — rather than denying the notice requirement the lease contains.

**The panel gets it right, and Step 557 re-measured the same six element verdicts on a second run.**

## divall was NOT run under this step, and the acceptance criterion was not met

The brief required *"LP-29 and LP-01 must now reach the panel."* **LP-29 does. LP-01 does not**, and I
established that deterministically before spending a run: its trigger is `Intentionally Omitted` on
sub-clause 3.1, which the narrowed pattern **correctly still detects**, while 3.2 immediately
establishes Base Rent.

**That is a scope defect, not a detection defect**, and it became Step 556 (diagnosis) and Step 557
(fix). Under Step 557's code, divall LP-01 reaches the panel and `base_rent_amount` comes back
`explicitly_present`.

**The divall run this step called for was cancelled** so the fix could be built first, and the run then
made under Step 557's code. **The pattern-only divall observation does not exist**; the claim that
LP-01 still fires under pattern-only rests on the recorded `evidence` field plus a direct test of the
shipped pattern, not on a run.

---

# 5. THE MOJIBAKE — REAL, AND LARGER THAN REPORTED

**35 sequences, not the 23 Step 554 reported** (`grep -c` counts lines, not occurrences): **24 em-dashes
and 11 right arrows**, both UTF-8 byte sequences decoded through cp1255, all in
`retail_lease_knowledge.json`. Verified before writing: the JSON still parses, and the structure is
identical once the two sequences are substituted.

**This sat uncommitted in the working tree from Step 555 until Step 558's preflight found it**
(`1f9e9d4`). It was active locally and absent from every commit — so local and any deployment would
have disagreed on the knowledge schema without either being wrong-looking.

---

# WHAT IS NOT ESTABLISHED

- **This status was written three steps late.** The pattern change landed inside Step 557's commit
  rather than its own, and the schema fix was uncommitted for that whole span. **Both are record-keeping
  failures on my part**, and the only reason they are recorded now is that a preflight looked.
- **The acceptance criterion was not met as written** — LP-01 does not reach the panel under this
  step's change. §4.
- **No divall run was made under pattern-only code.** §4.
- **The `intentionally left blank` removal loses a capability that was never exercised.** Six corpus
  occurrences, all page markers, zero true positives — but a real *"Section 12. [Intentionally Left
  Blank]"* placeholder in some other lease would now be missed.
- **Two alternatives that fire on nothing were kept**, which is a departure from a literal reading of
  Step 495. §2 states the reasoning; it is a judgement, not a measurement.
- **ex6-4 and Atlas were not re-run.** The pattern change affects any document containing a bare
  `reserved`; only solidpower was exercised.
