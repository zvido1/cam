# 431 Stage-2 Sanction — Q-prep record (exact unsigned message)

**Provenance only.** This file and the message it describes are NOT hashed into the package token and
are NOT read by the runtime gate. They exist so the exact bytes Tzvi will sign are fixed and
auditable before any signature exists.

Created in a commit AFTER the package commit, which is why it can name that commit without
self-reference.

## Bound facts (current)
- **Package commit P4:** `d679eec8525fa672724a012f7d1fac0d0d8e7620`
- **Token T4 / manifest self-hash:** `ef1a7af7f77d0999648bc39fa6b367a68d31d09470be699ee25555137cc511ca`
- **Authorized principal:** `zvido@yahoo.com`
- **Authorized key fingerprint:** `SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs`
- **Allowed namespace:** `git`

## Exact message
- **Path:** `build_log/431_sanction_message.txt` (pure ASCII, LF, LF-pinned)
- **SHA-256 of the exact bytes:** **`685d9dfe60cd9de5f808803ddee5507e8d6e15f1109f78c0b79de1a4c7674ec6`**
- **These bytes must not change between audit and signing.** If they change, the tag body will no
  longer match the recomputed token / policy and the runtime gate will reject the tag.

It names: package commit P4, token T4, manifest self-hash, all **eleven** artifact committed-blob
SHA-256 values, the authorized principal, the authorized key fingerprint, and the authorization
statement "Stage 2 authorized only for this exact package at commit
d679eec8525fa672724a012f7d1fac0d0d8e7620."

## OBSOLETE prior messages — DO NOT SIGN
Two superseded messages exist in this file's history. **Neither was ever signed.**

| SHA-256 | named package commit | token | why obsolete |
|---|---|---|---|
| `3de7329cfcb62e9c7a4da9f267f6c4b73df88ba9969c0477343811aa5f11b931` | `3fb5f39` (442) | `8389e965…` | its runtime permitted the manifest-trust bypass (the working-tree manifest decided what was verified) |
| `84e6aab4b5c9bdf507645956cc151f352d3bb512c50d3a5a7cd7a436b6105eb0` | `b05b735` (443) | `bb1c40b1…` | its runtime verified the nine package artifacts but not the repository-local modules the harness imports, so a modified `cam/core/*` still executed |
| `56bce9e915ef56361f5a166e71a78763bbcd2babc9b1f8d341f62f75c51560be` | `6a32d47` (444) | `f341a188…` | its package did not include the lease fixtures: `atlas_meridian_warehouse_lease.txt` was untracked, so a fresh worktree at that commit lacked an input the measurement reads |

Signing either would sanction a package whose gate can be circumvented. The message file was
replaced in place at this path; those bytes survive only in the history of that file.

Signing history to date: **no sanction tag has ever been created or signed in this repository.**

## Status
**UNSIGNED. No tag exists.** No tag was created in Step 443. The runtime gate HALTS until an
annotated tag signed by the authorized key points at P4 and satisfies every check.

## Execution environment (Step 444 — REQUIRED)
The gate halts unless `git status --porcelain --untracked-files=all` is EMPTY over the WHOLE
repository, because the harness imports repository-local modules (`cam/core/provider_router.py` and
its transitive imports) from the tree it runs in. A normal developer checkout will NOT satisfy this.
The sanctioned run therefore executes from a dedicated detached worktree at the package commit:

    git worktree add --detach <path> d679eec8525fa672724a012f7d1fac0d0d8e7620

`CAM_ROOT` is derived from the harness file's own location, so git inspection, `sys.path` and
artifact reads all resolve to that worktree.

**Input fixtures are now IN the package (Step 445 — the 444 gap is closed).** Both lease fixtures
are force-added to version control (the enclosing `05 Lease Analyzer/test_data/` stays gitignored),
pinned `text eol=lf`, and bound into the token and the runtime three-way blob equality — the artifact
set is **eleven**. Verified in a fresh detached worktree at the package commit: both leases present,
preflight admits 7/7, and both `source_document_hash` values equal the `FROZEN_LEASE_HASHES` pinned
at Step 430. The fixtures' reviewed content did not change: `source_document_hash` is invariant under
CRLF→LF normalization.

## Applying the sanction (Tzvi, after CLEAR — requires the passphrase-protected sanction key)
1. Create a dedicated detached worktree at P4 (see above) and work there.
2. Load the sanction private key into ssh-agent.
3. Sign the exact message as an annotated tag on P4:
   `git -c gpg.format=ssh -c user.signingkey=<sanction key> tag -s -F build_log/431_sanction_message.txt --cleanup=verbatim stage2-sanction-431-ef1a7af7 d679eec8525fa672724a012f7d1fac0d0d8e7620`
4. Verify against the COMMITTED anchor (not ambient config):
   `git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=build_log/431_sanction_allowed_signers tag -v stage2-sanction-431-ef1a7af7`
5. The runtime gate then independently re-verifies before any provider call: hardcoded nine-artifact
   scope, manifest read from HEAD (working-tree copy byte-identical), per-artifact three-way blob
   equality, clean tree, token recomputed from the nine HEAD blobs, four-way token equality
   (recomputed == committed manifest == `--stage2-sanction` == signed-tag body), and the tag verified
   against the one-key anchor materialized from the committed HEAD blob.

`--cleanup=verbatim` matters: any whitespace normalization of the message changes the bytes and
therefore the recorded SHA-256.
