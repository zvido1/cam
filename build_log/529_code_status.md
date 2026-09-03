# Step 529 — 9 of 9 real leases extract cleanly. Nothing truncated. There is no 429.

**Date:** 2026-09-03 · **Instruction:** `build_log/529_chat_instruction.md`
**MEASUREMENT ONLY. No fix, no coverage, no architectural change.**
**9 extraction calls. All completed. 33/33 provisions each. Zero repairs, zero 429s.**
**Persisted: `build_log/runs/529_extract-only_20260903_001620` (Step 490 store).**

---

# 0. THREE "KNOWN" ROWS IN THE BRIEF ARE WRONG

| brief says | measured |
|---|---|
| solidpower — **KNOWN truncated**, "5 provisions in 8,192" | **Not truncated.** Step 528: `parse_repaired: False`, `parse_path: fast_path_whole_text`. This survey: **33 provisions, 138,641 output chars ≈ 34.7k tokens, 53% of the 65,000 ceiling.** The "5" was the count of *empty* buckets — retail provisions absent from an industrial lease (Step 527's shape test). |
| atreca_eastjamie — **KNOWN 429** | **No 429 has ever been recorded.** Step 526 grepped both logs: zero `429`, zero `rate limit`. Extraction succeeded 4×; the run aborted at the completeness gate on LP-20/LP-21. This survey: **completed, 33 provisions, `FinishReason.STOP`.** |
| divall — 33 provisions, **6,041 tokens** | 33 provisions confirmed. **The 6,041 figure has no source in the record** — no run before Step 528 recorded `usage` at all, which is exactly what Step 527 found missing. |

**The density check's premise does not survive.** "A small dense lease truncates and a large sparse one
does not" describes solidpower truncating at 8,192 tokens. It did not truncate, and the ceiling is
65,000. **There is no truncating document in the corpus to contrast against.**

---

# 1. THE TABLE — one row per document, all nine

```
fixture                            doc_ch   raw_out out/doc est_tok  %of65k  prov  non-empty  sec  repaired  finish
everbridge_northlake_pasadena      294492    212712   0.722   53178     82%  33/33     28    338.0  False    STOP
ncino_parkerfarm_wilmington        230269    165094   0.717   41274     63%  33/33     28    281.6  False    STOP
quanterix_crosby_bedford           224528    166272   0.741   41568     64%  33/33     29    277.6  False    STOP
atreca_industrial_rd_sancarlos     216949    155170   0.715   38792     60%  33/33     28    237.8  False    STOP
solidpower_thornton_industrial     211735    138641   0.655   34660     53%  33/33     29    215.4  False    STOP
bokf_oklahoma_tower                205232    129049   0.629   32262     50%  33/33     29    209.4  False    STOP
albireo_10postoffice               179021    140636   0.786   35159     54%  33/33     27    222.6  False    STOP
atreca_eastjamie_southsf           160244    135562   0.846   33890     52%  33/33     29    203.9  False    STOP
divall_wendys_mtpleasant            59496     58063   0.976   14516     22%  33/33     28    176.1  False    STOP
```

**Every column the brief asked for, with one substitution stated below.**

- **completed / truncated / 429 / other:** **completed, 9 of 9.** No truncation, no rate limiting, no
  other failure.
- **finish_reason:** `FinishReason.STOP` on all nine.
- **provisions emitted:** **33 of 33 on every document.** Non-empty buckets range 27–29 — remarkably
  flat across a 5× size range.
- **truncation_repaired:** `False` on all nine.
- **provisions-per-KB:** meaningless as a discriminator here — every document emits exactly 33, so the
  ratio is purely 33/KB and carries no information about the extractor. Reported instead as
  **output-chars-per-document-char**, which does discriminate.

## The substitution: output TOKEN counts are still unavailable

`usage` is **`null` on all nine rows.** The Step-528 capture is wired but reads the wrong attribute:

```python
        u = getattr(resp, "usage", None)      # OpenAI/Anthropic shape
        if u is None:
            return None
```

**Google's SDK exposes `usage_metadata`, not `usage`,** so `_extract_usage` returns `None` for every
Gemini call. `est_tok` above is `raw_char_len / 4` — a direct measurement of response *length*, divided
by a conventional ratio. **It is an estimate and is labelled as one.** Not fixed: this step is
measurement only.

## What DID validate: the Step-528 streaming fix

Step 528 recorded `finish_reason` as **"asserted, not demonstrated — never exercised against a live
provider."** **It is now demonstrated: `FinishReason.STOP` on nine live calls.** The streaming-path
capture works. `usage` on the same path does not, for the separate reason above.

---

# 2. THE QUESTION: WHAT FRACTION CAN THE CURRENT EXTRACTION PROCESS?

**All of it. 9 of 9 real executed leases — 100% — extract cleanly in a single call at 33 provisions.**

**The largest document in the corpus, everbridge at 288.6 KB, completed at 82% of the output ceiling.**
That is the closest any document comes, and it still cleared.

**This retires the architecture question as posed.** There is no evidence the single-call
33-provision extraction is failing on document size. Chunked extraction — which the brief forbade
anyway — has no measured problem to solve.

**What the corpus's failures actually are**, from the preceding steps: atreca and ncino abort at the
**completeness gate** because `is_applicable` matches `exclusive use` inside `non-exclusive use`
(Step 526, quoted). That is an applicability-matcher defect, and extraction is not involved — both
documents extract 33 of 33 here.

---

# 3. THE DENSITY CHECK — output tracks DOCUMENT SIZE, strongly and sub-linearly

```
linear fit:  raw_out = 21,885 + 0.6197 x doc_chars      R^2 = 0.928
```

**Not provision count** — every document emitted exactly 33, so provision count has zero variance and
cannot be the predictor. **Not "something else"** — 93% of the variance in output length is explained
by input length alone.

**But the relationship is sub-linear, and that is the interesting part:**

```
out/doc ratio:   divall (59 KB)   0.976
                 atreca_east      0.846
                 albireo          0.786
                 quanterix        0.741
                 everbridge (288) 0.722
                 bokf             0.629
```

**The ratio falls as documents grow.** A small lease is reproduced almost verbatim into the provision
buckets (divall at 0.976 — the extraction is nearly a copy); a large one is compressed to ~0.63–0.72.
The extractor selects more aggressively as there is more to select from, which is why size alone has
not produced a truncation.

**Extrapolating the fit to the 65,000-token ceiling (≈260,000 output chars): a document of ~384,000
characters ≈ 375 KB.** The largest real lease is 288.6 KB. **The corpus has ~30% headroom before the
single-call path becomes a real constraint** — on a 9-point fit, extrapolated 30% beyond its range,
which is a weak basis and is stated as such.

---

# 4. THE 429: IT DOES NOT RECUR, BECAUSE IT NEVER OCCURRED

**Zero 429s across nine consecutive extraction calls**, including two on atreca_eastjamie itself
(Step 526's run plus this one). Searching `build_log/` for `429` returns only line numbers and a job id.

The brief's decision rule — *"two occurrences on one document and none elsewhere is document-specific;
three documents failing is a quota pattern"* — **has no occurrences to arbitrate.** The failure
attributed to a 429 was `TimeoutError: Router timeout exceeded: 308.8s > 300.0s`, recorded in
`FINDING_lease_term_years_contingent_term.md`.

## And that timeout finding is now confirmed as real, and as fixed

```
everbridge   338.0s     <- would have FAILED at the old 300s ceiling
ncino        281.6s
quanterix    277.6s
atreca_ind   237.8s
```

**everbridge takes 338.0s.** Under the pre-Step-525 ceiling of 300s it would have raised
`Router timeout exceeded` and, with canonical fail-closed, produced nothing. **Step 525's raise to 540s
was necessary — and this is the first measurement that demonstrates it, on a different document from
the one that motivated it.** All nine sit under 540s; the closest is everbridge at 63% of it.

---

# 5. WHAT WAS BUILT

`build_log/_harness/run_extract_only.py` — one provider call per document, persisting through Step
490's `run_and_persist`. **A failure is recorded as a row, not raised as an exception**: "this document
cannot be processed" is the finding the survey exists to collect, so it has to survive into the record
rather than abort the sweep. Nine rows, nine files, `index.json` alongside.

Cost: **9 calls, 2,162 seconds total.** A full Mode C run is ~85–100 calls; the equivalent survey by
full pipeline would have been ~800 calls and roughly five hours.

---

# WHAT IS NOT ESTABLISHED

- **Output token counts are not measured.** `usage` is null on every Gemini call because
  `_extract_usage` reads `resp.usage` and Google provides `usage_metadata`. Every token figure here is
  `raw_char_len / 4`.
- **The 375 KB extrapolation is a 9-point linear fit pushed 30% past its largest observation.** It is
  an estimate of where the ceiling would bite, not a measurement that it does.
- **One call per document, no repeats.** Extraction is known non-deterministic (Steps 464/517), so a
  document that completed here could truncate on another attempt. **Nine clean rows are nine
  observations, not nine guarantees.**
- **Non-empty counts of 27–29 were not audited.** Whether the 4–6 empty buckets per document are
  correct absences or lost content was not checked — Step 527 established that for solidpower only.
- **This says nothing about coverage.** No LP verdicts were produced; the completeness gate, the seam
  and the panel were not exercised. atreca and ncino still abort downstream for reasons this survey
  does not touch.
- **`albireo` remains unclassified by type/jurisdiction** — the brief listed it as `? ?` and this
  survey did not determine it.
- **Nothing was fixed and nothing was deployed.**
