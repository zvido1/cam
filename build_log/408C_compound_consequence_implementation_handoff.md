# 408C — Compound Consequence Implementation Handoff (for Claude Code)

**Date:** 2026-07-08
**Type:** Implementation instruction for Claude Code. Code change to ONE file plus a one-line threading edit in the pipeline caller.
**Predecessor:** 408B (`build_log/408B_compound_consequence_build_spec.md`) is the authoritative spec. This handoff is the executable narrowing of it. Where this doc and 408B disagree, 408B wins — but they should not disagree; report it if they do.
**Author of spec:** Chat. **Executor:** Claude Code.

---

## 0. One-paragraph statement of the task

Replace COV-A's deliberate `compound_risk` refusal with a compound-aware consequence assessment that reuses the existing evaluator lineup and the existing `_merge_finding_verdicts` governance UNCHANGED. Add a compound prompt builder that feeds NEUTRAL clause facts (never Stage 7 framing), thread the lease text into the one call site that lacks it, parameterize the evaluator's system prompt, and write `compound_`-prefixed consequence fields onto each compound finding keyed by `finding_id`. Populate/record only. No routing, no buckets, no UI, no Priority Exposure.

---

## 1. Files in scope (exactly two)

1. `cam/adapters/lease_review/lease_finding_consequence.py` — all new functions + the compound routing branch + the `_call_finding_evaluator` signature change.
2. `cam/adapters/lease_review/lease_adapter.py` — ONE line: add `full_tenant_text=tenant_text` to the existing `assess_finding_consequence(...)` call inside `run_lease_coverage_only`.

**No other file may be edited.** In particular: no `cam/core/`, no `lease_synthesis.py`, no `app.js`, no report generator, no routing module (`lease_p2pp_routing.py`), no `_merge_finding_verdicts` body.

---

## 2. Hard prohibitions (read before writing any code)

- Do NOT modify `_merge_finding_verdicts` in any way. It is the frozen governance instance. Compound findings pass through it unchanged because it keys on `finding_id` and reads no LP field.
- Do NOT touch the F8d provider-claim logic in `_call_finding_evaluator` (the `claimed_providers.add(provider)` claim-before-call / no-release-on-failure block). The only edit to that function is adding a `system_prompt` parameter and using it in the `adapter.call(...)` line.
- Do NOT write compound consequence onto any LP's `use_impact` or onto any `coverage_assessment` entry. Compound consequence lives ONLY on the compound finding object.
- Do NOT feed Stage 7 conclusion fields into the prompt: `headline`, `title`, `short_summary`, `detail`, `severity`, `verdict`, `pattern_type`, `evaluator_agreement`, `evaluator_verdicts`, `affected_party`. These stay on the object as provenance; they never enter the evaluator input.
- Do NOT feed existing LP-level `use_impact` verdicts into the compound prompt. Assemble raw clause facts fresh.
- Do NOT resolve `implicated_lps[0]` only. Use ALL implicated LPs.
- Do NOT add routing, bucket assignment, Priority Exposure, or any UI/report rendering. This step is populate/record only.
- Do NOT flip any default flag. Do NOT push.

---

## 3. Implementation steps (in order)

### Step A — thread lease text (lease_adapter.py, 1 line)

In `run_lease_coverage_only`, the Stage 5e-F block currently calls:

```python
result["cross_provision_findings"], _finding_consequence_meta = assess_finding_consequence(
    cross_provision_findings=result["cross_provision_findings"],
    coverage_assessment=coverage_assessment,
    use_profile=use_profile_data_c,
    perspective=cfg.get("perspective", "tenant"),
    cfg=cfg,
)
```

Add one keyword argument: `full_tenant_text=tenant_text`. (`tenant_text` is already in local scope — it is parsed near the top of `run_lease_coverage_only` and passed to `run_synthesis(full_tenant_text=tenant_text, ...)` a few blocks above.) This is the ONLY edit to `lease_adapter.py`.

### Step B — extend the signature (lease_finding_consequence.py)

Add `full_tenant_text: str = ""` to `assess_finding_consequence(...)` (defaulted, so any other caller and the directional-only path are unaffected). Confirmed single call site (Step A), but the default keeps it safe.

### Step C — add the section resolver (lease_finding_consequence.py)

New module-level helper, e.g.:

```python
def _resolve_section_excerpt(section_ref: str, full_tenant_text: str, max_chars: int = 600) -> Optional[str]:
    """Locate a cited section in the lease text and return a bounded neutral excerpt.
    Follows the same locate pattern as lease_adapter._section_relevant_to_provision.
    Returns None if the section cannot be located or text is empty."""
```

