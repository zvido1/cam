# 421B Follow-up — Extraction Probe, Run Audit, cam/core/ Decision

**Date:** 2026-07-13
**Step:** 421B follow-up (read-only except where noted; no push)

---

## Item 1 — Ceiling Fix: Does It Stop Gemini Failing?

**Method:** Extract-only harness, N=5, Atreca document (160,244 chars / 25,655 words / 33 provisions), Gemini primary, new 65k ceiling. No panel, no Stage 5.

### Results

| Run | Outcome | LP chars | Hash (first 16) | Elapsed |
|-----|---------|----------|-----------------|---------|
| 1 | SUCCESS | 115,495 | `d3e62ead1670adb8` | 179.5s |
| 2 | SUCCESS | 115,495 | `d3e62ead1670adb8` | 187.5s |
| 3 | SUCCESS | 127,480 | `f7f64b5c4b08b55c` | 213.5s |
| 4 | SUCCESS | 115,495 | `d3e62ead1670adb8` | 192.0s |
| 5 | SUCCESS | 115,495 | `d3e62ead1670adb8` | 192.0s |

**Summary:** 5/5 succeeded. 0 parse failures. The ceiling fix stops Gemini failing on this document.

### The Hash Moved — What This Means

**Prior hash (6 runs at 32k ceiling):** `ab80aafe9f7bce07`, 110,153 LP chars.
**New hash (4/5 runs at 65k ceiling):** `d3e62ead1670adb8`, 115,495 LP chars.
**Outlier (1/5 runs at 65k ceiling):** `f7f64b5c4b08b55c`, 127,480 LP chars.

The hash moved. This is the finding you asked to be stated plainly.

**The prior extraction was being silently truncated.** At 3.5 chars/token, 110,153 LP chars ≈ 31,472 output tokens — within 1.7% of the 32k ceiling. Gemini was hitting the ceiling every time and `_repair_truncated_json()` was recovering the partial JSON, making the output appear complete. The prior extraction was consistently incomplete.

**Artificial determinism:** The 32k ceiling was producing the same truncation point on every run, making the output hash-stable (`ab80aafe9f7bce07`). This was not true Gemini determinism — it was deterministic truncation. The Step 421A finding ("Gemini is deterministic") was measuring a ceiling artifact, not a Gemini property.

**Without the ceiling, Gemini is variable.** 4/5 runs produced `d3e62ead1670adb8` (115,495 chars), 1/5 produced a different hash (127,480 chars). Gemini is not reliably deterministic at the full output level. The variability is real.

**419 frozen baseline is keyed to truncated extraction.** The baseline hash `ab80aafe9f7bce07` used as a "frozen" reference in Step 419 represents an incomplete extraction (110,153 chars). The panel variance measured in Step 419 was measured on a truncated evidence base. This does not invalidate the panel-variance findings (the evaluators saw what they saw), but the "frozen extraction" label is now more accurately "frozen truncated extraction."

**LP char delta:** The new ceiling yields 115,495 − 110,153 = +5,342 additional chars on most runs. These are LP text blocks that the 32k ceiling was cutting off. Specific LP content that was absent from the prior extraction but now present is unknown without a diff (not run here).

**Implication for Step 419 and the attorney validation:** The 419 frozen baseline was truncated. The attorney review was conducted on the Atlas lease, which used Gemini primary but with the 32k ceiling. All Atlas runs produced extraction under the same truncation constraint. The ceiling fix changes what future runs will extract; it does not retroactively alter past results.

---

## Item 2 — Named Affected Runs

### Fallback Runs (non-Gemini extractor, 7 unique run IDs)

| Run ID | Date | Document | Extractor | Context |
|--------|------|----------|-----------|---------|
| `lease_20260419_202420` | 2026-04-19 | T-10_sophisticated.docx | google/gemini-2.5-pro | Step 247/248 — early dev run |
| `lease_408c_atreca_runA` | 2026-07-08 | atreca_eastjamie_southsf_lease.txt | openai/gpt-5.5 | Step 408C — compound-consequence measurement |
| `lease_408c_atreca_runB` | 2026-07-08 | atreca_eastjamie_southsf_lease.txt | openai/gpt-5.5 | Step 408C — compound-consequence measurement |
| `lease_417_atreca_run04` | 2026-07-12 | atreca_eastjamie_southsf_lease.txt | openai/gpt-5.5 | Step 417 — Stage 5 baseline (N=10) |
| `lease_417_atreca_run06` | 2026-07-12 | atreca_eastjamie_southsf_lease.txt | openai/gpt-5.5 | Step 417 — Stage 5 baseline (N=10) |
| `lease_418c_run02` | 2026-07-13 | atreca_eastjamie_southsf_lease.txt | openai/gpt-5.5 | Step 418c — payload capture (intended as measurement) |
| `lease_418c_run03` | 2026-07-13 | atreca_eastjamie_southsf_lease.txt | openai/gpt-5.2 | Step 418c — payload capture (intended as measurement) |

