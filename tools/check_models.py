"""Daily model availability check for the CAM lease pipeline.

WHY TWO CHECKS PER MODEL, NOT ONE
---------------------------------
On 2026-08-26 `anthropic` 1.x removed `temperature` from `Messages.create()`.
Every deployed Anthropic call failed for five days. **A models-list check would
not have caught it**: `claude-sonnet-4-6` was listed, available and being served
perfectly well to anyone calling it correctly. What broke was the SDK signature,
which only a real call with the pipeline's own parameters can detect.

So each model gets:

  1. LISTED   -- is it in the provider's models endpoint? Catches retirement,
                 renaming, and access revocation.
  2. CALLABLE -- does one tiny call THROUGH THE REAL ProviderRouter AND ADAPTER
                 PATH succeed? Catches SDK drift, parameter rejection, auth and
                 quota. Routed through ModelTarget -> ProviderRouter ->
                 _get_adapter -> adapter.call, exactly as lease_coverage_305
                 does at :464, because a hand-rolled client would test something
                 the pipeline does not do.

Neither subsumes the other. LISTED-but-not-CALLABLE is the 2026-08-26 failure.
CALLABLE-but-not-LISTED would be a soon-to-retire alias still being served.

RAW ERRORS ONLY
---------------
Failures print the raw exception type and message, never a classified label.
Step 502 established that `_classify_failure` matched the `_error:` substring
inside every wrapped provider exception and labelled a client-side `TypeError`
as `api_error` -- which sent an investigation to the billing dashboard for two
exchanges. This tool must not repeat that.

USAGE
    python tools/check_models.py            # human-readable
    python tools/check_models.py --json     # machine-readable, for scheduling later

Cost: one minimal call per model (max_output_tokens=256). Not free, but trivial.
This step does NOT schedule it and does NOT wire email.
"""
import argparse
import json
import os
import sys
import time
import traceback

CAM_ROOT = r"C:/Users/Owner/OneDrive/CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

KEYS_ENV = r"C:/Users/Owner/OneDrive/DoubleCheck/doublecheck-api/api_keys/.env"

# Output budget for the probe call. See the note at the ModelTarget below --
# this is a correctness floor, not a cost knob. Do not lower it.
PROBE_OUTPUT_TOKENS = 256

# (provider, model, role in the pipeline)
TARGETS = [
    ("anthropic", "claude-sonnet-4-6",          "panel role A (primary)"),
    ("anthropic", "claude-haiku-4-5-20251001",  "panel role A (own-chain fallback)"),
    ("openai",    "gpt-5.5",                    "panel role B (primary)"),
    ("xai",       "grok-4.3",                   "panel role C (primary)"),
    ("google",    "gemini-3.1-pro-preview",     "extractor (primary)"),
    ("google",    "gemini-2.5-pro",             "shared fallback pool"),
    ("anthropic", "claude-sonnet-4-20250514",   "document gate default"),
]


def bootstrap_env():
    loaded = []
    if os.path.exists(KEYS_ENV):
        for line in open(KEYS_ENV, encoding="utf-8"):
            k, _, v = line.strip().partition("=")
            k = k.strip()
            if k.endswith("_API_KEY"):
                os.environ[k] = v.strip().strip('"').strip("'")
                loaded.append(k)
    return loaded


def list_models(provider):
    """Return (ids, metadata_by_id, raw_error). Never raises."""
    try:
        if provider == "anthropic":
            from anthropic import Anthropic
            c = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), timeout=60.0)
            out, meta = [], {}
            for m in c.models.list(limit=1000):
                out.append(m.id)
                meta[m.id] = {k: str(v) for k, v in
                              (("display_name", getattr(m, "display_name", None)),
                               ("created_at", getattr(m, "created_at", None)),
                               ("type", getattr(m, "type", None))) if v is not None}
            return out, meta, None
        if provider in ("openai", "xai"):
            from openai import OpenAI
            if provider == "openai":
                c = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=60.0)
            else:
                c = OpenAI(api_key=os.getenv("XAI_API_KEY"),
                           base_url="https://api.x.ai/v1", timeout=60.0)
            out, meta = [], {}
            for m in c.models.list():
                out.append(m.id)
                meta[m.id] = {k: str(v) for k, v in
                              (("owned_by", getattr(m, "owned_by", None)),
                               ("created", getattr(m, "created", None))) if v is not None}
            return out, meta, None
        if provider == "google":
            from google import genai
            c = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
            out, meta = [], {}
            for m in c.models.list():
                mid = (m.name or "").replace("models/", "")
                out.append(mid)
                d = {}
                for attr in ("display_name", "version", "description"):
                    v = getattr(m, attr, None)
                    if v:
                        d[attr] = str(v)[:80]
                meta[mid] = d
            return out, meta, None
    except Exception as e:
        return None, None, "%s: %s" % (type(e).__name__, e)
    return None, None, "unknown provider %r" % provider


