"""
Thin wrapper around provider_router adapters for simple text-in / text-out LLM calls.

Used by the follow-up Q&A chat endpoint. Unlike the pipeline stages (which use
ProviderRouter.call_json for structured JSON output), this module returns raw text
responses for conversational use.

Usage:
    from cam.core.llm import call_llm

    result = call_llm(
        provider="claude",       # "claude" | "openai" | "xai" | "google"
        system_prompt="You are a helpful assistant.",
        user_prompt="What is a triple net lease?",
        temperature=0.3,
    )
    print(result["content"])  # raw text response
"""

import logging
from typing import Dict, Any, Optional

from cam.core.provider_router import (
    ModelTarget,
    OpenAIAdapter,
    AnthropicAdapter,
    GoogleGenAIAdapter,
    XAIAdapter,
)

logger = logging.getLogger(__name__)

# Default models per provider (chat-optimized choices)
_DEFAULT_MODELS = {
    "claude":    ("anthropic", "claude-sonnet-4-20250514"),
    "openai":    ("openai",    "gpt-5.2"),
    "xai":       ("xai",       "grok-3"),
    "google":    ("google",    "gemini-2.5-pro"),
}

# Alias mappings
_PROVIDER_ALIASES = {
    "anthropic": "claude",
    "gpt":       "openai",
    "gemini":    "google",
    "grok":      "xai",
}

_ADAPTER_CLASSES = {
    "openai":    OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "google":    GoogleGenAIAdapter,
    "xai":       XAIAdapter,
}


def call_llm(
    provider: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_output_tokens: int = 4000,
    timeout_sec: float = 60.0,
) -> Dict[str, Any]:
    """Call a single LLM provider and return raw text response.

    Args:
        provider: Provider key ("claude", "openai", "xai", "google") or alias
        system_prompt: System/context prompt
        user_prompt: User question
        temperature: Sampling temperature (default 0.3 for balanced responses)
        max_output_tokens: Max tokens in response
        timeout_sec: Request timeout

    Returns:
        {"content": str, "provider": str, "model": str}

    Raises:
        Exception on API errors (caught by caller for graceful handling)
    """
    # Resolve aliases
    canonical = _PROVIDER_ALIASES.get(provider, provider)
    if canonical not in _DEFAULT_MODELS:
        raise ValueError(f"Unknown provider: {provider}. "
                         f"Valid: {list(_DEFAULT_MODELS.keys())}")

    provider_key, model_name = _DEFAULT_MODELS[canonical]

    # Build target
    target = ModelTarget(
        name=f"{provider_key}:{model_name}",
        provider=provider_key,
        model=model_name,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        timeout_sec=timeout_sec,
    )

    # Get adapter
    adapter_cls = _ADAPTER_CLASSES[provider_key]
    adapter = adapter_cls()

    logger.info(f"[llm] Calling {provider_key}:{model_name} (temp={temperature})")

    raw = adapter.call(system_prompt, user_prompt, target)

    return {
        "content": raw,
        "provider": provider_key,
        "model": model_name,
    }
