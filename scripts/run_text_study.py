#!/usr/bin/env python3
"""Run one complete math/QA method lineage, or inspect saved study results."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from improving.text_study import run_text_study, text_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--method', choices=['base', 'plain', 'ssd', 'spectral_soft'])
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--report', action='store_true')
    parser.add_argument('--evaluate-only', action='store_true')
    parser.add_argument('--checkpoint')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    if args.report:
        report = text_report(config)
    else:
        if not args.method:
            parser.error('--method is required unless --report is selected')
        report = run_text_study(config, args.method, resume=args.resume,
                                evaluate_only=args.evaluate_only, checkpoint=args.checkpoint)
    print(json.dumps({'domain': report['domain'],
                      'states': [{'method': r['method'], 'round': r['round'], 'status': r['status']}
                                 for r in report['rows']]}, indent=2))


if __name__ == '__main__':
    main()
