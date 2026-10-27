"""Consistent prompt serialization, causal labels, and single-device HF loading."""
from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
import random

import numpy as np
import torch


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def render_prompt(tokenizer, task: dict) -> str:
    """One identical native template for every method and training/evaluation stage."""
    prompt = task['prompt']
    template_kwargs = task.get('chat_template_kwargs', {})
    if not isinstance(template_kwargs, dict) or set(template_kwargs) - {
            'enable_thinking', 'reasoning_effort', 'preserve_thinking'}:
        raise ValueError('Unsupported chat_template_kwargs; freeze thinking settings in each task')
    for key in ('enable_thinking', 'preserve_thinking'):
        if key in template_kwargs and type(template_kwargs[key]) is not bool:
            raise ValueError(f'chat_template_kwargs.{key} must be a boolean')
    if ('reasoning_effort' in template_kwargs
            and template_kwargs['reasoning_effort'] not in {'low', 'medium', 'xhigh'}):
        raise ValueError('reasoning_effort must be low, medium or xhigh')
    if getattr(tokenizer, 'chat_template', None):
        return tokenizer.apply_chat_template(
            [{'role': 'user', 'content': prompt}], tokenize=False, add_generation_prompt=True,
            **template_kwargs,
        )
    if template_kwargs:
        raise ValueError('Explicit thinking settings require a native chat template')
    return prompt


def encode_example(tokenizer, prompt: str, completion: str, *, max_length: int,
                   loss_scope: str = 'completion', spans=None,
                   completion_ids: list[int] | None = None, append_eos: bool = True) -> dict:
    """Concatenate tokenized prefix and continuation, preserving the generation prefix.

    Character spans address the reference completion only. Padding labels are masked
    by POSITION rather than by pad token ID, since many LMs reuse EOS for padding.
    """
    if loss_scope not in {'completion', 'all'}:
        raise ValueError('loss_scope must be completion or all')
    prefix = tokenizer.encode(prompt, add_special_tokens=False)
    if not prefix or len(prefix) >= max_length:
        raise ValueError('Empty/overlong prompt leaves no target; increase max_length')
    if spans is not None:
        if not spans or any(len(s) != 2 or not 0 <= s[0] < s[1] <= len(completion) for s in spans):
            raise ValueError('calibration_spans must be valid nonempty completion character intervals')
        encoded = tokenizer(completion, add_special_tokens=False, return_offsets_mapping=True)
        suffix = encoded['input_ids']
        target = [token if any(a < end and b > start for a, b in spans) else -100
                  for token, (start, end) in zip(suffix, encoded['offset_mapping'])]
    else:
        suffix = list(completion_ids) if completion_ids is not None else tokenizer.encode(
            completion, add_special_tokens=False)
        target = suffix.copy()
        eos = tokenizer.eos_token_id
        if append_eos and completion_ids is None and eos is not None and (not suffix or suffix[-1] != eos):
            suffix.append(eos)
            target.append(eos)
    labels = (prefix.copy() if loss_scope == 'all' and spans is None else [-100] * len(prefix)) + target
    ids = (prefix + suffix)[:max_length]
    labels = labels[:max_length]
    if not any(x != -100 for x in labels[1:]):
        raise ValueError('No supervised next-token target remains after truncation')
    return {'input_ids': ids, 'attention_mask': [1] * len(ids), 'labels': labels,
            'truncated_tokens': max(0, len(prefix) + len(suffix) - max_length)}


def collate_examples(examples: list[dict], pad_token_id: int) -> dict[str, torch.Tensor]:
    if not examples:
        raise ValueError('Cannot collate an empty batch')
    width = max(len(x['input_ids']) for x in examples)
    batch = {}
    for key, padding in [('input_ids', pad_token_id), ('attention_mask', 0), ('labels', -100)]:
        batch[key] = torch.tensor([x[key] + [padding] * (width - len(x[key])) for x in examples],
                                  dtype=torch.long)
    return batch


def load_model(settings: dict, checkpoint: str | Path | None = None):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    name = str(checkpoint or settings['name'])
    device = settings.get('device', 'auto')
    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    dtype_name = settings.get('dtype', 'bfloat16') if device.startswith('cuda') else 'float32'
    if dtype_name == 'bfloat16' and device.startswith('cuda') and not torch.cuda.is_bf16_supported():
        raise ValueError('This GPU does not support BF16; use dtype float32 or a compatible GPU')
    if dtype_name not in {'float32', 'bfloat16'}:
        raise ValueError('This tested training path supports float32 or bfloat16; FP16 needs a scaler')
    loader = settings.get('loader', 'causal_lm')
    if loader not in {'causal_lm', 'qwen3_5_text'}:
        raise ValueError('model.loader must be causal_lm or qwen3_5_text')
    if any(settings.get(key) for key in ('load_in_4bit', 'load_in_8bit', 'quantization_config')):
        raise ValueError('SPECTRUM folding requires unquantized native Linear weights')
    kwargs = {'trust_remote_code': False}
    if settings.get('local_files_only', False):
        kwargs['local_files_only'] = True
    if checkpoint is None and settings.get('revision'):
        kwargs['revision'] = settings['revision']
    tokenizer = AutoTokenizer.from_pretrained(name, use_fast=True, **kwargs)
    if tokenizer.pad_token_id is None:
        if tokenizer.eos_token_id is None:
            raise ValueError('Tokenizer must define padding or EOS')
        tokenizer.pad_token = tokenizer.eos_token
    model_class = AutoModelForCausalLM
    if loader == 'qwen3_5_text':
        # Official text-only class and weight-prefix conversion. It loads the
        # released language weights, without constructing an unused vision tower.
        # Saved/merged checkpoints subsequently contain the text configuration.
        try:
            from transformers import Qwen3_5ForCausalLM
        except ImportError as error:
            raise ImportError('qwen3_5_text needs the separate requirements/multidomain-27b.txt '
                              'environment; do not upgrade an active legacy run') from error
        model_class = Qwen3_5ForCausalLM
    model, loading_info = model_class.from_pretrained(
        name, torch_dtype=getattr(torch, dtype_name),
        attn_implementation=settings.get('attn_implementation', 'sdpa'),
        output_loading_info=True, **kwargs
    )
    if loading_info.get('missing_keys') or loading_info.get('mismatched_keys') or loading_info.get('error_msgs'):
        raise ValueError(f'Checkpoint loading was incomplete: {loading_info}')
    # The official qwen3_5_text conversion deliberately excludes vision and MTP.
    # Any other unexpected parameter is a loader/provenance mismatch.
    unexpected = loading_info.get('unexpected_keys', [])
    if loader == 'qwen3_5_text':
        unexpected = [key for key in unexpected
                      if not key.startswith(('model.visual.', 'visual.', 'mtp.', 'model.mtp.'))]
    if unexpected:
        raise ValueError(f'Unexpected checkpoint parameters: {unexpected}')
    model = model.to(device)
    return model, tokenizer


def text_model_config(model):
    """Return the language config for a plain or nested native checkpoint."""
    config = model.config
    return getattr(config, 'text_config', config)


def set_use_cache(model, enabled: bool) -> None:
    """Set both top-level and nested text defaults; forward calls still bind use_cache."""
    for config in (model.config, text_model_config(model)):
        config.use_cache = bool(enabled)


def autocast_for(model):
    parameter = next(model.parameters())
    if parameter.device.type == 'cuda' and parameter.dtype == torch.bfloat16:
        return torch.autocast('cuda', dtype=torch.bfloat16)
    return nullcontext()
