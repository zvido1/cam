# Diagnostic 372-BUD — Pipeline-wide token-budget utilization audit

**Date:** 2026-05-31
**Author:** Claude Code
**Type:** Read-only audit over code + stored runs. No model calls, no reruns.
**Base SHA:** `17d0f15` (372FAIL). Status file only. Gates 372c scope.

---

## Part 1 — Budget inventory (all structured-output calls)

| Call site | File | Budget constant | Value | Type | Line ref |
|---|---|---|---|---|---|
| **Stage 2** Extraction (single-doc) | lease_extract.py | `EXTRACTION_MAX_TOKENS_SINGLE` | 32,000 | Hard-coded | L247 |
| **Stage 2** Extraction (chunked) | lease_extract.py | `EXTRACTION_MAX_TOKENS_CHUNK` | 24,000 | Hard-coded | L248 |
| **Stage 305** base config (A/B/C) | lease_coverage_305.py | `EVALUATOR_LINEUP_305[X]["max_output_tokens"]` | 3,000 | Hard-coded | L73/82/91 |
| **Stage 305** actual call (scaled) | lease_coverage_305.py | `max(3000, len(elements_305) × 300 + 500)` | 3,000–5,600 | Computed from element count | L289 |
| **Stage 305** fallback pool (Gemini/Mistral) | lease_coverage_305.py | Same `_tokens` as primary | Same computed value | Inherited from caller | L380–390 |
| **Stage 5d** Use-aware coverage (A/B/C) | lease_use_aware_coverage.py | `EVALUATOR_LINEUP[X]["max_output_tokens"]` | 2,500 | Hard-coded | L89/99/109 |
| **Stage 5d** LP-summary sub-call | lease_use_aware_coverage.py | inline | 600 | Hard-coded | L349 |
| **Stage 5e** Use-impact (A/B/C) | lease_use_impact.py | `_EVALUATOR_LINEUP[X]["max_output_tokens"]` | 3,000 | Hard-coded | L59/64/69 |
| **Stage 7** Pass-1 (A/B/C) | lease_synthesis.py | `EVALUATOR_LINEUP[X]["max_output_tokens"]` | 8,000 | Hard-coded (was 6K) | L53/62/71 |
| **Stage 7** Compound-gen Q3 (A/B/C) | lease_synthesis.py | inline in `_call_compound_evaluator` | 4,000 | Hard-coded | L747 |
| **Stage 7** Pass-2 directional (A/B/C) | lease_synthesis.py | `DIRECTIONAL_PASS2_MAX_OUTPUT_TOKENS` | 12,000 | Hard-coded constant (was 8K, 370d) | L93/114 |
| **Stage 7** Consolidation (B only) | lease_synthesis.py | inline in `_call_consolidator` | 6,000 | Hard-coded | L811 |

**Note on gpt-5.x models:** `max_completion_tokens` is the parameter used for all gpt-5.x calls
(line 191 in provider_router.py). For gpt-5.5 (reasoning model), this budget is SHARED between
internal reasoning tokens and visible completion tokens. For gpt-5.4 and other non-reasoning
models, `max_completion_tokens` = `max_tokens` (visible output only).

---

## Part 2 — Utilization classification per call site

**Methodology:** Token estimates use ~4 chars/token for JSON (Claude Sonnet observed ratio),
actual raw_len from 370c and NDET logs where available, and NDET failure rates as utilization
signal (≥40% PARSE_ERROR → FAILING).

