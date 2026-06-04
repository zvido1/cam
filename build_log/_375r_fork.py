"""Step 375-R READ-ONLY fork diagnostic — directional Pass-2 confirmation-count-as-severity.
Entirely from stored artifacts (_stage_data/synthesis_meta/{pass2_raw,pass2_integrity}); NO provider keys,
NO production change. Two questions:
  Q1 WHY does Role B (and A/C) change the vote count? genuine-semantic vs lost/integrity vs candidate-match
     vs routing/fallback vs unauditable.
  Q2 PRODUCT CONSEQUENCE: how many stable directional findings enter/leave Risk solely because the tally
     moved 3-0<->2-1 (candidate persists), and what the Risk headline would be if integrity-failed votes
     were 'not assessed' rather than silently non-confirming.
Compound is the stable control (mapped severity, not raw tally)."""
import json, os
from collections import Counter

RUNS = {
    "030920": "lease_review_20260602_030920_d0e19e", "0604": "lease_review_20260604_033046_52adbf",
    "s370r1": "lease_review_20260529_191130_s370r1", "s370r2": "lease_review_20260529_193136_s370r2",
    "s370r3": "lease_review_20260529_195234_s370r3", "370c_H1": "lease_review_20260530_231425_370c_H1",
    "370c_H2": "lease_review_20260530_233514_370c_H2", "370c_H3": "lease_review_20260530_235847_370c_H3",
}
SETS = [("current-code pair (030920->0604)", ["030920", "0604"]),
        ("s370r1/2/3 (same commit)", ["s370r1", "s370r2", "s370r3"]),
        ("370c_H1/2/3 (same commit)", ["370c_H1", "370c_H2", "370c_H3"])]


def load(lbl):
    d = json.load(open("05 Lease Analyzer/results/%s/tenant_0/pipeline_results.json" % RUNS[lbl], encoding="utf-8"))
    cpf = d.get("cross_provision_findings", []) or []
    direc = {}
    for f in cpf:
        if f.get("finding_type") == "directional_mismatch":
            key = tuple(sorted(f.get("implicated_lps") or []))
            direc[key] = {"sev": f.get("severity"), "agree": f.get("evaluator_agreement"),
                          "ev": f.get("evaluator_verdicts") or {}, "fid": f.get("finding_id")}
    sm = (d.get("_stage_data") or {}).get("synthesis_meta") or {}
    pi = sm.get("pass2_integrity") or {}
    pr = sm.get("pass2_raw") or {}
    # per-role: candidate_id -> verdict (from raw objects) for directional only
    raw_by_role = {}
    for role, info in pr.items():
        m = {}
        for v in (info.get("verdicts") or []):
            if isinstance(v, dict) and str(v.get("candidate_id", "")).startswith("Dir-"):
                m[v.get("candidate_id")] = v.get("verdict")
        raw_by_role[role] = dict(model=info.get("model"), completed=info.get("completed"), cand=m)
    return direc, pi, raw_by_role


def integ(pi, role):
    i = pi.get(role, {}) or {}
    return dict(unmatched=i.get("unmatched_directional", "?"), trunc=i.get("truncation_detected", "?"),
                parse=i.get("json_parse_success", "?"), status=i.get("status", "n/a(pre-370d)"),
                completed=i.get("completed", "?"), matched=i.get("matched_directional", "?"))


print("================ PER-RUN PASS-2 INTEGRITY (lost-vote / truncation / parse) ================")
for lbl in RUNS:
    direc, pi, raw = load(lbl)
    cells = []
    for r in ("A", "B", "C"):
        x = integ(pi, r)
        cells.append("%s[m=%s un=%s tr=%s parse=%s st=%s]" % (r, x["matched"], x["unmatched"], x["trunc"], x["parse"], x["status"]))
    print("  %-8s %s" % (lbl, "  ".join(cells)))

