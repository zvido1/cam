"""Per-run provider preflight. Step 517, designed at Step 516.

WHY A RUN NEEDS ITS OWN CHECK
-----------------------------
The boot assertion runs once per container, and a container lives for days. A
verdict taken at 09:00 carries a run submitted at 15:00 into discovering a
provider failure one LP at a time, via fallback, silently. **That is the
2026-08-26 shape: the runs completed.** A cached boot verdict reproduces it
exactly, which is why this re-checks rather than reading `startup_health`.

Cost: EIGHT calls against a run's ~96, not the seven estimated at Step 516. The
chains cover every seat's full fallback path, which includes `openai:gpt-5.4` and
`mistral:mistral-large-latest` -- neither is in the Step-504 TARGETS list, because
that list checks the models a run USES and this checks the models a run could
FALL BACK TO. Measured, not estimated.

It BLOCKS rather than racing -- a verdict arriving mid-pipeline is the behaviour
this exists to replace.

The 5-minute TTL keeps a batch of tenants from probing once per tenant while
shrinking the staleness window from hours to minutes. It is deliberately NOT the
boot cache, which has no expiry at all; that absence is the bug.

LAYERING
--------
This lives beside `tools/check_models.py` and imports only `cam.core` and that
module. `cam/` must never import from `05 Lease Analyzer/app/` -- Step 461
established layering tests for exactly this direction -- so the pipeline entry
can call this, and the app passes a fresh verdict in when it has one.
"""
import os
import sys
import threading
import time
from datetime import datetime, timezone

CAM_ROOT = r"C:/Users/Owner/OneDrive/CAM"
if CAM_ROOT not in sys.path:
    sys.path.insert(0, CAM_ROOT)

TTL_SEC = 300  # 5 minutes. See the module note above.

_CACHE = {"at": 0.0, "result": None}
_LOCK = threading.Lock()


class PreflightRefused(Exception):
    """Raised when the panel cannot be assembled at all.

    Carries a user-facing `message` and the machine-readable `detail`.
    """

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


def _chains():
    """(role -> ordered candidate models) for every seat a run depends on.

    Built from the pipeline's own constants, not restated here, so a change to
    the lineup cannot leave this behind.
    """
    from cam.adapters.lease_review.lease_coverage_305 import (
        EVALUATOR_LINEUP_305, _SHARED_FALLBACK_POOL,
    )
    from cam.adapters.lease_review.model_config import (
        EXTRACTOR_PRIMARY, EXTRACTOR_FALLBACK,
    )
    pool = [(p, m) for p, m, _lbl in _SHARED_FALLBACK_POOL]
    out = {}
    for role, cfg in EVALUATOR_LINEUP_305.items():
        chain = [(cfg["provider"], cfg["model"])]
        chain += [(p, m) for p, m, _lbl in (cfg.get("own_chain") or [])]
        chain += pool
        seen, ordered = set(), []
        for c in chain:
            if c not in seen:
                seen.add(c)
                ordered.append(c)
        out["evaluator_%s" % role] = ordered
    out["extractor"] = [tuple(EXTRACTOR_PRIMARY), tuple(EXTRACTOR_FALLBACK)]
    return out


def _probe(candidates):
    """Live-probe each distinct model once. Returns {(provider, model): ok}."""
    from tools.check_models import try_call
    seen = {}
    for prov, model in candidates:
        if (prov, model) in seen:
            continue
        # try_call already retries 3x with 2s/8s backoff (Step 514), so a single
        # transient does not decide a run's fate.
        seen[(prov, model)] = try_call(prov, model)["raw_error"] is None
    return seen


