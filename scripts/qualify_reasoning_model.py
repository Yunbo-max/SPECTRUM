#!/usr/bin/env python3
"""Qualify the real 27B text path on prepared native development examples.

This Local-only command loads weights, generates, calibrates, takes one LoRA
optimizer step, saves a new checkpoint and reloads it. It produces no benchmark
score and never touches an existing scientific trajectory. Run through the
admitted native GPU harness after explicit model/data preparation.
"""
from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/multidomain/text_math.json')
    parser.add_argument('--asset-manifest', default='data/multidomain/reasoning-model.json')
    parser.add_argument('--output-dir', default='runs/qualification/qwen38-27b-math')
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text())
    if config['model'].get('loader') != 'qwen3_5_text':
        raise ValueError('This qualification command is for the declared qwen3_5_text path')
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)  # a prior attempt is immutable

    import torch
    from improving.generation import generate_to_file
    from improving.modeling import load_model, render_prompt
    from improving.pipeline import (_calibrate, _operators, checkpoint_fingerprint,
                                    training_runtime_identity)
    from improving.spectral import folded_operators, target_modules
    from improving.text_tasks import private_seed, verify_prepared_data
    from improving.training import train_on_records
    from improving.utils import atomic_json, stable_hash

    start = time.monotonic()
    measurement_device = None
    source_paths = ('scripts/qualify_reasoning_model.py', 'src/improving/modeling.py',
                    'src/improving/spectral.py', 'src/improving/training.py',
                    'src/improving/calibration.py', 'src/improving/generation.py',
                    'src/improving/pipeline.py', 'src/improving/text_tasks.py')
    receipt = {'schema': 1, 'status': 'running', 'scientific_result': False,
               'purpose': 'native_model_interface_and_one_step_qualification',
               'config_sha256': file_sha(config_path),
               'model': config['model'],
               'source_sha256': {path: file_sha(ROOT / path) for path in source_paths},
               'checks': {}, 'resource_measurement_scope': 'selected_native_development_examples',
               'formal_max_shape_capacity_qualified': False}
    receipt_path = output / 'qualification.json'
    atomic_json(receipt_path, receipt)
    try:
        if not torch.cuda.is_available():
            raise RuntimeError('Native 27B qualification requires the admitted CUDA device')
        if not torch.cuda.is_bf16_supported():
            raise RuntimeError('Native 27B qualification requires BF16-capable CUDA')
        if not str(config['model'].get('device', 'cuda')).startswith('cuda'):
            raise ValueError('Qualification requires an explicit admitted cuda or cuda:N device')
        if config['model'].get('local_files_only') is not True:
            raise ValueError('Explicit input acquisition is required; set local_files_only=true')
        subprocess.run([sys.executable, str(ROOT / 'scripts/prepare_reasoning_model.py'),
                        '--config', str(config_path), '--manifest',
                        str(Path(args.asset_manifest).resolve()), '--verify-only'], check=True)
        receipt['asset_manifest_sha256'] = file_sha(args.asset_manifest)
        receipt['checks']['pinned_model_files'] = True
        splits, data_manifest = verify_prepared_data(config['data']['output_dir'])
        receipt['prepared_data_sha256'] = stable_hash(data_manifest)
        seed = private_seed(config['seed_file'])
        receipt['runtime'] = training_runtime_identity()
        device = torch.device(config['model'].get('device', 'cuda'))
        measurement_device = device
        torch.cuda.reset_peak_memory_stats(device)
        properties = torch.cuda.get_device_properties(device)
        receipt['device'] = {'name': properties.name, 'total_memory_bytes': properties.total_memory,
                             'capability': [properties.major, properties.minor],
                             'uuid': str(getattr(properties, 'uuid', 'unavailable'))}
        model, tokenizer = load_model(config['model'])
        receipt['checks']['complete_native_model_load'] = True
        names = target_modules(model, layers=config['calibration']['layers'])
        receipt['spectral_targets'] = names

        # Select by input length before any result is observed. Training/evaluation
        # partitions are never combined and test questions never enter this script.
        prompt_size = lambda task: len(tokenizer.encode(render_prompt(tokenizer, task),
                                                       add_special_tokens=False))
        training_task = max(splits['train'], key=lambda task: (prompt_size(task), task['task_id']))
        anchor_task = max(splits['calibration'], key=lambda task: (
            prompt_size(task) + len(tokenizer.encode(task['reference'], add_special_tokens=False)),
            task['task_id']))
        receipt['native_task_ids'] = {'train': training_task['task_id'],
                                     'calibration': anchor_task['task_id']}
        receipt['prompt_sha256'] = stable_hash(render_prompt(tokenizer, training_task))
        settings = {**config['synthesis'], 'samples': 1, 'batch_size': 1,
                    'task_batch_size': 1, 'sequence_batch_size': 1}
        model_identity = stable_hash(config['model'])
        records = generate_to_file(model, tokenizer, [training_task], output / 'raw.jsonl',
                                   settings, seed=seed, model_identity=model_identity,
                                   method='qualification', stage='development', round_index=0)
        if len(records) != 1 or not records[0].get('completion_ids'):
            raise RuntimeError('Native development generation returned no target tokens')
        receipt['checks']['native_template_and_generation'] = True
        receipt['generation'] = {key: records[0].get(key) for key in
                                 ('prompt_tokens', 'generation_tokens', 'finish_reason')}
        calibration_settings = {**config['calibration'], 'max_examples': 1}
        covariances = _calibrate(model, tokenizer, [anchor_task], calibration_settings,
                                output / 'calibration.pt', model_identity)
        operators = _operators(covariances, 'spectral_soft', calibration_settings, seed)
        receipt['checks']['finite_projection_gradient_covariances'] = True
        originals = {name: {key: value.detach().cpu().clone()
                           for key, value in model.get_submodule(name).state_dict().items()}
                     for name in names}
        prompt_ids = tokenizer.encode(render_prompt(tokenizer, training_task),
                                      add_special_tokens=False)
        ids = torch.tensor([prompt_ids], device=device, dtype=torch.long)
        with folded_operators(model, operators), torch.inference_mode():
            logits = model(input_ids=ids, attention_mask=torch.ones_like(ids),
                           use_cache=False, logits_to_keep=1).logits
            if not torch.isfinite(logits).all():
                raise FloatingPointError('Folded native model produced nonfinite logits')
        for name, state in originals.items():
            if any(not torch.equal(value, model.get_submodule(name).state_dict()[key].detach().cpu())
                   for key, value in state.items()):
                raise RuntimeError(f'Folded projection was not restored exactly: {name}')
        receipt['checks']['folded_forward_and_exact_restoration'] = True
        del ids, logits, covariances, operators, originals

        train_settings = copy.deepcopy(config['train'])
        train_settings.update({'epochs': 1, 'batch_size': 1, 'gradient_accumulation_steps': 1})
        train_settings.pop('target_token_budget', None)
        model, stats = train_on_records(model, tokenizer, [training_task], records,
                                       train_settings, output / 'merged_model', seed=seed)
        if (stats['optimizer_steps'] != 1 or stats['trainable_parameter_count'] <= 0
                or stats.get('gradient_norm_max', 0) <= 0):
            raise RuntimeError('One-step native SFT did not produce a nonzero finite adapter gradient')
        receipt['checks']['one_native_lora_update_and_merge'] = True
        receipt['training'] = {key: stats[key] for key in (
            'optimizer_steps', 'mean_loss', 'gradient_norm_min', 'gradient_norm_max',
            'trainable_parameter_count', 'truncated_examples', 'truncated_tokens',
            'lora_target_modules', 'lora_attention_layers', 'lora_scope')}
        expected = {name: {key: value.detach().cpu().clone()
                          for key, value in model.get_submodule(name).state_dict().items()}
                    for name in names}
        receipt['merged_checkpoint_sha256'] = checkpoint_fingerprint(output / 'merged_model')
        del model
        gc.collect()
        torch.cuda.empty_cache()
        reloaded, restored_tokenizer = load_model(config['model'], checkpoint=output / 'merged_model')
        if render_prompt(restored_tokenizer, training_task) != render_prompt(tokenizer, training_task):
            raise RuntimeError('Native chat template changed after merged-checkpoint reload')
        if target_modules(reloaded, layers=config['calibration']['layers']) != names:
            raise RuntimeError('Native target topology changed after checkpoint reload')
        for name, state in expected.items():
            if any(not torch.equal(value, reloaded.get_submodule(name).state_dict()[key].detach().cpu())
                   for key, value in state.items()):
                raise RuntimeError(f'Checkpoint reload changed projection bytes: {name}')
        receipt['checks']['merged_checkpoint_reload_and_projection_identity'] = True
        receipt['status'] = 'functional_qualification_passed'
        receipt['formal_dispatch_note'] = ('Qualify remaining domain interfaces and formal maximum '
                                          'shapes within the admitted development envelope.')
    except Exception as error:
        receipt['status'] = 'failed'
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        receipt['elapsed_seconds'] = time.monotonic() - start
        receipt['host_peak_rss_kib_linux'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if measurement_device is not None:
            receipt['gpu_peak_allocated_bytes'] = torch.cuda.max_memory_allocated(measurement_device)
            receipt['gpu_peak_reserved_bytes'] = torch.cuda.max_memory_reserved(measurement_device)
        atomic_json(receipt_path, receipt)
    print(f'Native functional qualification saved: {receipt_path}')


if __name__ == '__main__':
    main()
