#!/usr/bin/env python3
"""Native ARC-AGI-3 baseline, reference qualification and recursive action SFT."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from improving.arc3 import load_config
from improving.arc3_study import collect_reference, import_reference, run, status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/multidomain/arc3.json')
    commands = parser.add_subparsers(dest='command', required=True)
    baseline = commands.add_parser('baseline')
    baseline.add_argument('--split', choices=['train', 'eval'], default='train')
    baseline.add_argument('--resume', action='store_true')
    reference = commands.add_parser('collect-reference')
    reference.add_argument('--resume', action='store_true')
    imported = commands.add_parser('import-reference')
    imported.add_argument('--recording', required=True)
    imported.add_argument('--game-seed', type=int, default=0)
    train = commands.add_parser('run')
    train.add_argument('--method', choices=['plain', 'ssd', 'spectral_soft'], required=True)
    train.add_argument('--resume', action='store_true')
    commands.add_parser('status')
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == 'status':
        print(json.dumps(status(config), indent=2))
        return
    # One model process per ARC study root; OS lock releases on process exit.
    root = Path(config['output_dir'])
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.owner.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == 'baseline':
            result = run(config, method='base', resume=args.resume, baseline_split=args.split)
        elif args.command == 'collect-reference':
            result = collect_reference(config, resume=args.resume)
        elif args.command == 'import-reference':
            result = import_reference(config, args.recording, game_seed=args.game_seed)
        else:
            result = run(config, method=args.method, resume=args.resume)
        if result is not None:
            print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
