import json
from pathlib import Path
import pytest
from improving.android.study import validate_config, seal_study, summarize_episodes, read_complete_stage


def config(tmp_path):
    return {'output_dir':str(tmp_path/'runs'),'model':{'checkpoint':str(tmp_path/'model')},
            'study':{'warmup_rounds':3,'rounds':3,'group_size':4,'spectral_fraction':0.5},
            'generation':{'temperature':0.7,'top_p':0.8,'max_new_tokens':256},
            'train':{'max_updates':16},'spectral':{'alpha':0.5,'tau':1.0}}


def test_invalid_collection_budget_is_rejected(tmp_path):
    c=config(tmp_path); c['study']['group_size']=3
    with pytest.raises(ValueError,match='even'):
        validate_config(c)


def test_sealed_study_refuses_changed_method(tmp_path):
    c=config(tmp_path); root=tmp_path/'run'
    seal_study(root,c,{'instances':[]},'source-a')
    seal_study(root,c,{'instances':[]},'source-a')
    c['spectral']['tau']=2
    with pytest.raises(ValueError,match='identity'):
        seal_study(root,c,{'instances':[]},'source-a')


def test_missing_episode_never_becomes_failed_score():
    with pytest.raises(ValueError,match='expected'):
        summarize_episodes([{'episode_id':'a','success':True,'steps':[]}],expected=2)


def test_eval_summary_retains_native_outcomes():
    rows=[{'episode_id':'a','instance_id':'x','success':True,'policy':'native','steps':[{'response_token_ids':[1,2],'action':{'action':'click'}}]},
          {'episode_id':'b','instance_id':'y','success':False,'policy':'native','steps':[]}]
    r=summarize_episodes(rows,expected=2)
    assert r['success_rate']==0.5 and r['episodes']==2 and r['response_tokens']==2


def test_incomplete_stage_is_not_resumed_as_success(tmp_path):
    stage=tmp_path/'stage'; stage.mkdir()
    (stage/'episodes.jsonl').write_text('')
    with pytest.raises(RuntimeError,match='Incomplete'):
        read_complete_stage(stage)


def test_resume_loads_only_named_operators(tmp_path):
    import torch
    from improving.android.study import load_operators
    path=tmp_path/'operators.pt'
    torch.save({'operators':{'layer.k_proj':torch.eye(2)},'anchor':{'extra':1},'feedback':{}},path)
    assert list(load_operators(path))==['layer.k_proj']


def test_empty_supervision_records_no_update_and_keeps_checkpoint(tmp_path):
    from improving.android.study import _train
    model=tmp_path/'model'; model.mkdir(); (model/'config.json').write_text('{}')
    stage=tmp_path/'stage'
    result=_train(str(model),[],stage,config(tmp_path),'grsd')
    assert result==str(model)
    receipt=json.loads((stage/'complete.json').read_text())
    assert receipt['training']['status']=='no_update'
    assert receipt['training']['optimizer_steps']==0


def test_changed_referenced_image_is_rejected(tmp_path):
    from improving.android.study import _finish
    stage=tmp_path/'stage'; stage.mkdir()
    image=tmp_path/'image.png'; image.write_bytes(b'original')
    _finish(stage,{},external_paths=[image])
    image.write_bytes(b'changed')
    with pytest.raises(ValueError,match='External'):
        read_complete_stage(stage)
