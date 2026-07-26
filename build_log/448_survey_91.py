"""independent post-run validation, not emitted by the sanctioned harness

Read-only against run outputs. COMPUTABILITY SURVEY ONLY: reports which fields exist in the
immutable Step-447 sidecar for each preregistered 9.1 criterion. Emits NO status, pass, fail,
satisfied or not-established judgment on any criterion -- that would be the prohibited
authorship (the 9.1 table must be COPIED FROM 431_validation.json, which does not exist).
"""
import json

d = json.load(open("build_log/431_selection_measurement_sidecar.json", encoding="utf-8"))

print("=== sidecar top-level keys ===")
print(sorted(d.keys()))

s = d["series"]["cand_01"]
print("\n=== series entry keys ===")
print(sorted(s.keys()))

p = s["canonical_panels"][0]
print("\n=== panel keys ===")
print(sorted(p.keys()))

r = p["per_role"]["A"]
print("\n=== per_role keys ===")
print(sorted(r.keys()))

j = r["judgment"]
print("\n=== judgment keys ===")
print(sorted(j.keys()))

f = j.get("value_applies_to_charge_basis_components")
print("\n=== a semantic field's shape ===")
print(json.dumps(f, indent=2)[:600])

print("\n=== attempts[0] keys (per-attempt provenance) ===")
print(sorted(r["attempts"][0].keys()))

t = d["certification_traces"][0]
print("\n=== certification_trace keys ===")
print(sorted(t.keys()))
print("\n=== per_candidate keys ===")
print(sorted(t["per_candidate"][0].keys()))

print("\n=== grounding / span / support field names anywhere in the sidecar ===")
names = set()


def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            names.add(k)
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)


walk(d)
for kw in ("span", "support", "quote", "resolve", "citation", "cited", "token",
           "verif", "complete", "agree", "candidate_id", "reason"):
    hits = sorted(n for n in names if kw in n.lower())
    print(f"  *{kw}*: {hits}")
