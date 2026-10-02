#!/usr/bin/env python3
"""Prepare pinned final-study data only; never load models or run benchmark code."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from improving.final_data import prepare_final_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=Path("configs/final/assets.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/final"))
    seeds = parser.add_mutually_exclusive_group(required=True)
    seeds.add_argument("--split-seed", type=int, help="Private predeclared data selection seed; no public default")
    seeds.add_argument("--seed-file", type=Path, help="Private JSON seed manifest with integer data_seed")
    args = parser.parse_args()
    seed = args.split_seed
    if args.seed_file:
        values = json.loads(args.seed_file.read_text(encoding="utf-8"))
        seed = values.get("data_seed")
    if type(seed) is not int or seed < 0:
        parser.error("Supply a nonnegative integer --split-seed or data_seed in --seed-file")
    registry = prepare_final_data(args.assets, args.output_dir, split_seed=seed)
    # Do not print private seed values or sample identities to public logs.
    print(json.dumps({"protocol": registry["protocol"], "complete": registry["complete"],
        "counts": {name: entry["task_count"] for name, entry in registry["benchmarks"].items()},
        "registry": str((args.output_dir / "benchmark_registry.json").resolve())}))


if __name__ == "__main__":
    main()
