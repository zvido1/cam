"""
CAM Lease Review — Coverage State Assessor (Step 242)

Assigns a coverage state to each issue area in a reviewed lease.
Operates at the ISSUE AREA level, not the provision level.

Assessment logic:
    1. Determine applicability (required / applicable / excluded / not_applicable / unclear)
    2. If not applicable → coverage_state = not_applicable
    3. If unclear → coverage_state = default_when_unclear (per schema)
    4. If applicable → examine extracted provision text for expected elements
    5. Apply coverage_state_rules from schema to assign final state
    6. Incorporate negative space signals as supporting evidence

Zero API calls. Pure logic against extracted text + schema + negative space signals.

Usage:
    from cam.adapters.lease_review.lease_coverage import assess_coverage

    coverage = assess_coverage(provisions, full_tenant_text, negative_space_signals)
    # Returns list of issue_area_assessment dicts
"""

import re
import logging
from typing import Optional

from cam.adapters.lease_review.lease_verdict_distance import NOT_ASSESSED_SENTINEL

logger = logging.getLogger(__name__)


# ── Main entry point ───────────────────────────────────────────────────────────

def assess_coverage(
    provisions: list,
    full_tenant_text: str,
    negative_space_signals: Optional[dict] = None,
    lp_progress_callback=None,
) -> list:
    """Assess coverage state for all issue areas.

    Args:
        provisions: list of provision dicts from extraction + negative space stage
        full_tenant_text: full raw tenant document text
        negative_space_signals: dict from detect_negative_space(), keyed by provision_id
                                 If None, skips negative space integration.

    Returns:
        List of issue_area_assessment dicts, one per LP-XX in the schema.
        Provisions not in the schema (CUSTOM-XX) are skipped here — they get
        separate handling in the exposure engine as tenant-added articles.
    """
    from cam.adapters.lease_review.lease_knowledge import (
        get_all_issue_areas,
        is_applicable,
        get_default_when_unclear,
        get_coverage_state_rules,
        get_expected_elements,
        get_caution_signals,
        get_exposure_statement,
        get_risk_if_missing,
        get_related_issue_areas,
    )

    ns_signals = negative_space_signals or {}

    # Step 305: routing config.
    # STEP_305_ENABLED is the global kill switch. Per-LP gate removed in Step 305
    # full-schema expansion (schema v2.1.0): all LPs with expected_elements_305
    # route through 305 when STEP_305_ENABLED is True.
    from cam.adapters.lease_review.lease_coverage_305 import STEP_305_ENABLED

    # Build a lookup map from the extracted provisions
    provision_map = {}
    for p in provisions:
        pid = p.get("provision_id", "")
        if pid:
            provision_map[pid] = p

    # Step 307b: build LP-text map for cross-LP text injection into 305 prompts.
    # Maps LP ID → extracted tenant_text so evaluators can assess cross-LP elements.
    all_lp_texts: dict = {
        p.get("provision_id"): p.get("tenant_text", "")
        for p in provisions
        if p.get("provision_id") and p.get("tenant_text")
    }

    assessments = []

    def _emit(assessment):
        if lp_progress_callback:
            try:
                lp_progress_callback(
                    lp_id=assessment["issue_area_id"],
                    lp_name=assessment["issue_area_name"],
                    state=assessment.get("coverage_state", "unknown"),
                )
            except Exception:
                pass

    for area in get_all_issue_areas():
        pid = area.get("id", "")
        lp_name = area.get("name", pid)

        # Signal LP as currently being assessed before any work runs
        if lp_progress_callback:
            try:
                lp_progress_callback(lp_id=pid, lp_name=lp_name, state="processing")
            except Exception:
                pass

        # ── Step 1: Applicability ─────────────────────────────────────────────
        applicability_result = is_applicable(pid, full_tenant_text)

        if applicability_result in ("excluded", "not_applicable"):
            reason = (
                "Exclusion clue found in document; issue area does not apply to this lease"
                if applicability_result == "excluded"
                else "No activation clues found; issue area absent by design"
            )
            _a = _build_assessment(
                pid=pid, area=area, coverage_state="not_applicable",
                applicability=applicability_result, evidence_summary=reason,
                supporting_provisions=[], negative_space=[],
                elements_found=[], elements_missing=[], tenant_text="",
            )
            assessments.append(_a)
            _emit(_a)
            continue

        if applicability_result == "unclear":
            default_state = get_default_when_unclear(pid)
            _a = _build_assessment(
                pid=pid, area=area, coverage_state=default_state,
                applicability=applicability_result,
                evidence_summary=f"Cannot determine whether this issue area applies; defaulting to '{default_state}'",
                supporting_provisions=[], negative_space=ns_signals.get(pid, []),
                elements_found=[], elements_missing=[], tenant_text="",
            )
            assessments.append(_a)
            _emit(_a)
            continue

        # applicability_result is "required" or "applicable"

        # ── Step 2: Find the extracted provision ──────────────────────────────
        prov = provision_map.get(pid)
        tenant_text = (prov.get("tenant_text", "") or "") if prov else ""
        ns = ns_signals.get(pid, [])

        # ── Step 2b: Misrouted-extraction guard (Step 298b) ───────────────────
        # For LPs in _GLOBAL_SCAN_LPS, verify the routed text is actually about
        # this LP by checking for at least one anchor keyword. If none are found,
        # the extractor likely routed irrelevant content here (e.g. Gemini sending
        # renewal-option text to LP-29). Reset tenant_text to empty so Step 4's
        # global-scan path handles it instead of element-matching noisy text.
        if pid in _GLOBAL_SCAN_LPS and tenant_text.strip():
            anchor_kws = _LP_GLOBAL_SCAN_KEYWORDS.get(pid, [])
            if anchor_kws:
                text_lower_check = tenant_text.lower()
                if not any(kw in text_lower_check for kw in anchor_kws):
                    logger.info(
                        f"[lease_coverage] {pid}: tenant_text contains no anchor "
                        f"keywords for this LP; treating as misrouted, will attempt global scan"
                    )
                    tenant_text = ""

        # ── Step 3: High-priority negative space: reserved/omitted ───────────
        reserved_signals = [s for s in ns if s["signal_type"] == "reserved_or_omitted"]
        if reserved_signals:
            _a = _build_assessment(
                pid=pid, area=area, coverage_state="broken_xref",
                applicability=applicability_result,
                evidence_summary="Section or subsection explicitly marked as omitted or reserved",
                supporting_provisions=[pid] if prov else [], negative_space=ns,
                elements_found=[], elements_missing=get_expected_elements(pid),
                tenant_text=tenant_text,
            )
            assessments.append(_a)
            _emit(_a)
            continue

        # ── Step 4: No tenant text → try global scan, then missing/broken_xref ───
        if not tenant_text.strip():
            # Step 298a: For LPs in _GLOBAL_SCAN_LPS, scan full document before
            # declaring missing. Handles entry rights embedded in maintenance
            # articles (LP-29). Uses min_kw_len=9 to suppress false positives
            # from common words like "tenant" and "landlord" in the excerpt.
            global_excerpt = _global_scan_for_lp(
                pid, full_tenant_text, get_expected_elements(pid)
            ) if full_tenant_text else ""

            if global_excerpt:
                tenant_text = global_excerpt
                # Fall through to element assessment with min_kw_len=9
                elements_found, elements_missing = _assess_elements(
                    pid, tenant_text, get_expected_elements(pid),
                    full_text=full_tenant_text, min_kw_len=9,
                )
            else:
                xref_signals = [s for s in ns if s["signal_type"] in ("broken_xref", "missing_exhibit")]
                state = "broken_xref" if xref_signals else "missing"
                evidence = (
                    "Provision not extracted; cross-reference or exhibit signals suggest incomplete clause"
                    if xref_signals else
                    "No provision text found in extracted document"
                )
                _a = _build_assessment(
                    pid=pid, area=area, coverage_state=state,
                    applicability=applicability_result, evidence_summary=evidence,
                    supporting_provisions=[], negative_space=ns,
                    elements_found=[], elements_missing=get_expected_elements(pid),
                    tenant_text="",
                )
                assessments.append(_a)
                _emit(_a)
                continue

            # Coverage state determination continues below for global-scan path
            coverage_state, evidence_summary = _determine_coverage_state(
                pid=pid, tenant_text=tenant_text,
                elements_found=elements_found, elements_missing=elements_missing,
                ns_signals=ns, coverage_state_rules=get_coverage_state_rules(pid), area=area,
            )
            _a = _build_assessment(
                pid=pid, area=area, coverage_state=coverage_state,
                applicability=applicability_result, evidence_summary=evidence_summary,
                supporting_provisions=[pid], negative_space=ns,
                elements_found=elements_found, elements_missing=elements_missing,
                tenant_text=tenant_text,
            )
            assessments.append(_a)
            _emit(_a)
            continue

        # ── Step 5: Provision text exists — assess elements ───────────────────

        # Step 305 routing: LPs with expected_elements_305 use per-element
        # multi-evaluator assessment. Gate is schema-driven (no per-LP list).
        if STEP_305_ENABLED and area.get("expected_elements_305"):
            try:
                from cam.adapters.lease_review.lease_coverage_305 import assess_coverage_305
                _ns_candidates = ns_signals.get(pid, [])
                _result_305 = assess_coverage_305(
                    pid=pid,
                    area=area,
                    tenant_text=tenant_text,
                    elements_305=area["expected_elements_305"],
                    negative_space_candidates=_ns_candidates,
                    all_lp_texts=all_lp_texts,
                )
                # Step 305 per-element verdicts are the authoritative source for
                # covered/partial/missing state — do NOT override with legacy regex
                # unfavorable patterns (those fire on clause text that the element-
                # level analysis already assessed more accurately).
                # Only apply potentially_unenforceable override: self-help without
                # judicial process is a jurisdiction-specific enforceability question
                # that the element verdicts do not address.
                _state_305 = _result_305["coverage_state_baseline"]
                _text_lower_305 = tenant_text.lower()
                _unenforceable_305 = _check_unenforceable_patterns(pid, _text_lower_305)
                if _unenforceable_305:
                    _state_305 = "potentially_unenforceable"
                _a = _build_assessment(
                    pid=pid, area=area, coverage_state=_state_305,
                    applicability=applicability_result,
                    evidence_summary=_result_305.get("evidence_summary", "Step 305 per-element assessment"),
                    supporting_provisions=[pid] if prov else [],
                    negative_space=ns,
                    elements_found=_result_305.get("elements_present", []),
                    elements_missing=_result_305.get("elements_missing", []),
                    tenant_text=tenant_text,
                )
                _a["coverage_method"] = _result_305.get("coverage_method", "step_305_per_element")
                _a["element_verdicts"] = _result_305.get("element_verdicts", [])
                _a["coverage_state_baseline"] = _result_305["coverage_state_baseline"]
                _a["_coverage_api_calls"] = _result_305.get("api_calls", 0)  # Step 335
                # Step 351: Architecture A Phase 2 — verdict distance at LP layer
                _a["verdict_distance"] = _result_305.get("verdict_distance")
                _a["lp_confidence_base"] = _result_305.get("lp_confidence_base", "low")
                _a["per_evaluator_lp_verdicts"] = _result_305.get("per_evaluator_lp_verdicts", {})
                assessments.append(_a)
                _emit(_a)
                continue
            except Exception as _e_305:
                logger.warning(
                    f"[lease_coverage] Step 305 assessment failed for {pid}: {_e_305}; "
                    f"falling through to legacy path"
                )
                # Fall through to existing element assessment below

        elements_found, elements_missing = _assess_elements(
            pid, tenant_text, get_expected_elements(pid), full_text=full_tenant_text
        )

        # ── Step 6: Determine coverage state ─────────────────────────────────
        coverage_state, evidence_summary = _determine_coverage_state(
            pid=pid, tenant_text=tenant_text,
            elements_found=elements_found, elements_missing=elements_missing,
            ns_signals=ns, coverage_state_rules=get_coverage_state_rules(pid), area=area,
        )

        _a = _build_assessment(
            pid=pid, area=area, coverage_state=coverage_state,
            applicability=applicability_result, evidence_summary=evidence_summary,
            supporting_provisions=[pid] if prov else [], negative_space=ns,
            elements_found=elements_found, elements_missing=elements_missing,
            tenant_text=tenant_text,
        )
        assessments.append(_a)
        _emit(_a)

    logger.info(f"[lease_coverage] Coverage assessment complete: {len(assessments)} issue areas assessed")
    _log_coverage_summary(assessments)
    return assessments


