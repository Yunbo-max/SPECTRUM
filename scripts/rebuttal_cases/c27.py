#!/usr/bin/env python3
"""Standalone ICLR2027 case c27: 50 vs 40 reference control: fixed gain with 40 references."""
from pathlib import Path
import runpy
import sys

if __name__ == "__main__":
    if any(arg == "--case" or arg.startswith("--case=") for arg in sys.argv[1:]):
        raise SystemExit("This entrypoint has a fixed case ID; do not pass --case")
    runner = runpy.run_path(str(Path(__file__).resolve().parents[1] / "rebuttal_cases.py"), run_name="rebuttal_case_dispatch")
    raise SystemExit(runner["main"](["--case", "c27", *sys.argv[1:]]))
