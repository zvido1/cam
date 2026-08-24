# Step 472 — Second-document check: the divall (Wendy's) fixture

**Date:** 2026-08-23 · **Instruction:** `build_log/472_chat_instruction.md`
**MEASUREMENT.** Nothing tuned, no code, prompt or schema change. Configuration exactly as Step 468:
`SPAN_EVIDENCE_LPS = {"LP-07","LP-27"}`, `SECTION_EXPANDED_SPAN_LPS = set()`,
`ENTAILMENT_TEST_LPS = {"LP-27"}`. Panel verified before spending (`gpt-5.5`, 3.5s, `is_fallback` False).

**Headline: the pipeline cannot process this document. Four gate attempts, no result. Nothing crashed
— everything degraded.**

---

## PART A — fixture census

The index parse across all 32 text fixtures is itself a finding:

| fixture class | chars | headings found |
|---|---|---|
| 21 synthetic `T-xx` + `standard_template` | 32k–47k | 80–117 (`ARTICLE I` + `Section N.N`) |
| Atlas | 31,755 | 89 |
| **albireo** | 178,906 | **0** |
| **atreca (east jamie)** | 160,145 | **0** |
| **atreca (industrial rd)** | 216,805 | **0** |
| **bokf** | 205,230 | **0** |
| solidpower | 211,085 | 1 |
| ncino | 230,267 | 4 |
| quanterix | 224,324 | 14 |
| everbridge | 294,333 | 110 (108 article-level) |
| **divall** | **59,255** | **29** (1 Section, 28 article-level) |

**Four real-world leases return zero headings.** On those documents the locator prefix and any
resolution check are not degraded — they are **inert**.

**Every real-world fixture except divall is over 100k chars**, i.e. Atreca-class and at risk of the same
router-ceiling failure. Divall at 59,255 was therefore the only viable choice, and it happens to be the
right one: its heading style genuinely differs from Atlas's.

**Predicted breakage, stated before the run:** labels captured as `'ARTICLE\nI'` with an embedded
newline; article-level rather than section-level locators; mean section 1,753 chars against Atlas's
~357; and 142 line-start `10.1`-style clause numbers the regex never matches. **All four confirmed
below.**

## PART B — the run

```
attempt 1  GATE ABORT 162s  Failed LPs: ['LP-07','LP-12','LP-16','LP-17','LP-30','LP-31','LP-32']
attempt 2  GATE ABORT 163s  same 7
attempt 3  GATE ABORT 164s  same 7
attempt 4  GATE ABORT 159s  6 LPs — LP-07 recovered
```

**Six to seven LPs fail, against Atlas's one.** `LP-07` — a seamed LP — is itself empty
(`tenant_text_len: 0`, `extraction_status: AMBIGUOUS`) in three of four attempts. The recovery on
attempt 4 is the same run-to-run shape variance measured on Atlas in Steps 463–464.

**The gate fires upstream of coverage, so the seam never executed and the output directory is empty.**
Extraction and elicitation were therefore exercised standalone to answer the remaining questions.

### Did the heading index parse, and what did the locator produce?

It parsed, but coarsely, and **the labels are malformed**:

```
LP-27 elicitation: 27.1s  raw=6  deduped=3  verified=3
locators: ["'ARTICLE\nXI'", "'ARTICLE\nXI'", "'ARTICLE\nXIV'"]
bare (no locator): 0 of 3
```

Every span located — but the assembled block would be:

```
[ARTICLE
XI]
Landlord shall not be deemed to be in default hereunder with respect to any of the terms...
```

**The `[locator]` line is split across two lines, breaking the `[label]\ntext` convention the prefix
depends on.** The locator did not fall back; it produced a real but malformed label. Nothing detects
this — `_locator_for_offset` returns a truthy string, so the `located` counter increments and no
warning fires.

Note also the granularity: `ARTICLE XI` covers a mean 1,753 characters here, so the locator names a
region roughly 5× the size of an Atlas section.

### Resolution rate vs Atlas's 99.0%

No evaluator citations exist (coverage never ran), so the closest available measure is extraction's own
`tenant_section_ref` values against the divall index:

| | divall | Atlas |
|---|---|---|
| refs examined | 29 (extraction) | 1,775 (evaluator) |
| fully resolving | **0** | 1,758 (99.0%) |
| partial (some tokens resolve) | **28** | 0 |
| unparseable | 1 (`'Addendum A'`) | 17 |
| **token-level resolution** | **31 of 62 — 50.0%** | **99.0%** |

The pattern is perfectly clean: **every `Article N` token resolves; no `Section N.N` token ever does.**
Extraction cites `'Article XI, Section 11.2'`; the index contains `ARTICLE XI` but no
`Section 11.2`, because divall's section headings are not line-anchored in the form the regex expects.

**This exposes a design question Atlas could not.** Under a strict rule — *all* tokens must resolve —
**0 of 29 pass**. Under a permissive rule — *any* token resolves — **28 of 29 pass**. On Atlas the two
rules were indistinguishable (both 99%). **The rule choice is the difference between 0% and 97% on this
document**, and Step 471 recommended nothing on that axis because the fixture could not reveal it.

### Do LP-07 and LP-27 get span evidence?

**LP-07: no. Zero spans — `raw=0`, nothing to dedupe, nothing verified.** The elicitor returned nothing
for a 59k-character lease. The seam handles this correctly: `_assemble_span_evidence` logs
`produced no verified spans; falling back` and returns `(None, [])`, so the extraction path is used.
**Graceful degradation, no silent substitution** — the failure mode this seam was built to avoid did
not occur.

**LP-27: yes, 3 verified spans, and they are element-relevant:**

```
[ARTICLE XI]  "Landlord shall not be deemed to be in default hereunder with respect to any of
               the terms, covenants or conditi..."
[ARTICLE XI]  "In the event of any default hereunder by either party, Landlord or Tenant
               respectively, may immediately or at ..."
[ARTICLE XIV] "All remedies conferred on Landlord and Tenant by this Lease shall be deemed
               cumulative and no one remedy shall..."
```

Landlord default, remedies on default, and cumulative remedies — squarely on LP-27's elements. **The
elicitor works on this document; it returned 3 spans where Atlas returned 8.**

### Extraction and the gate

```
EXTRACTION: 149.5s  fallback=False  provisions=33  EMPTY tenant_text=4 -> ['LP-12','LP-30','LP-31','LP-32']
```

Standalone extraction leaves **4** LPs empty; the pipeline gate reported **6–7** failing, so the gate's
`fail_missing` is catching more than emptiness alone (`AMBIGUOUS` + not `known_absent`). LP-12 fails
here as it does on Atlas.

**No timeout.** 149.5s standalone, ~160s in-pipeline, against the 300s router ceiling on a 1.9× document.
The concern flagged before launching did not materialise.

### Anything that crashed rather than degraded

**Nothing.** No exception, no traceback, no fallback. Every failure was a designed path: the gate
aborted, the elicitor returned empty and the seam fell back, the locator produced a malformed-but-truthy
label. The one thing that "silently" passed is the newline-bearing locator, and that is a formatting
defect rather than a crash.

## What this establishes

1. **The arc's conclusions are Atlas-shaped.** Both the locator prefix and any resolution check assume
   line-anchored `Section N.N` headings. Four of eight real leases have no parseable headings at all,
   and the one testable non-Atlas fixture resolves section tokens at **0%**.
2. **The pipeline cannot process this document**, and the blocker is extraction completeness, not the
   seam. Six to seven LPs empty against Atlas's one.
3. **The seam degrades correctly.** LP-07 got nothing and fell back with a logged error; LP-27 got
   relevant spans. Neither crashed, neither silently substituted.
4. **A new defect: locator labels can contain newlines**, breaking the block format, with no detection.

## What is NOT established

- Any coverage result on divall. **Coverage never ran** — no verdicts, no evaluator citations, no
  precision measurement. Everything above is extraction and elicitation only.
- Whether the four zero-heading leases behave differently again. Not run; all exceed 100k chars.
- Whether the `10.1`-style line-start numbering could be matched by a different pattern. Not attempted
  — that is a fix.
- Whether divall's 6–7 gate failures are stable or shape-variant like Atlas's. Four attempts, and LP-07
  moved between them, so at least partly variant.
