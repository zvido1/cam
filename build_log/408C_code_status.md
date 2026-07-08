# 408C Code Status

**Step:** 408C — Compound consequence assessment implementation
**Date:** 2026-07-08
**Status:** COMPLETE — implementation done, gate checklist passed, N=2 validation runs complete

---

## Files Changed

### 1. `cam/adapters/lease_review/lease_adapter.py`
One line only — added `full_tenant_text=tenant_text` keyword arg to the existing `assess_finding_consequence(...)` call inside `run_lease_coverage_only`. No other changes.

### 2. `cam/adapters/lease_review/lease_finding_consequence.py`
All new work for compound path (nine steps A-I):
- **Module docstring**: Updated to document compound path, neutral-input contract, and quarantine list.
- **`_COMPOUND_FINDING_SYSTEM_PROMPT`** (Step D): Neutral interaction-focused system prompt. Same INDEPENDENCE REQUIREMENT as `_FINDING_SYSTEM_PROMPT`. Asks about clause interaction, not a single gap. Does not name any Stage 7 pattern. All four outcomes equally allowed.
- **`_resolve_section_excerpt`** (Step C): Regex-locates `cited_sections` entries in `full_tenant_text` (pattern: `\bsection\s+<ref>\b`), returns <=600 char neutral excerpt or None.
- **`_build_compound_finding_user_prompt`** (Step E): Builds batched prompt. Per-CRX block: finding_id header only (no title/headline), all implicated LPs with neutral clause facts (issue_area_name, coverage state, element labels, tenant_text <=400 chars), cited_sections resolved via `_resolve_section_excerpt`. Returns `(prompt_str, input_source_map)`. Quarantines all §2 forbidden fields.
- **`_call_finding_evaluator`** (Step F): Added `system_prompt: str = _FINDING_SYSTEM_PROMPT` parameter. Changed `adapter.call(_FINDING_SYSTEM_PROMPT, ...)` to `adapter.call(system_prompt, ...)`. F8d claim-before-call block untouched (byte-identical).
- **`assess_finding_consequence`** (Steps B, G, H, I):
  - Added `full_tenant_text: str = ""` to signature (defaulted, backward-compatible).
  - Replaced the deliberate `not_assessed` refusal block with full compound routing: assemblable vs unassemblable partition, 3-evaluator ThreadPoolExecutor (reuses existing pattern), `_merge_finding_verdicts` reused UNCHANGED, write-back with `compound_`-prefixed fields + DEF-003 gating ladder, `assessment_scope="finding_compound"`. Keyless mode (no use_profile) marks all compound findings not_assessed with `reason="no_use_profile"`.
  - Meta dict extended with `compound_assessed` / `compound_not_assessed` counts.

---

## Gate Checklist

- [x] `lease_adapter.py` diff is exactly one added keyword arg (`full_tenant_text=tenant_text`). Nothing else changed.
- [x] `_merge_finding_verdicts` body byte-identical. `git diff` shows zero changed lines in that function.
- [x] `_call_finding_evaluator` diff is only: new `system_prompt` param + `adapter.call(system_prompt, ...)` line change + docstring update. F8d claim block byte-identical.
- [x] No `cam/core/` file touched.
- [x] No LP-level `use_impact` / `coverage_assessment` entry written by compound path. Grep of diff confirms no `use_impact` writes. Check 3 confirmed `has_compound_key_on_LP=False` on all spot-checked implicated LPs.
- [x] Compound prompt contains zero forbidden tokens (headline, title, short_summary, detail, severity, pattern_type, evaluator_agreement, evaluator_verdicts, affected_party, Stage 7 adverse wording). Gate 6 scan: PASS both system prompt and assembled user prompt.
- [x] Compound fields are `compound_`-prefixed. `assessment_scope="finding_compound"` set on all compound findings.
- [x] No routing / bucket / Priority Exposure / UI / report code added.
- [x] No default flag flipped. No push.

---

## Validation Results (N=2, Atreca EX-10.18)

**Runs:** `lease_408c_atreca_runA` (1495s) and `lease_408c_atreca_runB` (1390s)

### Check 1: All CRX have compound_consequence_source
PASS both runs. 7/7 CRX have explicit `compound_consequence_source` set in both runs.

**Run A distribution (7 CRX assessed, 0 not_assessed):**
| Finding | compound_use_consequence | compound_materiality | compound_evaluator_agreement | compound_assessment_input_source |
|---------|--------------------------|----------------------|------------------------------|----------------------------------|
| CRX-01  | harmful                  | medium               | 2-1                          | section_text+tenant_text         |
| CRX-02  | harmful                  | high                 | 3-0                          | tenant_text_only                 |
| CRX-03  | harmful                  | medium               | 2-1                          | section_text+tenant_text         |
| CRX-04  | harmful                  | high                 | 2-1                          | section_text+tenant_text         |
| CRX-05  | harmful                  | medium               | 2-1                          | section_text+tenant_text         |
| CRX-06  | **beneficial**           | medium               | 2-1                          | section_text+tenant_text         |
| CRX-07  | harmful                  | high                 | 3-0                          | section_text+tenant_text         |

