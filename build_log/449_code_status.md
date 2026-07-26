# Step 449 — semantic-support-span resolution + degradation-reason classification — CODE STATUS

Audit only. No harness edit, no rerun, no push, no remediation. Rule 6 throughout.
**No §9.1 criterion is computed in this step.**

---

## TASK A — SEMANTIC SUPPORT SPAN, RESOLVED FROM CODE

### A.1 Corrected prefix search — `semantic_support_span` (prefix, not exact string)

Searched all three Step-447 outputs for any identifier beginning `semantic_support_span`:

| artifact | prefix matches | distinct identifiers |
|---|---|---|
| `431_selection_measurement_sidecar.json` (818,521 B) | **0** | none |
| `431_runtime_seam_capture.json` | **0** | none |
| `431_selection_measurement.md` | **0** | none |

**Zero occurrences of any identifier beginning `semantic_support_span` in any Step-447 output.** The
prefix search returns the same result as the exact-string search: neither `semantic_support_spans`
nor `semantic_support_span_ids` nor any other variant is present.

**Where the identifiers do occur — the preregistration only**
(`build_log/431_partB_measurement_instruction.md`), three occurrences, two distinct identifiers:

| line | identifier | context |
|---|---|---|
| 105 | `semantic_support_spans` | §4.5 field-grounding: *"Failed quote stays in audit trace, never enters `semantic_support_spans`."* |
| 178 | `semantic_support_span_ids` | §8.1 `certification_trace` required field |
| 231 | `semantic_support_spans` | §9.1 criterion #6 |

### A.2 Harness search — every construction/population/emission site

**No such site exists.** Search evidence:

```
$ git show d679eec:build_log/run_431_selection_measurement.py | grep -n "semantic_support_span"
(exit=1 ; no output = no match)
```

Extended to the other token-bound configuration artifacts at P4 — occurrence counts for the prefix:

```
431_output_schema.json        0
431_requirement_profiles.json 0
431_measurement_config.json   0
431_selector_prompt.txt       0
```

**The output schema does not elicit it.** Its top-level properties, in full:

```
candidate_span_id, context_envelope_id, parameter_family_relevance, candidate_support_state,
text_role, value_completeness, value_applies_to_charge_basis_components, other_basis_description,
charge_scope, other_scope_description, candidate_citations, context_citations, field_support,
reason, confidence
```

There is no span-collection property. **The selector prompt never names the concept** (0
occurrences), so no panelist was ever asked to produce one.

**The `certification_trace` emission code, verbatim** (`certify_parameter_series`, harness at P4) —
the fields actually written:

```python
        traces.append({
            "parameter": parameter, "lease": lease, "series_index": k,
            "per_candidate": per_candidate_out,
            "series_complete": not incomplete,
            "completeness_provenance": {"status": "not_established"},
            "prompt_hash": hashes["431_selector_prompt.txt"],
            "schema_hash": hashes["431_output_schema.json"],
            "requirement_profiles_hash": hashes["431_requirement_profiles.json"],
            "config_hash": config_hash,
            "final_certification_state": final_state,
        })
```

and the `per_candidate` record it writes:

```python
            per_candidate_out.append({
                "candidate_id": cs["candidate_id"],
                "raw_attempt_index": panel["raw_attempt_index"],
                "canonical_attempt_index": panel["canonical_attempt_index"],
                "series_index": panel["series_index"],
                "relevance_ok": comparison["relevance_ok"],
                "basis_match": comparison["basis_match"],
                "text_role_ok": comparison["text_role_ok"],
                "value_ok": comparison["value_ok"],
                "support_ok": comparison["support_ok"],
                "applicability_match": comparison["applicability_match"],
                "agreement_by_field": comparison["agreement_by_field"],
                "candidate_qualification": comparison["candidate_qualification"],
                "_comparison": comparison,
            })
```

**§8.1 specifies these trace fields** (lines 170–182, verbatim):

> ```
> certification_trace:
>   parameter, lease
>   series_index                       # 1..5 — this trace certifies ONE parameter-series
>   per_candidate: [ { candidate_id, raw_attempt_index, canonical_attempt_index, series_index,
>                      relevance_ok, basis_match, text_role_ok,
>                      value_ok, support_ok, applicability_match,
>                      agreement_by_field, field_support_citation_ids,
>                      candidate_qualification } ]
>   semantic_support_span_ids
>   completeness_provenance            # status: not_established (§9)
>   prompt_hash, schema_hash, requirement_profiles_hash, config_hash
>   final_certification_state
> ```