Implementation notes: normalize `section_ref` (e.g. strip "Section "/"§"), regex-locate `\bsection\s+<ref>\b` case-insensitive, slice a bounded excerpt from the match. This is neutral clause text extraction, nothing more. If `full_tenant_text` is falsy or the section is not found, return None (caller falls back to per-LP `tenant_text`).

### Step D — add the compound system prompt (lease_finding_consequence.py)

New module constant `_COMPOUND_FINDING_SYSTEM_PROMPT`. Model it on `_FINDING_SYSTEM_PROMPT` (the A2-clean directional prompt). Requirements:
- Same INDEPENDENCE REQUIREMENT wording ("absence or structural incompleteness does NOT equal adverse by default; assess consequence independently").
- Asks about the INTERACTION of multiple provisions, not a single gap.
- MUST NOT name any Stage 7 pattern, MUST NOT assert a compound risk exists, MUST NOT use adverse framing words.
- Explicitly allows all four outcomes: beneficial / neutral / harmful / context_dependent. Harmful is NOT the default.
- Returns the same JSON shape per finding id (`use_consequence`, `materiality`, `use_reasoning`) that `_merge_finding_verdicts` already parses. Key by `finding_id` (e.g. "CRX-02"), exactly as the directional prompt keys by "Dir-NN".

### Step E — add the compound prompt builder (lease_finding_consequence.py)

`_build_compound_finding_user_prompt(compound_findings, coverage_by_lp, full_tenant_text, use_profile, perspective) -> str`. Per-CRX block:
1. `finding_id` header only (no title/headline).
2. For EACH LP in `implicated_lps`: `issue_area_name`, neutral coverage state, present/missing element labels, `tenant_text` excerpt (≤400 chars) — mirroring `_build_finding_user_prompt`'s per-LP rendering but looped over all implicated LPs.
3. For EACH `cited_sections` entry: `_resolve_section_excerpt(...)` output, if non-None.
4. The neutral interaction question (from 408B §4 "Neutral prompt discipline").
Batched (all CRX in one prompt), returning JSON-only instruction keyed by finding id. Track, per finding, what fed it (`section_text+tenant_text` vs `tenant_text_only` vs unassemblable) for the `compound_assessment_input_source` output field.

### Step F — parameterize the evaluator (lease_finding_consequence.py)

`_call_finding_evaluator(role, ev_cfg, user_prompt, claimed_providers, claimed_lock, system_prompt: str = _FINDING_SYSTEM_PROMPT)`. In the inner `_try`, change `adapter.call(_FINDING_SYSTEM_PROMPT, user_prompt, target)` to `adapter.call(system_prompt, user_prompt, target)`. Nothing else in that function changes — the F8d claim block is untouched. Directional callers omit the arg (default preserves behavior); the compound branch passes `system_prompt=_COMPOUND_FINDING_SYSTEM_PROMPT`.

### Step G — add the compound routing branch (lease_finding_consequence.py, in assess_finding_consequence)

Replace the current refusal block:

```python
for f in cross_provision_findings:
    if f.get("finding_type") == "compound_risk":
        f["compound_consequence_source"] = "not_assessed"
        n_compound += 1
```

with: collect the `compound_risk` findings; partition into assemblable (at least one implicated LP has `tenant_text`, OR at least one `cited_sections` entry resolves) vs unassemblable. For unassemblable and keyless (`not use_profile`) findings, keep `compound_consequence_source = "not_assessed"` + a `compound_consequence_reason` (`compound_input_unavailable` / `no_use_profile`). For assemblable findings with a use profile: build the prompt (Step E), run the 3-evaluator lineup via `_call_finding_evaluator(..., system_prompt=_COMPOUND_FINDING_SYSTEM_PROMPT)` (reuse the existing ThreadPoolExecutor pattern from the directional path), merge via `_merge_finding_verdicts(results, compound_findings_assessed)` UNCHANGED, then write back per Step H.

Chunking: mirror the directional/5e pattern only if compound count exceeds ~11 (Atreca has 6; chunking will not trigger, but keep the code path correct).

### Step H — write-back (lease_finding_consequence.py)

For each assessed compound finding, using the SAME DEF-003 support-label gating ladder as the directional write-back (support_label ∉ {no_evaluators, insufficient_support} → assessed; insufficient_support → insufficient; route_to_review_needed → no_majority_materiality; else absent), write `compound_`-prefixed fields:

