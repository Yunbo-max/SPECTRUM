#!/usr/bin/env python3
"""Acquire native ARC-AGI-3 games and freeze their exact local identities."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from improving.arc3 import load_config, prepare, verify_assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/multidomain/arc3.json')
    parser.add_argument('--split-file', help='Explicit train/calibration/eval game-ID lists; new data_dir only')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    config = load_config(args.config)
    seed = Path(config['seed_file'])
    if not args.verify_only:
        seed.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(seed, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, 'w') as stream:
                json.dump({'schema': 1, 'seed': secrets.randbelow(2**31)}, stream)
                stream.write('\n')
        if seed.stat().st_mode & 0o077:
            raise ValueError('Private seed file permissions must be 0600')
        existing = json.loads(seed.read_text())
        if type(existing.get('seed')) is not int or not 0 <= existing['seed'] < 2**31:
            raise ValueError('Existing shared seed is outside [0,2**31); preserve it and use a new study seed_file')
    manifest = verify_assets(config) if args.verify_only else prepare(config, args.split_file)
    print(json.dumps({'status': 'assets_verified', 'splits': manifest['splits'],
                      'scope': manifest['scope'], 'llm_execution': False}, indent=2))


if __name__ == '__main__':
    main()
