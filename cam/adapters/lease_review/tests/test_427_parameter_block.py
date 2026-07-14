"""
Step 427 — Parameter block + declared dependency map tests.

Covers: parameter extraction (mocked model call, real 423A resolver),
deterministic attachment, non-destructive multi-LP assignment, Gate B
pass/fail/degraded behavior, Gate B's literal-value-free and
evaluator-vote-free design, and the pipeline seam.
"""

import inspect
import json
import unittest
from unittest.mock import MagicMock, patch

from cam.adapters.lease_review.lease_evidence_spans import (
    build_canonical_source,
    VERIFIED,
    UNVERIFIED,
)
from cam.adapters.lease_review.lease_parameter_block import (
    DEPENDENCY_MAP,
    PARAMETER_NAMES,
    Parameter,
    attach_parameters_to_lp_evidence,
    check_gate_b,
    enforce_gate_b,
    extract_parameters,
)
from cam.adapters.lease_review.lease_adapter import GateAbortError


FIXTURE_TEXT = (
    "ARTICLE 1 - BASIC LEASE INFORMATION\n"
    "Base Rent:\n"
    "$3.75 per rentable square foot of the Premises per month.\n"
    "Tenant's Share of Operating Expenses of Building: 100%\n"
    "Building's Share of Project: 45.79%\n"
    "Rent Adjustment Percentage: 3%\n\n"
    "ARTICLE 2 - OPERATING EXPENSES\n"
    "Tenant shall pay its share of Operating Expenses as set forth herein.\n"
)


def _health_mock():
    h = MagicMock()
    h.is_available.return_value = True
    return h


def _valid_raw_response_all_four():
    return json.dumps({
        "target_matches": [
            {"target": "Target 1", "quotes": ["Tenant's Share of Operating Expenses of Building: 100%"]},
            {"target": "Target 2", "quotes": ["Building's Share of Project: 45.79%"]},
            {"target": "Target 3", "quotes": ["Rent Adjustment Percentage: 3%"]},
            {"target": "Target 4", "quotes": ["$3.75 per rentable square foot"]},
        ]
    })


def _valid_raw_response_missing_building_share():
    return json.dumps({
        "target_matches": [
            {"target": "Target 1", "quotes": ["Tenant's Share of Operating Expenses of Building: 100%"]},
            {"target": "Target 2", "quotes": []},
            {"target": "Target 3", "quotes": ["Rent Adjustment Percentage: 3%"]},
            {"target": "Target 4", "quotes": ["$3.75 per rentable square foot"]},
        ]
    })


def _extract_with_mock(response_text, canonical=True):
    adapter_mock = MagicMock()
    adapter_mock.call.return_value = response_text
    source = build_canonical_source(FIXTURE_TEXT, run_id="427-test")
    with patch("cam.adapters.lease_review.lease_extract._get_adapter_for_provider", return_value=adapter_mock), \
         patch("cam.adapters.lease_review.lease_element_elicitation.get_health_tracker", return_value=_health_mock()):
        result = extract_parameters(source, canonical=canonical)
    return source, result


# ── Test 1: each parameter extracts to a verified span with correct offsets ────

class TestParameterExtraction(unittest.TestCase):
    def test_all_four_parameters_verified_with_correct_offsets(self):
        source, result = _extract_with_mock(_valid_raw_response_all_four())
        params = result["parameters"]
        self.assertEqual(set(params.keys()), PARAMETER_NAMES)

        for name, expected_text in [
            ("tenant_share", "Tenant's Share of Operating Expenses of Building: 100%"),
            ("building_share", "Building's Share of Project: 45.79%"),
            ("rent_adjustment_pct", "Rent Adjustment Percentage: 3%"),
        ]:
            p = params[name]
            self.assertIsInstance(p, Parameter)
            self.assertEqual(p.span.verification_status, VERIFIED)
            self.assertEqual(
                source.canonical_text[p.span.start_char:p.span.end_char],
                expected_text,
            )

        base_rent = params["base_rent"]
        self.assertEqual(base_rent.span.verification_status, VERIFIED)
        self.assertIn(
            "$3.75 per rentable square foot",
            source.canonical_text[base_rent.span.start_char:base_rent.span.end_char],
        )

    def test_missing_parameter_is_absent_not_a_crash(self):
        source, result = _extract_with_mock(_valid_raw_response_missing_building_share())
        params = result["parameters"]
        self.assertNotIn("building_share", params)
        self.assertIn("tenant_share", params)

    def test_meta_carries_canonical_flag_explicitly(self):
        _, result = _extract_with_mock(_valid_raw_response_all_four(), canonical=True)
        self.assertTrue(result["meta"]["canonical"])


# ── Test 2/3: deterministic, non-destructive attachment ─────────────────────────

