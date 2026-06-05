# Step 375L — Code Status: Stage 5e `gap_impact` Prompt-Contract Audit

**Date:** 2026-06-05  **Mode:** KEYLESS — read-only code inspection, zero model calls.
**External-use pause:** still in force. 375L does not lift it.

---

## What was built

| File | What it does |
|---|---|
| `build_log/375L_results.md` | Q1–Q8 (prompt-says / outputs-contain separated), single forced finding with evidence, doctrine update |

**READ-ONLY honored:** No edits to any production file. No prompt change, no schema change, no routing change, no cam/core/ edits, no Stage 5e widening.

---

## Keyless confirmation

This step is entirely keyless. Total model calls: **0**.
All findings derive from reading source files and running Grep against the codebase.

---

## Exact files and functions inspected

### Prompt builder (the function that constructs the use_impact / materiality prompt)

| Function | File | Lines |
|---|---|---|
| `_SYSTEM_PROMPT` (module-level string constant) | `cam/adapters/lease_review/lease_use_impact.py` | 104–142 |
| `_build_user_prompt()` | `cam/adapters/lease_review/lease_use_impact.py` | 145–181 |

The system prompt (`_SYSTEM_PROMPT`) is the governing prompt text — it defines the task, value definitions, rules, and the LP-05 embedded example. `_build_user_prompt()` constructs the per-run user message with tenant use context (business_type, operational_dependencies) and per-LP coverage status. Neither function calls models; models are invoked by `_call_evaluator()` which receives the already-built prompt strings.

### Output schema / contract

| Element | File | Lines |
|---|---|---|
| `_VALID_GAP_IMPACT` | `cam/adapters/lease_review/lease_use_impact.py` | 76 |
| `_VALID_MATERIALITY` | `cam/adapters/lease_review/lease_use_impact.py` | 77 |
| Module docstring output contract | `cam/adapters/lease_review/lease_use_impact.py` | 19–25 |
| JSON schema in `_SYSTEM_PROMPT` | `cam/adapters/lease_review/lease_use_impact.py` | 109–115 |

Allowed values:
- `gap_impact`: `{"favorable", "neutral", "adverse", "context_dependent"}`
- `materiality`: `{"high", "medium", "low", "not_applicable"}`

### Every `gap_impact` consumer (file:line)

| Location | File | Line(s) | How it uses gap_impact | Sign or consequence? |
|---|---|---|---|---|
| `deriveProvisionRiskLevel` — favorable → green | `app.js` | 5011 | `gap==='favorable'` → return green (skip compound-risk routing) | Consequence |
| `deriveProvisionRiskLevel` — neutral+low → amber | `app.js` | 5014 | `gap==='neutral' && mat==='low'` → amber | Consequence |
| `deriveProvisionRiskLevel` — review_needed routing | `app.js` | 5056–5063 | adverse+high → red; adverse+medium → amber; favorable/neutral → amber | Consequence |
| `_isUseImpactFavorable` | `app.js` | 16302 | `gap==='favorable'` → move LP from problems to favorable group | Consequence |
| CSS class (Client Impact block) | `app.js` | 16643–16645 | `gap==='favorable'` → green style; `gap==='adverse'` → red style | Consequence display (closest to sign-like visual; still consequence-grounded) |
| Sidebar `_skipForUseImpact` | `app.js` | 17718 | `_uiGap==='favorable'` → skip from Needs Attention | Consequence |
| `classifyFindingType` — consequence tier | `app.js` | 18107 | `uiActive && gap==='favorable'` → 'addressed' | Consequence |
| `action_bucket()` skip | `_step371_variance.py` | 30 | `gap==='favorable'` → clean bucket | Consequence (mirrors app.js) |
| `governed_fields()` read | `_step371_variance.py` | 66 | reads and records gap_impact for variance tracking | Observational |
| `GOVERNANCE_KEYS` classification | `_step371_variance.py` | 72–76 | gap_impact is a Class 3 governance key | Tracking |
| `action_bucket()` skip | `_step372_decomp.py` | 36 | same skip logic as _step371 | Consequence (mirrors app.js) |
| `CHAIN_LAYERS` read | `_step372_decomp.py` | 106 | reads gap_impact as chain layer in stability decomp | Observational |

**Files with zero gap_impact references (confirmed by grep):**
- `cam/adapters/lease_review/lease_adapter.py` — 0 hits
- `cam/adapters/lease_review/lease_synthesis.py` — 0 hits
- Any `.json` artifact file under results/ — 0 hits (gap_impact only in the persisted `use_impact` object, not as a standalone key)

---

## Forced finding: **FINDING A — clean consequence field**

**One-sentence evidence:** The prompt instructs consequence-only (`lease_use_impact.py:107`), no production consumer reads gap_impact as sign/direction (`app.js:5011–18120`, `_step371:30`, `_step372:36`), and the 375K sign-conflict observation was an analytical cross-stage comparison, not a code-level misread.

**B vs C pivot:** B requires the prompt to EXPLICITLY ask for both sign and consequence — it does not. C requires downstream code to treat it as sign — none does. → A.

---

## Key numerical / structural findings

| Item | Result |
|---|---|
| Production consumers of gap_impact | 8 distinct call sites in app.js + 2 in _step371 + 2 in _step372 = 12 total |
| Consumers that read as sign/direction | 0 |
| Consumers that read as consequence | 12 (all) |
| Files with no gap_impact reference | lease_adapter.py, lease_synthesis.py |
| Prompt sign question? | NO |
| Prompt consequence question? | YES — "for THIS tenant — given their specific use" |
| Value set sign-flavored? | YES — {favorable, adverse, neutral} overlap with legal direction vocabulary |
| Schema ambiguous? | NO — definitions in prompt are consequence-only |
| Fix type needed | RENAME only (`gap_impact` → `use_consequence`; optionally rename values) |
| Split needed? | NO |
| Consumer repair needed? | NO (no sign-reading consumers to repair) |

---

## Recommended rename targets for 375E-COV

| File | Current name | Rename to |
|---|---|---|
| `cam/adapters/lease_review/lease_use_impact.py` | `gap_impact` (schema, prompt return line, merge logic) | `use_consequence` |
| `05 Lease Analyzer/static/app.js` | `gap_impact` (8 call sites) | `use_consequence` |
| `05 Lease Analyzer/_step371_variance.py` | `gap_impact` (3 references) | `use_consequence` |
| `05 Lease Analyzer/_step372_decomp.py` | `gap_impact` (2 references) | `use_consequence` |

Optional value vocabulary rename: `favorable→beneficial`, `adverse→harmful` (eliminates overlap with legal direction polarity language).

**NOTE:** This is the PLAN output for 375E-COV. No renames have been executed in this step.

---

## Queue (confirmed by 375L)

1. **375E-COV** — widen `_should_assess` coverage + add provenance fields on both axes. RENAME `gap_impact` → `use_consequence` as part of this step. Add `use_consequence_source` (assessed | defaulted_floor | not_eligible | absent). Finding A means the rename is vocabulary cleanup, not a schema surgery — 375E-COV absorbs it.
2. **375E-DIR** — routing formula consuming COV fields. LP-05 resolves cleanly once `use_consequence` replaces `gap_impact`: Stage 7 direction=adverse (generic gap) + use_consequence=beneficial (this tenant) → favorable position, not Risk. No fake conflict.
3. **375E-COV implementation** (keyed).
4. **375E-DIR implementation** — NOT production-enabled until COV exists.
5. **375H-C** keyed fixture matrix. DEPLOYMENT TRAP unchanged.
