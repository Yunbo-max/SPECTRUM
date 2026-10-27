"""Software routing contracts; these do not qualify the actual 27B checkpoint."""
from types import SimpleNamespace

import pytest
from torch import nn

from improving.modeling import render_prompt, set_use_cache
from improving.spectral import decoder_attention_layout, target_modules
from improving.training import attention_lora_targets


def native_layout(*, nested=False, hybrid=True):
    model = nn.Module()
    types = ['linear_attention', 'full_attention'] * 2 if hybrid else ['full_attention'] * 4
    config = SimpleNamespace(num_hidden_layers=4, layer_types=types, use_cache=True)
    model.config = SimpleNamespace(text_config=config, use_cache=True) if nested else config
    model.model = nn.Module()
    parent = model.model
    if nested:
        parent.language_model = nn.Module()
        parent = parent.language_model
    parent.layers = nn.ModuleList()
    for kind in types:
        layer = nn.Module()
        if kind == 'full_attention':
            layer.self_attn = nn.Module()
            for projection in ('q_proj', 'k_proj', 'v_proj', 'o_proj'):
                setattr(layer.self_attn, projection, nn.Linear(2, 2, bias=False))
        else:
            layer.linear_attn = nn.Module()
            layer.linear_attn.in_proj_qkv = nn.Linear(2, 6, bias=False)
        parent.layers.append(layer)
    # A distractor with the same leaf name must never become an adapter target.
    model.visual = nn.Module()
    model.visual.k_proj = nn.Linear(2, 2, bias=False)
    return model


@pytest.mark.parametrize('nested', [False, True])
def test_hybrid_requires_explicit_full_attention_and_excludes_gdn(nested):
    model = native_layout(nested=nested)
    prefix = 'model.language_model.layers' if nested else 'model.layers'
    assert decoder_attention_layout(model) == (prefix, 4, [1, 3])
    with pytest.raises(ValueError, match='explicit spectral.layers'):
        target_modules(model)
    with pytest.raises(ValueError, match='full-attention layers'):
        target_modules(model, layers=[0, 3])
    assert target_modules(model, layers=[1, 3]) == [
        f'{prefix}.{layer}.self_attn.{projection}'
        for layer in (1, 3) for projection in ('k_proj', 'v_proj')]


@pytest.mark.parametrize('nested', [False, True])
def test_lora_targets_exact_full_attention_paths_and_never_vision_or_gdn(nested):
    model = native_layout(nested=nested)
    paths, indices = attention_lora_targets(model)
    assert indices == [1, 3]
    assert len(paths) == 8
    assert all('.self_attn.' in path and 'visual' not in path and 'linear_attn' not in path
               for path in paths)
    assert all(type(model.get_submodule(path)) is nn.Linear for path in paths)
    subset, _ = attention_lora_targets(model, ['k_proj', 'v_proj'])
    assert subset == target_modules(model, layers=[1, 3])
    with pytest.raises(ValueError, match='lora_target_modules'):
        attention_lora_targets(model, ['in_proj_qkv'])


def test_standard_decoder_retains_middle_and_last_selection():
    model = native_layout(hybrid=False)
    del model.config.layer_types
    assert target_modules(model) == [
        f'model.layers.{layer}.self_attn.{projection}'
        for layer in (2, 3) for projection in ('k_proj', 'v_proj')]
    assert attention_lora_targets(model)[1] == [0, 1, 2, 3]


def test_config_mismatch_and_non_native_projection_fail():
    model = native_layout()
    model.config.num_hidden_layers = 5
    with pytest.raises(ValueError, match='length disagrees'):
        decoder_attention_layout(model)
    model.config.num_hidden_layers = 4
    model.model.layers[1].self_attn.k_proj = nn.Sequential(nn.Linear(2, 2))
    with pytest.raises(TypeError, match='native torch.nn.Linear'):
        target_modules(model, layers=[1, 3])


def test_ambiguous_decoder_paths_fail_instead_of_guessing():
    model = native_layout(nested=True)
    model.model.layers = nn.ModuleList([nn.Module() for _ in range(4)])
    with pytest.raises(ValueError, match='one supported native language decoder'):
        decoder_attention_layout(model)


def test_template_settings_are_explicit_and_shared_by_rendering():
    class NativeTokenizer:
        chat_template = 'native'

        def apply_chat_template(self, messages, **kwargs):
            self.messages, self.kwargs = messages, kwargs
            return 'rendered prompt'

    tokenizer = NativeTokenizer()
    task = {'prompt': 'A published development task',
            'chat_template_kwargs': {'enable_thinking': False}}
    assert render_prompt(tokenizer, task) == 'rendered prompt'
    assert tokenizer.kwargs == {'tokenize': False, 'add_generation_prompt': True,
                                'enable_thinking': False}
    assert tokenizer.messages == [{'role': 'user', 'content': task['prompt']}]
    with pytest.raises(ValueError, match='boolean'):
        render_prompt(tokenizer, {**task, 'chat_template_kwargs': {'enable_thinking': 'false'}})
    with pytest.raises(ValueError, match='Unsupported'):
        render_prompt(tokenizer, {**task, 'chat_template_kwargs': {'tokenize': True}})


def test_nested_cache_defaults_update_together():
    model = native_layout(nested=True)
    set_use_cache(model, False)
    assert model.config.use_cache is False and model.config.text_config.use_cache is False
    set_use_cache(model, True)
    assert model.config.use_cache is True and model.config.text_config.use_cache is True
