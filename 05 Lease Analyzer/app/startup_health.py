"""Boot-time provider health assertion. Step 506.

WHY AT BOOT
-----------
On 2026-08-26 Railway rebuilt, pip re-resolved `anthropic` to 1.x, and
`Messages.create()` no longer accepted `temperature`. Every Anthropic call in
production failed client-side for five days and nothing said so.

**A rebuild is the only moment the installed SDK can change**, so a check that
runs at boot runs exactly when the risk materialises. Step 505 established that
neither the local model check nor the requirements drift test would have caught
that day: the model was listed and served fine, and `1.2.0` satisfied the
then-declared `>=0.78.0`. Only a real call from inside production would have.

WHAT IT RECORDS, AND WHY BOTH HALVES
------------------------------------
The call detects the break. **The recorded SDK versions name the cause** --
Step 501 spent two exchanges not knowing `anthropic` had moved, because no
artefact carried the version.

FAIL-CLOSED, BY CONSTRUCTION
----------------------------
Every defect in this arc is something returning success on a broken path:
`send_email` returning True when unconfigured; `is_fallback: False` on a stub no
model produced; `api_error` asserting a call reached the API. So:

  * the initial status is "unknown", which callers must treat as UNHEALTHY;
  * if the probe module fails to import, or the thread dies, the status STAYS
    "unknown" -- absence of a result is never a pass;
  * nothing here can set "healthy" except a completed check with zero failures.

THE APP STILL STARTS
--------------------
The check runs on a daemon thread, so boot is never delayed and a slow or
failing provider cannot stop the service coming up. Crash-on-failure was
rejected at Step 505: it converts a provider blip into an outage, and
`restartPolicyType = "on_failure"` would then loop it.
"""
import logging
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Every pinned runtime dependency whose version could silently change on rebuild.
_TRACKED_SDKS = (
    "anthropic", "openai", "google-genai", "httpx",
    "fastapi", "uvicorn", "python-docx", "PyMuPDF", "reportlab",
    "google-api-python-client", "google-auth", "python-dotenv", "python-multipart",
)

# Fail-closed initial state. "unknown" is NOT a pass.
_STATE = {
    "status": "unknown",
    "checked_at": None,
    "started_at": None,
    "elapsed_sec": None,
    "models": [],
    "sdk_versions": {},
    "failures": [],
    "error": None,
}
_LOCK = threading.Lock()


def get_state() -> dict:
    """Snapshot of the last completed check. `status` is one of:
    unknown (never ran, still running, or crashed -- treat as UNHEALTHY),
    healthy, unhealthy.
    """
    with _LOCK:
        return dict(_STATE)


def is_healthy() -> bool:
    """True ONLY on a completed check with zero failures."""
    with _LOCK:
        return _STATE["status"] == "healthy"


def _sdk_versions() -> dict:
    from importlib.metadata import version, PackageNotFoundError
    out = {}
    for name in _TRACKED_SDKS:
        try:
            out[name] = version(name)
        except PackageNotFoundError:
            out[name] = "NOT INSTALLED"
        except Exception as e:                                  # pragma: no cover
            out[name] = "ERROR: %s" % type(e).__name__
    return out


def _run_check():
    started = datetime.now(timezone.utc)
    with _LOCK:
        _STATE["started_at"] = started.isoformat()
    versions = _sdk_versions()

    rows, err = [], None
    try:
        # Single source of truth for targets and probe parameters -- the same
        # module Step 504 built and proved. An ImportError here leaves the status
        # at "unknown", which is correctly unhealthy.
        from tools.check_models import TARGETS, list_models, try_call

        listings = {}
        for prov in sorted({p for p, _, _ in TARGETS}):
            ids, meta, list_err = list_models(prov)
            listings[prov] = (ids, meta, list_err)

        for provider, model, role in TARGETS:
            ids, meta, list_err = listings.get(provider, (None, None, None))
            call = try_call(provider, model)
            rows.append({
                "provider": provider, "model": model, "role": role,
                "listed": None if ids is None else (model in ids),
                "list_error": list_err,
                "lifecycle": (meta or {}).get(model),
                "callable": call["raw_error"] is None,
                "served_model": call["served_model"],
                "is_fallback": call["is_fallback"],
                "elapsed_sec": call["elapsed_sec"],
                "raw_error_type": call["raw_error_type"],
                "raw_error": call["raw_error"],
            })
    except Exception as e:
        err = "%s: %s" % (type(e).__name__, e)
        logger.error("[startup_health] check could not run: %s", err)

    failures = [
        "%s:%s (%s)" % (r["provider"], r["model"],
                        r["raw_error_type"] or ("not listed" if r["listed"] is False else "?"))
        for r in rows if (not r["callable"]) or r["listed"] is False
    ]
    finished = datetime.now(timezone.utc)
    status = "unknown" if err or not rows else ("healthy" if not failures else "unhealthy")

    with _LOCK:
        _STATE.update({
            "status": status,
            "checked_at": finished.isoformat(),
            "elapsed_sec": round((finished - started).total_seconds(), 2),
            "models": rows,
            "sdk_versions": versions,
            "failures": failures,
            "error": err,
        })

    # Loud, per Step 505: an unhealthy or unknown result must not look like a log line
    # nobody reads. Raw errors only -- never the classifier, which Step 502 showed lies
    # about where a failure happened.
    if status == "healthy":
        logger.info("[startup_health] HEALTHY -- %d/%d models listed and callable",
                    len(rows), len(rows))
        print("[startup_health] HEALTHY: %d models OK | anthropic=%s google-genai=%s openai=%s"
              % (len(rows), versions.get("anthropic"), versions.get("google-genai"),
                 versions.get("openai")), flush=True)
    else:
        logger.error("[startup_health] %s -- failures=%s", status.upper(), failures or err)
        print("=" * 78, flush=True)
        print("[startup_health] PROVIDER HEALTH %s" % status.upper(), flush=True)
        print("   SDK versions: %s" % versions, flush=True)
        if err:
            print("   CHECK DID NOT RUN: %s" % err, flush=True)
        for r in rows:
            if r["callable"] and r["listed"] is not False:
                continue
            print("   %s:%s (%s)  listed=%s callable=%s"
                  % (r["provider"], r["model"], r["role"], r["listed"], r["callable"]), flush=True)
            if r["raw_error"]:
                print("      RAW ERROR (%s): %s" % (r["raw_error_type"], r["raw_error"]), flush=True)
        print("=" * 78, flush=True)


def start_background_check() -> None:
    """Launch the check on a daemon thread. Never blocks boot, never raises."""
    try:
        threading.Thread(target=_run_check, name="startup-health",
                         daemon=True).start()
        logger.info("[startup_health] background check started (status stays 'unknown' until it completes)")
    except Exception as e:                                      # pragma: no cover
        logger.error("[startup_health] could not start check thread: %s", e)