# ── Element assessment ─────────────────────────────────────────────────────────

_ELEMENT_KEYWORDS = {
    "base rent amount or formula":              ["base rent", "monthly rent", "annual rent", "rent shall be"],
    "payment due date":                         ["due on the", "payable on", "first day", "due date"],
    "late payment fee or penalty mechanism":    ["late charge", "late fee", "late payment", "penalty"],
    "grace period for late payment":            ["grace period", "days after", "days written notice"],
    "accepted payment methods":                 ["wire transfer", "check", "ach", "electronic funds"],
    "additional rent definition":               ["additional rent", "all other sums", "deemed additional"],
    "annual increase mechanism":                ["annual increase", "escalation", "cpi", "fixed percentage", "percent per year"],
    "escalation cap or ceiling":                ["cap", "not to exceed", "maximum increase", "ceiling"],
    "effective date of first escalation":       ["first anniversary", "second lease year", "effective date"],
    "calculation methodology":                  ["calculated", "based on", "multiplied by", "formula"],
    "initial term duration":                    ["term of", "initial term", "lease term", "years commencing"],
    "commencement date or conditions":          ["commencement date", "commence on", "delivery date"],
    "expiration date":                          ["expiration date", "expire on", "term shall end"],
    "renewal option count and duration":        ["option to renew", "renewal option", "renew for"],
    "renewal notice period and deadline":       ["written notice", "prior to expiration", "notice of renewal"],
    "rent at renewal":                          ["fair market", "prevailing market", "renewal rent", "rent at renewal"],
    "deposit amount":                           ["security deposit", "deposit of $", "deposit in the amount"],
    "return deadline after lease expiration":   ["return", "within", "days after expiration", "days of expiration"],
    "permitted deduction conditions":           ["deduct", "apply toward", "offset", "damage"],
    "interest obligation":                      ["interest", "bear interest", "interest on deposit"],
    "letter of credit alternative":             ["letter of credit", "loc", "l/c"],
    "specific permitted use description":       ["permitted use", "shall use", "used solely", "use the premises"],
    "exclusive use right scope":                ["exclusive", "exclusivity", "exclusive right"],
    "continuous operation obligation":          ["continuously", "continuous operation", "remain open", "shall operate"],
    "prohibited use restrictions":              ["shall not use", "prohibited", "restriction on use"],
    "co-tenancy or anchor dependency":          ["co-tenancy", "anchor", "occupancy threshold"],
    "tenant maintenance obligations":           ["tenant shall maintain", "tenant's obligation", "tenant shall repair"],
    "landlord maintenance obligations":         ["landlord shall maintain", "landlord shall repair", "structural"],
    "hvac responsibility allocation":           ["hvac", "heating", "cooling", "ventilation", "air conditioning"],
    "repair response time obligations":         ["within", "days after notice", "emergency repair"],
    "damage and destruction repair process":    ["casualty", "damage", "destruction", "restore"],
    "tenant's proportionate share":             ["proportionate share", "pro rata", "tenant's share"],
    "included expense categories":              ["including", "shall include", "include,", "common area maintenance", "operating expenses include"],
    "excluded expense categories":              ["excluding", "shall not include", "excluded from"],
    "annual cam increase cap":                  ["cap", "not exceed", "maximum", "increase shall not"],
    "tenant audit rights":                      ["audit", "examine", "inspect", "review books"],
    "reconciliation timeline":                  ["reconciliation", "reconcile", "annual statement", "within"],
    "commercial general liability minimum":     ["commercial general liability", "cgl", "per occurrence", "aggregate"],
    "property insurance obligation":            ["property insurance", "all risk", "special form"],
    "business interruption coverage":           ["business interruption", "business income", "loss of income"],
    "landlord as additional insured":           ["additional insured", "named insured", "landlord as"],
    "certificate of insurance":                 ["certificate of insurance", "certificates of insurance", "acord", "evidence of insurance"],
    "waiver of subrogation":                    ["waiver of subrogation", "subrogation", "waive any right"],
    "landlord consent requirement":             ["landlord's consent", "landlord consent", "prior written consent"],
    "grounds for withholding consent":          ["unreasonably withheld", "reasonable grounds", "withheld conditioned"],
    "affiliate exception":                      ["affiliate", "parent", "subsidiary", "related entity", "without consent"],
    "profit sharing on sublet":                 ["profit", "excess rent", "above base rent", "sharing"],
    "recapture right":                          ["recapture", "terminate", "landlord may terminate"],
    "assignment in connection with sale":       ["sale of business", "sale of substantially all", "merger", "acquisition"],
    "threshold for required landlord approval": ["approval", "consent", "without landlord's", "exceed"],
    "landlord contribution to tenant improvements": ["allowance", "contribution", "landlord shall pay", "ti allowance"],
    "ownership of improvements at lease end":   ["ownership", "title", "property of", "become landlord's"],
    "removal obligation at lease expiration":   ["remove", "restore", "removal", "surrender"],
    "lien discharge or bond requirement":       ["lien", "mechanic's lien", "bond", "discharge"],
    "monetary default definition and cure period": ["monetary default", "failure to pay", "cure period", "five", "10 days"],
    "non-monetary default definition":          ["non-monetary", "default other than", "failure to perform", "30 days"],
    "notice requirement before default":        ["written notice", "notice of default", "prior notice"],
    "landlord termination right":               ["terminate", "termination", "landlord may terminate"],
    "landlord re-entry right":                  ["re-enter", "re-entry", "retake possession"],
    "tenant's right to cure third-party":       ["mortgagee", "lender", "third party cure"],
    "rent acceleration on default":             ["accelerate", "acceleration", "immediately due"],
    "triggering conditions for early termination": ["may terminate", "right to terminate", "upon", "if"],
    "notice period required":                   ["written notice", "months' notice", "prior written notice"],
    "termination fee or penalty formula":       ["termination fee", "penalty", "equal to", "months' rent"],
    "unamortized tenant improvement":           ["unamortized", "unamortized cost", "tenant improvement cost"],
    "co-tenancy termination trigger":           ["co-tenancy", "anchor", "go dark", "occupancy"],
    "tenant indemnification of landlord":       ["tenant shall indemnify", "tenant indemnifies", "hold landlord harmless"],
    "landlord indemnification of tenant":       ["landlord shall indemnify", "landlord indemnifies", "hold tenant harmless"],
    "mutual vs one-way indemnification":        ["mutual", "each party", "respectively"],
    "cap on liability":                         ["cap", "not exceed", "maximum liability", "limitation of liability"],
    "exclusion of consequential damages":       ["consequential", "punitive", "special damages", "indirect"],
    "carve-outs for indemnitee negligence":     ["negligence", "gross negligence", "willful misconduct", "solely caused"],
    "definition of qualifying force majeure":   ["force majeure", "act of god", "fire", "flood", "war", "pandemic"],
    "scope of excused obligations":             ["excused", "suspended", "delayed", "shall not be liable"],
    "rent abatement during force majeure":      ["abatement", "abate", "reduce rent", "suspend rent"],
    "partial rent abatement or adjustment for operational impairment": ["partial abatement", "proportionate abatement", "equitable abatement", "pro rata abatement", "partial rent reduction", "operational impairment", "partially untenantable"],
    "notice requirement to invoke":             ["notice", "notify", "written notice", "within"],
    "termination right if force majeure exceeds": ["terminate", "termination right", "180 days", "120 days"],
    "exterior signage right":                   ["exterior sign", "exterior storefront", "storefront", "facade", "storefront sign", "identification sign"],
    "pylon or monument sign right":             ["pylon", "monument", "freestanding sign", "pole sign"],
    "directory listing right":                  ["directory", "building directory", "tenant directory"],
    "approval process and timeline":            ["approval", "consent", "approve", "within"],
    "landlord's right to modify or remove":     ["modify", "remove", "relocate sign", "landlord may"],
    "compliance with code":                     ["code", "ordinance", "sign criteria", "applicable law"],
    "parking space allocation":                 ["parking spaces", "spaces", "per 1,000", "ratio"],
    "reserved vs unreserved designation":       ["reserved", "unreserved", "designated", "assigned"],
    "parking cost":                             ["parking fee", "parking charge", "included", "no charge"],
    "landlord's right to modify parking":       ["modify", "reconfigure", "change", "landlord may"],
    "visitor customer parking access":          ["visitor", "customer", "common parking", "public parking"],
    "exclusive parking protection":             ["exclusive", "dedicated", "reserved for tenant"],
    "dispute resolution mechanism":             ["arbitration", "mediation", "litigation", "dispute"],
    "governing law":                            ["governed by", "laws of", "state of", "governing law"],
    "venue jurisdiction":                       ["venue", "jurisdiction", "courts of", "county"],
    "attorney fee allocation":                  ["attorney", "attorney's fees", "prevailing party", "fees and costs"],
    "jury trial waiver":                        ["jury", "waive", "jury trial", "waiver of jury"],
    "time limit for bringing claims":           ["statute of limitations", "within", "months of", "years of"],
    "holdover rent rate":                       ["150%", "200%", "holdover rent", "monthly rent times"],
    "month-to-month vs tenancy-at-sufferance":  ["month-to-month", "tenancy at sufferance", "holdover tenancy"],
    "notice required to terminate holdover":    ["notice", "written notice", "terminate holdover"],
    "landlord's right to collect consequential": ["consequential", "damages", "losses", "costs"],
    "conversion to new lease conditions":       ["new lease", "same terms", "renewed", "converted"],
    # Step 298a: LP-30 estoppel — element matchers too narrow for actual lease phrasing
    "tenant's obligation to provide estoppel":  ["tenant shall execute", "tenant shall deliver",
                                                  "execute and deliver", "deliver an estoppel",
                                                  "deliver to landlord an estoppel"],
    "response deadline":                        ["days after landlord", "days after request",
                                                  "days of request", "days from request",
                                                  "business days from", "within ten", "within 10"],
    # Fix false-positive: "request" alone matched "landlord's written request"
    "limitation on request frequency":          ["per year", "times per year", "frequency limit",
                                                  "not more than once", "more than twice", "per calendar"],
}


