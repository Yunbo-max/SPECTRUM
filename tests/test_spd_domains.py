import pytest
import torch
from tests.helpers import tiny_model_and_tokenizer


def task(domain='math'):
    return {'task_id': domain + '/1', 'source': domain + '-fixture', 'split': 'calibration',
            'prompt': 'Write a function ', 'reference': 'return 1', 'calibration_spans': [[7, 8]]}


def settings():
    return {'layers': [0, 1], 'max_length': 128}


@pytest.mark.parametrize('domain', ['math', 'qa', 'safety'])
def test_projection_masks_cache_and_state(tmp_path, monkeypatch, domain):
    from improving.spd_domains import calibrate_domains
    from improving.spd_upstream import upstream, projector_record
    model, tok = tiny_model_and_tokenizer()
    tok.chat_template = "{{ messages[0]['content'] }}hello world "
    item = task(domain)
    model.train()
    model.model.layers[0].eval()
    params = list(model.parameters())
    params[0].requires_grad_(False)
    params[1].grad = torch.ones_like(params[1])
    flags, grad = [p.requires_grad for p in params], params[1].grad
    modes = [m.training for m in model.modules()]
    weights = [p.detach().clone() for p in params]
    calls = []
    original = upstream.collect_kv_gradients
    def collect(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append((args, kwargs, result))
        return result
    monkeypatch.setattr(upstream, 'collect_kv_gradients', collect)
    operators = calibrate_domains(model, tok, [item], settings(), tmp_path, model_identity='base')
    assert len(operators) == 4 and len(calls) == 1
    args, kwargs, gradients = calls[0]
    text = args[2][0]
    assert text == 'Write a function hello world return 1'
    assert kwargs['label_char_spans'] == [[(len(text)-1, len(text))]]
    for name, operator in operators.items():
        layer = int(name.split('.layers.')[1].split('.')[0])
        key = 'K_grads' if name.endswith('k_proj') else 'V_grads'
        assert torch.equal(operator, projector_record(gradients[layer][key])['spd_operator'])
    assert flags == [p.requires_grad for p in params]
    assert modes == [m.training for m in model.modules()]
    assert params[1].grad is grad and torch.all(grad == 1)
    assert all(torch.equal(old, new) for old, new in zip(weights, params))
    cached = calibrate_domains(model, tok, [item], settings(), tmp_path, model_identity='base')
    assert len(calls) == 1 and all(torch.equal(cached[k], v) for k, v in operators.items())
    saved = torch.load(tmp_path/'calibration.pt', weights_only=True)
    assert saved['metadata']['model_identity'] == 'base'
    for changed, config, identity in [
        ({**item, 'source': 'other'}, settings(), 'base'),
        ({**item, 'calibration_spans': [[0, 6]]}, settings(), 'base'),
        (item, {**settings(), 'max_length': 127}, 'base'), (item, settings(), 'other'),
    ]:
        with pytest.raises(ValueError, match='identity'):
            calibrate_domains(model, tok, [changed], config, tmp_path, model_identity=identity)
    tok.chat_template = "{{ messages[0]['content'] }}hello "
    with pytest.raises(ValueError, match='identity'):
        calibrate_domains(model, tok, [item], settings(), tmp_path, model_identity='base')


def test_failure_restores_existing_hooks_gradients_and_modes(tmp_path, monkeypatch):
    from improving.spd_domains import calibrate_domains
    from improving.spd_upstream import upstream
    model, tok = tiny_model_and_tokenizer()
    model.train()
    model.model.layers[0].eval()
    params = list(model.parameters())
    params[0].requires_grad_(False)
    params[1].grad = torch.ones_like(params[1])
    grad = params[1].grad
    flags, modes = [p.requires_grad for p in params], [m.training for m in model.modules()]
    attn = model.model.layers[0].self_attn
    handle = attn.k_proj.register_forward_hook(lambda *args: None)
    prior = dict(attn.k_proj._forward_hooks)
    def fail(model, *args, **kwargs):
        model.eval()
        model.zero_grad()
        attn.k_proj.register_forward_hook(lambda *args: None)
        raise RuntimeError('injected collector failure')
    monkeypatch.setattr(upstream, 'collect_kv_gradients', fail)
    with pytest.raises(RuntimeError, match='injected'):
        calibrate_domains(model, tok, [task()], settings(), tmp_path, model_identity='base')
    assert flags == [p.requires_grad for p in params]
    assert modes == [m.training for m in model.modules()]
    assert params[1].grad is grad and torch.all(grad == 1)
    assert dict(attn.k_proj._forward_hooks) == prior
    assert not (tmp_path/'calibration.pt').exists()
    handle.remove()


@pytest.mark.parametrize('changes', [
    {'split': 'eval'}, {'calibration_spans': []}, {'calibration_spans': [[7, 9]]},
    {'calibration_spans': [[6, 7]]}, {'calibration_spans': [[0.5, 3]]},
    {'calibration_spans': [[False, 3]]}, {'reference': ''},
])
def test_rejects_invalid_supervision(tmp_path, changes):
    from improving.spd_domains import calibrate_domains
    model, tok = tiny_model_and_tokenizer()
    with pytest.raises(ValueError):
        calibrate_domains(model, tok, [{**task(), **changes}], settings(), tmp_path, model_identity='base')


def test_rejects_truncation_and_nonhalf_rank(tmp_path):
    from improving.spd_domains import calibrate_domains
    model, tok = tiny_model_and_tokenizer()
    for overrides in ({'max_length': 3}, {'rank_fraction': .25}, {'rank': 1}, {'max_examples': 2}):
        with pytest.raises(ValueError):
            calibrate_domains(model, tok, [task()], {**settings(), **overrides}, tmp_path, model_identity='base')


def test_invalid_cached_projector_rejected(tmp_path):
    from improving.spd_domains import calibrate_domains
    model, tok = tiny_model_and_tokenizer()
    calibrate_domains(model, tok, [task()], settings(), tmp_path, model_identity='base')
    saved = torch.load(tmp_path/'calibration.pt', weights_only=True)
    next(iter(saved['modules'].values()))['spd_operator'].zero_()
    torch.save(saved, tmp_path/'calibration.pt')
    with pytest.raises(ValueError, match='projector'):
        calibrate_domains(model, tok, [task()], settings(), tmp_path, model_identity='base')


def test_default_layers_and_source_identity(tmp_path, monkeypatch):
    from improving import spd_domains
    model, tok = tiny_model_and_tokenizer()
    original = spd_domains.spectral.target_modules
    calls = []
    def select(model, *, layers):
        calls.append(layers)
        return original(model, layers=[0, 1])
    monkeypatch.setattr(spd_domains.spectral, 'target_modules', select)
    spd_domains.calibrate_domains(model, tok, [task()], {'max_length': 128}, tmp_path,
                                  model_identity='base')
    assert calls == [[24, 47]]
    saved = torch.load(tmp_path/'calibration.pt', weights_only=True)
    saved['metadata']['source_sha256']['_spd_upstream_utils.py'] = 'changed-source'
    torch.save(saved, tmp_path/'calibration.pt')
    with pytest.raises(ValueError, match='identity'):
        spd_domains.calibrate_domains(model, tok, [task()], {'max_length': 128}, tmp_path,
                                      model_identity='base')


def test_each_span_needs_a_causal_target(tmp_path):
    from improving.spd_domains import calibrate_domains
    model, tok = tiny_model_and_tokenizer()
    # One valid answer span must not hide an empty whitespace span.
    for changes in ({'calibration_spans': [[7, 8], [6, 7]]},
                    {'prompt': '', 'calibration_spans': [[0, 6]]}):
        with pytest.raises(ValueError, match='next-token'):
            calibrate_domains(model, tok, [{**task(), **changes}], settings(), tmp_path,
                              model_identity='base')


def test_svd_failure_also_restores_state(tmp_path, monkeypatch):
    from improving import spd_domains
    model, tok = tiny_model_and_tokenizer()
    model.train()
    parameters = list(model.parameters())
    parameters[0].grad = torch.ones_like(parameters[0])
    old_grad = parameters[0].grad
    flags = [p.requires_grad for p in parameters]
    def fail(_):
        raise RuntimeError('injected svd failure')
    monkeypatch.setattr(spd_domains, 'projector_record', fail)
    with pytest.raises(RuntimeError, match='svd'):
        spd_domains.calibrate_domains(model, tok, [task()], settings(), tmp_path,
                                      model_identity='base')
    assert model.training
    assert flags == [p.requires_grad for p in parameters]
    assert parameters[0].grad is old_grad and torch.all(old_grad == 1)
    assert all(not module._forward_hooks for module in model.modules())
    assert not (tmp_path/'calibration.pt').exists()


@pytest.mark.parametrize('span,valid', [
    ({'start': 7, 'end': 8, 'text': '1'}, True),
    ({'start': 7, 'end': 8, 'text': '2'}, False),
    ({'start': 7, 'end': 8}, False),
    ({'start': True, 'end': 8, 'text': '1'}, False),
])
def test_native_safety_span_schema(tmp_path, span, valid):
    from improving.spd_domains import calibrate_domains
    model, tok = tiny_model_and_tokenizer()
    item = {**task('safety'), 'calibration_spans': [span]}
    if valid:
        assert len(calibrate_domains(model, tok, [item], settings(), tmp_path, model_identity='base')) == 4
    else:
        with pytest.raises(ValueError):
            calibrate_domains(model, tok, [item], settings(), tmp_path, model_identity='base')