- `compound_use_consequence`, `compound_materiality`
- `compound_consequence_source` (assessed | insufficient_consequence_support | no_majority_materiality | not_assessed)
- `compound_consequence_reason` (only when not assessed)
- `compound_consequence_support_label`, `compound_vote_distribution`, `compound_valid_evaluator_count`, `compound_expected_evaluator_count`
- `compound_consequence_reasoning` (null on 1-1-1 split per F8c), `compound_evaluator_agreement`
- `compound_materiality_votes`, `compound_materiality_support`, `compound_materiality_disputed`
- `compound_assessment_input_source` (`section_text+tenant_text` | `tenant_text_only`)
- `assessment_scope = "finding_compound"`

Leave `severity`, `pattern_type`, `affected_party`, `title`, `headline`, `detail` on the object UNTOUCHED (provenance).

### Step I — docstring + meta

Update the module docstring: compound findings are now assessed via a neutral compound prompt; document the quarantine list and the `finding_compound` scope. Extend the returned `meta` dict with compound counts (`total_compound`, `compound_assessed`, `compound_not_assessed`) alongside the existing directional counts.

---

## 4. Gate checklist (Claude Code confirms each before reporting done)

- [ ] `lease_adapter.py` diff is exactly one added keyword arg (`full_tenant_text=tenant_text`). Nothing else in that file changed.
- [ ] `_merge_finding_verdicts` body is byte-identical (git diff shows zero lines changed in that function).
- [ ] `_call_finding_evaluator` diff is only the new `system_prompt` param + the `adapter.call` line; the F8d claim block is byte-identical.
- [ ] No `cam/core/` file touched.
- [ ] No LP-level `use_impact` / `coverage_assessment` entry is written by the compound path (grep the diff).
- [ ] The compound prompt string contains none of the §2 forbidden fields (add a lightweight self-check or unit assertion that dumps the assembled prompt and greps for forbidden tokens).
- [ ] Compound consequence fields are `compound_`-prefixed and `assessment_scope="finding_compound"`.
- [ ] No routing / bucket / Priority Exposure / UI / report code added.
- [ ] No default flag flipped. No push.

---

## 5. Validation (run after implementation, before any commit-for-review)

Reuse the 407 Atreca fixture (`lease_407_atreca_runA` / a fresh Atreca Mode C run). Per 408B §10:

1. All 6 CRX get either an assessed compound consequence or an explicit `compound_consequence_reason`.
2. LP-27 appears in its 5 CRX with 5 independently-computed verdicts (no state bleed) — dump each CRX's consequence and confirm they are computed per-finding.
3. No LP-level `use_impact` changed (diff the coverage_assessment consequence fields against a pre-408C run).
4. Dump the assembled compound prompt; confirm zero forbidden tokens.
5. Record the consequence distribution (harmful/beneficial/neutral/context_dependent), agreement, materiality, not_assessed count.
6. **A/B sensitivity probe on CRX-02 and CRX-05 (per 408B §10 item 10 — the REVISED version):** run neutral (A) vs deliberately-framed (B). Success is NOT "they diverge." Success is: neutral prompt excludes forbidden fields; neutral reasoning cites raw clause facts and is free of Stage 7 vocabulary; framed variant marked probe-only; divergence recorded as sensitivity evidence; non-divergence recorded without overclaiming safety. If neutral-variant reasoning echoes Stage 7 terms ("one-sided", "dead-end", "trap", pattern names), FAIL the prompt and revise it even if the label looks right.

N≥2 for any distribution claim. All results DIRECTIONAL, not promoted, not patent record.

---

## 6. What Claude Code returns

- `build_log/408C_code_status.md` with: files changed + diffs summary, the gate checklist results, the validation outputs (distribution, LP-27 independence proof, forbidden-token scan result, A/B probe reasoning inspection), and the commit SHA (explicit paths, no `git add .`, no push).
- Do NOT push. Do NOT flip defaults. Do NOT proceed to any UI/COV-B step.

---

## 7. Explicit non-goals (the haunted-attic guard)

408C ends at "compound findings carry a `compound_` consequence with honest provenance in `pipeline_results.json`." It does NOT:
- render compound consequence anywhere user-facing (no `app.js`, no PDF, no synopsis);
- route compound findings to any action bucket or Risk surface;
- build Priority Exposure or any ranking;
- change directional or LP-level behavior;
- flip the widened-5e default or any other flag.

Those are later, separately-authorized steps. If implementing 408C surfaces a tempting "while I'm here" change, STOP and note it in `408C_code_status.md` as a follow-up candidate — do not do it.

---

*Handoff artifact: Step 408C. Implementation instruction; execution by Claude Code, gated on 408B commit + Tzvi's go.*