### Stub-Provision Runs (extraction_failed=True, no evidence, 6 unique run IDs)

| Run ID | Date | Document | Context |
|--------|------|----------|---------|
| `lease_417_atreca_run05` | 2026-07-12 | atreca_eastjamie_southsf_lease.txt | Step 417 baseline — total extraction failure |
| `lease_417_atreca_run07` | 2026-07-12 | atreca_eastjamie_southsf_lease.txt | Step 417 baseline — total extraction failure |
| `lease_analyze_298a_t10_modec` | 2026-05-03 | T-10_sophisticated.txt | Step 298a — wiring test |
| `lease_analyze_298b_t10_modec` | 2026-05-03 | T-10_sophisticated.txt | Step 298b — wiring test |
| `lease_analyze_301_wiring_test` | 2026-05-04 | T-10_sophisticated.txt | Step 301 — wiring test |
| `lease_analyze_301a_gate_test` | 2026-05-04 | T-10_sophisticated.txt | Step 301a — gate test |

### Cross-reference Against External Validation and Benchmark

**Attorney validation set (Phase 1, R1/R2/R3 blind review):**
All attorney review was conducted on the Atlas lease (`atlas_meridian_warehouse_lease.txt`). Every Atlas run across all 33 Atlas pipeline_results.json files used `gemini-3.1-pro-preview` as primary — no fallback, no stubs. **No fallback or stub run appears in the attorney validation set.** No result needs to be withdrawn.

**Lease benchmark:**
- Atreca `408c` runs (`runA`, `runB`) are cited in internal measurement reports (Steps 409, 410, 411, 412). Those reports analyzed Stage 7 compound-consequence findings on extraction produced by gpt-5.5, not Gemini. The reports do not claim Gemini-primary extraction for those runs. The measurement conclusions (CRX instability, Layer 1/2/3 nondeterminism) were framed as pipeline-level observations, not as extraction-controlled measurements. **No measurement claim needs to be withdrawn**, but the extraction provenance should be noted as a caveat on those reports.
- Atreca `417` runs (run04, run05, run06, run07) are the Step 417 N=10 baseline. **run04 and run06 used gpt-5.5 fallback; run05 and run07 used stub provisions (no evidence).** The 417 report (`build_log/417_post_416_stage5_baseline.md`) computed a wobble rate across N=10 runs. Runs 05 and 07 produced results from empty evidence — their coverage assessments are not valid observations. Their inclusion in the N=10 wobble calculation inflates or distorts the wobble rate depending on how empty-evidence results are scored. **The 417 N=10 wobble rate should carry a caveat: 2/10 runs were stub-provision (no evidence), 2/10 used gpt-5.5 fallback.**

**Externally cited results:**
No fallback or stub run has been cited externally (i.e., outside internal build_log files or shared with reviewers). The attorney packet exclusively references Atlas results.

### Stub-provision runs in the 417 baseline — decision needed

`lease_417_atreca_run05` and `lease_417_atreca_run07` are stub-provision runs. Any coverage states produced by those runs are derived from empty LP text. They are not observations of the panel's behavior on the Atreca lease — they are noise from an empty evidence condition. The 421B guard (now live) would abort those runs before Stage 5. The question of whether to re-run the 417 baseline (N=8 valid + N=2 new canonical runs = N=10 corrected) is a decision for Chat.

---

## Item 3 — cam/core/ Question: response_mime_type and response_schema

### (a) Is response_schema supported in the SDK path currently used?

