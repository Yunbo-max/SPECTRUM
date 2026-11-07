import json
import pytest
from tests.helpers import tiny_model_and_tokenizer
from improving.pipeline import run_experiment
from improving.data import write_jsonl


def test_base_once_and_one_method_only(tmp_path, monkeypatch):
    model, tokenizer = tiny_model_and_tokenizer()
    model.save_pretrained(tmp_path / 'tiny')
    tokenizer.save_pretrained(tmp_path / 'tiny')
    paths = {}
    for split, prompt in zip(('train','calibration','validation','eval'),
                             ('Write a function','Sort the list','hello world','Write x')):
        p = tmp_path / (split + '.jsonl')
        write_jsonl(p, [{'task_id': split+'/1', 'prompt': prompt, 'reference': 'def f ( ) : return 1',
                        'source': 'fixture', 'split': split}])
        paths[split] = str(p)
    config = {'seed': 42, 'model': {'name': str(tmp_path/'tiny'), 'device':'cpu','dtype':'float32'},
              'data': paths, 'output_dir':str(tmp_path/'run'), 'methods':['plain','ssd'], 'rounds':1,
              'generation':{'train_samples':1,'eval_samples':2,'batch_size':2,
                            'max_new_tokens':4,'max_prompt_tokens':32,'temperature':.8},
              'train':{'epochs':1,'batch_size':1,'gradient_accumulation_steps':1,'learning_rate':.01,
                       'max_length':64,'lora_rank':2,'lora_alpha':2,'gradient_checkpointing':False},
              'evaluation':{'backend':'none','ks':[1,2],'correct_budget':1}}
    root = tmp_path/'run'
    result = run_experiment(config, base_only=True)
    assert result['methods'] == []
    assert not (root/'plain').exists() and not (root/'ssd').exists()
    base = (root/'base/complete.json').read_bytes()
    manifest = (root/'manifest.json').read_bytes()
    result = run_experiment(config, method='plain', resume=True)
    assert result['methods'] == ['plain']
    assert (root/'plain/round_1/complete.json').exists()
    assert not (root/'ssd').exists()
    assert (root/'base/complete.json').read_bytes() == base
    assert (root/'manifest.json').read_bytes() == manifest
    assert (root/'run_status.plain.json').exists()
    with pytest.raises(ValueError, match='method'):
        run_experiment(config, method='spectral_soft', resume=True)
    from improving.longitudinal import evaluate_checkpoints
    def inspect_selected_checkpoint(settings, checkpoint):
        assert checkpoint == root/'plain/round_1/model'
        raise RuntimeError('selected checkpoint reached')
    monkeypatch.setattr('improving.modeling.load_model', inspect_selected_checkpoint)
    with pytest.raises(RuntimeError, match='selected checkpoint reached'):
        evaluate_checkpoints(root, tmp_path/'transfer', samples=2, methods=['plain'], rounds=[1],
                             include_base=False, evaluator=lambda *a, **k: None, evaluator_identity={})


def test_base_only_rejects_method_selection():
    with pytest.raises(ValueError, match='base_only'):
        run_experiment({}, base_only=True, method='plain')
