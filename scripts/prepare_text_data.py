#!/usr/bin/env python3
"""Explicit pinned data acquisition for the math/QA study (no model execution)."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from improving.text_tasks import prepare_text_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    result = prepare_text_data(config)
    print(json.dumps({'domain': config['domain'], 'counts': result['counts'],
                      'manifest': str(Path(config['data']['output_dir']) / 'manifest.json')}, indent=2))


if __name__ == '__main__':
    main()
