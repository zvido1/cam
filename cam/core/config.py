"""
CAM Core Configuration
Environment loading, path resolution, shared constants.
"""
import os
from pathlib import Path

# Root of the CAM project (parent of cam/ package)
# cam/core/config.py -> cam/core -> cam -> CAM_ROOT
CAM_ROOT = Path(__file__).parent.parent.parent.resolve()


def load_env_file(env_path: str) -> None:
    """Load environment variables from a .env file."""
    p = Path(env_path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        # Override empty values — setdefault would preserve empty strings
        if not os.environ.get(k):
            os.environ[k] = v


def find_and_load_env(search_paths: list = None) -> bool:
    """Find and load the first available .env file from candidate paths.
    Returns True if a file was loaded, False otherwise."""
    if search_paths is None:
        # Default search paths
        search_paths = [
            CAM_ROOT / ".env",
            Path.home() / "OneDrive" / "DoubleCheck" / "doublecheck-api" / "api_keys" / ".env",
        ]
    for p in search_paths:
        p = Path(p)
        if p.exists():
            load_env_file(str(p))
            return True
    return False


def setup_openrouter():
    """Configure OpenRouter environment if API key is available."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        os.environ["OPENROUTER_DRY_RUN"] = "0"
