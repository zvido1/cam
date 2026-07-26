# 431 Stage-2 Sanction — FINAL RECORD (Q-final, Step 446)

**The sanction is complete and verifies.** This is the legibility record: provenance only. It is
**not** in the runtime gate, **not** in token derivation, and **not** among the eleven package
artifacts. P4, T4, the signed tag, and the approved message file are untouched by this commit.

## 1. Sanctioned package
| field | value |
|---|---|
| package commit **P4** | `d679eec8525fa672724a012f7d1fac0d0d8e7620` |
| token **T4** | `ef1a7af7f77d0999648bc39fa6b367a68d31d09470be699ee25555137cc511ca` |
| manifest self-hash | `ef1a7af7f77d0999648bc39fa6b367a68d31d09470be699ee25555137cc511ca` |
| artifact count | **11** |
| authorized principal | `zvido@yahoo.com` |
| authorized key fingerprint | `SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs` |
| signing key | `cam_sanction_ed25519` (dedicated; private key held by Tzvi) |

## 2. The sanction tag
| field | value |
|---|---|
| tag name | `stage2-sanction-431-ef1a7af7` |
| **tag-object ID** | `dba455a5821b3c7b1348619c1d820d39c4e98f5a` |
| peeled target | `d679eec8525fa672724a012f7d1fac0d0d8e7620` |
| peeled target == P4 | **True** |

```
$ git rev-parse stage2-sanction-431-ef1a7af7
dba455a5821b3c7b1348619c1d820d39c4e98f5a

$ git rev-parse stage2-sanction-431-ef1a7af7^{}
d679eec8525fa672724a012f7d1fac0d0d8e7620

$ git show-ref --tags
dba455a5821b3c7b1348619c1d820d39c4e98f5a refs/tags/stage2-sanction-431-ef1a7af7
```

## 3. Signature verification — verbatim
Verified against the **committed** trust anchor (`HEAD:build_log/431_sanction_allowed_signers`) with explicit `-c` overrides, so
no ambient `gpg.ssh.allowedSignersFile` from `.git/config` can influence the result.

```
$ git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=build_log/431_sanction_allowed_signers tag -v stage2-sanction-431-ef1a7af7
object d679eec8525fa672724a012f7d1fac0d0d8e7620
type commit
tag stage2-sanction-431-ef1a7af7
tagger Tzvi D. Daum <zvido@yahoo.com> 1785084553 -0400

Stage-2 sanction -- Step 431 governed-selection executable package (Construction A / Option 3)
package_commit: d679eec8525fa672724a012f7d1fac0d0d8e7620
token: ef1a7af7f77d0999648bc39fa6b367a68d31d09470be699ee25555137cc511ca
manifest_self_hash: ef1a7af7f77d0999648bc39fa6b367a68d31d09470be699ee25555137cc511ca
authorized_principal: zvido@yahoo.com
sanction_key_fingerprint: SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs
artifact_blob_sha256:
  431_measurement_config.json: 7000ad8f4c1f14b43d59f043fb90a52c7c03e139cd6ec808180cfd651f139a0b
  431_requirement_profiles.json: 57f8a22ae258e01afa94568c9fba8e9f895e79868c592134b162d5923bd8563b
  431_output_schema.json: a9724730044357131cec19e81558a0e05a9460d1a3588f9ef9d520e47d26d4b2
  431_selector_prompt.txt: 3a146f4122dddf09f8de984662685789ee6aee6a3276509d91fc5818a63e0007
  431_fixture_preflight.json: 080eb3ed9fca215d8e65faa3dafaa451536de974d7ccb53fbbda16af26ad8770
  run_431_selection_measurement.py: 0496dfc8af6aa761d7928ddf57884c4dfab41ae5a5f99e328145e5b5ff67002d
  431_sanction_allowed_signers: f0d2db7374ed8e6a0a5cc727f82794af9ad16c70b2532d6878a4706c337217d6
  431_sanction_key.pub: e0b26fd7f79e933db44deecca6820037cd950760ec1e5c4421e217a5963bb9b9
  431_sanction_policy.json: e78b5ffcfbd6a48afa674c91d971531179a2c5cdd22c6de5c87f7029d0f056d0
  atreca_eastjamie_southsf_lease.txt: e049ee63a4e2f475c133b65ceb7a454b4570e59ec288a39b37129740b200d04d
  atlas_meridian_warehouse_lease.txt: da9b5655c5cab382577f139a1884625d81f42b2610a146042018026dc28d2b71
statement: Stage 2 authorized only for this exact package at commit d679eec8525fa672724a012f7d1fac0d0d8e7620.
Good "git" signature for zvido@yahoo.com with ED25519 key SHA256:bHbLJOYJwDmI1E/cPduVFnOkbVpbRzwJEyAShQZuAHs
(exit=0)
```

## 4. Signed bytes == pre-approved bytes
The tag's message body (signature block excluded) is **byte-identical** to the message approved in
Q-prep4 `779cc887ce0875ea3d50f6d52485217974e4828c` before signing.

