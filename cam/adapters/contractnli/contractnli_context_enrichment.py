"""
ContractNLI Legal Context Enrichment Module

Uses the Google GenAI SDK (Gemini 3.1 Pro) with Google Search grounding
to look up interpretive context for disputed legal terms/concepts
identified from evaluator disagreements.

This module runs as a sub-step within the Evidence Challenge stage (Stage 2).
It:
  a) Identifies concepts in dispute from evaluator outputs
  b) Performs legal context lookup via Gemini + Google Search grounding
  c) Produces structured context output for the challenge prompt

Called directly via google-genai SDK (not through provider_router) because
the provider_router does not support the tools parameter for search grounding.

Usage:
    enrichment = run_enrichment(evaluations, hypothesis_text, hypothesis_id)
    context_block = format_enrichment_for_challenge(enrichment)
"""

import json
import logging
import os
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# Legal Term Extraction
# ============================================================

# Common NDA / contract terms that warrant context lookup when disputed
LEGAL_TERM_PATTERNS = [
    # NDA-specific
    r"[Cc]onfidential\s+[Ii]nformation",
    r"[Rr]esidual\s+[Ii]nformation",
    r"[Pp]roprietary\s+[Ii]nformation",
    r"[Tt]rade\s+[Ss]ecret",
    r"[Rr]eceiving\s+[Pp]arty",
    r"[Dd]isclosing\s+[Pp]arty",
    r"[Rr]epresentatives?",
    r"[Aa]ffiliates?",
    # Obligation / rights terms
    r"right\s+to",
    r"upon\s+(?:the\s+)?termination",
    r"upon\s+(?:the\s+)?request",
    r"upon\s+(?:the\s+)?expiration",
    r"return\s+or\s+destroy",
    r"return\s+or\s+destruction",
    r"shall\s+not\s+(?:be\s+)?(?:used|disclosed|shared|solicited)",
    r"non-?solicitation",
    r"non-?competition",
    r"non-?disclosure",
    r"non-?circumvention",
    r"retain(?:ed|ing)?",
    r"surviv(?:e|es|al)",
    r"indemnif(?:y|ication)",
    r"injunctive\s+relief",
    r"equitable\s+relief",
    # Scope qualifiers
    r"notwithstanding",
    r"provided\s+(?:however|that)",
    r"subject\s+to",
    r"except\s+(?:as|for|to)",
    r"excluding",
    r"other\s+than",
    r"in\s+no\s+event",
]


def extract_hypothesis_terms(hypothesis_text: str) -> List[str]:
    """
    Extract key legal terms from the hypothesis text.

    Returns a list of terms/phrases that may need interpretive context.
    """
    terms = []
    for pattern in LEGAL_TERM_PATTERNS:
        matches = re.findall(pattern, hypothesis_text)
        for m in matches:
            cleaned = m.strip()
            if cleaned and cleaned not in terms:
                terms.append(cleaned)

    # Also extract any quoted phrases
    quoted = re.findall(r'"([^"]+)"', hypothesis_text)
    for q in quoted:
        if q not in terms and len(q) > 3:
            terms.append(q)

    return terms