# LPs where certain elements are commonly cross-sectioned (in a different article
# from the main provision). Full-document text is searched as fallback ONLY for
# these LPs to avoid introducing false positives in all other 31 LPs. Step 298a.
_FULL_TEXT_FALLBACK_LPS = {"LP-08"}

# LPs where the extractor may miss the provision entirely (e.g. entry rights
# embedded inside a maintenance article rather than a standalone Right of Entry
# article). Global scan is attempted before declaring missing. Step 298a.
_GLOBAL_SCAN_LPS = {"LP-29"}

# LP-specific anchor keywords used ONLY for locating the relevant document
# excerpt in _global_scan_for_lp. Separate from _ELEMENT_KEYWORDS so they do
# not affect element matching for any other LP. Must be ≥8 chars and distinctive
# enough to avoid matching common boilerplate sections. Step 298a.
_LP_GLOBAL_SCAN_KEYWORDS = {
    "LP-29": ["landlord may enter", "right to enter", "right of entry", "enter the premises"],
}


def _global_scan_for_lp(pid: str, full_text: str, expected_elements: list) -> str:
    """Search the full document for LP-relevant content when the extractor missed it.

    Only runs for LPs in _GLOBAL_SCAN_LPS. Uses _LP_GLOBAL_SCAN_KEYWORDS when
    available (LP-specific, avoids generic keywords that appear in boilerplate
    before the relevant section). Returns a ~600-char excerpt, empty if not found.
    """
    if pid not in _GLOBAL_SCAN_LPS:
        return ""
    full_lower = full_text.lower()
    scan_kws = _LP_GLOBAL_SCAN_KEYWORDS.get(pid)
    if scan_kws:
        for kw in scan_kws:
            idx = full_lower.find(kw)
            if idx >= 0:
                start = max(0, idx - 150)
                end = min(len(full_text), idx + 450)
                return full_text[start:end].strip()
    else:
        # Fallback: use element keywords with ≥8-char filter
        for element in expected_elements:
            keywords = _get_element_keywords(element)
            long_kws = [kw for kw in keywords if len(kw) >= 8]
            for kw in long_kws:
                idx = full_lower.find(kw)
                if idx >= 0:
                    start = max(0, idx - 150)
                    end = min(len(full_text), idx + 450)
                    return full_text[start:end].strip()
    return ""


