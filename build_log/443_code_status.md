# Step 443 — Close the manifest-trust bypass — CODE STATUS

**Status:** COMPLETE. Both commits made. ZERO model calls, no tag created, no signing, not pushed.

- **P″ (package) = `b05b735ae9014386ba330092cbcdf52601d735a4`**
- **T″ (token) = `bb1c40b1e37a0d14d865c48526724c04184a00d0c18ebde8126733df4697c477`** (same nine artifacts)
- **Q-prep″ = the commit containing this file**
- **Exact sanction message SHA-256 = `84e6aab4b5c9bdf507645956cc151f352d3bb512c50d3a5a7cd7a436b6105eb0`**
- Prior message `3de7329c…` (P′ `3fb5f39`, token `8389e965`) marked **OBSOLETE — never signed.**

## The bypass, confirmed
GPT's flag was correct. `run_stage2` read the manifest from the **working tree** and passed it to the
gate, which enumerated artifacts from `committed_blob_binding`. The manifest thus defined its own
verification scope: deleting the harness entry while keeping the token field shrank the checked set,
so a **modified harness could execute under a valid signed tag**.

## Fix (all five required items)
| Required | Implemented |
|---|---|
| 1. HEAD manifest authoritative | `load_head_manifest()` reads `HEAD:build_log/431_config_manifest.json`. |
| 2. Working-tree copy must equal it (prefer HEAD-only) | **Both**: only the HEAD blob is consumed, *and* the working-tree copy must be byte-identical (LF-normalized) or halt. |
| 3. Fixed nine-artifact set hardcoded | `EXPECTED_PACKAGE_ARTIFACTS` (names **and** git paths) in the harness; shrunken/extended/re-pointed bindings halt. |
| 4. Recompute token from HEAD blobs | `recompute_token_from_head()`; recorded hashes are claims checked against it, never inputs. |
| 5. Four-way token equality | recomputed == committed-manifest == `--stage2-sanction` == signed-tag body; any inequality halts pre-call. |

Also hardened: `_assert_stage2` and the per-call `reviewed_config_hash` now derive from committed
blobs instead of the working-tree manifest.

## Negative tests — 9 run, 9 HALT pre-call (full output in the evidence file)
(a) working-tree manifest differs from HEAD blob · (b) harness entry removed from binding ·
(c) artifact added · (d) artifact omitted · (e) manifest artifact hash altered · (f) stale token
field · **(f2)** `--stage2-sanction` ≠ recomputed token, pristine tree · **(f3)** signed tag embeds a
stale token (real comparison logic, only tag primitives stubbed) · **(g) THE BYPASS**: harness
modified on disk **and** its binding entry removed **and** tag verification stubbed to SUCCEED —
still halts on the hardcoded-scope check.

(f2) and (f3) were added because (f)'s halt came from the dirty-tree check rather than the token
comparison; they isolate the four-way equality at the CLI and tag comparison points respectively.

## Mechanism-unchanged evidence — measured, not asserted
Per-region SHA-256 of the harness at `3fb5f39` (442) vs `b05b735` (443), extracted by AST name:
**IDENTICAL (11/13):** 434 config-integrity classifier · `certify` (F2) · `build_panelist_payload`
(F2) · `_provider_call` · `run_candidate_series` · `certify_parameter_series` · `render_report`
(**Role-C language**) · `merge_panel` · `_basis_rule` · `apply_field_grounding` · `compare_candidate`.

**DIFFERS (2/13), with scoped diffs in the evidence file:**
- `run_stage2` — only the gate invocation and the `config_hash` source changed (that is where the
  bypass lived). The FIX 1a `except (FatalProviderError, MeasurementIntegrityHalt)` terminal record
  and the `finally` seam/partial-sidecar closure are untouched; the diff shows a single hunk.
- `call_panelist` — one statement: `reviewed_config_hash` now reads the committed HEAD manifest
  instead of the working-tree file. 6 changed lines, no behavioural change to the call path.

**Correction (Rule 6):** the builder note committed inside P″ (`443_chat_instruction.md`) names only
`run_stage2` as the region that would change. `call_panelist` also changed, for the same reason. The
note is incomplete on that point; this status file and the evidence file are authoritative.

## Other constraints
- Five reviewed semantic artifacts **byte-identical to 65556ee** (empty diff).
- Manifest carries **no commit SHA** (`_commit_binding.commit_sha_in_this_manifest = null`).
- 442 committed trust anchor + explicit key enforcement **preserved unchanged**.
- Build gate 4/4, wiring 7/7 leak-checks, `PROVIDER CALLS MADE: 0`, `MODEL CALLS MADE: 0`.
- `git status --porcelain cam/` empty. No `cam/` file edited. **NOT pushed.** No tag created or signed.
