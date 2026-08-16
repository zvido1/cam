# 452 Key Isolation Record

**Date:** 2026-08-15
**Author:** Claude Code
**Purpose:** Evidence toward §8.2 of `452_production_package_instruction_v8.md`.

> **THIS DOCUMENT IS NOT A §8.2 CONFIRMATION.** §8.2 requires Tzvi to state that the private
> sanction key is not provided to, read by, copied by, or invoked from the Code/build process.
> That statement is his to make and has not been made. This record supplies facts he may use;
> it does not substitute for the statement, and Claude Code does not assert §8.2 is satisfied.

**No private key was opened, printed, or read at any point in this audit or in the repairs.**
Every comparison below used `.pub` files or digests only.

---

## Part 1 — Read-only audit, five results verbatim

### 1. Git signing configuration (before repair)

```
user.signingkey            = C:/Users/Owner/.ssh/cam_sanction_ed25519
gpg.format                 = ssh
gpg.ssh.allowedSignersFile = C:/Users/Owner/OneDrive/CAM/build_log/431_sanction_allowed_signers
commit.gpgsign             = (unset)
tag.gpgsign                = (unset)
```

`user.signingkey` named a **private key path** — no `.pub` extension. Scope was **local**
(`.git/config` of this repository); `global` and `system` were both unset. `.git/config` is not
tracked by git and was therefore never committed, but it is inside the working tree this process
operates on.

`gpg.ssh.allowedSignersFile` pointed at the **431** allowed-signers file, not the 452 one.

### 2. Filenames in `C:\Users\Owner\.ssh\` (filenames only; no file opened)

Private keys, identified by the absence of a `.pub` extension:

```
cam_sanction_ed25519              464 B   <- the sanction private key
id_ed25519                        399 B
id_rsa                           1766 B
ssh_key_github_jewish_lifetrack  3381 B
whm_root_ed25519                  464 B
```

Public counterparts present for each. Non-key files: `config`, `known_hosts`, `known_hosts.old`.

### 3. Private-key markers in the repository

Searched `C:\Users\Owner\OneDrive\CAM` for `BEGIN OPENSSH PRIVATE KEY`, `BEGIN RSA PRIVATE KEY`
and the EC/DSA variants, using match-count mode so no content could be surfaced.

```
Result: ZERO occurrences across ZERO files.
```

### 4. Private-key path references in committed scripts and `build_log`

Searched the whole working tree for `cam_sanction_ed25519`, `id_ed25519`, `id_rsa`,
`whm_root_ed25519`, `ssh_key_github_jewish_lifetrack`, and `.ssh/`.

```
Result: ZERO occurrences.
```

The only reference to a private key path anywhere was the `.git/config` entry in item 1, which is
local and uncommitted, and which has since been removed (Part 2).

### 5. `git tag -v stage2-sanction-431-ef1a7af7`

```
Good "git" signature for zvido@yahoo.com with ED25519 key
SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs
```

The fingerprint matches `authorized_fingerprint` in `452_sanction_policy.json` exactly.

---

## Part 2 — Two configuration repairs

| setting | before | after |
|---|---|---|
| `user.signingkey` (local) | `C:/Users/Owner/.ssh/cam_sanction_ed25519` | **unset** |
| `gpg.ssh.allowedSignersFile` (local) | `.../build_log/431_sanction_allowed_signers` | `.../build_log/452_sanction_allowed_signers` |

Confirmed after repair:

```
local  user.signingkey = (unset)
global user.signingkey = (unset)
system user.signingkey = (unset)
effective user.signingkey = (unset)
occurrences of "signingkey" in .git/config = 0
```

**Re-verification after the allowed-signers switch:** `git tag -v stage2-sanction-431-ef1a7af7`
still reports `Good "git" signature`. The 431 tag verifies against the **452** allowed-signers
file, confirming the byte-copy carries the same authorized key and that the two files do not
differ in any way the digest comparison missed.

### Public-key identity check (no private key opened)

| file | raw size | raw sha256 |
|---|---|---|
| `build_log/452_sanction_key.pub` | 98 B | `e0b26fd7f79e933db44deecca6820037cd950760ec1e5c4421e217a5963bb9b9` |
| `~/.ssh/cam_sanction_ed25519.pub` | 99 B | `08eddd6218b8cd33eed6b078e03d00aa2ce772b4a27b12e2f312808d65c74e7c` |

With trailing whitespace stripped, **both are 97 bytes and hash identically**:

```
1ce09377094f29c1ee3f0a3527d77359ffb64fb587ec911a45b3a8488d930d11
```

Trailing bytes: the repository copy ends `\n`; the `~/.ssh` copy ends `\r\n`. The one-byte
difference is a **line ending, not a different key**. Both parse as `ssh-ed25519`, 68-character
body, comment `CAM`.

---

## Part 3 — The residual, stated plainly

> Code retains shell access to the machine where the private key resides. Removing the configured
> signing key makes invocation from this working directory impossible by default and by accident,
> not impossible in principle. This is a procedural control with a technical default, not physical
> separation. §8.2 must not be restated to match; the environment moves toward the requirement.

What the audit establishes, and what it does not:

- **Established:** the private key was not read, not copied, and is not referenced by any
  committed file. No key material exists anywhere in the repository.
- **Established:** as of this record, no configured signing key exists in any git scope, so
  `git tag -s` from this working directory will fail rather than silently invoke the key.
- **NOT established:** physical separation. The private key remains on the same filesystem,
  reachable by any process with shell access, including this one.

Per §8.2's own instruction — **"Do not claim physical separation unless it is physically
separate"** — no such claim is made here.

---

## Part 4 — OPEN QUESTION against the P4 record (NOT §8.2)

**Who executed the signing command that created `stage2-sanction-431-ef1a7af7`?**

Recorded, not answered. Claude Code made no attempt to determine this and draws no inference
from the configuration state found in item 1. The question is filed against the **P4 / Step-431
record**, not against §8.2 of this package, and is not a blocker for Step 452's Stage-1 gates.

---

## Status

- Nothing committed. Nothing pushed. No tag created. No sanction message created.
- No private key generated, read, copied, or invoked.
- §8.2 remains **UNCONFIRMED**, pending Tzvi's statement.

**Note for the reviewing party:** this file is **not** in §3.1's `EXPECTED_PACKAGE_ARTIFACTS`
(37 entries), so `452_config_manifest.json` will not bind it at step 5. Step-447 through Step-451
status records *are* in §3.1. Whether a record offered as evidence toward §8.2 should likewise be
bound is a question for Chat and the reviewing party; Claude Code has not added it, because §3.1
was re-ratified at `b9343bd9…` and any further change requires another ratification cycle.
