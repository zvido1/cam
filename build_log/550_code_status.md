# Step 550 — Nine strings, not one. The stale file is `style.css`, not `app.js`. And the whole mechanism has been inert since the first deployment.

**Date:** 2026-09-03 · **Instruction:** `build_log/550_chat_instruction.md`
**Tests: 433 passed, 3 skipped, 12 subtests (427 → 433; 6 new). Not deployed.**

---

# 0. THE FINDING THAT REFRAMES THE BRIEF

**`?v=` has never busted a cache on this deployment.** `NoCacheStaticFiles` (`main.py:264`) sets
`Cache-Control: no-store, no-cache, must-revalidate` on every `.js` and `.css`, and it has been there
since `ec692d3` — **"Initial deployment: CAM Lease Analyzer", 2026-03-16.**

Verified against the live service, not read:

```
/static/style.css?v=400   HTTP 200   363,785 bytes
      Cache-Control: no-store, no-cache, must-revalidate
      Pragma: no-cache        Expires: 0
/static/app.js?v=475      HTTP 200   912,481 bytes
      Cache-Control: no-store, no-cache, must-revalidate
```

**`no-store` instructs the browser not to keep the response at all.** So the brief's *"a returning user
would have seen the old summary against new data"* **is not supported** — a returning user re-fetches
both files on every page load regardless of the query string.

**That does not make the fix pointless; it changes what it is for.** `no-store` is an expensive policy —
**1.25 MB of JS and CSS re-downloaded on every single page load** — and the only reason to keep it is
that the versioning underneath was not trustworthy. Making the versions automatic is the precondition
for turning caching back on. **It is a latent defect made safe, not a live one fixed**, and I would
rather say so than let the urgency stand uncorrected.

---

# 1. NINE STRINGS. THE STALE ONE IS `style.css`.

```
asset                              v   file last changed    v last bumped     commits since bump
style.css                        400   2026-08-30 9a74222   2026-06-04 b053c80          5
app_shared.js                      4   2026-05-01 7120ef8   2026-05-01 7120ef8          0
app_audit_shared.js               12   2026-03-22 ff68f7c   2026-03-22 ff68f7c          0
app_workflow_shared.js             2   2026-05-01 7120ef8   2026-03-20 aef28ac          1
app_docview_shared.js             10   2026-04-26 4aaa8c3   2026-04-26 4aaa8c3          0
app_docview_render_shared.js       3   2026-03-22 ff68f7c   2026-03-20 eb46b22          1
app_summary_shared.js             10   2026-04-26 4aaa8c3   2026-04-26 4aaa8c3          0
app_notes_shared.js                1   2026-03-16 77723df   2026-03-16 77723df          0
app.js                           475   2026-09-02 e9d1b34   2026-09-02 e9d1b34          0
```

**Three are stale. `style.css` is 87 days and five commits behind** — Steps 398, 400, 402, 477 and 497
all changed it after its last bump on 2026-06-04.

## The brief names the wrong failures — and the real ones are worse

**Step 522 DID bump.** `7b256f3` contains:

```
-    <script src="/static/app.js?v=473"></script>
+    <script src="/static/app.js?v=474"></script>
```

**Step 539 never touched a frontend file.** It changed `05 Lease Analyzer/app/summary_generator.py` —
Python that generates the summary DOCX and PDF server-side. Nothing a browser caches.

**The two that actually failed are Steps 477 and 497**, and each failed harder than described:

```
4fc4fce  477  touched: static/app.js, static/index.html, static/style.css   -> bumped NOTHING
9a74222  497  touched: static/app.js, static/index.html, static/style.css   -> bumped NOTHING
```

**Both changed three frontend files and moved no version.** `app.js` was rescued incidentally when Step
522 bumped it for its own change — any bump busts, so the sequence self-heals for whichever file the
next author happens to think about. **`style.css` has never been that file.**

**That is the shape of the defect: the bumps that do happen cover the file the author has in mind, not
the files the commit changed.**

---

# 2. CONTENT HASH — AND `GIT_SHA` IS THE ONE I RULED OUT

Every `/static/<file>?v=...` in the served HTML is now rewritten with a 10-character SHA-256 prefix of
the file it points at.

```python
_ASSET_REF_RE = re.compile(rb'(/static/([A-Za-z0-9_.\-]+))\?v=[0-9A-Za-z._\-]+')

def asset_version(name, root=None):     # cached on (mtime_ns, size)
def stamp_asset_versions(html, root=None) -> bytes
```

`serve_index()` now returns `stamp_asset_versions(index_path.read_bytes())`.

## Why not `GIT_SHA`

`GIT_SHA` is already in `config.py:37` and would have been one line. **It changes on every deploy,
including deploys that touch no frontend file.** Step 548 pushed **11 commits of which exactly one
touched a static asset** — under `GIT_SHA` that deploy would have invalidated 1.25 MB of JS and CSS for
every user, to ship a change none of it contained. **The hash moves when, and only when, the bytes
move**, which is the property the mechanism is supposed to have.

