"""
CAM Run Manager
Run directory creation and context management.
"""
import re
import sys
from pathlib import Path
from typing import Optional


def get_next_run_number(runs_dir: Path) -> int:
    """Find next available run number."""
    runs_dir.mkdir(parents=True, exist_ok=True)

    max_num = 0
    for item in runs_dir.iterdir():
        if item.is_dir():
            # Extract number from folder name
            match = re.match(r'^(\d+)', item.name)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)

    return max_num + 1


class RunContext:
    """Manages run directory and paths."""

    def __init__(self, runs_dir: Path, run_label: str, resume_run: Optional[int] = None):
        if resume_run is not None:
            self.run_number = resume_run
            self.run_dir = runs_dir / f"{resume_run} {run_label}"
            if not self.run_dir.exists():
                # Try alternative naming
                for item in runs_dir.iterdir():
                    if item.is_dir() and item.name.startswith(f"{resume_run} "):
                        self.run_dir = item
                        break
            if not self.run_dir.exists():
                print(f"ERROR: Could not find run folder for run {resume_run}")
                sys.exit(1)
            print(f"[RunContext] Resuming run {resume_run}: {self.run_dir}")
        else:
            self.run_number = get_next_run_number(runs_dir)
            self.run_dir = runs_dir / f"{self.run_number} {run_label}"
            print(f"[RunContext] Creating new run {self.run_number}: {self.run_dir}")

        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir = self.run_dir / "outputs"
        self.logs_dir = self.run_dir / "logs"
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
