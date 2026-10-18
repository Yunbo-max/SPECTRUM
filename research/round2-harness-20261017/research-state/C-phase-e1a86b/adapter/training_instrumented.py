"""Generated, unexecuted B02 instrumentation of pinned upstream SFT.

Preserves per-record causal loss, full-corpus token exposure, optimizer and merge.
No scorer or generated-program execution. Run only through admitted hn01 work.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import random
import tempfile
import time

import torch
from torch.utils.data import DataLoader, Subset

from improving.modeling import autocast_for, collate_examples, encode_example, render_prompt, seed_everything
from improving.utils import stable_hash


def plan_token_exposure(target_counts, target_token_budget, *, seed=42):
    """Plan deterministic whole-record exposures with a bounded token overshoot.

    Every encoded record is exposed at least once. Independent permutations of
    the *entire* corpus are then traversed until the number of supervised causal
    targets reaches the budget. No labels are masked to hit a boundary and no
    record is selected by correctness, content, or length. The final whole
    record can overshoot the requested budget by fewer than ``max(counts)``
    targets. Counts include prompt targets when ``loss_scope='all'``.
    """
    counts = list(target_counts)
    if not counts or any(type(count) is not int or count < 1 for count in counts):
        raise ValueError('Every encoded training record must have positive target tokens')
    if type(target_token_budget) is not int or target_token_budget < 1:
        raise ValueError('train.target_token_budget must be a positive integer or null')
    corpus_tokens = sum(counts)
    if target_token_budget < corpus_tokens:
        raise ValueError(f'train.target_token_budget={target_token_budget} is below one complete '
                         f'corpus pass ({corpus_tokens} target tokens); stop for reviewed budget revision; '
                         'do not filter records or enlarge the budget automatically')
    rng = random.Random(seed)
    indices, exposures = [], [0] * len(counts)
    permutation_hashes = []
    tokens, completed_passes = 0, 0
    while tokens < target_token_budget:
        order = list(range(len(counts)))
        rng.shuffle(order)
        permutation_hashes.append(stable_hash(order))
        used = 0
        for index in order:
            indices.append(index)
            exposures[index] += 1
            tokens += counts[index]
            used += 1
            if tokens >= target_token_budget:
                break
        if used == len(counts):
            completed_passes += 1
    return indices, {
        'full_permutation_sha256': permutation_hashes,
        'target_token_budget': target_token_budget,
        'actual_supervised_target_tokens': tokens,
        'target_token_overshoot': tokens - target_token_budget,
        'target_token_overshoot_upper_bound_exclusive': max(counts),
        'completed_corpus_passes': completed_passes,
        'partial_corpus_pass_records': len(indices) % len(counts),
        'record_exposure_counts': exposures,
        'record_exposures': len(indices),
        'exposure_order': 'seeded_full_corpus_permutations_then_whole_record_stop',
        'exposure_plan_sha256': stable_hash(indices),
        'budget_matching_contract': 'lower_bound_with_whole_record_overshoot',
    }



def accumulation_divisor(index, loader_length, accumulation):
    if not 0 <= index < loader_length or accumulation < 1:
        raise ValueError('Invalid accumulation position')
    group_start = (index // accumulation) * accumulation
    return min(accumulation, loader_length - group_start)


def target_breakdown(example, prefix_count):
    """Count true causal targets by original prompt/completion positions."""
    prompt = sum(label != -100 for i, label in enumerate(example['labels'])
                 if 0 < i < prefix_count)
    completion = sum(label != -100 for i, label in enumerate(example['labels'])
                     if i > 0 and i >= prefix_count)
    return {'prompt_targets': prompt, 'completion_targets': completion,
            'supervised_target_tokens': prompt + completion,
            'encoded_input_tokens': len(example['input_ids']),
            'truncated_tokens': example['truncated_tokens']}


class Telemetry:
    """Write once metadata and append-only observations; no recovery inference."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=False)
        self.phases = []
        self.active_phase = None

    def write(self, name, value):
        with (self.path / name).open('x') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())

    def append(self, name, value):
        with (self.path / name).open('a') as stream:
            stream.write(json.dumps(value) + '\n')
            stream.flush()

    def memory(self, device):
        if device.type != 'cuda':
            return {'cuda_allocated_bytes': None, 'cuda_reserved_bytes': None,
                    'cuda_peak_allocated_bytes': None, 'cuda_peak_reserved_bytes': None}
        return {'cuda_allocated_bytes': torch.cuda.memory_allocated(device),
                'cuda_reserved_bytes': torch.cuda.memory_reserved(device),
                'cuda_peak_allocated_bytes': torch.cuda.max_memory_allocated(device),
                'cuda_peak_reserved_bytes': torch.cuda.max_memory_reserved(device)}

    def start_phase(self, name, device):
        if self.active_phase is not None:
            raise RuntimeError('Nested telemetry phase')
        if device.type == 'cuda':
            torch.cuda.synchronize(device)
            torch.cuda.reset_peak_memory_stats(device)
        self.active_phase = (name, time.monotonic())

    def end_phase(self, device):
        if device.type == 'cuda':
            torch.cuda.synchronize(device)
        name, started = self.active_phase
        observation = {'phase': name, 'elapsed_seconds': time.monotonic() - started,
                       **self.memory(device)}
        self.phases.append(observation)
        self.append('resources.jsonl', observation)
        self.active_phase = None


