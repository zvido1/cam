# Step 441-fix3 — sanction-key verification setup + tag withdrawal + draft sanction message (verbatim brief, Rule 7)

STEP 441-fix3 — sanction-key verification setup, withdraw premature tag, prepare draft sanction
message for audit. ZERO model calls, no run, no push. Claude Code MUST NOT generate, read, copy, or
invoke any private key. Signing is Tzvi's act, later, after CLEAR.

DEDICATED SANCTION KEY (verification side only — Tzvi created it, private key passphrase-protected
and retained by Tzvi):
  - public key: ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHY5xKgVPjN04b8tyau0cN8VhMFawgt/JKjrMGmdDDBk CAM sanction key
  - SHA-256 fingerprint: SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs
  - authorized principal: zvido@yahoo.com
Configure verification against it:
  - create an allowed-signers file pairing principal zvido@yahoo.com with the public key above;
  - git config gpg.ssh.allowedSignersFile <that path>;
  - git config gpg.format ssh.
  Do NOT set user.signingkey to any private-key-bearing value. Do NOT create a keypair, sign
  anything, or touch a private key.

WITHDRAW THE PREMATURE TAG: record its tag-object ID, signer fingerprint (id_ed25519), full message,
and this withdrawal statement in the provenance record: "A signed tag was created before completion
of the final delta audit using the ordinary SSH access key (id_ed25519) and containing unconditional
authorization language. It is withdrawn and non-operative. It did not authorize execution, no model
calls occurred under it, and it is excluded from the sanction chain." Then delete or rename the
misleading tag ref so it cannot be mistaken for the sanction.

PREPARE THE EXACT DRAFT SANCTION MESSAGE (a FILE, not a tag — no signing): the precise bytes Tzvi
will sign after CLEAR, containing: token T, manifest self-hash, per-artifact committed-blob identity,
package commit P, authorized principal zvido@yahoo.com + fingerprint
SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs, and "Stage 2 authorized only for this exact
package at P." Compute and record its SHA-256. This message must not change between audit and signing.

PRODUCE RAW EVIDENCE (actual outputs IN the submission, not "ready on request"):
  git rev-parse HEAD
  git show <P>:build_log/431_config_manifest.json   (must show NO commit/head_at_build_time field)
  git show <P>:.gitattributes
  the draft sanction-message file contents + its SHA-256
  the allowed-signers file contents + the git config gpg.ssh.allowedSignersFile value
  the withdrawn tag's object ID + fingerprint + message + withdrawal statement
  the committed runtime-gate code (verify signed tag against allowed-signers + HEAD==peeled-tag==P +
    clean tree + three-way blob equality), showing identity comes from the TAG not the manifest
  the newline-equivalence actual outputs (JSON loaded-object equality, Python AST equality, prompt
    \r-only comparison, byte diff CRLF->LF only)
  fresh package token T + blob-anchored derivation
cam/ clean, no push, no model calls. STOP for construction delta audit. The real signed sanction tag
is NOT created here — Tzvi signs the exact pre-reviewed message after GPT clears.

---

## BUILDER NOTE (Rule 6 — repo-state discrepancy discovered at execution)

The brief instructs withdrawing a premature signed tag. **No tag exists in this repository** at fix3
time: `git tag -l` empty; `refs/tags/` empty; no packed tag refs; no dangling tag object
(`git fsck`); the reflog shows no tag creation; `git cat-file -t stage2-sanction-431-0b98c6fa` ->
"Not a valid object name." Therefore no tag-object ID / signature / message can be recorded from this
repo without fabrication, and there is no ref here to delete. The withdrawal STATEMENT is recorded as
a standing declaration in build_log/431_sanction_provenance.md; if a premature tag was created in a
different clone/checkout, it must be withdrawn there and its concrete details supplied. The ordinary
access key in THIS environment is id_ed25519 = SHA256:o22fIaTwSdjj10mT8mrKVLgz0BQhL3UvUioF2XF7wSI
("mister-key"), which is NOT the sanction key.
