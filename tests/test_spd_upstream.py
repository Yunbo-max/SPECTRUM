import copy
import importlib.util
import json
from pathlib import Path

import pytest
import torch

from tests.helpers import tiny_model_and_tokenizer


def test_projector_matches_pinned_upstream_centered_svd():
    from improving.spd_upstream import projector_record
    path = Path('/mnt/c/ai/SPD/utils.py')
    if not path.exists():
        path = Path(__file__).parents[1] / 'src/improving/_spd_upstream_utils.py'
    spec = importlib.util.spec_from_file_location('upstream_oracle', path)
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    g = torch.randn(37, 8, generator=torch.Generator().manual_seed(31)) + torch.arange(8) * 10
    basis, _, rank = upstream.extract_subspace(g, half_rank=True)
    record = projector_record(g)
    assert rank == record['effective_rank'] == 4
    assert torch.equal(record['spd_operator'], upstream.compute_projection_matrix(basis).double())
    assert torch.allclose(record['covariance'], (g-g.mean(0)).double().T @ (g-g.mean(0)).double() / len(g))
    assert torch.allclose(record['spd_operator'] @ record['spd_operator'], record['spd_operator'], atol=1e-6)


def test_calibration_cache_and_failure_restore_state(tmp_path, monkeypatch):
    from improving.spd_upstream import calibrate, upstream
    model, tok = tiny_model_and_tokenizer()
    task = {'task_id':'cal/1', 'split':'calibration', 'original_prompt':'Write a function',
            'reference':'def f ( ) : return 1', 'tests':'assert f ( ) == 1'}
    settings = {'max_examples':1, 'max_length':128, 'upstream_spd':True}
    model.train()
    flags = [p.requires_grad for p in model.parameters()]
    before = {n:p.detach().clone() for n,p in model.named_parameters()}
    result = calibrate(model, tok, [task], settings, tmp_path/'cal.pt', 'initial')
    assert model.training and flags == [p.requires_grad for p in model.parameters()]
    assert all(torch.equal(before[n], p) for n,p in model.named_parameters())
    assert all(not m._forward_hooks for m in model.modules())
    assert result.keys() == calibrate(model, tok, [task], settings, tmp_path/'cal.pt', 'initial').keys()
    with pytest.raises(ValueError, match='identity'):
        calibrate(model, tok, [{**task, 'tests':'assert f ( ) == 2'}], settings, tmp_path/'cal.pt', 'initial')
    with pytest.raises(ValueError, match='calibration'):
        calibrate(model, tok, [{**task, 'split':'eval'}], settings, tmp_path/'eval.pt', 'initial')
    def fail(model, *args, **kwargs):
        model.model.layers[0].self_attn.k_proj.register_forward_hook(lambda *a: None)
        next(model.parameters()).requires_grad_(False)
        raise RuntimeError('injected failure')
    monkeypatch.setattr(upstream, 'collect_kv_gradients', fail)
    with pytest.raises(RuntimeError, match='injected failure'):
        calibrate(model, tok, [task], settings, tmp_path/'failure.pt', 'initial')
    assert flags == [p.requires_grad for p in model.parameters()]
    assert all(not m._forward_hooks for m in model.modules())