| | SHA-256 |
|---|---|
| tag message body | `685d9dfe60cd9de5f808803ddee5507e8d6e15f1109f78c0b79de1a4c7674ec6` |
| approved message file at Q-prep4 | `685d9dfe60cd9de5f808803ddee5507e8d6e15f1109f78c0b79de1a4c7674ec6` |
| recorded in Q-prep4 | `685d9dfe60cd9de5f808803ddee5507e8d6e15f1109f78c0b79de1a4c7674ec6` |
| **byte-identical** | **True** |

## 5. The eleven sanctioned artifacts
| artifact | git path | committed-blob SHA-256 |
|---|---|---|
| `431_measurement_config.json` | `build_log/431_measurement_config.json` | `7000ad8f4c1f14b43d59f043fb90a52c7c03e139cd6ec808180cfd651f139a0b` |
| `431_requirement_profiles.json` | `build_log/431_requirement_profiles.json` | `57f8a22ae258e01afa94568c9fba8e9f895e79868c592134b162d5923bd8563b` |
| `431_output_schema.json` | `build_log/431_output_schema.json` | `a9724730044357131cec19e81558a0e05a9460d1a3588f9ef9d520e47d26d4b2` |
| `431_selector_prompt.txt` | `build_log/431_selector_prompt.txt` | `3a146f4122dddf09f8de984662685789ee6aee6a3276509d91fc5818a63e0007` |
| `431_fixture_preflight.json` | `build_log/431_fixture_preflight.json` | `080eb3ed9fca215d8e65faa3dafaa451536de974d7ccb53fbbda16af26ad8770` |
| `run_431_selection_measurement.py` | `build_log/run_431_selection_measurement.py` | `0496dfc8af6aa761d7928ddf57884c4dfab41ae5a5f99e328145e5b5ff67002d` |
| `431_sanction_allowed_signers` | `build_log/431_sanction_allowed_signers` | `f0d2db7374ed8e6a0a5cc727f82794af9ad16c70b2532d6878a4706c337217d6` |
| `431_sanction_key.pub` | `build_log/431_sanction_key.pub` | `e0b26fd7f79e933db44deecca6820037cd950760ec1e5c4421e217a5963bb9b9` |
| `431_sanction_policy.json` | `build_log/431_sanction_policy.json` | `e78b5ffcfbd6a48afa674c91d971531179a2c5cdd22c6de5c87f7029d0f056d0` |
| `atreca_eastjamie_southsf_lease.txt` | `05 Lease Analyzer/test_data/tenants/atreca_eastjamie_southsf_lease.txt` | `e049ee63a4e2f475c133b65ceb7a454b4570e59ec288a39b37129740b200d04d` |
| `atlas_meridian_warehouse_lease.txt` | `05 Lease Analyzer/test_data/tenants/atlas_meridian_warehouse_lease.txt` | `da9b5655c5cab382577f139a1884625d81f42b2610a146042018026dc28d2b71` |

## 6. Obsolete messages — **THREE**, none ever signed
| SHA-256 | named package commit | token | why obsolete |
|---|---|---|---|
| `3de7329cfcb62e9c7a4da9f267f6c4b73df88ba9969c0477343811aa5f11b931` | `3fb5f39` (442) | `8389e965…` | its runtime permitted the manifest-trust bypass |
| `84e6aab4b5c9bdf507645956cc151f352d3bb512c50d3a5a7cd7a436b6105eb0` | `b05b735` (443) | `bb1c40b1…` | its runtime did not verify repository-local imported modules |
| `56bce9e915ef56361f5a166e71a78763bbcd2babc9b1f8d341f62f75c51560be` | `6a32d47` (444) | `f341a188…` | its package excluded the lease fixtures (atlas lease untracked) |

**Signing any of them** would have sanctioned a package whose gate could be circumvented. None was
signed. The one and only signature ever produced in this repository is the tag in §2.

## 7. Clerical corrections to the Q-prep4 record (`779cc887ce0875ea3d50f6d52485217974e4828c:build_log/431_sanction_record.md`)
Applied **here**; that file is left as committed and is superseded by this record. Neither correction
touches P4, T4, the signed tag, or the approved message.

1. It says *"Two superseded messages exist in this file's history"* while its own table correctly
   lists **three**. The count is wrong; **three** is correct. (Introduced at Step 445 when the third
   row was added and the sentence was not updated.)
2. *"Signing either would sanction…"* → **"Signing any would sanction…"** (three items, not two).
3. **Additionally stale, not in GPT's list:** that record ends with *"Signing history to date: no
   sanction tag has ever been created or signed in this repository."* That was true when written and
   is now false — the tag in §2 exists and verifies. This record supersedes that sentence.

## 8. Audit disposition
**GPT: CLEAR** on the construction and on the exact message. The sanction was applied only after that
clearance, against the pre-reviewed message bytes recorded in Q-prep4.

## 9. Status
- The sanction tag exists, peels to P4, and verifies against the committed one-key anchor.
- **No measurement run has been performed.** No provider call has ever been made by this package.
- The run remains a separate, explicit act.
