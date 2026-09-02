import os
import json
import time
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ── Evaluator generation-parameter capability map ─────────────────────────────
#
# Step 416: Replace the broad startswith("gpt-5") temperature guard with an
# explicit, per-model capability table.  Any model not in this table is assumed
# to support all declared generation parameters unless explicitly listed below.
#
# Populated from live probes run 2026-07-12:
#   gpt-5.5  → BadRequestError: "temperature does not support 0 with this model.
#              Only the default (1) value is supported."
#              ANY value other than 1 is rejected.  Only temperature=1 (default)
#              is accepted, so we treat this as temperature-unsupported.
#   gpt-5.4  → Accepts temperature=0. ✓
#   gpt-5.2  → Accepts temperature=0. ✓  (original adapter comment was wrong)
#   gpt-4o   → Accepts temperature=0. ✓
#
# When a model is in TEMPERATURE_ONLY_DEFAULT, the adapter:
#   (a) omits the temperature parameter from the outbound payload,
#   (b) records the omission reason in effective_request_metadata on the adapter,
#   (c) does NOT raise — this is a documented capability exception.
# When a model is NOT in TEMPERATURE_ONLY_DEFAULT and temperature is declared,
#   temperature MUST appear in the outbound payload or the integrity check raises.
#
TEMPERATURE_ONLY_DEFAULT_MODELS: frozenset = frozenset({
    "gpt-5.5",   # Only accepts temperature=1 (provider default). Probe 2026-07-12.
})

# All OpenAI models that use max_completion_tokens instead of max_tokens.
# Probe confirmed: gpt-5.x models use the Responses / Chat-Completions path
# that requires max_completion_tokens.  This set is separate from the
# temperature capability map.
MAX_COMPLETION_TOKENS_MODELS: frozenset = frozenset({
    "gpt-5.5", "gpt-5.4", "gpt-5.2",
})

# Evaluator-critical generation parameters — the complete declared set.
# Used by the integrity assertion to enumerate what must be checked.
EVALUATOR_CRITICAL_PARAMS: tuple = (
    "temperature",
    "max_tokens",          # maps to max_output_tokens on ModelTarget
    "reasoning_effort",
    # top_p, top_k, penalties: not declared anywhere in the evaluator stack;
    # no assertion needed unless added to ModelTarget in future.
)


def _check_generation_integrity(
    target: "ModelTarget",
    params: dict,
    temperature_omit_reason: Optional[str] = None,
) -> dict:
    """Assert declared evaluator generation config matches outbound payload.

    Step 416: Core invariant — any declared evaluator-critical generation
    parameter that does not appear in the outbound payload must be backed by an
    explicit capability exception.  Silent omission is a hard failure.

    Returns effective_request_metadata dict for logging.

    Raises FatalProviderError if an undocumented omission is detected.
    """
    declared = {
        "temperature": target.temperature,
        "max_tokens": target.max_output_tokens,
        "reasoning_effort": target.reasoning_effort,
    }

    transmitted = {}
    omitted = {}
    omission_reasons = {}

    # temperature
    if "temperature" in params:
        transmitted["temperature"] = params["temperature"]
    else:
        if temperature_omit_reason:
            omitted["temperature"] = target.temperature
            omission_reasons["temperature"] = temperature_omit_reason
        else:
            raise FatalProviderError(
                f"config_integrity_violation: declared temperature={target.temperature!r} "
                f"for model={target.model!r} was dropped with no capability exception. "
                f"Either add the model to TEMPERATURE_ONLY_DEFAULT_MODELS (with probe evidence) "
                f"or transmit the parameter."
            )

    # max_tokens (outbound key varies but something must be present)
    tok_key = "max_completion_tokens" if "max_completion_tokens" in params else "max_tokens"
    if tok_key in params:
        transmitted["max_tokens"] = params[tok_key]
        transmitted["_max_tokens_key"] = tok_key
    else:
        raise FatalProviderError(
            f"config_integrity_violation: max_output_tokens={target.max_output_tokens!r} "
            f"for model={target.model!r} not present in outbound payload."
        )

    # reasoning_effort — optional; only declared on some roles/stages
    if target.reasoning_effort is not None:
        if "reasoning_effort" in params:
            transmitted["reasoning_effort"] = params["reasoning_effort"]
        else:
            # reasoning_effort is only sent for reasoning models; non-reasoning
            # models legitimately don't receive it.  This is not an integrity
            # violation — reasoning_effort absence is model-gated, not silent.
            omitted["reasoning_effort"] = target.reasoning_effort
            omission_reasons["reasoning_effort"] = "non_reasoning_model_or_effort_not_applicable"

    return {
        "declared": declared,
        "transmitted": transmitted,
        "omitted": omitted,
        "omission_reasons": omission_reasons,
        "provider": getattr(target, "provider", None),
        "model": target.model,
    }