def try_call(provider, model):
    """One tiny call through the REAL router+adapter path. Returns a dict."""
    from cam.core.provider_router import ModelTarget, ProviderRouter, RouterConfig
    rec = {"served_model": None, "is_fallback": None, "elapsed_sec": None,
           "reply": None, "usage": None, "raw_error": None, "raw_error_type": None}
    t0 = time.time()
    try:
        target = ModelTarget(
            name="modelcheck-%s-%s" % (provider, model),
            provider=provider, model=model,
            # 256, not 16. A reasoning model spends its output budget thinking
            # before emitting text, so a too-small budget returns empty and the
            # adapter raises `google_empty_output: no extractable text`. Measured:
            # gemini-3.1-pro-preview FAILS at 16 and 64, SUCCEEDS at 256 and 1024.
            # At 16 this check reported the live extractor as broken -- a daily
            # false alarm, caught only because Part C forced a discrimination test.
            max_output_tokens=PROBE_OUTPUT_TOKENS,
            temperature=0.0,           # the parameter anthropic 1.x rejected
            timeout_sec=90.0,
        )
        # Single-target router: no fallback is possible, so a failure here is a
        # failure of THIS model rather than of the chain.
        router = ProviderRouter([target], RouterConfig())
        adapter = router._get_adapter(provider)
        raw = (adapter.call("Answer in one word.", "Reply with exactly: OK", target) or "").strip()
        rec.update({"served_model": model, "is_fallback": False,
                    "elapsed_sec": round(time.time() - t0, 2),
                    "reply": raw[:40], "usage": getattr(adapter, "last_usage", None)})
    except Exception as e:
        rec.update({"elapsed_sec": round(time.time() - t0, 2),
                    "raw_error_type": type(e).__name__,
                    "raw_error": str(e)[:400],
                    "traceback_tail": traceback.format_exc()[-400:]})
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description="Daily model availability check")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)

    keys = bootstrap_env()
    listings, list_errors = {}, {}
    for prov in sorted({p for p, _, _ in TARGETS}):
        ids, meta, err = list_models(prov)
        listings[prov] = (ids, meta)
        if err:
            list_errors[prov] = err

    rows = []
    for provider, model, role in TARGETS:
        ids, meta = listings.get(provider, (None, None))
        listed = None if ids is None else (model in ids)
        call = try_call(provider, model)
        rows.append({
            "provider": provider, "model": model, "role": role,
            "listed": listed,
            "list_error": list_errors.get(provider),
            "lifecycle": (meta or {}).get(model),
            "callable": call["raw_error"] is None,
            **call,
        })

    if args.json:
        print(json.dumps({"keys_loaded": sorted(keys), "results": rows}, indent=2, default=str))
        return 0 if all(r["callable"] and r["listed"] is not False for r in rows) else 1

    print("CAM daily model check")
    print("=" * 96)
    for prov, err in sorted(list_errors.items()):
        print("  !! models-list for %s FAILED: %s" % (prov, err))
    print("%-10s %-27s %-7s %-9s %-8s %s" % ("provider", "model", "listed", "callable", "elapsed", "role"))
    print("-" * 96)
    for r in rows:
        print("%-10s %-27s %-7s %-9s %-8s %s" % (
            r["provider"], r["model"][:27],
            {True: "yes", False: "NO", None: "?"}[r["listed"]],
            "yes" if r["callable"] else "NO",
            ("%.2fs" % r["elapsed_sec"]) if r["elapsed_sec"] is not None else "-",
            r["role"]))
    bad = [r for r in rows if not r["callable"] or r["listed"] is False]
    print()
    if not bad:
        print("ALL %d MODELS LISTED AND CALLABLE." % len(rows))
    else:
        print("%d OF %d TARGETS FAILED -- raw errors below, unclassified:" % (len(bad), len(rows)))
        for r in bad:
            print()
            print("  %s:%s  (%s)" % (r["provider"], r["model"], r["role"]))
            print("     listed   : %s" % r["listed"])
            print("     callable : %s" % r["callable"])
            if r["raw_error"]:
                print("     RAW ERROR (%s): %s" % (r["raw_error_type"], r["raw_error"]))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
