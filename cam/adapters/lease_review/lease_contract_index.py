"""
Step 359 — Contract Section Index

Builds a structured index of lease sections from pipeline_results,
grouping findings (element verdicts and cross-provision findings) by
section reference.

Two public functions:
    normalize_section_ref(raw: str) -> list[str]
    build_contract_section_index(pipeline: dict) -> list[dict]
"""

import re

# ── Regex constants ────────────────────────────────────────────────────────

_LP_PREFIX_RE = re.compile(r'^LP-\d+[,\s]+\s*', re.IGNORECASE)  # handles "LP-27, Section" and "LP-27 Section"
_LP_SUFFIX_RE = re.compile(r'\s*\(LP-\d+\)\s*$', re.IGNORECASE)
_BARE_NUMBER_RE = re.compile(r'^\d+(\.\d+)*[a-z]?$', re.IGNORECASE)
_VALID_SEC_PART_RE = re.compile(r'^\d+(\.\d+)*[a-z]?$', re.IGNORECASE)
_SECTIONS_PREFIX_RE = re.compile(r'^sections?\s+', re.IGNORECASE)


# ── Public: normalize_section_ref ─────────────────────────────────────────

def normalize_section_ref(raw: str) -> list:
    """
    Takes a raw citation string and returns a list of one or more
    normalized section keys.

    Rules applied in order:
    1. Strip LP prefix  ("LP-24 Section 13.1" → "Section 13.1"; also "LP-27, Section 5.1")
    2. Strip LP suffix  ("Section 5.1 (LP-27)" → "Section 5.1")
    3. Bare number      ("15.1" → "Section 15.1")
    4. Plural split     ("Sections 11.1 and 11.2" → ["Section 11.1", "Section 11.2"])
    5. Range split      ("Sections 8.1-8.2" → ["Section 8.1", "Section 8.2"])
    6. Already "Section X.Y" → return as-is
    7. Article ref      → return as article-level ref
    7b. Embedded section ref ("Default law; Section 12.2" → "Section 12.2")
    8. Anything else    → return as-is

    Never throws. Returns [] for None/empty input.
    """
    if not raw:
        return []

    s = raw.strip()
    if not s:
        return []

    # 1. Strip LP prefix
    s = _LP_PREFIX_RE.sub('', s).strip()

    # 2. Strip LP suffix
    s = _LP_SUFFIX_RE.sub('', s).strip()

    if not s:
        return []

    # 3. Bare number: "15.1" → "Section 15.1"
    if _BARE_NUMBER_RE.match(s):
        return [f'Section {s}']

    # 4. Plural split: "Sections 11.1 and 11.2" or "Section 5.1 and Section 5.2"
    lower = s.lower()
    if lower.startswith('sections ') or ' and section' in lower:
        parts = re.split(r'\s+and\s+', s, flags=re.IGNORECASE)
        results = []
        for part in parts:
            part = part.strip()
            cleaned = _SECTIONS_PREFIX_RE.sub('', part).strip()
            if cleaned:
                results.append(f'Section {cleaned}')
        if len(results) >= 2:
            return results
        # Fall through if split yielded < 2

    # 5. Range split: "Sections 8.1-8.2"
    range_match = re.match(
        r'^sections?\s+(\d+(?:\.\d+)*[a-z]?)\s*[-–]\s*(\d+(?:\.\d+)*[a-z]?)$',
        s, re.IGNORECASE
    )
    if range_match:
        a, b = range_match.group(1), range_match.group(2)
        if _VALID_SEC_PART_RE.match(a) and _VALID_SEC_PART_RE.match(b):
            return [f'Section {a}', f'Section {b}']

    # 6. Already "Section X.Y" → return as-is
    if re.match(r'^section\s+\S', s, re.IGNORECASE):
        return [s]

    # 7. "Article N" or "Article N — Title" → normalize to "Article N"
    if re.match(r'^article\s+', s, re.IGNORECASE):
        art_match = re.match(r'^(article\s+[\w.]+)', s, re.IGNORECASE)
        if art_match:
            return [art_match.group(1)]
        return [s]

    # 7b. Contains an embedded "Section X.Y" — extract it
    # Handles: "Default law; Section 12.2", "Common law (Section 5.1)", etc.
    # This is a fallback for strings that reached this point without matching rules 1–7.
    # Use a numeric-only pattern to avoid capturing trailing punctuation like ")".
    sec_embedded = re.search(r'\bsection\s+(\d+(?:\.\d+)*[a-z]?)', s, re.IGNORECASE)
    if sec_embedded:
        return [f'Section {sec_embedded.group(1)}']

    # 8. Anything else → return as-is (do not invent precision)
    return [s]