# Import robust JSON extraction (handles nested JSON from LLM responses)
from cam.core.json_extract import safe_json_extract as _safe_json_extract_v2

# Dry-run flag for OpenRouter (no API key needed for testing)
OPENROUTER_DRY_RUN = os.getenv("OPENROUTER_DRY_RUN", "1") == "1"
# Kill-switch to disable OpenRouter entirely (prevents accidental billing)
DISABLE_OPENROUTER = os.getenv("DISABLE_OPENROUTER", "0") == "1"

# -----------------------------
# Exceptions / error taxonomy
# -----------------------------
class ProviderError(Exception):
    """Base class for provider errors."""

class RetryableProviderError(ProviderError):
    """Transient error: retry / failover (429, 5xx, network)."""

class FatalProviderError(ProviderError):
    """Non-retryable error: bad request, auth, etc."""

# -----------------------------
# Budget + routing primitives
# -----------------------------
@dataclass
class ModelTarget:
    """
    A single "target" the router can call (provider + model).
    """
    name: str                       # e.g. "openai:gpt-5.2" or "openrouter:anthropic/claude-opus-4-5"
    provider: str                   # "openai" | "anthropic" | "xai" | "google" | "openrouter"
    model: str                      # provider-specific model name
    priority: int = 100             # lower = preferred
    enabled: bool = True
    max_retries: int = 2            # retries before failover
    timeout_sec: float = 45.0
    # Optional knobs for "degrade mode"
    max_output_tokens: int = 350
    temperature: float = 0.0
    reasoning_effort: Optional[str] = None  # For OpenAI GPT-5.2: "low" | "medium" | "high" | None; For Anthropic: also "xhigh"

@dataclass
class RouterConfig:
    # Global retry/backoff
    base_backoff_sec: float = 1.5
    max_backoff_sec: float = 20.0
    jitter_sec: float = 0.4

    # If True, try next provider on retryable errors
    failover_on_retryable: bool = True

    # Soft budgeting (router doesn't know your bill, but it can enforce rules you track)
    # You can wire these into a DB later. For now, in-memory counters.
    daily_request_soft_cap: Optional[int] = None
    per_request_provider_attempt_cap: int = 5

@dataclass
class RouterState:
    # Basic counters. Replace with DB in production.
    requests_today: int = 0
    by_target_requests: Dict[str, int] = field(default_factory=dict)
    by_target_failures: Dict[str, int] = field(default_factory=dict)

# -----------------------------
# Utilities
# -----------------------------
def _sleep_backoff(cfg: RouterConfig, attempt: int) -> None:
    backoff = min(cfg.max_backoff_sec, cfg.base_backoff_sec * (2 ** max(0, attempt - 1)))
    backoff += random.random() * cfg.jitter_sec
    time.sleep(backoff)

