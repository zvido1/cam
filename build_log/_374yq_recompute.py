# Step 374Y-Q READ-ONLY polarity recompute. Reads existing run JSONs + the schema only.
# NO production change. Replicates derive_lp_state + _classify_materiality + _classify_partial +
# coverage action bucket, then recomputes under 4 polarity candidates. n=2 -> DIRECTIONAL ONLY.
import json
from collections import Counter

SCHEMA = 'cam/adapters/lease_review/schemas/retail_lease_knowledge.json'
RUNS = {'030920': '05 Lease Analyzer/results/lease_review_20260602_030920_d0e19e/tenant_0/pipeline_results.json',
        '181402': '05 Lease Analyzer/results/lease_review_20260601_181402_2d1700/tenant_0/pipeline_results.json'}
PERSP = 'tenant'
OPP = {'tenant': 'landlord', 'landlord': 'tenant'}[PERSP]

PRESENCE = {'explicitly_present', 'implicitly_present', 'covered_by_default_law', 'covered_in_other_LP'}
MISSING = {'missing', 'disputed'}

# verbatim from lease_exposure.py
_HIGH_MATERIALITY_ELEMENTS = {
    "cap on liability (if any)", "excluded expense categories", "assignment in connection with sale of business",
    "landlord indemnification of tenant scope", "rent abatement during force majeure period",
    "termination right if force majeure exceeds threshold period", "grounds for withholding consent (reasonableness standard)",
    "tenant's right to cure third-party defaults", "rent acceleration on default",
    "recapture right (landlord can terminate and lease directly)",
}
_MEDIUM_MATERIALITY_ELEMENTS = {
    "escalation cap or ceiling", "calculation methodology", "affiliate exception (no consent required for related entities)",
    "profit sharing on sublet above base rent", "removal obligation at lease expiration", "lien discharge or bond requirement",
    "annual CAM increase cap", "waiver of subrogation", "landlord contribution to tenant improvements (if any)",
    "unamortized tenant improvement cost recovery", "co-tenancy termination trigger (if applicable)",
    "time limit for bringing claims", "renewal option count and duration", "rent at renewal (formula or fair market value mechanism)",
}
_MODEL_STATES = {"covered_unfavorable", "ambiguous", "potentially_unenforceable"}
_HIGH_MATERIALITY_LPS = {"LP-27"}

# ── schema polarity map ───────────────────────────────────────────────────────
sch = json.load(open(SCHEMA, encoding='utf-8'))
POL = {}      # element_id -> (adverse_to, severity)
SEV_BY_ID = {}
for ia in sch['issue_areas']:
    for e in ia.get('expected_elements_305') or []:
        if isinstance(e, dict):
            POL[e.get('element_id')] = (e.get('absence_adverse_to'), e.get('absence_severity'))
            SEV_BY_ID[e.get('element_id')] = e.get('absence_severity')


def derive_lp_state(evs):
    """evs: list of {element_id, verdict}. Mirrors lease_coverage_305.derive_lp_state."""
    if not evs:
        return 'review_needed'
    high_ids = {e['element_id'] for e in evs if SEV_BY_ID.get(e['element_id']) == 'high'}
    any_unclear = any(r['verdict'] == 'unclear' for r in evs)
    all_pos = all(r['verdict'] in PRESENCE for r in evs)
    miss = [r for r in evs if r['verdict'] in MISSING]
    high_missing = any(r['element_id'] in high_ids for r in miss)
    if any_unclear:
        return 'review_needed'
    if all_pos:
        return 'covered'
    total = len(evs)
    n = len(miss)
    if high_missing:
        return 'missing' if n > total // 2 else 'partial'
    if n > 0:
        return 'partial'
    return 'covered'