def _assess_elements(pid: str, tenant_text: str, expected_elements: list,
                     full_text: str = None, min_kw_len: int = 1) -> tuple:
    """Match expected elements against tenant text.

    Args:
        pid: Issue area ID.
        tenant_text: Extracted provision text for this LP.
        expected_elements: List of expected element descriptions from schema.
        full_text: Optional full document text used as fallback ONLY for LPs in
                   _FULL_TEXT_FALLBACK_LPS. Handles cross-article elements such as
                   LP-08 waiver of subrogation located in the Indemnification article.
                   Only keywords ≥8 chars are used for the fallback. Step 298a.
        min_kw_len: Minimum keyword length for primary tenant_text matching.
                    Default 1 (all keywords, existing behavior). Pass 9 when
                    matching against a global-scan excerpt to suppress false
                    positives from common words ("tenant", "landlord", etc.).
                    Step 298a.
    """
    found = []
    missing = []
    text_lower = tenant_text.lower()
    full_text_lower = full_text.lower() if (full_text and pid in _FULL_TEXT_FALLBACK_LPS) else None

    for element in expected_elements:
        keywords = _get_element_keywords(element)

        # Apply min_kw_len filter (for global-scan excerpts with common words)
        if min_kw_len > 1:
            effective_kws = [kw for kw in keywords if len(kw) >= min_kw_len]
            if not effective_kws:
                # No keywords meet the minimum length threshold; skip this element
                missing.append(element)
                continue
        else:
            effective_kws = keywords

        if any(kw in text_lower for kw in effective_kws):
            found.append(element)
        elif full_text_lower:
            # Full-text fallback: only for _FULL_TEXT_FALLBACK_LPS, long keywords only
            long_kws = [kw for kw in keywords if len(kw) >= 8]
            if long_kws and any(kw in full_text_lower for kw in long_kws):
                found.append(element)
            else:
                missing.append(element)
        else:
            missing.append(element)
    return found, missing


