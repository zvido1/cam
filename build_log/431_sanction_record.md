# 431 Stage-2 Sanction — Q-prep record (exact unsigned message)

**Provenance only.** This file and the message it describes are NOT hashed into the package token and
are NOT read by the runtime gate. They exist so the exact bytes Tzvi will sign are fixed and
auditable before any signature exists.

Created in a commit AFTER the package commit, which is why it can name that commit without
self-reference.

## Bound facts (current)
- **Package commit P‴:** `6a32d47fde64147a0987ce76027e968f3fcb8396`
- **Token T‴ / manifest self-hash:** `f341a1886973bfec6d2e1f776b81fec29e16bdf7a3f1f2740f10aab876d7d352`
- **Authorized principal:** `zvido@yahoo.com`
- **Authorized key fingerprint:** `SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs`
- **Allowed namespace:** `git`

## Exact message
- **Path:** `build_log/431_sanction_message.txt` (pure ASCII, LF, LF-pinned)
- **SHA-256 of the exact bytes:** **`56bce9e915ef56361f5a166e71a78763bbcd2babc9b1f8d341f62f75c51560be`**
- **These bytes must not change between audit and signing.** If they change, the tag body will no
  longer match the recomputed token / policy and the runtime gate will reject the tag.

It names: package commit P‴, token T‴, manifest self-hash, all **nine** artifact committed-blob
SHA-256 values, the authorized principal, the authorized key fingerprint, and the authorization
statement "Stage 2 authorized only for this exact package at commit
6a32d47fde64147a0987ce76027e968f3fcb8396."

## OBSOLETE prior messages — DO NOT SIGN
Two superseded messages exist in this file's history. **Neither was ever signed.**

| SHA-256 | named package commit | token | why obsolete |
|---|---|---|---|
| `3de7329cfcb62e9c7a4da9f267f6c4b73df88ba9969c0477343811aa5f11b931` | `3fb5f39` (442) | `8389e965…` | its runtime permitted the manifest-trust bypass (the working-tree manifest decided what was verified) |
| `84e6aab4b5c9bdf507645956cc151f352d3bb512c50d3a5a7cd7a436b6105eb0` | `b05b735` (443) | `bb1c40b1…` | its runtime verified the nine package artifacts but not the repository-local modules the harness imports, so a modified `cam/core/*` still executed |

Signing either would sanction a package whose gate can be circumvented. The message file was
replaced in place at this path; those bytes survive only in the history of that file.

Signing history to date: **no sanction tag has ever been created or signed in this repository.**

## Status
**UNSIGNED. No tag exists.** No tag was created in Step 443. The runtime gate HALTS until an
annotated tag signed by the authorized key points at P‴ and satisfies every check.

## Execution environment (Step 444 — REQUIRED)
The gate halts unless `git status --porcelain --untracked-files=all` is EMPTY over the WHOLE
repository, because the harness imports repository-local modules (`cam/core/provider_router.py` and
its transitive imports) from the tree it runs in. A normal developer checkout will NOT satisfy this.
The sanctioned run therefore executes from a dedicated detached worktree at the package commit:

    git worktree add --detach <path> 6a32d47fde64147a0987ce76027e968f3fcb8396

`CAM_ROOT` is derived from the harness file's own location, so git inspection, `sys.path` and
artifact reads all resolve to that worktree.

**KNOWN GAP — an input is outside version control.** `.gitignore:51` ignores
`05 Lease Analyzer/test_data/`. The atreca lease is tracked; `atlas_meridian_warehouse_lease.txt`
is NOT tracked and IS ignored, so a fresh worktree does not contain it (verified: absent in a
worktree created at the package commit) and the run fails in preflight until it is materialized
there. `FROZEN_LEASE_HASHES` still guards content, so the exposure is a FAILED run, not a false
result. Ignored files do not appear in `--untracked-files=all`, so copying the fixture in does not
break the cleanliness check. Awaiting a ruling: track the fixtures, or accept out-of-band inputs
with hash pinning.

## Applying the sanction (Tzvi, after CLEAR — requires the passphrase-protected sanction key)
1. Create a dedicated detached worktree at P‴ (see above) and work there.
2. Load the sanction private key into ssh-agent.
3. Sign the exact message as an annotated tag on P‴:
   `git -c gpg.format=ssh -c user.signingkey=<sanction key> tag -s -F build_log/431_sanction_message.txt --cleanup=verbatim stage2-sanction-431-f341a188 6a32d47fde64147a0987ce76027e968f3fcb8396`
4. Verify against the COMMITTED anchor (not ambient config):
   `git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=build_log/431_sanction_allowed_signers tag -v stage2-sanction-431-f341a188`
5. The runtime gate then independently re-verifies before any provider call: hardcoded nine-artifact
   scope, manifest read from HEAD (working-tree copy byte-identical), per-artifact three-way blob
   equality, clean tree, token recomputed from the nine HEAD blobs, four-way token equality
   (recomputed == committed manifest == `--stage2-sanction` == signed-tag body), and the tag verified
   against the one-key anchor materialized from the committed HEAD blob.

`--cleanup=verbatim` matters: any whitespace normalization of the message changes the bytes and
therefore the recorded SHA-256.
