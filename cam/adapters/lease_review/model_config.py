"""
CAM Lease Review — Central Model Configuration

Single source of truth for ALL model strings and display names used across
the pipeline, chat endpoints, and frontend UI.

To upgrade a model: change it here. All stages, the chat advisor, and
the frontend display labels pick it up automatically via /api/models.

Last updated: 2026-05-01 (Step 293d)
  - Added CHAT_DEFAULTS, DISPLAY_NAMES, get_display_name()
  - llm.py and main.py now import from here instead of hardcoding
  - /api/models endpoint serves DISPLAY_NAMES to app.js at startup
"""

# ── Extractor (Stage 1) ───────────────────────────────────────────────────────
EXTRACTOR_PRIMARY   = ("google",      "gemini-3.1-pro-preview")
EXTRACTOR_FALLBACK  = ("google",      "gemini-2.5-pro")

EXTRACTION_CHAIN = [
    EXTRACTOR_PRIMARY,
    EXTRACTOR_FALLBACK,
    ("openai",     "gpt-5.5"),
    ("openai",     "gpt-5.4"),
    ("openai",     "gpt-5.2"),
    ("anthropic",  "claude-sonnet-4-6"),
    ("mistral",    "mistral-large-latest"),
]

# ── Evaluators (Stage 2) ──────────────────────────────────────────────────────
EVALUATOR_A_PRIMARY  = ("anthropic",  "claude-sonnet-4-6")
EVALUATOR_A_FALLBACK = ("anthropic",  "claude-haiku-4-5-20251001")

EVALUATOR_B_PRIMARY  = ("openai",     "gpt-5.5")
EVALUATOR_B_FALLBACK = ("openai",     "gpt-5.4")

EVALUATOR_C_PRIMARY  = ("xai",        "grok-4.3")
EVALUATOR_C_FALLBACK = ("xai",        "grok-4.3")  # grok-3 retired 2026-05-15

# ── Single-stage fallback chain (Challenge / Cascade / Severity) ──────────────
SINGLE_STAGE_CHAIN = [
    ("openai",     "gpt-5.5"),
    ("openai",     "gpt-5.4"),
    ("openai",     "gpt-5.2"),
    ("openai",     "gpt-4o"),
    ("anthropic",  "claude-sonnet-4-6"),
    ("google",     "gemini-2.5-pro"),
    ("xai",        "grok-4.3"),
]

# ── Chat / Advisory defaults ──────────────────────────────────────────────────
# Used by cam/core/llm.py and the /api/chat/* endpoints.
# These are the defaults when a provider key is specified without a model.
CHAT_DEFAULTS = {
    "claude":  ("anthropic", "claude-sonnet-4-6"),
    "openai":  ("openai",    "gpt-5.5"),
    "xai":     ("xai",       "grok-4.3"),
    "google":  ("google",    "gemini-3.1-pro-preview"),
}

# ── Display names ─────────────────────────────────────────────────────────────
# Single source of truth for model display names used in the UI.
# Served via /api/models endpoint; app.js fetches these at startup.
# When adding a new model to any chain above, add its display name here.
DISPLAY_NAMES = {
    # Anthropic
    "claude-sonnet-4-6":           "Claude Sonnet 4.6",
    "claude-opus-4-5-20250514":    "Claude Opus 4.5",
    "claude-haiku-4-5-20251001":   "Claude Haiku 4.5",
    "claude-haiku-4-5":            "Claude Haiku 4.5",
    # OpenAI
    "gpt-5.5":                     "GPT-5.5",
    "gpt-5.4":                     "GPT-5.4",
    "gpt-5.2":                     "GPT-5.2",
    "gpt-4o":                      "GPT-4o",
    # xAI
    "grok-4.3":                    "Grok 4.3",
    "grok-4":                      "Grok 4",    # retired 2026-05-15
    "grok-3":                      "Grok 3",    # retired 2026-05-15
    "grok-2":                      "Grok 2",
    # Google
    "gemini-3.1-pro-preview":      "Gemini 3.1 Pro",
    "gemini-2.5-pro":              "Gemini 2.5 Pro",
    "gemini-2.0-flash":            "Gemini 2.0 Flash",
    # Mistral
    "mistral-large-latest":        "Mistral Large",
    "mistral-medium-latest":       "Mistral Medium",
}


def get_display_name(model_string: str, fallback: str = None) -> str:
    """Return the display name for a model string, or fallback if not found."""
    return DISPLAY_NAMES.get(model_string, fallback or model_string)


# ── Evaluator display labels ──────────────────────────────────────────────────
# Derived from DISPLAY_NAMES so model migrations only require editing this file.
# All EVALUATORS / EVALUATOR_LINEUP / EVALUATOR_LINEUP_305 dicts import these.
EVALUATOR_A_LABEL          = get_display_name(EVALUATOR_A_PRIMARY[1],  "Claude Sonnet 4.6")
EVALUATOR_B_LABEL          = get_display_name(EVALUATOR_B_PRIMARY[1],  "GPT-5.5")
EVALUATOR_C_LABEL          = get_display_name(EVALUATOR_C_PRIMARY[1],  "Grok 4.3")
EVALUATOR_A_FALLBACK_LABEL = get_display_name(EVALUATOR_A_FALLBACK[1], "Claude Haiku 4.5")
EVALUATOR_B_FALLBACK_LABEL = get_display_name(EVALUATOR_B_FALLBACK[1], "GPT-5.4")
EVALUATOR_C_FALLBACK_LABEL = get_display_name(EVALUATOR_C_FALLBACK[1], "Grok 4.3")