def _safe_json_extract(text: str) -> Dict[str, Any]:
    """
    Extract JSON object from a string that might contain extra text.
    Enhanced with repair attempts for common issues.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("empty_output")

    # fast path
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass  # fall through to repair

    # Try to strip markdown code blocks
    json_match = None
    for pattern in [
        r"```(?:json)?\s*(\{.*?\})\s*```",  # ```json {...} ```
        r"```\s*(\{.*?\})\s*```",           # ``` {...} ```
        r"`(\{.*?\})`",                      # `{...}`
    ]:
        import re
        match = re.search(pattern, text, re.DOTALL)
        if match:
            json_match = match.group(1)
            break
    
    if json_match:
        try:
            return json.loads(json_match)
        except json.JSONDecodeError:
            pass

    # Find JSON object - try from each { position until we find valid JSON
    # This handles cases where text contains { in non-JSON contexts (e.g., LaTeX)
    import re
    
    # First, try to find a JSON object that looks like our expected output format
    # Look for patterns like {"final_choice": or {"reasoning_similarity":
    json_pattern = r'\{[^{}]*"(?:final_choice|reasoning_similarity|candidate_options|shared_eliminations)"[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    # Fallback: try each { position from the end (JSON is usually at the end)
    brace_positions = [i for i, c in enumerate(text) if c == '{']
    end = text.rfind("}")
    
    if not brace_positions or end == -1:
        excerpt = text[:500] if len(text) > 500 else text
        raise ValueError(f"no_json_object_found (raw: {repr(excerpt)})")
    
    # Try from rightmost { first (most likely to be the JSON we want)
    for start in reversed(brace_positions):
        if start >= end:
            continue
        try:
            candidate = text[start:end+1]
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            continue
    
    # If nothing worked, give error with context
    excerpt = text[-500:] if len(text) > 500 else text
    raise ValueError(f"json_parse_failed: no valid JSON found (tail: {repr(excerpt)})")

# -----------------------------
# Provider adapters
# -----------------------------
def _extract_usage(resp) -> Optional[dict]:
    """Best-effort extraction of token usage from a provider response object.

    Step 372c (permitted observability utility — Step 211 precedent): pure
    side-channel read; NEVER affects the returned text or any verdict. Returns
    {output_tokens, input_tokens, reasoning_tokens} or None when usage is absent.
    Adapters stash this on ``self.last_usage`` so callers can surface real budget
    utilization. Supports both OpenAI-style (completion/prompt_tokens) and
    Anthropic-style (output/input_tokens) usage shapes.
    """
    try:
        u = getattr(resp, "usage", None)
        if u is None:
            return None
        out = getattr(u, "completion_tokens", None)
        if out is None:
            out = getattr(u, "output_tokens", None)
        inp = getattr(u, "prompt_tokens", None)
        if inp is None:
            inp = getattr(u, "input_tokens", None)
        reasoning = None
        details = getattr(u, "completion_tokens_details", None)
        if details is not None:
            reasoning = getattr(details, "reasoning_tokens", None)
        return {"output_tokens": out, "input_tokens": inp, "reasoning_tokens": reasoning}
    except Exception:
        return None


class BaseAdapter:
    # Step 372c: most recent call's token usage (None until a call populates it).
    last_usage: Optional[dict] = None
    # Step 528: the provider's own statement about why generation stopped.
    # Google sets MAX_TOKENS when it truncates; before this field the value was
    # read, matched, and dropped on the floor (see the `pass` below), so nothing
    # downstream could tell a complete response from a cut-off one.
    last_finish_reason: Optional[str] = None

    def call(self, system_prompt: str, user_prompt: str, target: ModelTarget) -> str:
        raise NotImplementedError

class OpenAIAdapter(BaseAdapter):
    """
    OpenAI Chat Completions adapter.
    Env: OPENAI_API_KEY
    """
    # Effort escalation ladder for empty-output retries on reasoning models
    EFFORT_ESCALATION = ["medium", "high"]

    # Step 416: per-call integrity metadata for the most recent call.
    last_integrity: Optional[dict] = None

    def __init__(self):
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise FatalProviderError("OPENAI_API_KEY missing")
        self.client = OpenAI(api_key=api_key, timeout=600.0)

    def _call_once(self, system_prompt: str, user_prompt: str, target: ModelTarget, effort_override: str = None) -> str:
        """Single API call with optional effort override.

        Step 416: Uses explicit per-model capability map (TEMPERATURE_ONLY_DEFAULT_MODELS
        and MAX_COMPLETION_TOKENS_MODELS) instead of broad startswith("gpt-5") guards.
        Runs _check_generation_integrity before every call — undocumented parameter
        omissions raise FatalProviderError.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        params: Dict[str, Any] = {
            "model": target.model,
            "messages": messages,
        }

        # Max-token field: models in MAX_COMPLETION_TOKENS_MODELS require the
        # Responses-API field name; all others use the standard max_tokens key.
        if target.model in MAX_COMPLETION_TOKENS_MODELS:
            params["max_completion_tokens"] = target.max_output_tokens
        else:
            params["max_tokens"] = target.max_output_tokens

        # Temperature: omit only for models in TEMPERATURE_ONLY_DEFAULT_MODELS.
        # Those models reject any non-default value (probe confirmed 2026-07-12).
        # All other models receive declared temperature — no broad prefix guard.
        temperature_omit_reason: Optional[str] = None
        if target.model in TEMPERATURE_ONLY_DEFAULT_MODELS:
            temperature_omit_reason = (
                f"model={target.model!r} only accepts temperature=1 (provider default); "
                f"declared temperature={target.temperature!r} omitted. "
                f"Capability exception: TEMPERATURE_ONLY_DEFAULT_MODELS. Probe: 2026-07-12."
            )
            # Omit temperature from params — provider default (1) governs.
        else:
            params["temperature"] = target.temperature

        # reasoning_effort: only reasoning models support it.
        effort = effort_override or target.reasoning_effort
        _is_reasoning_model = (
            target.model.startswith("gpt-5") or
            target.model.startswith("o1") or
            target.model.startswith("o3") or
            target.model.startswith("o4")
        )
        if effort and _is_reasoning_model:
            params["reasoning_effort"] = effort

        # Step 416: integrity assertion — raises FatalProviderError on undocumented omission.
        integrity = _check_generation_integrity(target, params, temperature_omit_reason)
        self.last_integrity = integrity
        print(
            f"[openai][integrity] model={target.model!r} "
            f"transmitted={list(integrity['transmitted'].keys())} "
            f"omitted={list(integrity['omitted'].keys())} "
            f"reasons={integrity['omission_reasons']}",
            flush=True,
        )

        resp = self.client.chat.completions.create(**params, timeout=target.timeout_sec)
        self.last_usage = _extract_usage(resp)
        if resp.choices and len(resp.choices) > 0:
            return resp.choices[0].message.content or ""
        return ""

    def call(self, system_prompt: str, user_prompt: str, target: ModelTarget) -> str:
        try:
            result = self._call_once(system_prompt, user_prompt, target)
            
            # If empty output on GPT-5.2 with reasoning_effort, try escalating
            if not result.strip() and target.model.startswith("gpt-5") and target.reasoning_effort:
                current_effort = target.reasoning_effort
                try:
                    current_idx = self.EFFORT_ESCALATION.index(current_effort)
                except ValueError:
                    current_idx = -1
                
                # Try higher efforts
                for next_idx in range(current_idx + 1, len(self.EFFORT_ESCALATION)):
                    next_effort = self.EFFORT_ESCALATION[next_idx]
                    print(f"[OPENAI] Empty output with effort={current_effort}, escalating to {next_effort}", flush=True)
                    result = self._call_once(system_prompt, user_prompt, target, effort_override=next_effort)
                    if result.strip():
                        print(f"[OPENAI] Escalation to {next_effort} succeeded", flush=True)
                        return result
                    current_effort = next_effort
            
            return result
        except Exception as e:
            msg = f"openai_error: {type(e).__name__}: {e}"
            # Try to detect common retryable patterns
            s = str(e).lower()
            if "rate limit" in s or "429" in s or "timeout" in s or "temporarily" in s:
                raise RetryableProviderError(msg)
            raise ProviderError(msg)

