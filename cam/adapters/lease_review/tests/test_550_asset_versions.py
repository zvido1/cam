"""Step 550: asset cache-bust versions are stamped from content, and no literal survives.

Measured at Step 550, on the repository as it stood:

    style.css                     v=400  last bumped 2026-06-04, file changed in
                                         FIVE commits since (398, 400, 402, 477, 497)
    app_workflow_shared.js        v=2    1 commit behind
    app_docview_render_shared.js  v=3    1 commit behind

Steps 477 and 497 each changed `app.js`, `index.html` AND `style.css` and bumped
no version at all. Step 522 bumped app.js 473->474 and Step 533 474->475, which
is why app.js is current and style.css is not -- the bumps that did happen only
ever covered the file the author was thinking about.

`test_no_literal_version_survives` is the one that makes the discipline
non-optional: it reads the SERVED html, not the file on disk, and fails if any
`?v=` is not the current content hash of the asset it points at. A frontend file
that changes without its version moving cannot pass it.

Deterministic, no network, no app startup.
"""
import hashlib
import importlib.util
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

CAM_ROOT = Path(__file__).resolve().parents[4]
STATIC = CAM_ROOT / "05 Lease Analyzer" / "static"


def _load_stamper():
    """Import `stamp_asset_versions`/`asset_version` without importing the whole app.

    `app.main` pulls in FastAPI, the router, every adapter and the provider
    config at import time. The two functions under test are pure, so they are
    extracted and exec'd on their own -- the test stays a unit test and does not
    depend on the service being importable.
    """
    src = io.open(CAM_ROOT / "05 Lease Analyzer" / "app" / "main.py", encoding="utf-8").read()
    start = src.index("_ASSET_VERSION_CACHE: dict = {}")
    end = src.index('@app.get("/")', start)
    ns = {"hashlib": hashlib, "re": re, "static_dir": STATIC,
          "Optional": __import__("typing").Optional}
    exec(compile(src[start:end], "<asset_versions>", "exec"), ns)
    return ns


NS = _load_stamper()
stamp_asset_versions = NS["stamp_asset_versions"]
asset_version = NS["asset_version"]

_REF = re.compile(rb'/static/([A-Za-z0-9_.\-]+)\?v=([0-9A-Za-z._\-]+)')


class TestStamping(unittest.TestCase):

    def test_no_literal_version_survives(self):
        """Every ?v= in the SERVED html is the current content hash of its asset."""
        served = stamp_asset_versions((STATIC / "index.html").read_bytes())
        refs = _REF.findall(served)
        self.assertTrue(refs, "index.html has no /static/...?v= references to check")
        stale = []
        for name, ver in refs:
            name = name.decode()
            want = asset_version(name)
            if want is None:
                continue                       # asset absent: fails open by design
            if ver.decode() != want:
                stale.append((name, ver.decode(), want))
        self.assertEqual(stale, [], "asset versions not stamped from content: %r" % (stale,))

    def test_every_reference_resolves_to_a_real_file(self):
        raw = (STATIC / "index.html").read_bytes()
        missing = [n.decode() for n, _ in _REF.findall(raw)
                   if not (STATIC / n.decode()).exists()]
        self.assertEqual(missing, [], "index.html references assets that do not exist")

    def test_version_moves_when_the_file_changes(self):
        """The property the hand-maintained string failed to hold, exercised."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            asset = root / "app.js"
            asset.write_bytes(b"console.log(1)")
            html = b'<script src="/static/app.js?v=475"></script>'

            before = stamp_asset_versions(html, root)
            v1 = _REF.findall(before)[0][1]

            asset.write_bytes(b"console.log(2)")
            os.utime(asset, (0, 0))            # defeat the (mtime, size) cache
            after = stamp_asset_versions(html, root)
            v2 = _REF.findall(after)[0][1]

            self.assertNotEqual(v1, v2, "version did not move when the file changed")
            self.assertNotIn(b"?v=475", after, "the hand-maintained literal survived")

    def test_same_bytes_same_version(self):
        """A backend-only deploy must not invalidate the cache -- the GIT_SHA failure mode."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "app.js").write_bytes(b"console.log(1)")
            html = b'<script src="/static/app.js?v=1"></script>'
            first = stamp_asset_versions(html, root)
            os.utime(root / "app.js", (0, 0))   # touched, contents identical
            self.assertEqual(first, stamp_asset_versions(html, root))

    def test_missing_asset_fails_open(self):
        with tempfile.TemporaryDirectory() as d:
            html = b'<script src="/static/nope.js?v=9"></script>'
            self.assertEqual(stamp_asset_versions(html, Path(d)), html)

    def test_non_static_urls_are_untouched(self):
        html = b'<a href="https://cdn.example.com/lib.js?v=3">x</a>'
        self.assertEqual(stamp_asset_versions(html, STATIC), html)


if __name__ == "__main__":
    unittest.main()
