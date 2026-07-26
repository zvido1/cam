# Step 431 Part B — Governed Evidence-Selection Measurement — Report (§9)

- config_hash: `ef1a7af7f77d0999648bc39fa6b367a68d31d09470be699ee25555137cc511ca`
- admitted candidates: ['cand_01', 'cand_02', 'cand_03', 'cand_04', 'cand_05', 'cand_06', 'cand_07']
- completeness: not_established (no terminal `unsatisfied_*` may be emitted, §8.3)

## Provenance — line-ending correction and committed-blob identity (Step 441)

Tokens generated before the line-ending correction were derived from Windows working-tree bytes under core.autocrlf=true. They remain evidence of local sanction-to-execution drift gating on that checkout, but they are not independently reproducible from the repository's LF-normalized Git blobs.

Beginning with this package, artifact identity is derived from committed Git-blob bytes under path-pinned LF line endings. Runtime preflight verifies that the executed working-tree bytes exactly equal the pinned committed blobs and that the repository commit matches the manifest.

## §9 Panel integrity — adapter-level config-integrity asymmetry

All three canonical adapters invoke `_check_generation_integrity` on the real outbound payload (Anthropic, OpenAI, xAI). Fatal propagation is NOT uniform: Anthropic (role A) and xAI (role C) propagate `FatalProviderError` typed; OpenAI (role B) WRAPS its integrity fatal into a generic `ProviderError` (message preserved). The harness halts on a fatal via the exception type for A/C and via the `config_integrity_violation` message-match for the OpenAI-wrapped case; either way a config-integrity violation aborts the whole run (§11), never degrades to a fallback. The only adapter WITHOUT the integrity assertion is Google, used solely as a degraded pool fallback (never a canonical role).

### Role C (grok-4.3) — shared integrity checking and structurally inapplicable omission branch

Role C (`grok-4.3`, canonical self-retry role) invokes the shared module-level outbound generation-integrity check and records the resulting integrity metadata. Its configured temperature is transmitted explicitly as `0`, and the xAI call path re-raises fatal integrity failures. Grok is outside `TEMPERATURE_ONLY_DEFAULT_MODELS`, so the conditional-temperature-omission branch is structurally inapplicable to Role C.

**Claim bound:** a `satisfied` result on a parameter whose certification depends on a canonical Role-C panel is certified under a Role-C call whose transmitted config is recorded (`adapter.last_integrity`) AND cannot drift (temperature=0 by construction) — there is no unguarded-drift exposure to caveat.

## §9.1 / §9.2 per-parameter results

- tenant_share (atreca), series 1: satisfied (completeness: not_established)
- tenant_share (atreca), series 2: satisfied (completeness: not_established)
- tenant_share (atreca), series 3: review_needed_disagreement (completeness: not_established)
- tenant_share (atreca), series 4: satisfied (completeness: not_established)
- tenant_share (atreca), series 5: satisfied (completeness: not_established)
- base_rent (atreca), series 1: satisfied (completeness: not_established)
- base_rent (atreca), series 2: satisfied (completeness: not_established)
- base_rent (atreca), series 3: satisfied (completeness: not_established)
- base_rent (atreca), series 4: satisfied (completeness: not_established)
- base_rent (atreca), series 5: satisfied (completeness: not_established)
- rent_adjustment_pct (atreca), series 1: review_needed_disagreement (completeness: not_established)
- rent_adjustment_pct (atreca), series 2: review_needed_disagreement (completeness: not_established)
- rent_adjustment_pct (atreca), series 3: review_needed_disagreement (completeness: not_established)
- rent_adjustment_pct (atreca), series 4: review_needed_disagreement (completeness: not_established)
- rent_adjustment_pct (atreca), series 5: review_needed_disagreement (completeness: not_established)
- tenant_share (atlas), series 1: review_needed_disagreement (completeness: not_established)
- tenant_share (atlas), series 2: review_needed_disagreement (completeness: not_established)
- tenant_share (atlas), series 3: review_needed_disagreement (completeness: not_established)
- tenant_share (atlas), series 4: review_needed_disagreement (completeness: not_established)
- tenant_share (atlas), series 5: review_needed_disagreement (completeness: not_established)
- base_rent (atlas), series 1: satisfied (completeness: not_established)
- base_rent (atlas), series 2: satisfied (completeness: not_established)
- base_rent (atlas), series 3: satisfied (completeness: not_established)
- base_rent (atlas), series 4: satisfied (completeness: not_established)
- base_rent (atlas), series 5: satisfied (completeness: not_established)
- rent_adjustment_pct (atlas), series 1: review_needed_no_qualifying_candidate (completeness: not_established)
- rent_adjustment_pct (atlas), series 2: review_needed_no_qualifying_candidate (completeness: not_established)
- rent_adjustment_pct (atlas), series 3: review_needed_no_qualifying_candidate (completeness: not_established)
- rent_adjustment_pct (atlas), series 4: review_needed_no_qualifying_candidate (completeness: not_established)
- rent_adjustment_pct (atlas), series 5: review_needed_no_qualifying_candidate (completeness: not_established)
