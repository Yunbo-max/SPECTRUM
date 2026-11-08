#!/usr/bin/env python3
"""Independent continual-gain case cg14: self_distill, qa -> math, retention.

Generated source only. Native execution requires the explicit --execute flag.
"""
from pathlib import Path
import runpy
import sys


if __name__ == "__main__":
    dispatch = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "run_continual_gains.py"),
        run_name="continual_gain_case_dispatch",
    )
    raise SystemExit(dispatch["main"](sys.argv[1:], fixed_case="cg14"))
