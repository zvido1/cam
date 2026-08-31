"""Step 517: the suite stays CALL-FREE.

`run_lease_coverage_only` now performs a blocking provider preflight before any
work. That is correct for a real run and wrong for a test: the suite runs on every
step, its output is quoted in every status file, and it must not spend money or
need network. Adding the preflight made it take 87s and fail 15 tests.

The bypass is recorded on the result (`run_preflight.decision == "skipped"`), so a
skipped preflight is never mistaken for a passed one.
"""
import os

os.environ.setdefault("CAM_SKIP_RUN_PREFLIGHT", "1")
