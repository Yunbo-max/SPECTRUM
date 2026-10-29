"""Raw-completion LoRA SFT shared by every experimental arm."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import random
import tempfile

import torch
from torch.utils.data import DataLoader, Subset

from .modeling import (autocast_for, collate_examples, encode_example, render_prompt,
                       seed_everything, set_use_cache)
from .spectral import decoder_attention_layout, _native_linear
from .utils import stable_hash


def validate_full_completion_targets(settings, generation=None):
    """Validate the opt-in no-SFT-truncation contract without changing legacy runs."""
    required = settings.get('require_full_completion_targets', False)
    if type(required) is not bool:
        raise ValueError('train.require_full_completion_targets must be boolean')
    if not required:
        return False
    max_length = settings.get('max_length', 1536)
    if type(max_length) is not int or max_length < 1:
        raise ValueError('train.max_length must be a positive integer')
    if generation is not None:
        limits = {}
        for key, default in (('max_prompt_tokens', 1024), ('max_new_tokens', 512)):
            value = generation.get(key, default)
            if type(value) is not int or value < 1:
                raise ValueError(f'generation.{key} must be a positive integer')
            limits[key] = value
        needed = limits['max_prompt_tokens'] + limits['max_new_tokens']
        if max_length < needed:
            raise ValueError(
                'train.require_full_completion_targets requires train.max_length '
                '>= generation.max_prompt_tokens + generation.max_new_tokens '
                f'({max_length} < {needed}); increase the training context in a new run')
    return True


def attention_lora_targets(model, projections=None):
    """Qualify exact native full-attention paths before PEFT matches any modules."""
    projections = ['q_proj', 'k_proj', 'v_proj', 'o_proj'] if projections is None else projections
    if (not isinstance(projections, list) or not projections
            or any(not isinstance(name, str) for name in projections)
            or len(projections) != len(set(projections))
            or any(name not in {'q_proj', 'k_proj', 'v_proj', 'o_proj'} for name in projections)):
        raise ValueError('lora_target_modules must be unique native attention q/k/v/o projection names')
    layer_prefix, _, attention_layers = decoder_attention_layout(model)
    targets = [f'{layer_prefix}.{layer}.self_attn.{projection}'
               for layer in attention_layers for projection in projections]
    for name in targets:
        _native_linear(model, name)
    return targets, attention_layers


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
                         f'corpus pass ({corpus_tokens} target tokens); increase the budget '
                         'so every raw completion is trained on at least once')
    rng = random.Random(seed)
    indices, exposures = [], [0] * len(counts)
    tokens, completed_passes = 0, 0
    while tokens < target_token_budget:
        order = list(range(len(counts)))
        rng.shuffle(order)
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


def train_on_records(model, tokenizer, tasks, records, settings, output_dir, *, seed=42):
    require_full_targets = validate_full_completion_targets(settings)
    from peft import LoraConfig, get_peft_model
    from transformers import get_cosine_schedule_with_warmup
    from .data import validate_tasks, validate_completions
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
    if require_full_targets:
        truncated = [(record, example) for record, example in zip(records, examples)
                     if example['truncated_tokens'] > 0]
        if truncated:
            record, example = truncated[0]
            raise ValueError(
                'train.require_full_completion_targets forbids SFT truncation: '
                f'{len(truncated)} records exceed train.max_length; first task '
                f'{record["task_id"]!r}, sample {record["sample_id"]}, '
                f'dropped_tokens={example["truncated_tokens"]}. '
                'No records were filtered and no adapter was created; '
                'increase the training context in a new run.')
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
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=target_budget is None,
                        generator=torch.Generator().manual_seed(seed),
                        collate_fn=lambda xs: collate_examples(xs, tokenizer.pad_token_id))
    lora_targets, attention_layers = attention_lora_targets(model, settings.get('lora_target_modules'))
    model = get_peft_model(model, LoraConfig(
        task_type='CAUSAL_LM', r=int(settings.get('lora_rank', 8)),
        lora_alpha=int(settings.get('lora_alpha', 8)),
        lora_dropout=float(settings.get('lora_dropout', .05)), bias='none',
        target_modules=lora_targets
    ))
    set_use_cache(model, False)
    if settings.get('gradient_checkpointing', True):
        # Non-reentrant checkpointing works with frozen embeddings; no input hooks.
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),
                                 lr=float(settings.get('learning_rate', 1e-5)),
                                 weight_decay=float(settings.get('weight_decay', .01)))
    total_steps = math.ceil(len(loader) / accumulation) * passes
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, int(total_steps * float(settings.get('warmup_ratio', .03))), total_steps
    )
    device = next(model.parameters()).device
    model.train()
    losses, gradient_norms, optimizer_steps = [], [], 0
    optimizer.zero_grad(set_to_none=True)
    for _epoch in range(passes):
        for index, batch in enumerate(loader):
            # Normalize by actual microbatches in final incomplete accumulation group.
            group_start = (index // accumulation) * accumulation
            divisor = min(accumulation, len(loader) - group_start)
            batch = {k: v.to(device) for k, v in batch.items()}
            with autocast_for(model):
                loss = model(**batch).loss
            if not torch.isfinite(loss):
                raise FloatingPointError('Nonfinite SFT loss; checkpoint not saved')
            (loss / divisor).backward()
            losses.append(float(loss.detach().cpu()))
            if (index + 1) % accumulation == 0 or index + 1 == len(loader):
                gradient_norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), float(settings.get('max_grad_norm', 1.0)))
                if not torch.isfinite(gradient_norm):
                    raise FloatingPointError('Nonfinite SFT gradient norm; checkpoint not saved')
                gradient_norms.append(float(gradient_norm.detach().cpu()))
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                optimizer_steps += 1
    # A single merged checkpoint is the next round's model, never an adapter pool.
    model.gradient_checkpointing_disable()
    merged = model.merge_and_unload(safe_merge=True)
    set_use_cache(merged, True)
    merged.eval()
    stats = {'examples': len(examples), 'optimizer_steps': optimizer_steps,
             'mean_loss': sum(losses) / len(losses), 'epochs': epochs if target_budget is None else None,
             'gradient_norm_min': min(gradient_norms),
             'gradient_norm_max': max(gradient_norms),
             'truncated_examples': sum(x['truncated_tokens'] > 0 for x in examples),
             'truncated_tokens': sum(x['truncated_tokens'] for x in examples),
             'supervised_tokens_per_epoch': sum(target_counts),
             'trainable_parameter_count': sum(p.numel() for group in optimizer.param_groups for p in group['params']),
             'lora_target_modules': lora_targets,
             'lora_attention_layers': attention_layers,
             'lora_scope': 'native_full_attention_qkvo_only',
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
             'require_full_completion_targets': require_full_targets,
             'target_token_definition': 'nonignored_causally_shifted_labels_after_max_length_encoding',
             'truncation_policy': ('reject_any_sft_truncation; no_record_filtering'
                                   if require_full_targets else
                                   'declared_max_length; dropped_token_counts_reported_per_record'),
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
    # Interrupted saves cannot look like a resumable completed checkpoint.
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f'.{output_dir.name}.saving-', dir=output_dir.parent) as temporary:
        temporary_path = Path(temporary)
        merged.save_pretrained(temporary_path, safe_serialization=True)
        tokenizer.save_pretrained(temporary_path)
        (temporary_path / 'training_stats.json').write_text(json.dumps(stats, indent=2) + '\n')
        if output_dir.exists():
            output_dir.rmdir()  # Only an empty destination was permitted above.
        os.replace(temporary_path, output_dir)
    return merged, stats
