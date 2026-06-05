# 375L — Stage 5e `gap_impact` Prompt-Contract Audit

**Date:** 2026-06-05  **Mode:** KEYLESS — read-only code inspection, zero model calls.  
**External-use pause:** still in force. 375L does not lift it.

---

## Files / functions inspected

| File | What was read |
|---|---|
| `cam/adapters/lease_review/lease_use_impact.py` | `_SYSTEM_PROMPT` (lines 104–142), `_build_user_prompt()` (145–181), `_VALID_GAP_IMPACT` (line 76), `_merge_verdicts()` (239–337), `assess_use_impact()` (341–441) |
| `05 Lease Analyzer/static/app.js` | `deriveProvisionRiskLevel()` (5004–5065), `_isUseImpactFavorable()` (16297–16311), coverage card CSS block (16641–16651), sidebar `_skipForUseImpact` (17716–17729), `classifyFindingType()` consequence block (18072–18120) |
| `05 Lease Analyzer/_step371_variance.py` | `action_bucket()` (line 30), `governed_fields()` (line 66), `GOVERNANCE_KEYS` (lines 72–76) |
| `05 Lease Analyzer/_step372_decomp.py` | `action_bucket()` (line 36), `CHAIN_LAYERS` (line 106) |
| `cam/adapters/lease_review/lease_adapter.py` | Full grep — **no `gap_impact` references** |
| `cam/adapters/lease_review/lease_synthesis.py` | Full grep — **no `gap_impact` references** |

---

## Q1. Does the 5e prompt explicitly ask whether the gap HELPS or HURTS this tenant (use-consequence)?

| Column | Answer |
|---|---|
| **PROMPT INSTRUCTS** | YES — unambiguously. The system prompt (`lease_use_impact.py:107`): *"determine whether the gap (missing or significantly partial coverage) is favorable, neutral, or adverse for THIS tenant — given their specific use of the space."* Value definitions: "favorable: The absence or weakness of this provision **benefits THIS client given their use**"; "adverse: This gap creates **meaningful risk or cost for this client given their use**." Every definition uses "THIS client" and "given their use." The explicit LP-05 example in the prompt further anchors this as consequence: "LP-05 Permitted Use absent for a warehouse tenant → tenant has maximum operational flexibility; landlord cannot restrict the tenant's activities... Gap impact: favorable." |
| **OUTPUTS CONTAIN** | Yes — use-aware reasoning grounded in tenant business type and operational dependencies. LP-05 output (favorable) and LP-20 output (neutral×8) reflect the consequence framing exactly as the prompt intends. |

**Proven-claim:** The prompt explicitly asks for use-aware consequence — is the gap beneficial, neutral, or harmful FOR THIS tenant.  
**Caveat:** None. This is a code fact, not n-dependent.  
**Still-unmeasured:** Whether models consistently apply the "absence ≠ adverse" rule across use types beyond the warehouse example embedded in the prompt.

---

## Q2. Does the prompt ask whether the underlying gap is directionally adverse (SIGN), or only whether its consequence is adverse for this use?

| Column | Answer |
|---|---|
| **PROMPT INSTRUCTS** | **Consequence ONLY.** The prompt never asks "is this gap a directional adverse signal for tenants generically?" The LP-05 example is the clearest evidence: an ABSENT provision (a structural gap) = favorable consequence because this specific warehouse tenant gains operational flexibility. The prompt explicitly instructs: "Absence ≠ adverse by default. When a restriction is MISSING, ask: does the absence give the tenant MORE freedom or MORE exposure?" This is a consequence question, not a sign question. The word "sign," "direction," "directional," and "generic adverse" appear nowhere in `_SYSTEM_PROMPT` or `_build_user_prompt()`. |
| **OUTPUTS CONTAIN** | The LP-05 output (favorable) is the canonical example of consequence-without-sign: Stage 7 independently records this same LP as `tenant_unprotected` (adverse sign generically), but the 5e output records it as favorable consequence for this tenant. These two values are both correct answers to different questions — the model did not err. |