def validate_training_contract(settings, seed):
    expected = {'batch_size': 1, 'gradient_accumulation_steps': 16,
                'max_length': 1536, 'loss_scope': 'all',
                'target_token_budget': 7200000, 'epochs': 1,
                'learning_rate': 1e-5, 'weight_decay': .01,
                'warmup_ratio': .03, 'max_grad_norm': 1,
                'lora_rank': 8, 'lora_alpha': 8, 'lora_dropout': .05,
                'gradient_checkpointing': True}
    for key, value in expected.items():
        if settings.get(key) != value:
            raise ValueError(f'Frozen B02 training setting mismatch: {key}')
    if seed != 44:
        raise ValueError('B02 training seed must be 44')


def train_on_records(model, tokenizer, tasks, records, settings, output_dir, *,
                     seed=44, telemetry_dir=None):
    """Same upstream call plus telemetry_dir; one completed checkpoint or failure.

    A fresh output/telemetry location is mandatory. Interrupted training has no
    optimizer resume path. A caller must reconcile the old attempt before retry.
    This function is deliberately NOT a scorer and never executes completions.
    """
    validate_training_contract(settings, seed)
    return _execute_training(model, tokenizer, tasks, records, settings, output_dir,
                             seed=seed, telemetry_dir=telemetry_dir,
                             execution_scope='formal_development_training')


def qualify_training(model, tokenizer, tasks, records, settings, output_dir, *,
                     seed=44, telemetry_dir=None):
    """One disposable accumulation/optimizer/merge/save on 16 real records.

    Inputs must be supplied from the preselected calibration data, not model
    outcome selection. Caller retains identities and disposes of this model/RNG.
    This does not qualify the full-corpus time or every length's memory peak.
    """
    validate_training_contract(settings, seed)
    if len(records) != 16:
        raise ValueError('Qualification needs exactly 16 existing real records')
    task_map = {task['task_id']: task for task in tasks}
    counts = []
    for record in records:
        example = encode_example(
            tokenizer, render_prompt(tokenizer, task_map[record['task_id']]),
            record['completion'], max_length=settings['max_length'],
            loss_scope=settings['loss_scope'], completion_ids=record.get('completion_ids'),
            append_eos=record.get('completion_ids') is None and record.get('finish_reason') != 'length')
        counts.append(sum(token != -100 for token in example['labels'][1:]))
    qualification_settings = dict(settings, target_token_budget=sum(counts))
    return _execute_training(model, tokenizer, tasks, records, qualification_settings,
                             output_dir, seed=seed, telemetry_dir=telemetry_dir,
                             execution_scope='disposable_16_record_resource_qualification')


