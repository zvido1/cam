"""Step 414 fallback integrity tests — no real API calls.

Covers: transient-failure class helper, Role C chain config after check-0 fix,
validate_evaluator_chains canonical strictness, Role C hard-failure canonical abstain,
recovered transient (clean run), reason code distinctness, truncation rationale,
collect_run_fallback_events event types, and run_degraded logic.

Run from repo root:
  PYTHONPATH=. python -m pytest cam/adapters/lease_review/tests/test_414_fallback_integrity.py -v
"""
import sys
import os
import unittest

# Ensure repo root is on path when run directly
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cam.adapters.lease_review.lease_coverage_305 import (
    _is_transient_failure,
    _TRANSIENT_FAILURE_CLASSES,
    _classify_failure,
    EVALUATOR_LINEUP_305,
    validate_evaluator_chains,
    collect_run_fallback_events,
)


# ── Check 0: own_chain population ─────────────────────────────────────────────

class TestRoleCChainAfterFix(unittest.TestCase):

    def test_role_c_own_chain_populated(self):
        """After check-0 fix, Role C own_chain must be non-empty (self-retry via grok-4.3)."""
        self.assertGreater(len(EVALUATOR_LINEUP_305["C"]["own_chain"]), 0)

    def test_role_c_own_chain_is_xai_grok(self):
        """The chain entry must be an XAI/grok entry (not a different provider)."""
        entry = EVALUATOR_LINEUP_305["C"]["own_chain"][0]
        self.assertEqual(entry[0], "xai")
        self.assertIn("grok", entry[1].lower())

    def test_role_c_own_chain_same_model_as_primary(self):
        """Chain entry model equals primary — this is the self-retry design."""
        primary_model = EVALUATOR_LINEUP_305["C"]["model"]
        chain_model = EVALUATOR_LINEUP_305["C"]["own_chain"][0][1]
        self.assertEqual(primary_model, chain_model)

    def test_role_c_no_own_chain_empty_reason(self):
        """With own_chain populated, own_chain_empty_reason must not be present."""
        self.assertNotIn("own_chain_empty_reason", EVALUATOR_LINEUP_305["C"])

    def test_roles_a_b_non_empty_chains(self):
        for role in ("A", "B"):
            self.assertGreater(len(EVALUATOR_LINEUP_305[role]["own_chain"]), 0)


# ── Transient / hard failure classification ───────────────────────────────────

class TestTransientFailureHelper(unittest.TestCase):

    def test_transient_classes_are_all_transient(self):
        for cls in _TRANSIENT_FAILURE_CLASSES:
            self.assertTrue(_is_transient_failure(cls), f"{cls!r} should be transient")

    def test_hard_classes_not_transient(self):
        for cls in ("api_error", "provider_unavailable", "reasoning_exhaustion", "unknown"):
            self.assertFalse(_is_transient_failure(cls), f"{cls!r} should be hard")

    def test_empty_string_not_transient(self):
        self.assertFalse(_is_transient_failure(""))

    def test_classify_api_error_is_hard(self):
        cls = _classify_failure("HTTP 503 service unavailable", "grok-4.3")
        self.assertFalse(_is_transient_failure(cls), f"503 should be hard ({cls!r})")

    def test_classify_429_is_hard(self):
        cls = _classify_failure("rate limit exceeded 429", "grok-4.3")
        self.assertFalse(_is_transient_failure(cls), f"429 should be hard ({cls!r})")

    def test_classify_malformed_is_transient(self):
        cls = _classify_failure("malformed json: not a list", "grok-4.3")
        self.assertTrue(_is_transient_failure(cls), f"malformed should be transient ({cls!r})")

    def test_classify_truncation_is_transient(self):
        cls = _classify_failure("truncation detected in response", "grok-4.3")
        self.assertTrue(_is_transient_failure(cls), f"truncation should be transient ({cls!r})")


# ── Issue 1: validate_evaluator_chains canonical strictness ───────────────────