def _get_element_keywords(element: str) -> list:
    element_lower = element.lower()
    # Normalize slashes and parens so "venue / jurisdiction" matches "venue jurisdiction"
    element_normalized = re.sub(r"[/()|]+", " ", element_lower)
    element_normalized = re.sub(r"\s+", " ", element_normalized).strip()
    for key, keywords in _ELEMENT_KEYWORDS.items():
        if (key in element_normalized or element_normalized in key
                or key in element_lower or element_lower in key):
            return keywords
    stop_words = {"or", "and", "the", "a", "an", "of", "in", "for",
                  "to", "at", "by", "if", "any", "with"}
    words = re.split(r"[\s\(\)/,]+", element_lower)
    keywords = [w for w in words if len(w) >= 4 and w not in stop_words]
    return keywords[:3] if keywords else [element_lower[:20]]


# ── Coverage state determination ───────────────────────────────────────────────

def _determine_coverage_state(pid, tenant_text, elements_found, elements_missing,
                               ns_signals, coverage_state_rules, area) -> tuple:
    text_lower = tenant_text.lower()
    total_elements = len(elements_found) + len(elements_missing)

    high_ns = [s for s in ns_signals if s.get("severity") == "high"
               and s["signal_type"] in ("broken_xref", "missing_exhibit")]
    if high_ns and len(elements_missing) > len(elements_found):
        return (
            "broken_xref",
            f"Provision present but {len(high_ns)} broken reference(s) detected and "
            f"{len(elements_missing)} of {total_elements} expected elements missing"
        )

    unfavorable = _check_unfavorable_patterns(pid, text_lower)
    if unfavorable:
        return ("covered_unfavorable", unfavorable)

    unenforceable = _check_unenforceable_patterns(pid, text_lower)
    if unenforceable:
        return ("potentially_unenforceable", unenforceable)

    if total_elements == 0:
        return ("covered", "No expected elements to assess; provision present")

    found_ratio = len(elements_found) / total_elements

    if found_ratio == 1.0:
        return ("covered", f"All {total_elements} expected elements found")

    if found_ratio >= 0.6:
        missing_names = ", ".join(elements_missing[:3])
        if len(elements_missing) > 3:
            missing_names += f" (+{len(elements_missing) - 3} more)"
        return (
            "partial",
            f"{len(elements_found)} of {total_elements} expected elements found; "
            f"missing: {missing_names}"
        )

    if found_ratio >= 0.3:
        ambiguous = _check_ambiguous_patterns(pid, text_lower)
        if ambiguous:
            return ("ambiguous", ambiguous)
        return ("partial", f"Only {len(elements_found)} of {total_elements} expected elements found")

    ambiguous = _check_ambiguous_patterns(pid, text_lower)
    if ambiguous:
        return ("ambiguous", ambiguous)

    return (
        "review_needed",
        f"Provision present but only {len(elements_found)} of {total_elements} "
        f"expected elements found; manual review recommended"
    )


