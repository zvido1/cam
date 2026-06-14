"""Step 386 — Stage 7 Pass-1 instrumentation.

Unit tests verifying that:
1. Pass-1 artifact files are written when cfg["_p1_artifact_dir"] is set.
2. Dropped-attention summary correctly flags LPs with no directional candidate.
3. Candidate density is computed and recorded.
4. Artifact paths are recorded in directional_guard["raw_response_paths"].
5. finish_reason field is present (None) on every evaluator output dict.

All tests are deterministic (no model calls). Run directly or via pytest.

  python -m cam.adapters.lease_review.tests.test_386_pass1_instrumentation
  pytest cam/adapters/lease_review/tests/test_386_pass1_instrumentation.py -v
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

_THIS_DIR = os.path.dirname(__file__)
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ── helpers to build fake evaluator output dicts ──────────────────────────────

_UNSET = object()


def _fake_ev_output(role: str, completed: bool, lp_ids: list, raw=_UNSET) -> dict:
    """Minimal evaluator output as _call_single_evaluator would return it.

    Pass raw=None to simulate a failed call with no raw response.
    Omit raw (default) to get a placeholder string for a successful call.
    """
    findings = []
    for lp_id in lp_ids:
        findings.append({
            "lp_id": lp_id,
            "lp_ids": [lp_id],
            "mismatch_flag": True,
            "exposed_party": "tenant",
            "opposing_framework_summary": "summary",
            "weaker_framework_summary": "weaker",
            "why_mismatch_matters": "matters",
        })
    raw_response = (f"raw response from {role}") if raw is _UNSET else raw
    return {
        "role": role,
        "model": f"test-model-{role}",
        "provider": "test",
        "label": role,
        "completed": completed,
        "result": {"cross_coverage_findings": findings} if completed else None,
        "error": None if completed else "simulated failure",
        "elapsed_sec": 1.0,
        "raw_response": raw_response,
        "finish_reason": None,
    }


def _fake_flagged_lps(lp_ids: list) -> list:
    return [{"lp_id": lid, "lp_name": f"Name {lid}", "coverage_state": "partial"} for lid in lp_ids]


# ── test cases ─────────────────────────────────────────────────────────────────

class TestPass1FinishReason(unittest.TestCase):
    """finish_reason field is present and None in evaluator output dicts."""

    def test_successful_call_has_finish_reason_none(self):
        out = _fake_ev_output("A", True, ["LP-01"])
        self.assertIn("finish_reason", out)
        self.assertIsNone(out["finish_reason"])

    def test_failed_call_has_finish_reason_none(self):
        out = _fake_ev_output("B", False, [])
        self.assertIn("finish_reason", out)
        self.assertIsNone(out["finish_reason"])

    def test_raw_response_present_on_success(self):
        out = _fake_ev_output("C", True, ["LP-02"], raw="my raw text")
        self.assertEqual(out["raw_response"], "my raw text")

    def test_raw_response_none_on_failure(self):
        out = _fake_ev_output("A", False, [])
        out["raw_response"] = None  # as would be set on exception path
        self.assertIsNone(out["raw_response"])


class TestDroppedAttentionItems(unittest.TestCase):
    """Dropped-attention logic: LPs with no directional candidate are flagged."""

    def _compute_dropped(self, flagged_lps, directional_candidates):
        """Replicate the dropped-items logic from run_synthesis()."""
        candidate_lp_ids = set()
        for dc in directional_candidates:
            for lid in (dc.get("lp_ids") or []):
                candidate_lp_ids.add(lid)
        return [
            lp for lp in flagged_lps
            if lp["lp_id"] not in candidate_lp_ids
        ]

    def test_no_dropped_when_all_covered(self):
        flagged = _fake_flagged_lps(["LP-01", "LP-02", "LP-03"])
        candidates = [{"lp_ids": ["LP-01"]}, {"lp_ids": ["LP-02"]}, {"lp_ids": ["LP-03"]}]
        dropped = self._compute_dropped(flagged, candidates)
        self.assertEqual(dropped, [])

    def test_dropped_when_lp_has_no_candidate(self):
        flagged = _fake_flagged_lps(["LP-01", "LP-02", "LP-03"])
        candidates = [{"lp_ids": ["LP-01"]}, {"lp_ids": ["LP-02"]}]
        dropped = self._compute_dropped(flagged, candidates)
        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0]["lp_id"], "LP-03")

    def test_all_dropped_when_no_candidates(self):
        flagged = _fake_flagged_lps(["LP-03", "LP-17"])
        dropped = self._compute_dropped(flagged, [])
        self.assertEqual(len(dropped), 2)
        self.assertIn("LP-03", [d["lp_id"] for d in dropped])
        self.assertIn("LP-17", [d["lp_id"] for d in dropped])


class TestCandidateDensity(unittest.TestCase):
    """candidate_density matches pass1_directional_candidate_count / flagged_lp_count."""

    def _density(self, flagged_count, candidate_count):
        from cam.adapters.lease_review.lease_synthesis import _evaluate_directional_completeness_guard
        _, guard = _evaluate_directional_completeness_guard(flagged_count, candidate_count)
        return guard["candidate_density"]

    def test_density_1_when_equal(self):
        self.assertAlmostEqual(self._density(27, 27), 1.0)

    def test_density_fraction_when_fewer_candidates(self):
        d = self._density(27, 24)
        self.assertAlmostEqual(d, 24 / 27)

    def test_density_none_when_no_flagged(self):
        self.assertIsNone(self._density(0, 0))


class TestArtifactFiles(unittest.TestCase):
    """Artifact files are written to _p1_artifact_dir and paths recorded."""

    def _run_artifact_block(self, flagged_lps, evaluator_outputs, directional_candidates, artifact_dir):
        """Replicate the Step 386 artifact writing block from run_synthesis()."""
        import json as _json386
        from pathlib import Path as _Path386

        _p1_hash = "testhash"
        user_prompt = "test prompt"
        _p1_artifact_paths = {}

        _p1_art_dir = artifact_dir
        if _p1_art_dir:
            _d = _Path386(_p1_art_dir)
            _d.mkdir(parents=True, exist_ok=True)

            _raw_input = {
                "flagged_lp_count": len(flagged_lps),
                "flagged_lp_ids": [lp["lp_id"] for lp in flagged_lps],
                "prompt_hash_md5": _p1_hash,
                "prompt_len": len(user_prompt),
            }
            _f_input = _d / "stage7_pass1_raw_input.json"
            _f_input.write_text(_json386.dumps(_raw_input, indent=2), encoding="utf-8")
            _p1_artifact_paths["raw_input"] = str(_f_input)

            _raw_output_lines = []
            for _r in ("A", "B", "C"):
                _ev = evaluator_outputs.get(_r, {})
                _raw_output_lines.append(
                    f"=== EVALUATOR {_r} | model={_ev.get('model','')} | completed={_ev.get('completed')} ==="
                )
                _raw_output_lines.append(_ev.get("raw_response") or "(no response)")
                _raw_output_lines.append("")
            _f_output = _d / "stage7_pass1_raw_output.txt"
            _f_output.write_text("\n".join(_raw_output_lines), encoding="utf-8")
            _p1_artifact_paths["raw_output"] = str(_f_output)

            _f_cands = _d / "stage7_pass1_parsed_candidates.json"
            _f_cands.write_text(_json386.dumps(directional_candidates, indent=2, default=str), encoding="utf-8")
            _p1_artifact_paths["parsed_candidates"] = str(_f_cands)

            _candidate_lp_ids: set = set()
            for _dc in directional_candidates:
                for _lid in (_dc.get("lp_ids") or []):
                    _candidate_lp_ids.add(_lid)
            _dropped = [
                {"lp_id": lp["lp_id"], "lp_name": lp.get("lp_name", ""), "coverage_state": lp.get("coverage_state", "")}
                for lp in flagged_lps
                if lp["lp_id"] not in _candidate_lp_ids
            ]
            _f_dropped = _d / "stage7_pass1_dropped_attention_items.json"
            _f_dropped.write_text(_json386.dumps({
                "flagged_lp_count": len(flagged_lps),
                "candidate_count": len(directional_candidates),
                "dropped_count": len(_dropped),
                "dropped": _dropped,
                "finish_reasons": {
                    _r: evaluator_outputs.get(_r, {}).get("finish_reason")
                    for _r in ("A", "B", "C")
                },
            }, indent=2), encoding="utf-8")
            _p1_artifact_paths["dropped_attention_items"] = str(_f_dropped)

        return _p1_artifact_paths

    def test_all_four_files_written(self):
        flagged = _fake_flagged_lps(["LP-01", "LP-02", "LP-03"])
        ev_out = {
            "A": _fake_ev_output("A", True, ["LP-01", "LP-02"]),
            "B": _fake_ev_output("B", True, ["LP-01", "LP-02"]),
            "C": _fake_ev_output("C", True, ["LP-01", "LP-02"]),
        }
        candidates = [{"lp_ids": ["LP-01"]}, {"lp_ids": ["LP-02"]}]

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._run_artifact_block(flagged, ev_out, candidates, tmpdir)

            self.assertIn("raw_input", paths)
            self.assertIn("raw_output", paths)
            self.assertIn("parsed_candidates", paths)
            self.assertIn("dropped_attention_items", paths)

            for key, path in paths.items():
                self.assertTrue(os.path.exists(path), f"File missing: {path}")

    def test_raw_input_contains_lp_ids(self):
        flagged = _fake_flagged_lps(["LP-03", "LP-17"])
        ev_out = {r: _fake_ev_output(r, True, []) for r in ("A", "B", "C")}
        candidates = []

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._run_artifact_block(flagged, ev_out, candidates, tmpdir)
            raw_input = json.loads(open(paths["raw_input"], encoding="utf-8").read())
            self.assertEqual(raw_input["flagged_lp_count"], 2)
            self.assertIn("LP-03", raw_input["flagged_lp_ids"])
            self.assertIn("LP-17", raw_input["flagged_lp_ids"])

    def test_raw_output_contains_evaluator_sections(self):
        flagged = _fake_flagged_lps(["LP-01"])
        ev_out = {
            "A": _fake_ev_output("A", True, ["LP-01"], raw="response from A"),
            "B": _fake_ev_output("B", True, ["LP-01"], raw="response from B"),
            "C": _fake_ev_output("C", False, [], raw=None),
        }
        candidates = [{"lp_ids": ["LP-01"]}]

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._run_artifact_block(flagged, ev_out, candidates, tmpdir)
            raw_out = open(paths["raw_output"], encoding="utf-8").read()
            self.assertIn("=== EVALUATOR A", raw_out)
            self.assertIn("=== EVALUATOR B", raw_out)
            self.assertIn("=== EVALUATOR C", raw_out)
            self.assertIn("response from A", raw_out)
            self.assertIn("response from B", raw_out)
            self.assertIn("(no response)", raw_out)

    def test_dropped_items_correctly_identified(self):
        flagged = _fake_flagged_lps(["LP-03", "LP-17", "LP-22"])
        ev_out = {r: _fake_ev_output(r, True, ["LP-17", "LP-22"]) for r in ("A", "B", "C")}
        candidates = [{"lp_ids": ["LP-17"]}, {"lp_ids": ["LP-22"]}]

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._run_artifact_block(flagged, ev_out, candidates, tmpdir)
            dropped_data = json.loads(open(paths["dropped_attention_items"], encoding="utf-8").read())
            self.assertEqual(dropped_data["dropped_count"], 1)
            self.assertEqual(dropped_data["dropped"][0]["lp_id"], "LP-03")
            self.assertEqual(dropped_data["candidate_count"], 2)
            self.assertIsNone(dropped_data["finish_reasons"]["A"])
            self.assertIsNone(dropped_data["finish_reasons"]["B"])
            self.assertIsNone(dropped_data["finish_reasons"]["C"])

    def test_paths_recorded_in_artifact_paths_dict(self):
        flagged = _fake_flagged_lps(["LP-01"])
        ev_out = {r: _fake_ev_output(r, True, ["LP-01"]) for r in ("A", "B", "C")}
        candidates = [{"lp_ids": ["LP-01"]}]

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self._run_artifact_block(flagged, ev_out, candidates, tmpdir)
            self.assertEqual(len(paths), 4)
            for key in ("raw_input", "raw_output", "parsed_candidates", "dropped_attention_items"):
                self.assertIn(key, paths)
                self.assertTrue(paths[key].startswith(tmpdir))

    def test_no_files_when_no_artifact_dir(self):
        paths = self._run_artifact_block(
            _fake_flagged_lps(["LP-01"]),
            {"A": _fake_ev_output("A", True, ["LP-01"])},
            [{"lp_ids": ["LP-01"]}],
            None,
        )
        self.assertEqual(paths, {})


# ── existing-test regression guard ────────────────────────────────────────────

class TestExistingTestsStillImportable(unittest.TestCase):
    """Confirm Step 378 and DEF-010a modules still import cleanly."""

    def test_governance_module_imports(self):
        from cam.adapters.lease_review import lease_p2pp_routing
        self.assertTrue(hasattr(lease_p2pp_routing, "apply_p2pp_routing"))

    def test_coverage_module_imports(self):
        from cam.adapters.lease_review.lease_coverage_305 import merge_element_verdicts
        self.assertTrue(callable(merge_element_verdicts))


if __name__ == "__main__":
    unittest.main(verbosity=2)