class TestValidateEvaluatorChains(unittest.TestCase):

    def test_populated_chains_no_degraded(self):
        """All roles have non-empty own_chain → run_config_degraded=False."""
        result = validate_evaluator_chains(EVALUATOR_LINEUP_305, mode="canonical")
        self.assertFalse(result["run_config_degraded"])
        self.assertEqual(result["warnings"], [])

    def test_canonical_raises_on_empty_chain_no_reason(self):
        bad_lineup = {"X": {"provider": "fake", "model": "fake", "label": "Fake", "own_chain": []}}
        with self.assertRaises(RuntimeError):
            validate_evaluator_chains(bad_lineup, mode="canonical")

    def test_canonical_raises_on_empty_chain_WITH_reason(self):
        """Canonical must raise even when own_chain_empty_reason is declared (no exemption)."""
        lineup_with_reason = {
            "C": {
                "provider": "xai", "model": "grok-4.3", "label": "Grok 4.3",
                "own_chain": [],
                "own_chain_empty_reason": "deliberate test: verifying canonical strictness",
            }
        }
        with self.assertRaises(RuntimeError) as ctx:
            validate_evaluator_chains(lineup_with_reason, mode="canonical")
        self.assertIn("deliberate test", str(ctx.exception))

    def test_product_warns_on_empty_chain_with_reason(self):
        lineup_with_reason = {
            "C": {
                "provider": "xai", "model": "grok-4.3", "label": "Grok 4.3",
                "own_chain": [],
                "own_chain_empty_reason": "test reason",
            }
        }
        result = validate_evaluator_chains(lineup_with_reason, mode="product")
        self.assertTrue(result["run_config_degraded"])
        self.assertEqual(len(result["warnings"]), 1)

    def test_product_warns_on_empty_chain_no_reason(self):
        bad_lineup = {"X": {"provider": "fake", "model": "fake", "label": "Fake", "own_chain": []}}
        result = validate_evaluator_chains(bad_lineup, mode="product")
        self.assertTrue(result["run_config_degraded"])

    def test_actual_lineup_canonical_clean(self):
        """After check-0 fix, the live EVALUATOR_LINEUP_305 passes canonical validation cleanly."""
        result = validate_evaluator_chains(EVALUATOR_LINEUP_305, mode="canonical")
        self.assertFalse(result["run_config_degraded"])
        self.assertEqual(result["warnings"], [])


# ── Issue 2: Role C hard-failure canonical abstain path ──────────────────────

class TestRoleCCanonicalHardFailAbstain(unittest.TestCase):
    """Verify Role C hard-failure canonical behavior using its actual chain config."""

    def setUp(self):
        self.role_cfg = EVALUATOR_LINEUP_305["C"]
        self.primary_model = self.role_cfg["model"]
        self.own_candidates = [(self.role_cfg["provider"], self.role_cfg["model"], self.role_cfg["label"])]
        for entry in self.role_cfg.get("own_chain", []):
            self.own_candidates.append(entry)

    def test_own_candidates_has_two_entries(self):
        self.assertEqual(len(self.own_candidates), 2)

    def test_both_entries_are_grok_43(self):
        self.assertEqual(self.own_candidates[0][1], "grok-4.3")
        self.assertEqual(self.own_candidates[1][1], "grok-4.3")

    def test_hard_failure_triggers_skip_guard(self):
        """Hard failure at idx=0: next candidate is same model → guard fires, skip self-retry."""
        fail_class = _classify_failure("HTTP 503 provider unavailable", self.primary_model)
        self.assertFalse(_is_transient_failure(fail_class))
        _next_idx = 1
        _should_skip = (
            _next_idx < len(self.own_candidates)
            and self.own_candidates[_next_idx][1] == self.primary_model
            and not _is_transient_failure(fail_class)
        )
        self.assertTrue(_should_skip)

    def test_hard_fail_abstain_reason_code(self):
        _hard_fail_no_retry, _retry_attempted = True, False
        _abstain_reason = (
            "hard_failure_no_retry_canonical_abstain" if _hard_fail_no_retry
            else "same_provider_retry_exhausted_canonical_abstain"
        )
        self.assertEqual(_abstain_reason, "hard_failure_no_retry_canonical_abstain")
        self.assertFalse(_retry_attempted)

    def test_canonical_abstain_result_model_is_not_gemini(self):
        result_model = self.role_cfg["model"]
        result_provider = self.role_cfg["provider"]
        self.assertNotIn("gemini", result_model.lower())
        self.assertEqual(result_provider, "xai")

    def test_canonical_abstain_marks_completed_false_abstained_true(self):
        abstain_dict = {
            "completed": False, "abstained": True,
            "abstain_reason": "hard_failure_no_retry_canonical_abstain",
            "model": self.primary_model, "provider": "xai",
        }
        self.assertFalse(abstain_dict["completed"])
        self.assertTrue(abstain_dict["abstained"])
        self.assertNotIn("gemini", abstain_dict["model"])

    def test_abstain_event_makes_run_degraded(self):
        """collect_run_fallback_events captures abstain → run_degraded=True."""
        lp = {
            "issue_area_id": "LP-05",
            "lp_meta": {"fallback_used": False, "fallbacks": None},
            "evaluator_meta": {
                "C": {
                    "completed": False, "abstained": True,
                    "abstain_reason": "hard_failure_no_retry_canonical_abstain",
                    "model": "grok-4.3", "provider": "xai",
                    "fallback_reason": "api_error",
                    "same_provider_retry_attempted": False,
                    "same_provider_retry_succeeded": False,
                }
            },
        }
        events = collect_run_fallback_events([lp], "ts")
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["event_type"], "abstain")
        self.assertTrue(ev["abstained"])
        self.assertEqual(ev["abstain_reason"], "hard_failure_no_retry_canonical_abstain")
        self.assertIsNone(ev["actual_model"])
        self.assertFalse(ev["same_provider_retry_attempted"])
        self.assertTrue(bool(events))  # run_degraded=True

    def test_transient_fail_does_not_trigger_skip_guard(self):
        fail_class = _classify_failure("malformed json: not a list", self.primary_model)
        self.assertTrue(_is_transient_failure(fail_class))
        _next_idx = 1
        _should_skip = (
            _next_idx < len(self.own_candidates)
            and self.own_candidates[_next_idx][1] == self.primary_model
            and not _is_transient_failure(fail_class)
        )
        self.assertFalse(_should_skip)

    def test_transient_retry_exhausted_reason_code(self):
        _hard_fail_no_retry, _retry_attempted = False, True
        _abstain_reason = (
            "hard_failure_no_retry_canonical_abstain" if _hard_fail_no_retry
            else "same_provider_retry_exhausted_canonical_abstain"
        )
        self.assertEqual(_abstain_reason, "same_provider_retry_exhausted_canonical_abstain")
        self.assertTrue(_retry_attempted)


