#!/usr/bin/env python3
"""Prepare fresh jointly disjoint continual Math/MMLU-Pro data without downloads."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from improving.continual_data import prepare_joint

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent-root', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--seed-file', required=True)
    args = parser.parse_args()
    result = prepare_joint(args.parent_root, args.output_root, args.seed_file)
    print(json.dumps({'replacement_count': result['replacement_count'], 'output_root': args.output_root}))

if __name__ == '__main__':
    main()
