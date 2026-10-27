"""Software contract specifications only; no models, downloads or real grading.

Artificial records below check denominator/binding arithmetic. They do not
qualify native datasets, scientific outcomes or model quality.
"""
import copy
import math
from pathlib import Path

import pytest

from improving import text_study, text_tasks
from improving.utils import stable_hash


def prepared_fixture(monkeypatch):
    monkeypatch.setattr(text_study, 'file_sha', lambda _: 'fixture-builder')
    config = {'domain': 'math', 'data': {'output_dir': 'fixture', 'train_size': 1024}}
    manifest = {'identity': {'domain': 'math', 'data': copy.deepcopy(config['data']),
                             'seed_sha256': stable_hash(17), 'builder_sha256': 'fixture-builder'},
                'evaluation_counts': {'math500': 500}}
    return config, manifest


@pytest.mark.parametrize('mutation,match', [
    ('domain', 'domain/splits'), ('selection', 'domain/splits'),
    ('population', 'native populations'), ('seed', 'randomization'), ('builder', 'builder changed'),
])
def test_prepared_identity_rejects_changed_scientific_population(monkeypatch, mutation, match):
    config, manifest = prepared_fixture(monkeypatch)
    text_study.validate_prepared_binding(config, manifest, 17)
    if mutation == 'domain':
        manifest['identity']['domain'] = 'qa'
    elif mutation == 'selection':
        config['data']['train_size'] = 512
    elif mutation == 'population':
        manifest['evaluation_counts']['math500'] = 499
    elif mutation == 'seed':
        manifest['identity']['seed_sha256'] = stable_hash(18)
    else:
        manifest['identity']['builder_sha256'] = 'changed'
    with pytest.raises(ValueError, match=match):
        text_study.validate_prepared_binding(config, manifest, 17)


def task(task_id, benchmark, answer='A'):
    return {'task_id': task_id, 'prompt': 'Artificial contract example', 'original_prompt': task_id,
            'source': 'software-fixture', 'split': 'eval', 'benchmark': benchmark,
            'answer': answer, 'options': ['first', 'second', 'third', 'fourth']}


def test_math_unbiased_pass_at_k_and_scoped_runtime_verification(monkeypatch):
    from improving import native_sandbox
    calls = {'runtime': 0, 'grader_verification': 0, 'answers': 0}
    runtime = {'fixture': 'runtime'}
    context = {'fixture': 'verified-grader'}

    def runtime_identity():
        calls['runtime'] += 1
        return runtime

    def verify(_):
        calls['grader_verification'] += 1
        return context

    def grade(answer, expected, root, sandbox, *, native_identity, grader_context):
        calls['answers'] += 1
        assert native_identity is runtime and grader_context is context
        return answer == expected, 'parsed'

    monkeypatch.setattr(native_sandbox, 'runtime_identity', runtime_identity)
    monkeypatch.setattr(text_tasks, '_verified_math_grader', verify)
    monkeypatch.setattr(text_tasks, 'grade_math_sandboxed', grade)
    tasks = [task('FixtureMath/one', 'math500', '2')]
    records = [{'task_id': tasks[0]['task_id'], 'sample_id': index,
                'completion': r'\boxed{2}' if index < 3 else r'\boxed{3}'} for index in range(16)]
    _, metrics = text_tasks.score_text_records(tasks, records, expected_samples=16,
                                               grader_root='fixture', sandbox={'timeout': 10})
    assert metrics['math500']['pass@1'] == pytest.approx(3 / 16)
    assert metrics['math500']['pass@4'] == pytest.approx(1 - math.comb(13, 4) / math.comb(16, 4))
    assert metrics['math500']['pass@16'] == 1
    assert calls == {'runtime': 1, 'grader_verification': 1, 'answers': 16}
    # A second invocation re-verifies; no stale global cache is reused.
    text_tasks.score_text_records(tasks, records, expected_samples=16,
                                  grader_root='fixture', sandbox={'timeout': 10})
    assert calls == {'runtime': 2, 'grader_verification': 2, 'answers': 32}


def test_qa_unparsed_is_wrong_without_shrinking_denominator():
    tasks = [task('FixtureQA/one', 'mmlu_pro'), task('FixtureQA/two', 'mmlu_pro')]
    records = [{'task_id': tasks[0]['task_id'], 'sample_id': 0, 'completion': 'the answer is (A)'},
               {'task_id': tasks[1]['task_id'], 'sample_id': 0, 'completion': 'Unable to answer.'}]
    scored, metrics = text_tasks.score_text_records(tasks, records, expected_samples=1)
    assert [row['correct'] for row in scored] == [True, False]
    assert metrics['mmlu_pro']['tasks'] == metrics['mmlu_pro']['samples'] == 2
    assert metrics['mmlu_pro']['accuracy'] == 0.5
    assert metrics['mmlu_pro']['unparsed_samples'] == 1
    assert not any(key.startswith('pass@') for key in metrics['mmlu_pro'])


def test_qa_missing_or_duplicate_predictions_never_score_as_complete():
    tasks = [task('FixtureQA/one', 'gpqa_diamond'), task('FixtureQA/two', 'gpqa_diamond')]
    record = {'task_id': tasks[0]['task_id'], 'sample_id': 0, 'completion': 'answer is (A)'}
    with pytest.raises(ValueError, match='every expected task/sample'):
        text_tasks.score_text_records(tasks, [record], expected_samples=1)
    with pytest.raises(ValueError, match='Duplicate completion'):
        text_tasks.score_text_records(tasks, [record, record], expected_samples=1)
