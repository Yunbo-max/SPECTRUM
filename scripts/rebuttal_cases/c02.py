#!/usr/bin/env python3
"""Standalone ICLR 2027 rebuttal case c02: SPD-hard original seed43."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_iclr_rebuttal_cases import main
if __name__ == "__main__":
    raise SystemExit(main([sys.argv[1] if len(sys.argv)>1 else "preview", "--case", "c02", *sys.argv[2:]]))
