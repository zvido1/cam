# Step 374R-Q READ-ONLY Priority-Risks basis recompute. Reads existing run JSONs only.
# NO production change. Reuses the 374P provenance + bucket logic verbatim.
import json
from collections import Counter

RANK = {'explicitly_present': 0, 'implicitly_present': 1, 'covered_in_other_lp': 2,
        'covered_in_other_LP': 2, 'covered_by_default_law': 2, 'unclear': 3, 'missing': 5}


def roll(elems, pess=True):
    if not elems:
        return 'unclear', False
    c = Counter(elems); mx = max(c.values()); cand = [v for v, n in c.items() if n == mx]; tie = len(cand) > 1
    if not tie:
        return cand[0], False
    best = cand[0]; br = RANK.get(best, 3)
    for v in cand[1:]:
        r = RANK.get(v, 3)
        if (pess and r > br) or ((not pess) and r < br):
            best = v; br = r
    return best, tie


def severity(vs):
    ds = [abs(RANK.get(a, 0) - RANK.get(b, 0)) for i, a in enumerate(vs) for b in vs[i + 1:] if a in RANK and b in RANK]
    md = max(ds) if ds else 0
    return ('severe' if md >= 4 else 'moderate' if md >= 2 else 'minor' if md == 1 else 'none'), md


def per_ev(a):
    m = {}
    for e in (a.get('element_verdicts') or []):
        for ev in (e.get('evaluator_verdicts') or []):
            m.setdefault(ev.get('role'), []).append(ev.get('verdict'))
    return m


def provenance(a):
    m = per_ev(a); deriv = {}; prod = {}
    for role, el in m.items():
        v, t = roll(el, True); deriv[role] = 'pessimistic_tie_break' if t else 'unique_plurality'; prod[role] = v
    prod_list = list(prod.values()); opt_list = [roll(el, False)[0] for el in m.values()]
    sev_prod, _ = severity(prod_list); sev_opt, _ = severity(opt_list)
    tie_art = any(d == 'pessimistic_tie_break' for d in deriv.values()) and sev_prod == 'severe' and sev_opt != 'severe'
    ui = a.get('use_impact')
    if ui is None:
        cons_src = 'defaulted_missing_use_impact'
    elif (ui or {}).get('materiality') in (None, ''):
        cons_src = 'not_assessed'
    else:
        cons_src = 'assessed'
    return dict(deriv=deriv, prod=prod, sev_prod=sev_prod, sev_opt=sev_opt, tie_derived_severe=tie_art,
                consequence_source=cons_src, assessed_materiality=(ui or {}).get('materiality') if ui else None)


def hf(a):
    return (a.get('review_priority_distance_signal') or {}).get('hard_flag') == True


def cons_bucket(a, p):
    state = a.get('coverage_state') or ''; pcls = a.get('partial_class') or ''
    ui = a.get('use_impact'); gap = ui.get('gap_impact') if ui else None; mat = ui.get('materiality') if ui else None
    uiA = bool(ui) and ui.get('confidence') != 'no_evaluators'
    if state in ('covered', 'covered_typical', 'not_applicable'):
        return 'addressed'
    if state == 'potentially_unenforceable':
        return 'risk'
    mt = 'HIGH' if pcls == 'partial_material' else 'HIGH' if mat == 'high' else 'LOW' if mat == 'low' else 'MEDIUM'; ih = mt == 'HIGH'
    if state == 'covered_unfavorable':
        adv = a.get('covered_unfavorable_adverse_to')
        if adv and p and p != 'neutral' and adv != p:
            return 'addressed'
        return 'risk' if ih else 'improvement'
    sv = lambda: 'risk' if ih else 'improvement'
    if state == 'missing':
        if uiA and gap == 'favorable':
            return 'addressed'
        if uiA and mat == 'not_applicable':
            return 'improvement'
        return sv()
    if state == 'partial':
        if pcls == 'partial_review':
            return 'improvement'
        return sv()
    if state == 'review_needed':
        return 'review_needed'
    return 'review_needed'


def csynth(f, p):
    ft = f.get('finding_type'); sev = (f.get('severity') or 'MEDIUM').upper()
    if ft == 'compound_risk':
        return 'risk'
    if ft == 'directional_mismatch':
        a = int((f.get('evaluator_agreement') or '0-0').split('-')[0] or 0); isV = a >= 3
        d = f.get('directionality') or ''
        adv = 'tenant' if d == 'tenant_unprotected' else 'landlord' if d == 'landlord_unprotected' else None
        if not adv or p == 'neutral':
            return 'review_needed'
        if adv != p:
            return 'addressed'
        return 'risk' if isV else 'review_needed'
    if ft == 'cross_coverage_relief':
        return 'addressed'
    return 'risk' if sev in ('CRITICAL', 'HIGH') else 'improvement'


