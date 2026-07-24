# Step 441 (line-ending / "441le") — line-ending determinism + committed-blob token derivation — CODE STATUS

**Numbering note:** the user labeled this "STEP 441", but `441_code_status.md` was already taken by the
earlier "440-reconcile" finding. Filed as `441le_*` to avoid clobbering that. The instruction for this
step is `build_log/441_chat_instruction.md` (committed with the code).

**Status:** COMPLETE (build-only; ZERO provider calls). The token is now **reproducible from the
repository's committed Git blobs** (verified post-commit), a runtime gate enforces it, and the change
is proven **newline-only** for the reviewed artifacts. No mechanism/semantic change. Fresh token
`541989ef…` supersedes `8d14543a` (retained as historical, machine-local evidence only). STOP for
scoped delta audit.

---

## 1. Path-scoped line-ending policy (`.gitattributes`, repo root)
`eol=lf` pinned for the 7 Step-431 package files ONLY. Whole repo NOT renormalized. After
renormalizing the package working-tree files CRLF→LF, **each file's working-tree bytes now equal its
committed blob bytes** (config `7000ad8f`, profiles `57f8a22a`, schema `a9724730`, prompt `3a146f41`,
preflight `080eb3ed`). The committed blobs were ALREADY LF (autocrlf); only the working tree + the
manifest's recorded hashes changed — the 5 semantic-artifact blobs are byte-unchanged from `f9048ed`.

## 2. Manifest/token derived from committed bytes — REPRODUCIBLE (post-commit `HEAD`=`2ee8144`)
`sha256_lf()` (LF-normalized = committed-blob bytes) replaces `sha256_file()`; all generated files use
`write_lf()` (LF). Manifest binds per-artifact `git_path` + `committed_blob_sha256`, `head_at_build_time`,
`line_ending_policy`, self-hash/token.
```
sha256(HEAD:build_log/<artifact>) for all 6  -> each == manifest.artifact_hashes[name]  (MATCH x6)
recomputed self-hash of committed blobs : 541989ef06213907716d2a613a26465f9571dd1e9e8c0d516b0405117f985a93
manifest token                          : 541989ef06213907716d2a613a26465f9571dd1e9e8c0d516b0405117f985a93
TOKEN REPRODUCIBLE FROM COMMITTED BLOBS  : True
```

## 3. Runtime blob-equality gate (`verify_repository_execution_identity`, before the first call)
HALTS unless `working-tree LF sha256 == manifest.committed_blob_sha256 == sha256(HEAD:git_path)` for
every artifact, the package tree is clean, no CRLF remains, and paths resolve inside the repo. Wired at
the top of `run_stage2` before `build_sources`/seam/first call. **Post-commit the gate PASSES**
(`all_artifacts_verified=True`, 6 artifacts, `HEAD=2ee8144`).

**Flagged deviation (logical impossibility):** Part 3's literal "HEAD equals the manifest's pinned
commit" is unenforceable — a manifest cannot contain the SHA of its own containing commit. The enforced
guarantee is instead `sha256(HEAD:git_path) == committed_blob_sha256 == working-tree-LF` per artifact
(content-addressed, stronger than a commit label). `head_at_build_time`/`head_matches_package_commit`
(=False) are provenance only, never halt conditions.

## 4. Newline-only equivalence (semantic reviews carry forward) — per artifact
`[JSON] config/profiles/schema/preflight: parsed objects identical; bytes differ ONLY by CRLF→LF` ·
`[prompt] content unchanged apart from carriage returns` · `[harness] CRLF→LF is AST-identical`
(the harness's intentional 441 functional edits are separately audited via the committed diff). No
requirement/fixture/config value or model-facing character other than `\r` changed.

## 5. Provenance record (exact GPT wording) — EMITTED in report `## Provenance` + manifest metadata
Both verbatim sentences are in the report renderer and the manifest
(`_provenance_line_ending_correction`, `_provenance_committed_blob_identity`).

## 6. No mechanism/semantic change
FIX 1a, 434 message-halt, terminal-fatal machinery, F2, corrected Role-C §9 language — ALL UNCHANGED
(439 assembled 6/6 + 432 orchestration 6/6 re-pass).

## 7. Tests — PASS, zero provider calls
Build gate 4/4 (0 calls) · 441 Part-4 + gate 8/8 (incl. post-commit gate PASS) · 439 assembled 6/6 ·
432 orchestration 6/6.

## 8. Token + chain + files
- **NEW token:** `541989ef06213907716d2a613a26465f9571dd1e9e8c0d516b0405117f985a93` (committed-blob
  derived, repository-reproducible).
- Chain: `47cb312a → 833fd43e → 9c2cc8e1 → 48054981 → ce284b55 → 8d14543a → 541989ef`; `8d14543a`
  recorded UNSANCTIONED / historical-machine-local-evidence-only.
- Files changed (blob level): `.gitattributes` (new), `run_431_selection_measurement.py`,
  `431_config_manifest.json` (+ 441 docs). 5 semantic blobs unchanged.
- `git status --porcelain cam/` empty; no `cam/` edit. Commit `2ee8144`; this status in a follow-up
  commit. Not pushed. STOP for scoped delta audit.
