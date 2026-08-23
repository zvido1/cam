# Finding: span evidence is uncitable, and the citation gate converts that into `unclear`

**Date:** 2026-08-22
**Status:** MEASURED. Diagnostic only. The seam (`lease_coverage.py`) remains uncommitted.
**Method:** two completed full 33-LP Atlas Mode C runs with `SPAN_EVIDENCE_LPS = {"LP-07", "LP-27"}`,
compared against four completed runs where LP-27 took the extraction path.
Artifacts: `seam2lp_r4/`, `seam2lp_r5/` (span path); `rerun_out/`, `seam_out/`, `seam_out_r2/`,
`seam_out_r3/` (LP-27 on the extraction path).

---

## 1. Why LP-27 was the LP routed through the seam

LP-22 and LP-27 were the two candidates. LP-27 was chosen because its evidence is genuinely
scattered while its extraction bucket is not: the pipeline's own compound-risk output places tenant
remedies across Sections 5.1, 6.3 and 13.3, while LP-27's `tenant_text` bucket contains only
Section 5.1 — and opens on the wrong subject entirely:

```
Section 5.1. Security Deposit. Tenant shall deposit with Landlord the Security Deposit upon
execution of this Lease as security for the faithful performance of Tenant's obligations
hereunder...
```

LP-22's material, by contrast, is concentrated in Article 19 (Sections 19.1–19.3), which its bucket
already contains — so its churn was less likely to be evidence-side.

## 2. The measurement

LP-27, per element. `b1`–`b4` = extraction path (`tenant_text` = 1272 chars, byte-identical every
run); `s4`/`s5` = span path (877 and 929 chars).

| element | b1 | b2 | b3 | b4 | s4 | s5 |
|---|---|---|---|---|---|---|
| Landlord default is defined | EXP | EXP | EXP | EXP | **UNC** | **UNC** |
| Tenant must give written notice of default | EXP | EXP | EXP | EXP | **UNC** | **UNC** |
| Cure period specified | EXP | EXP | EXP | EXP | **UNC** | **UNC** |
| Perform and offset against rent | – | MIS | MIS | MIS | MIS | MIS |
| Right to terminate on uncured default | EXP | EXP | EXP | EXP | **UNC** | **UNC** |
| Right to monetary damages | EXP | IMP | IMP | IMP | **UNC** | **UNC** |
| Specific performance / injunction | IMP | IMP | – | IMP | **UNC** | **UNC** |
| Lender notice and cure period | MIS | MIS | MIS | MIS | MIS | MIS |
| Common law remedies preserved | EXP | EXP | EXP | EXP | **UNC** | **UNC** |
| Remedies cumulative | IMP | IMP | IMP | IMP | **UNC** | **UNC** |

LP-level: `partial` / materiality `high` / confidence `high` on all four extraction-path runs →
**`review_needed` / `high` / `low`** on both span-path runs.

**The noisy LP settled.** `s4` and `s5` are identical on all ten elements, and neither LP-07 nor
LP-27 appears in the `r4`-vs-`r5` moved set (8 of 32 LPs moved, inside the established 7–9 noise
floor). It settled by collapsing.

## 3. Mechanism — the evaluators did not disagree about the lease

On "Landlord default is defined", two of three evaluators returned `explicitly_present`:

- **A (claude-sonnet-4-6):** "The lease explicitly defines landlord default as failure to perform any
  material obligation under the Lease, which directly satisfies the element. The quote is drawn from
  the LP text itself, though no section number is provided."
- **C (grok-4.3):** "The text directly defines landlord default by failure to perform material
  obligations."
- **B (gemini-2.5-pro, fallback):** "...as no section reference is available in the provided text, a
  verdict of 'unclear' is required per instruction rule #5, which mandates a section reference for
  any presence verdict."

All three returned `section_ref = None`. **Across LP-27's span-path runs, 0 of 30 evaluator citations
carried a `section_ref`**, against 23–25 of 30 on the extraction path.

The verdict was then produced by code, not by the panel — `lease_coverage_305.py:991`:

```python
# Citation-or-it-didn't-happen check (architecture spec §6)
if majority_verdict in PRESENCE_VERDICTS:
    valid_citations = [
        c for c in majority_citations
        if c and c.get("section_ref")
    ]
    if not valid_citations:
        return {
            "verdict": "unclear",
            "confidence": "low",
            "citation": None,
            "reason": "citation_required_but_absent",
            ...
        }
```

matching the prompt rule at `lease_coverage_305.py:243`:

> `5. Any presence verdict (explicitly_present, implicitly_present, covered_by_default_law, covered_in_other_LP) requires section_ref in the citation. If section_ref is null, use unclear instead.`

Confirmed in the run data by the `reason` field on merged element verdicts:

```
seam_out_r3 (extraction path)  {None: 10}
seam2lp_r4  (span path)        {'citation_required_but_absent': 8, None: 2}
seam2lp_r5  (span path)        {'citation_required_but_absent': 7, 'no_consensus': 1, None: 2}
```

## 4. Cause: the assembler emits clause bodies with no locator

The seam joins verified span texts and nothing else. For LP-27 those are fragments:

```
[1] if Landlord fails to perform any material obligation under this Lease
[2] such failure continues uncured for thirty (30) days after written notice from Tenant
    specifying the nature of such failure
[3] written notice from Tenant specifying the nature of such failure
```

The extraction bucket is the *wrong clause but citable*; the spans are the *right clauses but
uncitable*. The gate rewards the former.

## 5. LP-07 survives only because two evaluators fabricate a locator

LP-07 is stable across all five span-path runs to date: `partial`, materiality `low`, confidence
`high`, 5 spans, 5 found / 1 missing (`Annual CAM increase cap` the sole miss), `22.4` present.
**Including both two-LP runs — so LP-07 does not destabilise when a second LP joins the span path.**

But it clears the same gate only on manufactured locators. `section_ref` on the Proportionate Share
element, all five runs:

| run | A | B | C |
|---|---|---|---|
| seam_out | `None` | `'LP-07 CAM provision, paragraph 1'` | `'"Proportionate Share" shall mean'` |
| seam_out_r2 | `None` | `'LP-07 CAM Provision, paragraph 1'` | `None` |
| seam_out_r3 | `None` | `'Proportionate Share paragraph'` | `None` |
| seam2lp_r4 | `None` | `'Paragraph 1'` | `'Proportionate Share definition'` |
| seam2lp_r5 | `None` | `'Para. 1'` | `None` |

Not one is a real section number. **LP-07 passes because its evaluators paraphrase a locator; LP-27
fails because its evaluators decline to.** The gate cannot tell these apart, so on the span path it
is currently selecting for fabrication.

## 6. Confound, and its bound

The OpenAI account exhausted its credits during this session:

```
openai_error: RateLimitError: Error code: 429 - 'You have no credits remaining...'
code: 'credit_balance_exhausted'
```

Evaluator B therefore ran as fallback `gemini-2.5-pro` in both span runs, where all four
extraction-path baselines ran B as `gpt-5.5`.

**This did not cause the LP-27 collapse.** The majority was A + C, both `explicitly_present`, and
`valid_citations` was empty from their citations alone — B's abstention is not load-bearing on that
code path. **What is not excluded** is that a live `gpt-5.5` in seat B would have manufactured a
locator as it did for LP-07 in the baselines, carrying elements through the gate on a fabricated
citation. Unmeasured, and unmeasurable until credits are restored.

## 7. Gate abort rate

10 aborts / 12 attempts this session (`Extraction completeness failure: 1 required LP(s) have
missing evidence and are not classi...`), against a prior standing figure of 6 aborts across 13
observations. **Which LP tripped it is not recoverable from these logs** — the harness truncated the
exception at 90 characters. LP-12 is the historical intermittent aborter; that is *not* asserted for
these runs. This blocker is independent of the OpenAI credit state and will dominate the cost of any
clean rerun.

## What is NOT established

- Whether prepending a deterministic locator restores LP-27's presence verdicts. Not run.
- Whether LP-07's result survives once its evaluators are handed a real locator instead of inventing
  one. Not run.
- Whether the two-run identity holds at three runs. The third replicate aborted 4/4, twice.
- Precision of the span sets. Only stability and citability were measured here.