def identify_disputed_concepts(
    evaluations: Dict[str, dict],
    hypothesis_text: str,
    hypothesis_id: str,
) -> List[Dict[str, str]]:
    """
    Identify concepts in dispute from evaluator outputs.

    Looks for:
    1. Evaluator disagreement on verdict (2-1 or 3-way split)
    2. Key legal terms in the hypothesis itself
    3. Terms mentioned in evaluator reasoning that differ between evaluators

    Returns:
        List of dicts with 'concept', 'dispute_description'
    """
    concepts = []

    # Extract verdicts
    verdicts = {}
    for label, ev in evaluations.items():
        if "error" in ev and "verdict" not in ev:
            continue
        verdicts[label] = ev.get("verdict", "UNKNOWN")

    counts = Counter(verdicts.values())
    has_disagreement = len(counts) > 1

    # 1. Extract terms from hypothesis
    hyp_terms = extract_hypothesis_terms(hypothesis_text)

    # 2. Find reasoning differences if there's disagreement
    reasoning_terms = {}
    for label, ev in evaluations.items():
        if "error" in ev and "verdict" not in ev:
            continue
        reasoning = ev.get("reasoning", "")
        assumptions = ev.get("assumptions", [])
        ev_terms = extract_hypothesis_terms(reasoning)
        for a in assumptions:
            if isinstance(a, str):
                ev_terms.extend(extract_hypothesis_terms(a))
        reasoning_terms[label] = set(ev_terms)

    # 3. Build concept list
    # Always include hypothesis-level terms
    for term in hyp_terms:
        desc = f"Key term from hypothesis '{hypothesis_id}'"
        if has_disagreement:
            # Check if this term appears in dissenting evaluator's reasoning
            majority_verdict = counts.most_common(1)[0][0] if counts else None
            dissenters = [l for l, v in verdicts.items() if v != majority_verdict]
            if dissenters:
                desc = (f"Term from hypothesis — evaluators disagree "
                        f"({', '.join(f'{l}={verdicts[l]}' for l in sorted(verdicts.keys()))})")
        concepts.append({"concept": term, "dispute_description": desc})

    # 4. If disagreement, look for terms unique to dissenting evaluator
    if has_disagreement and reasoning_terms:
        majority_verdict = counts.most_common(1)[0][0] if counts else None
        majority_labels = {l for l, v in verdicts.items() if v == majority_verdict}
        minority_labels = {l for l, v in verdicts.items() if v != majority_verdict}

        # Terms used by minority but not majority
        majority_all = set()
        for l in majority_labels:
            majority_all |= reasoning_terms.get(l, set())
        minority_all = set()
        for l in minority_labels:
            minority_all |= reasoning_terms.get(l, set())

        unique_to_minority = minority_all - majority_all
        for term in list(unique_to_minority)[:3]:  # Cap at 3 unique terms
            if term not in [c["concept"] for c in concepts]:
                concepts.append({
                    "concept": term,
                    "dispute_description": (
                        f"Term used by dissenting evaluator(s) "
                        f"{', '.join(sorted(minority_labels))} but not by majority"
                    ),
                })

    # Deduplicate and cap at 5 concepts
    seen = set()
    deduped = []
    for c in concepts:
        key = c["concept"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped[:5]


# ============================================================
# Gemini API Call with Google Search grounding
# ============================================================

def _call_gemini_with_search(query: str, max_tokens: int = 2048) -> Tuple[str, dict]:
    """
    Call Gemini 3.1 Pro via Google GenAI SDK with Google Search grounding.

    Returns:
        (response_text, usage_metadata)
    """
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")

    client = genai.Client(api_key=api_key)

    system_prompt = (
        "You are a legal reference assistant. When asked about legal terminology "
        "or contract interpretation, use web search to find authoritative legal "
        "references and provide concise, factual interpretive context. "
        "Focus on how legal professionals interpret the specific terms in the "
        "context of NDA (Non-Disclosure Agreement) contracts. "
        "Be precise about definitional boundaries — what IS and IS NOT included "
        "in a legal term's scope."
    )

    start_time = time.time()

    response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=query,
        config={
            "tools": [{"google_search": {}}],
            "system_instruction": system_prompt,
            "temperature": 0.0,
            "max_output_tokens": max_tokens,
        },
    )

    elapsed = time.time() - start_time

    # Extract text content from response
    response_text = ""
    if response.text:
        response_text = response.text
    elif response.candidates and response.candidates[0].content:
        text_parts = []
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                text_parts.append(part.text)
        response_text = "\n".join(text_parts)

    # Extract usage metadata (Google SDK exposes usage_metadata)
    input_tokens = 0
    output_tokens = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

    usage = {
        "model": "gemini-3.1-pro-preview",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "elapsed_sec": round(elapsed, 2),
    }

    return response_text, usage


