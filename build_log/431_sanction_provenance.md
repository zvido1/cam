# 431 Stage-2 Sanction — Provenance & Verification Record (Step 441-fix3)

Governs how the Step-431 executable package (commit **P = `c9f6dd7f6db7899e729b5f6f6407398a64f41d65`**,
token **T = `0b98c6fa3a3cf098d243fd90573cda582482c00bf5c6723a4e76a975d5e89164`**) is bound to a
sanction. Construction A / Option 3: the package manifest carries NO commit SHA; the run-commit↔token
binding lives in an EXTERNAL signed annotated tag verified against a dedicated sanction key.

## 1. Dedicated sanction key (verification side only)
- Public key: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHY5xKgVPjN04b8tyau0cN8VhMFawgt/JKjrMGmdDDBk CAM sanction key`
- SHA-256 fingerprint: `SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs` (independently recomputed
  from the public-key blob: **MATCH**).
- Authorized principal: `zvido@yahoo.com`.
- Private key: created and retained by Tzvi, passphrase-protected. **Never generated, read, copied, or
  invoked by Claude Code.**

Verification configured (this repo, machine-local `.git/config`; verification only — no signing):
- `gpg.format = ssh`
- `gpg.ssh.allowedSignersFile = C:/Users/Owner/OneDrive/CAM/build_log/431_sanction_allowed_signers`
- `user.signingkey` = **empty** (deliberately — this checkout cannot sign; the signature is Tzvi's act).
- Allowed-signers file (committed): pairs `zvido@yahoo.com` (namespaces="git") with the sanction
  public key above.

## 2. Premature-tag withdrawal (standing declaration)
Verbatim withdrawal statement (per brief):

> "A signed tag was created before completion of the final delta audit using the ordinary SSH access
> key (id_ed25519) and containing unconditional authorization language. It is withdrawn and
> non-operative. It did not authorize execution, no model calls occurred under it, and it is excluded
> from the sanction chain."

**Repo-state finding at fix3 (Rule 6 — verified, not assumed):** NO tag object exists in this
repository. `git tag -l` empty; `.git/refs/tags/` empty; no packed tag refs; `git fsck` shows no
dangling tag; the reflog records no tag creation; `git cat-file -t stage2-sanction-431-0b98c6fa` ->
"Not a valid object name". Consequences:
- There is **no tag-object ID, signature, or message to record from this repository**, and **no ref
  here to delete or rename** — nothing operative to withdraw was found.
- The ordinary access key present in this environment is `id_ed25519` =
  `SHA256:o22fIaTwSdjj10mT8mrKVLgz0BQhL3UvUioF2XF7wSI` ("mister-key"), which is NOT the sanction key.
- The withdrawal statement above is recorded as a **standing declaration**: any signed tag that names
  this package/token but is (a) signed by anything other than the sanction key
  `SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs`, or (b) created before GPT CLEAR, is
  **non-operative and excluded from the sanction chain**, regardless of the clone it appears in. If
  such a tag was created in another checkout, it must be deleted there and its object ID reported.

## 3. Exact draft sanction message (to be signed by Tzvi after CLEAR — NOT signed here)
- File: `build_log/431_sanction_message_draft.txt` (pure ASCII, LF).
- SHA-256 of the exact bytes: **`a5d80b82758b0ffcba72b8fb7c9ceb32f86cdf116f3b08476209f1c8d48b9041`**.
- Must not change between audit and signing. Contains: `package_commit: <P>`, `token: <T>`,
  `manifest_self_hash: <T>`, `authorized_principal: zvido@yahoo.com`,
  `sanction_key_fingerprint: SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs`, per-artifact
  committed-blob SHA-256 for all six, and the statement "Stage 2 authorized only for this exact
  package at commit c9f6dd7f6db7899e729b5f6f6407398a64f41d65."

## 4. How the real sanction is applied (Tzvi, after CLEAR)
1. Load the sanction private key into ssh-agent (passphrase entered by Tzvi).
2. `git tag -s -F build_log/431_sanction_message_draft.txt --cleanup=verbatim stage2-sanction-431-0b98c6fa c9f6dd7f6db7899e729b5f6f6407398a64f41d65`
   (signing with `user.signingkey` set to the sanction key for that command only).
3. `git tag -v stage2-sanction-431-0b98c6fa` must verify against the allowed-signers file (only the
   sanction key passes).
4. The runtime gate (`verify_signed_sanction_binding`) then finds the tag at HEAD, `git tag -v`
   passes against the allowed-signers, the embedded `token:`/`package_commit:` match, and content
   identity holds — only then may a run proceed. The legibility record Q is authored after the tag
   exists.

## 5. Runtime binding (committed at P — unchanged by fix3)
Commit identity comes from the TAG, never the manifest. `verify_signed_sanction_binding()` requires
exactly one annotated tag pointing at HEAD whose signature verifies (`git tag -v`, i.e. against the
allowed-signers under `gpg.format ssh`), whose peeled target == HEAD, and whose embedded `token:` ==
manifest token; `verify_repository_execution_identity()` additionally HALTS if the manifest carries
any commit SHA and enforces per-artifact `working-tree-LF == committed_blob_sha256 == sha256(HEAD:path)`
plus a clean package tree and the LF pin. fix3 changed no harness/manifest bytes; token T unchanged.