class AnthropicAdapter(BaseAdapter):
    """
    Env: ANTHROPIC_API_KEY
    """
    # Step 416: per-call integrity metadata for the most recent call.
    last_integrity: Optional[dict] = None

    def __init__(self):
        from anthropic import Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise FatalProviderError("ANTHROPIC_API_KEY missing")
        self.client = Anthropic(api_key=api_key, timeout=600.0)

    def call(self, system_prompt: str, user_prompt: str, target: ModelTarget) -> str:
        try:
            params: Dict[str, Any] = {
                "model": target.model,
                "max_tokens": target.max_output_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            }

            # Extended thinking mode: temperature is not supported alongside thinking.
            # Anthropic API rejects temperature when thinking is enabled.
            temperature_omit_reason: Optional[str] = None
            if target.reasoning_effort:
                budget_map = {"low": 5000, "medium": 10000, "high": 20000, "xhigh": 32000}
                budget = budget_map.get(target.reasoning_effort, 10000)
                params["thinking"] = {"type": "enabled", "budget_tokens": budget}
                temperature_omit_reason = (
                    f"Anthropic extended thinking (reasoning_effort={target.reasoning_effort!r}) "
                    f"does not support custom temperature; declared temperature={target.temperature!r} omitted. "
                    f"Capability exception: Anthropic extended-thinking API constraint."
                )
            else:
                params["temperature"] = target.temperature

            # Step 416: integrity assertion.
            integrity = _check_generation_integrity(target, params, temperature_omit_reason)
            self.last_integrity = integrity

            resp = self.client.messages.create(**params, timeout=target.timeout_sec)
            self.last_usage = _extract_usage(resp)
            chunks = []
            for block in resp.content:
                if getattr(block, "type", None) == "text":
                    chunks.append(block.text)
            return "\n".join(chunks).strip()
        except FatalProviderError:
            raise
        except Exception as e:
            msg = f"anthropic_error: {type(e).__name__}: {e}"
            s = str(e).lower()
            if "rate" in s or "429" in s or "overloaded" in s or "timeout" in s:
                raise RetryableProviderError(msg)
            if "not_found" in s or "model" in s and "not found" in s:
                raise FatalProviderError(msg)
            raise ProviderError(msg)