# ── Internal helpers ──────────────────────────────────────────────────────

def _extract_section_key(display_ref: str):
    """
    Extract (section_key, article_key, article_display) from a normalized
    display_ref string.

    Examples:
        "Section 3.1"  → ("3.1",       "3",   "Article 3")
        "Section 15"   → ("15",         "15",  "Article 15")
        "Article 3"    → ("article-3",  "3",   "Article 3")
        other          → (display_ref, display_ref, display_ref)
    """
    s = display_ref.strip()

    if re.match(r'^section\s+', s, re.IGNORECASE):
        key = re.sub(r'^section\s+', '', s, flags=re.IGNORECASE).strip()
        # Extract article key: part before first "."
        dot_pos = key.find('.')
        art_key = key[:dot_pos] if dot_pos != -1 else key
        # Trim non-numeric suffix for article grouping (e.g. "15" from "15.1(a)")
        art_num = re.match(r'^(\d+)', art_key)
        art_key_clean = art_num.group(1) if art_num else art_key
        return key, art_key_clean, f'Article {art_key_clean}'

    if re.match(r'^article\s+', s, re.IGNORECASE):
        rest = re.sub(r'^article\s+', '', s, flags=re.IGNORECASE).strip()
        # "3" or "3.1" or "3 — Title"
        rest = re.split(r'\s*[—–-]\s*', rest)[0].strip()
        dot_pos = rest.find('.')
        art_key = rest[:dot_pos] if dot_pos != -1 else rest
        art_num = re.match(r'^(\d+)', art_key)
        art_key_clean = art_num.group(1) if art_num else art_key
        return f'article-{rest}', art_key_clean, f'Article {art_key_clean}'

    return s, s, s


def _confidence_rank(cq: str) -> int:
    """Higher integer = better confidence."""
    return {
        'section_and_quote': 3,
        'section_only': 2,
        'evaluator_citation': 1,
        'cross_provision': 0,
    }.get(cq, 0)


def _bucket_priority(bucket: str, materiality: str) -> tuple:
    """
    Returns (priority, materiality_rank) — lower value = higher priority.

    Precedence:
    1. review_needed with high materiality  → (0, 0)
    2. risk (any materiality)               → (1, mat)
    3. review_needed (any materiality)      → (2, mat)
    4. improvement                          → (3, mat)
    5. addressed                            → (4, mat)
    """
    mat_rank = {'high': 0, 'medium': 1, 'low': 2}.get(materiality, 2)
    if bucket == 'review_needed' and materiality == 'high':
        return (0, mat_rank)
    if bucket == 'risk':
        return (1, mat_rank)
    if bucket == 'review_needed':
        return (2, mat_rank)
    if bucket == 'improvement':
        return (3, mat_rank)
    if bucket == 'addressed':
        return (4, mat_rank)
    return (9, 9)


# ── Action bucket helpers ─────────────────────────────────────────────────

def classify_action_bucket(lp: dict, el: dict) -> str:
    """
    Determine action bucket for a single element finding.
    Logic mirrors classifyFindingType() in app.js but at element level.
    """
    verdict = el.get('verdict')
    coverage_state = lp.get('coverage_state')

    # Disputed → review_needed
    if verdict == 'disputed':
        return 'review_needed'

    # Unclear → review_needed
    if verdict == 'unclear':
        return 'review_needed'

    # Missing → risk (coverage gap)
    if verdict == 'missing':
        return 'risk'

    # Present verdicts
    if verdict in ('explicitly_present', 'implicitly_present',
                   'covered_in_other_LP', 'covered_by_default_law'):
        if coverage_state in ('covered', 'addressed'):
            return 'addressed'
        if coverage_state in ('review_needed',):
            return 'review_needed'
        if coverage_state in ('partial', 'missing', 'covered_unfavorable'):
            return 'improvement'
        return 'improvement'

    return 'improvement'