def _sample_parameters(source):
    from cam.adapters.lease_review.lease_evidence_spans import resolve_span
    names_and_quotes = [
        ("tenant_share", "Tenant's Share of Operating Expenses of Building: 100%"),
        ("building_share", "Building's Share of Project: 45.79%"),
        ("rent_adjustment_pct", "Rent Adjustment Percentage: 3%"),
        ("base_rent", "$3.75 per rentable square foot"),
    ]
    params = {}
    for name, quote in names_and_quotes:
        span = resolve_span(source, quote, evidence_span_id=f"TEST-{name}")
        params[name] = Parameter(name=name, span=span)
    return params


class TestDeterministicAttachment(unittest.TestCase):
    def setUp(self):
        self.source = build_canonical_source(FIXTURE_TEXT, run_id="427-attach-test")
        self.parameters = _sample_parameters(self.source)

    def test_lp07_gets_tenant_share_and_building_share_every_call(self):
        for _ in range(5):  # "every run" -- deterministic, not just once
            attached = attach_parameters_to_lp_evidence(self.parameters, "LP-07")
            names = {p.name for p in attached}
            self.assertEqual(names, {"tenant_share", "building_share"})

    def test_lp02_gets_base_rent_and_rent_adjustment_every_call(self):
        for _ in range(5):
            attached = attach_parameters_to_lp_evidence(self.parameters, "LP-02")
            names = {p.name for p in attached}
            self.assertEqual(names, {"base_rent", "rent_adjustment_pct"})

    def test_attachment_uses_dependency_map_only_no_model_call(self):
        """Code-level check: attach_parameters_to_lp_evidence never CALLS or
        references anything model/elicitation-related — purely a dict
        lookup. Checked against actual referenced names (co_names), not
        docstring prose, so a docstring saying "no model call" doesn't
        trip its own check."""
        names = {n.lower() for n in attach_parameters_to_lp_evidence.__code__.co_names}
        for banned in ("elicit", "adapter", "model", "_get_adapter_for_provider"):
            self.assertFalse(
                any(banned in n for n in names),
                f"unexpected reference containing {banned!r} in co_names: {names}",
            )

    def test_same_span_attaches_to_multiple_lps_without_being_consumed(self):
        """Non-destructive assignment: the SAME Parameter/span attaches to
        two different LPs (using a test-local dependency map with a
        deliberate overlap -- the production DEPENDENCY_MAP has none by
        design) without being removed from the pool or mutated."""
        overlapping_map = {
            "LP-07": ["tenant_share", "building_share"],
            "LP-99-TEST": ["tenant_share"],  # synthetic overlap, test-only
        }
        attached_lp07 = attach_parameters_to_lp_evidence(self.parameters, "LP-07", dependency_map=overlapping_map)
        attached_lp99 = attach_parameters_to_lp_evidence(self.parameters, "LP-99-TEST", dependency_map=overlapping_map)

        tenant_share_lp07 = next(p for p in attached_lp07 if p.name == "tenant_share")
        tenant_share_lp99 = attached_lp99[0]

        self.assertIs(tenant_share_lp07, tenant_share_lp99)  # identical object, not a copy
        self.assertEqual(tenant_share_lp07.span.start_char, tenant_share_lp99.span.start_char)
        self.assertEqual(tenant_share_lp07.span.end_char, tenant_share_lp99.span.end_char)
        # still present and unmutated in the pool afterward
        self.assertIn("tenant_share", self.parameters)
        self.assertEqual(self.parameters["tenant_share"].span.verification_status, VERIFIED)


# ── Test 4/5/8: Gate B pass / abort / degraded ───────────────────────────────────

class TestGateB(unittest.TestCase):
    def setUp(self):
        self.source = build_canonical_source(FIXTURE_TEXT, run_id="427-gate-test")
        self.parameters = _sample_parameters(self.source)

    def test_gate_b_passes_when_all_dependencies_satisfied(self):
        result = enforce_gate_b(self.parameters, canonical=True)
        self.assertEqual(result["gate_status"], "pass")
        self.assertEqual(result["failures"], [])

    def test_gate_b_check_reports_pass_for_every_declared_pair(self):
        results = check_gate_b(self.parameters)
        self.assertEqual(len(results), 4)  # LP-02: 2 deps, LP-07: 2 deps
        self.assertTrue(all(r["gate_status"] == "pass" for r in results))

    def test_gate_b_aborts_canonical_when_dependency_missing(self):
        del self.parameters["building_share"]
        with self.assertRaises(GateAbortError) as ctx:
            enforce_gate_b(self.parameters, canonical=True)
        msg = str(ctx.exception)
        self.assertIn("LP-07", msg)
        self.assertIn("building_share", msg)

    def test_gate_b_aborts_when_dependency_present_but_unverified(self):
        """A dependency with an unverified span (not just a missing one)
        must also fail the gate -- gate keys on verification_status."""
        from cam.adapters.lease_review.lease_evidence_spans import resolve_span
        bad_span = resolve_span(self.source, "this text does not appear anywhere", "TEST-bad")
        self.assertEqual(bad_span.verification_status, UNVERIFIED)
        self.parameters["building_share"] = Parameter(name="building_share", span=bad_span)
        with self.assertRaises(GateAbortError):
            enforce_gate_b(self.parameters, canonical=True)

    def test_gate_b_degraded_not_abort_when_non_canonical(self):
        del self.parameters["tenant_share"]
        result = enforce_gate_b(self.parameters, canonical=False)
        self.assertEqual(result["gate_status"], "degraded")
        self.assertEqual(len(result["failures"]), 1)
        self.assertEqual(result["failures"][0]["dependency"], "tenant_share")


