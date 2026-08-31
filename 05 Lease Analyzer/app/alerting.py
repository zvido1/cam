"""Provider-health alerting. Step 512.

KEYS ON THE PER-MODEL SET, NEVER THE SUMMARY
--------------------------------------------
Step 507 left production reporting `unhealthy` for one target while six were
fine. A summary status says "red"; the set says WHICH target moved. It also
survives the case that actually matters -- a new failure arriving while an old
one is unfixed -- which a summary cannot distinguish at all.

TRIGGERS (Step 505 design)
--------------------------
LOUD:
  * a model goes healthy -> unhealthy and STAYS there for two consecutive checks
  * any `listed=False`, immediately, no consecutive requirement -- a retirement
    is never transient
  * any installed SDK version changing between checks, even when every call
    passes. That is the 2026-08-26 signal, visible BEFORE it breaks anything.

SILENT: everything else. Alert on state CHANGE, not on state -- a target already
alerted on and still failing produces nothing further.

ANTI-NOISE
----------
Step 504's model check reported the live extractor broken because the probe
budget was 16 tokens. Shipped, that is a daily false alarm, and a monitor that
cries wolf is worse than none because the next real failure gets ignored. The
two-consecutive rule and the alert-on-change rule both exist for that.

COLD START
----------
With no prior state, this is SILENT and merely records the baseline. A first
boot must never alert: every model would look like a change from nothing.
"""
import io
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Where the previous state lives. See STATE PERSISTENCE in the module notes below
# and the caveat recorded in build_log/512_code_status.md -- on Railway this
# directory is EPHEMERAL and does not survive a redeploy.
STATE_DIR = os.getenv("CAM_ALERT_STATE_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "telemetry")
STATE_PATH = os.path.join(STATE_DIR, "provider_alert_state.json")

_ALERT_EMAIL_ENV = "CAM_ALERT_EMAIL"


# ── state ────────────────────────────────────────────────────────────────────

def load_state(path: str = None) -> dict:
    """Previous state, or {} when there is none. A missing/corrupt file is a COLD
    START, which is silent -- never an alert, never an exception."""
    p = path or STATE_PATH
    try:
        if os.path.exists(p):
            return json.load(io.open(p, encoding="utf-8")) or {}
    except Exception as e:
        logger.warning("[alerting] unreadable state at %s (%s) -- treating as cold start", p, e)
    return {}


def save_state(state: dict, path: str = None) -> bool:
    p = path or STATE_PATH
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        io.open(p, "w", encoding="utf-8").write(json.dumps(state, indent=2, default=str))
        return True
    except Exception as e:
        logger.error("[alerting] could not persist state to %s: %s", p, e)
        return False


def _model_key(row: dict) -> str:
    return "%s:%s" % (row.get("provider"), row.get("model"))


# ── the decision, as a pure function so it can be tested without a network ────

def evaluate(models: list, sdk_versions: dict, prior: dict) -> tuple:
    """Return (alerts, new_state).

    `alerts` is a list of {"kind", "target", "detail"}. Empty means stay silent.
    Pure: no I/O, no sending. Every branch below is exercised in Step 512 Part C.
    """
    prior_models = (prior or {}).get("models") or {}
    prior_sdks = (prior or {}).get("sdk_versions") or {}
    cold_start = not prior_models and not prior_sdks

    alerts, new_models = [], {}
    for row in (models or []):
        key = _model_key(row)
        was = prior_models.get(key) or {}
        callable_ = bool(row.get("callable"))
        listed = row.get("listed")
        # Duplicate targets (the gate model is also role A's fallback) collapse to
        # the worst observation rather than the last one written.
        prev_new = new_models.get(key)
        if prev_new and (prev_new["healthy"] is False):
            callable_ = callable_ and prev_new["healthy"]

        healthy = callable_ and listed is not False
        consecutive = (was.get("consecutive_unhealthy") or 0) + 1 if not healthy else 0

        if not cold_start:
            # (a) retirement -- immediate, no consecutive requirement, but still
            #     only on CHANGE so it does not re-fire every check.
            if listed is False and was.get("listed") is not False:
                alerts.append({
                    "kind": "delisted", "target": key,
                    "detail": "no longer listed by the provider (role: %s). A retirement is "
                              "never transient." % row.get("role"),
                })
            # (b) healthy -> unhealthy, on the FIRST confirmed failure.
            #     Step 514 replaced "two consecutive checks" with retry-within-the-run
            #     (tools/check_models.try_call: 3 attempts, 2s then 8s backoff). The old
            #     rule was written with no cadence in mind: at the daily cadence Step 513
            #     costed it meant up to 48 HOURS before an outage was reported, and Step
            #     512 measured that state does not survive a redeploy so the second check
            #     often never happened. The transient absorption now lives in the probe,
            #     where it costs seconds instead of a day.
            #     Still fires only on the healthy -> unhealthy TRANSITION, so a known
            #     failure does not re-alert on every later check.
            #     SUPPRESSED while delisted: a delisted model is also unhealthy, and
            #     without this it fires a SECOND message saying nothing new. Step 512
            #     Part C caught exactly that -- the cry-wolf failure this design exists
            #     to prevent, produced by the design itself.
            elif not healthy and was.get("healthy") is not False and listed is not False:
                alerts.append({
                    "kind": "unhealthy", "target": key,
                    "detail": "unhealthy (role: %s). Probe retried %s time(s) before "
                              "reporting. raw: %s"
                              % (row.get("role"), row.get("attempts_made", "?"),
                                 (row.get("raw_error") or "")[:200]),
                })

        new_models[key] = {
            "healthy": healthy, "listed": listed, "callable": callable_,
            "consecutive_unhealthy": consecutive, "role": row.get("role"),
        }

    # (c) an SDK version change, even when every call passes. The 2026-08-26 signal.
    if not cold_start:
        for name, now in sorted((sdk_versions or {}).items()):
            before = prior_sdks.get(name)
            if before is not None and before != now:
                alerts.append({
                    "kind": "sdk_change", "target": name,
                    "detail": "installed version changed %s -> %s. anthropic 1.x removing "
                              "`temperature` is what this trigger exists for." % (before, now),
                })

    new_state = {
        "models": new_models,
        "sdk_versions": dict(sdk_versions or {}),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "cold_start": cold_start,
        "last_alerts": alerts,
    }
    return alerts, new_state


# ── dispatch, which must record its own outcome ──────────────────────────────

def _format(alerts: list) -> tuple:
    kinds = sorted({a["kind"] for a in alerts})
    subject = "CAM provider alert: %s (%d)" % (", ".join(kinds), len(alerts))
    lines = ["CAM provider-health alert", ""]
    for a in alerts:
        lines.append("[%s] %s" % (a["kind"].upper(), a["target"]))
        lines.append("    %s" % a["detail"])
        lines.append("")
    if any(a["kind"] in ("sdk_change", "manifest_missing", "manifest_unreadable") for a in alerts):
        lines.append("An SDK version moving without anyone deciding it should is what broke "
                     "production on 2026-08-26: anthropic 1.x removed `temperature` from "
                     "Messages.create() and every Anthropic call failed for five days.")
        lines.append("")
    lines.append("This alert keys on the per-model set, not the summary status.")
    return subject, "\n".join(lines)


def dispatch(alerts: list, to_email: str = None) -> dict:
    """Send the alert and RECORD WHETHER IT SENT.

    Uses the Step-511 contract: `_send_email` returns
    {"sent", "channel", "reason", "attempts"} and this captures it. An alerting
    system that discards its own send result is the defect this step exists past
    -- it would report success while never alerting anyone, which is the shape
    Step 510 found in SendGrid, Step 497 in `is_fallback`, Step 502 in
    `api_error` and Step 508 in the gate's fail-open.

    Returns the dispatch record. Never raises: a failure to alert must not take
    down whatever called it.
    """
    if not alerts:
        return {"attempted": False, "sent": None, "reason": "no_alerts"}

    target = to_email or os.getenv(_ALERT_EMAIL_ENV) or ""
    if not target:
        rec = {"attempted": False, "sent": False, "channel": "none",
               "reason": "no_alert_recipient_configured", "alert_count": len(alerts)}
        logger.error("[alerting] %d alert(s) RAISED BUT NOT SENT: %s is unset",
                     len(alerts), _ALERT_EMAIL_ENV)
        return rec

    subject, body = _format(alerts)
    try:
        from app.notifications import _send_email
        result = _send_email(target, subject, body)
    except Exception as e:
        result = {"sent": False, "channel": "unknown",
                  "reason": "dispatch_exception: %s: %s" % (type(e).__name__, str(e)[:160])}

    rec = {
        "attempted": True,
        "sent": bool(result.get("sent")),
        "channel": result.get("channel"),
        "reason": result.get("reason"),
        "alert_count": len(alerts),
        "kinds": sorted({a["kind"] for a in alerts}),
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if rec["sent"]:
        logger.info("[alerting] %d alert(s) delivered via %s", rec["alert_count"], rec["channel"])
    else:
        # A failed alert must be visible where a human would look for it.
        logger.error("[alerting] %d alert(s) NOT DELIVERED: channel=%s reason=%s",
                     rec["alert_count"], rec["channel"], rec["reason"])
    return rec


def run(models: list, sdk_versions: dict, to_email: str = None, path: str = None) -> dict:
    """Evaluate, dispatch if warranted, persist. Returns a record for surfacing."""
    prior = load_state(path)
    alerts, new_state = evaluate(models, sdk_versions, prior)
    dispatch_rec = dispatch(alerts, to_email) if alerts else {
        "attempted": False, "sent": None, "reason": "no_alerts"}
    new_state["last_dispatch"] = dispatch_rec
    persisted = save_state(new_state, path)
    return {
        "cold_start": new_state["cold_start"],
        "alerts": alerts,
        "dispatch": dispatch_rec,
        "state_persisted": persisted,
    }


# ── sdk_change via a COMMITTED MANIFEST (Step 514) ───────────────────────────
#
# This closes the 2026-08-26 trigger with NO scheduler, NO volume, NO persistent
# state and NO provider call. The manifest lives in the repo, which survives a
# redeploy by construction -- that is what a repo is. The comparison runs at boot,
# which is WHEN the change happens: Railway re-resolves dependencies on every push.
#
# The baseline is generated FROM PRODUCTION, not from local. Step 507 measured
# local and production differing on 6 of 13 packages, with local the drifted one
# (it was even below its own declared floor for `anthropic`). A manifest built
# from a dev box would encode the wrong truth.

MANIFEST_PATH = os.getenv("CAM_DEPS_MANIFEST") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "deps.manifest.json")


def _installed_versions(names) -> dict:
    from importlib.metadata import version, PackageNotFoundError
    out = {}
    for n in names:
        try:
            out[n] = version(n)
        except PackageNotFoundError:
            out[n] = "NOT INSTALLED"
        except Exception as e:                                   # pragma: no cover
            out[n] = "ERROR: %s" % type(e).__name__
    return out


def check_sdk_manifest(path: str = None, installed: dict = None) -> list:
    """Compare installed versions against the committed manifest.

    Returns a list of alerts. Empty means the manifest matched -- and ONLY that.

    FAILS CLOSED, and the three not-OK outcomes are DISTINGUISHABLE:

        manifest matches      -> []                       (silent)
        version differs       -> kind="sdk_change"
        manifest missing      -> kind="manifest_missing"
        manifest unreadable   -> kind="manifest_unreadable"

    Step 512's `load_state` collapsed missing and corrupt into a silent cold
    start, which is fail-OPEN against missing a failure. That defect is
    deliberately not reproduced here: an absent baseline is not a pass, because
    "nothing to compare against" and "compared and matched" are different facts.
    """
    p = path or MANIFEST_PATH

    if not os.path.exists(p):
        logger.error("[alerting] deps manifest MISSING at %s -- cannot verify SDK versions", p)
        return [{
            "kind": "manifest_missing", "target": os.path.basename(p),
            "detail": "No dependency manifest at %s. SDK drift cannot be detected at all "
                      "until this is restored -- this is not a pass." % p,
        }]

    try:
        doc = json.load(io.open(p, encoding="utf-8"))
        expected = doc["packages"]
        if not isinstance(expected, dict) or not expected:
            raise ValueError("manifest has no usable `packages` mapping")
    except Exception as e:
        logger.error("[alerting] deps manifest UNREADABLE at %s: %s", p, e)
        return [{
            "kind": "manifest_unreadable", "target": os.path.basename(p),
            "detail": "Manifest at %s could not be parsed (%s: %s). Distinct from missing: the file "
                      "is present but unusable, so SDK drift is undetectable." % (
                          p, type(e).__name__, str(e)[:160]),
        }]

    now = installed if installed is not None else _installed_versions(expected.keys())
    alerts = []
    for name in sorted(expected):
        want, got = expected[name], now.get(name, "NOT INSTALLED")
        if want != got:
            alerts.append({
                "kind": "sdk_change", "target": name,
                # Both versions are reported and the direction is NOT inferred: version
                # strings do not reliably order (0.125.0 vs 1.2.0 is a major bump; 2.8.1
                # vs 2.54.0 is not what string comparison suggests). The reader gets the
                # facts and draws the conclusion.
                "detail": "expected %s, installed %s" % (want, got),
                "expected": want, "installed": got,
            })
    if alerts:
        logger.error("[alerting] SDK MANIFEST MISMATCH on %d package(s): %s",
                     len(alerts), ", ".join(a["target"] for a in alerts))
    else:
        logger.info("[alerting] SDK manifest matches installed (%d packages)", len(expected))
    return alerts