def test_upstream_baseline_five_rounds_and_resume(tmp_path):
    from improving.pipeline import run_experiment
    from improving.data import write_jsonl
    model, tok = tiny_model_and_tokenizer()
    model.save_pretrained(tmp_path/'model')
    tok.save_pretrained(tmp_path/'model')
    paths = {}
    for split, prompt in zip(('train','calibration','validation','eval'), ('Write a function','Sort the list','hello world','Write x')):
        p=tmp_path/(split+'.jsonl')
        write_jsonl(p,[{'task_id':split+'/1','split':split,'source':'fixture','prompt':prompt,'original_prompt':prompt,
                        'reference':'def f ( ) : return 1','tests':'assert f ( ) == 1'}])
        paths[split]=str(p)
    config={'seed':43,'model':{'name':str(tmp_path/'model'),'device':'cpu','dtype':'float32'},
            'data':paths,'output_dir':str(tmp_path/'run'),'methods':['spd_upstream'],'rounds':5,
            'calibration':{'max_examples':1,'max_length':128,'upstream_spd':True,'rank_fraction':.5},
            'generation':{'train_samples':1,'eval_samples':2,'batch_size':2,'max_new_tokens':4,'max_prompt_tokens':32,'temperature':.8},
            'train':{'epochs':1,'batch_size':1,'gradient_accumulation_steps':1,'learning_rate':.01,
                     'max_length':64,'lora_rank':2,'lora_alpha':2,'gradient_checkpointing':False},
            'evaluation':{'backend':'none','ks':[1,2],'correct_budget':1}}
    run_experiment(config)
    stages=[tmp_path/f'run/spd_upstream/round_{i}' for i in range(1,6)]
    assert all((p/'complete.json').exists() and (p/'model/config.json').exists() for p in stages)
    seals=[(p/'complete.json').read_bytes() for p in stages]
    run_experiment(config,resume=True)
    assert seals==[(p/'complete.json').read_bytes() for p in stages]
    saved=torch.load(stages[-1]/'calibration.pt',weights_only=True)
    assert saved['metadata']['upstream_commit']=='caa408c699f13c209a6484f626939cf3a3dcbe18'


def test_c48_preserves_old_hard_baseline():
    path=Path(__file__).parents[1]/'scripts/rebuttal_cases.py'
    spec=importlib.util.spec_from_file_location('rebuttal',path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.one_case('c45')['method']=='spd_hard'
    row=mod.one_case('c48')
    assert (row['method'],row['rounds'],row['model'])==('spd_upstream',5,'qwen1.5b')


def test_folded_projection_matches_upstream_activation_hook_and_restores():
    from improving.spd_upstream import projector_record
    from improving.spectral import folded_operators
    model=torch.nn.Sequential(torch.nn.Linear(8,8,bias=True))
    operator=projector_record(torch.randn(30,8))['spd_operator']
    inputs=torch.randn(2,7,8)
    expected=model(inputs) @ operator.float()
    before=copy.deepcopy(model.state_dict())
    with folded_operators(model, {'0':operator}):
        assert torch.allclose(model(inputs),expected,atol=2e-6,rtol=2e-5)
    assert all(torch.equal(before[k],v) for k,v in model.state_dict().items())


def test_actual_calibration_matches_upstream_assertion_only_loss(tmp_path, monkeypatch):
    from improving.spd_upstream import calibrate, upstream, calibration_texts, projector_record
    model,tok=tiny_model_and_tokenizer()
    task={'task_id':'cal/1','split':'calibration','original_prompt':'Write a function',
          'reference':'def f ( ) : return 1','tests':'assert f ( ) == 1'}
    text=calibration_texts([task])[0]
    start=text.index(task['tests'])
    spans=[[(start,start+len(task['tests']))]]
    oracle=copy.deepcopy(model)
    for p in oracle.parameters():
        p.requires_grad_(False)
    gradients=upstream.collect_kv_gradients(oracle,tok,[text],[0,1],max_length=128,
                                           device='cpu',label_char_spans=spans)
    original=upstream.collect_kv_gradients
    seen=[]
    def capture(*args, **kwargs):
        seen.append(kwargs.get('label_char_spans'))
        return original(*args,**kwargs)
    monkeypatch.setattr(upstream,'collect_kv_gradients',capture)
    result=calibrate(model,tok,[task],{'max_examples':1,'max_length':128},tmp_path/'cal.pt','initial')
    assert seen==[spans]
    for name,record in result.items():
        layer=int(name.split('.layers.')[1].split('.')[0])
        key='K_grads' if name.endswith('.k_proj') else 'V_grads'
        expected=projector_record(gradients[layer][key])
        assert torch.equal(record['spd_operator'],expected['spd_operator'])
