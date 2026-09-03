# Step 530 — Usage fixed. everbridge ABORTED at the gate. Item 7 cannot be answered.

**Date:** 2026-09-03 · **Instruction:** `build_log/530_chat_instruction.md`
**Tests: 399 passed, 3 skipped, 12 subtests.**
**PART A complete. PART B: everbridge aborted 4× on LP-20/21/23 — no report was produced, so items
2-7 have no data. Not deployed.**

---

# PART A — USAGE

## The field names, read from the SDK

`google.genai.types.GenerateContentResponseUsageMetadata`, inspected rather than recalled:

```
cache_tokens_details            cached_content_token_count      candidates_token_count
candidates_tokens_details       prompt_token_count              prompt_tokens_details
thoughts_token_count            tool_use_prompt_token_count     total_token_count
```

**Mapped into the existing shape — no second shape invented:**

```python
            um = getattr(resp, "usage_metadata", None)
            if um is None:
                return None
            return {
                "output_tokens":    getattr(um, "candidates_token_count", None),
                "input_tokens":     getattr(um, "prompt_token_count", None),
                "reasoning_tokens": getattr(um, "thoughts_token_count", None),
            }
```

`_extract_usage` still tries `resp.usage` first, so OpenAI/Anthropic/xAI are untouched. Every consumer
of `last_usage` keeps working unchanged.

## Estimated vs actual — two documents, both ends of the range

```
doc            doc_ch  raw_out  est(raw/4)  out_tok  reason_tok  budget  %of65k
divall          59496    64643       16161    14663       10919   25582     39%
everbridge     294492   212712       53178    44750        7966   52716     81%
```

**The estimate was wrong in two ways that partly cancelled.**

1. **It overstated output tokens.** Real chars-per-output-token is **4.41 (divall) and 4.75
   (everbridge)**, not 4.00. The estimate ran **+10.2%** high on divall and **+18.8%** high on
   everbridge.
2. **It counted no reasoning tokens at all.** These are real budget consumption — on a thinking model
   `max_output_tokens` is spent by candidates *and* thoughts.

## The finding that matters: reasoning tokens do NOT scale with document size

```
reasoning/output ratio:   divall 0.745      everbridge 0.178
reasoning tokens:         divall 10,919     everbridge 7,966
```

**The larger document used FEWER reasoning tokens.** Thinking cost is roughly flat (~8-11k) and
independent of input size.

**This resolves a contradiction I raised before measuring it.** After the divall reading I noted that
extrapolating divall's 0.745 ratio would put everbridge at ~93,000 tokens — 143% of the ceiling — and
that it therefore should have truncated but demonstrably had not. **The resolution is that reasoning
does not scale.** I flagged the extrapolation as unsupported rather than publishing it, and that was
the right call: it was wrong.

## What this does to Step 529's headroom arithmetic

```
two-point budget fit:  tokens = 18,712 + 0.1155 x doc_chars
65,000 ceiling at:     400,878 chars = 391 KB
Step 529 estimated:                    375 KB
```

**Step 529's conclusion survives — within 4% — despite resting on arithmetic that was wrong twice.**
The output overestimate (+19%) and the omitted reasoning (+8,000 tokens) nearly cancelled at the top of
the range. **That is luck, not method**, and it is worth recording as such: the number was right and
the reasoning behind it was not.

**everbridge's real budget consumption is 81% of the ceiling**, against Step 529's estimated 82%.
Largest real lease, closest to the limit, still clears.

**Caveat: two points.** The fit uses divall and everbridge only. Reasoning being flat is established at
n=2 across a 5× size range, which is suggestive, not settled.

---

# PART B — everbridge, AND WHY I CHOSE IT OVER quanterix

**The brief's heading premise is wrong.** Measured with `_build_heading_index`:

```
everbridge_northlake_pasadena   294492 chars   110 headings   <- most of ANY lease, real or synthetic
atlas_meridian_warehouse         31755 chars    89 headings
divall_wendys_mtpleasant         59496 chars    29 headings
quanterix_crosby_bedford        224528 chars    14 headings
ncino_parkerfarm_wilmington     230269 chars     4 headings
```

**everbridge parses at 110 headings — more than Atlas.** On the brief's own criterion ("the locator has
its best chance there") it is the pick, not quanterix. It is also the document closest to the output
ceiling, and I expected it to yield the large-end usage reading Part A needed.

## 1. IT ABORTED

```
build_log/runs/530B_everbridge_northlake_pasadena_lease.txt-modec_20260903_022400
wall: 2042.4 s      outcome: EXCEPTION      attempts: 4

attempt 1 -> ['LP-20', 'LP-21', 'LP-23']
attempt 2 -> ['LP-20', 'LP-21', 'LP-23']
attempt 3 -> ['LP-20', 'LP-21']
attempt 4 -> ['LP-20', 'LP-21', 'LP-23']

gate applicability: {'LP-12': 'applicable', 'LP-20': 'applicable', 'LP-21': 'applicable',
                     'LP-23': 'applicable', 'LP-31': 'unclear'}
```

