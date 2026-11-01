#!/usr/bin/env python3
"""Run the real-model gain calibration only; no SFT or benchmark execution.

Run on the user's qualified native host. Identity fallback is a controller result,
not evidence that the method improves the benchmark.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    from improving.data import assert_disjoint_splits, read_jsonl
    from improving.gain_pipeline import calibrate_learned_round
    from improving.modeling import load_model
    from improving.pipeline import (checkpoint_fingerprint, file_sha, load_config,
                                    record_stage, training_runtime_identity)
    from improving.utils import atomic_json, stable_hash
    import improving.pipeline as pipeline

    config = load_config(args.config)
    if config['methods'] != ['spectral_learned']:
        raise ValueError('Qualification requires a spectral_learned-only configuration')
    root = Path(args.output_dir)
    if root.resolve() == Path(config['output_dir']).resolve():
        raise ValueError('Use a separate qualification directory, not the experiment output root')
    splits = {key: read_jsonl(path) for key, path in config['data'].items()}
    if set(splits) != {'train', 'calibration', 'validation', 'eval'}:
        raise ValueError('Expected the existing four disjoint data splits')
    assert_disjoint_splits(splits)
    for key, count in config.get('data_limits', {}).items():
        if key not in splits or type(count) is not int or not 1 <= count <= len(splits[key]):
            raise ValueError(f'Invalid data_limits.{key}')
        ordered = sorted(splits[key], key=lambda item: item['task_id'])
        random.Random(config.get('data_seed', 42)).shuffle(ordered)
        splits[key] = ordered[:count]
    local_model = Path(config['model']['name'])
    model_files = checkpoint_fingerprint(local_model) if local_model.is_dir() else None
    identity = {
        'config': config,
        'data_hashes': {key: file_sha(path) for key, path in config['data'].items()},
        'source_hashes': {path.name: file_sha(path) for path in
                          Path(pipeline.__file__).parent.glob('*.py')},
        'qualification_script_sha256': file_sha(__file__),
        'runtime': training_runtime_identity(), 'local_model_fingerprint': model_files,
        'scope': 'round_one_gain_calibration_only_no_sft_no_evaluation',
    }
    manifest_path = root / 'qualification_manifest.json'
    if manifest_path.exists():
        if not args.resume:
            raise FileExistsError('Qualification exists; use --resume or a new directory')
        if json.loads(manifest_path.read_text()) != identity:
            raise ValueError('Qualification config, inputs, source or runtime changed')
    else:
        if root.exists() and any(root.iterdir()):
            raise ValueError('Existing qualification directory has no matching manifest')
        atomic_json(manifest_path, identity)
    with record_stage(root, 'model_loading'):
        model, tokenizer = load_model(config['model'])
    revision = getattr(model.config, '_commit_hash', None)
    model_identity = stable_hash([config['model'], revision, model_files])
    _, _, audit, provenance = calibrate_learned_round(
        model, tokenizer, splits['calibration'], splits['train'],
        config.get('calibration', {}), config.get('generation', {}), root,
        model_identity, seed=int(config.get('seed', 42)), round_index=1, resume=args.resume)
    receipt = {
        'status': 'calibration_completed', 'selected_identity': audit['selected_identity'],
        'fallback_reason': audit.get('fallback_reason'), 'model_identity': model_identity,
        'resolved_revision': revision, 'operator_sha256': provenance['operator_sha256'],
        'audit_sha256': file_sha(root / 'learned_gains.json'),
        'sft_executed': False, 'benchmark_evaluation_executed': False,
        'scientific_effectiveness': 'not_evaluated',
    }
    atomic_json(root / 'qualification_complete.json', receipt)
    print(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