# ── Test 6: Gate B keyed to names, never literal values ────────────────────────

class TestGateBNoLiteralValues(unittest.TestCase):
    LEASE_SPECIFIC_VALUES = ["45.79", "100%", "3.75", "3%"]

    def test_check_gate_b_source_has_no_lease_specific_literals(self):
        src = inspect.getsource(check_gate_b)
        for val in self.LEASE_SPECIFIC_VALUES:
            self.assertNotIn(val, src, f"check_gate_b must not contain literal {val!r}")

    def test_enforce_gate_b_source_has_no_lease_specific_literals(self):
        src = inspect.getsource(enforce_gate_b)
        for val in self.LEASE_SPECIFIC_VALUES:
            self.assertNotIn(val, src, f"enforce_gate_b must not contain literal {val!r}")

    def test_whole_module_has_no_lease_specific_literals(self):
        import cam.adapters.lease_review.lease_parameter_block as mod
        src = inspect.getsource(mod)
        for val in self.LEASE_SPECIFIC_VALUES:
            self.assertNotIn(val, src, f"lease_parameter_block.py must not contain literal {val!r}")


# ── Test 7: Gate B does not consult evaluator votes ──────────────────────────────

class TestGateBNoEvaluatorVotes(unittest.TestCase):
    def test_gate_b_functions_never_reference_evaluators_or_votes(self):
        """Checked against actual referenced names (co_names) — real calls,
        attribute accesses, and globals the function touches — not
        docstring prose, so a docstring explaining "never any evaluator
        output" doesn't trip its own check."""
        for fn in (check_gate_b, enforce_gate_b):
            names = {n.lower() for n in fn.__code__.co_names}
            for banned in ("evaluator", "vote", "consensus", "assess_coverage", "verdict"):
                self.assertFalse(
                    any(banned in n for n in names),
                    f"{fn.__name__} unexpectedly references {banned!r} in co_names: {names}",
                )

    def test_gate_b_signature_takes_no_evaluator_argument(self):
        import inspect as _inspect
        sig = _inspect.signature(enforce_gate_b)
        for banned_param in ("evaluators", "votes", "verdicts", "evaluator_results"):
            self.assertNotIn(banned_param, sig.parameters)


# ── Dependency map sanity ─────────────────────────────────────────────────────

class TestDependencyMapContent(unittest.TestCase):
    def test_dependency_map_is_exactly_two_lps_four_params(self):
        self.assertEqual(set(DEPENDENCY_MAP.keys()), {"LP-02", "LP-07"})
        self.assertEqual(set(DEPENDENCY_MAP["LP-02"]), {"base_rent", "rent_adjustment_pct"})
        self.assertEqual(set(DEPENDENCY_MAP["LP-07"]), {"tenant_share", "building_share"})

    def test_dependency_map_has_no_overlapping_parameters(self):
        """The production map's two LPs happen to be disjoint -- confirmed
        explicitly since the non-destructive test above had to construct
        a synthetic overlap to exercise that property."""
        self.assertEqual(
            set(DEPENDENCY_MAP["LP-02"]) & set(DEPENDENCY_MAP["LP-07"]),
            set(),
        )

    def test_every_dependency_name_is_a_declared_parameter(self):
        all_deps = {d for deps in DEPENDENCY_MAP.values() for d in deps}
        self.assertTrue(all_deps.issubset(PARAMETER_NAMES))


# ── Pipeline seam ──────────────────────────────────────────────────────────────

class TestPipelineSeam(unittest.TestCase):
    def test_lease_adapter_does_not_import_parameter_block(self):
        import cam.adapters.lease_review.lease_adapter as la
        src = inspect.getsource(la)
        self.assertNotIn("lease_parameter_block", src)

    def test_lease_coverage_does_not_import_parameter_block(self):
        import cam.adapters.lease_review.lease_coverage as lc
        src = inspect.getsource(lc)
        self.assertNotIn("lease_parameter_block", src)


if __name__ == "__main__":
    unittest.main()