**Proven-claim:** The prompt asks consequence only. No sign or direction question appears in the prompt text.  
**Caveat:** The value set uses sign-flavored vocabulary (`favorable/adverse`) that OVERLAPS with legal direction language, which creates analytical confusion when comparing 5e outputs against Stage 7 direction — but this is a vocabulary artifact, not a prompt ambiguity.  
**Still-unmeasured:** Whether the LP-05 embedded example creates implicit guidance that makes the model systematically distinguish use-consequence from generic direction across all use profiles, or only for the warehouse-use profile shown.

---

## Q3. How is gap_impact described in the prompt/schema — legal direction, practical consequence, use consequence, action priority, or mixed?

| Column | Answer |
|---|---|
| **PROMPT INSTRUCTS** | **Use consequence** — consistently and exclusively. The prompt uses the phrase "for THIS tenant — given their specific use" in the task description and in each value definition. The Materiality definitions similarly ground each level in operational specificity: "Directly affects the tenant's **core business operations**." The rule "Do not give generic lease-risk answers — 'adverse because missing' is not sufficient" explicitly prohibits legal-direction interpretation. |
| **OUTPUTS CONTAIN** | Values from `_VALID_GAP_IMPACT = {favorable, neutral, adverse, context_dependent}` paired with `use_reasoning` that grounds the polarity in business context. The `use_reasoning` field is the in-prompt mechanism for requiring consequence grounding. |

**Proven-claim:** The prompt describes gap_impact as use consequence, not legal direction.  
**Caveat:** The VALUE NAMES (favorable, adverse, neutral) are borrowed from legal direction vocabulary. The distinction between "use consequence" and "generic legal direction" exists only in the definitions — not in the value labels themselves.  
**Still-unmeasured:** Whether n>1 leases with different use profiles produce use_reasoning that genuinely grounds the polarity in use rather than defaulting to generic legal direction.

---

## Q4. Does the schema allow sign-flavored values?

| Column | Answer |
|---|---|
| **PROMPT INSTRUCTS** | The prompt's schema (`lease_use_impact.py:111`) specifies: `"gap_impact": "favorable" | "neutral" | "adverse" | "context_dependent"`. These four values are identical in vocabulary to legal direction polarity words used throughout commercial real estate law ("adverse terms," "favorable clause," "neutral provision"). The prompt REDEFINES them with consequence-oriented definitions, but the VALUE LABELS themselves are sign-flavored. |
| **OUTPUTS CONTAIN** | The model emits these four values (plus `context_dependent` for 1-1-1 governance splits or no-evaluator fallback). The LP-20 instability across 10 replays (neutral×8, adverse×1, context_dependent×1) illustrates that the model navigates these sign-flavored values in the consequence domain. |

**Proven-claim:** The schema allows `{favorable, neutral, adverse, context_dependent}` — sign-flavored vocabulary repurposed as consequence labels.  
**Caveat:** The definitions in the prompt reframe these as consequence values. The schema alone, without prompt context, reads as sign polarity.  
**Still-unmeasured:** Whether the vocabulary overlap causes model drift toward sign-oriented reasoning on edge cases.

---

## Q5. Does any downstream code consume gap_impact AS IF it were sign/direction?

| Consumer | File:Line | What it does | Sign or consequence? |
|---|---|---|---|
| `deriveProvisionRiskLevel` — favorable skip | app.js:5011 | `gap==='favorable'` → return green (no compound risk check triggered) | **Consequence**: favorable consequence = downgrade concern |
| `deriveProvisionRiskLevel` — neutral+low skip | app.js:5014 | `gap==='neutral' && mat==='low'` → amber | **Consequence**: low-materiality neutral consequence = minor concern |
| `deriveProvisionRiskLevel` — review_needed routing | app.js:5056–5063 | `gap==='adverse' && mat==='high'` → red; `gap==='favorable'/'neutral'` → amber | **Consequence**: adverse consequence resolves uncertain-coverage LP to risk level |
| `_isUseImpactFavorable` | app.js:16302 | `gap==='favorable'` → move LP from problems to favorable group | **Consequence**: beneficial consequence removes LP from concern list |
| CSS coloring | app.js:16643–16645 | `gap==='favorable'` → green CSS; `gap==='adverse'` → red CSS | **Closest to sign-like**: uses gap polarity to color Client Impact box green/red. Still grounded in consequence (coloring the consequence display), not asserting generic direction. |
| Sidebar skip | app.js:17718 | `_uiGap==='favorable'` → skip from Needs Attention | **Consequence**: favorable consequence removes from priority list |
| `classifyFindingType` | app.js:18107 | `uiActive && gap==='favorable'` → 'addressed' | **Consequence**: favorable+active 5e = LP is addressed |
| `action_bucket` | _step371_variance.py:30, _step372_decomp.py:36 | `gap==='favorable'` → clean bucket | **Consequence**: mirror of app.js Mode-C logic |

