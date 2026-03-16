"""
CAM Lease Review — Central Model Configuration

Single source of truth for all model strings used in the pipeline.
To upgrade a model, change it here — all stages pick it up automatically.

Last updated: 2026-03-15 (session 2)
  - Evaluator A: claude-sonnet-4-20250514 → claude-sonnet-4-6
  - Evaluator C: grok-3 → grok-4
  - Evaluator B: gpt-5.2 → gpt-5.4 (released 2026-03-05; 33% fewer errors vs 5.2)
  - Challenge/Severity/Cascade: gpt-5.2 → gpt-5.4
  - Fallback chain: gpt-5.4 primary, gpt-5.2 fallback everywhere
  - gpt-5.4-pro explicitly excluded: $180/M output, not cost-viable for pipeline
"""

# ── Extractor (Stage 1) ────────────────────────────────────────────────────────
# Gemini is the sole extractor. Primary is the latest preview; 2.5 Pro as fallback.
EXTRACTOR_PRIMARY   = ("google",      "gemini-3.1-pro-preview")
EXTRACTOR_FALLBACK  = ("google",      "gemini-2.5-pro")

EXTRACTION_CHAIN = [
    EXTRACTOR_PRIMARY,
    EXTRACTOR_FALLBACK,
    ("openai",     "gpt-5.4"),
    ("openai",     "gpt-5.2"),
    ("anthropic",  "claude-sonnet-4-6"),
    ("mistral",    "mistral-large-latest"),   # last resort — provider diversity
]

# ── Evaluators (Stage 2) ───────────────────────────────────────────────────────
# Three independent models, one per provider. Blind to each other.
EVALUATOR_A_PRIMARY  = ("anthropic",  "claude-sonnet-4-6")
EVALUATOR_A_FALLBACK = ("anthropic",  "claude-sonnet-4-20250514")   # prev Sonnet

EVALUATOR_B_PRIMARY  = ("openai",     "gpt-5.4")
EVALUATOR_B_FALLBACK = ("openai",     "gpt-5.2")          # prev primary

EVALUATOR_C_PRIMARY  = ("xai",        "grok-4")
EVALUATOR_C_FALLBACK = ("xai",        "grok-3")                     # prev Grok

# ── Single-stage fallback chain (Challenge / Cascade / Severity) ───────────────
# GPT-5.4 is primary for adversarial stages (reasoning_effort=high).
# GPT-5.2 retained as first fallback — 30% cheaper, proven performance.
# Note: mistral omitted — ProviderRouter does not support the 'mistral' provider.
SINGLE_STAGE_CHAIN = [
    ("openai",     "gpt-5.4"),
    ("openai",     "gpt-5.2"),
    ("anthropic",  "claude-sonnet-4-6"),
    ("google",     "gemini-3.1-pro-preview"),
    ("xai",        "grok-4"),
]
