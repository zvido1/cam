"""
CAM Lease Review — Knowledge Schema Loader (Step 240)

Loads retail_lease_knowledge.json and exposes clean lookup helpers
for the coverage state assessor, negative space detector, and exposure engine.

Usage:
    from cam.adapters.lease_review.lease_knowledge import get_schema, get_issue_area, validate_schema

All functions return plain dicts/lists — no custom objects, no surprises.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "retail_lease_knowledge.json"
_schema_cache: Optional[dict] = None


# ── Loading ────────────────────────────────────────────────────────────────────

def get_schema(path: Optional[Path] = None) -> dict:
    """Load and cache the retail lease knowledge schema.

    Returns the full schema dict. Cached after first load.
    Pass a custom path to load a different schema file (useful for testing).
    """
    global _schema_cache
    if _schema_cache is not None and path is None:
        return _schema_cache

    target = path or _SCHEMA_PATH
    try:
        raw = target.read_text(encoding="utf-8")
        schema = json.loads(raw)
        if path is None:
            _schema_cache = schema
        logger.info(
            f"[lease_knowledge] Loaded schema v{schema.get('schema_version', '?')} "
            f"({len(schema.get('issue_areas', []))} issue areas)"
        )
        return schema
    except FileNotFoundError:
        logger.error(f"[lease_knowledge] Schema file not found: {target}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"[lease_knowledge] Schema JSON parse error: {e}")
        raise


def reload_schema() -> dict:
    """Force reload from disk (clears cache). Useful after schema edits."""
    global _schema_cache
    _schema_cache = None
    return get_schema()


# ── Issue Area Lookups ─────────────────────────────────────────────────────────

def get_issue_area(provision_id: str) -> Optional[dict]:
    """Return the issue area dict for a given LP-XX id, or None if not found."""
    schema = get_schema()
    for area in schema.get("issue_areas", []):
        if area.get("id") == provision_id:
            return area
    return None


def get_all_issue_areas() -> list:
    """Return all issue area dicts."""
    return get_schema().get("issue_areas", [])


def get_required_issue_areas() -> list:
    """Return issue areas with applicability == 'required'."""
    return [a for a in get_all_issue_areas() if a.get("applicability") == "required"]


def get_conditional_issue_areas() -> list:
    """Return issue areas with applicability == 'conditional'."""
    return [a for a in get_all_issue_areas() if a.get("applicability") == "conditional"]


def get_optional_issue_areas() -> list:
    """Return issue areas with applicability == 'optional'."""
    return [a for a in get_all_issue_areas() if a.get("applicability") == "optional"]


# ── Applicability Helpers ──────────────────────────────────────────────────────

def get_activation_clues(provision_id: str) -> list:
    """Return activation clue strings for a conditional/optional issue area."""
    area = get_issue_area(provision_id)
    if not area:
        return []
    return area.get("activation_clues", [])


def get_exclusion_clues(provision_id: str) -> list:
    """Return exclusion clue strings for an issue area."""
    area = get_issue_area(provision_id)
    if not area:
        return []
    return area.get("exclusion_clues", [])


def get_default_when_unclear(provision_id: str) -> str:
    """Return the coverage state to assign when applicability cannot be determined."""
    area = get_issue_area(provision_id)
    if not area:
        return "review_needed"
    return area.get("default_when_unclear", "review_needed")


def is_applicable(provision_id: str, document_text: str) -> str:
    """Determine applicability of an issue area given document text.

    Returns one of:
        'required'    — always applicable, no text check needed
        'applicable'  — conditional issue area with activation clue found
        'excluded'    — exclusion clue found; issue area does not apply
        'not_applicable' — conditional/optional with no activation clues found
        'unclear'     — cannot determine (use default_when_unclear)

    Args:
        provision_id: LP-XX id string
        document_text: full lowercase document text to search (caller should lower())
    """
    area = get_issue_area(provision_id)
    if not area:
        return "unclear"

    applicability = area.get("applicability", "required")

    if applicability == "required":
        return "required"

    text_lower = document_text.lower() if document_text else ""

    # Check exclusion clues first — if present, issue area does not apply
    for clue in area.get("exclusion_clues", []):
        if clue.lower() in text_lower:
            logger.debug(f"[lease_knowledge] {provision_id}: excluded by clue '{clue}'")
            return "excluded"

    # Check activation clues
    for clue in area.get("activation_clues", []):
        if clue.lower() in text_lower:
            logger.debug(f"[lease_knowledge] {provision_id}: activated by clue '{clue}'")
            return "applicable"

    # No activation found
    if applicability == "optional":
        return "not_applicable"

    # Conditional with no activation clues found — unclear
    return "unclear"


# ── Coverage State Helpers ─────────────────────────────────────────────────────

def get_coverage_state_rules(provision_id: str) -> dict:
    """Return the coverage_state_rules dict for an issue area."""
    area = get_issue_area(provision_id)
    if not area:
        return {}
    return area.get("coverage_state_rules", {})


def get_valid_coverage_states() -> dict:
    """Return the full coverage_states definitions dict."""
    return get_schema().get("coverage_states", {})


def get_exposure_statement(provision_id: str) -> str:
    """Return the fallback exposure statement for an issue area."""
    area = get_issue_area(provision_id)
    if not area:
        return ""
    return area.get("exposure_statement", "")


def get_risk_if_missing(provision_id: str) -> str:
    """Return the risk_if_missing string for an issue area."""
    area = get_issue_area(provision_id)
    if not area:
        return ""
    return area.get("risk_if_missing", "")


def get_caution_signals(provision_id: str) -> list:
    """Return caution signal keys for an issue area."""
    area = get_issue_area(provision_id)
    if not area:
        return []
    return area.get("caution_signals", [])


def get_caution_signal_definition(signal_key: str) -> str:
    """Return the human-readable definition for a caution signal key."""
    schema = get_schema()
    return schema.get("caution_signal_definitions", {}).get(signal_key, signal_key)


def get_related_issue_areas(provision_id: str) -> list:
    """Return IDs of related issue areas (for cascade risk tracking)."""
    area = get_issue_area(provision_id)
    if not area:
        return []
    return area.get("related_issue_areas", [])


# ── Negative Space Helpers ─────────────────────────────────────────────────────

def get_negative_space_clues(provision_id: str) -> list:
    """Return negative space clue strings for an issue area."""
    area = get_issue_area(provision_id)
    if not area:
        return []
    return area.get("negative_space_clues", [])


def get_expected_elements(provision_id: str) -> list:
    """Return the list of expected sub-elements for an issue area."""
    area = get_issue_area(provision_id)
    if not area:
        return []
    return area.get("expected_elements", [])


# ── Discovered Provision Patterns ─────────────────────────────────────────────

def get_discovered_provision_patterns() -> list:
    """Return known non-standard provision patterns for CUSTOM-XX framing."""
    schema = get_schema()
    return schema.get("discovered_provision_patterns", {}).get("patterns", [])


def get_discovered_pattern(name: str) -> Optional[dict]:
    """Look up a discovered provision pattern by name (case-insensitive)."""
    name_lower = name.lower().strip()
    for pattern in get_discovered_provision_patterns():
        if pattern.get("name", "").lower().strip() == name_lower:
            return pattern
    return None


# ── Schema Validation ──────────────────────────────────────────────────────────

def validate_schema(schema: Optional[dict] = None) -> list:
    """Validate the schema and return a list of error strings.

    Returns an empty list if the schema is valid.
    Checks the rules defined in schema.schema_validation_rules.checks.

    Args:
        schema: schema dict to validate. If None, loads from disk.
    """
    if schema is None:
        schema = get_schema()

    errors = []
    valid_states = set(schema.get("coverage_states", {}).keys())
    valid_signals = set(schema.get("caution_signal_definitions", {}).keys())
    seen_ids = set()

    for area in schema.get("issue_areas", []):
        pid = area.get("id", "<missing id>")

        # Duplicate ID check
        if pid in seen_ids:
            errors.append(f"{pid}: duplicate issue area id")
        seen_ids.add(pid)

        # Required fields
        if "applicability" not in area:
            errors.append(f"{pid}: missing 'applicability' field")

        if "default_when_unclear" not in area:
            errors.append(f"{pid}: missing 'default_when_unclear' field")

        if not area.get("expected_elements"):
            errors.append(f"{pid}: 'expected_elements' is empty or missing")

        if not area.get("exposure_statement"):
            errors.append(f"{pid}: 'exposure_statement' is empty or missing")

        if not area.get("risk_if_missing"):
            errors.append(f"{pid}: 'risk_if_missing' is empty or missing")

        # Conditional must have activation clues
        if area.get("applicability") == "conditional" and not area.get("activation_clues"):
            errors.append(f"{pid}: applicability is 'conditional' but no activation_clues defined")

        # Coverage state rules must reference valid states
        for state_key in area.get("coverage_state_rules", {}).keys():
            if state_key not in valid_states:
                errors.append(f"{pid}: coverage_state_rules references unknown state '{state_key}'")

        # Caution signals must reference valid keys
        for signal in area.get("caution_signals", []):
            if signal not in valid_signals:
                errors.append(f"{pid}: caution_signals references unknown signal '{signal}'")

        # default_when_unclear must be a valid state
        default = area.get("default_when_unclear", "")
        if default and default not in valid_states:
            errors.append(f"{pid}: default_when_unclear '{default}' is not a valid coverage state")

    # Discovered provision patterns
    for pattern in schema.get("discovered_provision_patterns", {}).get("patterns", []):
        pname = pattern.get("name", "<missing>")
        if "applicability" not in pattern:
            errors.append(f"discovered_pattern '{pname}': missing 'applicability' field")
        if "activation_clues" not in pattern:
            errors.append(f"discovered_pattern '{pname}': missing 'activation_clues' field")

    return errors


def assert_schema_valid() -> None:
    """Load and validate schema. Raises ValueError if any errors found."""
    schema = get_schema()
    errors = validate_schema(schema)
    if errors:
        msg = f"Schema validation failed ({len(errors)} error(s)):\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(msg)
    logger.info("[lease_knowledge] Schema validation passed")


# ── CLI / Quick Check ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading schema...")
    schema = get_schema()
    print(f"Schema version: {schema.get('schema_version')}")
    print(f"Issue areas: {len(schema.get('issue_areas', []))}")
    print()

    print("Running validation...")
    errors = validate_schema(schema)
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    else:
        print("Validation PASSED — schema is clean.")
    print()

    print("Sample lookups:")
    lp01 = get_issue_area("LP-01")
    print(f"  LP-01 applicability: {lp01.get('applicability')}")
    print(f"  LP-01 expected elements: {len(get_expected_elements('LP-01'))}")
    print(f"  LP-04 default_when_unclear: {get_default_when_unclear('LP-04')}")
    print(f"  LP-07 activation clues: {get_activation_clues('LP-07')}")
    print(f"  LP-12 default_when_unclear: {get_default_when_unclear('LP-12')}")
    print()

    print("Applicability test (LP-07 CAM):")
    test_text_nnn = "tenant shall pay proportionate share of cam charges and operating expenses"
    test_text_gross = "this is a full service gross lease and landlord pays all operating expenses"
    print(f"  NNN lease text: {is_applicable('LP-07', test_text_nnn)}")
    print(f"  Gross lease text: {is_applicable('LP-07', test_text_gross)}")
    print(f"  LP-01 (required): {is_applicable('LP-01', test_text_nnn)}")