class GoogleGenAIAdapter(BaseAdapter):
    """
    Uses google-genai SDK (your current setup).
    Env: GEMINI_API_KEY
    """
    def __init__(self):
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise FatalProviderError("GEMINI_API_KEY missing")
        # Initialize client with custom httpx client that has longer timeout
        # Google GenAI SDK uses httpx internally, so we create a custom client
        # with a high timeout (600s) to prevent SDK from using default 1s deadline
        import httpx
        custom_httpx_client = httpx.Client(timeout=600.0)
        try:
            # Try to pass http_client if supported
            self.client = genai.Client(api_key=api_key, http_client=custom_httpx_client)
        except TypeError:
            # Fallback if http_client parameter not supported
            # Timeout will be enforced manually via router_elapsed checks
            self.client = genai.Client(api_key=api_key)

    def call(self, system_prompt: str, user_prompt: str, target: ModelTarget) -> str:
        import signal

        # Step 528: clear before the call. A stale MAX_TOKENS from a previous
        # call read as truncation on this one, which would be a false positive of
        # exactly the kind this field exists to prevent.
        self.last_finish_reason = None

        provider_start_time = time.time()
        router_start_time = time.time()
        
        # Timeout handler for hard timeout enforcement
        timeout_occurred = [False]
        
        def timeout_handler(signum, frame):
            timeout_occurred[0] = True
            raise TimeoutError(f"Gemini call exceeded timeout_sec={target.timeout_sec}")
        
        try:
            # Build config
            config = {
                "temperature": target.temperature,
                "max_output_tokens": target.max_output_tokens,
            }
            
            # Note: Google GenAI SDK doesn't accept deadline in config dict
            # Timeout is enforced manually via router_elapsed checks in the streaming loop
            # The SDK's internal HTTP client may have its own timeout, but we override via manual checks
            
            # For Gemini 3.0, use system_instruction if system prompt exists
            if system_prompt:
                config["system_instruction"] = system_prompt
                contents = user_prompt
            else:
                contents = user_prompt
            
            # Set up timeout signal (Unix only, main thread only)
            # Railway runs jobs in background threads where signal.alarm() is not allowed.
            # The streaming loop already enforces timeout via elapsed-time checks, so
            # signal.alarm() is only used as an additional safety net when available.
            import threading
            _in_main_thread = threading.current_thread() is threading.main_thread()
            if hasattr(signal, "SIGALRM") and _in_main_thread:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(target.timeout_sec))
            
            try:
                # Use streaming to work around MAX_TOKENS bug in Google GenAI SDK
                # When finish_reason is MAX_TOKENS, non-streaming responses can have empty content
                # Note: Google GenAI SDK doesn't expose per-request timeout, so we enforce it manually
                # The timeout_sec from ModelTarget is enforced via router_elapsed checks in the loop
                stream = self.client.models.generate_content_stream(
                    model=target.model,
                    contents=contents,
                    config=config,
                )
                
                # Collect all chunks from stream with timeout checking
                chunks = []
                last_chunk = None
                for chunk in stream:
                    router_elapsed = time.time() - router_start_time
                    if router_elapsed > target.timeout_sec:
                        timeout_occurred[0] = True
                        raise TimeoutError(f"Router timeout exceeded: {router_elapsed:.1f}s > {target.timeout_sec}s")
                    
                    last_chunk = chunk
                    # Try to get text from each chunk
                    if hasattr(chunk, "text") and chunk.text:
                        chunks.append(chunk.text)
                    # Also check candidates in chunk
                    elif hasattr(chunk, "candidates") and chunk.candidates:
                        for cand in chunk.candidates:
                            if hasattr(cand, "content") and hasattr(cand.content, "parts"):
                                parts = cand.content.parts
                                if parts:
                                    for p in parts:
                                        if hasattr(p, "text") and p.text:
                                            chunks.append(p.text)
                                        elif hasattr(p, "thought") and p.thought:
                                            chunks.append(str(p.thought))
                
                # Cancel timeout signal
                if hasattr(signal, "SIGALRM") and _in_main_thread:
                    signal.alarm(0)
                
                # Step 528: capture the finish reason and usage from the LAST chunk
                # of the stream. STREAMING IS THE PRIMARY PATH here (see the comment
                # above about the SDK's MAX_TOKENS bug), so recording finish_reason
                # only in the non-streaming fallback below left it None on every
                # real call -- and a None that means "not recorded" is
                # indistinguishable from a None that means "not truncated", which
                # is the exact ambiguity this step exists to remove.
                if last_chunk is not None:
                    try:
                        _lc_cands = getattr(last_chunk, "candidates", None) or []
                        if _lc_cands:
                            _fr = getattr(_lc_cands[0], "finish_reason", None)
                            if _fr:
                                self.last_finish_reason = str(_fr)
                        _um = getattr(last_chunk, "usage_metadata", None)
                        if _um is not None:
                            self.last_usage = _extract_usage(last_chunk)
                    except Exception:
                        # Never let telemetry capture break a successful call.
                        pass

                # If we got text from streaming, return it
                if chunks:
                    result = "".join(chunks).strip()
                    if result:
                        provider_elapsed = time.time() - provider_start_time
                        router_elapsed = time.time() - router_start_time
                        # Store timing in target for later retrieval (hacky but works)
                        target._provider_elapsed = provider_elapsed
                        target._router_elapsed = router_elapsed
                        return result
                
                # Use last chunk as response if streaming worked but no text found
                if last_chunk:
                    resp = last_chunk
                else:
                    raise Exception("No chunks received from stream")
            except TimeoutError:
                if hasattr(signal, "SIGALRM") and _in_main_thread:
                    signal.alarm(0)
                raise
            except Exception as e:
                # Cancel timeout signal before fallback
                if hasattr(signal, "SIGALRM") and _in_main_thread:
                    signal.alarm(0)
                # Fallback to non-streaming (but still enforce timeout)
                router_elapsed = time.time() - router_start_time
                if router_elapsed > target.timeout_sec:
                    raise TimeoutError(f"Router timeout exceeded before fallback: {router_elapsed:.1f}s > {target.timeout_sec}s")
                
                resp = self.client.models.generate_content(
                    model=target.model,
                    contents=contents,
                    config=config,
                )
            
            # Check timeout before processing response
            router_elapsed = time.time() - router_start_time
            if router_elapsed > target.timeout_sec:
                raise TimeoutError(f"Router timeout exceeded: {router_elapsed:.1f}s > {target.timeout_sec}s")
            
            # Follow official SDK pattern: use response.text directly
            # This is the recommended way per Google's quickstart
            try:
                text = resp.text
                if text and text.strip():
                    provider_elapsed = time.time() - provider_start_time
                    router_elapsed = time.time() - router_start_time
                    # Store timing in target for later retrieval
                    target._provider_elapsed = provider_elapsed
                    target._router_elapsed = router_elapsed
                    return text.strip()
            except Exception as e:
                pass  # Fall through to candidate extraction
            
            # Fallback: extract from candidates if response.text doesn't work
            cand = getattr(resp, "candidates", None) or []
            if not cand:
                provider_elapsed = time.time() - provider_start_time
                router_elapsed = time.time() - router_start_time
                target._provider_elapsed = provider_elapsed
                target._router_elapsed = router_elapsed
                raise RetryableProviderError("google_empty_output: no candidates")
            
            # Check finish reason
            finish_reason = getattr(cand[0], "finish_reason", None)
            if finish_reason:
                finish_str = str(finish_reason)
                # Step 528: RECORD it. This branch previously executed `pass` --
                # the truncation was detected, named in a comment, and discarded,
                # so a caller had no way to know the JSON it received was a cut-off
                # prefix. Behaviour is unchanged: MAX_TOKENS still continues to
                # extraction, because truncated content is still worth salvaging.
                # What changes is that the salvage is now visible.
                self.last_finish_reason = finish_str
                if "MAX_TOKENS" in finish_str:
                    # Continue to extract - truncated content is still valid
                    pass
                elif "SAFETY" in finish_str or "RECITATION" in finish_str:
                    raise FatalProviderError(f"google_safety_filter: {finish_reason}")
            
            # Extract from candidate content.parts
            candidate = cand[0]
            
            # Check finish_message - might contain the text when MAX_TOKENS is hit
            finish_message = getattr(candidate, "finish_message", None)
            if finish_message:
                try:
                    if hasattr(finish_message, "text"):
                        finish_text = finish_message.text
                        if finish_text and str(finish_text).strip():
                            return str(finish_text).strip()
                    elif hasattr(finish_message, "parts"):
                        finish_parts = finish_message.parts
                        if finish_parts:
                            out = []
                            for p in finish_parts:
                                if hasattr(p, "text"):
                                    out.append(str(p.text))
                            result = "\n".join(out).strip()
                            if result:
                                return result
                except Exception:
                    pass
            
            content = getattr(candidate, "content", None)
            if content:
                # Try parts
                parts = getattr(content, "parts", None)
                if parts:
                    out = []
                    for p in parts:
                        # Try as dict if it's a dict
                        if isinstance(p, dict):
                            if "text" in p and p["text"]:
                                out.append(str(p["text"]))
                            if "thought" in p and p["thought"]:
                                out.append(str(p["thought"]))
                        else:
                            # Try text attribute
                            t = getattr(p, "text", None)
                            if t and str(t).strip():
                                out.append(str(t))
                            # Try thought attribute
                            thought = getattr(p, "thought", None)
                            if thought and str(thought).strip():
                                out.append(str(thought))
                            # Try as string directly
                            elif isinstance(p, str):
                                out.append(p)
                            # Try model_dump if it's a Pydantic model
                            elif hasattr(p, "model_dump"):
                                p_dict = p.model_dump()
                                if "text" in p_dict and p_dict["text"]:
                                    out.append(str(p_dict["text"]))
                                if "thought" in p_dict and p_dict["thought"]:
                                    out.append(str(p_dict["thought"]))
                    result = "\n".join(out).strip()
                    if result:
                        return result
            
            raise RetryableProviderError("google_empty_output: no extractable text")
        except Exception as e:
            msg = f"google_error: {type(e).__name__}: {e}"
            s = str(e).lower()
            if "429" in s or "resource_exhausted" in s or "quota" in s:
                raise RetryableProviderError(msg)
            raise ProviderError(msg)

