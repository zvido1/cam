"""Step 416 — Evaluator generation-config integrity tests.

Covers:
1. gpt-5.5: temperature=0 declared → omitted with capability exception recorded (not rejected).
2. gpt-5.4: temperature=0 declared → transmitted in outbound payload.
3. gpt-5.2: temperature=0 declared → transmitted in outbound payload.
4. No broad prefix: gpt-5.4 and gpt-5.2 are NOT caught by TEMPERATURE_ONLY_DEFAULT_MODELS.
5. Guard failure: undocumented omission raises FatalProviderError.
6. Integrity assertion records declared/transmitted/omitted/omission_reasons structure.
7. Anthropic temperature-with-thinking: omission backed by capability exception.
8. Anthropic normal (no reasoning_effort): temperature transmitted.
9. xAI: temperature unconditionally transmitted.
10. max_tokens field present in all provider params (no silent drop).
11. reasoning_effort transmitted only for reasoning models (openai); omission for non-reasoning recorded.
12. 414 evaluator lineup unchanged: Role A=anthropic, B=openai, C=xai; provider dedup invariant preserved.

All tests are no-API-call (pure unit). Run:
  PYTHONPATH=. python -m pytest cam/adapters/lease_review/tests/test_416_config_integrity.py -v
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cam.core.provider_router import (
    ModelTarget,
    FatalProviderError,
    TEMPERATURE_ONLY_DEFAULT_MODELS,
    MAX_COMPLETION_TOKENS_MODELS,
    _check_generation_integrity,
)
from cam.adapters.lease_review.lease_evaluate import EVALUATORS


# ── Helpers ──────────────────────────────────────────────────────────────────

def _target(model: str, temperature: float = 0.0, reasoning_effort=None,
            max_output_tokens: int = 1000, provider: str = "openai") -> ModelTarget:
    return ModelTarget(
        name=f"test:{model}",
        provider=provider,
        model=model,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        reasoning_effort=reasoning_effort,
    )


def _openai_params(target: ModelTarget, include_temperature: bool = True) -> dict:
    """Build the minimal params dict as the OpenAI adapter would, for testing."""
    params: dict = {"model": target.model, "messages": []}
    if target.model in MAX_COMPLETION_TOKENS_MODELS:
        params["max_completion_tokens"] = target.max_output_tokens
    else:
        params["max_tokens"] = target.max_output_tokens
    if include_temperature:
        params["temperature"] = target.temperature
    return params


# ── 1. gpt-5.5: temperature omitted with capability exception ─────────────────

class TestGpt55TemperatureOmission(unittest.TestCase):

    def test_gpt55_in_temperature_only_default(self):
        """gpt-5.5 must be in TEMPERATURE_ONLY_DEFAULT_MODELS (probe-confirmed)."""
        self.assertIn("gpt-5.5", TEMPERATURE_ONLY_DEFAULT_MODELS)

    def test_gpt55_integrity_omission_is_not_an_error(self):
        """_check_generation_integrity with documented omission reason must not raise."""
        t = _target("gpt-5.5", temperature=0.0)
        params = _openai_params(t, include_temperature=False)
        omit_reason = "model only accepts temperature=1; TEMPERATURE_ONLY_DEFAULT_MODELS exception"
        meta = _check_generation_integrity(t, params, temperature_omit_reason=omit_reason)
        self.assertIn("temperature", meta["omitted"])
        self.assertIn("temperature", meta["omission_reasons"])
        self.assertNotIn("temperature", meta["transmitted"])

    def test_gpt55_omission_reason_recorded(self):
        """Omission reason string must be non-empty."""
        t = _target("gpt-5.5", temperature=0.0)
        params = _openai_params(t, include_temperature=False)
        meta = _check_generation_integrity(t, params, temperature_omit_reason="cap_exception")
        self.assertTrue(meta["omission_reasons"]["temperature"])

    def test_gpt55_declared_value_preserved_in_omitted(self):
        """The declared temperature=0.0 must be preserved in omitted (not lost)."""
        t = _target("gpt-5.5", temperature=0.0)
        params = _openai_params(t, include_temperature=False)
        meta = _check_generation_integrity(t, params, temperature_omit_reason="cap")
        self.assertEqual(meta["omitted"]["temperature"], 0.0)


# ── 2. gpt-5.4: temperature transmitted ──────────────────────────────────────

class TestGpt54TemperatureTransmitted(unittest.TestCase):

    def test_gpt54_not_in_temperature_only_default(self):
        """gpt-5.4 must NOT be in TEMPERATURE_ONLY_DEFAULT_MODELS."""
        self.assertNotIn("gpt-5.4", TEMPERATURE_ONLY_DEFAULT_MODELS)

    def test_gpt54_temperature_transmitted(self):
        """gpt-5.4 with temperature=0 → transmitted in payload, no omission."""
        t = _target("gpt-5.4", temperature=0.0)
        params = _openai_params(t, include_temperature=True)
        meta = _check_generation_integrity(t, params)
        self.assertIn("temperature", meta["transmitted"])
        self.assertEqual(meta["transmitted"]["temperature"], 0.0)
        self.assertNotIn("temperature", meta["omitted"])

    def test_gpt54_in_max_completion_tokens_models(self):
        """gpt-5.4 uses max_completion_tokens (not max_tokens)."""
        self.assertIn("gpt-5.4", MAX_COMPLETION_TOKENS_MODELS)


# ── 3. gpt-5.2: temperature transmitted (original comment was wrong) ──────────

class TestGpt52TemperatureTransmitted(unittest.TestCase):

    def test_gpt52_not_in_temperature_only_default(self):
        """gpt-5.2 must NOT be in TEMPERATURE_ONLY_DEFAULT_MODELS."""
        self.assertNotIn("gpt-5.2", TEMPERATURE_ONLY_DEFAULT_MODELS)

    def test_gpt52_temperature_transmitted(self):
        """gpt-5.2 with temperature=0 → transmitted, no omission."""
        t = _target("gpt-5.2", temperature=0.0)
        params = _openai_params(t, include_temperature=True)
        meta = _check_generation_integrity(t, params)
        self.assertIn("temperature", meta["transmitted"])
        self.assertNotIn("temperature", meta["omitted"])


# ── 4. No broad prefix regression ─────────────────────────────────────────────

class TestNoBroadPrefixRegression(unittest.TestCase):

    def test_only_gpt55_in_temperature_only_default(self):
        """TEMPERATURE_ONLY_DEFAULT_MODELS must not contain gpt-5.4 or gpt-5.2."""
        self.assertNotIn("gpt-5.4", TEMPERATURE_ONLY_DEFAULT_MODELS)
        self.assertNotIn("gpt-5.2", TEMPERATURE_ONLY_DEFAULT_MODELS)

    def test_gpt55_excluded_not_54(self):
        """The set is narrow: only the probe-confirmed model is excluded."""
        excluded = [m for m in TEMPERATURE_ONLY_DEFAULT_MODELS if m.startswith("gpt-5")]
        self.assertIn("gpt-5.5", excluded)
        self.assertNotIn("gpt-5.4", excluded)


# ── 5. Guard failure: undocumented omission raises FatalProviderError ─────────

class TestGuardFailure(unittest.TestCase):

    def test_undocumented_omission_raises(self):
        """Dropping temperature with no exception reason must raise FatalProviderError."""
        t = _target("gpt-5.4", temperature=0.0)
        params = _openai_params(t, include_temperature=False)  # temperature missing, no reason
        with self.assertRaises(FatalProviderError) as ctx:
            _check_generation_integrity(t, params, temperature_omit_reason=None)
        self.assertIn("config_integrity_violation", str(ctx.exception))

    def test_max_tokens_missing_raises(self):
        """Dropping max_tokens entirely must raise FatalProviderError."""
        t = _target("gpt-4o", temperature=0.0, provider="openai")
        params = {"model": t.model, "messages": [], "temperature": 0.0}
        # No max_tokens or max_completion_tokens in params
        with self.assertRaises(FatalProviderError) as ctx:
            _check_generation_integrity(t, params)
        self.assertIn("config_integrity_violation", str(ctx.exception))


# ── 6. Integrity metadata structure ──────────────────────────────────────────

class TestIntegrityMetadataStructure(unittest.TestCase):

    def test_metadata_keys_present(self):
        """Metadata dict must have declared, transmitted, omitted, omission_reasons, provider, model."""
        t = _target("gpt-5.4", temperature=0.0)
        params = _openai_params(t, include_temperature=True)
        meta = _check_generation_integrity(t, params)
        for key in ("declared", "transmitted", "omitted", "omission_reasons", "model"):
            self.assertIn(key, meta, f"Missing key: {key}")

    def test_declared_values_match_target(self):
        """Declared dict must reflect ModelTarget values."""
        t = _target("gpt-5.4", temperature=0.0, max_output_tokens=3000)
        params = _openai_params(t, include_temperature=True)
        meta = _check_generation_integrity(t, params)
        self.assertEqual(meta["declared"]["temperature"], 0.0)
        self.assertEqual(meta["declared"]["max_tokens"], 3000)


# ── 7. Anthropic temperature-with-thinking: capability exception ──────────────

class TestAnthropicThinkingTemperature(unittest.TestCase):

    def test_thinking_mode_omits_temperature_with_reason(self):
        """Anthropic extended-thinking path omits temperature with documented reason."""
        t = _target("claude-sonnet-4-6", temperature=0.0, reasoning_effort="medium",
                    provider="anthropic")
        # Anthropic adapter adds 'thinking' and omits temperature when reasoning_effort is set
        params = {
            "model": t.model,
            "max_tokens": t.max_output_tokens,
            "system": "",
            "messages": [],
            "thinking": {"type": "enabled", "budget_tokens": 10000},
            # temperature intentionally absent
        }
        omit_reason = "Anthropic extended thinking does not support custom temperature"
        meta = _check_generation_integrity(t, params, temperature_omit_reason=omit_reason)
        self.assertIn("temperature", meta["omitted"])
        self.assertNotIn("temperature", meta["transmitted"])


# ── 8. Anthropic normal (no reasoning_effort): temperature transmitted ─────────

class TestAnthropicNormalMode(unittest.TestCase):

    def test_normal_mode_transmits_temperature(self):
        """Anthropic without extended thinking transmits temperature=0."""
        t = _target("claude-sonnet-4-6", temperature=0.0, provider="anthropic")
        params = {
            "model": t.model,
            "max_tokens": t.max_output_tokens,
            "system": "",
            "messages": [],
            "temperature": 0.0,
        }
        meta = _check_generation_integrity(t, params)
        self.assertIn("temperature", meta["transmitted"])
        self.assertEqual(meta["transmitted"]["temperature"], 0.0)
        self.assertNotIn("temperature", meta["omitted"])


# ── 9. xAI: temperature unconditionally transmitted ───────────────────────────

class TestXAIAdapter(unittest.TestCase):

    def test_xai_temperature_transmitted(self):
        """xAI adapter includes temperature in params unconditionally."""
        t = _target("grok-4.3", temperature=0.0, provider="xai")
        params = {
            "model": t.model,
            "messages": [],
            "temperature": 0.0,
            "max_tokens": t.max_output_tokens,
        }
        meta = _check_generation_integrity(t, params)
        self.assertIn("temperature", meta["transmitted"])
        self.assertNotIn("temperature", meta["omitted"])


# ── 10. max_tokens field present in all provider params ───────────────────────

class TestMaxTokensField(unittest.TestCase):

    def _assert_max_tokens_present(self, model, provider="openai"):
        t = _target(model, provider=provider)
        if model in MAX_COMPLETION_TOKENS_MODELS:
            params = {"model": model, "messages": [], "max_completion_tokens": 1000,
                      "temperature": 0.0}
        else:
            params = {"model": model, "messages": [], "max_tokens": 1000,
                      "temperature": 0.0}
        meta = _check_generation_integrity(t, params)
        self.assertIn("max_tokens", meta["transmitted"])

    def test_gpt55_max_tokens_recorded(self):
        t = _target("gpt-5.5")
        params = {"model": "gpt-5.5", "messages": [], "max_completion_tokens": 1000}
        meta = _check_generation_integrity(t, params, temperature_omit_reason="cap")
        self.assertIn("max_tokens", meta["transmitted"])
        self.assertEqual(meta["transmitted"]["_max_tokens_key"], "max_completion_tokens")

    def test_gpt4o_max_tokens_recorded(self):
        self._assert_max_tokens_present("gpt-4o")

    def test_gpt54_max_tokens_is_max_completion_tokens(self):
        t = _target("gpt-5.4")
        params = {"model": "gpt-5.4", "messages": [], "max_completion_tokens": 2000,
                  "temperature": 0.0}
        meta = _check_generation_integrity(t, params)
        self.assertEqual(meta["transmitted"]["_max_tokens_key"], "max_completion_tokens")


# ── 11. reasoning_effort: transmitted for reasoning models, omission recorded ──

class TestReasoningEffort(unittest.TestCase):

    def test_reasoning_effort_transmitted_when_declared(self):
        """reasoning_effort in params → recorded in transmitted."""
        t = _target("gpt-5.5", reasoning_effort="medium")
        params = {"model": t.model, "messages": [], "max_completion_tokens": 1000,
                  "reasoning_effort": "medium"}
        meta = _check_generation_integrity(t, params, temperature_omit_reason="cap")
        self.assertIn("reasoning_effort", meta["transmitted"])

    def test_reasoning_effort_omission_not_hard_failure(self):
        """reasoning_effort declared but absent from params → recorded in omitted, no raise."""
        t = _target("gpt-5.4", reasoning_effort="medium")
        params = {"model": t.model, "messages": [], "max_completion_tokens": 1000,
                  "temperature": 0.0}
        # reasoning_effort absent — non-reasoning-model path
        meta = _check_generation_integrity(t, params)
        self.assertIn("reasoning_effort", meta["omitted"])
        self.assertIn("reasoning_effort", meta["omission_reasons"])

    def test_reasoning_effort_none_no_omission_recorded(self):
        """When reasoning_effort is None, omitted dict must not contain it."""
        t = _target("gpt-5.4", reasoning_effort=None)
        params = {"model": t.model, "messages": [], "max_completion_tokens": 1000,
                  "temperature": 0.0}
        meta = _check_generation_integrity(t, params)
        self.assertNotIn("reasoning_effort", meta["omitted"])


# ── 12. 414 evaluator lineup unchanged ────────────────────────────────────────

class TestEvaluatorLineupUnchanged(unittest.TestCase):
    """414 invariant: evaluator identities and providers unchanged by 416 patch."""

    def test_role_a_provider_anthropic(self):
        self.assertEqual(EVALUATORS["A"]["provider"], "anthropic")

    def test_role_b_provider_openai(self):
        self.assertEqual(EVALUATORS["B"]["provider"], "openai")

    def test_role_c_provider_xai(self):
        self.assertEqual(EVALUATORS["C"]["provider"], "xai")

    def test_role_a_model_claude_sonnet(self):
        self.assertIn("claude-sonnet", EVALUATORS["A"]["model"])

    def test_role_b_model_gpt55(self):
        self.assertEqual(EVALUATORS["B"]["model"], "gpt-5.5")

    def test_role_c_model_grok(self):
        self.assertIn("grok", EVALUATORS["C"]["model"])

    def test_all_roles_declare_temperature_zero(self):
        for role in ("A", "B", "C"):
            self.assertEqual(EVALUATORS[role]["temperature"], 0.0,
                             f"Role {role} temperature should be 0.0")

    def test_providers_are_distinct(self):
        providers = [EVALUATORS[r]["provider"] for r in ("A", "B", "C")]
        self.assertEqual(len(providers), len(set(providers)), "Provider dedup violated")


if __name__ == "__main__":
    unittest.main(verbosity=2)
