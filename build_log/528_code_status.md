# Step 528 — Truncation is now observable. solidpower did not truncate, and now the record says so.

**Date:** 2026-09-02 · **Instruction:** `build_log/528_chat_instruction.md`
**Tests: 399 passed, 3 skipped, 12 subtests — 10 new.**
**solidpower re-run: COMPLETED, `parse_repaired: False`, `parse_path: fast_path_whole_text`. Not deployed.**

---

# 0. THREE PREMISES CORRECTED — ONE OF THEM CHANGES WHAT ITEM 5 CAN SHOW

**"`_repair_truncated_json` computes `repaired` at line 275 and discards it."** Line 275 is inside a
brace-walking loop in `_extract_provisions_json`. The `repaired` variable is at ~line 326 and it **is
returned**:

```python
            repaired = _repair_truncated_json(fragment)
            if repaired:
                return repaired
```

What was discarded is **the fact of repair**, not the variable. The defect is real; the location is not.

**"producing 5 of 33 provisions with a passing gate."** Inverted. solidpower produced **27 filled and 5
empty of 32**, gate passed on attempt 1, `extraction_completeness_failed: False`. Step 527's shape test
showed the 5 empties are LP-04/20/21/23/31 — retail provisions absent from an industrial lease — not a
truncation tail.

**"8,192 is the model ceiling and cannot be raised."** The ceiling in this codebase is
`EXTRACTION_MAX_TOKENS_SINGLE = 65_000` (`lease_extract.py:376`). solidpower's response measured
**138,641 characters ≈ 34.7k tokens**, about 53% of it. I raised nothing.

**Consequence for item 5:** this step is pure observability. **It cannot make solidpower fail** unless
solidpower actually truncated — and it did not. The prediction "it should now FAIL VISIBLY" rests on
the inverted premise. What the run does deliver is the answer to Step 527's open question.

---

# 1. THE CONTRACT

`safe_json_extract` has **107 call sites**. Changing its signature is not a no-architectural-change
edit, so it keeps it:

```python
def safe_json_extract(text: str) -> Dict[str, Any]:
    obj, _meta = safe_json_extract_with_meta(text)
    return obj
```

**New: `safe_json_extract_with_meta(text) -> (obj, meta)`**, meta being
`{"repaired": bool, "path": str, "repair_kinds": [...]}`.

**Why a pair and not a flag inside the payload.** Per Step 511 — never return a bare success for
something partially done. The object alone *is* a bare success. A key inside the returned dict would
pollute the parsed payload with our own bookkeeping, and a caller that forwards the dict would forward
the flag as if the model had produced it. **The pair separates the parse from the account of the
parse.**

`repaired` is True whenever the object is **not a straight parse of what the model produced** — the
text was mutated (LaTeX escapes rewritten) or the structure was invented (a wrapper assembled from
loose objects, or an array closed by us).

**Stated rather than hidden:** the bare wrapper remains, and a caller using it still cannot tell a
clean parse from a salvage. The extraction path was migrated; the other ~100 call sites were not. Its
docstring says so.

---

# 2. finish_reason AND USAGE — AND THE PART I GOT WRONG FIRST

`provider_router.py` previously read the signal and dropped it:

```python
                if "MAX_TOKENS" in finish_str:
                    # Continue to extract - truncated content is still valid
                    pass
```

Now `self.last_finish_reason = finish_str`, with `BaseAdapter.last_finish_reason` declared and **reset
at the top of every `call()`** so a stale MAX_TOKENS cannot read as truncation on the next request.

## The real run proved my first attempt insufficient

**The live solidpower run recorded `extraction_finish_reason: None`.** Not because nothing truncated —
because I had wired the capture into the **non-streaming fallback only**. The Google adapter's primary
path is `generate_content_stream` (`:561`), with a comment saying exactly why:

> *"Use streaming to work around MAX_TOKENS bug in Google GenAI SDK — When finish_reason is MAX_TOKENS,
> non-streaming responses can have empty content"*

**So on every real call, `finish_reason` was never recorded — and a `None` meaning "not recorded" is
indistinguishable from a `None` meaning "not truncated". That is precisely the ambiguity this step
exists to remove, reintroduced one layer down.** Found by running it, not by reading it.

Fixed: the stream path now reads `finish_reason` and `usage_metadata` off the last chunk, inside a
`try/except` so telemetry can never break a successful call.

**NOT ESTABLISHED: the streaming fix has not been exercised against a live provider.** It is covered by
a unit test on a stream-shaped chunk, and the next real run will be its first true test.

---

# 3. A REPAIRED EXTRACTION MARKS THE RUN — EXISTING PATH, NO NEW SURFACE

`lease_adapter.py`, extending the Step 476-478 machinery:

```python
    _parse_repaired_c = bool(extraction["meta"].get("parse_repaired"))
    _run_degraded_c = (
        bool(_fallback_events_c) or _run_config_degraded_c or bool(_completeness_failed_ids)
        or _parse_repaired_c
    )
    _degraded_reason_c = (
        "extraction_completeness_failed" if _completeness_failed_ids
        else ("extraction_truncated_and_repaired" if _parse_repaired_c
              else ("evaluator_fallback" if _fallback_events_c ...
```