class XAIAdapter(BaseAdapter):
    """
    xAI via OpenAI-compatible endpoint.
    Env: XAI_API_KEY
    """
    # Step 416: per-call integrity metadata for the most recent call.
    last_integrity: Optional[dict] = None

    def __init__(self):
        from openai import OpenAI
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise FatalProviderError("XAI_API_KEY missing")
        self.base_url = "https://api.x.ai/v1"
        self.api_key = api_key
        self._openai_class = OpenAI

    def call(self, system_prompt: str, user_prompt: str, target: ModelTarget) -> str:
        timeout_sec = target.timeout_sec if target.timeout_sec else 60.0
        client = self._openai_class(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout_sec,
        )
        try:
            params: Dict[str, Any] = {
                "model": target.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": target.temperature,
                "max_tokens": target.max_output_tokens,
            }

            # Step 416: integrity assertion — temperature unconditionally transmitted.
            integrity = _check_generation_integrity(target, params)
            self.last_integrity = integrity

            resp = client.chat.completions.create(**params)
            self.last_usage = _extract_usage(resp)
            return (resp.choices[0].message.content or "").strip()
        except FatalProviderError:
            raise
        except Exception as e:
            msg = f"xai_error: {type(e).__name__}: {e}"
            s = str(e).lower()
            if "429" in s or "rate" in s or "timeout" in s or "temporarily" in s:
                raise RetryableProviderError(msg)
            if "401" in s or "unauthorized" in s or "invalid api key" in s:
                raise FatalProviderError(msg)
            raise ProviderError(msg)

