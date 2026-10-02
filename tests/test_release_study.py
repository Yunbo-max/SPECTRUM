"""Offline regression specifications; no models, downloads, or generated code."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_runner', ROOT / 'scripts/run_release_study.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def make_plan(tmp_path, monkeypatch):
    seeds = tmp_path / 'private.json'
    # Artificial unit-test values, not research-run randomization.
    seeds.write_text(json.dumps({'data_seed': 100, 'replicates': {'r1': 200, 'r2': 300, 'r3': 400}}))
    assets_path = ROOT / 'configs/final/assets.json'
    assets = json.loads(assets_path.read_text())
    snapshots = {f'{name}/eval.jsonl': {'count': item['expected_count'], 'sha256': 'a'*64,
                                      'path': str(tmp_path / name / 'eval.jsonl')}
                 for name, item in assets['datasets'].items()}
    monkeypatch.setattr(runner, 'prepared_snapshots', lambda *_: snapshots)
    monkeypatch.setattr(runner, 'source_snapshot', lambda: {'fixture': 'b'*64})
    monkeypatch.setattr(runner, 'jsonl', lambda _: [{'split_seed': 100}])
    args = SimpleNamespace(backend='docker', allow_unsafe_local=False, workers=4,
        run_root=tmp_path / 'run', data_root=tmp_path / 'data/mbpp',
        benchmark_root=tmp_path / 'data/benchmarks', assets=assets_path,
        seed_file=seeds, profile='48gb')
    runner.build_plan(args)
    return args.run_root / 'plan/manifest.json'


def test_finite_release_matrix_and_budget(tmp_path, monkeypatch):
    manifest = runner.load_manifest(make_plan(tmp_path, monkeypatch))
    jobs = manifest['jobs']
    assert len(jobs) == 40
    assert sum(j['kind'] == 'training' for j in jobs) == 13
    assert sum(j['block'] == 'transfer' for j in jobs) == 24
    assert sum(j['block'] == 'decoder' for j in jobs) == 3
    budget = manifest['protocol']['candidate_budget']
    assert budget['method_replicate_rounds'] == 134
    assert budget['total_candidates'] == 7106080
    assert len({j['seed'] for j in jobs if j['block'] == 'core'}) == 3
    for job in jobs:
        assert job['command'] == runner.command_for(job)
        if job['kind'] == 'training':
            config = json.loads(Path(job['config']).read_text())
            assert config['model']['revision'] == manifest['protocol']['models'][job['model_key']]['revision']
            assert config['generation']['eval_samples'] == 64


def test_controls_keep_original_method_and_distinct_information(tmp_path, monkeypatch):
    manifest = runner.load_manifest(make_plan(tmp_path, monkeypatch))
    configs = {j['job_id']: json.loads(Path(j['config']).read_text())
               for j in manifest['jobs'] if j['kind'] == 'training'}
    assert configs['mechanism-fixed-r1']['calibration']['reestimate_each_round'] is False
    assert configs['mechanism-anchor-replay-r1']['methods'] == ['plain']
    assert configs['mechanism-anchor-replay-r1']['train']['fixed_anchor_replay'] is True
    assert configs['token-matched-r1']['train']['target_token_budget'] == 7200000
    for name, config in configs.items():
        if name.startswith('core-'):
            assert config['calibration']['tau'] == 1
            assert 'target_token_budget' not in config['train']
            assert 'fixed_anchor_replay' not in config['train']


def test_changed_or_missing_config_can_be_reported_but_not_executed(tmp_path, monkeypatch):
    path = make_plan(tmp_path, monkeypatch)
    original = runner.load_manifest(path)
    Path(original['jobs'][0]['config']).unlink()
    assert runner.load_manifest(path, verify_inputs=False)['jobs']
    with pytest.raises(FileNotFoundError):
        runner.load_manifest(path, verify_inputs=True)


def test_private_randomization_does_not_overwrite(tmp_path):
    path = tmp_path / 'private.json'
    runner.init_seeds(SimpleNamespace(output=path))
    assert len(set(runner.private_seeds(path)['replicates'].values())) == 3
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        runner.init_seeds(SimpleNamespace(output=path))


def test_pending_job_is_not_completed(tmp_path):
    job = {'job_id': 'pending', 'block': 'core', 'kind': 'training',
           'output_dir': str(tmp_path / 'absent'), 'rounds': 5,
           'methods': ['plain', 'ssd', 'spectral_soft']}
    assert runner.job_status(job)['status'] == 'pending'
    assert runner.job_status(job)['expected_stages'] == 16


def test_decoder_job_never_invokes_training(tmp_path, monkeypatch):
    manifest = runner.load_manifest(make_plan(tmp_path, monkeypatch))
    for job in manifest['jobs']:
        if job['block'] == 'decoder':
            assert job['command'][1] == 'scripts/evaluate_decoder.py'
            assert job['depends_on'] == ['core-qwen1.5b-r1']
            assert job['samples_per_task'] == 64
