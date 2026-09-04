# Step 553 — Pushed and measured. The stamping works in production. The compression saved ~3 KB, not 1,026 KB, and Step 551's premise is why I thought otherwise.

**Date:** 2026-09-04 · **Instruction:** `build_log/553_chat_instruction.md`
**`f0415d9..134f01f  main -> main`, branch only. Redeployed `started_at 2026-09-04T02:27:43Z`. Tests: 437 passed, 3 skipped, 12 subtests.**

---

# 0. THE CORRECTION, FIRST

**Production was already serving gzip before this push.** Measured against the pre-push instance
(`started_at 19:42:28Z`, the build with no `GZipMiddleware` in it):

```
  Accept-Encoding=identity   ->   912,481 bytes  Content-Encoding=None
  Accept-Encoding=gzip       ->   213,113 bytes  Content-Encoding=gzip
  Accept-Encoding=gzip, br   ->   213,089 bytes  Content-Encoding=gzip
```

**Step 551 reported `Content-Encoding: None` and 1,337,587 bytes for the same nine assets, using the
same header and the same method.** Re-run hours later against that same unchanged boot, it returns gzip.
**One of those readings is wrong, and it is Step 551's.**

## What that does to the benefit

```
  9 static assets, Accept-Encoding: gzip
     pre-push  production   290,508 bytes
     post-push production   287,282 bytes
     difference               3,226 bytes  (1.1%)
```

**`GZipMiddleware` bought about 3 KB in production, not 1,026 KB.** The 1,026 KB figure is real but it
is measured against `identity`, and **no browser sends `identity`** — every real client offers gzip and
was already receiving it. **Step 552's headline benefit is wrong, and the error originates in a
measurement I made at Step 551 and built two steps on.**

I cannot say why the Step-551 reading came back uncompressed. Same host, same header, same method, same
boot, ~5 hours apart, different answer. **A plausible explanation is edge-level compression that was
cold for those objects and passed the origin bytes through on first request** — that is a hypothesis
consistent with common CDN behaviour and **it is not established.**

## What the change is still worth

**The app is now the compressor rather than depending on an edge whose behaviour I cannot see,
configure, or rely on.** A discriminating probe confirms the app is doing it:

```
  /api/provider-health (anon)   AE=identity  22 bytes  enc=None
  /api/provider-health (anon)   AE=gzip      22 bytes  enc=None
```

**A 22-byte response is not compressed even when gzip is offered — exactly `minimum_size=500`
behaviour.** That is the app's configured threshold showing through, so compression is now originating
where the repository can see it. **That is a smaller and more defensible claim than "1,056 KB saved",
and it is the one I should have made.**

---

# 1. PREFLIGHT

```
git fetch origin       -> nothing incoming
git status -sb         -> ## main...origin/main [ahead 5]
tests against HEAD     -> 437 passed, 3 skipped, 12 subtests
```

**Deployable files across the five commits — three, and no pipeline file among them:**

```
550  05 Lease Analyzer/app/main.py
     cam/adapters/lease_review/tests/test_550_asset_versions.py
552  05 Lease Analyzer/app/main.py
     CLAUDE.md
     cam/adapters/lease_review/tests/test_550_asset_versions.py
548, 549, 551 shipped no code.
```

```
forbidden paths (results/, _*_results/, .env, driveupload, keys, creds) : NONE
secret scan (sk-/xai-/AIza/ghp_/PRIVATE KEY/Bearer/aws_secret)          : NO MATCHES
access-code literal in the diff                                          : NONE
```

*(The shared demo access code appeared in a job-status payload I read at Step 549. It is not in any
committed file and I checked the diff for it explicitly.)*

---

# 2. THE SIX FLAGS — UNCHANGED FROM STEP 548

**No pipeline file was touched at all**, so there is nothing to diff:

```
git diff origin/main..HEAD -- lease_adapter.py lease_coverage.py lease_coverage_305.py  ->  EMPTY
```

```
SPAN_EVIDENCE_ENABLED       = True                                lease_coverage.py:51
SPAN_EVIDENCE_LPS           = {"LP-07","LP-12","LP-17","LP-27"}   lease_coverage.py:52
SECTION_EXPANDED_SPAN_LPS   = set()                               lease_coverage.py:76
ENTAILMENT_TEST_LPS         = {"LP-27"}                           lease_coverage_305.py:284
GATE_ABORT_RETURNS_DEGRADED = True                                lease_adapter.py:173
DEGRADABLE_APPLICABILITY    = {"not_applicable","unclear"}        lease_adapter.py:194
```