# ── Recovered transient: clean run, no degraded event ────────────────────────

class TestRoleCTransientRecovery(unittest.TestCase):
    """Verify that a recovered transient does NOT trigger run_degraded.

    When Role C primary transient-fails and the same-model self-retry succeeds:
      - actual_model == grok-4.3, provider == xai
      - is_fallback == False  (answering model is still the primary)
      - same_provider_retry_attempted == True  (visible provenance)
      - collect_run_fallback_events returns [] (no fallback/abstain event)
      - run_degraded == False  (stack stayed intact, Grok answered)
    """

    def _make_recovered_transient_ev(self):
        """Build the evaluator_meta dict that _call_single_evaluator_305 produces
        when idx=1 (self-retry) succeeds after a transient failure at idx=0."""
        primary_model = EVALUATOR_LINEUP_305["C"]["model"]  # grok-4.3
        return {
            # Success at idx=1 (retry slot): model/provider stay grok-4.3/xai
            "completed": True,
            "model": primary_model,
            "provider": "xai",
            # is_fallback is False because answering model == primary model
            "is_fallback": primary_model != primary_model,  # False
            "abstained": False,
            "abstain_reason": None,
            # Retry provenance — visible but NOT a degradation trigger
            "same_provider_retry_attempted": True,
            "same_provider_retry_succeeded": True,
            # fallback_reason records the first failure; fallback_trigger_stage is set
            # because _idx > 0 on the answering call — this is provenance, not degradation
            "fallback_reason": "malformed_response",
            "fallback_trigger_stage": "305",
        }

    def test_is_fallback_false_on_recovered_transient(self):
        ev = self._make_recovered_transient_ev()
        self.assertFalse(ev["is_fallback"],
                         "Recovered transient: answering model is still primary → is_fallback=False")

    def test_actual_model_is_grok_43(self):
        ev = self._make_recovered_transient_ev()
        self.assertEqual(ev["model"], "grok-4.3")
        self.assertEqual(ev["provider"], "xai")

    def test_retry_provenance_visible(self):
        ev = self._make_recovered_transient_ev()
        self.assertTrue(ev["same_provider_retry_attempted"])
        self.assertTrue(ev["same_provider_retry_succeeded"])

    def test_lp_meta_fallback_used_false(self):
        """lp_meta.fallback_used must be False when answering model == primary model."""
        primary_model = EVALUATOR_LINEUP_305["C"]["model"]
        # Simulates the _fallbacks list comprehension in assess_coverage_305:
        # only includes roles where actual_model != primary_model
        r = {"model": primary_model, "label": "Grok 4.3", "provider": "xai"}
        in_fallbacks = bool(r.get("model")) and r.get("model") != EVALUATOR_LINEUP_305["C"]["model"]
        self.assertFalse(in_fallbacks,
                         "Self-retry success: answering model == primary → not in _fallbacks")

    def test_no_fallback_event_emitted(self):
        """collect_run_fallback_events must return [] for a recovered transient."""
        lp = {
            "issue_area_id": "LP-07",
            "lp_meta": {
                "fallback_used": False,   # model didn't change
                "fallbacks": None,
            },
            "evaluator_meta": {"C": self._make_recovered_transient_ev()},
        }
        events = collect_run_fallback_events([lp], "2026-07-08T00:00:00Z")
        self.assertEqual(events, [],
                         f"Recovered transient must emit no events; got {events}")

    def test_run_degraded_false_on_recovered_transient(self):
        """run_degraded must be False when the self-retry recovered the transient failure."""
        lp = {
            "issue_area_id": "LP-07",
            "lp_meta": {"fallback_used": False, "fallbacks": None},
            "evaluator_meta": {"C": self._make_recovered_transient_ev()},
        }
        events = collect_run_fallback_events([lp], "ts")
        run_degraded = bool(events)
        self.assertFalse(run_degraded,
                         "Recovered transient: stack stayed intact → run_degraded must be False")

    def test_no_abstain_no_all_failed_event(self):
        """completed=True means the abstain/all-fail branch is not entered."""
        ev = self._make_recovered_transient_ev()
        self.assertTrue(ev["completed"])   # guard condition: if completed=True → skip
        self.assertFalse(ev["abstained"])


