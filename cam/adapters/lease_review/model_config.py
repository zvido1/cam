"""
CAM Lease Review — Central Model Configuration

Single source of truth for all model strings used in the pipeline.
To upgrade a model, change it here — all stages pick it up automatically.

Last updated: 2026-05-01 (Step 290)
  - gemini-3-pro-preview was SHUT DOWN March 9, 2026. Now using
    gemini-3.1-pro-preview (current active 3.1 generation preview model).
  - gemini-2.5-pro retained as fallback (schema compliance issues seen
    in Step 289 are prompt-level, not model availability issues)
  - gpt-5.5 released April 24, 2026 — now primary in extraction chain,
    Evaluator B, and single-stage chain
  - Evaluator A: claude-sonnet-4-20250514 → claude-sonnet-4-6
  - Evaluator A fallback: claude-sonnet-4-6 → claude-haiku-4-5-20251001
  - Evaluator B: gpt-5.2 → gpt-5.5; fallback gpt-4o → gpt-5.4
  - Single-stage chain: gpt-5.2 primary → gpt-5.5 primary
  - grok-4/grok-3: unchanged
"""

# ── Extractor (Stage 1) ────────────────────────────────────────────────────────
# Gemini is the preferred extractor (1M context, strong document comprehension).
# gemini-3-pro-preview was SHUT DOWN March 9, 2026 — now using gemini-3.1-pro-preview.
# gemini-2.5-pro retained as first fallback (stable, 1M context).
# Pipeline falls through to GPT if all Gemini models fail.
EXTRACTOR_PRIMARY   = ("google",      "gemini-3.1-pro-preview")
EXTRACTOR_FALLBACK  = ("google",      "gemini-2.5-pro")

EXTRACTION_CHAIN = [
    EXTRACTOR_PRIMARY,
    EXTRACTOR_FALLBACK,
    ("openai",     "gpt-5.5"),
    ("openai",     "gpt-5.4"),
    ("openai",     "gpt-5.2"),
    ("anthropic",  "claude-sonnet-4-6"),
    ("mistral",    "mistral-large-latest"),   # last resort — provider diversity
]

# ── Evaluators (Stage 2) ───────────────────────────────────────────────────────
# Three independent models, one per provider. Blind to each other.
EVALUATOR_A_PRIMARY  = ("anthropic",  "claude-sonnet-4-6")
EVALUATOR_A_FALLBACK = ("anthropic",  "claude-haiku-4-5-20251001")

EVALUATOR_B_PRIMARY  = ("openai",     "gpt-5.5")
EVALUATOR_B_FALLBACK = ("openai",     "gpt-5.4")

EVALUATOR_C_PRIMARY  = ("xai",        "grok-4")
EVALUATOR_C_FALLBACK = ("xai",        "grok-3")

# ── Single-stage fallback chain (Challenge / Cascade / Severity) ───────────────
# GPT-5.5 is primary for adversarial stages (reasoning_effort=high).
# GPT-5.4 and GPT-5.2 retained as fallbacks — proven performance.
# Note: mistral omitted — ProviderRouter does not support the 'mistral' provider.
SINGLE_STAGE_CHAIN = [
    ("openai",     "gpt-5.5"),
    ("openai",     "gpt-5.4"),
    ("openai",     "gpt-5.2"),
    ("openai",     "gpt-4o"),
    ("anthropic",  "claude-sonnet-4-6"),
    ("google",     "gemini-2.5-pro"),
    ("xai",        "grok-4"),
]