print("\n================ Q1+Q2: FORK PER SET ================")
for label, members in SETS:
    runs = {m: load(m) for m in members}
    direcs = {m: runs[m][0] for m in members}
    persist = set(direcs[members[0]])
    for m in members[1:]:
        persist &= set(direcs[m])
    print("\n#### SET: %s ####" % label)
    print("  persistent directional candidates (same implicated_lps across set): %d" % len(persist))

    sev_flip = 0; risk_cross = 0
    classes = Counter()
    risk_cross_detail = []
    for key in sorted(persist):
        sevs = {m: direcs[m][key]["sev"] for m in members}
        agrees = {m: direcs[m][key]["agree"] for m in members}
        if len(set(sevs.values())) == 1:
            continue
        sev_flip += 1
        # Risk routing for directional = 3-0 (ASSERT_SIGNAL). enters/leaves Risk iff 3-0 status changes.
        is_risk = {m: (agrees[m] == "3-0") for m in members}
        if len(set(is_risk.values())) > 1:
            risk_cross += 1
            risk_cross_detail.append((key, {m: agrees[m] for m in members}))
        # Classify the swing per role using integrity + raw presence
        for m in members:
            pass
        # Focus: classify EACH role whose verdict differs across the set
        for role in ("A", "B", "C"):
            verds = {m: direcs[m][key]["ev"].get(role) for m in members}
            if len(set(verds.values())) <= 1:
                continue
            # examine each run's integrity/raw for THIS candidate (matched by fid==candidate_id)
            verdict_kinds = set()
            lost_any = False
            routing = False
            model_seen = set()
            for m in members:
                pi = runs[m][1]; raw = runs[m][2]; fid = direcs[m][key]["fid"]
                ri = integ(pi, role)
                rr = raw.get(role, {})
                model_seen.add(rr.get("model"))
                has_obj = fid in rr.get("cand", {}) if fid else None
                ev = direcs[m][key]["ev"].get(role)
                if ev == "unclear":
                    # ambiguous in output; disambiguate via integrity + raw object presence
                    if (ri["unmatched"] not in (0, "?")) or ri["trunc"] is True or ri["parse"] is False or has_obj is False:
                        lost_any = True
                    elif has_obj is True:
                        verdict_kinds.add("unclear(genuine)")
                    else:
                        verdict_kinds.add("unclear(unauditable)")
                else:
                    verdict_kinds.add(ev)  # mismatch_confirmed / no_mismatch = genuine parsed verdict
                if rr.get("completed") is False:
                    routing = True
            if len({x for x in model_seen if x}) > 1:
                routing = True
            # final class for this role's swing on this finding
            genuine_verdicts = {v for v in verdict_kinds if v in ("mismatch_confirmed", "no_mismatch") or v == "unclear(genuine)"}
            if lost_any and len(genuine_verdicts) >= 1:
                classes["LOST/INTEGRITY vs genuine (mixed -> integrity-driven)"] += 1
            elif lost_any:
                classes["LOST/INTEGRITY (no-object/truncation/parse)"] += 1
            elif routing:
                classes["ROUTING/FALLBACK (model/completed differs)"] += 1
            elif len(genuine_verdicts) >= 2 or ("mismatch_confirmed" in verdict_kinds and "no_mismatch" in verdict_kinds):
                classes["GENUINE semantic verdict change"] += 1
            elif "unclear(unauditable)" in verdict_kinds:
                classes["UNAUDITABLE from stored artifacts"] += 1
            else:
                classes["GENUINE semantic verdict change"] += 1
    print("  directional findings that FLIP severity (persistent): %d" % sev_flip)
    print("  ... that ENTER/LEAVE Risk solely on 3-0<->non-3-0 tally (candidate persists): %d" % risk_cross)
    print("  Q1 role-swing classification (per role per flipped finding):")
    for k, v in classes.most_common():
        print("       %-52s %d" % (k, v))

    # Q2 counterfactual: per run, of directional findings NOT routed Risk (not 3-0), how many have a
    # NON-confirming vote that is a LOST vote vs a genuine no_mismatch -> "incomplete masquerading as MED/LOW".
    print("  Q2 counterfactual — current Risk-directional vs integrity-cleaned, per run:")
    for m in members:
        direc, pi, raw = runs[m]
        risk_now = sum(1 for k in direc if direc[k]["agree"] == "3-0")
        # integrity-failed votes anywhere this run?
        lost_roles = {r: integ(pi, r)["unmatched"] for r in ("A", "B", "C")}
        any_lost = any((x not in (0, "?")) for x in lost_roles.values())
        print("       %-8s directional-Risk(3-0)=%2d | per-role unmatched=%s | any lost vote this run: %s"
              % (m, risk_now, lost_roles, any_lost))