def classify_materiality(state, missing_labels, pid):
    if state in _MODEL_STATES:
        return 'high'
    if state == 'missing':
        return 'high'
    if state in ('covered', 'not_applicable'):
        return 'low'
    if pid in _HIGH_MATERIALITY_LPS and state not in ('covered', 'not_applicable'):
        return 'high'
    ms = {m.lower() for m in missing_labels}
    if any(x in ms for x in _HIGH_MATERIALITY_ELEMENTS):
        return 'high'
    if any(x in ms for x in _MEDIUM_MATERIALITY_ELEMENTS):
        return 'medium'
    return 'low'


def classify_partial(state, materiality):
    if state != 'partial':
        return None
    return {'high': 'partial_material', 'medium': 'partial_review'}.get(materiality, 'partial_typical')


def bucket(state, pcls, use_impact, adverse_to_for_state):
    """Coverage action bucket — mirrors app.js classifyFindingType / 374P cons_bucket."""
    ui = use_impact
    mat = (ui or {}).get('materiality') if ui else None
    gap = (ui or {}).get('gap_impact') if ui else None
    uiA = bool(ui) and (ui or {}).get('confidence') != 'no_evaluators'
    if state in ('covered', 'covered_typical', 'not_applicable'):
        return 'addressed'
    if state == 'potentially_unenforceable':
        return 'risk'
    ih = (pcls == 'partial_material') or (mat == 'high')
    sv = 'risk' if ih else 'improvement'
    if state == 'covered_unfavorable':
        return 'risk' if ih else 'improvement'
    if state == 'missing':
        if uiA and gap == 'favorable':
            return 'addressed'
        if uiA and mat == 'not_applicable':
            return 'improvement'
        return sv
    if state == 'partial':
        if pcls == 'partial_review':
            return 'improvement'
        return sv
    if state == 'review_needed':
        return 'review_needed'
    return 'review_needed'


# Candidate exclusion: which missing elements are NOT counted as adverse for the perspective.
# C1 baseline: exclude none. C2: exclude opposite + null (only tenant/both count).
# C3: exclude opposite only (null/contextual stay adverse/reviewable). C4: same exclusion as C3 for
# state scoring, but opposite-only-driven LPs may never be Risk-by-absence (favorable annotation).
def excluded_missing(evs, cand):
    """Return set of element_ids to treat as NON-adverse (drop from adverse scoring) for candidate."""
    out = set()
    for r in evs:
        if r['verdict'] not in MISSING:
            continue
        adv, _ = POL.get(r['element_id'], (None, None))
        if cand == 'C1':
            continue
        if adv == OPP:                      # clearly opposite-polarity -> favorable
            out.add(r['element_id'])
        elif adv in (None, '', 'unknown'):  # ambiguous / null
            if cand == 'C2':                # C2 aggressive: treat ambiguous as non-adverse
                out.add(r['element_id'])
            # C3/C4 keep ambiguous reviewable (do not exclude)
        # adv == tenant or 'both' -> stays adverse (kept) for all candidates
    return out


