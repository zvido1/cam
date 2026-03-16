"""
CAM Core — Provider Health Tracker

Lightweight in-memory, thread-safe health tracker for API providers.
Tracks provider-level failures and marks providers as degraded for a
cooldown period after errors (503, timeout, connection failure).

Health state is per-process and resets on server restart.
"""

import threading
import time
from typing import Dict, Optional, Set


# Cooldown: how long a provider stays degraded after a failure (seconds)
DEGRADED_COOLDOWN_SEC = 60.0


class ProviderHealth:
    """Thread-safe provider health tracker.

    Usage:
        health = get_health_tracker()
        if health.is_available("google"):
            try:
                result = call_google(...)
            except TimeoutError:
                health.mark_degraded("google")
    """

    def __init__(self, cooldown_sec: float = DEGRADED_COOLDOWN_SEC):
        self._lock = threading.Lock()
        self._cooldown_sec = cooldown_sec
        # provider_name -> timestamp when degraded status expires
        self._degraded_until: Dict[str, float] = {}

    def is_available(self, provider: str) -> bool:
        """Check if a provider is currently available (not degraded)."""
        with self._lock:
            deadline = self._degraded_until.get(provider)
            if deadline is None:
                return True
            if time.time() >= deadline:
                # Cooldown expired — provider is back
                del self._degraded_until[provider]
                return True
            return False

    def mark_degraded(self, provider: str, reason: str = "") -> None:
        """Mark a provider as degraded for the cooldown period."""
        with self._lock:
            until = time.time() + self._cooldown_sec
            self._degraded_until[provider] = until
        print(f"[provider_health] {provider} marked DEGRADED for {self._cooldown_sec}s"
              f"{f': {reason}' if reason else ''}", flush=True)

    def get_status(self, provider: str) -> str:
        """Return 'up' or 'degraded'."""
        return "up" if self.is_available(provider) else "degraded"

    def get_all_statuses(self) -> Dict[str, str]:
        """Return status dict for all known providers."""
        providers = ["google", "openai", "anthropic", "xai", "mistral"]
        return {p: self.get_status(p) for p in providers}

    def filter_available(self, providers: list) -> list:
        """Filter a list of (provider, model) tuples to only available providers."""
        return [(p, m) for p, m in providers if self.is_available(p)]

    def reset(self) -> None:
        """Reset all providers to healthy (for testing)."""
        with self._lock:
            self._degraded_until.clear()


# ── Singleton ──

_instance: Optional[ProviderHealth] = None
_instance_lock = threading.Lock()


def get_health_tracker() -> ProviderHealth:
    """Get the global ProviderHealth singleton."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ProviderHealth()
    return _instance