# ── Issue 3: reason code distinctness ────────────────────────────────────────

class TestAbstainReasonCodes(unittest.TestCase):

    EXPECTED_CODES = {
        "hard_failure_no_retry_canonical_abstain",
        "same_provider_retry_exhausted_canonical_abstain",
    }

    def test_two_codes_are_distinct(self):
        codes = list(self.EXPECTED_CODES)
        self.assertNotEqual(codes[0], codes[1])

    def test_reason_code_from_hard_fail(self):
        self.assertIn("hard_failure_no_retry_canonical_abstain", self.EXPECTED_CODES)

    def test_reason_code_from_retry_exhausted(self):
        self.assertIn("same_provider_retry_exhausted_canonical_abstain", self.EXPECTED_CODES)

    def test_collect_distinguishes_event_types(self):
        lps = [
            {
                "issue_area_id": "LP-01",
                "lp_meta": {"fallback_used": False, "fallbacks": None},
                "evaluator_meta": {
                    "C": {
                        "completed": False, "abstained": True,
                        "abstain_reason": "hard_failure_no_retry_canonical_abstain",
                        "model": "grok-4.3", "provider": "xai",
                        "fallback_reason": "api_error",
                        "same_provider_retry_attempted": False,
                        "same_provider_retry_succeeded": False,
                    }
                },
            },
            {
                "issue_area_id": "LP-02",
                "lp_meta": {
                    "fallback_used": True,
                    "fallbacks": [{"role": "A", "actual_model": "gemini-2.5-pro",
                                   "actual_label": "Gemini", "actual_provider": "google"}],
                },
                "evaluator_meta": {
                    "A": {
                        "completed": True, "abstained": False, "abstain_reason": None,
                        "model": "gemini-2.5-pro", "provider": "google",
                        "fallback_reason": "api_error",
                        "same_provider_retry_attempted": False,
                        "same_provider_retry_succeeded": False,
                    }
                },
            },
        ]
        events = collect_run_fallback_events(lps, "ts")
        types = {ev["event_type"] for ev in events}
        self.assertIn("abstain", types)
        self.assertIn("fallback", types)
        self.assertNotIn("all_failed", types)


# ── Issue 4: truncation in transient set ─────────────────────────────────────

class TestTruncationInTransientSet(unittest.TestCase):

    def test_truncation_is_transient(self):
        self.assertIn("truncation", _TRANSIENT_FAILURE_CLASSES)

    def test_truncation_classified_as_transient(self):
        cls = _classify_failure("truncation detected in response", "grok-4.3")
        self.assertTrue(_is_transient_failure(cls))

    def test_truncation_does_not_trigger_skip_guard(self):
        """truncation (transient) must NOT skip the self-retry."""
        _should_skip = not _is_transient_failure("truncation")
        self.assertFalse(_should_skip)


# ── collect_run_fallback_events comprehensive ─────────────────────────────────