**NO production consumer reads gap_impact as a sign/direction field** — meaning: no code compares gap_impact against Stage 7's `directionality` field, and no code uses gap_impact to answer "is there a generic directional protection gap for tenants."

The CSS coloring (app.js:16643–16645) is the closest case: green for favorable, red for adverse. This is visual polarity, but it's coloring the CONSEQUENCE display (the "Client Impact" block), not asserting generic direction of the underlying provision.

The 375K "sign conflict" (LP-05: 5e=favorable vs Stage 7=adverse) was an **analytical harness observation** comparing two different stage outputs — not a production code misread. No production code path makes this comparison.

**Proven-claim:** Zero production consumers read gap_impact as a sign/direction field. All consumers gate on polarity (favorable/adverse) for consequence-routing purposes.  
**Caveat:** The sign-flavored vocabulary creates analytical confusion when comparing gap_impact against Stage 7 direction values in cross-stage audits (as 375K demonstrated).  
**Still-unmeasured:** Whether future code additions might conflate gap_impact with Stage 7 direction given the shared vocabulary — the vocabulary gap is the risk vector.

---

## Q6. Does any downstream code consume gap_impact AS IF it were materiality/consequence?

YES — ALL production consumers treat gap_impact as the **polarity dimension** of the consequence signal, paired with `materiality` as the **severity dimension**:

| Pattern | Code |
|---|---|
| polarity gate: favorable → downgrade | app.js:5011, 16302, 17718, 18107; _step371:30, _step372:36 |
| polarity + severity: adverse+high → red; adverse+medium → amber | app.js:5056–5058 |
| polarity + severity: neutral+low → amber | app.js:5014 |
| polarity for display color | app.js:16643–16645 |

The comment at app.js:18080 makes this explicit: `"Consequence tier (UNCHANGED — use_impact.materiality + partial_class + gap_impact)"`.

**Proven-claim:** Every production consumer treats gap_impact as consequence (polarity dimension). Combined with `materiality` (severity dimension), they form a joint consequence routing signal.  
**Caveat:** None specific to Q6. This is consistent and unambiguous across all consumers.  
**Still-unmeasured:** N/A.

---

## Q7. Are materiality and gap_impact separable or entangled?

**DISTINCT FIELDS, DISTINCT VALUE SETS:**

| Field | Value set | Semantic role |
|---|---|---|
| `gap_impact` | {favorable, neutral, adverse, context_dependent} | Polarity of consequence (direction of effect on tenant) |
| `materiality` | {high, medium, low, not_applicable} | Severity of consequence (magnitude of effect on tenant) |

They're used JOINTLY in routing (adverse+high → red; adverse+medium → amber; favorable → green regardless of materiality) but are NOT interchangeable. Neither stands in for the other.

The routing logic is: `gap_impact` is the gate (favorable → stop, downgrade; adverse → continue to materiality tier). `materiality` is the severity tier once the gate passes. Together they define consequence priority, not two independent signals.

**Proven-claim:** gap_impact (polarity) and materiality (severity) are distinct fields with distinct value sets, used jointly as a two-dimensional consequence signal. Neither stands in for the other.  
**Caveat:** gap_impact='favorable' overrides materiality entirely in routing (favorable+high → green, not red). So polarity is dominant when favorable; severity matters only when polarity is adverse or neutral.  
**Still-unmeasured:** N/A.

---

## Q8. Split, rename, or interpretation cleanup?

Given Q1–Q7:

| Q | Finding |
|---|---|
| Q1–Q2 | Prompt: consequence-only, unambiguous |
| Q3 | Schema/prompt description: use consequence |
| Q4 | Value set: sign-flavored vocabulary, consequence-defined |
| Q5 | Consumers: NONE read as sign/direction |
| Q6 | Consumers: ALL read as consequence |
| Q7 | gap_impact and materiality: separable, jointly used as consequence signal |