| Call site | Max observed output (tokens est.) | Budget | % budget | Classification | Scaling |
|---|---|---|---|---|---|
| Stage 2 extraction | ~5,000–8,000 (Gemini verbose) | 32,000 / 24,000 | 25–33% | **COMFORTABLE** | Flat (full-document call) |
| Stage 305 (6-elem LP, Sonnet) | ~2,500–3,000 | 3,000 | 83–100% | **HOT** | Per element: ~300–500 tok/elem |
| Stage 305 (11-elem LP-22, Sonnet) | ~6,750 (27,087 chars ÷ 4) | 3,800 | ~178% | **FAILING** | 40% PARSE_ERROR at N=20 |
| Stage 305 (12-elem LP-09, Sonnet) | ~5,000–6,000 est. | 4,100 | ~122–146% | **FAILING/HOT** | 0% fail at N=20 but close |
| Stage 305 (17-elem LP-11 est., Sonnet) | ~10,463 (extrapolated from LP-22) | 5,600 | ~187% | **FAILING (predicted)** | LP-22 verbosity extrapolated |
| Stage 305 (11-elem LP-22, gpt-5.5) | 0 (reasoning exhaustion) | 3,800 | — | **FAILING** | 90% empty at N=20 |
| Stage 305 (12-elem LP-09, gpt-5.5) | 0 (reasoning exhaustion) | 4,100 | — | **FAILING** | 50% empty at N=20 |
| Stage 5d use-aware (per LP) | ~800–1,500 est. | 2,500 | 32–60% | **WATCH** | Short LP-level verdict |
| Stage 5e use-impact (per LP) | ~1,200–2,000 est. | 3,000 | 40–67% | **WATCH** | 3 fields per LP |
| Stage 7 Pass-1 (28 LPs, Sonnet) | ~8,000–8,400 | 8,000 | 100–105% | **HOT/FAILING** | 28 LPs × ~300 tok/LP; comment: "28 LPs × ~300 = 8.4K needed" |
| Stage 7 compound-gen Q3 | ~625–1,250 (5 candidates) | 4,000 | 16–31% | **COMFORTABLE** | Per compound candidate |
| Stage 7 Pass-2 directional | ~6,000–7,000 | 12,000 | 50–58% | **COMFORTABLE** | Post-370d; LP-22 worst: 27,087 chars = 6,772 tok |
| Stage 7 consolidation | ~2,000–3,500 | 6,000 | 33–58% | **COMFORTABLE** | 30 CPFs est. |

**Calibration notes:**
- Stage 305 LP-22 Sonnet actual: 27,087 chars (H2 complete run) = 6,772 tokens at 4 chars/tok.
  Budget at LP-22 = 3,800. Ratio = 178%. Confirmed FAILING (40% PARSE_ERROR at N=20).
- Stage 7 Pass-1 comment in code (L53): "raised from 6K — 28 LPs × ~300 tokens/entry ≈ 8.4K needed."
  Budget was raised to 8K but estimated need is 8.4K → still technically over budget. Mitigated by
  Step 334 (separate compound call) but the Q1/Q2 output may still truncate on verbose runs.
- Stage 305 LP-11 (17 elements): budget = 5,600 tokens. Sonnet at LP-22 verbosity would need
  17 × 2,462 chars/element = 41,854 chars ≈ 10,463 tokens — 1.87× the budget. **Predicted FAILING.**
  Caveat: LP-11 (environmental/hazmat) may have shorter per-element reasoning than LP-22 (SNDA);
  the 3 headless production runs had no failure — but N=3 is insufficient evidence of adequacy.

---

## Part 3 — Step 333 compound-candidates: same-root budget exhaustion?

**Confirmed YES — fourth instance of the same pattern.**

**Step 334 code comment** (lease_synthesis.py L2233):
> *"Pass 1 (Q1+Q2) hits the 8K token limit before writing candidates[]. A separate focused call
> gives each evaluator a clean budget for Q3."*

This is identical in structure to the Stage 305 and Stage 7 Pass-2 failures:
- Stage 305: budget exhausted on verbose per-element JSON → empty output (B) or truncated (A)
- Stage 7 Pass-1: budget exhausted on Q1/Q2 cross-coverage analysis before reaching `candidates[]`
  (the final required output field for Q3)
- Stage 7 Pass-2 (pre-370d): budget exhausted mid-directional-array → truncated response
- **Step 333/334**: same mechanism — Q1/Q2 response fills the 8K budget, leaving no tokens for
  `candidates[]`. Fix was a workaround (separate call) not a budget increase.

All four are the same root cause: **a fixed output budget that is insufficient for the
combined output required, exhausted before reaching a required field.** The mitigation approaches
differ (workaround compound call vs budget raise), but the root mechanism is identical.

**Is Step 334's 4,000-token compound-gen call adequate?** Yes — observed 5 candidates ×
~250 tokens each ≈ 1,250 tokens = 31% utilization. **COMFORTABLE.** The compound call was
correctly sized for its narrower task (Q3 only, ~5 candidates per run).

---

## Part 4 — Other non-budget same-model variance causes

### V1 — gpt-5.5 always runs at temperature=1 (not 0.0)

**File:** `cam/core/provider_router.py` lines 190–195:
```python
if target.model.startswith("gpt-5"):
    params["max_completion_tokens"] = target.max_output_tokens
    # Don't set temperature for GPT-5.2 (uses default 1)
```