_UNFAVORABLE_PATTERNS = {
    "LP-01": [
        (r"grace period.{0,50}(?:none|no grace|waived)", "No late payment grace period"),
    ],
    "LP-07": [
        (r"audit.{0,80}(?:waived|no right|shall not|not entitled)", "Audit rights waived or absent"),
        (r"(?:shall not|no right).{0,40}(?:audit|inspect).{0,40}(?:books|records|landlord)", "Audit rights explicitly removed"),
    ],
    "LP-09": [
        (r"sole.{0,20}(?:and absolute )?discretion", "Landlord consent in sole discretion — no reasonableness standard"),
    ],
    "LP-11": [
        (r"(?:one|1|two|2|three|3)\s+(?:business\s+)?days.{0,40}(?:cure|default)", "Unusually short cure period"),
        (r"(?:perform|covenant|condition).{0,200}(?:ten|10|fifteen|15)\s*\(?\d*\)?\s*(?:business\s+)?days?\s+after\s+written\s+notice", "Non-monetary cure period unusually short (under 30 days) — typical is 30 days"),
    ],
    "LP-13": [
        (r"(?:no\s+cap|uncapped|unlimited).{0,50}(?:liability|damages)", "No liability cap"),
        (r"landlord\s+(?:shall|will|agrees?\s+to)\s+indemnif.{0,200}gross\s+negligence\s+(?:or|and)\s+willful\s+misconduct", "Asymmetric mutual indemnification: landlord indemnification limited to gross negligence or willful misconduct"),
    ],
    "LP-14": [
        (r"(?:wholly|totally)\s+untenantable", "Abatement limited to 'wholly/totally untenantable' standard with no partial-abatement mechanism for operational impairment"),
    ],
    "LP-17": [
        (r"attorney.{0,40}(?:landlord only|only landlord|landlord.s fees)", "One-sided attorney fee provision"),
    ],
    "LP-18": [
        (r"200%|two hundred percent|double.{0,30}rent", "Holdover rate at 200% or above"),
        (r"automatically.{0,50}(?:renew|converted).{0,50}(?:12|twelve).{0,20}month", "Holdover converts to new 12-month term automatically"),
    ],
}

