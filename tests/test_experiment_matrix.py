import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('matrix', Path(__file__).parents[1]/'scripts/run_experiment_matrix.py')
matrix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix)


def test_matrix_is_ten_round_single_method_and_complete():
    jobs = matrix.case_specs()
    assert len(jobs) == 72
    assert len({j['id'] for j in jobs}) == len(jobs)
    train = [j for j in jobs if j['kind'].endswith('_train')]
    assert len(train) == 18  # Includes three archived Qwen and three blocked ARC arms.
    assert all(j['rounds'] == 10 and isinstance(j['method'], str) for j in train)
    assert len([j for j in train if j['availability'] == 'enabled']) == 12
    assert all(j['rounds'] == 0 for j in jobs if j['kind'].endswith('_base'))
    ids = {j['id'] for j in jobs}
    assert all(set(j['depends_on']) <= ids for j in jobs)
    assert all(j['source_round'] == 10 for j in jobs if j['kind'] == 'code_eval' and j['method'] != 'base')


def test_training_requires_own_base_and_transfer_requires_own_method():
    jobs = matrix.case_specs()
    ready = {j['id'] for j in matrix.ready_cases(jobs, set())}
    assert 'code.llama8b.mbpp.base' in ready
    assert 'code.llama8b.mbpp.plain' not in ready
    ready = {j['id'] for j in matrix.ready_cases(jobs, {'code.llama8b.mbpp.base'})}
    assert 'code.llama8b.mbpp.plain' in ready
    assert 'eval.llama8b.humanevalplus.plain' not in ready
    done = {'code.llama8b.mbpp.base','code.llama8b.mbpp.plain'}
    ready = {j['id'] for j in matrix.ready_cases(jobs, done)}
    assert 'eval.llama8b.humanevalplus.plain' in ready
    assert 'eval.llama8b.humanevalplus.ssd' not in ready
    assert all(not name.startswith('arc.') for name in ready)
    assert all(not name.startswith('code.qwen7b.mbpp.') for name in ready)


def test_completed_rejects_changed_or_missing_payload(tmp_path):
    native=tmp_path/'native';native.mkdir()
    payload=native/'evaluation.jsonl';payload.write_text('original')
    marker=native/'complete.json'
    marker.write_text(json.dumps({'files':{'evaluation.jsonl':matrix.sha(payload)}}))
    m={'root':str(tmp_path),'fingerprint':'test','jobs':[{'id':'one'}]}
    matrix.save(tmp_path/'cases/one/complete.json',{'plan_fingerprint':'test','markers':{str(marker):matrix.sha(marker)}})
    assert matrix.completed(m)=={'one'}
    payload.write_text('corrupt')
    with pytest.raises(ValueError): matrix.completed(m)
    payload.unlink()
    with pytest.raises((ValueError, FileNotFoundError)): matrix.completed(m)


def test_queue_termination_uses_cleanup_exception():
    with pytest.raises(KeyboardInterrupt): matrix.terminate_queue(15,None)