**Written vs specified — TWO §8.1 fields are absent from the emitted trace:**

| §8.1 field | emitted? |
|---|---|
| `semantic_support_span_ids` (trace top level) | **NOT WRITTEN** |
| `field_support_citation_ids` (inside `per_candidate`) | **NOT WRITTEN** |

(`series_complete` is written and is *not* in §8.1's list — an addition, not an omission. The
`field_support_citation_ids` omission is a **new finding of this step**, not previously recorded.)

### A.3 Which holds, from code

**(c) — never materialized by this harness.**

Basis, quoted above rather than inferred: the identifier prefix has **zero** occurrences in the
harness source; **zero** in the output schema, so the panel was never asked for it; **zero** in the
selector prompt, so the concept never reached a model; and the trace emission code contains no key
of that name. There is no construction site, no population site, and no emission site. Options (a)
and (b) both require a materialization event somewhere in the code; none exists.

**On whether §9.1 #3 is thereby vacuous rather than satisfied.** §9.1 #3 reads (line 228):

> - No property borrowed from a semantic-support span to cure a deficient primary.

This is a negative existential. Its domain — the set of materialized semantic-support spans — is
**empty**, established by (c) above. Any evaluation returning true would therefore be **vacuously
true: true because nothing of the quantified kind exists, not because a mechanism declined to borrow
from one.**

The basis for treating that as vacuity rather than substantive satisfaction is §8.2 line 195, which
couples the prohibition to a materialization requirement in a single criterion:

> - semantic-support-span behavior (materialized, not value-only; no borrowed property)

The same §8.2 criterion requires spans to be **materialized** *and* requires **no borrowed
property**. An empty domain satisfies the second conjunct only by failing the first. Crediting #3
as satisfied would report the absence of an unimplemented feature as evidence that the mechanism
governed correctly.

**Per this step's constraint, no verdict is recorded for #3.** The statement above is about the
criterion's domain, established from code; it is not a computation of the criterion over run data.

### A.4 Effect on the survey

| criterion | 448 survey | 449, corrected search | basis |
|---|---|---|---|
| **#6** — *"Certified parameters (if any) carry materialized `semantic_support_spans`, not value-only."* | ABSENT | **ABSENT — unchanged, and strengthened** | The prefix search confirms the exact-string result. Strengthened because the concept is additionally absent from the output schema and selector prompt: the data was not merely unrecorded at write time, it was never elicited or constructed. No re-search can recover it. |
| **#3** — *"No property borrowed from a semantic-support span to cure a deficient primary."* | PARTIAL | **PARTIAL is SUPERSEDED** | The 448 PARTIAL rested on an open question — whether `context_citations` is the recorded form of a semantic-support span. That question is now **closed from code, negatively**: the harness has no notion of a semantic-support span at all, so `context_citations` cannot be its recorded form under any code-supported reading. The residual uncertainty that produced PARTIAL is resolved. What remains is not missing data but an **empty domain** (A.3). I do not relabel #3 ABSENT, because "absent data" and "empty quantification domain" are different findings and the distinction is the point. |

**Correction to the 448 record:** the 448 survey reported #3 as PARTIAL on the strength of an
unresolved definitional question. That characterization was accurate as to what 448 had established,
but the question was resolvable from code and 448 did not resolve it. It is resolved here.

---

## TASK B — DEGRADATION-REASON CLASSIFICATION

**The classifier is not in `provider_router.py`.** It is in
`cam/adapters/lease_review/lease_coverage_305.py`. Search evidence at P4:

```
$ git grep -n "reasoning_exhaustion" d679eec -- cam/
d679eec:cam/adapters/lease_review/lease_coverage_305.py:164:    Mapping (per spec): empty content → reasoning_exhaustion for gpt-5.x; unclosed
d679eec:cam/adapters/lease_review/lease_coverage_305.py:176:        return "reasoning_exhaustion" if _is_split_model(model) else "empty_response"
d679eec:cam/adapters/lease_review/lease_coverage_305.py:180:        return "reasoning_exhaustion" if _is_split_model(model) else "malformed_response"
```

Verbatim, `lease_coverage_305.py` at P4:

```python
def _is_split_model(model: str) -> bool:
    """B-split gate: only gpt-5.x evaluators batch their prompt (Step 372c)."""
    return (model or "").lower().startswith("gpt-5")


def _classify_failure(error_msg: str, model: str) -> str:
    """Classify why a primary evaluator call failed (Step 372c observability).

    Mapping (per spec): empty content → reasoning_exhaustion for gpt-5.x; unclosed
    array → truncation; HTTP/timeout/rate → api_error. Recorded where the fallback
    fires so budget pressure is queryable from run metadata, not a future probe.
    """
    m = (error_msg or "").lower()
    if "degraded" in m or "already claimed" in m:
        return "provider_unavailable"
    if ("_error:" in m or "timeout" in m or "timed out" in m or "rate" in m
            or "429" in m or "connection" in m or "unauthorized" in m
            or "401" in m or " 500" in m or " 502" in m or " 503" in m):
        return "api_error"
    if "empty_content" in m or "empty content" in m:
        return "reasoning_exhaustion" if _is_split_model(model) else "empty_response"
```

### Settled from code: the two fields DO NOT disagree
The recorded error string was `empty_content: model returned no output`; the failing model was
`gpt-5.5`. Tracing the quoted code: `"empty_content" in m` is true → returns
`"reasoning_exhaustion" if _is_split_model("gpt-5.5") else "empty_response"`, and
`"gpt-5.5".lower().startswith("gpt-5")` evaluates to **True** → `reasoning_exhaustion`.

**`reasoning_exhaustion` IS the classification of an `empty_content` error for a gpt-5.x model.** The
two recorded values are the same event at two layers — raw error string and assigned class. The 448
observation that they are "not the same string" was correct and is now explained; there is no
inconsistency to record and no unreliable-pending-verification finding on this field.

### A precision limit that the code does establish, and which should not be over-read
The class name asserts a cause the classifier does not observe. `_classify_failure` receives only
`error_msg` and `model`; it inspects no token accounting. The label is assigned from
**model-family + empty output**, nothing more. Corroborating design text at P4,
`build_log/413_fallback_integrity_design.md:128`:

> | `reasoning_exhaustion` | Empty from gpt-5.x | GPT-5.x reasoning budget exceeded. …

The recorded `usage` on that role-call is `{"output_tokens": 590, "input_tokens": 3730,
"reasoning_tokens": 0}` — and those figures belong to the **successful gpt-5.4 replacement attempt**,
not the failed gpt-5.5 attempt; no usage was recorded for the failure.

**Therefore:** `fallback_reason: reasoning_exhaustion` is a faithful, correctly-applied *label* for
"gpt-5.x returned empty content." It is **not** an observation that a reasoning budget was
exhausted. Any downstream claim that the degradation was *caused by* reasoning-budget exhaustion is
**[UNVERIFIED — the classifier infers the name from model family and empty output; it measures no
reasoning budget]**.

---

## TASK C — CORRECTIONS TO THE RECORD

1. **The Step-447 and Step-448 statements of the cand_04 degradation cause are superseded by Task B.**
   Both reported `cause: reasoning_exhaustion`. That value is confirmed correctly recorded and
   correctly derived, so the supersession resolves in favour of the recorded value — **with the
   added bound** that the label denotes "gpt-5.x returned empty content", not an observed
   budget exhaustion. Wherever 447 or 448 reads as though a reasoning budget was measured, this
   status governs.

2. **Chat's 448 brief propagated the unverified `reasoning_exhaustion` cause, and Code correctly
   declined to assert it.** The 448 brief directed the disclosure wording *"cause
   reasoning_exhaustion"*. The 448 status recorded the value but flagged, without resolving, that
   *"the recorded `fallback_reason` is `reasoning_exhaustion`, while the underlying attempt error
   string is `empty_content: model returned no output`. Both are recorded; they are not the same
   string."* Declining to assert equivalence was correct; the equivalence is established here, from
   code.

3. **New finding this step, not previously recorded:** `field_support_citation_ids` — a §8.1-required
   `per_candidate` field — is also never written by `certify_parameter_series`. §8.1 therefore has
   **two** unwritten fields, not one. Recorded, not remediated.

4. **The 448 survey's PARTIAL on §9.1 #3 is superseded** by A.4. Recorded there.

---

## Scope compliance
No §9.1 criterion was computed. No verdict of satisfied, failed, or not-established was emitted on
any criterion. Partial computation remains unauthorized until Task A's resolution is ruled on.

## Git
`449_chat_instruction.md` written verbatim before execution (Rule 7). This status committed with
`git add -f`. **NOT pushed.** No harness edit, no rerun, no remediation.
