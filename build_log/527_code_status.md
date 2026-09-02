# Step 527 — The repair is real and traceless. But it did not cause the atreca/ncino aborts.

**Date:** 2026-09-02 · **Instruction:** `build_log/527_chat_instruction.md`
**DIAGNOSTIC ONLY. Nothing changed, no provider calls, not deployed.**

---

# 0. THE FUNCTION NAMED IN THE BRIEF IS NOT THE ONE THAT REPAIRS

> *"safe_json_extract rebalanced brackets on a truncated response"*

**`safe_json_extract` does not rebalance anything.** Its bracket walker,
`_find_balanced_json` (`cam/core/json_extract.py`), returns a slice **only** when depth returns to
zero:

```python
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start_pos:i+1]

    return None
```

On truncated input depth never closes and it returns `None`. No repair.

**The rebalancer is `_repair_truncated_json` in `cam/adapters/lease_review/lease_extract.py:200`** — a
different function in a different module. The substance of the brief is right; the attribution is not.

There is also a *second* mechanism in `safe_json_extract` that turns a truncated response into a
shorter valid object without repairing brackets: `_collect_provision_objects` gathers whichever inner
objects happened to close and wraps them in a synthetic
`{"evaluations": [...], "discovered_clauses": []}`. It is not on the extraction path — extraction calls
`_extract_provisions_json` first — but it is the same defect class one module over.

---

# 1. THE REPAIR, QUOTED — AND IT LEAVES NO TRACE

`lease_extract.py:200-243`:

```python
def _repair_truncated_json(fragment: str) -> Optional[dict]:
    """Attempt to repair truncated JSON by closing open structures.

    When the model hits max_output_tokens, the JSON is cut off mid-provision.
    We try to close open strings and brackets to salvage completed provisions.
    """
    ...
        elif c == "}":
            depth -= 1
            if depth == 1:
                # We just closed a provision object (depth returns to 1 = inside array)
                last_complete = i
    ...
    truncated = fragment[: last_complete + 1] + "\n  ]\n}"
    try:
        obj = json.loads(truncated)
        if isinstance(obj, dict) and "provisions" in obj and isinstance(obj["provisions"], list):
            print(f"[lease_extract] Repaired truncated JSON: {len(obj['provisions'])} provisions recovered", flush=True)
            return obj
```

**Conditions for repair:** the balanced-parse path fails, the text contains `"provisions"`, and at
least one provision object closed (`depth` returned to 1). It then discards everything after the last
complete provision and synthesises `]` `}`.

**Does it record that it repaired? Only to stdout.** It `print`s a line and **returns a bare `dict`,
structurally identical to a complete parse.** The caller takes it verbatim:

```python
            repaired = _repair_truncated_json(fragment)
            if repaired:
                return repaired
```

No flag, no wrapper, no metadata. And the persisted record confirms it — `extraction_meta` on every
saved run carries only:

```
['canonical', 'elapsed_sec', 'errors', 'extraction_attempt_chain',
 'fallback_used', 'model', 'primary_model', 'primary_provider', 'provider', 'single_doc']
```

**No `repaired`, no `truncated`, no `finish_reason`, no token usage.** The brief's characterisation is
exactly right: *a repair that leaves no trace is indistinguishable from no repair having been needed.*

## And the signal is discarded twice more, upstream

`cam/core/provider_router.py:650-656`:

```python
            finish_reason = getattr(cand[0], "finish_reason", None)
            if finish_reason:
                finish_str = str(finish_reason)
                # MAX_TOKENS means response was truncated but still has content
                if "MAX_TOKENS" in finish_str:
                    # Continue to extract - truncated content is still valid
                    pass
```

**The adapter detects `MAX_TOKENS`, writes a comment saying the response was truncated, and executes
`pass`.** It is not that the information is unavailable — it is read, named, and dropped.

And `self.last_usage = _extract_usage(resp)` is populated on every Google call, but
`grep -rn "last_usage" cam/adapters/lease_review/` returns **one** consumer —
`lease_coverage_305.py:497`. **`lease_extract` never reads it**, so the extraction call's token usage
is never recorded anywhere.

**Three independent points where truncation is knowable, and it is dropped at all three.**

---

# 2. WAS THE RESPONSE TRUNCATED? UNKNOWABLE FOR THOSE RUNS — AND THAT IS PART OF THE ANSWER

**`max_output_tokens` for single-call extraction is `EXTRACTION_MAX_TOKENS_SINGLE = 65_000`**
(`lease_extract.py:376`), passed at `:820`. The chunked path uses `24_000`.

**`finish_reason`: not recorded.** Read at `provider_router.py:650`, matched against `MAX_TOKENS`, and
discarded. It reaches no result field and no log line.

**Token usage: not recorded** for extraction, per above.

**The one available trace is the `print` — and for the Step-526 runs I destroyed it myself.** I piped
`run_mode_c.py` through `tail -20` / `tail -25`, so the background task files hold only 2.0-3.3 KB of
tail output. Grepping all four for `Repaired truncated JSON` returns **0 lines in each**, but that is
**not evidence of absence** — the lines, if any, were discarded before the file was written. **That is
my error, and it is the difference between "no repair occurred" and "I cannot tell."**