**Recommendation: RENAME only. No split needed. No consumer repair needed.**

The field is a **clean consequence field** (Finding A). The problem is vocabulary: `gap_impact` with values `favorable/adverse/neutral` uses legal direction language to describe use consequence. The naming is the confusion vector — not the prompt, not the consumers.

Fix:
- Rename `gap_impact` → `use_consequence` — unambiguously consequence
- Optionally revise values: `beneficial | harmful | neutral | context_dependent` (eliminates vocabulary overlap with sign/direction language)
- No consumer repair required (all consumers already treat it as consequence)
- This makes LP-05 expressible without analytical confusion: `use_consequence=beneficial` vs Stage 7 `directionality=tenant_unprotected` — clearly two different things, not a "conflict"

---

## Forced Finding

**FINDING A — clean consequence field.**

**Evidence that picks Finding A over B, C, and D:**

1. **Against B (overloaded hybrid):** The prompt does NOT explicitly ask for both sign and consequence in one field. The LP-05 example embedded in the prompt is the clearest anti-B evidence: it instructs the model that an absent provision = favorable consequence, which CONTRADICTS what a sign question would produce (absent provision = adverse sign). A prompt asking for sign would never embed this example.

2. **Against C (prompt consequence-only but code treats as sign):** Q5 shows zero production consumers read gap_impact as sign. All consumers gate on polarity for consequence-routing purposes (favorable → downgrade concern, adverse → add concern). The 375K "sign conflict" was an analytical observation comparing fields across stages, not a code-level misread.

3. **Against D (ambiguous prompt):** The prompt is not ambiguous. The task description, value definitions, and the LP-05 embedded example all consistently define the question as use-consequence. "Do not give generic lease-risk answers" is an explicit anti-ambiguity rule.

4. **For A:** Q1 (consequence question asked) + Q2 (sign question NOT asked) + Q5 (no sign-reading consumers) + Q6 (all consequence consumers) → clean consequence field, misnamed.

**B vs C pivot (as required by spec):** B vs C is decided by Q1/Q2 — what the prompt instructs. Q1/Q2 are unambiguous: consequence-only, no sign instruction. Finding B requires the prompt to EXPLICITLY ask for both; it does not. Finding C requires that downstream code treats it as sign; Q5 shows no code does. Therefore neither B nor C; Finding A.

**Fix for 375E-COV:**
- Rename `gap_impact` → `use_consequence` in: `lease_use_impact.py` (field definition, prompt return instruction, merge logic), `app.js` (all 8 consumers), `_step371_variance.py`, `_step372_decomp.py`
- Optionally rename values to `{beneficial, harmful, neutral, context_dependent}` (eliminates vocabulary overlap with Stage 7 direction)
- No split of the field required — it is already a pure consequence field
- Add `use_consequence_source` provenance field per 375E-COV spec (assessed | defaulted_floor | not_eligible | absent)

**Note on recommended contract from spec:** Because the finding is A (not B or D), the full split contract from the spec is NOT required. The LP-05 situation is expressible without a fake conflict once the field is renamed: Stage 7 `directionality=tenant_unprotected` (generic directional gap) + 5e `use_consequence=beneficial` (consequence for this warehouse tenant) → these are two different measurements, not a conflict. The axis_conflict schema element from the spec would only be needed if the prompt itself asked for both sign and consequence (Finding B). Under Finding A, the fix is vocabulary cleanup, not schema surgery.

---

## Doctrine update (for 375E-COV spec)

375L confirms what 375K diagnosed: LP-05 is NOT a sign conflict — it is a vocabulary artifact. Stage 7 answers "is there a directional protection gap generically?" (yes → adverse). Stage 5e answers "does that gap harm THIS tenant?" (no → beneficial for warehouse operator). Two correct answers to two different questions. The confusion arose because `gap_impact` used `favorable/adverse` vocabulary (sign-flavored) for a consequence answer.

The fix is rename, not redesign. Once `gap_impact` becomes `use_consequence` with values `{beneficial, harmful, neutral, context_dependent}`, the LP-05 outputs are: Stage 7 direction = adverse (gap exists generically) + Stage 5e use_consequence = beneficial (gap helps this tenant) → favorable position, not Risk. No conflict. No split schema required.