_AMBIGUOUS_PATTERNS = {
    "LP-02": [(r"(?:reasonable|fair)\s+market.{0,30}(?:increase|adjustment)", "Escalation based on undefined market standard")],
    "LP-03": [(r"fair\s+market\s+(?:rent|value).{0,100}(?:renewal|option).{0,100}(?!determined|appraiser|arbitration)", "Renewal rent at FMV with no determination mechanism")],
    "LP-05": [(r"(?:retail|general|lawful).{0,20}use", "Use defined too broadly without specific business description")],
    "LP-07": [(r"landlord.s\s+(?:reasonable\s+)?determination", "Proportionate share at landlord's determination — no formula")],
    "LP-14": [(r"including\s+without\s+limitation[^.;]{0,20}[.;]", "Force majeure catch-all with no enumeration")],
    "LP-16": [(r"(?:in common|shared).{0,40}parking.{0,40}(?:without|no).{0,30}(?:count|number|ratio|allocated)", "Parking in common with no allocation count")],
}

_UNENFORCEABLE_PATTERNS = {
    "LP-11": [(r"(?:self.help|re.enter|retake).{0,80}(?:without\s+)?(?:notice|court|judicial)", "Self-help re-entry without court order — may be unenforceable")],
    "LP-13": [(r"indemnif.{0,60}gross\s+negligence.{0,60}(?:landlord|indemnitee)", "Indemnification for gross negligence — unenforceable in many jurisdictions")],
}