# P3 corroboration arm: an INDEPENDENT element-level signal beyond the LP-rollup tie —
# a single element with a genuine severe evaluator distance, OR a critical element whose
# merged verdict is missing/disputed. (Directional only at n=2.)
def p3_corroborated(a):
    for e in (a.get('element_verdicts') or []):
        evs = [ev.get('verdict') for ev in (e.get('evaluator_verdicts') or [])]
        _, md = severity(evs)
        crit = (e.get('criticality') or '').lower() in ('critical', 'high')
        mv = e.get('verdict')
        label = e.get('element_label') or e.get('element_id') or '?'
        if md >= 4:
            return True, 'element-level severe distance (%s)' % label
        if crit and mv in ('missing', 'disputed'):
            return True, 'critical element %s (%s)' % (mv, label)
    return False, 'no independent element dispute/critical-defect'


RUNS = {'030920': r'05 Lease Analyzer/results/lease_review_20260602_030920_d0e19e/tenant_0/pipeline_results.json',
        '181402': r'05 Lease Analyzer/results/lease_review_20260601_181402_2d1700/tenant_0/pipeline_results.json'}
P = 'tenant'
HIGHMAT = ('high', 'medium', 'moderate', 'material')

for lbl, pth in RUNS.items():
    d = json.load(open(pth, encoding='utf-8')); ca = d['coverage_assessment']; cpf = d.get('cross_provision_findings', []) or []
    pr = []
    for a in ca:
        st = a.get('coverage_state') or ''
        if st == 'not_applicable':
            continue
        if cons_bucket(a, P) == 'risk' and hf(a):
            pv = provenance(a); corro, why = p3_corroborated(a)
            pr.append(dict(kind='coverage', id=a.get('issue_area_id'), tie=pv['tie_derived_severe'],
                           sev_prod=pv['sev_prod'], sev_opt=pv['sev_opt'], cons_src=pv['consequence_source'],
                           mat=pv['assessed_materiality'], corro=corro, why=why))
    for f in cpf:
        if csynth(f, P) == 'risk' and (f.get('severity') or '').upper() == 'HIGH':
            pr.append(dict(kind='synthesis', id=f.get('finding_id') or f.get('finding_type'), tie=False,
                           sev_prod='n/a', sev_opt='n/a', cons_src='synthesis_high', mat='HIGH', corro=True, why='synthesis HIGH'))
    base = len(pr); cov = [m for m in pr if m['kind'] == 'coverage']; syn = [m for m in pr if m['kind'] == 'synthesis']
    print('================ RUN %s : Priority Risks baseline = %d (coverage=%d, synthesis-HIGH=%d) ================' % (lbl, base, len(cov), len(syn)))
    print('  --- coverage PR members (the only members any policy can move) ---')
    for m in cov:
        tag = 'TIE-DERIVED' if m['tie'] else 'genuine-severe'
        print('    %-7s sev_prod=%-6s sev_opt=%-6s %-12s cons=%-26s mat=%-12s P3corro=%-5s [%s]' % (
            m['id'], m['sev_prod'], m['sev_opt'], tag, m['cons_src'], m['mat'], m['corro'], m['why']))

    def hm(m):
        return m['mat'] in HIGHMAT

    masq = [m['id'] for m in cov if m['tie']]
    print('  --- POLICY RESULTS (PR count / leaving / displayed basis / genuine-demotions / residual masquerade) ---')
    print('  P4 baseline    : PR=%d | leaving=[] | basis(tie members)="severe disagreement" (FALSE) | demoted=[] | masquerade=%s' % (base, masq))
    p1_leave = [m['id'] for m in cov if m['tie']]
    p1_dem = [m['id'] for m in cov if m['tie'] and hm(m)]
    print('  P1 provenance  : PR=%d | leaving=%s | basis=removed (no independent PR rule) | demoted-genuine-assessed-high=%s | masquerade=[]' % (base - len(p1_leave), p1_leave, p1_dem))
    p2_relabel = [(m['id'], m['mat']) for m in cov if m['tie'] and hm(m)]
    p2_leave = [m['id'] for m in cov if m['tie'] and not hm(m)]
    print('  P2 consequence : PR=%d | leaving=%s | basis(tie+assessed-high)="high assessed consequence" | demoted-genuine=%s | masquerade=[]  RELABELED=%s' % (base - len(p2_leave), p2_leave, p2_leave, p2_relabel))
    p3_leave = [m['id'] for m in cov if m['tie'] and not (hm(m) and m['corro'])]
    p3_dem = [m['id'] for m in cov if m['id'] in p3_leave and hm(m)]
    p3_keep_tie = [m['id'] for m in cov if m['tie'] and hm(m) and m['corro']]
    print('  P3 combined    : PR=%d | leaving=%s | retained-tie(corroborated)=%s | demoted-genuine-assessed-high=%s | masquerade=[]' % (base - len(p3_leave), p3_leave, p3_keep_tie, p3_dem))
    print()