---

# 3. WHAT A 33-LP EXTRACTION COSTS — MEASURED

Estimated from the persisted results: sum of `tenant_text` across all coverage entries, ÷4 chars/token,
×1.35 for JSON scaffolding.

| document | doc chars | LPs filled | Σ tenant_text | est. output tokens | % of 65,000 |
|---|---|---|---|---|---|
| atlas | 31,755 | 30 | 28,722 | ~9,694 | **15%** |
| divall | 59,496 | 27 | 47,687 | ~16,094 | **25%** |
| **solidpower** | **211,735** | **27** | **117,380** | **~39,616** | **61%** |

**This is a LOWER bound** — it excludes `provision_id`, `status`, `section_ref`, `alignment_notes` and
the template fields the extraction JSON also carries.

**solidpower ran at ~61% of the ceiling and completed.** Extrapolating its rate (0.187 tokens/char):
atreca ~30,000 (46%), ncino ~43,000 (66%), everbridge ~55,000 (85%). **None of them should hit 65,000
on this estimate** — though everbridge at 85% of a lower-bound estimate is close enough that it is not
safe to call.

**So the answer to "would the same limit that fits Atlas truncate solidpower" is no — it did not,
measured.** Atlas uses 15% of a budget solidpower uses 61% of, and both fit.

---

# 4. DID ATLAS OR DIVALL EVER SILENTLY TRUNCATE? — AND THE SHAPE TEST THAT ANSWERS THE REAL QUESTION

**Cannot be determined from the persisted runs.** `extraction_meta` has no repair field, and no
historical stdout is retained. **The repair leaves no trace, so the archive cannot be interrogated.**

**But the atreca/ncino aborts can be tested a different way, and the test says truncation did not cause
them.**

**Truncation cuts a suffix.** `_repair_truncated_json` keeps provisions up to `last_complete` and drops
everything after, so a truncated extraction leaves the *tail* of the emission order empty — a
contiguous run of high-numbered LPs.

What the runs actually show:

```
solidpower (COMPLETED, 5 empty)   LP-04, LP-20, LP-21, LP-23, LP-31
                                  positions 4, 20, 21, 23, 31 of 32
                                  LP-32 -- the LAST provision -- IS populated

atreca  (aborted)   empty: LP-20, LP-21 (must_abort) + LP-23, LP-31 (degradable)
ncino   (aborted)   empty: LP-20 (must_abort) + LP-21, LP-23, LP-31 (degradable)
```

**Scattered, not a suffix.** And the same four LPs recur across all three documents:

```
LP-20  Exclusivity        LP-21  Guaranty of Lease
LP-23  Percentage Rent    LP-31  Co-Tenancy
```

**All four are retail-specific provisions.** atreca is a South San Francisco lab lease, ncino a
Wilmington office lease, solidpower a Colorado industrial lease. None is retail. **An empty bucket for
Exclusivity in an office lease is a correct extraction, not a lost one** — and Step 526 quoted the
proof for LP-20: every clue hit in both documents is inside `non-exclusive`, describing common-area
access.

**A truncation hypothesis has to explain why the cut lands on exactly the retail provisions in three
different documents, and skips LP-32 in the one that completed. It cannot.** The empty set is semantic,
not positional.

**Conclusion: the repair mechanism is real, unguarded and untraceable — and it is not what aborted
atreca and ncino.** Step 526's finding stands: the applicability matcher fires on `non-exclusive`, and
the gate turns a correct absence into a hard abort.

## What would have to change to find out

Four changes, none of them made here:

1. **Return a flag, not a bare dict.** `_repair_truncated_json` should return
   `(obj, {"repaired": True, "provisions_recovered": n, "bytes_discarded": len(fragment) - last_complete})`,
   and `_extract_provisions_json` should carry it onto `extraction["meta"]`.
2. **Stop discarding `finish_reason`.** `provider_router.py:653` already knows; the `pass` should set a
   field on the target or the adapter that `lease_extract` reads.
3. **Plumb `last_usage` into `extraction_meta`** — the adapter already populates it and extraction
   never looks.
4. **Persist full run stdout.** The harness writes `index.json`, the result and the census; it does not
   keep the log. Had it, this question would be answered rather than argued.

**Given (1)-(3), a single boolean on the result would settle in future what this step had to
reconstruct from the shape of the empty set.**

---

# WHAT IS NOT ESTABLISHED

- **Whether truncation has EVER fired on any run.** The shape test says it did not cause the Step-526
  aborts; it does not establish that the repair has never run. No archive can answer that.
- **Whether the Step-526 logs contained a repair line.** They were truncated by my own `tail` before
  capture. Absence of the string in those files is not evidence.
- **The token estimates are a lower bound and are inferred**, not read from `usage`. No run records
  actual output tokens for extraction.
- **everbridge at ~85% of the ceiling is untested** and is the document most likely to truncate. It has
  never been run.
- **`_collect_provision_objects` in `safe_json_extract` was read but not exercised.** Whether it can be
  reached on the extraction path was not tested — `_extract_provisions_json` returns first in every
  path I traced, but I did not prove it cannot fall through.
- **Nothing was changed.**