**Precedence, and why:** completeness failure first (evidence provably absent for a named LP), then a
repaired parse, then the substitution reasons. **A repair ranks above fallback because a fallback means
a different model answered in full, while a repair means some model answered in part and we do not know
what was lost.** `extraction_degraded` is now `fallback_used OR parse_repaired`.

---

# 4. THE EXERCISE — EVERY PATH, QUOTED

```
COMPLETE      -> {'repaired': False, 'path': 'fast_path_whole_text', 'repair_kinds': []}
TRUNCATED     -> {'repaired': True,  'path': 'truncation_repair',
                  'repair_kinds': ['closed_truncated_array'],
                  'provisions_recovered': 3, 'bytes_discarded': 1}
UNREPAIRABLE  -> ValueError: json_parse_failed: no valid JSON found (tail: '{"provisions"...
```

The eight `safe_json_extract` paths:

```
  fast_path  -> {'repaired': False, 'path': 'fast_path',              'repair_kinds': []}
  latex      -> {'repaired': True,  'path': 'fast_path_latex_fixed',  'repair_kinds': ['latex_escapes']}
  priority   -> {'repaired': False, 'path': 'candidate_priority_key', 'repair_kinds': []}
  synthetic  -> {'repaired': True,  'path': 'collected_provisions',   'repair_kinds': ['synthetic_wrapper']}
  best       -> {'repaired': False, 'path': 'candidate_best_scored',  'repair_kinds': []}
```

plus the three `raw_*` variants on the pre-normalisation branch. `test_every_path_label_is_distinct`
asserts no two paths share a label — otherwise a caller could tell *that* a salvage happened but not
*which*.

**10 tests, 399 passing overall.**

---

# 5. THE RE-RUN — AND IT ANSWERS STEP 527

```
build_log/runs/528_solidpower_thornton_industrial_lease.txt-modec_20260902_191838
COMPLETED     84 calls / 1278.0s     (prior run: 86 calls / 1159.0s)

extraction_parse_repaired        False
extraction_parse_path            fast_path_whole_text
extraction_parse_repair_kinds    []
extraction_provisions_recovered  None
extraction_bytes_discarded       None
extraction_raw_char_len          138641
extraction_degraded              False
degraded_reason                  None
coverage entries 32 | filled 27
```

**Full log captured this time — 48,212 bytes, and `grep -c "Repaired truncated JSON"` returns 0.**
(Step 527 could not answer this because I had piped the run through `tail`; that was my error and it is
not repeated.)

**`fast_path_whole_text` means the entire response parsed as valid JSON on the first attempt — no
bracket closing, no synthetic wrapper, no LaTeX rewriting, no salvage of any kind.**

**It did not fail visibly, because there was nothing to fail on.** Step 527 inferred this from the
*shape* of the empty LPs; it is now a direct measurement on a recorded field.

**What the user sees: unchanged.** No degraded banner, no `invalid_for_legal_analysis`, same 27 filled
LPs. That is the correct outcome for a run that did not truncate — and it is now a *statement* rather
than an absence of evidence.

`extraction_meta` grew from 10 keys to 18: `bytes_discarded, finish_reason, parse_path,
parse_repair_kinds, parse_repaired, provisions_recovered, raw_char_len, usage` added.

---

# 6. TWO DEFECTS FOUND BY RUNNING, BOTH MINE

**6.1 A missed bare-dict return unpacked a dict's keys.** `_extract_provisions_json` had a
fast-path `return obj` I did not convert, so `obj, _parse_meta = _extract_provisions_json(raw)`
unpacked the dict's **keys** — `too many values to unpack (expected 2)`. **Four existing tests caught
it**; my reading had not.

**6.2 My edit to the repair body silently no-op'd.** The docstring updated and the code did not, because
`\n` in the replacement pattern collapsed through two escaping layers — the same bug that bit me in
Step 524 — and I had not asserted on that particular `str.replace`. **Caught because the printed line
still read "3 provisions recovered" without the byte count.** Redone with explicit `chr()` construction.

**One test-fixture correction:** `_PROVISION_SHAPE` is `{provision_id, reasoning, verdict}` — an
*evaluation* shape, not the extraction shape. My first fixture used the extraction shape, which meant
the synthetic-wrapper path was **never actually exercised while the test appeared to pass.**

---

# WHAT IS NOT ESTABLISHED

- **The streaming `finish_reason` capture has never seen a live provider.** It is unit-tested on a
  stream-shaped chunk only. Until a real run records a non-None value, "the streaming path records
  finish_reason" is asserted, not demonstrated.
- **`usage` was `None` on the solidpower run** for the same reason, and is likewise unverified live.
- **Whether Atlas or divall ever truncated remains unanswerable.** The instrumentation is forward-only;
  no persisted historical run carries these fields. Step 527's question is now answered **for
  solidpower and for every future run**, not retrospectively.
- **Only the extraction path was migrated to the meta-returning form.** ~100 other `safe_json_extract`
  call sites still receive a bare object and still cannot distinguish a salvage.
- **No truncation has been observed anywhere yet**, so the `extraction_truncated_and_repaired` degraded
  reason has never fired on a real run — it is exercised only by unit test. everbridge (288 KB), the
  document most likely to truncate, remains unrun.
- **`bytes_discarded: 1` in the test** is an artefact of where the fixture was cut, not a
  representative magnitude.
- **Not deployed.**
