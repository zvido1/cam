"""
Step 429 — Robust `Target N` ordinal resolution + raise-on-unresolvable.

428 (Gate C, N=10) returned 0/10 extraction. The model located and quoted
all four parameter values correctly; it echoed the full descriptive label in
the `target` field (`"Target 1: Tenant's Share of Operating Expenses
percentage"`) instead of the bare ordinal the schema asks for. Exact-string
lookup missed, and `extract_parameters()` silently discarded the whole record
— quotes included — before `resolve_span` was ever called.

The fixture in this module is built from the REAL echoed-label output quoted
verbatim in `build_log/428_gate_c_parameter_assignment_stability.md`
(the diagnostic probe's raw `target_matches`), NOT from clean `"Target 1"`
records. Clean records are exactly what hid the 428 defect: every pre-429
test fed a shape the model does not actually produce.

Covers: real-output recovery in both modules, raise-on-unresolvable in both
modules (unparseable label and out-of-range ordinal), and happy-path
byte-identity against the pre-429 mapping for well-formed input.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from cam.adapters.lease_review.lease_evidence_spans import (
    build_canonical_source,
    resolve_span,
    VERIFIED,
)
from cam.adapters.lease_review.lease_element_elicitation import (
    UnresolvableTargetError,
    resolve_elicited_spans,
    resolve_target_ordinal,
)
from cam.adapters.lease_review.lease_parameter_block import (
    PARAMETER_NAMES,
    PARAMETER_TARGETS,
    Parameter,
    extract_parameters,
)


# Contains, verbatim, every quote the 428 probe returned — including the
# multi-line Base Rent quote with its "subject to adjustment" tail.
FIXTURE_TEXT = (
    "ARTICLE 1 - BASIC LEASE INFORMATION\n"
    "Base Rent:\n"
    "$3.75 per rentable square foot of the Premises per month, subject to "
    "adjustment pursuant to Section 4 hereof.\n"
    "Tenant's Share of Operating Expenses of Building: 100%\n"
    "Building's Share of Project: 45.79%\n"
    "Rent Adjustment Percentage: 3%\n\n"
    "ARTICLE 2 - OPERATING EXPENSES\n"
    "Tenant shall pay its share of Operating Expenses as set forth herein.\n"
)

# The four (echoed label, quote) pairs exactly as recorded in the 428 report's
# diagnostic-probe JSON. Do not "clean" these — the echoed form IS the fixture.
ECHOED_TARGET_MATCHES = [
    {
        "target": "Target 1: Tenant's Share of Operating Expenses percentage",
        "quotes": ["Tenant's Share of Operating Expenses of Building: 100%"],
    },
    {
        "target": "Target 2: Building's Share of Project Operating Expenses percentage",
        "quotes": ["Building's Share of Project: 45.79%"],
    },
    {
        "target": "Target 3: Rent Adjustment Percentage (annual escalation rate)",
        "quotes": ["Rent Adjustment Percentage: 3%"],
    },
    {
        "target": "Target 4: Base Rent amount stated in the key-terms block",
        "quotes": [
            "Base Rent:\n$3.75 per rentable square foot of the Premises per month, "
            "subject to adjustment pursuant to Section 4 hereof."
        ],
    },
]

# Same four quotes, bare-ordinal `target` — the shape the schema asks for and
# the only shape pre-429 tests exercised.
BARE_TARGET_MATCHES = [
    {"target": f"Target {i}", "quotes": m["quotes"]}
    for i, m in enumerate(ECHOED_TARGET_MATCHES, start=1)
]

EXPECTED_VALUE_BY_PARAM = {
    "tenant_share": "100%",
    "building_share": "45.79%",
    "rent_adjustment_pct": "3%",
    "base_rent": "$3.75 per rentable square foot",
}


def _health_mock():
    h = MagicMock()
    h.is_available.return_value = True
    return h


def _extract_with_mock(target_matches, canonical=True):
    adapter_mock = MagicMock()
    adapter_mock.call.return_value = json.dumps({"target_matches": target_matches})
    source = build_canonical_source(FIXTURE_TEXT, run_id="429-test")
    with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
         patch("cam.adapters.lease_review.lease_element_elicitation.get_health_tracker", return_value=_health_mock()):
        result = extract_parameters(source, canonical=canonical)
    return source, result


def _param_elements():
    """The element list `extract_parameters` builds from PARAMETER_TARGETS."""
    return [
        {"element_id": t["param_name"], "element_label": t["element_label"], "synonyms": t.get("synonyms", [])}
        for t in PARAMETER_TARGETS
    ]


def _pre429_resolve_elicited_spans(canonical_source, elements, elicitation_result):
    """The PRE-429 mapping, inlined as a test oracle for the happy path.

    For well-formed bare-`Target N` input this exact-string lookup is
    trivially correct, which is what makes it a legitimate reference for
    "happy-path behavior did not change." It is NOT correct for echoed
    labels — that is the defect 429 fixes, and it is asserted separately.
    """
    target_to_element = {f"Target {i}": e["element_id"] for i, e in enumerate(elements, start=1)}
    records = []
    counter = 0
    for match in elicitation_result.get("target_matches", []):
        target_label = match.get("target", "")
        element_id = target_to_element.get(target_label, target_label)
        for quote in match.get("quotes", []):
            counter += 1
            span = resolve_span(canonical_source, quote=quote, evidence_span_id=f"EV-raw-{counter:06d}")
            records.append({
                "verification_status": span.verification_status,
                "start_char": span.start_char,
                "end_char": span.end_char,
                "span_text": span.span_text,
                "elicited_by": [element_id],
                "quote_variants": [quote],
            })
    return records


# ── Test 1: real-output fixture recovers what 428 lost (parameter block) ───────

class TestRealOutputFixtureParameterBlock(unittest.TestCase):
    """The regression test that would have caught 428."""

    def test_echoed_labels_resolve_all_four_parameters(self):
        source, result = _extract_with_mock(ECHOED_TARGET_MATCHES)
        params = result["parameters"]
        self.assertEqual(
            set(params.keys()), set(PARAMETER_NAMES),
            "echoed-label output must resolve all four parameters; pre-429 this "
            "returned {} (428: 0/10 runs)",
        )
        for name, param in params.items():
            self.assertIsInstance(param, Parameter)
            self.assertEqual(param.span.verification_status, VERIFIED)

    def test_recovered_spans_contain_the_VALUE_not_just_the_label(self):
        """428's brief: a span reading 'Tenant's Share ...:' without 100% is a
        failure dressed as a success. Check the value is inside the span."""
        source, result = _extract_with_mock(ECHOED_TARGET_MATCHES)
        for name, expected_value in EXPECTED_VALUE_BY_PARAM.items():
            span = result["parameters"][name].span
            span_text = source.canonical_text[span.start_char:span.end_char]
            self.assertIn(expected_value, span_text, f"{name} span lacks its value")

    def test_provenance_records_the_echoed_label_actually_received(self):
        _, result = _extract_with_mock(ECHOED_TARGET_MATCHES)
        self.assertEqual(
            result["parameters"]["tenant_share"].provenance["elicited_target"],
            "Target 1: Tenant's Share of Operating Expenses percentage",
        )


# ── Test 2: real-output fixture, element elicitation ──────────────────────────

class TestRealOutputFixtureElementElicitation(unittest.TestCase):
    def test_echoed_labels_tag_correct_element_id_not_the_raw_label(self):
        source = build_canonical_source(FIXTURE_TEXT, run_id="429-elicit")
        elements = _param_elements()
        records = resolve_elicited_spans(
            source, elements, {"target_matches": ECHOED_TARGET_MATCHES}
        )
        self.assertEqual(len(records), 4)
        self.assertEqual(
            [r["elicited_by"] for r in records],
            [["tenant_share"], ["building_share"], ["rent_adjustment_pct"], ["base_rent"]],
        )
        for r in records:
            self.assertEqual(r["verification_status"], VERIFIED)
            # pre-429 these carried the raw echoed label as elicited_by
            self.assertNotIn("Target", r["elicited_by"][0])

    def test_echoed_and_bare_labels_produce_identical_records(self):
        """The label form must be invisible below resolution: same offsets,
        same status, same provenance, same everything."""
        source = build_canonical_source(FIXTURE_TEXT, run_id="429-equiv")
        elements = _param_elements()
        echoed = resolve_elicited_spans(source, elements, {"target_matches": ECHOED_TARGET_MATCHES})
        bare = resolve_elicited_spans(source, elements, {"target_matches": BARE_TARGET_MATCHES})
        self.assertEqual(echoed, bare)


# ── Test 3: raise-on-unresolvable, BOTH modules ───────────────────────────────

UNPARSEABLE_LABEL = "Tenant's Share"          # ordinal stripped entirely
OUT_OF_RANGE_LABEL = "Target 99"              # 99 against a 4-element list


class TestRaiseOnUnresolvableElementElicitation(unittest.TestCase):
    def setUp(self):
        self.source = build_canonical_source(FIXTURE_TEXT, run_id="429-raise-elicit")
        self.elements = _param_elements()

    def _resolve(self, target_label):
        return resolve_elicited_spans(
            self.source,
            self.elements,
            {"target_matches": [{"target": target_label, "quotes": ["Rent Adjustment Percentage: 3%"]}]},
        )

    def test_unparseable_label_raises_and_names_the_offending_value(self):
        with self.assertRaises(UnresolvableTargetError) as ctx:
            self._resolve(UNPARSEABLE_LABEL)
        self.assertIn(UNPARSEABLE_LABEL, str(ctx.exception))

    def test_out_of_range_ordinal_raises_and_names_the_offending_value(self):
        with self.assertRaises(UnresolvableTargetError) as ctx:
            self._resolve(OUT_OF_RANGE_LABEL)
        msg = str(ctx.exception)
        self.assertIn(OUT_OF_RANGE_LABEL, msg)
        self.assertIn("99", msg)

    def test_empty_target_raises_rather_than_mislabelling(self):
        with self.assertRaises(UnresolvableTargetError):
            self._resolve("")

    def test_no_record_is_kept_when_resolution_fails(self):
        """Not 'mislabel and keep', and not 'quietly drop' — nothing is
        returned at all, because the call aborts."""
        with self.assertRaises(UnresolvableTargetError):
            resolve_elicited_spans(
                self.source,
                self.elements,
                {"target_matches": [
                    {"target": "Target 1", "quotes": ["Rent Adjustment Percentage: 3%"]},
                    {"target": UNPARSEABLE_LABEL, "quotes": ["Building's Share of Project: 45.79%"]},
                ]},
            )


class TestRaiseOnUnresolvableParameterBlock(unittest.TestCase):
    def test_unparseable_label_raises_and_names_the_offending_value(self):
        with self.assertRaises(UnresolvableTargetError) as ctx:
            _extract_with_mock([{"target": UNPARSEABLE_LABEL, "quotes": ["Rent Adjustment Percentage: 3%"]}])
        self.assertIn(UNPARSEABLE_LABEL, str(ctx.exception))

    def test_out_of_range_ordinal_raises_and_names_the_offending_value(self):
        with self.assertRaises(UnresolvableTargetError) as ctx:
            _extract_with_mock([{"target": OUT_OF_RANGE_LABEL, "quotes": ["Rent Adjustment Percentage: 3%"]}])
        msg = str(ctx.exception)
        self.assertIn(OUT_OF_RANGE_LABEL, msg)
        self.assertIn("99", msg)

    def test_unresolvable_is_not_silently_discarded(self):
        """The 428 defect precisely: pre-429 this returned an empty parameter
        dict and Gate B aborted downstream with no trace of the discard.
        Post-429 the loss surfaces at the point it happens."""
        with self.assertRaises(UnresolvableTargetError):
            _extract_with_mock([
                {"target": "Target 1", "quotes": ["Tenant's Share of Operating Expenses of Building: 100%"]},
                {"target": UNPARSEABLE_LABEL, "quotes": ["Building's Share of Project: 45.79%"]},
            ])


class TestResolveTargetOrdinalDirect(unittest.TestCase):
    """Unit-level: only the ordinal is authoritative; the description is
    never matched, exactly or fuzzily."""

    def setUp(self):
        self.elements = _param_elements()

    def test_ordinal_wins_even_when_description_names_a_different_parameter(self):
        self.assertEqual(
            resolve_target_ordinal("Target 1: Base Rent amount", self.elements),
            "tenant_share",
        )

    def test_bare_and_echoed_forms_resolve_identically(self):
        for i, expected in enumerate(
            ["tenant_share", "building_share", "rent_adjustment_pct", "base_rent"], start=1
        ):
            self.assertEqual(resolve_target_ordinal(f"Target {i}", self.elements), expected)
            self.assertEqual(resolve_target_ordinal(f"Target {i}: whatever", self.elements), expected)

    def test_zero_ordinal_is_out_of_range(self):
        with self.assertRaises(UnresolvableTargetError):
            resolve_target_ordinal("Target 0", self.elements)


# ── Test 4: happy path unchanged, BOTH modules ────────────────────────────────

class TestHappyPathUnchangedElementElicitation(unittest.TestCase):
    def test_bare_targets_byte_identical_to_pre429_mapping(self):
        source = build_canonical_source(FIXTURE_TEXT, run_id="429-happy-elicit")
        elements = _param_elements()
        result = {"target_matches": BARE_TARGET_MATCHES}

        actual = resolve_elicited_spans(source, elements, result)
        expected = _pre429_resolve_elicited_spans(source, elements, result)

        self.assertEqual(len(actual), len(expected))
        for a, e in zip(actual, expected):
            for key in ("verification_status", "start_char", "end_char", "span_text",
                        "elicited_by", "quote_variants"):
                self.assertEqual(a[key], e[key], f"happy-path drift on {key!r}")


class TestHappyPathUnchangedParameterBlock(unittest.TestCase):
    def test_bare_targets_produce_the_same_parameters_and_offsets(self):
        source, result = _extract_with_mock(BARE_TARGET_MATCHES)
        params = result["parameters"]
        self.assertEqual(set(params.keys()), set(PARAMETER_NAMES))

        # Reference offsets computed straight off the unmodified 423A resolver.
        for idx, param_name in enumerate(
            ["tenant_share", "building_share", "rent_adjustment_pct", "base_rent"]
        ):
            quote = BARE_TARGET_MATCHES[idx]["quotes"][0]
            reference = resolve_span(source, quote, evidence_span_id="REF")
            self.assertEqual(reference.verification_status, VERIFIED)
            self.assertEqual(params[param_name].span.start_char, reference.start_char)
            self.assertEqual(params[param_name].span.end_char, reference.end_char)
            self.assertEqual(params[param_name].span.span_text, reference.span_text)

    def test_first_verified_quote_still_wins_per_parameter(self):
        """Unchanged pre-429 semantics: a parameter is one value, not a list."""
        matches = [
            {"target": "Target 3", "quotes": ["Rent Adjustment Percentage: 3%"]},
            {"target": "Target 3", "quotes": ["Building's Share of Project: 45.79%"]},
        ]
        source, result = _extract_with_mock(matches)
        span = result["parameters"]["rent_adjustment_pct"].span
        self.assertEqual(
            source.canonical_text[span.start_char:span.end_char],
            "Rent Adjustment Percentage: 3%",
        )


if __name__ == "__main__":
    unittest.main()