def evaluate(chains: dict, ok: dict) -> dict:
    """Pure decision. No I/O, so every branch is testable without a network.

    proceed        -- every seat's PRIMARY is available
    proceed_marked -- a primary is down but a substitute exists
    refuse         -- a seat has NO available candidate at all
    """
    substituted, unavailable, detail = [], [], {}
    for seat, chain in sorted(chains.items()):
        primary = chain[0]
        avail = [c for c in chain if ok.get(c)]
        detail[seat] = {
            "primary": "%s:%s" % primary,
            "primary_ok": bool(ok.get(primary)),
            "available": ["%s:%s" % c for c in avail],
        }
        if not avail:
            unavailable.append(seat)
        elif not ok.get(primary):
            substituted.append(seat)

    if unavailable:
        decision = "refuse"
    elif substituted:
        decision = "proceed_marked"
    else:
        decision = "proceed"
    return {"decision": decision, "substituted": substituted,
            "unavailable": unavailable, "seats": detail}


def _refusal_message(unavailable, seats) -> str:
    """Names the provider, says it is not the document's fault, and does NOT
    claim nothing was charged -- the preflight itself just spent calls, and a
    false reassurance about cost is the defect class this arc has spent fifteen
    steps removing."""
    bits = []
    for seat in unavailable:
        chain = seats.get(seat, {})
        bits.append("%s (named model: %s)" % (seat, chain.get("primary", "?")))
    return (
        "This analysis could not start. No model is currently available for: %s. "
        "Every candidate for that seat failed a live check just now -- the named model "
        "and every fallback configured for it. This is a provider outage on our side, "
        "NOT a problem with your document, and nothing about your lease caused it. "
        "No analysis was performed. Please try again shortly."
        % "; ".join(bits)
    )
    # Wording note: an earlier version said "the named model, its fallback, and the
    # shared pool". That is true of an evaluator seat and FALSE of the extractor,
    # whose chain is primary + fallback with no shared pool. A user-facing message
    # must not assert a structure that does not exist for the seat it names.


def preflight(ttl_sec: int = None, force: bool = False, _probe_fn=None,
              _chains_fn=None) -> dict:
    """Blocking per-run provider preflight. NEVER fails open.

    Returns a verdict dict; raises PreflightRefused only when a seat has no
    available model at all.

    ON ITS OWN FAILURE it returns decision="proceed_marked" with
    reason="preflight_error". That is deliberate and is the middle of three bad
    options: failing OPEN would claim health it never verified (the defect this
    arc keeps finding), and failing CLOSED would let a bug in THIS module block
    every run in the product. Marking says the honest thing -- we do not know --
    and mirrors `startup_health`'s `unknown`, which is likewise never a pass.
    """
    ttl = TTL_SEC if ttl_sec is None else ttl_sec
    now = time.time()

    with _LOCK:
        cached = _CACHE["result"]
        fresh = cached is not None and (now - _CACHE["at"]) < ttl
    if fresh and not force:
        out = dict(cached)
        out["from_cache"] = True
        out["cache_age_sec"] = round(now - _CACHE["at"], 1)
        if out["decision"] == "refuse":
            raise PreflightRefused(out["message"], out)
        return out

    try:
        chains = (_chains_fn or _chains)()
        ok = (_probe_fn or _probe)([c for chain in chains.values() for c in chain])
        verdict = evaluate(chains, ok)
        verdict["reason"] = None
    except Exception as e:
        verdict = {
            "decision": "proceed_marked", "substituted": [], "unavailable": [],
            "seats": {}, "reason": "preflight_error",
            "error": "%s: %s" % (type(e).__name__, str(e)[:300]),
        }

    verdict["checked_at"] = datetime.now(timezone.utc).isoformat()
    verdict["from_cache"] = False
    verdict["cache_age_sec"] = 0.0
    if verdict["decision"] == "refuse":
        verdict["message"] = _refusal_message(verdict["unavailable"], verdict["seats"])

    with _LOCK:
        _CACHE["at"] = time.time()
        _CACHE["result"] = dict(verdict)

    if verdict["decision"] == "refuse":
        raise PreflightRefused(verdict["message"], verdict)
    return verdict


def reset_cache():
    """Test hook. Not used in production paths."""
    with _LOCK:
        _CACHE["at"] = 0.0
        _CACHE["result"] = None