def _check_unfavorable_patterns(pid, text_lower):
    for pattern, description in _UNFAVORABLE_PATTERNS.get(pid, []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return description
    return None


def _check_ambiguous_patterns(pid, text_lower):
    for pattern, description in _AMBIGUOUS_PATTERNS.get(pid, []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return description
    return None


def _check_unenforceable_patterns(pid, text_lower):
    for pattern, description in _UNENFORCEABLE_PATTERNS.get(pid, []):
        if re.search(pattern, text_lower, re.IGNORECASE):
            return description
    return None


# ── Assessment builder ─────────────────────────────────────────────────────────

def _build_assessment(pid, area, coverage_state, applicability, evidence_summary,
                      supporting_provisions, negative_space, elements_found, elements_missing,
                      tenant_text=""):
    from cam.adapters.lease_review.lease_knowledge import (
        get_caution_signals, get_caution_signal_definition,
        get_exposure_statement, get_risk_if_missing, get_related_issue_areas,
    )
    caution_keys = get_caution_signals(pid)
    caution_definitions = {k: get_caution_signal_definition(k) for k in caution_keys}
    if coverage_state == "not_applicable":
        exposure = ""
    elif coverage_state in ("missing", "broken_xref"):
        exposure = get_risk_if_missing(pid) or get_exposure_statement(pid)
    else:
        exposure = get_exposure_statement(pid)
    return {
        "issue_area_id": pid,
        "issue_area_name": area.get("name", pid),
        "applicability": applicability,
        "coverage_state": coverage_state,
        "evidence_summary": evidence_summary,
        "exposure_statement": exposure,
        "supporting_provision_ids": supporting_provisions,
        "elements_found": elements_found,
        "elements_missing": elements_missing,
        "negative_space_signals": negative_space,
        "caution_signals": caution_keys,
        "caution_signal_definitions": caution_definitions,
        "related_issue_areas": get_related_issue_areas(pid),
        "requires_attention": coverage_state in (
            "missing", "broken_xref", "covered_unfavorable",
            "partial", "potentially_unenforceable"
        ),
        # Step 297d.J-fix: which party is adversely affected when state is covered_unfavorable.
        # Read from schema area.covered_unfavorable_adverse_to; null for non-unfavorable states.
        # Frontend uses this (not exposure_perspective) to determine viewer-favorability.
        "covered_unfavorable_adverse_to": (
            area.get("covered_unfavorable_adverse_to")
            if coverage_state == "covered_unfavorable" else None
        ),
        # Step 301 (Stage 5d): baseline immutable record of what deterministic rules said.
        # use_adjusted / use_adjustment_reason may be mutated by lease_use_aware_coverage
        # after assessment but before conflicts; baseline is never modified post-hoc.
        "coverage_state_baseline": coverage_state,
        "use_adjusted": False,
        "use_adjustment_reason": None,
        # Step 303 (Stage 5d multi-eval): governance fields — set by merge function.
        # Initialized here so every CA entry carries these fields regardless of flag state.
        "use_aware_consensus": None,   # "3_of_3" | "2_of_3" | "1_of_3" | "2_of_2" | None
        "use_aware_abstained": False,  # True when merge outcome is abstain
        "tenant_text": tenant_text,
        # Step 352: verdict distance defaults — Stage 305 overrides these when it runs.
        # not_assessed means Stage 305 genuinely did not run for this LP.
        "verdict_distance": dict(NOT_ASSESSED_SENTINEL),
        "per_evaluator_lp_verdicts": {},
        "lp_confidence_base": None,
    }


def _log_coverage_summary(assessments):
    state_counts = {}
    attention_count = 0
    for a in assessments:
        state = a["coverage_state"]
        state_counts[state] = state_counts.get(state, 0) + 1
        if a["requires_attention"]:
            attention_count += 1
    logger.info(f"[lease_coverage] States: {state_counts} | Requires attention: {attention_count}")


# ── Summary helper ─────────────────────────────────────────────────────────────

def summarize_coverage(assessments: list) -> dict:
    state_counts = {}
    attention_items = []
    for a in assessments:
        state = a["coverage_state"]
        state_counts[state] = state_counts.get(state, 0) + 1
        if a["requires_attention"]:
            attention_items.append({
                "id": a["issue_area_id"],
                "name": a["issue_area_name"],
                "state": state,
                "exposure": a["exposure_statement"],
            })
    state_order = {"missing": 0, "broken_xref": 1, "potentially_unenforceable": 2,
                   "covered_unfavorable": 3, "partial": 4, "ambiguous": 5, "review_needed": 6}
    attention_items.sort(key=lambda x: state_order.get(x["state"], 99))
    return {
        "total_assessed": len(assessments),
        "state_counts": state_counts,
        "attention_count": len(attention_items),
        "attention_items": attention_items,
        "not_applicable_count": state_counts.get("not_applicable", 0),
        "covered_count": state_counts.get("covered", 0),
    }


# ── CLI / Quick Test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from pathlib import Path
    _project_root = Path(__file__).parents[3]
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

    from cam.adapters.lease_review.lease_parser import parse_document
    from cam.adapters.lease_review.lease_negative_space import detect_negative_space
    from cam.adapters.lease_review.lease_knowledge import get_all_issue_areas

    demo_dir = Path(__file__).parents[3] / "05 Lease Analyzer" / "static" / "demo"
    demo_files = sorted(demo_dir.glob("*.txt"))

    if demo_files:
        demo_file = demo_files[0]
        print(f"Testing with: {demo_file.name}")
        full_text = parse_document(str(demo_file))
    else:
        print("No demo files found — using synthetic text")
        full_text = ""

    print("Note: CLI test uses full document text per provision (approximation).")
    print("Real pipeline passes precisely extracted clause text — results will differ.\n")

    provisions = [
        {
            "provision_id": area["id"],
            "provision_name": area["name"],
            "tenant_text": full_text,
            "template_text": "",
        }
        for area in get_all_issue_areas()
    ]

    ns_signals = detect_negative_space(provisions, full_text)
    assessments = assess_coverage(provisions, full_text, ns_signals)
    summary = summarize_coverage(assessments)

    print(f"Assessed {summary['total_assessed']} issue areas")
    print(f"Covered: {summary['covered_count']} | "
          f"Not applicable: {summary['not_applicable_count']} | "
          f"Requires attention: {summary['attention_count']}")
    print()

    for a in assessments:
        state = a["coverage_state"]
        marker = "⚠ " if a["requires_attention"] else "✓ " if state == "covered" else "— "
        ns_count = len(a["negative_space_signals"])
        ns_note = f" [{ns_count} neg-space signal(s)]" if ns_count else ""
        print(f"{marker}{a['issue_area_id']} {a['issue_area_name']}: {state}{ns_note}")
        if a["evidence_summary"] and state not in ("covered", "not_applicable"):
            print(f"    {a['evidence_summary']}")
