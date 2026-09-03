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
    start = src.index("_ASSET_REF_RE = re.compile(")
    end = src.index('@app.get("/")', start)
    ns = {"hashlib": hashlib, "re": re, "static_dir": STATIC,
          "Optional": __import__("typing").Optional}
    exec(compile(src[start:end], "<asset_versions>", "exec"), ns)
    ns["_SOURCE"] = src[start:end]
    return ns


NS = _load_stamper()
stamp_asset_versions = NS["stamp_asset_versions"]
asset_version = NS["asset_version"]

_REF = re.compile(rb'/static/([A-Za-z0-9_.\-]+)\?v=([0-9A-Za-z._\-]+)')


class TestHashBinding(unittest.TestCase):
    """Step 552: the expected hash is computed HERE, not by the code under test.

    Step 551 exercised the Step-550 assertion against a stamper whose hash
    function returned the constant "deadbeef00" for every asset, and it PASSED --
    because `test_no_literal_version_survives` asks `asset_version` what the right
    answer is, and `asset_version` is the thing that might be wrong. It proves the
    stamping ran; it cannot prove the version means anything.

    These tests read the file and hash it independently. A wrong-but-self-
    consistent hash fails them.
    """

    def _independent(self, name, root=None):
        base = root if root is not None else STATIC
        return hashlib.sha256((base / name).read_bytes()).hexdigest()[:10]

    def test_served_url_carries_the_hash_of_the_served_bytes(self):
        served = stamp_asset_versions((STATIC / "index.html").read_bytes())
        refs = _REF.findall(served)
        self.assertTrue(refs)
        wrong = []
        for name, ver in refs:
            name = name.decode()
            if not (STATIC / name).exists():
                continue
            expected = self._independent(name)
            if ver.decode() != expected:
                wrong.append((name, ver.decode(), expected))
        self.assertEqual(wrong, [], "stamped version is not sha256(file)[:10]: %r" % (wrong,))

    def test_a_self_consistent_but_wrong_hash_is_caught(self):
        """The exercise Step 551 ran, made permanent.

        Build a stamper whose version function is stable, plausible, and has
        nothing to do with the bytes -- exactly the shape the Step-550 assertion
        could not see -- and assert the independent check rejects it.
        """
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "app.js").write_bytes(b"console.log(1)")
            html = b'<script src="/static/app.js?v=475"></script>'

            def _wrong(name, root=None):
                return "deadbeef00"

            ns = dict(NS)
            ns["asset_version"] = _wrong
            exec(compile(NS["_SOURCE"], "<wrong>", "exec"), ns)
            ns["asset_version"] = _wrong
            served = ns["stamp_asset_versions"](html, root)

            self.assertIn(b"?v=deadbeef00", served,
                          "the wrong stamper did not take effect; the test proves nothing")
            name, ver = _REF.findall(served)[0]
            self.assertNotEqual(ver.decode(), self._independent(name.decode(), root),
                                "an independent hash check failed to reject a bogus version")

    def test_no_stale_hash_when_size_and_mtime_do_not_move(self):
        """Step 551 demonstrated the (mtime_ns, size) cache returning a stale hash."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            asset = root / "app.js"
            asset.write_bytes(b"AAAA")
            os.utime(asset, (1000, 1000))
            v1 = asset_version("app.js", root)
            asset.write_bytes(b"BBBB")
            os.utime(asset, (1000, 1000))          # same size AND same mtime
            v2 = asset_version("app.js", root)
            self.assertNotEqual(v1, v2, "asset_version returned a cached, stale hash")
            self.assertEqual(v2, self._independent("app.js", root))


class TestShellRoutesStamp(unittest.TestCase):
    """Step 552: BOTH shell routes stamp. Step 550 patched one and reported both."""

    def test_every_route_serving_index_html_stamps(self):
        """Any route that reads index.html must pass it through the stamper.

        Written as a scan rather than a list of route names on purpose: a route
        added tomorrow that serves the shell is exactly the case Step 550 missed,
        and naming the two we know about would not catch a third.
        """
        src = io.open(CAM_ROOT / "05 Lease Analyzer" / "app" / "main.py",
                      encoding="utf-8").read()
        blocks = src.split("\n@app.")
        offenders = []
        for block in blocks[1:]:
            if 'static_dir / "index.html"' not in block:
                continue
            if "stamp_asset_versions" in block:
                continue
            first_line = block.split("\n", 1)[0]
            offenders.append(first_line.strip())
        self.assertEqual(offenders, [],
                         "route(s) serve index.html without stamping: %r" % (offenders,))


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