---

# 3. WHAT CHANGES FOR A USER

- **Compression now originates in the app.** Against `identity`, 1,337,587 → 287,282 bytes (78.5%).
  **Against what production was already delivering, ~3 KB.** §0.
- **Both shell routes serve content-hashed asset URLs.** §4.
- **`asset_version` computes on every request**, 1.39 ms for all nine assets, no cache — so the version
  can never be stale, which is what the Step-550 `(mtime_ns, size)` key could not guarantee.
- **`no-store` is unchanged and no caching header was added.** Verified live:
  `Cache-Control: no-cache, no-store, must-revalidate` on both shell routes.

---

# 4. THE DEPLOYED MEASUREMENT

## Static assets

```
  Accept-Encoding=identity  wire=1,337,587  Content-Encoding=None
  Accept-Encoding=gzip      wire=  287,282  Content-Encoding=gzip
  saving                        1,026 KB  (78.5%)
```

Step 552 predicted 288,630 from the local ASGI measurement. **Production came in at 287,282 — 0.5%
apart.** The local method was sound even though the conclusion drawn from Step 551 was not.

## Both shell routes stamp — confirmed in production

```
  /                                             wire=16,324  decoded=80,776  enc=gzip
      stamped(10-hex)=9   numeric ?v= remaining=0   CC=no-cache, no-store, must-revalidate
      e.g. style.css?v=b24b84c413

  /results/lease_review_20260903_200838_80c9fa  wire=16,324  decoded=80,776  enc=gzip
      stamped(10-hex)=9   numeric ?v= remaining=0   CC=no-cache, no-store, must-revalidate
      e.g. style.css?v=b24b84c413
```

**Byte-identical, nine stamped references each, zero hand-maintained literals surviving on either.** The
results route — the one in every emailed `results_url`, and the one Step 550 missed — is fixed and
verified where it runs.

## `/static/index.html` — still reachable, still unstamped. Recorded, not fixed.

```
  wire=16,244  decoded=80,702  enc=gzip  Cache-Control: None
  stamped(10-hex)=0   numeric ?v= = 9
  values: ['1','2','3','4','10','12','400','475']
```

**All nine hand-maintained literals, including the 87-day-stale `style.css?v=400`, and no
`Cache-Control` at all.** Inert under `no-store` on the shell; **a precondition for any caching change**,
exactly as Step 551 recorded.

## A hash difference between local and production, explained

The deployed stamp for `style.css` is `b24b84c413`; locally it is `630d438920`. **Line endings:**

```
  local (as on disk, CRLF): 630d438920   377,416 bytes
  same file with LF        : b24b84c413   363,785 bytes
  deployed stamped value   : b24b84c413
```

Git checks out LF on Linux and CRLF on Windows (the `LF will be replaced by CRLF` warnings on every
commit). **The stamp is content-derived and internally consistent within each environment**, which is
all the mechanism requires — but **a hash computed locally will never equal the deployed one**, and a
future session comparing the two would otherwise think something was broken.

---

# 5. THE PUSH

```
To https://github.com/zvido1/cam.git
   f0415d9..134f01f  main -> main
## main...origin/main        unpushed: 0

local tags:  stage2-sanction-431-ef1a7af7  stage2-sanction-452-e0b985b4
remote tags: 0
```

**`--follow-tags` not used. Both sanction tags remain local.**

---

# WHAT IS NOT ESTABLISHED

- **Why Step 551 measured `Content-Encoding: None` is unknown.** The edge-compression hypothesis in §0 is
  consistent with the evidence and unverified. **What is established is that the reading is not
  reproducible and the conclusion built on it was wrong.**
- **I did not verify that the pre-push instance lacked `GZipMiddleware` by inspecting the running
  container** — that is inferred from the commit history, which is solid, but it is an inference.
- **Whether Railway's edge compresses is not confirmed.** The `minimum_size=500` probe shows the app is
  compressing *now*; it says nothing about what else may be in the path.
- **Brotli is still not offered.** `Accept-Encoding: gzip, br` returns gzip.
- **No page was rendered in a browser.** Everything is verified at the HTTP layer; that the stamped URLs
  actually load and the app boots in a browser is untested.
- **No pipeline run was made against this build.** The changes are routing and middleware only and no
  pipeline file was touched, but the first Mode C run on this deploy is unobserved.
- **`/static/index.html` and the five unhashed `demo/*.txt` remain as they were.** Both are preconditions
  for removing `no-store`, and `no-store` was deliberately not removed.
