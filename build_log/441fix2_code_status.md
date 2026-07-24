# Step 441-fix2 — Construction A / Option 3 (commit binding out of the package manifest) — CODE STATUS

**Status:** PARTIAL — the code rework + committed package **P** + fresh blob-anchored token are
COMPLETE and verified; the **load-bearing signed sanction tag** and the **legibility record Q** are
deferred to Tzvi because this environment has **no signing key** and, by design, the tag signature
IS Tzvi's sanction act. All work below is zero-provider-call.

Package commit **P = `c9f6dd7f6db7899e729b5f6f6407398a64f41d65`**.
Fresh token **T = `0b98c6fa3a3cf098d243fd90573cda582482c00bf5c6723a4e76a975d5e89164`**
(supersedes `541989ef…`).

---

## Root-cause correction (Rule 6 — used everywhere)
The Step-441 defect was **NOT** "manifest contains its own SHA / `pinned_commit=C`." The committed
441 bytes never contained `pinned_commit`. The actual defect: the manifest stored the **PARENT**
commit (`f9048ed`) as `head_at_build_time`, and the runtime `head == head_at_build_time` check is
**structurally ALWAYS-FALSE** once the containing commit exists (run-time HEAD is the containing
commit, not the parent). A manifest inside commit C cannot name C. This wording is used in the
manifest provenance, the commit message, and here.

## What changed (all in `build_log/`, zero `cam/` edits)
1. **Manifest (`431_config_manifest.json`)** — removed `head_at_build_time` + its note; added
   `_commit_binding` (`commit_sha_in_this_manifest: null`) documenting Construction A. Manifest now
   carries **no run/containing-commit SHA**. (Historical doc refs `authorizing_instruction.commit`
   `38785e7` and `supersedes.prior_build_commit` `5954e6e` are provenance of the *brief* and the
   *prior build*, not the run-commit binding — unchanged from 441.)
2. **Harness (`run_431_selection_measurement.py`)** —
   - `verify_repository_execution_identity()` reworked: (a) unchanged load-bearing **content**
     gate (per artifact `working-tree-LF == committed_blob_sha256 == sha256(HEAD:path)`, tree
     clean, LF pin, path inside repo); (b) NEW **Construction-A invariant guard** — HALTS if the
     manifest carries any of `head_at_build_time`/`pinned_commit`/`package_commit`/`containing_commit`;
     (c) NEW **commit binding** read from an external signed tag via `verify_signed_sanction_binding()`.
   - `verify_signed_sanction_binding(head, token)` (new): requires exactly one **annotated** tag
     pointing at HEAD whose **signature verifies** (`git tag -v`), whose **peeled target == HEAD**,
     and whose embedded **`token:` == manifest token**; else HALT. Commit identity comes from the
     TAG, never the manifest.
   - Manifest generation: removed the `git rev-parse HEAD` that fed the parent-proxy field.
   - `run_stage2` call-site print updated (no longer references the removed
     `head_matches_package_commit`).
3. **Instruction (`441fix2_chat_instruction.md`)** — verbatim brief (both messages) filed per Rule 7.

## Tests — RUN, actual output (zero provider calls)
- **Build (`--mode build`)**: `MODEL CALLS MADE: 0`. Build gate **4/4** relationship tests PASS
  (`a_combined_opex_taxes` match; `b_sibling_tax_candidate` mismatch; `c_comention_no_linkage`
  mismatch; `d_ungrounded_linkage` undeterminable). Wiring check: call path implemented, 7 payloads
  built, §5 leak-checks 7/7, **PROVIDER CALLS MADE: 0**. `cam/ clean: True`.
- **Token reproducible from P's committed blobs**: recomputed `sha256(json.dumps(hashes,sort_keys))`
  over `git show c9f6dd7:<path>` (CRLF→LF) for all 6 artifacts →
  `0b98c6fa3a3cf098d243fd90573cda582482c00bf5c6723a4e76a975d5e89164` == manifest token. **True.**
  Harness committed-blob hash `30f10e3a…` (was `e4f98484…` in 441).
- **Content identity at HEAD=P**: all 6 artifacts `working-tree-LF == committed_blob == sha256(HEAD:path)
  == artifact_hashes`. Equal. **True.**
- **Gate HALTs on missing signed tag** (correct pre-sanction state): `verify_repository_execution_identity`
  raised `MeasurementIntegrityHalt` — "the run-commit is NOT bound … by a valid signed sanction tag …
  points at HEAD (c9f6dd7f6db7) and embeds this manifest token (0b98c6fa3a3c). Valid tags found: 0."
- **Invariant guard fires**: injecting `head_at_build_time` into the manifest → HALT
  ("package manifest carries a self-referential commit field 'head_at_build_time'").
- **Semantic artifacts**: `git diff 65556ee c9f6dd7 -- <5 semantic paths>` = **empty** (byte-identical).

## No mechanism/semantic change
FIX 1a, 434 message-halt, `run_stage2` terminal-fatal machinery, F2, corrected Role-C §9 language —
UNCHANGED (untouched code paths). Only the manifest commit field + the runtime gate's commit-binding
were reworked; the content gate is byte-for-byte the same logic.

## DEFERRED to Tzvi (named, at the top per Rule 5) — the load-bearing signature
No signing key exists here (`git config gpg.format`/`user.signingkey` empty; gpg has zero secret
keys) and the signature is Tzvi's sanction act. Until a valid signed tag points at P embedding T,
the runtime **correctly HALTS** — the package is built but unsanctioned, which is the intended state.
- **Step 3 (signed tag):** Tzvi runs `git tag -s <name> <P>` with the body specified in the handoff.
- **Step 4 (record Q):** authored AFTER the signed tag exists (it must record the tag object ID),
  in a later commit — not written now, because writing a "sanction record" before the sanction
  occurred would be false.

## Git
- Commit **P = `c9f6dd7`** (this status filed in a follow-up commit). `git add -f` explicit paths.
- `git status --porcelain cam/` → empty. No `cam/` file edited.
- **NOT pushed.** STOP for delta audit.
