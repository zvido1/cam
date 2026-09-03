# Step 552 — 1.38 MB → 298 KB. Both shell routes stamp. The new test fails where the old one passed, exercised.

**Date:** 2026-09-03 · **Instruction:** `build_log/552_chat_instruction.md`
**Tests: 437 passed, 3 skipped, 12 subtests (433 → 437; 4 new). `no-store` unchanged. No caching header added. Not deployed.**

---

# 1. COMPRESSION — 1,056 KB PER PAGE LOAD, MEASURED THROUGH THE MIDDLEWARE

```python
app.add_middleware(GZipMiddleware, minimum_size=500)
```

Measured by driving the ASGI interface and collecting the raw `http.response.body` chunks — **the bytes
the app emits, before any client-side decoding:**

```
  identity (compression off)   wire bytes = 1,370,065   Content-Encoding=None
  gzip                         wire bytes =   288,630   Content-Encoding=gzip
  saving                           1,056 KB per page load (78.9%)

  /                      identity= 80,776  gzip=16,325
  /results/testjob123    identity= 80,776  gzip=16,325

  per-asset:
    app.js                        931,328 -> 211,606 (22.7%)
    style.css                     377,416 ->  60,343 (16.0%)
    app_audit_shared.js            15,950 ->   4,476 (28.1%)
    app_docview_shared.js          12,975 ->   3,026 (23.3%)
    app_shared.js                   9,784 ->   3,321 (33.9%)
    app_docview_render_shared.js    9,049 ->   2,095 (23.2%)
    app_summary_shared.js           7,119 ->   1,925 (27.0%)
    app_workflow_shared.js          5,180 ->   1,285 (24.8%)
    app_notes_shared.js             1,264 ->     553 (43.8%)
```

**Whole page load, shell included: 1,450,841 → 304,955 bytes. 1.38 MB → 298 KB.**

## A false alarm in my own first measurement, recorded

My first attempt used `TestClient` and reported **44 KB saved (3.3%)** — I nearly wrote that down.
**It was a measurement artefact:** Starlette's `GZipMiddleware` drops `Content-Length` on streamed
responses and httpx transparently decodes the body, so `len(response.content)` was the *decoded* size
and my content-length fallback returned it. **A 3.3% gzip ratio on JavaScript is not believable, which
is what made me look again.** Driving ASGI directly gives the real number.

## The deployed "after" is NOT measured

**The brief asked for before-and-after against the deployed service. The "before" is deployed and
measured (Step 551: `Content-Encoding: None`, 1,337,587 bytes). The "after" is not — this brief carries
no push sanction and I did not push.** The figures above come from the real middleware stack running
the committed code locally. **They are a measurement, not a computation, but they are not a measurement
of production.**

## Why `minimum_size=500`

It is Starlette's default, stated explicitly rather than inherited silently: below it the gzip header
and CPU cost exceed the saving. Every asset above is far past it; `app_notes_shared.js` at 1,264 bytes
is the smallest and still compresses to 43.8%.

---

# 2. BOTH SHELL ROUTES STAMP

**Every route in `main.py` that reads `index.html`:**

| route | line | stamps |
|---|---|---|
| `serve_index` — `GET /` | `main.py:337` | **yes** (Step 550) |
| `serve_results_page` — `GET /results/{job_id}` | `main.py:2542` | **yes — fixed here** |

Exercised on both:

```
  /                      HTTP 200  stamped_refs=9  literal_v475=False  CC=no-cache, no-store, must-revalidate
  /results/testjob123    HTTP 200  stamped_refs=9  literal_v475=False  CC=no-cache, no-store, must-revalidate
```

**This was mine.** Step 550 patched `serve_index` and reported it as covering the page; the results
route — the one in every emailed `results_url` — kept serving the hand-maintained literals.

`test_every_route_serving_index_html_stamps` now scans `main.py` by `@app.` decorator block and fails on
any block that reads `index.html` without calling the stamper. **Written as a scan, not a list of the
two route names, because a third route added tomorrow is exactly the case Step 550 missed.**

**`/static/index.html` remains reachable and unstamped** — Starlette's `StaticFiles` serves it directly.
Nothing links to it. Under `no-store` it is inert; **it would need blocking before any caching change**,
and it is recorded here rather than fixed because the brief scoped this step to the shell routes.

---

# 3. THE INDEPENDENT TEST — AND THE EXERCISE THE BRIEF ASKED FOR

The old assertion asked `asset_version` what the right answer was, and `asset_version` is the thing that
might be wrong. The new one reads the file and hashes it in the test.