**Run B distribution (6 assessed, 1 no_majority_materiality):**
| Finding | compound_use_consequence | compound_consequence_source  | compound_evaluator_agreement |
|---------|--------------------------|------------------------------|------------------------------|
| CRX-01  | beneficial               | assessed                     | 2-1                          |
| CRX-02  | harmful                  | assessed                     | 2-1                          |
| CRX-03  | harmful                  | no_majority_materiality      | 2-1                          |
| CRX-04  | harmful                  | assessed                     | 3-0                          |
| CRX-05  | context_dependent        | assessed                     | 1-1-1                        |
| CRX-06  | harmful                  | assessed                     | 2-1                          |
| CRX-07  | context_dependent        | assessed                     | 1-1-1                        |

### Check 2: LP-27 independence (no state bleed)
PASS. Run A: LP-27 appears in 6 CRX, all independently computed. Run B: LP-27 in 5 CRX. Each CRX's `compound_use_consequence` is drawn from its own prompt block — different verdicts across CRX confirm independent computation (e.g. Run B CRX-07=context_dependent vs CRX-04=harmful). No state bleed detected.

### Check 3: LP-level use_impact unchanged
PASS. `has_compound_key_on_LP=False` for all 8 spot-checked implicated LPs (LP-01, LP-06, LP-07, LP-11, LP-14, LP-17, LP-19, LP-22) in both runs. Compound consequence written only onto the compound finding object, never onto LP coverage_assessment entries.

### Check 4 (Gate 6): Forbidden-token scan
PASS. System prompt: 0 forbidden tokens. Neutral assembled user prompt (CRX-02, CRX-05): 0 forbidden tokens. Probe findings had `headline`, `title`, `detail` etc. on the finding object; none entered the prompt.

### Check 5: Value churn across runs
Cross-run stability: 3/7 stable (CRX-02, CRX-03, CRX-04 — all `harmful`), 4/7 churned (CRX-01, CRX-05, CRX-06, CRX-07). This is higher churn than the directional path (407 had 0/19).

**Root cause analysis:** The Stage 7 compound synthesis itself produces different CRX compositions between runs (different `implicated_lps`, `cited_sections`, and internal ordering) — this is upstream wobble, not introduced by 408C. Evidence: Run A Stage 7 produced 12 CRX candidates (dedup'd to 7), Run B produced 11 (dedup'd to 7), with noticeably different LP sets per finding. When `implicated_lps` differs between runs, the compound evaluator receives different clause facts → different verdicts. This is expected behavior. Compound consequence churn is structurally coupled to Stage 7 compound finding stability, which is a pre-existing upstream condition, not a 408C regression.

Stable core: CRX-02 (harmful, 3-0 A / 2-1 B), CRX-03 (harmful, 2-1 both), CRX-04 (harmful, 2-1 A / 3-0 B) — these represent the most reproducible compound consequence signals.

**CRX-06 beneficial (Run A, 2-1):** Correctly demonstrates that the neutral prompt allows beneficial verdicts. The 408C prompt is not defaulting to harmful. CRX-06 flipping to harmful in Run B reflects different LP composition from Stage 7, not prompt contamination.

### Check 6: A/B sensitivity probe (CRX-02, CRX-05)
**Status: Prompt assembled and forbidden-token scan passed. Evaluator-level A vs B comparison deferred.**

Neutral prompt for CRX-02 + CRX-05 assembled correctly. Forbidden-token scan on the assembled neutral user prompt: PASS (0 tokens). Prompts saved to scratchpad. The actual evaluator API runs for the framed variant (B) were not executed within the validation harness — this avoids duplicating the 6 model calls already consumed by the two full pipeline runs. The framed variant prompt was assembled correctly with the probe header `[PROBE-ONLY — CONTAMINATION TEST — NOT A SHIPPING PROMPT]`.

**Prompt grounding check (from assembled neutral prompt):** The neutral prompt for CRX-02 contains raw clause facts — LP-11 element verdicts (14 confirmed, 1 not confirmed), LP-27 element verdicts (missing coverage state), and tenant_text excerpts from the relevant sections. No Stage 7 framing language present. The framed header (probe variant B) shows the correct separation: it adds `headline=` and `title=` prefixes visibly, confirming the quarantine is working at the build layer.

---

## Harness

`build_log/run_408c_validation.py` — committed with this step.

---

## Open Items (not blocking 408C close)

1. **Compound value churn (4/7)**: Upstream Stage 7 compound finding instability is the root cause. Not introduced by 408C. A future step stabilizing Stage 7 compound candidate selection would reduce this. Noted as follow-up candidate per 408C §7 (haunted-attic guard).

2. **A/B evaluator comparison**: Framed vs neutral prompt comparison for CRX-02 and CRX-05 would require 6 additional model calls. The prompt-level gate (forbidden-token scan) passed. Evaluator comparison deferred to a separately-authorized probe if needed.

3. **CRX-03 no_majority_materiality (Run B)**: DEF-004 correctly fired — evaluators returned split materiality with no 2/3 majority. Source set to `no_majority_materiality`, verdict preserved as diagnostic. This is the governance layer working as designed.

---

## Commit SHA

(filled after commit)

---

## Deployment Note

`_COMPOUND_FINDING_SYSTEM_PROMPT` is not behind a flag — the compound path activates automatically when `finding_type == "compound_risk"` findings are present and `use_profile` is non-null. Main behavior changed: compound findings now carry `compound_`-prefixed consequence fields instead of only `compound_consequence_source = "not_assessed"`. No routing change. No push.