def lookup_legal_context(concept: str, hypothesis_text: str) -> Dict[str, Any]:
    """
    Look up interpretive context for a single legal concept.

    Constructs a targeted query and calls Gemini with Google Search grounding.

    Returns:
        Dict with context_found, query, source_summary, usage
    """
    # Build a focused query
    query = (
        f"In the context of NDA (Non-Disclosure Agreement) contract interpretation, "
        f"what is the precise legal meaning and scope of '{concept}'? "
        f"Specifically, regarding the hypothesis: \"{hypothesis_text}\" — "
        f"what definitional boundaries should a legal analyst apply when "
        f"determining whether this concept is present in a contract clause? "
        f"Provide 1-2 paragraphs of interpretive context focusing on how "
        f"legal professionals distinguish this concept from adjacent or "
        f"related terms."
    )

    try:
        response_text, usage = _call_gemini_with_search(query)
        return {
            "context_found": response_text,
            "query": query,
            "source_summary": f"Legal reference lookup for '{concept}' in NDA context",
            "usage": usage,
            "error": None,
        }
    except Exception as e:
        logger.warning(f"Enrichment lookup failed for '{concept}': {e}")
        return {
            "context_found": None,
            "query": query,
            "source_summary": None,
            "usage": None,
            "error": str(e),
        }


# ============================================================
# Main Enrichment Entry Point
# ============================================================

def run_enrichment(
    evaluations: Dict[str, dict],
    hypothesis_text: str,
    hypothesis_id: str,
) -> Dict[str, Any]:
    """
    Run the full enrichment pipeline for a single (contract, hypothesis) pair.

    1. Identify disputed concepts
    2. Look up legal context for each
    3. Return structured enrichment output

    Args:
        evaluations: dict of evaluator label -> normalized response (Stage 1)
        hypothesis_text: the hypothesis being evaluated
        hypothesis_id: identifier for the hypothesis (e.g., "nda-15")

    Returns:
        Structured enrichment dict matching enrichment_schema.json
    """
    logger.info(f"  Enrichment: identifying disputed concepts for {hypothesis_id}...")

    # Step 1: Identify concepts
    concepts = identify_disputed_concepts(evaluations, hypothesis_text, hypothesis_id)

    if not concepts:
        return {
            "enrichment_performed": False,
            "concepts_searched": [],
            "enrichment_summary": "No disputed concepts identified",
            "total_usage": {"input_tokens": 0, "output_tokens": 0, "calls": 0},
        }

    logger.info(f"  Enrichment: found {len(concepts)} concepts to search")

    # Step 2: Look up context for each concept
    searched = []
    total_input = 0
    total_output = 0

    for concept_info in concepts:
        concept = concept_info["concept"]
        logger.info(f"    Looking up: '{concept}'...")

        result = lookup_legal_context(concept, hypothesis_text)

        entry = {
            "concept": concept,
            "query": result["query"],
            "context_found": result["context_found"],
            "source_summary": result["source_summary"],
            "relevance_to_disagreement": concept_info["dispute_description"],
            "error": result["error"],
        }
        searched.append(entry)

        if result["usage"]:
            total_input += result["usage"].get("input_tokens", 0)
            total_output += result["usage"].get("output_tokens", 0)

    # Step 3: Build output
    successful = [s for s in searched if s["context_found"]]
    enrichment = {
        "enrichment_performed": True,
        "concepts_searched": searched,
        "enrichment_summary": (
            f"Found interpretive context for {len(successful)}/{len(searched)} "
            f"disputed concepts"
        ),
        "total_usage": {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "calls": len(searched),
        },
    }

    return enrichment


# ============================================================
# Format Enrichment for Challenge Prompt
# ============================================================

def format_enrichment_for_challenge(enrichment: Dict[str, Any]) -> str:
    """
    Format the enrichment output as a text block for inclusion in the
    evidence challenge prompt.

    Returns:
        Formatted string to inject into the challenge prompt, or empty
        string if no enrichment was performed.
    """
    if not enrichment.get("enrichment_performed"):
        return ""

    concepts = enrichment.get("concepts_searched", [])
    successful = [c for c in concepts if c.get("context_found")]

    if not successful:
        return ""

    lines = [
        "",
        "LEGAL CONTEXT (from external reference):",
        "The following interpretive context was retrieved for key terms in dispute:",
        "",
    ]

    for c in successful:
        concept = c["concept"]
        context = c["context_found"]
        # Truncate very long context
        if len(context) > 1500:
            context = context[:1500] + "..."
        lines.append(f"  [{concept}]: {context}")
        lines.append("")

    lines.append(
        "Use this context to evaluate whether the evaluators' interpretations are "
        "consistent with standard legal usage. If an evaluator's interpretation "
        "conflicts with standard usage, flag this as a HIGH severity challenge."
    )
    lines.append("")

    return "\n".join(lines)
