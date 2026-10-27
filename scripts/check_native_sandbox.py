#!/usr/bin/env python3
"""Qualify the native code boundary on the actual execution host."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from improving.native_sandbox import qualify_sandbox

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError("Preserve the existing receipt; use a new output path for requalification")
    result = qualify_sandbox()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "output": str(output)}))

if __name__ == "__main__":
    main()