def _call_openrouter_stub(prompt: str) -> dict:
    """Dry-run stub for OpenRouter - returns mock FEVER response."""
    return {
        "label": "NEI",
        "confidence": "low",  # Valid: "low", "medium", or "high"
        "reason": "openrouter dry-run stub",
        "raw": ""
    }

class OpenRouterAdapter(BaseAdapter):
    """
    OpenRouter is basically OpenAI-compatible for chat/completions.
    Env: OPENROUTER_API_KEY (or OPENROUTER_DRY_RUN=1 for stub mode)
    """
    def __init__(self):
        if OPENROUTER_DRY_RUN:
            # Skip client init in dry-run mode
            self.client = None
            return
        
        from openai import OpenAI
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise FatalProviderError("OPENROUTER_API_KEY missing")
        # OpenRouter uses OpenAI-compatible endpoint with proper headers
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
            default_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost"),
                "X-Title": os.getenv("OPENROUTER_APP_NAME", "DoubleCheck"),
            },
        )

    def call(self, system_prompt: str, user_prompt: str, target: ModelTarget) -> str:
        # Log when OpenRouter is actually called (for debugging billing)
        print("[OPENROUTER] CALLED — THIS SHOULD NOT HAPPEN", flush=True)
        print(f"[OPENROUTER] model={target.model} name={target.name}", flush=True)
        
        # Dry-run mode: return JSON string from stub
        if OPENROUTER_DRY_RUN:
            stub_result = _call_openrouter_stub(user_prompt)
            return json.dumps(stub_result)
        
        try:
            # OpenRouter supports chat.completions style
            resp = self.client.chat.completions.create(
                model=target.model,  # e.g. "anthropic/claude-opus-4-5"
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=target.temperature,
                max_tokens=target.max_output_tokens,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            msg = f"openrouter_error: {type(e).__name__}: {e}"
            s = str(e).lower()
            if "429" in s or "rate" in s or "temporarily" in s or "timeout" in s:
                raise RetryableProviderError(msg)
            raise ProviderError(msg)

# -----------------------------
# Router
# -----------------------------
class ProviderRouter:
    def __init__(self, targets: List[ModelTarget], cfg: Optional[RouterConfig] = None):
        self.cfg = cfg or RouterConfig()
        self.state = RouterState()

        # sort by priority (lower is better)
        # Filter out OpenRouter if DISABLE_OPENROUTER is set
        filtered_targets = [t for t in targets if t.enabled]
        if DISABLE_OPENROUTER:
            filtered_targets = [t for t in filtered_targets if t.provider != "openrouter"]
        self.targets = sorted(filtered_targets, key=lambda x: x.priority)
        
        # Debug: print targets after filtering (single line to avoid noise)
        target_list = [(t.provider, t.name) for t in self.targets]
        print(f"[router] initialized with {len(self.targets)} targets after filtering: {target_list}", flush=True)

        # lazy init adapters (some require installed deps)
        self.adapters: Dict[str, BaseAdapter] = {}

    def _get_adapter(self, provider: str) -> BaseAdapter:
        if provider in self.adapters:
            return self.adapters[provider]
        if provider == "openai":
            self.adapters[provider] = OpenAIAdapter()
        elif provider == "anthropic":
            self.adapters[provider] = AnthropicAdapter()
        elif provider == "google":
            self.adapters[provider] = GoogleGenAIAdapter()
        elif provider == "xai":
            self.adapters[provider] = XAIAdapter()
        elif provider == "openrouter":
            self.adapters[provider] = OpenRouterAdapter()
        else:
            raise FatalProviderError(f"Unknown provider: {provider}")
        return self.adapters[provider]

    def call_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_validate_fn=None,
        prefer_targets: Optional[List[str]] = None,
        allowed_providers: Optional[set] = None,
        trace: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Try targets in order. On success return (json_obj, meta).
        Meta includes which target was used and error history.
        
        Args:
            allowed_providers: If set, ONLY try targets from these providers (no fallback to others).
        """
        trace = trace or {}
        errors: List[Dict[str, Any]] = []

        if self.cfg.daily_request_soft_cap is not None and self.state.requests_today >= self.cfg.daily_request_soft_cap:
            raise RetryableProviderError("router_daily_soft_cap_reached")

        # Filter to allowed providers ONLY (hard constraint, no fallback)
        targets = self.targets
        if allowed_providers is not None:
            targets = [t for t in targets if t.provider in allowed_providers]
            if not targets:
                raise FatalProviderError(f"no_targets_for_allowed_providers: {allowed_providers}")

        # If prefer_targets provided, reorder so those come first (but keep priority among them)
        if prefer_targets:
            prefer_set = set(prefer_targets)
            preferred = [t for t in targets if t.name in prefer_set]
            rest = [t for t in targets if t.name not in prefer_set]
            targets = preferred + rest

        attempts = 0
        for t in targets:
            if attempts >= self.cfg.per_request_provider_attempt_cap:
                break

            adapter = self._get_adapter(t.provider)
            # per-target retries
            for attempt in range(1, t.max_retries + 1):
                attempts += 1
                try:
                    raw = adapter.call(system_prompt, user_prompt, t)

                    try:
                        obj = _safe_json_extract_v2(raw)
                    except ValueError as json_err:
                        # A1: Capture raw response for debugging
                        error_msg = str(json_err)
                        # Store raw in trace for debugging
                        if trace is not None:
                            trace["raw_response_on_json_fail"] = raw[:1000] if raw else None
                        raise ProviderError(f"json_extraction_failed: {error_msg}")

                    if schema_validate_fn:
                        ok, why = schema_validate_fn(obj)
                        if not ok:
                            if trace is not None:
                                trace["parsed_obj_on_schema_fail"] = obj
                                trace["schema_fail_top_level_keys"] = list(obj.keys()) if isinstance(obj, dict) else None
                                try:
                                    import json as _json
                                    trace["schema_fail_preview"] = _json.dumps(obj, ensure_ascii=True)[:1000]
                                except Exception:
                                    trace["schema_fail_preview"] = str(obj)[:1000]
                            raise ProviderError(f"schema_validation_failed: {why}")

                    # Router-level assertion: verify picked target matches allowed providers
                    if allowed_providers is not None and t.provider not in allowed_providers:
                        raise RuntimeError(f"router_bug: selected target {t.name} (provider={t.provider}) not in allowed_providers {allowed_providers}")

                    # update state
                    self.state.requests_today += 1
                    self.state.by_target_requests[t.name] = self.state.by_target_requests.get(t.name, 0) + 1

                    meta = {
                        "target": {"name": t.name, "provider": t.provider, "model": t.model},
                        "attempts": attempts,
                        "errors": errors,
                        "raw_excerpt": (raw[:250] + "...") if raw and len(raw) > 250 else raw,
                        "trace": trace,
                    }
                    return obj, meta

                except RetryableProviderError as e:
                    err = {"target": t.name, "attempt": attempt, "retryable": True, "error": str(e)}
                    errors.append(err)
                    self.state.by_target_failures[t.name] = self.state.by_target_failures.get(t.name, 0) + 1
                    _sleep_backoff(self.cfg, attempt)
                    # If last retry for this target, fall through to next target
                    continue

                except FatalProviderError as e:
                    err = {"target": t.name, "attempt": attempt, "retryable": False, "fatal": True, "error": str(e)}
                    errors.append(err)
                    self.state.by_target_failures[t.name] = self.state.by_target_failures.get(t.name, 0) + 1
                    # fatal -> don't retry this target further
                    break

                except ProviderError as e:
                    # treat unknown provider errors as retryable once, then failover
                    err = {"target": t.name, "attempt": attempt, "retryable": True, "error": str(e)}
                    errors.append(err)
                    self.state.by_target_failures[t.name] = self.state.by_target_failures.get(t.name, 0) + 1
                    _sleep_backoff(self.cfg, attempt)
                    continue

        raise RetryableProviderError(f"all_targets_failed: {errors}")