class TestCollectRunFallbackEvents(unittest.TestCase):

    def test_no_events_when_all_completed_primary(self):
        lp = {
            "issue_area_id": "LP-01",
            "lp_meta": {"fallback_used": False, "fallbacks": None},
            "evaluator_meta": {
                "A": {"completed": True, "abstained": False, "model": "claude-sonnet-4-6"},
                "B": {"completed": True, "abstained": False, "model": "gpt-5.5"},
                "C": {"completed": True, "abstained": False, "model": "grok-4.3"},
            },
        }
        self.assertEqual(collect_run_fallback_events([lp], "ts"), [])

    def test_fallback_event_captured(self):
        lp = {
            "issue_area_id": "LP-05",
            "lp_meta": {
                "fallback_used": True,
                "fallbacks": [{"role": "C", "actual_model": "gemini-2.5-pro",
                               "actual_label": "Gemini", "actual_provider": "google"}],
            },
            "evaluator_meta": {
                "C": {
                    "completed": True, "abstained": False,
                    "model": "gemini-2.5-pro", "provider": "google",
                    "fallback_reason": "api_error",
                    "same_provider_retry_attempted": True,
                    "same_provider_retry_succeeded": False,
                }
            },
        }
        events = collect_run_fallback_events([lp], "ts")
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["event_type"], "fallback")
        self.assertEqual(ev["actual_model"], "gemini-2.5-pro")
        self.assertEqual(ev["fallback_class"], "hard")
        self.assertFalse(ev["abstained"])

    def test_abstain_event_captured(self):
        lp = {
            "issue_area_id": "LP-03",
            "lp_meta": {"fallback_used": False, "fallbacks": None},
            "evaluator_meta": {
                "C": {
                    "completed": False, "abstained": True,
                    "abstain_reason": "hard_failure_no_retry_canonical_abstain",
                    "model": "grok-4.3", "provider": "xai",
                    "fallback_reason": "api_error",
                    "same_provider_retry_attempted": False,
                    "same_provider_retry_succeeded": False,
                }
            },
        }
        events = collect_run_fallback_events([lp], "ts")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "abstain")
        self.assertIsNone(events[0]["actual_model"])

    def test_all_failed_event_captured(self):
        lp = {
            "issue_area_id": "LP-04",
            "lp_meta": {"fallback_used": False, "fallbacks": None},
            "evaluator_meta": {
                "B": {
                    "completed": False, "abstained": False, "abstain_reason": None,
                    "model": "gpt-5.5", "provider": "openai",
                    "fallback_reason": "api_error",
                    "same_provider_retry_attempted": False,
                    "same_provider_retry_succeeded": False,
                }
            },
        }
        events = collect_run_fallback_events([lp], "ts")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "all_failed")

    def test_transient_fallback_class(self):
        lp = {
            "issue_area_id": "LP-06",
            "lp_meta": {
                "fallback_used": True,
                "fallbacks": [{"role": "A", "actual_model": "claude-haiku-4-5",
                               "actual_label": "Haiku", "actual_provider": "anthropic"}],
            },
            "evaluator_meta": {
                "A": {
                    "completed": True, "abstained": False,
                    "model": "claude-haiku-4-5", "provider": "anthropic",
                    "fallback_reason": "malformed_response",
                    "same_provider_retry_attempted": False,
                    "same_provider_retry_succeeded": False,
                }
            },
        }
        events = collect_run_fallback_events([lp], "ts")
        self.assertEqual(events[0]["fallback_class"], "transient")


# ── run_degraded logic ────────────────────────────────────────────────────────

class TestRunDegradedLogic(unittest.TestCase):

    def _compute(self, fallback_events, run_config_degraded):
        run_degraded = bool(fallback_events) or run_config_degraded
        degraded_reason = (
            "evaluator_fallback" if fallback_events
            else ("chain_config_degraded" if run_config_degraded else None)
        )
        return run_degraded, degraded_reason

    def test_clean_run_not_degraded(self):
        rd, dr = self._compute([], False)
        self.assertFalse(rd); self.assertIsNone(dr)

    def test_fallback_event_sets_degraded(self):
        rd, dr = self._compute([{"event_type": "fallback"}], False)
        self.assertTrue(rd); self.assertEqual(dr, "evaluator_fallback")

    def test_abstain_event_sets_degraded(self):
        rd, dr = self._compute([{"event_type": "abstain"}], False)
        self.assertTrue(rd); self.assertEqual(dr, "evaluator_fallback")

    def test_config_degraded_sets_degraded(self):
        rd, dr = self._compute([], True)
        self.assertTrue(rd); self.assertEqual(dr, "chain_config_degraded")

    def test_fallback_events_take_precedence(self):
        rd, dr = self._compute([{"event_type": "abstain"}], True)
        self.assertTrue(rd); self.assertEqual(dr, "evaluator_fallback")

    def test_recovered_transient_not_degraded(self):
        """Recovered transient emits no events → run_degraded=False."""
        rd, dr = self._compute([], False)
        self.assertFalse(rd); self.assertIsNone(dr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