def map_cpf_to_bucket(cpf: dict) -> str:
    finding_type = cpf.get('finding_type', '')
    verdict = cpf.get('verdict', '')
    severity = cpf.get('severity', 'LOW')

    if finding_type == 'cross_coverage_relief':
        return 'addressed'
    if finding_type in ('directional_mismatch', 'compound_risk', 'coverage_gap'):
        return 'risk'
    if verdict in ('cross_coverage_confirmed',):
        return 'addressed'
    if severity in ('HIGH', 'MEDIUM'):
        return 'risk'
    return 'improvement'


def severity_to_materiality(severity: str) -> str:
    return {'HIGH': 'high', 'MEDIUM': 'medium', 'LOW': 'low', 'INFO': 'low'}.get(severity, 'low')


# ── Public: build_contract_section_index ──────────────────────────────────

def build_contract_section_index(pipeline: dict) -> list:
    """
    Takes the full pipeline_results dict. Returns a list of section
    index entries, ordered by source_order (contract reading order).

    Sources processed in order:
      A — Element verdicts with non-null citation
      B — Disputed element evaluator-level citations (when element citation is null)
      C — Cross-provision findings (cited_sections + relief_section)
    """
    # index_map: display_ref_normalized → entry dict
    index_map: dict = {}
    _order_counter = [0]

    def get_or_create_entry(section_ref: str, citation_quality: str) -> dict:
        if section_ref not in index_map:
            section_key, article_key, article_display = _extract_section_key(section_ref)
            _order_counter[0] += 1
            index_map[section_ref] = {
                'section_key': section_key,
                'display_ref': section_ref,
                'article_key': article_key,
                'article_display': article_display,
                'source_order': _order_counter[0],
                'anchor_confidence': citation_quality,
                'primary_action_bucket': '',
                'finding_count': 0,
                'affected_lp_ids': [],
                'findings': [],
            }
        else:
            # Upgrade anchor_confidence if this source is more precise
            entry = index_map[section_ref]
            if _confidence_rank(citation_quality) > _confidence_rank(entry['anchor_confidence']):
                entry['anchor_confidence'] = citation_quality
        return index_map[section_ref]

    # ── Source A: Element verdicts with non-null citation ────────────────────
    for lp in pipeline.get('coverage_assessment', []):
        for el in lp.get('element_verdicts', []):
            citation = el.get('citation')
            if citation and isinstance(citation, dict):
                section_refs = normalize_section_ref(citation.get('section_ref', ''))
                cq = citation.get('citation_quality', 'section_only')
                for section_ref in section_refs:
                    entry = get_or_create_entry(section_ref, cq)
                    finding = {
                        'finding_id': el.get('element_id', ''),
                        'finding_source': 'coverage_element',
                        'issue_area_id': lp.get('issue_area_id'),
                        'issue_area_name': lp.get('issue_area_name'),
                        'element_label': el.get('element_label', ''),
                        'action_bucket': classify_action_bucket(lp, el),
                        'verdict': el.get('verdict'),
                        'criticality': el.get('criticality'),
                        'materiality': lp.get('materiality', 'low'),
                        'severity': lp.get('severity'),
                        'dispute_signal': lp.get('dispute_signal', {}).get('triggered', False),
                        'hard_flag': lp.get('review_priority_distance_signal', {}).get('hard_flag', False),
                        'quote': citation.get('quote', ''),
                        'citation_quality': cq,
                        'raw_section_ref': citation.get('section_ref', ''),
                        'section_ref_normalized': section_ref,
                    }
                    entry['findings'].append(finding)
                    lp_id = lp.get('issue_area_id')
                    if lp_id and lp_id not in entry['affected_lp_ids']:
                        entry['affected_lp_ids'].append(lp_id)

    # ── Source B: Disputed element evaluator citations ────────────────────────
    # Elements with verdict='disputed' have citation=null at the merge level.
    # The per-evaluator records (the side that found the clause) carry citations.
    # Check both 'per_evaluator_verdicts' (future schema) and 'evaluator_verdicts'
    # (current schema). If neither exists, skip silently.
    for lp in pipeline.get('coverage_assessment', []):
        for el in lp.get('element_verdicts', []):
            if el.get('verdict') == 'disputed' and el.get('citation') is None:
                per_eval = (
                    el.get('per_evaluator_verdicts')
                    or el.get('evaluator_verdicts')
                    or []
                )
                for eval_verdict in per_eval:
                    eval_cite = eval_verdict.get('citation')
                    if eval_cite and isinstance(eval_cite, dict) and eval_cite.get('section_ref'):
                        section_refs = normalize_section_ref(eval_cite['section_ref'])
                        for section_ref in section_refs:
                            entry = get_or_create_entry(section_ref, 'evaluator_citation')
                            # Skip if Source A already indexed this element at this section
                            already = any(
                                f['finding_id'] == el.get('element_id')
                                for f in entry['findings']
                            )
                            if not already:
                                finding = {
                                    'finding_id': el.get('element_id', ''),
                                    'finding_source': 'coverage_element',
                                    'issue_area_id': lp.get('issue_area_id'),
                                    'issue_area_name': lp.get('issue_area_name'),
                                    'element_label': el.get('element_label', ''),
                                    'action_bucket': 'review_needed',
                                    'verdict': 'disputed',
                                    'criticality': el.get('criticality'),
                                    'materiality': lp.get('materiality', 'low'),
                                    'severity': lp.get('severity'),
                                    'dispute_signal': True,
                                    'hard_flag': lp.get('review_priority_distance_signal', {}).get('hard_flag', False),
                                    'quote': eval_cite.get('quote', ''),
                                    'citation_quality': 'evaluator_citation',
                                    'raw_section_ref': eval_cite['section_ref'],
                                    'section_ref_normalized': section_ref,
                                }
                                entry['findings'].append(finding)
                                lp_id = lp.get('issue_area_id')
                                if lp_id and lp_id not in entry['affected_lp_ids']:
                                    entry['affected_lp_ids'].append(lp_id)

    # ── Source C: Cross-provision findings ────────────────────────────────────
    for cpf in pipeline.get('cross_provision_findings', []):
        all_refs = list(cpf.get('cited_sections', []))
        # Include relief_section if present and not already in cited_sections
        relief = cpf.get('relief_section')
        if relief and relief not in all_refs:
            all_refs.append(relief)

        bucket = map_cpf_to_bucket(cpf)
        mat = severity_to_materiality(cpf.get('severity', 'LOW'))
        for raw_ref in all_refs:
            section_refs = normalize_section_ref(raw_ref)
            for section_ref in section_refs:
                entry = get_or_create_entry(section_ref, 'cross_provision')
                finding = {
                    'finding_id': cpf.get('finding_id', ''),
                    'finding_source': 'cross_provision',
                    'issue_area_id': None,
                    'issue_area_name': None,
                    'element_label': cpf.get('title') or cpf.get('short_summary') or cpf.get('headline', ''),
                    'action_bucket': bucket,
                    'verdict': cpf.get('verdict'),
                    'criticality': None,
                    'materiality': mat,
                    'severity': cpf.get('severity'),
                    'dispute_signal': False,
                    'hard_flag': False,
                    'quote': (cpf.get('detail') or '')[:200],
                    'citation_quality': 'cross_provision',
                    'raw_section_ref': raw_ref,
                    'section_ref_normalized': section_ref,
                    'implicated_lps': cpf.get('implicated_lps', []),
                }
                entry['findings'].append(finding)

    # ── Finalize entries ──────────────────────────────────────────────────────
    bucket_order = {'risk': 0, 'review_needed': 1, 'improvement': 2, 'addressed': 3}
    materiality_order = {'high': 0, 'medium': 1, 'low': 2}

    entries = []
    for entry in index_map.values():
        findings = entry['findings']

        # Sort findings within each section entry
        findings.sort(key=lambda f: (
            bucket_order.get(f['action_bucket'], 9),
            materiality_order.get(f.get('materiality', 'low'), 9),
            0 if f.get('dispute_signal') else 1,
            0 if f.get('hard_flag') else 1,
        ))

        # Determine primary_action_bucket (highest priority across all findings)
        best_priority = None
        best_bucket = 'improvement'
        for f in findings:
            p = _bucket_priority(f['action_bucket'], f.get('materiality', 'low'))
            if best_priority is None or p < best_priority:
                best_priority = p
                best_bucket = f['action_bucket']

        entry['primary_action_bucket'] = best_bucket
        entry['finding_count'] = len(findings)
        entries.append(entry)

    # Sort entries by source_order (contract reading order)
    entries.sort(key=lambda e: e['source_order'])

    return entries