**Yes.** `google-genai==1.52.0` (the installed version) includes `response_schema` and `response_mime_type` in `GenerateContentConfig`. The Google adapter passes a plain dict as the `config` argument to `client.models.generate_content_stream()`. The SDK accepts plain dicts for `config` and converts them to `GenerateContentConfig` internally. Adding `response_mime_type` and `response_schema` to that dict is the intended usage.

```
google.genai.types.GenerateContentConfig.model_fields includes:
  response_mime_type  (str | None)
  response_schema     (dict | type | Schema | None)
  response_json_schema (dict | None)
```

For JSON output: `response_mime_type="application/json"` + `response_schema=<dict>`. The SDK description: "A compatible response_mime_type must also be set. Compatible mimetypes: `application/json`: Schema for JSON response."

### (b) How many lines would the change be?

Two approaches:

**Approach A — name-based targeting in the adapter (no ModelTarget change):**
4 lines added to `GoogleGenAIAdapter.call()` in `cam/core/provider_router.py`:
```python
if "extraction" in target.name:
    config["response_mime_type"] = "application/json"
    config["response_schema"] = _EXTRACTION_RESPONSE_SCHEMA  # defined at top of file
```
Plus schema definition: 1 constant in the file (~20 lines for the schema dict, or `_EXTRACTION_RESPONSE_SCHEMA = json.load(open(SCHEMA_PATH))` = 1 line if imported).
Total cam/core/ change: ~4-6 lines. Downside: implicit routing via target name is brittle.

**Approach B — `extra_provider_params` field on ModelTarget (recommended):**
1 line in `ModelTarget` dataclass:
```python
extra_provider_params: Optional[dict] = None
```
2 lines in `GoogleGenAIAdapter.call()` config building block:
```python
if target.extra_provider_params:
    config.update(target.extra_provider_params)
```
2 lines in `lease_extract.py` (extraction target construction):
```python
extra_provider_params={"response_mime_type": "application/json", "response_schema": _extraction_schema},
```
Total cam/core/ change: 3 lines. Total change including lease_extract.py: ~5 lines. Approach B is fully generic — any caller can pass any provider-specific params; the adapter passes them through without opinion.

### (c) Does this fall under the 416 precedent?

The 416 precedent: `_check_generation_integrity()` was added to `cam/core/provider_router.py` under the infrastructure-utility exception — the argument being "this is provider routing plumbing, not epistemic logic."

**The argument for Approach B:**

Adding `extra_provider_params: Optional[dict]` to ModelTarget and `config.update(target.extra_provider_params)` in the Google adapter is parameter passthrough infrastructure. The adapter has no opinion about what the params mean; it passes them to the SDK. The extraction layer (in `cam/adapters/`) decides what schema to use — which is already its domain (`lease_extract.py` owns the schema definition and the validation logic). Nothing in `cam/core/` knows what an "extraction schema" is; it just forwards a dict to the API.

This is structurally identical to the 416 change: that change made `cam/core/` assert what params are being sent. This change makes `cam/core/` accept additional params to send. Both are provider routing plumbing. Neither introduces evaluation logic into cam/core/.

**The counterargument:**

`extra_provider_params` is unconstrained — any caller can inject any SDK parameter, including ones that change model behavior in ways not visible to `_check_generation_integrity()`. The 416 guard was additive (assertion only, no behavioral change); Approach B is behavioral (changes what the SDK receives). This broadens the blast radius of any bug in the callers.

**Decision recommended:** Approach B is cleaner and falls under the 416 precedent. But the cam/core/ gate should be Tzvi's call, not inferred from precedent. The change is small (3 lines in cam/core/) and reversible; the benefit is eliminating JSON parse failures as a class. State the argument; do not act.

---

## Action Required

**Item 1:** No action. Data is in. The ceiling fix works mechanically. The hash movement and artificial-determinism finding are stated above for the record.

**Item 2:** **Decision needed on the 417 baseline.** 2/10 runs (run05, run07) are stub-provision. The reported wobble rate for Step 417 should carry a caveat. Whether to re-run the 2 missing slots (with the new canonical guard ensuring Gemini-primary extraction) is a Chat decision.

The 408c run findings (Steps 409-412) used gpt-5.5 extraction for both runA and runB. Those reports should note this. Whether any conclusions need to be hedged further is a Chat decision.

**Item 3:** Decision on cam/core/ authorization. The technical path is clear; the decision is yours.

---

*Read-only report. No code changes. Not committed.*
