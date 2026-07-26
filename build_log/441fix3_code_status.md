# Step 441-fix3 — sanction-key verification setup + tag withdrawal + draft sanction message — CODE STATUS

**Status:** COMPLETE for the executable parts (verification config, draft message, provenance,
evidence). **One brief item was N/A against actual repo state** and is reported honestly rather than
fabricated: there is **no premature tag in this repository** to withdraw. ZERO model calls, no run,
no push, no private key touched. Package **P = `c9f6dd7`** and token **T = `0b98c6fa…`** unchanged
(no harness/manifest byte changed).

## Named objective vs. result
| Brief item | Result |
|---|---|
| Configure verification against the dedicated sanction key | **DONE** — allowed-signers file committed; `gpg.format=ssh`, `gpg.ssh.allowedSignersFile` set; `user.signingkey` empty. Sanction pubkey fingerprint recomputed = `SHA256:bHbL…` (MATCH). |
| Withdraw the premature tag | **N/A — no tag exists here** (verified: empty `refs/tags/`, no packed refs, no dangling tag via `git fsck`, no reflog tag event, `cat-file -t` → "Not a valid object name"). Withdrawal statement recorded as a standing declaration; nothing operative found to delete. Rule 6: not fabricated. |
| Prepare exact draft sanction message (file, no signing) | **DONE** — `build_log/431_sanction_message_draft.txt` (pure ASCII, LF), SHA-256 `a5d80b82758b0ffcba72b8fb7c9ceb32f86cdf116f3b08476209f1c8d48b9041`, LF-pinned in `.gitattributes`. |
| Raw evidence | **PRODUCED** (see report / below). |

## What is a config-only fix vs. genuinely unavailable (carried from fix3 diagnosis)
- GPG signing: unavailable (keyring empty). SSH signing: enabled for **verification** here (public
  key only). **Signing** still requires Tzvi's passphrase-protected private sanction key — done by
  Tzvi after CLEAR. Claude Code did not generate/read/copy/invoke any private key.

## Verification config (machine-local `.git/config`)
- `gpg.format = ssh`
- `gpg.ssh.allowedSignersFile = C:/Users/Owner/OneDrive/CAM/build_log/431_sanction_allowed_signers`
- `user.signingkey = <empty>` (this checkout cannot sign — intended)
- Allowed-signers (committed): `zvido@yahoo.com namespaces="git" ssh-ed25519 AAAA…DDBk CAM sanction key`

## Tag withdrawal — standing declaration (verbatim, from brief)
"A signed tag was created before completion of the final delta audit using the ordinary SSH access
key (id_ed25519) and containing unconditional authorization language. It is withdrawn and
non-operative. It did not authorize execution, no model calls occurred under it, and it is excluded
from the sanction chain." (Recorded in `431_sanction_provenance.md`. Repo-state finding: no such tag
object present here; ordinary key in this env = id_ed25519 `SHA256:o22f…` "mister-key", ≠ sanction key.)

## Newline-equivalence — actual outputs (P vs 65556ee)
- JSON loaded-object equality: config/profiles/schema/preflight → **parsed-equal True** (4/4).
- prompt: raw-bytes-equal **True**; equal-after-stripping-CR **True**.
- 5 semantic artifacts byte diff: **raw-identical True** (⇒ CRLF→LF-only vacuously) for all 5.
- Harness (P) AST(LF)==AST(CRLF): **True**; parses True.

## Token — reproduced from P's committed blobs
`sha256(json.dumps(6 committed-blob hashes, sort_keys))` = `0b98c6fa…` == manifest token. Harness
committed-blob hash `30f10e3a…`. Five semantic artifacts byte-identical to `65556ee`.

## Runtime binding (committed at P, unchanged) — identity from the TAG not the manifest
`verify_signed_sanction_binding()` requires one annotated tag at HEAD, `git tag -v` verifies (against
the allowed-signers under `gpg.format ssh` — only the sanction key passes), peeled target == HEAD,
embedded `token:`/`package_commit:` match. `verify_repository_execution_identity()` HALTS if the
manifest carries any commit SHA and enforces the three-way blob equality + clean tree + LF pin.

## Git
- New/changed files committed with `git add -f` explicit paths: `.gitattributes`,
  `build_log/441fix3_chat_instruction.md`, `build_log/431_sanction_allowed_signers`,
  `build_log/431_sanction_message_draft.txt`, `build_log/431_sanction_provenance.md`,
  `build_log/441fix3_code_status.md`.
- Pre-existing `M` on 398/399/406/407 status files predate this session — NOT touched.
- `git status --porcelain cam/` empty. **NOT pushed.** STOP for construction delta audit.
- The real signed sanction tag is NOT created here — Tzvi signs the exact pre-reviewed draft after CLEAR.
