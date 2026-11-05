"""No-network tests for frozen rebuttal plans, complete evidence and uncertainty."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def runner():
    spec = importlib.util.spec_from_file_location('rebuttal_runner', ROOT/'scripts/run_iclr_rebuttal.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_configs(tmp_path):
    m = runner()
    seeds = {'data_seed': 101, 'training_seeds': [11, 22, 33]}
    return m, m.build_configs(tmp_path, seeds)


def test_core_has_three_independent_trajectories_and_matched_arms(tmp_path):
    _, configs = fixture_configs(tmp_path)
    main = [v for v in configs.values() if v['block'] == 'core']
    assert len(main) == 3
    assert len({v['config']['seed'] for v in main}) == 3
    for v in main:
        cfg = v['config']
        assert cfg['rounds'] == 10
        assert cfg['methods'] == ['plain', 'ssd', 'spectral_soft', 'spectral_learned']
        assert cfg['train']['loss_scope'] == 'all'
        assert cfg['calibration']['matched_reference_fit_examples'] == 40
        assert cfg['diagnostics']['transfer_gap']['rounds'] == [1,5,8,10]
        assert cfg['evaluation']['backend'] == 'docker'
        assert cfg['checkpoint_retention'] == 'latest'
    assert len({json.dumps(v['config']['data'],sort_keys=True) for v in main}) == 1


def test_every_planned_config_is_accepted_by_real_pipeline(tmp_path):
    from improving.pipeline import validate_config
    _, configs = fixture_configs(tmp_path)
    for entry in configs.values():
        validate_config(entry['config'])


def test_crossfamily_uses_pinned_models_and_fixed_endpoints(tmp_path):
    _, configs = fixture_configs(tmp_path)
    cross = [v for v in configs.values() if v['block']=='crossfamily']
    assert {v['model'] for v in cross} == {'llama8b','deepseek6.7b'}
    assert all(v['config']['rounds']==5 for v in cross)
    assert all(len(v['config']['model']['revision'])==40 for v in cross)


def test_completion_ablation_changes_all_arms_not_only_ours(tmp_path):
    _, configs = fixture_configs(tmp_path)
    objective = [v for v in configs.values() if v['block']=='objective']
    assert len(objective)==1
    assert objective[0]['config']['methods']==configs['core-qwen7b-r1']['config']['methods']
    left = dict(configs['core-qwen7b-r1']['config']['train'])
    right = dict(objective[0]['config']['train'])
    assert right.pop('loss_scope') == 'completion'
    left.pop('loss_scope')
    assert left == right


def test_budgets_count_base_and_all_three_dev_states(tmp_path):
    m, configs=fixture_configs(tmp_path)
    counts=m.budget(configs['core-qwen7b-r1']['config'])
    assert counts['training_completions']==291*16*10*4
    assert counts['test_completions']==500*64*(1+10*4)
    assert counts['dev_completions']==30*64*3*4*4
    assert counts['probe_completions']==8*10


def test_unknown_or_empty_job_selection_is_not_a_success(tmp_path):
    m, configs=fixture_configs(tmp_path)
    with pytest.raises(ValueError, match='No jobs'):
        m.select_jobs(configs, block='core', model='llama8b', replicate='all')


def test_new_seed_file_is_private_unique_and_never_replaced(tmp_path):
    m=runner()
    m.initialize(tmp_path)
    path=tmp_path/'private_seeds.json'
    original=path.read_bytes()
    seeds=json.loads(original)
    assert len(set(seeds['training_seeds']))==3
    assert path.stat().st_mode & 0o777 == 0o600
    m.initialize(tmp_path)
    assert path.read_bytes()==original


def test_missing_result_is_none_not_zero(tmp_path):
    m=runner()
    row=m.round_evidence(tmp_path/'missing', method='plain', round_index=1)
    assert row['status']=='missing'
    assert row['metrics'] is None


def test_result_receipt_detects_tampering_and_requires_metrics(tmp_path):
    m=runner()
    (tmp_path/'evaluation.metrics.json').write_text('{}')
    marker={'status':'completed','files':{'evaluation.metrics.json':m.cf.sha(tmp_path/'evaluation.metrics.json')}}
    (tmp_path/'complete.json').write_text(json.dumps(marker))
    with pytest.raises((ValueError,KeyError)):
        m.round_evidence(tmp_path, method='plain', round_index=1)
    (tmp_path/'evaluation.metrics.json').write_text('{"altered": true}')
    with pytest.raises(ValueError,match='integrity'):
        m.round_evidence(tmp_path, method='plain', round_index=1)


def test_seed_summary_does_not_pool_tasks_as_independent_runs():
    m=runner()
    rows=[{'replicate':f'r{i+1}','value':x} for i,x in enumerate([.4,.5,.6])]
    out=m.seed_summary(rows,expected=3)
    assert out['n_completed']==3
    assert out['mean']==pytest.approx(.5)
    assert out['sample_sd']==pytest.approx(.1)
    assert out['status']=='complete'
    incomplete=m.seed_summary(rows[:2],expected=3)
    assert incomplete['status']=='incomplete'
    assert incomplete['expected_replicates']==3


def test_backend_choice_is_frozen_and_local_requires_explicit_acknowledgement(tmp_path):
    m=runner()
    with pytest.raises(ValueError, match='unsafe'):
        m.initialize(tmp_path, backend='local')
    m.initialize(tmp_path, backend='bwrap')
    m.initialize(tmp_path)
    with pytest.raises(ValueError, match='Frozen'):
        m.initialize(tmp_path, backend='docker')


def test_transfer_proxy_keeps_declared_backend(tmp_path):
    m, jobs=fixture_configs(tmp_path)
    job=jobs['core-qwen7b-r1']
    job['config']['evaluation']['backend']='bwrap'
    proxy=m.transfer_proxy(tmp_path,job)
    assert proxy['settings']['evaluation']['backend']=='bwrap'
    assert proxy['settings']['transfer']['round']==10
