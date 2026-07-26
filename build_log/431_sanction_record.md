# 431 Stage-2 Sanction — Q-prep record (exact unsigned message)

**Provenance only.** This file and the message it describes are NOT hashed into the package token and
are NOT read by the runtime gate. They exist so the exact bytes Tzvi will sign are fixed and
auditable before any signature exists.

Created in a commit AFTER the package commit, which is why it can name that commit without
self-reference.

## Bound facts (current)
- **Package commit P″:** `b05b735ae9014386ba330092cbcdf52601d735a4`
- **Token T″ / manifest self-hash:** `bb1c40b1e37a0d14d865c48526724c04184a00d0c18ebde8126733df4697c477`
- **Authorized principal:** `zvido@yahoo.com`
- **Authorized key fingerprint:** `SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs`
- **Allowed namespace:** `git`

## Exact message
- **Path:** `build_log/431_sanction_message.txt` (pure ASCII, LF, LF-pinned)
- **SHA-256 of the exact bytes:** **`84e6aab4b5c9bdf507645956cc151f352d3bb512c50d3a5a7cd7a436b6105eb0`**
- **These bytes must not change between audit and signing.** If they change, the tag body will no
  longer match the recomputed token / policy and the runtime gate will reject the tag.

It names: package commit P″, token T″, manifest self-hash, all **nine** artifact committed-blob
SHA-256 values, the authorized principal, the authorized key fingerprint, and the authorization
statement "Stage 2 authorized only for this exact package at commit
b05b735ae9014386ba330092cbcdf52601d735a4."

## OBSOLETE prior message — DO NOT SIGN
The previous Q-prep message, SHA-256 `3de7329cfcb62e9c7a4da9f267f6c4b73df88ba9969c0477343811aa5f11b931`,
naming package commit `3fb5f39a9932c1249241f5e987c2e206c074ded1` and token
`8389e9651438e72707eadd63a1e69a17a78035ea36ea75de640d8dcd76a2a071`, is **OBSOLETE — superseded,
never signed.** It authorized the Step-442 package, whose runtime still permitted the manifest-trust
bypass (the working-tree manifest decided what was verified). Signing it would sanction a package
whose gate can be circumvented. It was replaced in place at this path; its bytes survive only in the
history of that file.

Signing history to date: **no sanction tag has ever been created or signed in this repository.**

## Status
**UNSIGNED. No tag exists.** No tag was created in Step 443. The runtime gate HALTS until an
annotated tag signed by the authorized key points at P″ and satisfies every check.

## Applying the sanction (Tzvi, after CLEAR — requires the passphrase-protected sanction key)
1. Check out P″ (detached): `git checkout --detach b05b735ae9014386ba330092cbcdf52601d735a4`
2. Load the sanction private key into ssh-agent.
3. Sign the exact message as an annotated tag on P″:
   `git -c gpg.format=ssh -c user.signingkey=<sanction key> tag -s -F build_log/431_sanction_message.txt --cleanup=verbatim stage2-sanction-431-bb1c40b1 b05b735ae9014386ba330092cbcdf52601d735a4`
4. Verify against the COMMITTED anchor (not ambient config):
   `git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=build_log/431_sanction_allowed_signers tag -v stage2-sanction-431-bb1c40b1`
5. The runtime gate then independently re-verifies before any provider call: hardcoded nine-artifact
   scope, manifest read from HEAD (working-tree copy byte-identical), per-artifact three-way blob
   equality, clean tree, token recomputed from the nine HEAD blobs, four-way token equality
   (recomputed == committed manifest == `--stage2-sanction` == signed-tag body), and the tag verified
   against the one-key anchor materialized from the committed HEAD blob.

`--cleanup=verbatim` matters: any whitespace normalization of the message changes the bytes and
therefore the recorded SHA-256.