for lbl, path in RUNS.items():
    d = json.load(open(path, encoding='utf-8'))
    ca = [a for a in d['coverage_assessment'] if (a.get('coverage_state') != 'not_applicable')]
    print('================ RUN %s ================' % lbl)
    # Governance gate: only LPs where derive_lp_state(all) reproduces the production coverage_state
    # are governed by the missing-element-count path; polarity exclusion can only move THOSE. LPs whose
    # state comes from another path (unclear/dispute/unenforceable) are reported separately and never move.
    governed, nongoverned = [], []
    for a in ca:
        evs = [{'element_id': e.get('element_id'), 'verdict': e.get('verdict'), 'label': e.get('element_label')}
               for e in (a.get('element_verdicts') or [])]
        if derive_lp_state(evs) == a.get('coverage_state'):
            governed.append(a)
        else:
            nongoverned.append((a.get('issue_area_id'), a.get('coverage_state'), derive_lp_state(evs)))
    print('  governed-by-missing-count LPs: %d | non-governed (state via other path): %d' % (len(governed), len(nongoverned)))
    print('  non-governed (excluded from polarity-flip analysis):',
          ', '.join('%s[%s]' % (p, s) for p, s, _ in nongoverned))

    for cand in ['C2', 'C3', 'C4']:
        moves = []
        d_risk = d_pr = 0
        lost = []
        for a in governed:
            pid = a.get('issue_area_id')
            evs = [{'element_id': e.get('element_id'), 'verdict': e.get('verdict'), 'label': e.get('element_label')}
                   for e in (a.get('element_verdicts') or [])]
            ui = a.get('use_impact')
            base_state = a.get('coverage_state')
            base_mat = classify_materiality(base_state, [e['label'] for e in evs if e['verdict'] in MISSING], pid)
            base_b = bucket(base_state, classify_partial(base_state, base_mat), ui, None)
            excl = excluded_missing(evs, cand)
            if not excl:
                continue
            evs_c = [e for e in evs if e['element_id'] not in excl]
            state_c = derive_lp_state(evs_c)
            mat_c = classify_materiality(state_c, [e['label'] for e in evs_c if e['verdict'] in MISSING], pid)
            b = bucket(state_c, classify_partial(state_c, mat_c), ui, None)
            if state_c != base_state or b != base_b:
                drv = sorted({POL.get(e['element_id'], (None, None))[0] or 'null' for e in evs
                              if e['verdict'] in MISSING and e['element_id'] in excl})
                kind = 'FAVORABLE' if drv == ['landlord'] else ('AMBIGUOUS' if 'null' in drv else 'mixed')
                moves.append((pid, base_state, state_c, base_b, b, ','.join(drv), kind))
                if base_b == 'risk':
                    d_risk -= 1
                    if base_b == 'risk':
                        d_pr -= 1 if (ui or {}).get('materiality') == 'high' else 0
                if base_b == 'risk' and b != 'risk':
                    lost.append((pid, drv))
        print('  --- %s : dRisk=%+d dPriority=%+d | lost-genuine-adverse=%s ---' % (cand, d_risk, d_pr, lost or 'NONE'))
        if not moves:
            print('     (no governed LP changes)')
        for m in moves:
            print('     %-7s state %-13s->%-10s | bucket %-11s->%-11s | driver=%-10s [%s]' % m)
    print()

# null/ambiguous live missing?
print('================ NULL/AMBIGUOUS live missing check ================')
nnull = 0
for lbl, path in RUNS.items():
    d = json.load(open(path, encoding='utf-8'))
    for a in d['coverage_assessment']:
        for e in (a.get('element_verdicts') or []):
            if e.get('verdict') in MISSING:
                adv, _ = POL.get(e.get('element_id'), ('__missing_from_schema__', None))
                if adv in (None, '', 'unknown', '__missing_from_schema__'):
                    nnull += 1
                    print('  %s %s %s adv=%r' % (lbl, a.get('issue_area_id'), e.get('element_id'), adv))
print('  total null/ambiguous live missing:', nnull)

# _HIGH/_MEDIUM_MATERIALITY_ELEMENTS opposite-polarity landmine: match legacy strings to schema labels
print('================ _HIGH/_MEDIUM_MATERIALITY_ELEMENTS polarity (legacy strings vs schema) ================')
label_pol = {}
for ia in sch['issue_areas']:
    for e in ia.get('expected_elements_305') or []:
        if isinstance(e, dict):
            label_pol[(e.get('element_label') or '').lower()] = (e.get('element_id'), e.get('absence_adverse_to'))
for setname, S in [('HIGH', _HIGH_MATERIALITY_ELEMENTS), ('MED', _MEDIUM_MATERIALITY_ELEMENTS)]:
    for s in sorted(S):
        # substring match against any schema label
        hits = [(eid, adv) for lab, (eid, adv) in label_pol.items() if s in lab or lab in s]
        tag = ''
        if any(adv and adv != PERSP for _, adv in hits):
            tag = '  <== OPPOSITE/NON-TENANT POLARITY'
        print('  [%s] %-58s schema-match=%s%s' % (setname, s, hits if hits else 'NO 305-LABEL MATCH', tag))
