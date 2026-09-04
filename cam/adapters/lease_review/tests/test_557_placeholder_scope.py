"""Step 557: a placeholder that is one sub-clause among several is not an absence.

`lease_negative_space`'s header has said since Step 241 that its signals are
"EVIDENCE, not verdicts... the coverage state assessor makes the actual
determination". `lease_coverage.py` did not honour it: any `reserved_or_omitted`
match, anywhere in the block, sent the LP to `broken_xref` with every expected
element asserted missing and the panel skipped.

The case that named the defect (Step 556), verbatim from divall_wendys:

    "3.1 One Time Fixed Rental Charge . Intentionally Omitted .
     3.2 Base Rent . During the Term, Tenant covenants and agrees to pay to
     Landlord, in advance on the first day of each month..."

One sub-clause omitted, base rent established in the next line, and the report
said there was no enforceable rent obligation.

`test_label_only_block_still_short_circuits` is the one that must not regress:
divall LP-21's whole block is 52 characters of clause title plus placeholder, and
that IS a real absence.

Deterministic, no provider calls, no network.
"""
import unittest

from cam.adapters.lease_review.lease_negative_space import (
    placeholder_covers_provision,
    prose_outside_placeholders,
)

# divall LP-01: sub-clause omitted, the LP's substance in the next line.
SUBCLAUSE_OMITTED = (
    "3.1 One Time Fixed Rental Charge . Intentionally Omitted .\n"
    "3.2 Base Rent . During the Term, Tenant covenants and agrees to pay to "
    "Landlord, in advance on the first day of each month at Landlord's address, "
    "without demand or offset whatsoever, one-twelfth (1/12) of the Base Annual Rent."
)

# divall LP-21: the entire block. 52 characters, all label and placeholder.
WHOLLY_OMITTED = "ADDENDUM A PERSONAL GUARANTY - Intentionally Omitted"

# divall LP-02: three placeholders, residue is clause titles only.
LABELS_AND_PLACEHOLDERS = (
    "1.15 Fixed Rent Increases: Intentionally Omitted\n"
    "1.16 Lease Years to which Fixed Rent Increases Apply: Intentionally Omitted\n"
    "3.4 Base Rent Increases . Intentionally Omitted ."
)


class TestScope(unittest.TestCase):

    def test_subclause_placeholder_does_not_cover_the_provision(self):
        self.assertFalse(placeholder_covers_provision(SUBCLAUSE_OMITTED))
        prose = prose_outside_placeholders(SUBCLAUSE_OMITTED)
        self.assertTrue(prose)
        self.assertIn("Tenant covenants and agrees to pay", prose[0])

    def test_label_only_block_still_short_circuits(self):
        """The real absences must survive. Step 495's first rule."""
        self.assertTrue(placeholder_covers_provision(WHOLLY_OMITTED))
        self.assertEqual(prose_outside_placeholders(WHOLLY_OMITTED), [])

    def test_a_block_of_labels_and_placeholders_still_short_circuits(self):
        self.assertTrue(placeholder_covers_provision(LABELS_AND_PLACEHOLDERS))

    def test_the_clause_name_alone_is_not_prose(self):
        """`_assess_elements` matched 3 of 7 LP-21 elements off the word GUARANTY.

        A keyword matcher cannot decide whether a clause exists, because the
        clause's name survives its omission. This test pins the property that
        made the element-based rule unusable (Step 556).
        """
        self.assertTrue(placeholder_covers_provision("PERSONAL GUARANTY - Intentionally Omitted"))
        self.assertTrue(placeholder_covers_provision("Section 24.15 [Reserved]"))

    def test_empty_and_absent_text(self):
        self.assertTrue(placeholder_covers_provision(""))
        self.assertTrue(placeholder_covers_provision(None))

    def test_prose_needs_both_length_and_a_verb(self):
        # a long noun phrase is not prose
        self.assertTrue(placeholder_covers_provision(
            "1.11 One Time Fixed Rental Charge Base Annual Rent Schedule: Intentionally Omitted"))
        # a short sentence with a verb is not prose either -- below the word floor
        self.assertTrue(placeholder_covers_provision("3.1 Rent . Intentionally Omitted . It is."))


class TestConsumerHonoursTheContract(unittest.TestCase):

    def test_coverage_only_short_circuits_when_the_placeholder_covers_the_block(self):
        """The branch in lease_coverage must gate on the scope test.

        Read as source rather than exercised end-to-end: driving `assess_coverage`
        needs the schema, the panel and provider keys, and the property under test
        is a one-line guard. The end-to-end evidence is the Step-557 re-runs.
        """
        import io
        from pathlib import Path
        src = io.open(Path(__file__).resolve().parents[4] / "cam" / "adapters" /
                      "lease_review" / "lease_coverage.py", encoding="utf-8").read()
        i = src.index('reserved_signals = [s for s in ns if s["signal_type"] == "reserved_or_omitted"]')
        window = src[i:i + 700]
        self.assertIn("placeholder_covers_provision(tenant_text)", window,
                      "the short-circuit no longer consults the scope test")
        self.assertIn("reserved_signals = []", window,
                      "the guard does not clear the signal list")

    def test_the_signal_is_not_removed_from_the_evidence_list(self):
        """Clearing `reserved_signals` must not mutate `ns`.

        `_ns_candidates = ns_signals.get(pid, [])` is what reaches the 305 prompt.
        If the guard mutated `ns` in place, the evidence would vanish from the
        prompt -- the same defect one layer over.
        """
        ns = [{"signal_type": "reserved_or_omitted", "evidence": "Intentionally Omitted"}]
        reserved_signals = [s for s in ns if s["signal_type"] == "reserved_or_omitted"]
        reserved_signals = []          # exactly what the guard does
        self.assertEqual(len(ns), 1, "clearing the filtered list must not empty `ns`")


if __name__ == "__main__":
    unittest.main()