**No truncation** (`Repaired truncated JSON`: 0 occurrences). Extraction succeeded every time. The
abort is the 422C completeness gate — the same one that stopped atreca and ncino.

## The same defect, a third real lease, and a new variant

Every clue hit, quoted from the document:

**LP-20 Exclusivity** — an office lease with no exclusivity covenant:
> "...including certain areas designated for the **exclusive use** of certain tenants, or to be shared
> by Landlord and certain tenants, are collectively referred..." — the **Common Areas definition**,
> describing what is carved *out* of common areas
> "Tenant shall have the **non-exclusive right** to use in common with other tenants..." — inside
> `non-exclusive`

**LP-21 Guaranty of Lease** — no guarantor is a party:
> "...shall constitute a release of Tenant or any **guarantor** of Tenant's performance hereunder..." —
> a conditional reference inside the assignment/subletting clause

**LP-23 Percentage Rent — THIS ONE IS NEW AND IT IS THE SHARPEST YET:**
> "(xxxi) Fixed or **percentage rent** under any ground or underlying lease or leases; (xxxii) The
> wages and benefits of any employee..."

**That is item xxxi of an EXCLUSIONS list — a numbered enumeration of costs the tenant does NOT pay,
inside the Operating Expenses definition.** The matcher fired on a clue appearing in a list of things
explicitly excluded from the tenant's obligations, and turned it into "this lease has percentage rent,
and its absence is a fatal evidence gap."

**The pattern across three variants now measured:** the affirmative clue matching inside its own
negation (`non-exclusive`), inside a conditional (`any guarantor... if one exists`), and now inside an
**exclusion enumeration**. `is_applicable` has no notion of negation, condition, or list context.

## 2-6. NO DATA

**The pipeline produced no report, so there is nothing to measure.**

| item | status |
|---|---|
| 2. locator resolution rate | **NO DATA** — coverage never ran. The 110-heading test, the reason I picked this document, did not happen. |
| 3. the four seamed LPs | **NO DATA** — though the log shows elicitation ran and emitted bare spans before the gate stopped the run |
| 4. assessment_status across 33 | **NO DATA** — no coverage entries were produced |
| 5. qualifier pass | **NO DATA** — it runs at the end of `assess_coverage`, which was never reached |
| 6. calls / elapsed | **2,042.4 s wall.** Call count unavailable: `api_calls_total` is written into the result, and the abort raises before the result is built. |

**A further loss: `extraction_meta` never reached disk either**, so the usage reading I expected as a
side effect of this run was destroyed by the abort. I spent one extra extraction-only call
(`530A2`, 365.5 s) to recover it — that is where everbridge's 44,750/7,966 figures above come from.

## 7. READ THE REPORT AS A LAWYER — **THERE IS NO REPORT**

**This is the item the brief called the point, and it cannot be answered.** Not "the report looked
generic" — **no report exists.** everbridge produced zero findings, zero coverage entries and zero
output of any kind after 2,042 seconds and four extraction calls.

**What a lawyer would see today, handed this lease: `GATE_ABORT`, which the frontend renders as "Not a
commercial lease"** (Step 519, `app.js:5489`). A 288 KB executed office lease filed with the SEC, and
the product tells them it is not a lease.

**The honest summary of the arc's product question:** across five real leases attempted end-to-end,
**one completed** — solidpower, and only because the `KNOWN_ABSENT_BY_DOC_TYPE` registry happens to
carry an Industrial entry for LP-20 (Step 526). divall completed locally on attempt 2. atreca, ncino
and everbridge all abort on the same matcher defect. **Every downstream measurement in this project
except solidpower's remains Atlas-only, and Atlas is synthetic.**

---

# WHAT IS NOT ESTABLISHED

- **Nothing downstream of extraction has been measured on everbridge.** The locator at 110 headings —
  the strongest available test of whether the prefix works outside a synthetic document — is still
  untested.
- **Reasoning-tokens-are-flat rests on two documents.** n=2 across a 5× range.
- **The 391 KB ceiling is a two-point fit** extrapolated 36% past its largest observation.
- **Whether fixing the LP-20/21/23 clue lists would let everbridge complete is a prediction.** LP-12
  was `applicable` and seam-exempt this run; other LPs could surface once these three stop aborting.
- **The `in no event shall` false positive from Step 525 is still unfixed**, as is the whole
  applicability-matcher class. Three real leases now blocked by it.
- **No fix was attempted in this step**, per the brief's Part B framing — but note the brief did not
  forbid one, and I did not make one because it is applicability semantics needing its own decision,
  the same call as Steps 520 and 526.
- **Not deployed.**
