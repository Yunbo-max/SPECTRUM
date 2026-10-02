#!/usr/bin/env python3
"""Freeze, inspect, and explicitly execute the finite final self-distillation study.

Planning and status use only the standard library, without model imports,
downloads, candidate execution, or GPU access. Planning requires prepared data.
Execution is sequential and resumes the native pipeline; it never selects a
configuration from evaluation outcomes or expands this fixed experiment matrix.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import unicodedata


REPO = Path(__file__).resolve().parents[1]
STUDY = "spectrum_release_v1"
MODEL_KEYS = ("qwen1.5b", "qwen3b", "qwen7b", "deepseek6.7b")
BLOCKS = ("core", "scale", "mechanism", "token_matched", "diagnostic", "transfer", "decoder")
METHODS = ("plain", "ssd", "spectral_soft")
BENCHMARKS = ("humanevalplus", "apps_intro", "codecontests", "livecodebench")
COUNTS = {"train": 291, "calibration": 50, "validation": 30, "eval": 500}
DEFAULT_MANIFEST = "runs/spectrum_release_v1/plan/manifest.json"

# Import the existing stdlib-only planner by its known file path. In particular,
# do not import improving.pipeline merely to construct or inspect a plan.
_spec = importlib.util.spec_from_file_location("_final_native_planner", REPO / "scripts/run_iclr2027.py")
if _spec is None or _spec.loader is None:
    raise ImportError("Cannot load scripts/run_iclr2027.py")
_native = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_native)
native_config = _native.native_config
preflight = _native.preflight
digest = _native.digest
immutable_json = _native.immutable_json


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def file_sha(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def resolved(path):
    path = Path(path).expanduser()
    return (path if path.is_absolute() else REPO / path).resolve()


def contained(path, root):
    path, root = resolved(path), resolved(root)
    if path == root or not path.is_relative_to(root):
        raise ValueError(f"Path must be contained within {root}: {path}")
    return path


def jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}:{line_number}: expected a JSON object")
                rows.append(row)
    return rows


def snapshot_file(path, *, count=None):
    path = resolved(path)
    result = {"path": str(path), "sha256": file_sha(path), "bytes": path.stat().st_size}
    if count is not None:
        result["count"] = count
    return result


def prompt_key(value):
    return " ".join(unicodedata.normalize("NFKC", value).split())


def task_keys(rows, split, *, references=False):
    ids, prompts = set(), set()
    for row in rows:
        task_id, prompt = row.get("task_id"), row.get("prompt")
        if (not isinstance(task_id, str) or not task_id or task_id in ids or
                not isinstance(prompt, str) or not prompt.strip() or row.get("split") != split):
            raise ValueError(f"Invalid/duplicate task or split in prepared {split} snapshot")
        if references and not row.get("reference"):
            raise ValueError(f"Calibration reference is missing: {task_id}")
        ids.add(task_id)
        for key in ("prompt", "original_prompt"):
            if row.get(key):
                prompts.add(prompt_key(row[key]))
    return ids, prompts


def init_seeds(args):
    import secrets
    path = resolved(args.output)
    if path.exists():
        raise FileExistsError('Private randomization already exists; keep it for reproducibility')
    values = set()
    while len(values) < 4:
        values.add(secrets.randbelow(2**30))
    data, *replicates = sorted(values)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        json.dump({'schema_version': 1, 'data_seed': data,
                   'replicates': dict(zip(('r1', 'r2', 'r3'), replicates))}, stream, indent=2)
        stream.write('\n')
    print(f'Created private randomization file: {path}; values are not printed.')
    return 0


def private_seeds(path):
    value = read_json(path)
    if set(value.get('replicates', {})) != {'r1', 'r2', 'r3'}:
        raise ValueError('Private seed file requires three independent replicates r1/r2/r3')
    values = [value.get('data_seed'), *value['replicates'].values()]
    if any(type(n) is not int or not 0 <= n < 2**31 - 100 for n in values) or len(set(values)) != 4:
        raise ValueError('Private randomization values must be distinct, valid nonnegative integers')
    return value


def prepared_snapshots(data_root, benchmark_root, assets):
    snapshots, keys = {}, {}
    final_root = data_root.parent
    lock, registry_path = final_root / 'assets.lock.json', final_root / 'benchmark_registry.json'
    if read_json(lock) != assets:
        raise ValueError('Prepared data asset lock differs from the final asset specification')
    registry = read_json(registry_path)
    if registry.get('complete') is not True or set(registry.get('benchmarks', {})) != {'mbpp', *BENCHMARKS}:
        raise ValueError('Final data registry is incomplete')
    for name, entry in registry['benchmarks'].items():
        expected_directory = data_root if name == 'mbpp' else benchmark_root / name
        if resolved(entry['directory']) != expected_directory or entry.get('revision') != assets['datasets'][name]['revision']:
            raise ValueError(f'Prepared registry path/revision differs: {name}')
        manifest_path = expected_directory / 'manifest.json'
        if file_sha(manifest_path) != entry.get('manifest_sha256'):
            raise ValueError(f'Changed data preparation manifest: {name}')
        prepared = read_json(manifest_path)
        if not isinstance(prepared.get('output_files'), dict) or 'eval.jsonl' not in prepared['output_files']:
            raise ValueError(f'Missing prepared file inventory: {name}')
        for filename, expected in prepared['output_files'].items():
            target = contained(expected_directory / filename, expected_directory)
            if file_sha(target) != expected.get('sha256'):
                raise ValueError(f'Prepared output changed before planning: {name}/{filename}')
        snapshots[f'{name}/manifest.json'] = snapshot_file(manifest_path)
    snapshots['final/assets.lock.json'] = snapshot_file(lock)
    snapshots['final/benchmark_registry.json'] = snapshot_file(registry_path)
    for name, count in COUNTS.items():
        path = data_root / f'{name}.jsonl'
        rows = jsonl(path)
        if len(rows) != count:
            raise ValueError(f'MBPP {name}: expected {count} records, got {len(rows)}')
        keys[name] = task_keys(rows, name, references=name == 'calibration')
        snapshots[f'mbpp/{name}.jsonl'] = snapshot_file(path, count=len(rows))
    for i, name in enumerate(COUNTS):
        for other in list(COUNTS)[i + 1:]:
            if any(a & b for a, b in zip(keys[name], keys[other])):
                raise ValueError(f'Overlapping MBPP splits: {name}/{other}')
    preparation = data_root / 'preparation_manifest.jsonl'
    if not preparation.is_file():
        raise ValueError('Use scripts/prepare_final_data.py; MBPP preparation manifest is required')
    metadata = jsonl(preparation)
    if len(metadata) != 1 or metadata[0].get('output_counts') != COUNTS:
        raise ValueError('MBPP preparation metadata does not match the frozen population')
    snapshots['mbpp/preparation_manifest.jsonl'] = snapshot_file(preparation)
    fit_ids = set().union(*(keys[k][0] for k in ('train', 'calibration', 'validation')))
    fit_prompts = set().union(*(keys[k][1] for k in ('train', 'calibration', 'validation')))
    for name in BENCHMARKS:
        directory = benchmark_root / name
        manifest_path = directory / 'manifest.json'
        meta = read_json(manifest_path)
        if meta.get('name') != name:
            raise ValueError(f'Wrong benchmark manifest: {name}')
        outputs = meta.get('output_files', {})
        if 'eval.jsonl' not in outputs:
            raise ValueError(f'Missing evaluation snapshot declaration: {name}')
        for filename, expected in outputs.items():
            path = contained(directory / filename, directory)
            if file_sha(path) != expected.get('sha256'):
                raise ValueError(f'Changed prepared benchmark: {name}/{filename}')
            snapshots[f'{name}/{filename}'] = snapshot_file(path, count=expected.get('count'))
        snapshots[f'{name}/manifest.json'] = snapshot_file(manifest_path)
        rows = jsonl(directory / 'eval.jsonl')
        count = assets['datasets'][name]['expected_count']
        if len(rows) != count or outputs['eval.jsonl'].get('count') != count:
            raise ValueError(f'{name}: expected {count} tasks, got {len(rows)}')
        ids, prompts = task_keys(rows, 'eval')
        if ids & fit_ids or prompts & fit_prompts:
            raise ValueError(f'{name} overlaps fitting data')
        if name == 'humanevalplus' and (meta.get('evaluation_backend') != 'evalplus'
                or 'dataset_metadata.json' not in outputs
                or any(row.get('evaluation_backend') != 'evalplus' for row in rows)):
            raise ValueError('HumanEval+ must use the official complete EvalPlus snapshot')
    return snapshots


def source_snapshot():
    paths = set((REPO / 'src/improving').glob('*.py'))
    paths.update(REPO / p for p in (
        'scripts/run_release_study.py', 'scripts/report_release_study.py',
        'scripts/run_iclr2027.py', 'scripts/run_final_study.py',
        'scripts/report_final_study.py', 'scripts/prepare_final_data.py', 'scripts/evaluate_decoder.py',
        'scripts/export_longitudinal.py', 'scripts/evalplus_docker.sh',
        'experiments/iclr2027/transfer.py', 'docker/EvalPlus.Dockerfile',
        'pyproject.toml', 'configs/final/assets.json'))
    return {str(p.relative_to(REPO)): file_sha(p) for p in sorted(paths)}


def training_config(args, assets, seeds, job_id, model_key, replicate_id,
                    methods, rounds, *, tau=1., loss_scope='all', fixed=False,
                    token_budget=None, anchor_replay=False):
    seed = seeds['replicates'][replicate_id]
    cfg = native_config(args, model_key, seed)
    batch = {'24gb': [8, 4, 1, 1], '48gb': [16, 8, 2, 2],
             '80gb': [32, 16, 8, 8]}[args.profile][MODEL_KEYS.index(model_key)]
    cfg.update(label=job_id, methods=list(methods), rounds=rounds,
               data_seed=seeds['data_seed'],
               output_dir=str(contained(args.run_root / 'jobs' / job_id, args.run_root)))
    cfg['model'].update(name=assets['models'][model_key]['repo_id'],
                        revision=assets['models'][model_key]['revision'])
    cfg['generation'].update(batch_size=batch, sequence_batch_size=batch, task_batch_size=batch)
    cfg['calibration'].update(tau=tau, reestimate_each_round=not fixed)
    cfg['train'].update(loss_scope=loss_scope)
    if token_budget is not None:
        cfg['train']['target_token_budget'] = token_budget
    if anchor_replay:
        cfg['train']['fixed_anchor_replay'] = True
    cfg['diagnostics']['evaluate_generation_policy'] = True
    return cfg


def training_job(args, job_id, block, model_key, replicate_id, cfg, comparison_job=None):
    return {'job_id': job_id, 'kind': 'training', 'block': block,
            'model_key': model_key, 'replicate_id': replicate_id,
            'model_revision': cfg['model']['revision'],
            'config': str(contained(args.run_root / 'plan/configs' / f'{job_id}.json', args.run_root)),
            'config_sha256': digest(cfg), 'output_dir': cfg['output_dir'],
            'rounds': cfg['rounds'], 'methods': cfg['methods'], 'seed': cfg['seed'],
            'samples_per_task': 64, 'task_count': 500, 'depends_on': [],
            'comparison_job': comparison_job,
            'question': {'core': 'joint five-round correctness and correct-solution retention',
                         'scale': 'trained-method model size and architecture replication',
                         'mechanism': 'direction, reference information, or recalibration necessity',
                         'token_matched': 'matched supervised-token exposure over five rounds',
                         'diagnostic': 'predeclared one-round strength or loss-scope sensitivity'}[block]}


def transfer_job(args, source, name, snapshot):
    job_id = f'transfer-{source["model_key"]}-{source["replicate_id"]}-{name}'
    return {'job_id': job_id, 'kind': 'transfer', 'block': 'transfer',
            'model_key': source['model_key'], 'model_revision': source['model_revision'],
            'replicate_id': source['replicate_id'], 'seed': source['seed'],
            'output_dir': str(contained(args.run_root / 'jobs' / job_id, args.run_root)),
            'rounds': 1, 'student_round': 5, 'methods': list(METHODS),
            'benchmark': name, 'benchmark_root': str(args.benchmark_root),
            'source_run': source['output_dir'], 'samples_per_task': 64,
            'task_count': snapshot['count'], 'task_sha256': snapshot['sha256'],
            'sequence_batch_size': 1 if args.profile == '24gb' else 2 if args.profile == '48gb' else 8,
            'backend': args.backend, 'allow_unsafe_local': args.allow_unsafe_local,
            'depends_on': [source['job_id']]}


def command_for(job):
    if job['kind'] == 'training':
        return ['python', '-m', 'improving', 'run', '--config', job['config'], '--resume']
    if job['block'] == 'decoder':
        command = ['python', 'scripts/evaluate_decoder.py', '--run-dir', job['source_run'],
                   '--output-dir', job['output_dir'], '--decoder', job['decoder_id'],
                   '--samples', '64', '--sequence-batch-size', str(job['sequence_batch_size']),
                   '--backend', job['backend'], '--resume']
        if job['allow_unsafe_local']:
            command.append('--allow-unsafe-local')
        return command
    command = ['python', 'experiments/iclr2027/transfer.py', '--run-dir', job['source_run'],
               '--benchmark', job['benchmark'], '--benchmark-root', job['benchmark_root'],
               '--output-dir', job['output_dir'], '--round', str(job['student_round']),
               '--methods', ','.join(job['methods']), '--samples', str(job['samples_per_task']),
               '--bootstrap-samples', '2000', '--max-prompt-tokens', '4096',
               '--max-new-tokens', '1024', '--sequence-batch-size', str(job['sequence_batch_size']),
               '--timeout', '30', '--backend', job['backend'], '--resume']
    if job['allow_unsafe_local']:
        command.append('--allow-unsafe-local')
    return command


def candidate_budget(jobs, configs):
    values = {'training_candidates': 0, 'native_student_evaluation_candidates': 0,
              'native_base_evaluation_candidates': 0, 'teacher_diagnostic_candidates': 0,
              'transfer_candidates': 0, 'decoder_candidates': 0, 'method_replicate_rounds': 0}
    for job in jobs:
        if job['kind'] == 'training':
            cfg = configs[job['job_id']]
            count = len(job['methods']) * job['rounds']
            values['method_replicate_rounds'] += count
            values['training_candidates'] += count * 291 * 16
            values['native_student_evaluation_candidates'] += count * 500 * 64
            values['native_base_evaluation_candidates'] += 500 * 64
            values['teacher_diagnostic_candidates'] += count * 128 * 16
        else:
            category = 'decoder_candidates' if job['block'] == 'decoder' else 'transfer_candidates'
            values[category] += (1 + len(job['methods'])) * job['task_count'] * job['samples_per_task']
    values['total_candidates'] = sum(v for k, v in values.items() if k.endswith('_candidates'))
    values['maximum_new_tokens_before_retries'] = (
        (values['total_candidates'] - values['transfer_candidates']) * 512 + values['transfer_candidates'] * 1024)
    values['note'] = 'Fresh-run generated candidate counts. Anchor replay and calibration generate none. Token-budget SFT reuses the raw corpus; training exposures and FLOPs are separate. Retries cost additional compute.'
    return values


def build_plan(args):
    if args.backend == 'local' and not args.allow_unsafe_local:
        raise ValueError('Local execution requires --allow-unsafe-local; Docker is the default')
    if args.workers < 1:
        raise ValueError('workers must be positive')
    args.run_root, args.data_root, args.benchmark_root = map(resolved,
        (args.run_root, args.data_root, args.benchmark_root))
    assets, seeds = read_json(resolved(args.assets)), private_seeds(resolved(args.seed_file))
    for name in MODEL_KEYS:
        model = assets['models'][name]
        revision = model.get('revision', '')
        if len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
            raise ValueError(f'An immutable model revision is required: {name}')
    snapshots = prepared_snapshots(args.data_root, args.benchmark_root, assets)
    preparation = jsonl(args.data_root / 'preparation_manifest.jsonl')[0]
    if preparation.get('split_seed') != seeds['data_seed']:
        raise ValueError('Prepared data and private data_seed differ')
    jobs, configs = [], {}
    def add(job_id, block, model='qwen1.5b', replicate='r1', methods=METHODS, rounds=5, **kwargs):
        cfg = training_config(args, assets, seeds, job_id, model, replicate, methods, rounds, **kwargs)
        configs[job_id] = cfg
        jobs.append(training_job(args, job_id, block, model, replicate, cfg,
                                 comparison_job='core-qwen1.5b-r1' if block in {'mechanism', 'diagnostic'} else None))
    for replicate in ('r1', 'r2', 'r3'):
        add(f'core-qwen1.5b-{replicate}', 'core', replicate=replicate)
    for model in MODEL_KEYS[1:]:
        add(f'scale-{model}-r1', 'scale', model=model)
    sources = list(jobs)
    add('mechanism-geometry-r1', 'mechanism', methods=('spd_hard', 'random_soft', 'isotropic_soft'))
    add('mechanism-fixed-r1', 'mechanism', methods=('spectral_soft',), fixed=True)
    add('mechanism-anchor-replay-r1', 'mechanism', methods=('plain',), anchor_replay=True)
    # 291*16*(1536-1)=7,146,960 is the largest possible one-pass target count.
    # This bound guarantees every raw record can be exposed without corpus filtering.
    add('token-matched-r1', 'token_matched', token_budget=7_200_000)
    add('diagnostic-tau-half-r1', 'diagnostic', methods=('spectral_soft',), rounds=1, tau=.5)
    add('diagnostic-tau-two-r1', 'diagnostic', methods=('spectral_soft',), rounds=1, tau=2.)
    add('diagnostic-completion-r1', 'diagnostic', methods=('plain', 'spectral_soft'), rounds=1, loss_scope='completion')
    jobs.extend(transfer_job(args, source, name, snapshots[f'{name}/eval.jsonl'])
                for source in sources for name in BENCHMARKS)
    for decoder_id, policy in (
            ('cool', {'temperature': .6, 'top_p': .95, 'top_k': 0}),
            ('warm', {'temperature': 1., 'top_p': .95, 'top_k': 0}),
            ('ssd_recipe', {'temperature': 1.5, 'top_p': .8, 'top_k': 20})):
        job = transfer_job(args, sources[0], 'mbpp', snapshots['mbpp/eval.jsonl'])
        job_id = f'decoder-{decoder_id}-qwen1.5b-r1'
        job.update(job_id=job_id, block='decoder', decoder_id=decoder_id,
                   source_job=sources[0]['job_id'],
                   generation_overrides=policy,
                   output_dir=str(contained(args.run_root / 'jobs' / job_id, args.run_root)))
        jobs.append(job)
    for job in jobs:
        job['command'] = command_for(job)
    budget = candidate_budget(jobs, configs)
    value = {'schema_version': 1, 'study': STUDY, 'run_root': str(args.run_root),
             'protocol': {'evidence_mode': 'prospective_plan_not_executed',
                'training_dataset': 'mbpp', 'models': assets['models'],
                'replicate_policy': {'qwen1.5b': ['r1', 'r2', 'r3'],
                                     **{name: ['r1'] for name in MODEL_KEYS[1:]}},
                'core_rounds': 5, 'main_methods': list(METHODS), 'mbpp_counts': COUNTS,
                'data_seed': seeds['data_seed'], 'replicates': seeds['replicates'],
                'training_samples_per_task': 16, 'evaluation_samples_per_task': 64,
                'task_bootstrap_resamples': 2000, 'primary_metrics': ['pass@1', 'pass@64', 'C64', 'D4'],
                'correct_count_matched_budgets': [4, 8, 16],
                'uncertainty_unit': 'paired tasks within each independent training replicate; never pool model families',
                'information_budget': 'fixed initial anchor; no generated-sample correctness signal in training; direct-anchor replay is a separately labeled supervised control',
                'native_evaluation_decoder': {'temperature': .8, 'top_p': .95, 'top_k': 0},
                'main_token_budgets_matched': False,
                'token_control': {'target_tokens_per_round': 7200000, 'maximum_overshoot_exclusive': 1535,
                                  'scope': 'causally shifted supervised targets; whole-record exposures; not equal FLOPs'},
                'selection': 'fixed matrix and fifth-round checkpoint; all outcomes reported; no test-set method selection',
                'profile': args.profile, 'backend': args.backend, 'workers': args.workers,
                'dataset_snapshots': snapshots, 'asset_lock': snapshot_file(resolved(args.assets)),
                'implementation_sha256': source_snapshot(), 'candidate_budget': budget}, 'jobs': jobs}
    value['manifest_sha256'] = digest(value)
    path = contained(args.run_root / 'plan/manifest.json', args.run_root)
    writes = [(Path(job['config']), configs[job['job_id']]) for job in jobs if job['kind'] == 'training'] + [(path, value)]
    for target, document in writes:
        if target.exists() and read_json(target) != document:
            raise ValueError(f'Different immutable plan already exists: {target}; use a new run root')
    for target, document in writes:
        immutable_json(target, document)
    print(f'Manifest: {path}\nTraining jobs: {len(configs)}; evaluation jobs: {len(jobs)-len(configs)}')
    print(f'Method-replicate-rounds: {budget["method_replicate_rounds"]}; fresh-run candidates: {budget["total_candidates"]:,}')
    print('No models downloaded, no experiments executed. Choose a block explicitly; public job IDs use replicate labels.')
    return 0


def load_manifest(path, verify_inputs=False):
    path = resolved(path)
    value = read_json(path)
    if value.get('study') != STUDY or value.get('schema_version') != 1:
        raise ValueError('Expected a spectrum_release_v1 manifest')
    if digest({k: v for k, v in value.items() if k != 'manifest_sha256'}) != value.get('manifest_sha256'):
        raise ValueError('Manifest changed since planning')
    root = resolved(value['run_root'])
    if path != contained(root / 'plan/manifest.json', root):
        raise ValueError('Manifest must remain at its planned path')
    jobs = value.get('jobs', [])
    ids = [j['job_id'] for j in jobs]
    if len(ids) != len(set(ids)) or not jobs:
        raise ValueError('Job IDs must be unique and nonempty')
    for job in jobs:
        if job['kind'] not in {'training', 'transfer'} or job['block'] not in BLOCKS:
            raise ValueError('Unknown job kind/block')
        if resolved(job['output_dir']) != contained(root / 'jobs' / job['job_id'], root):
            raise ValueError('Unexpected output path')
        if any(dep not in ids or ids.index(dep) >= ids.index(job['job_id']) for dep in job['depends_on']):
            raise ValueError('Dependencies must be earlier planned jobs')
        if job['command'] != command_for(job):
            raise ValueError('Job command differs from the supported native runner')
        if job['kind'] == 'training':
            if resolved(job['config']) != contained(root / 'plan/configs' / f'{job["job_id"]}.json', root):
                raise ValueError('Unexpected config path')
            if verify_inputs:
                cfg = read_json(job['config'])
                if digest(cfg) != job['config_sha256'] or any(cfg[k] != job[k] for k in ('output_dir', 'rounds', 'methods', 'seed')):
                    raise ValueError(f'Configuration changed: {job["job_id"]}')
                if cfg['model']['revision'] != job['model_revision']:
                    raise ValueError('Model revision differs from plan')
    if verify_inputs:
        verify_plan_inputs(value)
    return value


def verify_plan_inputs(manifest):
    for name, snapshot in manifest['protocol']['dataset_snapshots'].items():
        if not Path(snapshot['path']).is_file() or file_sha(snapshot['path']) != snapshot['sha256']:
            raise ValueError(f'Changed or missing prepared input: {name}')
    lock = manifest['protocol']['asset_lock']
    if file_sha(lock['path']) != lock['sha256']:
        raise ValueError('Asset specification changed since planning')
    if source_snapshot() != manifest['protocol']['implementation_sha256']:
        raise ValueError('Implementation changed since planning; use a new run root')


def verify_marker(directory, *, base=False, transfer_fingerprint=None,
                  verify_hashes=False, model_revision=None):
    marker = directory / 'complete.json'
    if not marker.is_file():
        return False, 'completion marker missing'
    try:
        state = read_json(marker)
        if not state.get('model_identity'):
            return False, 'model identity missing'
        if transfer_fingerprint is not None:
            if state.get('status') != 'completed' or state.get('protocol_fingerprint') != transfer_fingerprint:
                return False, 'transfer completion identity mismatch'
        elif base:
            if state.get('integrity_schema') != 2 or state.get('resolved_revision') != model_revision:
                return False, 'base revision or integrity mismatch'
        elif state.get('status') != 'completed' or state.get('checkpoint_status') == 'pruned':
            return False, 'student stage not complete or weights pruned'
        files = state.get('files', {})
        required = {'evaluation.jsonl', 'evaluation.verified.jsonl', 'evaluation.metrics.json'}
        if not base and transfer_fingerprint is None:
            required |= {'train.jsonl', 'training_stats.json', 'model/config.json',
                         'generation_policy.jsonl', 'generation_policy.verified.jsonl', 'generation_policy.metrics.json'}
            if not any(n.startswith('model/') and n.endswith(('.bin', '.safetensors')) for n in files):
                return False, 'retained model weights missing'
        if not required <= files.keys():
            return False, 'required artifacts not sealed'
        for name, expected in files.items():
            file = contained(directory / name, directory)
            if not isinstance(expected, str) or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
                return False, f'invalid checksum metadata: {name}'
            if not file.is_file() or (verify_hashes and file_sha(file) != expected):
                return False, f'missing or changed artifact: {name}'
    except (OSError, ValueError, TypeError, KeyError) as error:
        return False, str(error)
    return True, None


def job_status(job, verify_hashes=False):
    root = Path(job['output_dir'])
    rounds = range(1, job['rounds'] + 1) if job['kind'] == 'training' else [job['student_round']]
    stages = ['base'] + [f'{m}/round_{r}' for m in job['methods'] for r in rounds]
    result = {'job_id': job['job_id'], 'block': job['block'], 'status': 'pending',
              'completed_stages': 0, 'expected_stages': len(stages), 'issues': []}
    if not root.exists():
        return result
    result['status'] = 'partial'
    try:
        saved = read_json(root / 'manifest.json')
        fingerprint = None
        if job['kind'] == 'training':
            if digest(saved.get('config')) != job['config_sha256']:
                raise ValueError('Run config differs from plan')
        else:
            p = saved.get('protocol', {})
            if (p.get('source_run') != job['source_run'] or p.get('methods') != job['methods']
                    or p.get('rounds') != [job['student_round']] or p.get('seed') != job['seed']
                    or p.get('generation', {}).get('samples') != job['samples_per_task']
                    or p.get('task_sha256') != job['task_sha256']
                    or len(p.get('task_ids', [])) != job['task_count']):
                raise ValueError('Transfer protocol differs from plan')
            fingerprint = saved.get('fingerprint')
            if not fingerprint:
                raise ValueError('Transfer fingerprint missing')
            if job.get('generation_overrides') and any(p['generation'].get(k) != v for k, v in job['generation_overrides'].items()):
                raise ValueError('Decoder policy differs from the planned robustness condition')
        for stage in stages:
            ok, reason = verify_marker(root / stage, base=stage == 'base',
                transfer_fingerprint=fingerprint, verify_hashes=verify_hashes,
                model_revision=job['model_revision'])
            result['completed_stages'] += int(ok)
            if not ok:
                result['issues'].append(f'{stage}: {reason}')
        if job['kind'] == 'training':
            state = read_json(root / 'run_status.json')
            if state.get('status') != 'completed' or state.get('verification') != 'completed' or state.get('rounds') != job['rounds'] or state.get('methods') != job['methods']:
                raise ValueError('Native run is incomplete')
        else:
            state = read_json(root / 'transfer_complete.json')
            if (state.get('status') != 'completed' or state.get('benchmark') != job['benchmark']
                    or state.get('source_run') != job['source_run'] or state.get('student_round') != job['student_round']
                    or state.get('samples_per_task') != job['samples_per_task'] or state.get('task_count') != job['task_count']
                    or state.get('training_on_target') is not False or state.get('calibration_on_target') is not False
                    or set(state.get('results', {}).get('completed', [])) != set(stages)):
                raise ValueError('Transfer completion does not match the plan')
            if job['benchmark'] == 'humanevalplus' and state.get('evaluation_protocol') != 'official_evalplus_base_and_plus':
                raise ValueError('Official EvalPlus protocol missing')
    except (OSError, ValueError, TypeError, KeyError) as error:
        result['issues'].append(str(error))
    if not result['issues'] and result['completed_stages'] == len(stages):
        result['status'] = 'completed'
    return result


@contextmanager
def job_lock(root, job_id):
    import fcntl
    path = contained(root / 'locks' / f'{job_id}.lock', root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+', encoding='utf-8') as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f'Job already running: {job_id}') from error
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def execute(command):
    if not command or command[0] != 'python':
        raise ValueError('Only a frozen native Python command is supported')
    subprocess.run([sys.executable, *command[1:]], check=True, cwd=REPO)


def record_event(root, job_id, event, **fields):
    from datetime import datetime, timezone
    path = root / 'execution' / f'{job_id}.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'time_utc': datetime.now(timezone.utc).isoformat(),
                                'job_id': job_id, 'event': event, **fields}, allow_nan=False) + '\n')


def run(args):
    manifest = load_manifest(args.manifest, verify_inputs=True)
    if bool(args.block) == bool(args.job):
        raise ValueError('Choose exactly one --block or --job')
    selected = [j for j in manifest['jobs'] if (j['job_id'] == args.job if args.job else args.block == 'all' or j['block'] == args.block)]
    if not selected:
        raise ValueError('No planned jobs selected')
    by_id = {j['job_id']: j for j in manifest['jobs']}
    root = Path(manifest['run_root'])
    for job in selected:
        with job_lock(root, job['job_id']):
            verify_plan_inputs(manifest)
            for dependency in job['depends_on']:
                source = by_id[dependency]
                if job_status(source)['status'] != 'completed':
                    raise RuntimeError(f'{job["job_id"]} requires completed {dependency}')
                for stage in ['base', *(f'{m}/round_5' for m in source['methods'])]:
                    ok, reason = verify_marker(Path(source['output_dir']) / stage, base=stage == 'base',
                                              verify_hashes=True, model_revision=source['model_revision'])
                    if not ok:
                        raise RuntimeError(f'Dependency integrity failure: {dependency}/{stage}: {reason}')
            if job_status(job, verify_hashes=True)['status'] == 'completed':
                print(f'{job["job_id"]}: already sealed; skipped', flush=True)
                continue
            preflight(job)
            record_event(root, job['job_id'], 'started_or_resumed', protocol=manifest['manifest_sha256'])
            print(f'{job["job_id"]}: running/resuming', flush=True)
            try:
                execute(command_for(job))
                state = job_status(job)
                if state['status'] != 'completed':
                    raise RuntimeError(f'Job did not seal all planned outputs: {state["issues"]}')
                record_event(root, job['job_id'], 'completed')
            except BaseException as error:
                record_event(root, job['job_id'], 'interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                             error_type=type(error).__name__, message=str(error))
                raise
    print('Selected jobs complete. Use report to export all available and missing endpoints.')
    return 0


def report(args):
    manifest = load_manifest(args.manifest)
    with job_lock(Path(manifest['run_root']), 'report'):
        execute(['python', 'scripts/report_release_study.py', '--manifest', str(resolved(args.manifest))])
    return 0


def status(args):
    manifest = load_manifest(args.manifest)
    print(json.dumps([job_status(j) for j in manifest['jobs']], indent=2))
    return 0


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest='command', required=True)
    seed = sub.add_parser('init-seeds', help='Create ignored private randomization; no numeric values are printed')
    seed.add_argument('--output', default='runs/private/seeds.json')
    plan = sub.add_parser('plan', help='Seal finite jobs from prepared data; no downloads/model loading')
    plan.add_argument('--run-root', default='runs/spectrum_release_v1')
    plan.add_argument('--assets', default='configs/final/assets.json')
    plan.add_argument('--seed-file', default='runs/private/seeds.json')
    plan.add_argument('--profile', choices=('24gb', '48gb', '80gb'), default='48gb')
    plan.add_argument('--backend', choices=('docker', 'local'), default='docker')
    plan.add_argument('--allow-unsafe-local', action='store_true')
    plan.add_argument('--workers', type=int, default=4)
    plan.add_argument('--data-root', default='data/final/mbpp')
    plan.add_argument('--benchmark-root', default='data/final/benchmarks')
    run_parser = sub.add_parser('run', help='Explicitly run/resume a finite block or one job')
    run_parser.add_argument('--manifest', default=DEFAULT_MANIFEST)
    group = run_parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--block', choices=(*BLOCKS, 'all'))
    group.add_argument('--job')
    for name in ('status', 'report'):
        p = sub.add_parser(name)
        p.add_argument('--manifest', default=DEFAULT_MANIFEST)
    return root


def main():
    args = parser().parse_args()
    os.chdir(REPO)
    try:
        return {'init-seeds': init_seeds, 'plan': build_plan, 'run': run,
                'status': status, 'report': report}[args.command](args)
    except (OSError, ValueError, KeyError, TypeError, ImportError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
