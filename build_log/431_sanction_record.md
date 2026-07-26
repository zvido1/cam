# 431 Stage-2 Sanction — Q-prep record (exact unsigned message)

**Provenance only.** This file and the message it describes are NOT hashed into the package token and
are NOT read by the runtime gate. They exist so the exact bytes Tzvi will sign are fixed and
auditable before any signature exists.

Created in a commit AFTER the package commit, which is why it can name that commit without
self-reference.

## Bound facts
- **Package commit P′:** `3fb5f39a9932c1249241f5e987c2e206c074ded1`
- **Token T′ / manifest self-hash:** `8389e9651438e72707eadd63a1e69a17a78035ea36ea75de640d8dcd76a2a071`
- **Authorized principal:** `zvido@yahoo.com`
- **Authorized key fingerprint:** `SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs`
- **Allowed namespace:** `git`

## Exact message
- **Path:** `build_log/431_sanction_message.txt` (pure ASCII, LF, LF-pinned)
- **SHA-256 of the exact bytes:** **`3de7329cfcb62e9c7a4da9f267f6c4b73df88ba9969c0477343811aa5f11b931`**
- **These bytes must not change between audit and signing.** If they change, the tag body will no
  longer match the manifest token / policy and the runtime gate will reject the tag.

It names: package commit P′, token T′, manifest self-hash, all **nine** artifact committed-blob
SHA-256 values, the authorized principal, the authorized key fingerprint, and the authorization
statement "Stage 2 authorized only for this exact package at commit
3fb5f39a9932c1249241f5e987c2e206c074ded1."

## Status
**UNSIGNED. No tag exists.** No tag was created in Step 442. The runtime gate HALTS until an
annotated tag signed by the authorized key points at P′ and satisfies every check.

## Applying the sanction (Tzvi, after CLEAR — requires the passphrase-protected sanction key)
1. Check out P′ (detached): `git checkout 3fb5f39a9932c1249241f5e987c2e206c074ded1`
2. Load the sanction private key into ssh-agent.
3. Sign the exact message as an annotated tag on P′:
   `git -c gpg.format=ssh -c user.signingkey=<sanction key> tag -s -F build_log/431_sanction_message.txt --cleanup=verbatim stage2-sanction-431-8389e965 3fb5f39a9932c1249241f5e987c2e206c074ded1`
4. Verify against the COMMITTED anchor (not ambient config):
   `git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=build_log/431_sanction_allowed_signers tag -v stage2-sanction-431-8389e965`
5. The runtime gate then independently re-verifies (one-key anchor materialized from HEAD blobs,
   peel == HEAD, token/package_commit/principal/fingerprint match, nine-artifact three-way blob
   equality, clean tree) before any provider call.

Step 4 must be run from a checkout of P′; `--cleanup=verbatim` matters, because any whitespace
normalization of the message changes the bytes and therefore the recorded SHA-256.