Every call in the pipeline requests `temperature=0.0` but the OpenAI adapter silently discards
the temperature parameter for `gpt-5.x` models. gpt-5.5 always runs at its default sampling
temperature (1.0). This is a mechanical source of variance for ALL gpt-5.5 calls throughout
the pipeline (Stage 305, Stage 5d, Stage 5e, Stage 7 Pass-1 — all affected). This affects every
run where B (gpt-5.5) is the primary. gpt-5.4 (the B fallback and Stage 7 Pass-1/consolidation
model) uses `max_tokens` with explicit temperature; its temperature=0.0 is honored.

**Non-fix note:** the comment says "GPT-5.2 only supports default temperature." If gpt-5.5 also
doesn't support explicit temperature, this is a model constraint, not a code defect. But it means
B cannot be made deterministic even in principle, and any "within-model variance" in B that looks
like non-determinism is working as designed.

### V2 — Stage 5 LP-text extraction non-determinism (tenant_text varies)

From 372WV verification: LP-19's `tenant_text` differed in W1 vs all other 5 runs (different
section extraction). From 370c: `_stage_data.negative_space` differed in W1 (len=634 vs 429 for
others). The Stage 2 extraction / Stage 3 LP-text segmentation produces slightly different
`tenant_text` per LP on some runs — making every downstream call (Stage 305, Stage 5d, Stage 5e,
Stage 7 Pass-1 prompt) potentially non-identical even for byte-identical input leases.

The negative_space detection in `lease_negative_space.py` IS regex-based (LLM-free, deterministic
given the same input). The variance is upstream in Stage 2/3 LP-text extraction.

### V3 — Stage 7 Pass-1 prompt assembly varies with Stage 5 output

`_build_evaluator_user_prompt` (Stage 7 Pass-1) takes the `coverage_assessment` as input —
which is the Stage 5 output. Stage 5 is non-deterministic (V2 above). Different Stage 5 outputs
→ different Stage 7 Pass-1 prompts → different Pass-1 directional candidates. Confirmed by
370c `pass1_prompt_hash` being different across H1/H2/H3 (md5: dcf54a2c / e0a0aafcb / 7575f8cf,
lengths 42,392 / 42,274 / 42,105 chars).

**This is the upstream cascade:** Stage 2/3 text extraction variance → Stage 5 verdict variance →
Stage 7 Pass-1 prompt variance → directional candidate count variance → bucket flip.

### V4 — Silent fallback substitution on Stage 2/3/5 evaluator calls (not only Stage 305)

`lease_evaluate.py` (Stage 3) also has `own_chain` + `_SHARED_FALLBACK_POOL` (Gemini/Mistral)
for each of A/B/C (L70/83/95/104). The same silent-label-mislabeling defect found in Stage 305
(372ID) exists here too — `_extract_verdicts_for_element`-equivalent code in Stage 3 uses the
static role label. Fallback invocations in Stage 3 would also be invisible in stored data.
Stage 5d (`lease_use_aware_coverage.py`) and Stage 5e (`lease_use_impact.py`) also have
`own_chain` fallbacks. The 372ID audit was limited to Stage 305; this is the broader scope.

---

## Summary — Full HOT/FAILING list (= 372c scope)

| Site | Status | Mechanism | Models affected | Suggested fix for 372c |
|---|---|---|---|---|
| **Stage 305 Sonnet (6-elem LPs)** | HOT (83-100%) | Output truncation | A (Sonnet) | Raise formula: N×500+1000 |
| **Stage 305 Sonnet (11+ elem LPs)** | FAILING | Output truncation | A (Sonnet) | Raise formula: N×500+1000 |
| **Stage 305 gpt-5.5 (10+ elem LPs)** | FAILING | Reasoning exhaustion | B (gpt-5.5) | SPLIT prompt (≤8 elements/call) PLUS reasoning-aware budget |
| **Stage 305 LP-11 (17 elem, all models)** | PREDICTED FAILING | A: truncation; B: reasoning exhaustion | A + B | Both fixes above |
| **Stage 7 Pass-1 (28 flagged LPs)** | HOT (budget under estimated need) | Near-budget (Q1/Q2 fills 8K); Step 334 is the mitigations | All | Raise budget OR confirm Step 334 fully mitigates |

Sites that are **not** HOT/FAILING and do not need budget changes in 372c:
- Stage 2 extraction: COMFORTABLE
- Stage 305 (≤10 elements, C/Grok): COMFORTABLE
- Stage 5d/5e: WATCH but not failing in production evidence
- Stage 7 compound-gen: COMFORTABLE
- Stage 7 Pass-2 directional: COMFORTABLE (post-370d)
- Stage 7 consolidation: COMFORTABLE

---

## Commit scope

Status file only. No code changes. Analysis from code + stored runs only.
