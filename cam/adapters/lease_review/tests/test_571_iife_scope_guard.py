"""Step 571-impl: no code after the app.js IIFE may read IIFE-scoped module state.

WHAT HAPPENED. `app.js` wraps the whole application in `(() => { ... })()` closing
at line 18776. Step 477 (`4fc4fce`, 2026-08-24) appended two banner functions
AFTER that close, in global scope, and both read `currentResults` -- which is
declared `let` inside the IIFE and is therefore not in scope there. Every call
threw `ReferenceError: currentResults is not defined`.

WHY IT SURVIVED THIRTEEN DAYS IN PRODUCTION. `renderResults()` calls the first of
them at :3226, which is the FIRST render call after the pre-amble, and
`loadResults()` wraps the whole thing in a try/catch that logs to console and
continues. So the symptom was not an error page -- it was 20+ render calls and the
entire tab wiring silently not running, leaving a static shell that looks like a
page which merely has nothing to show. Three later commits touched app.js on main
without noticing (497, 522, 533).

WHAT THIS TEST DOES. Scans the region after the IIFE close for reads of any
identifier declared inside it. Position in a file is not a thing a reviewer
reliably checks, and the failure mode is silent, so it needs to be mechanical.

The fix was to parameterise (`renderIncompleteBanner(results)`), not to move the
functions inside the IIFE -- so this test also guards the choice: moving them
would pass, and so would a future function that reads module state from global
scope only if it is added carefully. This test removes the "carefully".

Deterministic. No network, no app startup, no provider calls.
"""
import re
import unittest
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[4] / "05 Lease Analyzer" / "static" / "app.js"

# Module-scope state declared inside the IIFE. Reading any of these from global
# scope is the defect. Kept explicit rather than derived: a derived list would
# silently shrink if the declaration style changed, which is the same class of
# silent failure this test exists to catch.
IIFE_SCOPED = [
    "currentResults",
    "currentJobId",
    "currentJobData",
    "currentTenantIndex",
    # Step 571-impl item 3b: a FUNCTION, added after the same defect recurred in a
    # nastier form. `esc` is the HTML escaper, defined inside the IIFE, and three
    # post-IIFE functions called it: the Step-477 incomplete-report banner, the
    # Step-497 panel-substitution banner, and the rerun banner. The first two threw
    # `ReferenceError: esc is not defined` -- but ONLY when they had content, because
    # a banner with nothing to warn about early-returns before ever reaching the
    # escaper. So the "NOT VALID FOR LEGAL ANALYSIS" disclosure broke precisely when
    # there was something to disclose, and `loadResults()` swallowed it.
    #
    # The original guard listed only state, so it passed while this was live. State
    # was never the category -- anything lexically scoped to the IIFE is.
    "esc",
]


def _load():
    return APP_JS.read_text(encoding="utf-8").split("\n")


def _iife_close_line(lines):
    """1-indexed line of the IIFE's closing `})();`, or None if the wrapper is gone."""
    closes = [i + 1 for i, l in enumerate(lines) if l.rstrip() == "})();"]
    return closes[0] if closes else None


def _strip_comment(line):
    """Drop `//` tails and whole-line block comments. Crude on purpose -- it only
    needs to stop this test tripping on its own explanatory comments."""
    s = line.strip()
    if s.startswith("//") or s.startswith("*") or s.startswith("/*"):
        return ""
    return line.split("//", 1)[0]


class TestNoIifeScopedReadsAfterClose(unittest.TestCase):

    def setUp(self):
        self.lines = _load()
        self.close = _iife_close_line(self.lines)

    def test_app_js_exists_and_is_iife_wrapped(self):
        """If the wrapper is ever removed the premise changes and the guard below
        becomes vacuous -- fail loudly rather than pass silently."""
        self.assertTrue(APP_JS.exists(), "app.js not found at %s" % APP_JS)
        self.assertIsNotNone(
            self.close,
            "app.js is no longer IIFE-wrapped. This guard assumed it was; "
            "re-derive the scope boundary before deleting the test.")

    def test_no_iife_scoped_identifier_is_read_after_the_close(self):
        """The regression itself."""
        offenders = []
        for i, raw in enumerate(self.lines):
            lineno = i + 1
            if lineno <= self.close:
                continue
            code = _strip_comment(raw)
            if not code.strip():
                continue
            for name in IIFE_SCOPED:
                # `window.CAM.esc(...)` is the legitimate, explicit crossing;
                # a BARE `esc(...)` or `currentResults` is the defect.
                if re.search(r"(?<![.\w])" + re.escape(name) + r"\b", code):
                    offenders.append("%d: %s" % (lineno, code.strip()[:90]))
        self.assertEqual(
            offenders, [],
            "code after the IIFE close (line %d) reads IIFE-scoped state. It will "
            "throw ReferenceError at runtime, and if the caller catches, silently.\n"
            "Pass the value in as a parameter instead.\n  %s"
            % (self.close, "\n  ".join(offenders)))

    def test_the_two_step_477_banners_take_a_parameter(self):
        """Pins the specific fix. Both must accept the results object rather than
        reaching for module scope."""
        src = "\n".join(self.lines)
        for fn in ("renderIncompleteBanner", "renderPanelBanner"):
            m = re.search(r"function\s+" + fn + r"\s*\(([^)]*)\)", src)
            self.assertIsNotNone(m, "%s not found" % fn)
            self.assertTrue(
                m.group(1).strip(),
                "%s() takes no parameter -- it can only be reading module scope, "
                "which is the Step-477 regression." % fn)

    def test_call_sites_pass_the_results_object(self):
        src = "\n".join(self.lines)
        for fn in ("renderIncompleteBanner", "renderPanelBanner"):
            self.assertIn(
                fn + "(currentResults)", src,
                "%s must be called with currentResults from inside the IIFE" % fn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
