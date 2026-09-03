# Step 551 — No. Compress first. `no-store` is worth 292 KB after gzip, not 1.25 MB — and three preconditions are unmet, one of which I shipped at Step 550.

**Date:** 2026-09-03 · **Instruction:** `build_log/551_chat_instruction.md`
**DESIGN. No code changed. Not deployed.**

---

# 0. THE MEASUREMENT THAT DECIDES IT

**Nothing is compressed. There is no compression middleware in the app at all.**

```
/static/app.js       Content-Encoding: None   wire = 912,481 bytes
/static/style.css    Content-Encoding: None   wire = 363,785 bytes
TOTAL over 9 assets  Content-Encoding: None   wire = 1,337,587 bytes
```

Measured with `Accept-Encoding: gzip, br` on the request. Measured gzip ratio on the same files:

```
app.js       931,328 -> 213,223  (22.9%)
style.css    377,416 ->  61,946  (16.4%)
TOTAL      1,370,065 -> 291,889  (21.3%)     saving 1,053 KB per load
```

**gzip removes 1,053 KB of the 1,370 KB, on every load including the first, in one line
(`GZipMiddleware`), with no staleness risk of any kind.** Caching removes the remaining 292 KB, only on
repeat loads, and only if the hash binding is correct — which §3 shows is not yet guaranteed.

**So the question "remove `no-store`?" is being asked about the smaller 21% of the problem while the
78% sits untouched.** Recommendation in §5.

---

# 1. WHAT `NoCacheStaticFiles` COVERS — AND THE THREE THINGS OUTSIDE IT

```python
    class NoCacheStaticFiles(StaticFiles):
        async def get_response(self, path, scope):
            response = await super().get_response(path, scope)
            if path.endswith(('.js', '.css')):
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
```

**Only `.js` and `.css`.** Everything else served under `/static` gets Starlette's defaults — `ETag` and
`Last-Modified`, **no `Cache-Control` at all** — which means browser *heuristic* caching applies.

Verified live:

```
/static/demo/template.txt   Cache-Control: None   ETag: "f3f5b249..."   Last-Modified: ...
/static/index.html          Cache-Control: None   ETag: "a96275ea..."   Last-Modified: ...
```

## The static tree, complete

```
  931,328  app.js                       hashed
  377,416  style.css                    hashed
   80,702  index.html                   THE STAMPER -- see below
   39,235  demo/T-10_sophisticated.txt  NOT hashed
   38,993  demo/template.txt            NOT hashed
   38,991  demo/T-07_aggressive.txt     NOT hashed
   38,660  demo/T-01_clean.txt          NOT hashed
   37,768  demo/T-03_obvious.txt        NOT hashed
   15,950  app_audit_shared.js          hashed
   12,975  app_docview_shared.js        hashed
    9,784  app_shared.js                hashed
    9,049  app_docview_render_shared.js hashed
    7,119  app_summary_shared.js        hashed
    5,180  app_workflow_shared.js       hashed
    1,264  app_notes_shared.js          hashed
```

`static/icons/` exists and is **empty**.

## Not content-hashed and would go stale under caching

**(a) The five `demo/*.txt` files, ~194 KB.** Fetched at runtime by `app.js:16006`:

```javascript
        const resp = await fetch('/static/demo/template.txt');
```

No `?v=`, so nothing to stamp, and no `Cache-Control` today. **Low harm — they are demo fixtures whose
content is inert — but they are the honest answer to "what would go stale".**

**(b) `/static/index.html` is directly reachable and serves the UNSTAMPED file** — the hand-maintained
literals `?v=400`, `?v=475`. Nothing links to it, but nothing blocks it either, and it currently has no
`Cache-Control`.

**(c) `/results/{job_id}` DOES NOT STAMP. This is a defect I shipped at Step 550.**

```
serve_index          stamps: True
serve_results_page   stamps: False
```

`main.py:2542` reads `index_path.read_bytes()` raw. **Step 550 patched one of the two shell routes and I
reported it as though it covered the page.** It is the route in every `results_url` we email:
`{APP_BASE_URL}/results/{job_id}`.

**Under `no-store` this is invisible.** Under caching it is not: `/` would reference
`app.js?v=7d09466604` and the results page `app.js?v=475`, **two URLs for the same asset**, and the
results page's URL never changes again — so a stale copy cached under `?v=475` would persist
indefinitely. **This must be fixed before `no-store` comes off.**

---

# 2. THE PROPOSED SPLIT

| what | header | why |
|---|---|---|
| `/` and `/results/{job_id}` (the shell) | `no-cache, no-store, must-revalidate` — **unchanged** | It carries the hashes. Caching it caches the pointers, and every downstream asset freezes with it. |
| `.js` / `.css` under `/static` | `public, max-age=31536000, immutable` | The URL changes when the bytes change. `immutable` additionally suppresses revalidation on reload. |
| `demo/*.txt` | `public, max-age=3600` | Not hashed, so it must expire on time rather than on URL. One hour bounds staleness without re-fetching per load. |
| everything else under `/static` | `public, max-age=3600` | Conservative default for anything added later that nobody remembered to hash. |

**The default matters more than the aggressive case.** `NoCacheStaticFiles` currently keys on
`endswith(('.js','.css'))`, so a new asset type gets whatever Starlette does. The replacement should
**allow-list what may be cached forever and give everything else a short TTL** — fail-safe, not
fail-fast.

**`immutable` is the load-bearing token,** not `max-age`. Without it, a reload revalidates every asset:
nine conditional requests returning 304, which on a 1.3 MB payload saves the bytes but not the round
trips.

---

