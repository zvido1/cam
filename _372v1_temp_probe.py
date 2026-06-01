"""372-V1 Part B probe: does gpt-5.5 accept temperature=0 in our actual call config?

Sends gpt-5.5 with our EXACT call shape (same max_completion_tokens as Stage 305,
no reasoning_effort) but with temperature=0 EXPLICITLY included.
Then repeats 5x to test convergence.

NOT changing the production adapter — just testing directly.
"""
import os, sys, json

KEYS_ENV = r"C:\Users\Owner\OneDrive\DoubleCheck\doublecheck-api\api_keys\.env"
for line in open(KEYS_ENV, encoding="utf-8"):
    k, _, v = line.strip().partition("=")
    if k.strip() == "OPENAI_API_KEY":
        os.environ["OPENAI_API_KEY"] = v.strip().strip('"').strip("'")

from openai import OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=120.0)

# Minimal prompt matching the Stage 305 call shape (system + user)
SYSTEM = "You are a structured data extractor."
USER = (
    "LP: LP-01 -- Rent & Payment Terms\n"
    "GOVERNING LAW: NY\n\n"
    "EXPECTED ELEMENTS (2 total):\n"
    '[{"element_id":"LP-01.base_rent","element_label":"Base rent is stated","must_be_explicit":true},'
    '{"element_id":"LP-01.payment_due_date","element_label":"Payment due date is stated","must_be_explicit":true}]\n\n'
    "LEASE PROVISION TEXT:\n"
    "Section 3.1. Base Rent. Tenant shall pay $10,000/month on the 1st of each month.\n\n"
    "Return a JSON array of exactly 2 verdict objects, one per element."
)

print("=== gpt-5.5 temperature probe ===")
print("Config: max_completion_tokens=3000, NO reasoning_effort, temperature=0 EXPLICITLY")
print()

results = []
for i in range(5):
    params = {
        "model": "gpt-5.5",
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}],
        "max_completion_tokens": 3000,
        "temperature": 0,   # ← explicitly setting temperature=0 (production adapter drops this)
    }
    try:
        resp = client.chat.completions.create(**params, timeout=60.0)
        content = resp.choices[0].message.content if resp.choices else ""
        finish_reason = resp.choices[0].finish_reason if resp.choices else "?"
        results.append({"sample": i, "verdict": "OK", "content_len": len(content or ""),
                        "finish_reason": finish_reason,
                        "content_hash": hash(content)})
        print(f"s{i}: OK finish={finish_reason} len={len(content or '')} "
              f"content={repr((content or '')[:120])}")
    except Exception as e:
        results.append({"sample": i, "verdict": "ERROR", "error": str(e)[:200]})
        print(f"s{i}: ERROR {str(e)[:200]}")

print()
print("=== Convergence check ===")
ok = [r for r in results if r["verdict"] == "OK"]
if ok:
    hashes = [r["content_hash"] for r in ok]
    unique = len(set(hashes))
    print(f"Successful calls: {len(ok)}/5")
    print(f"Unique outputs: {unique}/{len(ok)}")
    if unique == 1:
        print("VERDICT: IDENTICAL OUTPUTS → temperature=0 accepted AND honored → #1 (adapter over-drop)")
    elif unique <= 2:
        print("VERDICT: MOSTLY CONVERGED → temperature=0 likely honored → #1")
    else:
        print("VERDICT: HIGH VARIANCE despite temp=0 → model ignores temperature → #2")
else:
    print("All calls failed — likely API rejection")
    errors = [r.get("error","") for r in results if r.get("error")]
    for e in errors[:3]:
        print(f"  ERROR: {e}")
