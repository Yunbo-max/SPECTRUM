#!/usr/bin/env python3
"""Standalone ICLR2027 rebuttal case c30 -- independent plan/run/status."""
from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    runner = runpy.run_path(str(Path(__file__).resolve().parents[1] / "rebuttal_cases.py"), run_name="rebuttal_case_dispatch")
    raise SystemExit(runner["main"](["--case", "c30", *sys.argv[1:]]))
