"""
Robust JSON extraction from LLM responses.
Handles nested JSON, markdown wrappers, LaTeX, and LLM artifacts.
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple


# Priority keys: any object containing these beats all others unconditionally
PRIORITY_KEYS = {
    'evaluations', 'discovered_clauses', 'challenges', 'severities',
    'cascade_results', 'extraction',
}

# Regular CAM keys for tiebreaking among non-priority objects
CAM_KEYS = [
    'final_choice', 'reasoning_similarity', 'candidate_options',
    'shared_eliminations', 'choice', 'jb', 'assumptions',
    'eliminate', 'abstain', 'weakest_link', 'confidence',
]

# Fields that identify a single provision evaluation object
_PROVISION_SHAPE = frozenset({'provision_id', 'verdict', 'reasoning'})


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


def _collect_provision_objects(candidates: list) -> Optional[Dict[str, Any]]:
    """
    If no wrapper with 'evaluations' key was found, check whether we have
    multiple individual provision evaluation objects. If so, collect them
    into a synthetic wrapper.

    This handles models that output provision objects one-by-one instead of
    batching them in an evaluations array.

    Returns a synthetic {"evaluations": [...], "discovered_clauses": []} dict
    if 2+ unique provision objects are found, else None.
    """
    provision_objects = [
        parsed for _, _, parsed in candidates
        if _PROVISION_SHAPE.issubset(parsed.keys())
    ]
    if len(provision_objects) < 2:
        return None

    # Deduplicate by provision_id, preserving first occurrence
    seen: set = set()
    unique: list = []
    for obj in provision_objects:
        pid = obj.get('provision_id')
        if pid and pid not in seen:
            seen.add(pid)
            unique.append(obj)

    if len(unique) < 2:
        return None

    return {"evaluations": unique, "discovered_clauses": []}


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
            result = json.loads(normalized)
            # Only take the fast path if it's a priority-key wrapper or not a provision object
            # (i.e., don't short-circuit with a single provision object)
            if not _PROVISION_SHAPE.issubset(result.keys()) or any(k in result for k in PRIORITY_KEYS):
                return result
            # Single provision object on fast path — fall through to full extraction
        except json.JSONDecodeError:
            try:
                fixed = _fix_latex_escapes(normalized)
                result = json.loads(fixed)
                if not _PROVISION_SHAPE.issubset(result.keys()) or any(k in result for k in PRIORITY_KEYS):
                    return result
            except json.JSONDecodeError:
                pass

    # Find ALL valid JSON objects in the text
    candidates = _extract_all_json_candidates(normalized)

    if candidates:
        def score_candidate(item):
            start_pos, json_str, parsed = item
            # Priority key presence: any priority key wins with score 1000
            priority_score = 1000 if any(k in parsed for k in PRIORITY_KEYS) else 0
            cam_key_count = sum(1 for k in CAM_KEYS if k in parsed)
            field_count = len(parsed)
            position_score = start_pos
            return (priority_score, cam_key_count, field_count, position_score)

        # Sort by score descending (best first)
        candidates.sort(key=score_candidate, reverse=True)
        best = candidates[0]

        # If best candidate has a priority key, return it directly
        if any(k in best[2] for k in PRIORITY_KEYS):
            return best[2]

        # No priority-key wrapper found — try collecting individual provision objects
        synthetic = _collect_provision_objects(candidates)
        if synthetic is not None:
            return synthetic

        # Fall back to best-scored candidate
        return best[2]

    # Try the original text too (before normalization)
    if text != normalized:
        candidates = _extract_all_json_candidates(text)
        if candidates:
            def score_candidate(item):
                start_pos, json_str, parsed = item
                priority_score = 1000 if any(k in parsed for k in PRIORITY_KEYS) else 0
                cam_key_count = sum(1 for k in CAM_KEYS if k in parsed)
                field_count = len(parsed)
                position_score = start_pos
                return (priority_score, cam_key_count, field_count, position_score)

            candidates.sort(key=score_candidate, reverse=True)
            best = candidates[0]

            if any(k in best[2] for k in PRIORITY_KEYS):
                return best[2]

            synthetic = _collect_provision_objects(candidates)
            if synthetic is not None:
                return synthetic

            return best[2]

    # If nothing worked, give error with context
    excerpt = text[-500:] if len(text) > 500 else text
    raise ValueError(f"json_parse_failed: no valid JSON found (tail: {repr(excerpt)})")