def _execute_training(model, tokenizer, tasks, records, settings, output_dir, *,
                      seed, telemetry_dir, execution_scope):
    telemetry = Telemetry(telemetry_dir or str(output_dir) + '.telemetry')
    started = time.monotonic()
    telemetry.write('invocation.json', {'seed': seed, 'settings': settings,
                                     'output_dir': str(output_dir),
                                     'status': 'started', 'execution_scope': execution_scope,
                                     'records_sha256': stable_hash(records),
                                     'tasks_sha256': stable_hash(tasks)})
    try:
        merged, stats = _train_on_records(model, tokenizer, tasks, records, settings,
                                         output_dir, seed=seed, telemetry=telemetry)
    except BaseException as error:
        telemetry.write('failure.json', {'status': 'failed',
            'exception_type': type(error).__name__, 'error': str(error),
            'elapsed_seconds': time.monotonic() - started,
            'active_phase': telemetry.active_phase,
            'checkpoint_resume_supported': False})
        raise
    telemetry.write('completed.json', {'status': 'completed',
        'elapsed_seconds': time.monotonic() - started,
        'checkpoint': str(output_dir), 'execution_scope': execution_scope, 'stats': stats})
    return merged, stats


def _train_on_records(model, tokenizer, tasks, records, settings, output_dir, *, seed, telemetry):
    from peft import LoraConfig, get_peft_model
    from transformers import get_cosine_schedule_with_warmup
    from improving.data import validate_tasks, validate_completions
    validate_tasks(tasks)
    validate_completions(records, tasks)
    if not records:
        raise ValueError('No raw completions to train on')
    origins = [record.get('record_origin', 'synthetic_raw') for record in records]
    if any(origin not in {'synthetic_raw', 'fixed_anchor_reference'} for origin in origins):
        raise ValueError('Unrecognized SFT record_origin')
    anchor_count = origins.count('fixed_anchor_reference')
    if bool(settings.get('fixed_anchor_replay', False)) != (anchor_count > 0):
        raise ValueError('Fixed anchor reference records require explicit train.fixed_anchor_replay '
                         'and replay mode requires explicit reference records')
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f'Refusing to overwrite checkpoint: {output_dir}')
    task_map = {x['task_id']: x for x in tasks}
    if set(task_map) != {x['task_id'] for x in records}:
        raise ValueError('Training corpus must include every training task')
    seed_everything(seed)
    examples = [encode_example(
        tokenizer, render_prompt(tokenizer, task_map[r['task_id']]), r['completion'],
        max_length=settings.get('max_length', 1536),
        loss_scope=settings.get('loss_scope', 'all'), completion_ids=r.get('completion_ids'),
        append_eos=r.get('completion_ids') is None and r.get('finish_reason') != 'length'
    ) for r in records]  # Deliberately no `correct`, strategy, length or AST filtering.
    record_details = []
    for record, example, origin in zip(records, examples, origins):
        prompt = render_prompt(tokenizer, task_map[record['task_id']])
        prefix_count = len(tokenizer.encode(prompt, add_special_tokens=False))
        detail = target_breakdown(example, prefix_count)
        detail.update(task_id=record['task_id'], sample_id=record['sample_id'],
                      record_origin=origin, prompt_sha256=stable_hash(prompt),
                      prompt_input_tokens=prefix_count,
                      completion_ids_supplied=record.get('completion_ids') is not None,
                      finish_reason=record.get('finish_reason'))
        record_details.append(detail)
        telemetry.append('encoded-records.jsonl', detail)
    batch_size = int(settings.get('batch_size', 1))
    accumulation = int(settings.get('gradient_accumulation_steps', 16))
    epochs = int(settings.get('epochs', 5))
    if min(batch_size, accumulation, epochs) < 1:
        raise ValueError('batch_size, accumulation and epochs must be positive')
    target_counts = [sum(token != -100 for token in example['labels'][1:]) for example in examples]
    target_budget = settings.get('target_token_budget')
    exposure = None
    dataset, passes = examples, epochs
    if target_budget is not None:
        indices, exposure = plan_token_exposure(target_counts, target_budget, seed=seed)
        dataset, passes = Subset(examples, indices), 1
        telemetry.write('exposure-plan.json', exposure)
        for position, source_index in enumerate(indices):
            telemetry.append('planned-exposure.jsonl', {
                'position': position, 'record_index': source_index,
                **record_details[source_index]})
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=target_budget is None,
                        generator=torch.Generator().manual_seed(seed),
                        collate_fn=lambda xs: collate_examples(xs, tokenizer.pad_token_id))
    model = get_peft_model(model, LoraConfig(
        task_type='CAUSAL_LM', r=int(settings.get('lora_rank', 8)),
        lora_alpha=int(settings.get('lora_alpha', 8)),
        lora_dropout=float(settings.get('lora_dropout', .05)), bias='none',
        target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj']
    ))
    model.config.use_cache = False
    if settings.get('gradient_checkpointing', True):
        # Non-reentrant checkpointing works with frozen embeddings; no input hooks.
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),
                                 lr=float(settings.get('learning_rate', 1e-5)),
                                 weight_decay=float(settings.get('weight_decay', .01)))
    telemetry.write('optimizer.json', {
        'class': type(optimizer).__name__, 'module': type(optimizer).__module__,
        'torch_version': torch.__version__, 'defaults': optimizer.defaults,
        'parameter_groups': [{k: v for k, v in group.items() if k != 'params'}
                             for group in optimizer.param_groups]})
    total_steps = math.ceil(len(loader) / accumulation) * passes
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, int(total_steps * float(settings.get('warmup_ratio', .03))), total_steps
    )
    device = next(model.parameters()).device
    model.train()
    telemetry.start_phase('forward_backward_optimizer', device)
    losses, optimizer_steps = [], 0
    optimizer.zero_grad(set_to_none=True)
    for _epoch in range(passes):
        for index, batch in enumerate(loader):
            # Normalize by actual microbatches in final incomplete accumulation group.
            divisor = accumulation_divisor(index, len(loader), accumulation)
            micro_started = time.monotonic()
            lr_before = [group['lr'] for group in optimizer.param_groups]
            batch = {k: v.to(device) for k, v in batch.items()}
            with autocast_for(model):
                loss = model(**batch).loss
            if not torch.isfinite(loss):
                raise FloatingPointError('Nonfinite SFT loss; checkpoint not saved')
            (loss / divisor).backward()
            losses.append(float(loss.detach().cpu()))
            telemetry.append('exposure.jsonl', {
                'position': index, 'epoch': _epoch, 'record_index': indices[index],
                **record_details[indices[index]],
                'loss': losses[-1], 'loss_divisor': divisor,
                'lr_for_backward': lr_before,
                'optimizer_step_before': optimizer_steps,
                'microbatch_elapsed_seconds': time.monotonic() - micro_started})
            if (index + 1) % accumulation == 0 or index + 1 == len(loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), float(settings.get('max_grad_norm', 1.0)))
                optimizer_started = time.monotonic()
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                optimizer_steps += 1
                if device.type == 'cuda':
                    torch.cuda.synchronize(device)
                telemetry.append('optimizer-steps.jsonl', {
                    'optimizer_step': optimizer_steps, 'last_record_position': index,
                    'group_size': divisor, 'lr_used': lr_before,
                    'lr_after_schedule': [group['lr'] for group in optimizer.param_groups],
                    'elapsed_seconds': time.monotonic() - optimizer_started,
                    **telemetry.memory(device)})
    # A single merged checkpoint is the next round's model, never an adapter pool.
    telemetry.end_phase(device)
    telemetry.start_phase('merge', device)
    model.gradient_checkpointing_disable()
    merged = model.merge_and_unload(safe_merge=True)
    merged.config.use_cache = True
    merged.eval()
    telemetry.end_phase(device)
    stats = {'examples': len(examples), 'optimizer_steps': optimizer_steps,
             'mean_loss': sum(losses) / len(losses), 'epochs': epochs if target_budget is None else None,
             'truncated_examples': sum(x['truncated_tokens'] > 0 for x in examples),
             'truncated_tokens': sum(x['truncated_tokens'] for x in examples),
             'supervised_tokens_per_epoch': sum(target_counts),
             'trainable_parameter_count': sum(p.numel() for group in optimizer.param_groups for p in group['params']),
             'loss_scope': settings.get('loss_scope', 'all'), 'seed': seed,
             'training_budget_mode': 'fixed_epochs' if target_budget is None else 'target_tokens_whole_records',
             'configured_epochs': epochs, 'configured_epochs_applied': target_budget is None,
             'training_records_received': len(records), 'training_records_retained': len(examples),
             'raw_records_received': len(records) - anchor_count,
             'raw_records_retained': len(examples) - anchor_count,
             'all_raw_records_retained': len(records) == len(examples),
             'anchor_reference_records': anchor_count,
             'fixed_anchor_replay': bool(settings.get('fixed_anchor_replay', False)),
             'quality_filtering': False, 'budget_label_masking': False,
             'target_token_definition': 'nonignored_causally_shifted_labels_after_max_length_encoding',
             'truncation_policy': 'declared_max_length; dropped_token_counts_reported_per_record',
             'actual_supervised_target_tokens': sum(target_counts) * epochs,
             'record_exposures': len(examples) * epochs}
    if exposure is not None:
        stats.update(exposure)
    exposure_counts = stats.pop('record_exposure_counts', [epochs] * len(records))
    stats['all_training_records_exposed'] = all(count >= 1 for count in exposure_counts)
    stats['all_raw_records_exposed'] = all(count >= 1 for count, origin in zip(exposure_counts, origins)
                                          if origin == 'synthetic_raw')
    stats['supervised_target_tokens_by_origin'] = {
        origin: sum(count * exposures for count, exposures, record_origin in
                    zip(target_counts, exposure_counts, origins) if record_origin == origin)
        for origin in ('synthetic_raw', 'fixed_anchor_reference')
    }
    stats['record_retention'] = [
        {'task_id': record['task_id'], 'sample_id': record['sample_id'],
         'record_origin': origin,
         'supervised_target_tokens': count, 'exposures': exposures,
         'truncated_tokens': example['truncated_tokens']}
        for record, example, count, exposures, origin in zip(records, examples, target_counts, exposure_counts, origins)
    ]
    stats['loss_aggregation'] = 'mean_per_record_causal_loss_then_mean_actual_accumulation_group'
    stats['last_accumulation_group_size'] = len(loader) % accumulation or accumulation
    stats['prompt_supervised_target_tokens'] = sum(
        d['prompt_targets'] * n for d, n in zip(record_details, exposure_counts))
    stats['completion_supervised_target_tokens'] = sum(
        d['completion_targets'] * n for d, n in zip(record_details, exposure_counts))
    stats['token_budget_is_not_equal_update_or_compute_budget'] = True
    telemetry.write('record-retention.json', stats['record_retention'])
    # Interrupted saves cannot look like a resumable completed checkpoint.
    # Retain interrupted temporary files for reconciliation, unlike upstream cleanup.
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = Path(tempfile.mkdtemp(prefix=f'.{output_dir.name}.saving-', dir=output_dir.parent))
    telemetry.write('checkpoint-staging.json', {'staging_path': str(temporary_path),
                                               'destination': str(output_dir)})
    telemetry.start_phase('save', device)
    merged.save_pretrained(temporary_path, safe_serialization=True)
    tokenizer.save_pretrained(temporary_path)
    telemetry.end_phase(device)
    stats['phase_observations'] = telemetry.phases
    (temporary_path / 'training_stats.json').write_text(json.dumps(stats, indent=2) + '\n')
    if output_dir.exists():
        output_dir.rmdir()  # Only an empty destination was permitted above.
    os.replace(temporary_path, output_dir)
    return merged, stats
