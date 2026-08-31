"""Step 509: the document gate must pass leases and reject non-leases.

WHY THIS EXISTS
---------------
Step 508 replaced the gate's retired `claude-sonnet-4-20250514` with
`claude-haiku-4-5-20251001` and verified both directions by hand. But the
negatives were ad-hoc probe strings written in that step, so a future change to
the gate prompt or model had **no regression test to fail**. Step 508 recorded
that as an open gap; this closes it.

The gate fails OPEN (`is_lease: True` on any exception, `lease_gate.py`), so a
broken gate is silent by design. Only a test that exercises the negative can
tell a working classifier from an absent one.

WHY AN NDA, AND NOT A RECIPE
----------------------------
The fixture is a **Mutual Non-Disclosure Agreement between a commercial property
owner and a capital partner**, and every detail of it is chosen to make the test
mean something:

  * It is a document that genuinely gets mis-uploaded. NDAs circulate in every
    real-estate transaction and sit in the same deal folder as the lease.
  * It shares the lease register almost completely -- Delaware LLC parties,
    recitals, defined terms in quotes, term and termination, governing law,
    notices, assignment, counterparts, a signature block. A classifier keying on
    "looks like a commercial contract" will get this wrong.
  * It even mentions real property, rent rolls and operating statements, so
    keyword overlap alone will not save the gate.
  * What it lacks is what actually makes a lease: no premises demised, no rent,
    no landlord/tenant relationship, no term of tenancy.

A recipe would pass this test with any classifier at all, which is the same
failure as the Step-504 gemini false positive one level up: a check that cannot
fail proves nothing.

COST AND PLACEMENT
------------------
**This test makes real provider calls, so it is NOT part of the default suite.**
The suite runs on every step, its output is quoted in every status file, and it
must stay call-free and fast (369 tests in ~3s). A test that spends money and
needs network on every step would get disabled the first time it flaked.

Run it deliberately:

    CAM_RUN_PROVIDER_TESTS=1 python -m pytest cam/adapters/lease_review/tests/test_509_gate_discrimination.py -v

**Cost: 3 provider calls** -- 2 leases + 1 non-lease, `claude-haiku-4-5`,
`max_output_tokens=10` each. Fractions of a cent, a few seconds.
"""
import io
import os
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
TENANTS = os.path.join(REPO, "05 Lease Analyzer", "test_data", "tenants")
NON_LEASE = os.path.join(REPO, "05 Lease Analyzer", "test_data", "non_lease")

LEASES = [
    ("atlas", os.path.join(TENANTS, "atlas_meridian_warehouse_lease.txt")),
    ("divall", os.path.join(TENANTS, "divall_wendys_mtpleasant_lease.txt")),
]
NON_LEASES = [
    ("mutual_nda", os.path.join(NON_LEASE, "mutual_nda.txt")),
]

_ENABLED = os.getenv("CAM_RUN_PROVIDER_TESTS") == "1"


def _load(path):
    return io.open(path, encoding="utf-8").read()


@unittest.skipUnless(_ENABLED, "makes real provider calls; set CAM_RUN_PROVIDER_TESTS=1")
class TestGateDiscrimination(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Keys live outside the repo (see CLAUDE.md); the harness bootstrap loads them.
        import sys
        h = os.path.join(REPO, "build_log", "_harness")
        if h not in sys.path:
            sys.path.insert(0, h)
        from run_store import bootstrap_env
        bootstrap_env()

    def test_fixtures_exist(self):
        """Runs even without keys being useful -- a missing fixture is a real failure."""
        for _, p in LEASES + NON_LEASES:
            self.assertTrue(os.path.exists(p), "fixture missing: %s" % p)

    def test_leases_classify_as_leases(self):
        from cam.adapters.lease_review.lease_gate import check_document_is_lease
        for name, path in LEASES:
            with self.subTest(fixture=name):
                r = check_document_is_lease(_load(path), {})
                self.assertTrue(r["is_lease"], "%s should classify as a lease" % name)
                self.assertFalse(r["abort"])

    def test_non_lease_classifies_as_not_a_lease(self):
        """The case the gate's fail-open makes silent. This is the whole point."""
        from cam.adapters.lease_review.lease_gate import check_document_is_lease
        for name, path in NON_LEASES:
            with self.subTest(fixture=name):
                r = check_document_is_lease(_load(path), {})
                self.assertFalse(r["is_lease"],
                                 "%s is NOT a lease and must be rejected -- a gate that "
                                 "passes everything is indistinguishable from no gate" % name)
                self.assertTrue(r["abort"])
                self.assertIn("does not appear to be a commercial lease", r["abort_message"])


if __name__ == "__main__":
    unittest.main()
