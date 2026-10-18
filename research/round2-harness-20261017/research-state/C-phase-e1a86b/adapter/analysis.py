"""Authored, unexecuted B02 development analysis; never executes generated code.

CLI: python analysis.py --root PROJECT --bundle reviewed-score-bundle.json --output DIR
Bundle contains protocol_ref, task_manifest_ref ({task_ids: original 500 IDs}),
metrics_ref and exactly six runs with arm, seed, method, raw_ref, scored_ref,
generation_manifest_ref, generation_identity_ref, generation_receipt_ref, scoring_receipt_ref. Every ref is {path, sha256}.
Scoring receipts are *future independently reviewed adapter outputs*, not supplied
by this module: status=verified, raw_ref/scored_ref/protocol_ref, native_replay_ref,
isolation_review_ref, scorer_source_ref, and per_sample_outcomes with task_id,
sample_id and classification=model_outcome|infrastructure_error|unscored.
These bindings check consistency, not authenticity or scientific acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import sys

METRICS_SHA = '9e2fc30e1c8df0c9d9ff95f6a025f69245226efb6cf29ee9738243b30a311528'
BASE_REVISION = '2e1fd397ee46e1388853d2af2c993145b0f1098a'
SEEDS = (43, 45)
ARMS = ('F', 'P', 'A')
MODEL_STATUSES = {'passed', 'failed', 'compile_error', 'runtime_error', 'timeout', 'empty'}


class PendingEvidence(ValueError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_ref(root, ref):
    if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
        raise ValueError('Every ref must contain exactly path and sha256')
    path = (Path(root) / ref['path']).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Reference escapes project root')
    if not path.is_file():
        raise PendingEvidence(f'Missing evidence: {ref["path"]}')
    if digest(path) != ref['sha256']:
        raise ValueError(f'Changed evidence: {ref["path"]}')
    return path


def verify_nested_refs(root, value):
    if isinstance(value, dict):
        if set(value) == {'path', 'sha256'}:
            resolve_ref(root, value)
        else:
            for item in value.values():
                verify_nested_refs(root, item)
    elif isinstance(value, list):
        for item in value:
            verify_nested_refs(root, item)


def read_json(root, ref):
    return json.loads(resolve_ref(root, ref).read_text())


def read_rows(root, ref):
    path = resolve_ref(root, ref)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def indexed(rows, ids):
    result = {}
    allowed = set(ids)
    for row in rows:
        key = (row.get('task_id'), row.get('sample_id'))
        if key[0] not in allowed or type(key[1]) is not int or not 0 <= key[1] < 16:
            raise ValueError(f'Unexpected task/sample: {key}')
        if key in result:
            raise ValueError(f'Duplicate task/sample: {key}')
        result[key] = row
    expected = {(task, sample) for task in ids for sample in range(16)}
    if set(result) != expected:
        raise PendingEvidence(f'Missing {len(expected-set(result))} samples; full500 endpoint unavailable')
    return result


def validate_rows(raw, scored, outcomes, ids, seed, method):
    raw_i, score_i, out_i = (indexed(x, ids) for x in (raw, scored, outcomes))
    inventory = []
    for key in raw_i:
        r, s, o = raw_i[key], score_i[key], out_i[key]
        for field, expected in [('seed', seed), ('round', 1), ('method', method)]:
            if r.get(field) != expected or s.get(field) != expected:
                raise ValueError(f'{key}: mismatched {field}')
        for field, value in r.items():
            if s.get(field) != value:
                raise ValueError(f'{key}: scoring changed raw field {field}')
        classification = o.get('classification')
        status = s.get('status')
        if classification != 'model_outcome':
            raise PendingEvidence(f'{key}: {classification}; never count infrastructure/unscored as model failure')
        if status not in MODEL_STATUSES or type(s.get('correct')) is not bool:
            raise PendingEvidence(f'{key}: missing/unknown scoring outcome')
        if s['correct'] != (status == 'passed'):
            raise ValueError(f'{key}: correct/status contradiction')
        provenance = s.get('evaluation_provenance')
        if not isinstance(provenance, dict) or provenance.get('provenance_version') != 2:
            raise PendingEvidence(f'{key}: missing actual scorer provenance')
        backend = provenance.get('backend', '')
        if backend in {'', 'none', 'local', 'unsafe_local', 'docker'} or 'docker' in backend.lower():
            raise PendingEvidence(f'{key}: unqualified scoring backend {backend!r}')
        if not s['correct']:
            inventory.append({'task_id': key[0], 'sample_id': key[1], 'status': status,
                              'verification_error': s.get('verification_error'),
                              'interpretation': 'observed_model_outcome_not_semantic_cause'})
    return inventory


def quantile(values, q):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    left = int(pos)
    return ordered[left] + (ordered[min(left + 1, len(ordered)-1)] - ordered[left]) * (pos-left)


def paired_summary(values, ids, samples=10000, seed=1042, confidence=.9875):
    """Equal-weight tasks; preserve nulls and fixed common eligibility."""
    eligible = [task for task in ids if values[task] is not None]
    missing = [task for task in ids if values[task] is None]
    if not eligible:
        return {'mean': None, 'ci': None, 'eligible_tasks': 0, 'total_tasks': len(ids),
                'missing_task_ids': missing, 'empty_bootstraps': samples, 'all_task_mean': None}
    observed = sum(values[t] for t in eligible) / len(eligible)
    rng = random.Random(seed)
    draws, empty = [], 0
    # Resample original task universe, retaining eligibility and paired structure.
    for _ in range(samples):
        picked = [values[ids[rng.randrange(len(ids))]] for _ in ids]
        available = [v for v in picked if v is not None]
        if available:
            draws.append(sum(available)/len(available))
        else:
            empty += 1
    alpha = (1-confidence)/2
    return {'mean': observed, 'all_task_mean': observed if not missing else None,
            'ci': [quantile(draws, alpha), quantile(draws, 1-alpha)] if draws else None,
            'confidence': confidence, 'eligible_tasks': len(eligible), 'total_tasks': len(ids),
            'missing_task_ids': missing, 'empty_bootstraps': empty}


def get_metric(task, metric):
    if metric == 'pass@1':
        return task['pass_at_k']['1']
    if metric == 'C16':
        return task['implementation_proxy']['coverage_at_k']['16']
    return task['implementation_proxy']['correct_matched_coverage_at_budgets'][metric[1:]]


def effect_values(summaries, ids, high, low, metric, seeds=SEEDS):
    values = {}
    for task in ids:
        pairs = [(get_metric(summaries[(high, s)]['per_task'][task], metric),
                  get_metric(summaries[(low, s)]['per_task'][task], metric)) for s in seeds]
        # All arm x repeat measurements must exist: changing subsets cannot be averaged.
        values[task] = None if any(a is None or b is None for a, b in pairs) else sum(a-b for a, b in pairs)/len(pairs)
    return values


def calculate(summaries, ids):
    effects = {}
    for high, low in [('P', 'F'), ('A', 'P')]:
        result = {}
        for metric in ('pass@1', 'C16', 'D4', 'D8', 'D16'):
            vals = effect_values(summaries, ids, high, low, metric)
            main = metric in {'pass@1', 'C16'}
            result[metric] = {'repeat_mean': paired_summary(vals, ids, confidence=.9875 if main else .95),
                             'per_task_repeat_mean': vals,
                             'by_seed': {str(s): paired_summary(effect_values(summaries, ids, high, low, metric, (s,)), ids, samples=0) for s in SEEDS},
                             'multiplicity': 'four_primary_contrasts_Bonferroni' if main else 'exploratory_pointwise',
                             'direction': high+' minus '+low}
        effects[high+'-'+low] = result
    sensitivity = {}
    for arm in ARMS:
        sensitivity[arm] = {}
        for metric in ('pass@1', 'C16', 'D4', 'D8', 'D16'):
            vals = {}
            for task in ids:
                a = get_metric(summaries[(arm,45)]['per_task'][task], metric)
                b = get_metric(summaries[(arm,43)]['per_task'][task], metric)
                vals[task] = None if a is None or b is None else a-b
            sensitivity[arm][metric] = {'paired': paired_summary(vals, ids, samples=0), 'per_task': vals}
    return {'effects': effects, 'F45_minus_F43': sensitivity['F'],
            'P45_minus_P43': sensitivity['P'], 'A45_minus_A43': sensitivity['A'],
            'bootstrap': {'unit': 'paired_task_with_all_arm_seed_measurements', 'samples': 10000, 'seed': 1042},
            'development_thresholds_only': {'pass@1_absolute': .02, 'C16_absolute': .5},
            'primary_full500_available': {contrast: {metric: result[metric]['repeat_mean']['eligible_tasks'] == 500 for metric in ('pass@1', 'C16')} for contrast, result in effects.items()},
            'scientific_acceptance': 'pending_independent_review',
            'caveats': ['AST coverage is not semantic diversity.', 'Two decoding seeds cannot exclude randomness or estimate training variance.',
                        'Task bootstrap does not establish training replication.', 'A-P is reference-supervision alternative, not pure information causality.',
                        'Nonsignificance is not equivalence/noninferiority.', 'D uses joint arm-and-repeat eligible intersection; never full500 when missing.',
                        'B03/S04/E04, strong SSD/n64 matrix, training repeats and untouched confirmation remain pending.']}


def same_ref(root, left, right):
    return resolve_ref(root, left) == resolve_ref(root, right) and left['sha256'] == right['sha256']


def validate_arm_identity(run, identity, manifest, training=None):
    """Pure metadata checks; caller verifies every pin and stage receipt."""
    arm, seed = run['arm'], run['seed']
    if arm not in ARMS or run.get('method') != arm:
        raise ValueError('Arm cannot relabel a different generation method')
    for field, expected in [('arm',arm),('seed',seed),('round',1),('stage','evaluation')]:
        if identity.get(field) != expected:
            raise ValueError('Generation identity differs: '+field)
    if manifest.get('method') != arm or manifest.get('model_identity') != identity.get('model_identity'):
        raise ValueError('Manifest arm/model differs from generation identity')
    cp = identity.get('checkpoint_receipt_ref')
    if arm == 'F':
        if cp is not None or identity.get('model_identity') != BASE_REVISION:
            raise ValueError('F must be the exact frozen base revision')
    else:
        if not isinstance(cp,dict) or identity.get('model_identity') != cp.get('sha256'):
            raise ValueError('Trained model must identify its actual checkpoint receipt')
        if training is None or training.get('status') != 'completed' or training.get('stage') != 'train-'+arm:
            raise ValueError('Missing completed arm-specific training receipt')
        result = training.get('result', {})
        if result.get('arm') != arm or result.get('training_seed') != 44 or result.get('base_revision') != BASE_REVISION:
            raise ValueError('Training arm/seed/base lineage differs')


def validate_generation_identity(root, bundle, run, manifest):
    identity_path = resolve_ref(root, run['generation_identity_ref'])
    identity = read_json(root, run['generation_identity_ref'])
    stage_path = resolve_ref(root, run['generation_receipt_ref'])
    stage = read_json(root, run['generation_receipt_ref'])
    if stage.get('status') != 'completed' or stage.get('stage') != f"generate-eval-{run['arm']}-{run['seed']}":
        raise ValueError('Generation stage is not completed for this arm/seed')
    if stage.get('result') != identity:
        raise ValueError('Generation receipt result does not equal captured identity')
    if identity_path != stage_path.parent/'outputs'/'identity.json':
        raise ValueError('Identity is not an output of the cited generation stage')
    inventory = {item['path']:item['sha256'] for item in stage['outputs']}
    for field in ('generation_identity_ref','raw_ref','generation_manifest_ref'):
        path = resolve_ref(root, run[field])
        if not path.is_relative_to(stage_path.parent/'outputs'):
            raise ValueError('Generation artifact outside actual stage output directory')
        if inventory.get(str(path.relative_to(stage_path.parent/'outputs'))) != run[field]['sha256']:
            raise ValueError('Generation receipt did not retain the declared output')
    if not same_ref(root, identity['protocol_ref'], bundle['protocol_ref']) or not same_ref(root, stage['protocol_ref'],bundle['protocol_ref']):
        raise ValueError('Generation protocol differs')
    for field in ('raw_ref','generation_manifest_ref'):
        if not same_ref(root, identity[field], run[field]):
            raise ValueError('Generation identity differs from bundle '+field)
    cp = identity.get('checkpoint_receipt_ref')
    training = read_json(root, cp) if cp is not None else None
    validate_arm_identity(run, identity, manifest, training)
    verify_nested_refs(root, identity)
    if training is not None:
        verify_nested_refs(root, training)
        result = training['result']
        if not same_ref(root, training['protocol_ref'],bundle['protocol_ref']) or not same_ref(root,result['protocol_ref'],bundle['protocol_ref']):
            raise ValueError('Training protocol differs')
        synthetic = result['synthetic_ref']
        resolve_ref(root, synthetic)
        return synthetic
    return None


def analyze(root, bundle):
    protocol = read_json(root, bundle['protocol_ref'])
    cd = protocol.get('cd_development', {})
    if protocol.get('evidence_mode') != 'developmental' or cd.get('flow_profile') != 'work-harness-cd-v1' or cd.get('stage') != 'diagnosis':
        raise ValueError('Requires developmental diagnosis protocol under work-harness-cd-v1')
    resolve_ref(root, cd['cd_evidence_ref'])
    ids = read_json(root, bundle['task_manifest_ref'])['task_ids']
    if len(ids) != 500 or len(set(ids)) != 500 or any(not isinstance(t, str) or not t for t in ids):
        raise ValueError('Full endpoint requires exactly 500 unique original test IDs')
    original = read_json(root, {'path':'research-state/B01-scorer-source-binding-000003/hf-full-test-decoded.json', 'sha256':'02ec024e5ec83ab2e01d4f527ff6a80e431d83f39361d5754f8248830c292aaf'})
    if ids != [f"Mbpp/{r['task_id']}" for r in original]:
        raise ValueError('Task order differs from pinned original full/test500')
    metrics_ref = bundle['metrics_ref']
    if metrics_ref['sha256'] != METRICS_SHA:
        raise ValueError('Metrics source differs from pinned upstream bytes')
    metrics_path = resolve_ref(root, metrics_ref)
    spec = importlib.util.spec_from_file_location('pinned_spectrum_metrics', metrics_path)
    metrics = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(metrics)  # Pinned trusted analysis source, never a completion.
    runs = bundle['runs']
    if len(runs) != 6 or {(r['arm'], r['seed']) for r in runs} != {(a,s) for a in ARMS for s in SEEDS}:
        raise ValueError('Exactly six distinct F/P/A x 43/45 runs required')
    summaries, failures, manifest_identity = {}, {}, None
    evaluator = None
    synthetic_ref = None
    checkpoint_by_arm = {}
    common_prepared_ref = None
    common_profile_ref = None
    for run in runs:
        key = run['arm'], run['seed']
        manifest = read_json(root, run['generation_manifest_ref'])
        current_synthetic = validate_generation_identity(root,bundle,run,manifest)
        identity = read_json(root, run['generation_identity_ref'])
        checkpoint = identity['checkpoint_receipt_ref']
        if key[0] in checkpoint_by_arm:
            previous = checkpoint_by_arm[key[0]]
            if (previous is None) != (checkpoint is None) or (checkpoint is not None and
                    not same_ref(root, previous, checkpoint)):
                raise ValueError('Both decoding repeats must use the identical arm checkpoint')
        checkpoint_by_arm[key[0]] = checkpoint
        prepared = identity['prepared_receipt_ref']
        profile = identity['profile_receipt_ref']
        if common_prepared_ref is not None and not same_ref(root, common_prepared_ref, prepared):
            raise ValueError('All arms/repeats must share the prepared population receipt')
        if common_profile_ref is not None and not same_ref(root, common_profile_ref, profile):
            raise ValueError('All arms/repeats must share the frozen inference profile receipt')
        common_prepared_ref, common_profile_ref = prepared, profile
        if current_synthetic is not None:
            if synthetic_ref is not None and not same_ref(root,synthetic_ref,current_synthetic):
                raise ValueError('P/A must reuse the same immutable synthetic corpus')
            synthetic_ref = current_synthetic
        for field, expected in [('seed', key[1]), ('round', 1), ('stage', 'evaluation'), ('method', run['method'])]:
            if manifest.get(field) != expected:
                raise ValueError(f'{key}: invalid generation {field}')
        settings = manifest['settings']
        for field, expected in [('samples',16), ('temperature',.8), ('top_p',.95), ('top_k',0), ('max_prompt_tokens',1024), ('max_new_tokens',512)]:
            if settings.get(field) != expected:
                raise ValueError(f'{key}: changed generation setting {field}')
        identity = (manifest['prompts'], settings)
        if manifest_identity is not None and identity != manifest_identity:
            raise ValueError('Prompt/batch/decoding settings changed across arms or repeats')
        manifest_identity = identity
        receipt = read_json(root, run['scoring_receipt_ref'])
        if receipt.get('status') != 'verified':
            raise PendingEvidence('Scoring pending independent qualification/replay')
        for name in ('raw_ref', 'scored_ref'):
            if not same_ref(root, receipt[name], run[name]):
                raise ValueError(f'Scoring receipt does not bind {name}')
        if not same_ref(root, receipt['protocol_ref'], bundle['protocol_ref']):
            raise ValueError('Scoring protocol mismatch')
        for name in ('native_replay_ref', 'isolation_review_ref', 'scorer_source_ref'):
            resolve_ref(root, receipt[name])
        verify_nested_refs(root, receipt)
        scored = read_rows(root, run['scored_ref'])
        failures[f'{key[0]}{key[1]}'] = validate_rows(read_rows(root,run['raw_ref']), scored,
                      receipt['per_sample_outcomes'], ids, key[1], run['method'])
        summary = metrics.summarize_records(scored, ks=[1,8,16], correct_budget=8,
                      correct_budgets=[4,8,16], bootstrap_samples=0, seed=1042,
                      expected_samples={t:16 for t in ids})
        ev = (summary['protocol'].get('evaluation'), summary['protocol'].get('evaluation_task_harnesses'))
        if evaluator is not None and ev != evaluator:
            raise ValueError('Evaluator/task tests changed across arm-seed files')
        evaluator = ev
        summaries[key] = summary
    result = calculate(summaries, ids)
    result.update(status='developmental_analysis', task_ids=ids, sample_count=48000,
                  per_run={f'{a}{s}': v for (a,s),v in summaries.items()}, failure_inventory=failures,
                  input_bundle=bundle, generated_code_execution_enabled=False)
    return result


def collect_inventory(root, bundle):
    """Read every available pinned record, even when strict analysis must stop.

    This is an inventory of reported statuses, not acceptance of their validity.
    No source with changed hashes is consumed; missing/changed files are listed.
    """
    failures, exclusions = [], []
    original_ref = {'path':'research-state/B01-scorer-source-binding-000003/hf-full-test-decoded.json',
                    'sha256':'02ec024e5ec83ab2e01d4f527ff6a80e431d83f39361d5754f8248830c292aaf'}
    try:
        ids = [f"Mbpp/{r['task_id']}" for r in read_json(root, original_ref)]
    except (ValueError, KeyError, OSError) as exc:
        return [], [{'scope':'original_population', 'reason':str(exc)}]
    expected = {(t,i) for t in ids for i in range(16)}
    for run in bundle.get('runs', []):
        context = {'arm':run.get('arm'), 'seed':run.get('seed')}
        try:
            receipt = read_json(root, run['scoring_receipt_ref'])
            outcomes = receipt.get('per_sample_outcomes', [])
            if receipt.get('status') != 'verified':
                exclusions.append({**context, 'scope':'scoring_receipt', 'reason':'scoring_not_verified'})
        except (ValueError, KeyError, OSError) as exc:
            outcomes = []
            exclusions.append({**context, 'scope':'scoring_receipt', 'reason':str(exc)})
        collections = {'outcomes': outcomes}
        for field in ('raw_ref', 'scored_ref'):
            try:
                collections[field] = read_rows(root, run[field])
            except (ValueError, KeyError, OSError) as exc:
                collections[field] = []
                exclusions.append({**context, 'scope':field, 'reason':str(exc)})
        for name, rows in collections.items():
            seen = set()
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get('task_id'), str) or type(row.get('sample_id')) is not int:
                    exclusions.append({**context, 'scope':name, 'reason':'malformed_record_identity'})
                    continue
                key = row.get('task_id'), row.get('sample_id')
                entry = {**context, 'task_id':key[0], 'sample_id':key[1], 'scope':name}
                if key in seen:
                    exclusions.append({**entry, 'reason':'duplicate'})
                seen.add(key)
                if key not in expected:
                    exclusions.append({**entry, 'reason':'unexpected_task_or_sample'})
                if name == 'outcomes' and row.get('classification') != 'model_outcome':
                    exclusions.append({**entry, 'reason':row.get('classification', 'unclassified')})
                if name == 'scored_ref':
                    provenance = row.get('evaluation_provenance')
                    if not isinstance(provenance, dict) or provenance.get('provenance_version') != 2:
                        exclusions.append({**entry, 'reason':'missing_scorer_provenance'})
                    elif provenance.get('backend', '') in {'', 'none', 'local', 'unsafe_local', 'docker'} or 'docker' in str(provenance.get('backend','')).lower():
                        exclusions.append({**entry, 'reason':'unqualified_backend'})
                    if row.get('correct') is False or row.get('status') not in ('passed', None):
                        failures.append({**entry, 'status':row.get('status'), 'correct':row.get('correct'),
                            'verification_error':row.get('verification_error'),
                            'interpretation':'reported_status_only_validity_separately_checked'})
                    if type(row.get('correct')) is not bool or row.get('status') not in MODEL_STATUSES:
                        exclusions.append({**entry, 'reason':'missing_or_unknown_score'})
            for task, sample in sorted(expected-seen):
                exclusions.append({**context, 'task_id':task, 'sample_id':sample, 'scope':name, 'reason':'missing'})
    return failures, exclusions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    bundle_path = args.bundle if args.bundle.is_absolute() else root / args.bundle
    bundle = json.loads(bundle_path.read_text())
    binding = {'bundle_sha256': digest(bundle_path), 'analysis_sha256': digest(__file__)}
    output = args.output if args.output.is_absolute() else root / args.output
    if output.exists():
        receipt_path = output/'receipt.json'
        if not receipt_path.is_file():
            raise ValueError('Unknown existing output; refusing overwrite')
        receipt = json.loads(receipt_path.read_text())
        if receipt.get('binding') != binding or digest(output/'analysis.json') != receipt['analysis_sha256']:
            raise ValueError('Existing output differs; use a reviewed fresh attempt path')
        for name, expected_sha in receipt['output_sha256'].items():
            if digest(output/name) != expected_sha:
                raise ValueError('Changed analysis output: '+name)
        verify_nested_refs(root, bundle)
        for run in bundle['runs']:
            verify_nested_refs(root, read_json(root, run['scoring_receipt_ref']))
            validate_generation_identity(root,bundle,run,read_json(root,run['generation_manifest_ref']))
        print(json.dumps(receipt)); return 0 if receipt['status'] == 'developmental_analysis' else 2
    output.mkdir(parents=True, exist_ok=False)
    failures, exclusions = collect_inventory(root, bundle)
    try:
        result = analyze(root, bundle)
    except PendingEvidence as exc:
        result = {'status':'pending', 'reason':str(exc), 'scores':None, 'generated_code_execution_enabled':False}
    except (KeyError, ValueError) as exc:
        result = {'status':'invalid', 'reason':str(exc), 'scores':None, 'generated_code_execution_enabled':False}
    for contrast, details in result.get('effects', {}).items():
        for metric, details_for_metric in details.items():
            for task in details_for_metric['repeat_mean']['missing_task_ids']:
                exclusions.append({'scope':'metric_eligibility', 'contrast':contrast, 'metric':metric, 'task_id':task, 'reason':'not_in_joint_arm_repeat_eligible_intersection'})
    for name, rows in [('failures.jsonl', failures), ('exclusions.jsonl', exclusions)]:
        (output/name).write_text(''.join(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n' for row in rows))
    target = output/'analysis.json'
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    receipt = {'binding':binding, 'status':result['status'], 'analysis_sha256':digest(target),
               'scientific_acceptance':False, 'outputs':['analysis.json','failures.jsonl','exclusions.jsonl'],
               'output_sha256':{name:digest(output/name) for name in ('analysis.json','failures.jsonl','exclusions.jsonl')}}
    (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))
    return 0 if result['status']=='developmental_analysis' else 2


if __name__ == '__main__':
    sys.exit(main())
