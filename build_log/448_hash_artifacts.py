"""independent post-run validation, not emitted by the sanctioned harness

Read-only against run outputs. Records SHA-256 of every Step 447 output artifact and the
sidecar. Opens files in binary read mode only; never writes to a run artifact.
"""
import hashlib
import sys
from pathlib import Path

ARTIFACTS = [
    "build_log/431_selection_measurement_sidecar.json",
    "build_log/431_runtime_seam_capture.json",
    "build_log/431_selection_measurement.md",
    "build_log/431_validation.json",
    "build_log/431_repository_seam_check.json",
    "build_log/431_fatal_run_error.json",
]

label = sys.argv[1] if len(sys.argv) > 1 else "RECORD"
print("| artifact | bytes | SHA-256 |")
print("|---|---|---|")
for a in ARTIFACTS:
    p = Path(a)
    if not p.exists():
        print("| `%s` | -- | **NOT PRODUCED** |" % a)
        continue
    b = p.read_bytes()
    print("| `%s` | %d | `%s` |" % (a, len(b), hashlib.sha256(b).hexdigest()))