# 3. WHAT THE STEP-550 TEST DOES AND DOES NOT GUARANTEE

**It does not assert the hash matches the bytes.** Exercised, not reasoned:

```
stamped with a WRONG but SELF-CONSISTENT hash ("deadbeef00")
   -> the Step-550 assertion finds 0 stale.  THE SUITE PASSES.
   sample stamped value: deadbeef00
```

`test_no_literal_version_survives` computes the expected value by calling **the same
`asset_version` the stamper called**. It proves the stamping *ran*; it cannot detect a hash function
that is wrong, because it asks the wrong function what right looks like. **That is a tautology I wrote
and did not notice at Step 550.**

The check that would catch it — an **independent** `sha256` of each file on disk against the stamped
value — reports **0 mismatches today** but **is not in the suite**.

## And the cache has a real failure mode, demonstrated

```
same size, same mtime, different bytes:
   v1=63c1dd951f   v2=63c1dd951f   cache returned a STALE hash: True
   true sha256 of the new bytes:  4a8d8134f2
```

`asset_version` caches on `(mtime_ns, size)`. **When both are unchanged and the content is not, it
returns the previous hash.** My Step-550 test *defeats* this cache with `os.utime(asset, (0,0))` to
force a recompute, so **the cache's failure mode is untested by construction.**

**How bad is it in production?** Low, and for a structural reason worth stating: Railway ships an
immutable container per deploy, so the process starts with an empty cache and the asset cannot change
underneath it. The exposure is local `uvicorn --reload` and any future deploy model that writes assets
into a running container. **It is a latent bug, not a live one — the same shape as the thing Step 550
fixed.**

## The asymmetry the brief names is the crux

Under `no-store` a wrong hash is **cosmetic**. Under caching it is **self-reinforcing**: the browser
caches bytes under a URL, the URL only changes when the hash changes, and a hash that is wrong-but-stable
never changes. **A user can be pinned to a broken build with no recovery short of a hard refresh they
have no reason to perform.**

**Three things must exist before that trade is acceptable:**

1. An independent hash-binding test (`sha256(file) == stamped value`, computed without calling
   `asset_version`).
2. `serve_results_page` stamping.
3. Either drop the `(mtime_ns, size)` cache or key it on something that cannot collide.

**None of the three exists today.**

---

# 4. THE BENEFIT, MEASURED

## Page loads per lease: 2–3, not 1

Three routes serve the shell — `/` (`main.py:337`), `/results/{job_id}` (`:2542`), and
`/static/index.html`. A realistic session is:

```
1. open /            upload the lease
2. open /results/... the emailed link, usually a later session -> a COLD load
3. re-open results   jobs live 7 days (JOB_EXPIRY / expires_at)
```

**Step 2 is the one caching cannot help**, because it is typically a different session on a different
day, and — today — a different URL for the same assets (§1c).

## Traffic

```
/api/jobs on the deployed service -> 1 job, created 2026-09-03
```

**That is my own Step-549 run.** There is no production traffic to optimise. Any bandwidth argument is
about a hypothetical future user.

## What each measure is actually worth, per load

```
                              first load        repeat load
today                          1,370 KB           1,370 KB
+ gzip                           292 KB             292 KB
+ gzip + immutable caching       292 KB              ~0 KB
```

**gzip: 1,053 KB saved on every load. Caching: a further 292 KB, on repeat loads only.**

**The brief's "1.25 MB per page load" is right about today and wrong about the prize.** Removing
`no-store` without compressing first would leave 1,370 KB on every cold load — including the emailed
results link, the load a lawyer is most likely to make.

---

# 5. IS IT WORTH DOING? — NOT YET, AND NOT FIRST

**Recommended order:**

1. **Add `GZipMiddleware`.** One line, no cache semantics, **1,053 KB per load**, helps the cold load
   caching cannot reach. **This is the whole benefit at a fraction of the risk.**
2. **Fix `serve_results_page`** to stamp. It is a Step-550 defect regardless of caching.
3. **Add the independent hash-binding test** and remove or re-key the `(mtime_ns, size)` cache.
4. **Only then** consider the header split in §2 — for 292 KB on repeat loads.

**I would do 1–3 and stop.** Step 4's remaining benefit is 292 KB against a failure mode that pins a
user to a broken build, on a service with one recorded job. **The ratio does not justify it yet.** It
becomes worth doing when there is traffic, and steps 2 and 3 are the honest precondition either way.

---

# WHAT IS NOT ESTABLISHED

- **Nothing was built or changed**, per the brief.
- **`serve_results_page` not stamping is a defect I introduced at Step 550** by patching one of two
  routes and reporting it as covered. It is unfixed.
- **The gzip figures are local `gzip.compress(level=6)`**, not measured through the server. Starlette's
  `GZipMiddleware` uses the same zlib at level 9 by default, so the real saving should be slightly
  better — **but I have not run it through the middleware and cannot state the served number.**
- **Brotli was not measured.** `Accept-Encoding: br` was sent and nothing came back; whether Railway's
  edge could add it was not investigated.
- **The 2–3 page loads per lease figure is reasoning from the routes and the 7-day expiry, not
  telemetry.** No request logs were consulted; I do not have access to them.
- **The `(mtime_ns, size)` collision is demonstrated in a temp directory with `os.utime`**, not observed
  in a build. Whether nixpacks normalises mtimes was not checked.
- **`demo/*.txt` staleness is judged low-harm on the grounds that the files are inert fixtures.** I did
  not verify that no code path treats their content as significant beyond pre-filling a demo upload.
- **No measurement of what `immutable` does in the browsers this app's users run.** It is well
  supported; I did not test it.
