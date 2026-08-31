"""Step 502 Part B: fail loudly when the local environment does not satisfy requirements.txt.

WHY THIS EXISTS
---------------
`anthropic` was declared `>=0.78.0` and locally installed at 0.75.0 -- BELOW the
declared floor -- for an unknown length of time. Nothing detected it. The
consequence was that six local runs (Steps 491/494/496/498) exercised an SDK
production never had, so they could not and did not predict that every deployed
Anthropic call was failing. Five days of production ran role A on gemini.

Step 502 found the same defect on two more packages: `google-genai` installed
1.52.0 against a declared floor of 1.74.0, and `python-docx` installed 0.8.11
against a declared floor of 1.1.0. Three of thirteen dependencies were below
their own floor and nothing said so.

WHY A TEST, NOT A HARNESS PREFLIGHT OR A SCRIPT
-----------------------------------------------
A harness preflight only runs when someone runs the harness, and the harness is
exactly what produced the six misleading local runs -- it would have been
checking the environment it was already misreporting from. A standalone script
only runs when someone remembers it, and nobody remembered for five days.

The suite runs on every step in this project, its result is quoted in every
status file, and CLAUDE.md forbids marking a step COMPLETE without pasting real
test output. Putting the check here means a drifted environment cannot reach a
status file unnoticed.

NO NETWORK, NO DEPLOY: it compares `requirements.txt` against installed
metadata via `importlib.metadata`. It never contacts an index and never asks
what the newest version is -- only whether what is installed satisfies what is
declared.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not assert that local and production resolve to the SAME version. They
cannot be compared without querying the deployed environment, which needs
network and a running service. Bounding every dependency (Part A) is what
narrows the band; this test enforces that local sits inside it.
"""
import io
import os
import re
import unittest

from importlib.metadata import version, PackageNotFoundError

try:
    from packaging.requirements import Requirement
    from packaging.version import Version
    _HAVE_PACKAGING = True
except ImportError:                                    # pragma: no cover
    _HAVE_PACKAGING = False

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
REQ = os.path.join(REPO, "requirements.txt")


def _requirement_lines():
    with io.open(REQ, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if line and not line.startswith("#"):
                yield line


class TestEnvironmentMatchesRequirements(unittest.TestCase):

    def setUp(self):
        if not _HAVE_PACKAGING:
            self.skipTest("packaging not available")
        self.assertTrue(os.path.exists(REQ), "requirements.txt not found at %s" % REQ)

    def test_every_declared_dependency_is_installed_and_satisfies_its_spec(self):
        """The check that would have caught anthropic 0.75.0 under a >=0.78.0 floor."""
        violations = []
        for line in _requirement_lines():
            req = Requirement(line)
            try:
                installed = version(req.name)
            except PackageNotFoundError:
                violations.append("%s: DECLARED %s but NOT INSTALLED" % (req.name, req.specifier))
                continue
            if not req.specifier.contains(Version(installed), prereleases=True):
                violations.append("%s: installed %s does NOT satisfy %s"
                                  % (req.name, installed, req.specifier))
        self.assertEqual(violations, [], "\n\nLocal environment does not match requirements.txt:\n"
                                         + "\n".join("  - " + v for v in violations)
                                         + "\n\nRun: pip install -r requirements.txt\n")

    def test_every_dependency_has_an_upper_bound(self):
        """Unbounded `>=` is what let Railway resolve anthropic to 1.x. Step 502."""
        unbounded = []
        for line in _requirement_lines():
            req = Requirement(line)
            ops = {s.operator for s in req.specifier}
            if not ops & {"<", "<=", "==", "~="}:
                unbounded.append("%s%s" % (req.name, req.specifier))
        self.assertEqual(unbounded, [], "\n\nDependencies with no upper bound -- a rebuild can "
                                        "resolve these to a breaking major:\n"
                                        + "\n".join("  - " + u for u in unbounded) + "\n")


if __name__ == "__main__":
    unittest.main()