```
stamped with a wrong-but-self-consistent hash:
   sample -> deadbeef00

--- THE OLD (Step-550) ASSERTION, run against those bytes ---
   stale found: 0  ->  PASSES (blind)

--- THE NEW (Step-552) INDEPENDENT ASSERTION, same bytes ---
   mismatches found: 9  ->  FAILS (catches it)
      style.css            stamped=deadbeef00  true sha256=630d438920
      app_shared.js        stamped=deadbeef00  true sha256=b84061c166
      app_audit_shared.js  stamped=deadbeef00  true sha256=8201ee7aaa

--- the same independent check against the REAL stamper ---
   PASSES
```

**The old test passes blind on all nine. The new one fails on all nine.** That exercise is now a
permanent test (`test_a_self_consistent_but_wrong_hash_is_caught`), which asserts both that the bogus
stamper took effect *and* that the independent check rejects it — so the test cannot pass by failing to
set up its own scenario.

Four tests added:

| test | what it makes impossible |
|---|---|
| `test_served_url_carries_the_hash_of_the_served_bytes` | a version that is not `sha256(file)[:10]` |
| `test_a_self_consistent_but_wrong_hash_is_caught` | the Step-550 blindness returning |
| `test_no_stale_hash_when_size_and_mtime_do_not_move` | the cache defect of §4 returning |
| `test_every_route_serving_index_html_stamps` | a new shell route that forgets to stamp |

---

# 4. THE CACHE — REMOVED, NOT RE-KEYED

```python
def asset_version(name: str, root=None) -> Optional[str]:
    """Short content hash for a static asset. Computed from the bytes, every time."""
    base = root if root is not None else static_dir
    try:
        return hashlib.sha256((base / name).read_bytes()).hexdigest()[:10]
    except (OSError, ValueError):
        return None
```

**No key is correct, so there is no key.** Measured cost of hashing all nine assets from scratch, per
page load:

```
  read from disk   0.80 ms
  sha256           0.60 ms
  total            1.39 ms
```

**The brief is right that this is not free — it is 1.39 ms.** Against a page load that already reads
`index.html` from disk and now ships 298 KB, that buys the removal of an entire failure class.

## The keys I considered and rejected

- **`(mtime_ns, size)`** — the Step-550 key. Step 551 demonstrated it returning a stale hash when a file
  changed with both unchanged. `test_no_stale_hash_when_size_and_mtime_do_not_move` now fails on it.
- **Permanent, process-lifetime** — correct in production, because Railway ships an immutable container
  per deploy and the process starts with an empty cache. **Wrong under `uvicorn --reload`**, where an
  edited asset would keep its old hash and a developer would chase a phantom. **Correct everywhere beats
  fast and conditional**, especially for a mechanism whose entire purpose is to be trustworthy without
  anyone thinking about it.
- **`(mtime_ns, size, st_ino)`** — does not address the demonstrated case at all; the inode is unchanged
  by a rewrite in place.

**If 1.39 ms ever matters, the right move is a boot-time computation plus an explicit dev override —
not a heuristic key.** It does not matter today.

---

# 5. `CLAUDE.md` — THE OBSOLETE INSTRUCTION IS REPLACED

The section read:

> *"The `index.html` version bump applies **only to frontend changes**. Backend, pipeline, investigation,
> and spec steps do not touch it and are not gated on it."*

It now opens **"### Version numbers — DO NOT HAND-BUMP"**, states that the literals are decorative and
that editing one has no effect, names both stamping routes, and carries the same
*"if you recall this file saying otherwise, you are recalling the old, wrong version"* construction the
Git Workflow section already uses for the `git add -A` correction. It also records **why** the old rule
was worth removing rather than merely relaxing:

> *"That instruction described a discipline that had already failed twice unnoticed — Steps 477 and 497
> each changed `app.js`, `index.html` and `style.css` and bumped nothing, leaving `style.css?v=400`
> 87 days and five commits stale."*

and adds the forward-looking rule the new test enforces: **do not add a route that serves `index.html`
without calling `stamp_asset_versions`.**

---

# WHAT IS NOT ESTABLISHED

- **The deployed "after" is unmeasured.** §1. No push sanction in this brief; the gzip figures are from
  the committed code running locally through the real middleware, not from production.
- **`no-store` is unchanged and no caching header was added**, per the brief. The 298 KB that caching
  would save on repeat loads is still on the table and still gated on Step 551's remaining condition —
  which this step has now met, so the blocker is down to `/static/index.html` and a traffic case.
- **`/static/index.html` still serves the unstamped literals.** Recorded at Step 551, unfixed, inert
  under `no-store`.
- **The five `demo/*.txt` are still not content-hashed** and still carry no `Cache-Control`. Irrelevant
  under `no-store`; a precondition for caching.
- **Brotli was not attempted.** `GZipMiddleware` is gzip only; whether Railway's edge could add `br` was
  not investigated.
- **The 1.39 ms hashing cost is measured on this machine with a warm OS page cache.** A cold container
  filesystem read may be slower on the first request after a deploy; I did not measure that.
- **No browser was opened.** The stamping and compression are verified at the HTTP layer, not by loading
  the page and confirming it renders.
