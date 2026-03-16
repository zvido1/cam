"""
Robust JSON extraction from LLM responses.
Handles nested JSON, markdown wrappers, LaTeX, and LLM artifacts.
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple


def _fix_latex_escapes(json_str: str) -> str:
    r"""
    Fix invalid JSON escape sequences commonly found in LaTeX.
    
    LLMs often output LaTeX like $\gamma$ inside JSON strings, but JSON
    only allows specific escape sequences: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX.
    
    This function finds backslashes followed by invalid escape chars and
    doubles them to make valid JSON.
    """
    # Valid JSON escape characters (after backslash)
    # These are: " \ / b f n r t u
    valid_escapes = set('"' + '\\' + '/' + 'bfnrtu')
    
    result = []
    i = 0
    in_string = False
    
    while i < len(json_str):
        c = json_str[i]
        
        # Track whether we're inside a JSON string
        if c == '"' and (i == 0 or json_str[i-1] != '\\'):
            in_string = not in_string
            result.append(c)
            i += 1
            continue
        
        # Only process backslashes inside strings
        if c == '\\' and in_string and i + 1 < len(json_str):
            next_char = json_str[i + 1]
            
            # Check if this is already a valid escape or needs fixing
            if next_char in valid_escapes:
                # Valid escape - keep as is
                result.append(c)
                result.append(next_char)
                i += 2
            elif next_char == '\\':
                # Already escaped backslash
                result.append(c)
                result.append(next_char)
                i += 2
            else:
                # Invalid escape (like \g, \a from LaTeX) - escape the backslash
                result.append('\\')  # Add extra backslash
                result.append(c)
                i += 1
        else:
            result.append(c)
            i += 1
    
    return ''.join(result)


def _find_balanced_json(text: str, start_pos: int) -> Optional[str]:
    """
    Find a balanced JSON object starting at start_pos using brace counting.
    Handles nested objects, arrays, and strings with escaped characters.
    """
    if start_pos >= len(text) or text[start_pos] != '{':
        return None
    
    depth = 0
    in_string = False
    escape_next = False
    
    for i in range(start_pos, len(text)):
        c = text[i]
        
        if escape_next:
            escape_next = False
            continue
        
        if c == '\\':
            escape_next = True
            continue
        
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start_pos:i+1]
    
    return None


def _normalize_json_text(text: str) -> str:
    """Remove LLM artifacts (thinking tags, markdown wrappers)."""
    # Remove XML-style thinking/reasoning tags
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<analysis>.*?</analysis>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove markdown code block wrappers
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    
    return text.strip()


def _extract_all_json_candidates(text: str) -> List[Tuple[int, str, Dict]]:
    """
    Find all valid JSON objects in text.
    Returns list of (start_pos, json_string, parsed_dict) tuples.
    
    Note: This function attempts to fix invalid LaTeX escape sequences
    that LLMs commonly produce inside JSON strings.
    """
    candidates = []
    brace_positions = [i for i, c in enumerate(text) if c == '{']
    
    for start_pos in brace_positions:
        json_str = _find_balanced_json(text, start_pos)
        if json_str:
            # First try parsing as-is
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    candidates.append((start_pos, json_str, parsed))
                continue
            except json.JSONDecodeError:
                pass
            
            # Try fixing LaTeX escapes (common in LLM outputs)
            try:
                fixed_json = _fix_latex_escapes(json_str)
                parsed = json.loads(fixed_json)
                if isinstance(parsed, dict):
                    candidates.append((start_pos, fixed_json, parsed))
            except json.JSONDecodeError:
                continue
    
    return candidates


def safe_json_extract(text: str) -> Dict[str, Any]:
    r"""
    Extract JSON object from a string that might contain extra text.
    Uses balanced brace counting to handle nested JSON structures.
    Prioritizes the LARGEST valid JSON object with expected CAM keys.
    
    Handles invalid LaTeX escape sequences (e.g., \gamma, \beta) that LLMs
    commonly produce inside JSON strings.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("empty_output")
    
    # Normalize first to remove LLM artifacts
    normalized = _normalize_json_text(text)

    # Fast path: entire text is valid JSON
    if normalized.startswith("{") and normalized.endswith("}"):
        try:
            return json.loads(normalized)
        except json.JSONDecodeError:
            # Try fixing LaTeX escapes
            try:
                fixed = _fix_latex_escapes(normalized)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    # Known CAM schema keys to prioritize
    cam_keys = [
        'final_choice', 'reasoning_similarity', 'candidate_options',
        'shared_eliminations', 'choice', 'jb', 'assumptions',
        'eliminate', 'abstain', 'weakest_link', 'confidence'
    ]
    
    # Find ALL valid JSON objects in the text
    candidates = _extract_all_json_candidates(normalized)
    
    if candidates:
        # Score each candidate: prefer larger objects with more CAM keys
        def score_candidate(item):
            start_pos, json_str, parsed = item
            # Count CAM keys present
            cam_key_count = sum(1 for k in cam_keys if k in parsed)
            # Size of the JSON (more fields = likely the main response)
            field_count = len(parsed)
            # Prefer objects later in the text (JSON response usually at end)
            position_score = start_pos
            # Combined score: CAM keys most important, then size, then position
            return (cam_key_count, field_count, position_score)
        
        # Sort by score descending (best first)
        candidates.sort(key=score_candidate, reverse=True)
        
        # Return the best candidate
        best = candidates[0]
        return best[2]  # Return parsed dict
    
    # Try the original text too (before normalization)
    if text != normalized:
        candidates = _extract_all_json_candidates(text)
        if candidates:
            def score_candidate(item):
                start_pos, json_str, parsed = item
                cam_key_count = sum(1 for k in cam_keys if k in parsed)
                field_count = len(parsed)
                position_score = start_pos
                return (cam_key_count, field_count, position_score)
            
            candidates.sort(key=score_candidate, reverse=True)
            return candidates[0][2]
    
    # If nothing worked, give error with context
    excerpt = text[-500:] if len(text) > 500 else text
    raise ValueError(f"json_parse_failed: no valid JSON found (tail: {repr(excerpt)})")