`test_same_bytes_same_version` locks that in: it touches the file's mtime, leaves the contents alone,
and asserts the version does not move. **That test fails under a `GIT_SHA` implementation.**

## Why request-time, not build-time

There is no build step — Railway runs `uvicorn` against the repo. A build-time generator would need one,
plus a committed artefact that can itself go stale, which is the same failure one layer out.

**Cost, paid once and cached:** the hash is keyed on `(mtime_ns, size)`, so a warm process does two
`stat()` calls per asset per page load and no reads. Cold cost is nine SHA-256s over 1.3 MB.

**It fails open.** A missing or unreadable asset leaves its literal `?v=` untouched rather than raising
— the page must still serve. **The test, not a 500, is what surfaces a stale literal.**

---

# 3. THE TEST — IT READS THE SERVED BYTES, NOT THE FILE

`cam/adapters/lease_review/tests/test_550_asset_versions.py`, 6 tests:

| test | what it makes impossible |
|---|---|
| `test_no_literal_version_survives` | a `?v=` in the served page that is not the asset's current content hash |
| `test_version_moves_when_the_file_changes` | the exact failure of Steps 477 and 497 |
| `test_same_bytes_same_version` | reintroducing `GIT_SHA`-style over-invalidation |
| `test_every_reference_resolves_to_a_real_file` | a `<script>` pointing at a deleted asset |
| `test_missing_asset_fails_open` | a missing asset taking down the index route |
| `test_non_static_urls_are_untouched` | rewriting a CDN or third-party URL |

It imports the two functions by extracting them from `main.py` and `exec`-ing them alone, so it does not
require FastAPI, the router, or the provider config to be importable. **A pure unit test of a pure
function.**

---

# 4. VERIFIED BY EXERCISE

## The literal values, against content — all nine were wrong

```
style.css                        literal ?v=400    content-hash=630d438920  STALE
app_shared.js                    literal ?v=4      content-hash=b84061c166  STALE
app_audit_shared.js              literal ?v=12     content-hash=8201ee7aaa  STALE
app_workflow_shared.js           literal ?v=2      content-hash=055d5d0907  STALE
app_docview_shared.js            literal ?v=10     content-hash=8f4130efc9  STALE
app_docview_render_shared.js     literal ?v=3      content-hash=10470a3a60  STALE
app_summary_shared.js            literal ?v=10     content-hash=e39c99f079  STALE
app_notes_shared.js              literal ?v=1      content-hash=26ca9177bb  STALE
app.js                           literal ?v=475    content-hash=7d09466604  STALE
```

**"9 of 9 stale" is a statement about the sequence numbers not being hashes, not about nine broken
files** — the sequence never encoded content. The git measurement in §1 is the one that says which
files a user could actually have been served wrongly.

## The proof the test can fail

```
assertion run against UNSTAMPED bytes -> 9 of 9 stale
   test_no_literal_version_survives would FAIL
```

**Run against the file as it is on disk — the pre-Step-550 behaviour — the test fails.** It only passes
because the stamping happens.

## The mutation

```
before       : style.css ?v=630d438920
after edit   : style.css ?v=dc867b0306   MOVED=True
served page  : style.css ?v=dc867b0306   matches new hash=True
restored     : style.css ?v=630d438920   back to original=True
```

**A byte appended to `style.css` moved the version and moved it in the served page.** The file was
restored and the restore was asserted.

## The real route, invoked

```python
>>> r = app.main.serve_index()
serve_index -> Response  80,776 bytes   Cache-Control: no-cache, no-store, must-revalidate
refs stamped: 9
literal ?v=475 present in served body: False
```

**Not the helper — `serve_index()` itself.** Nine references stamped, no literal survives, the existing
cache header is unchanged.

---

# WHAT IS NOT ESTABLISHED

- **The premise that a user saw stale assets is NOT supported**, and I did not find evidence for it.
  `no-store` has been live since 2026-03-16. §0.
- **`no-store` was left in place.** Removing it is the change that would make this work *matter*, and it
  is a user-visible performance decision (1.25 MB per page load) that belongs in its own brief. **This
  step makes that change safe to consider; it does not make it.**
- **The nine literals still sit in `index.html` on disk.** They are overwritten at serve time and never
  read as authority. I left them rather than deleting them so the file still works when opened directly
  from the filesystem, and so the diff stays small — **but they are now decorative, and a future author
  bumping one by hand will have no effect.** A comment in `index.html` saying so would be worth adding;
  I did not add one because the brief said not to widen.
- **`CLAUDE.md`'s Git Workflow section still says "The `index.html` version bump applies only to frontend
  changes."** That rule is now obsolete for `?v=`. **I did not edit `CLAUDE.md`** — it is not mine to
  change unilaterally — but it should be updated or it will send a future session to do work the code now
  does.
- **Not deployed**, per the brief. The stamping has never run in production.
- **Only `index.html` is stamped.** It is the only HTML file in `static/`, verified, but any future page
  added outside `serve_index()` would not be covered.
- **The 10-character prefix is a choice, not a measurement.** Collision risk is negligible for nine
  files; I did not compute a bound.
