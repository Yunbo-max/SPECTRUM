#!/usr/bin/env python3
"""Evaluate one predeclared decoding policy on retained native MBPP students."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
DECODERS = {
    'cool': {'temperature': .6, 'top_p': .95, 'top_k': 0},
    'warm': {'temperature': 1., 'top_p': .95, 'top_k': 0},
    'ssd_recipe': {'temperature': 1.5, 'top_p': .8, 'top_k': 20},
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--decoder', choices=DECODERS, required=True)
    p.add_argument('--samples', type=int, default=64)
    p.add_argument('--sequence-batch-size', type=int, default=1)
    p.add_argument('--backend', choices=('docker', 'local'), default='docker')
    p.add_argument('--allow-unsafe-local', action='store_true')
    p.add_argument('--resume', action='store_true')
    args = p.parse_args()
    if args.samples != 64 or args.sequence_batch_size < 1:
        p.error('This fixed decoder audit uses 64 samples and a positive batch size')
    if args.backend == 'local' and not args.allow_unsafe_local:
        p.error('Local execution requires --allow-unsafe-local')
    from improving.longitudinal import evaluate_checkpoints
    from improving.data import read_jsonl
    from improving.utils import atomic_json
    source = Path(args.run_dir).resolve()
    tasks = source / 'tasks/eval.jsonl'
    if len(read_jsonl(tasks)) != 500:
        raise ValueError('Decoder audit requires the same 500 MBPP test tasks')
    generation = {**DECODERS[args.decoder], 'max_prompt_tokens': 1024,
                  'max_new_tokens': 512, 'batch_size': args.sequence_batch_size,
                  'sequence_batch_size': args.sequence_batch_size,
                  'task_batch_size': args.sequence_batch_size}
    result = evaluate_checkpoints(source, args.output_dir, samples=64, rounds=[5],
        methods=['plain', 'ssd', 'spectral_soft'], eval_tasks_path=tasks,
        evaluation_overrides={'backend': args.backend, 'allow_unsafe_local': args.allow_unsafe_local},
        generation_overrides=generation, bootstrap_samples=2000, resume=args.resume)
    if result['status'] != 'completed':
        print(json.dumps(result, indent=2))
        return 2
    atomic_json(Path(args.output_dir) / 'transfer_complete.json', {
        'status': 'completed', 'benchmark': 'mbpp', 'source_run': str(source),
        'student_round': 5, 'task_count': 500, 'samples_per_task': 64,
        'training_on_target': False, 'calibration_on_target': False,
        'generation': generation, 'decoder_id': args.decoder,
        'evaluation_protocol': 'MBPP_original_tests_decoder_robustness',
        'results': result})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
