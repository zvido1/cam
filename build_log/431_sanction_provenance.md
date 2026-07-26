# 431 Stage-2 Sanction — Provenance & Verification Record (Step 442)

Governs how the Step-431 executable package is bound to a sanction. Construction A / Option 3 with a
COMMITTED trust anchor: the package manifest carries NO commit SHA; the run-commit↔token binding lives
in an EXTERNAL signed annotated tag; and the key that may sign it is fixed by artifacts committed
inside the package commit and hashed into the package token.

Superseded package: P = `c9f6dd7f6db7899e729b5f6f6407398a64f41d65`, token
`0b98c6fa3a3cf098d243fd90573cda582482c00bf5c6723a4e76a975d5e89164` — correct commit-binding topology,
but its trust anchor was machine-local configuration, not committed content (see §6).

## 1. Dedicated sanction key (verification side only)
- Public key: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHY5xKgVPjN04b8tyau0cN8VhMFawgt/JKjrMGmdDDBk CAM sanction key`
- SHA-256 fingerprint: `SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs` (independently recomputed
  from the public-key blob: **MATCH**).
- Authorized principal: `zvido@yahoo.com`. Allowed namespace: `git`.
- Private key: created and retained by Tzvi, passphrase-protected. **Never generated, read, copied, or
  invoked by Claude Code.**

**Trust anchor is COMMITTED CONTENT (Step 442), not configuration.** Three artifacts are committed in
the package commit, LF-pinned, bound in `committed_blob_binding`, hashed into `artifact_hashes`, and
re-verified by the runtime three-way blob check:
- `build_log/431_sanction_allowed_signers` — the sole authorized signer entry
- `build_log/431_sanction_key.pub` — the standalone authorized public key
- `build_log/431_sanction_policy.json` — authorized principal, fingerprint, namespace

At run time the gate materializes the allowed-signers anchor from `HEAD:build_log/431_sanction_allowed_signers`
into a temp file and verifies with explicit `-c gpg.format=ssh -c gpg.ssh.allowedSignersFile=<temp>`
overrides. **No ambient `gpg.ssh.allowedSignersFile` from `.git/config` is consulted or trusted.**
Machine-local config in this clone (`gpg.format=ssh`, an allowedSignersFile path, `user.signingkey`
empty) is a convenience for manual `git tag -v` only and is NOT load-bearing.

## 2. Premature-tag record — CORRECTED (Step 442)
**This supersedes the earlier withdrawal statement, which asserted as fact that a premature signed
tag had been created. That assertion was never verified against this repository and is retracted;
it is not preserved here as fact.** The corrected statement of record is exactly:

> "No premature sanction tag or tag object was found in this repository. No model calls occurred.
> Any alleged tag created in another clone is outside this repository's current evidentiary record
> unless its raw tag object and provenance are separately produced."

**Supporting repo-state checks (Rule 6 — verified, not assumed):** `git tag -l` empty;
`git show-ref --tags` empty (exit 1); `.git/refs/tags/` empty; no packed tag refs; `git fsck` reports
no dangling tag object; the reflog records no tag-creation event; `git cat-file -t
stage2-sanction-431-0b98c6fa` -> "Not a valid object name".

**Standing rule (forward-looking, not a claim about the past):** any tag that names this package or
token is non-operative and excluded from the sanction chain unless it is an annotated tag signed by
`SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs` (principal `zvido@yahoo.com`) and it satisfies
the runtime gate. The ordinary access key present in this environment is `id_ed25519` =
`SHA256:o22fIaTwSdjj10mT8mrKVLgz0BQhL3UvUioF2XF7wSI` ("mister-key"), which is NOT the sanction key
and cannot produce a tag this gate will accept.

## 3. Sanction message — template here, exact bytes produced AFTER the package commit exists
**This file is committed INSIDE the package commit and therefore deliberately does not name it**
(the same self-reference bar that governs the manifest). What is committed here is the
placeholder-only template `build_log/431_sanction_message_template.txt`.

The EXACT message Tzvi signs — naming the concrete package commit, the concrete token, and all nine
artifact blob hashes — is written in a LATER commit (Q-prep), which can name the package commit
because that commit already exists. Q-prep also records the exact message's SHA-256. Q-prep is
provenance only: it is NOT hashed into the token and NOT read by the runtime gate.

## 4. How the real sanction is applied (Tzvi, after CLEAR)
1. Load the sanction private key into ssh-agent (passphrase entered by Tzvi).
2. Sign the exact message from Q-prep as an annotated tag on the package commit:
   `git tag -s -F <exact-message-path> --cleanup=verbatim <tag-name> <package-commit>`
   with `user.signingkey` set to the sanction key for that command only.
3. Verify against the COMMITTED anchor (not ambient config):
   `git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=build_log/431_sanction_allowed_signers tag -v <tag-name>`
4. Only then may a run proceed, and only if the runtime gate independently passes.

## 5. Runtime binding (committed in the package commit)
Commit identity comes from the TAG, never the manifest. The gate:
1. `load_committed_trust_anchor()` reads the allowed-signers, public key, and policy **as blobs from
   HEAD**; requires exactly ONE authorized key; recomputes its SHA-256 fingerprint from the key blob;
   requires fingerprint == policy `authorized_fingerprint`, principal == `authorized_principal`, and
   `namespaces=="git"`; requires the standalone `.pub` to be the same key.
2. `verify_signed_sanction_binding()` materializes that one-key anchor to a temp file and runs
   `git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=<temp> tag -v <tag>`; requires the tag to be
   annotated, to peel to HEAD, and its body fields `token:`, `package_commit:`, `authorized_principal:`
   and `sanction_key_fingerprint:` to match the manifest token, HEAD, and the committed policy.
3. `verify_repository_execution_identity()` HALTS if the manifest carries any commit SHA, and enforces
   per-artifact `working-tree-LF == committed_blob_sha256 == sha256(HEAD:path)` over all NINE package
   artifacts (the three authorization artifacts included), plus a clean package tree and the LF pin.

Soundness of the key enforcement without parsing tool prose: verification runs against an anchor
containing ONLY the authorized key, whose fingerprint was independently recomputed from the committed
key blob and matched to the committed policy. Under a one-key anchor, `git tag -v` exiting 0 entails
that the signature validated against that key.

## 6. Why the previous package was superseded (trust-anchor defect)
At the previous package commit the allowed-signers file did **not** exist in the tree (it was added
only in a descendant commit), and `gpg.ssh.allowedSignersFile` was a machine-local absolute path in
`.git/config`. `git tag -v` therefore drew its trust anchor from configuration rather than from bytes
committed at the package commit, and a third party checking out that commit alone could not identify
the authorized key. The content half of the gate was self-contained; the signature half was not.
Step 442 fixes this by committing the anchor, binding it into the token, and materializing it from
HEAD at verification time.
