"""Recursive text-domain study with independent method lineages and bound resume."""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
import copy
import fcntl
import gc
import importlib.metadata
import json
from pathlib import Path
import shutil

from .data import read_jsonl, write_jsonl
from .text_tasks import (file_sha, private_seed, score_text_records,
                         verify_prepared_data)
from .utils import atomic_json, stable_hash

METHODS = ('base', 'plain', 'ssd', 'spectral_soft')


@contextmanager
def _exclusive(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f'Another process owns this lineage: {path}') from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def validate_text_config(config):
    if config.get('domain') not in ('math', 'qa') or int(config.get('rounds', 0)) < 1:
        raise ValueError('Expected math/qa domain and positive rounds')
    model = config['model']
    if (model.get('loader') != 'qwen3_5_text' or model.get('name') != 'Qwen/Qwen3.8-27B'
            or model.get('revision') != '1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0'):
        raise ValueError('This protocol pins the official Qwen3.8-27B text backbone')
    if model.get('dtype') != 'bfloat16' or not model.get('local_files_only'):
        raise ValueError('Use prepared unquantized BF16 weights with local_files_only=true')
    if config.get('calibration', {}).get('layers') != [31, 63]:
        raise ValueError('Pinned hybrid model intervention uses full-attention layers 31 and 63')
    for stage in ('synthesis', 'evaluation'):
        spec = config[stage]
        if min(int(spec[k]) for k in ('samples', 'max_new_tokens', 'max_prompt_tokens')) < 1:
            raise ValueError(f'Invalid {stage} token/sample budget')
    if config['train'].get('loss_scope') != 'completion':
        raise ValueError('Text protocol trains generated completion targets only')
    # No truncation during training can silently discard the generated targets.
    if int(config['train']['max_length']) < int(config['synthesis']['max_prompt_tokens']) + int(config['synthesis']['max_new_tokens']):
        raise ValueError('Training max_length must cover the entire declared synthesis context')
    if config['domain'] == 'qa' and config['evaluation']['samples'] != 1:
        raise ValueError('QA primary protocol uses one answer per question')
    if config['domain'] == 'math' and config['evaluation']['samples'] != 16:
        raise ValueError('Math coverage protocol uses exactly 16 answers per question')
    if config.get('checkpoint_retention', 'all') not in ('all', 'latest'):
        raise ValueError('checkpoint_retention must be all or latest')
    return config


def _source_identity():
    root = Path(__file__).parent
    files = ('text_tasks.py', 'text_study.py', 'modeling.py', 'training.py', 'generation.py',
             'calibration.py', 'spectral.py', 'pipeline.py', 'native_sandbox.py', 'data.py', 'utils.py')
    return {name: file_sha(root / name) for name in files}


def _binding(config, data_manifest, seed):
    from .pipeline import training_runtime_identity
    from .native_sandbox import runtime_identity
    return {'schema': 1, 'config': config, 'data_manifest': data_manifest,
            'seed_sha256': stable_hash(seed), 'source_files': _source_identity(),
            'runtime': training_runtime_identity(),
            'scorer_dependencies': {name: importlib.metadata.version(name)
                                    for name in ('sympy', 'pylatexenc')}
            if config['domain'] == 'math' else {},
            'scoring_runtime': runtime_identity() if config['domain'] == 'math' else {'backend': 'pure_string_matching'}}


def _manifest(path, value, resume):
    if path.exists():
        if not resume:
            raise FileExistsError(f'Existing lineage; use --resume: {path}')
        if json.loads(path.read_text()) != value:
            raise ValueError('Code/data/model/decoder/runtime changed; use a new study output directory')
    else:
        atomic_json(path, value)


def _base_identity(config):
    """Require an existing exact HF snapshot and bind its actual complete weights."""
    from huggingface_hub import snapshot_download
    from .pipeline import checkpoint_fingerprint
    snapshot = Path(snapshot_download(repo_id=config['model']['name'],
                                     revision=config['model']['revision'], local_files_only=True))
    indices = list(snapshot.glob('*.safetensors.index.json'))
    if not indices:
        raise ValueError('Expected complete sharded official model snapshot')
    for index in indices:
        shards = set(json.loads(index.read_text())['weight_map'].values())
        if any(not (snapshot / shard).is_file() for shard in shards):
            raise ValueError('Model snapshot is missing a referenced weight shard')
    return checkpoint_fingerprint(snapshot)


def _score(config, tasks, records, directory, seed):
    from .pipeline import record_stage
    root = Path(config['data']['output_dir'])
    with record_stage(directory, 'scoring'):
        scored, metrics = score_text_records(
            tasks, records, expected_samples=config['evaluation']['samples'],
            grader_root=root / 'sources' / 'prm800k', sandbox=config.get('math_sandbox'), seed=seed)
    write_jsonl(directory / 'evaluation.scored.jsonl', scored)
    atomic_json(directory / 'metrics.json', metrics)
    return metrics


def _evaluate(config, model, tokenizer, tasks, directory, identity, seed, method, round_index, resume):
    from .generation import generate_to_file
    from .pipeline import record_stage
    with record_stage(directory, 'evaluation'):
        records = generate_to_file(model, tokenizer, tasks, directory / 'evaluation.jsonl',
                                   config['evaluation'], seed=seed, model_identity=identity,
                                   method=method, round_index=round_index, stage='evaluation', resume=resume)
    _score(config, tasks, records, directory, seed)
    outputs = ['evaluation.jsonl', 'evaluation.scored.jsonl', 'metrics.json']
    return {name: file_sha(directory / name) for name in outputs}


def _check_completed(directory, identity):
    marker = directory / 'complete.json'
    if not marker.exists():
        return False
    saved = json.loads(marker.read_text())
    if saved['identity'] != identity:
        raise ValueError(f'Completed stage binding changed: {directory}')
    for name, expected in saved['output_hashes'].items():
        if file_sha(directory / name) != expected:
            raise ValueError(f'Completed stage output changed: {directory / name}')
    return True


def _preflight_math(config):
    if config['domain'] != 'math':
        return
    from .native_sandbox import qualify_sandbox
    qualify_sandbox()
    # Two trusted author expressions exercise the actual imported grader. This
    # qualifies plumbing only; it is not a scientific benchmark validation.
    from .text_tasks import grade_math_sandboxed
    result, _ = grade_math_sandboxed('2', '2', Path(config['data']['output_dir']) / 'sources' / 'prm800k',
                                    config['math_sandbox'])
    if result is not True:
        raise RuntimeError('Native PRM grader qualification failed')


def validate_prepared_binding(config, data_manifest, seed):
    """Reject cross-domain, changed-selection and incomplete-population reuse."""
    if data_manifest['identity']['seed_sha256'] != stable_hash(seed):
        raise ValueError('Data and run randomization identities differ')
    if (data_manifest['identity']['domain'] != config['domain']
            or data_manifest['identity']['data'] != config['data']):
        raise ValueError('Prepared domain/splits differ from the requested configuration')
    expected_counts = {'math500': 500} if config['domain'] == 'math' else {'mmlu_pro': 12032, 'gpqa_diamond': 198}
    if data_manifest['evaluation_counts'] != expected_counts:
        raise ValueError('Prepared evaluation does not contain the complete native populations')
    if data_manifest['identity']['builder_sha256'] != file_sha(Path(__file__).with_name('text_tasks.py')):
        raise ValueError('Data builder changed after preparation; freeze a fresh prepared directory')


def run_text_study(config, method, *, resume=False, evaluate_only=False, checkpoint=None):
    import torch
    from .modeling import load_model
    from .pipeline import (_calibrate, _operators, checkpoint_fingerprint,
                           record_stage)
    from .spectral import folded_operators
    from .training import train_on_records
    from .generation import generate_to_file

    validate_text_config(config)
    if method not in METHODS:
        raise ValueError(f'Unknown method: {method}')
    if checkpoint and not evaluate_only:
        raise ValueError('--checkpoint is only for explicit transfer/evaluation mode')
    if evaluate_only and not checkpoint:
        raise ValueError('--evaluate-only requires the exact source checkpoint')
    seed = private_seed(config['seed_file'])
    splits, data_manifest = verify_prepared_data(config['data']['output_dir'])
    validate_prepared_binding(config, data_manifest, seed)
    _preflight_math(config)
    binding = _binding(config, data_manifest, seed)
    base_identity = _base_identity(config)
    binding['base_checkpoint_identity'] = base_identity
    root = Path(config['output_dir'])
    # All method lineages must share one frozen study, even when launched in
    # separate processes/days. Per-lineage resume checks alone would permit
    # comparing an old Vanilla run with a newly configured SPECTRUM run.
    with _exclusive(root / '.study.lock'):
        study_manifest = root / 'study_manifest.json'
        if study_manifest.exists():
            if json.loads(study_manifest.read_text()) != binding:
                raise ValueError('Another arm froze different study conditions; use a new output directory')
        else:
            atomic_json(study_manifest, binding)
    if evaluate_only:
        identity = checkpoint_fingerprint(checkpoint)
        method_root = root / 'transfer' / identity[:20]
    else:
        method_root = root / method
    with _exclusive(method_root / '.writer.lock'):
        manifest_path = method_root / 'manifest.json'
        _manifest(manifest_path, {**binding, 'method': method,
                                  'evaluation_only_checkpoint': str(Path(checkpoint).resolve()) if checkpoint else None}, resume)
        if method == 'base' or evaluate_only:
            identity = checkpoint_fingerprint(checkpoint) if checkpoint else base_identity
            stage = method_root / 'round_0'
            if not _check_completed(stage, identity):
                model, tokenizer = load_model(config['model'], checkpoint)
                hashes = _evaluate(config, model, tokenizer, splits['eval'], stage, identity,
                                   seed, method, 0, resume)
                atomic_json(stage / 'complete.json', {'identity': identity, 'output_hashes': hashes})
                del model, tokenizer
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            return text_report(config)

        parent_path = None
        parent_identity = base_identity
        for round_index in range(1, config['rounds'] + 1):
            directory = method_root / f'round_{round_index}'
            directory.mkdir(parents=True, exist_ok=True)
            checkpoint_dir = directory / 'model'
            checkpoint_receipt = directory / 'checkpoint.json'
            round_binding = stable_hash({'parent': parent_identity, 'round': round_index,
                                         'method': method, 'study': binding})
            if _check_completed(directory, round_binding):
                receipt = json.loads(checkpoint_receipt.read_text())
                pruned = directory / 'checkpoint_pruned.json'
                if pruned.exists():
                    prune_receipt = json.loads(pruned.read_text())
                    descendant = method_root / f'round_{round_index + 1}'
                    if (prune_receipt['checkpoint_identity'] != receipt['checkpoint_identity']
                            or not (descendant / 'complete.json').exists()
                            or prune_receipt['replaced_by_complete_sha256'] != file_sha(descendant / 'complete.json')):
                        raise ValueError('Invalid checkpoint pruning chain')
                    if checkpoint_dir.exists():
                        # Finish only this already sealed, explicitly recorded cleanup.
                        shutil.rmtree(checkpoint_dir)
                elif checkpoint_fingerprint(checkpoint_dir) != receipt['checkpoint_identity']:
                    raise ValueError('Saved descendant checkpoint changed')
                parent_path, parent_identity = checkpoint_dir, receipt['checkpoint_identity']
                continue
            if checkpoint_receipt.exists():
                receipt = json.loads(checkpoint_receipt.read_text())
                if receipt['round_binding'] != round_binding or checkpoint_fingerprint(checkpoint_dir) != receipt['checkpoint_identity']:
                    raise ValueError('Training checkpoint binding mismatch')
                model, tokenizer = load_model(config['model'], checkpoint_dir)
            else:
                if checkpoint_dir.exists():
                    raise ValueError('Uncommitted checkpoint exists; preserve it and reconcile interrupted save before retry')
                model, tokenizer = load_model(config['model'], parent_path)
                generation = copy.deepcopy(config['synthesis'])
                if method == 'ssd':
                    generation.update(config['ssd_synthesis'])
                context = nullcontext()
                if method == 'spectral_soft':
                    with record_stage(directory, 'calibration'):
                        covariances = _calibrate(model, tokenizer, splits['calibration'], config['calibration'],
                                                 directory / 'calibration.pt', parent_identity)
                        operators = _operators(covariances, 'spectral_soft', config['calibration'], seed)
                    context = folded_operators(model, operators)
                with record_stage(directory, 'synthesis'), context:
                    records = generate_to_file(model, tokenizer, splits['train'], directory / 'synthetic.jsonl',
                                               generation, seed=seed, model_identity=parent_identity,
                                               method=method, round_index=round_index, stage='synthesis', resume=resume)
                # Modulation is restored before student SFT. Every raw response is
                # retained, including wrong, empty or malformed responses.
                with record_stage(directory, 'training'):
                    model, stats = train_on_records(model, tokenizer, splits['train'], records,
                                                    config['train'], checkpoint_dir, seed=seed)
                if stats['truncated_tokens']:
                    raise ValueError('Unexpected training truncation: preserve checkpoint as unqualified and fix context budget')
                receipt = {'round_binding': round_binding, 'parent_identity': parent_identity,
                           'checkpoint_identity': checkpoint_fingerprint(checkpoint_dir),
                           'synthetic_sha256': file_sha(directory / 'synthetic.jsonl'),
                           'training_stats_sha256': file_sha(checkpoint_dir / 'training_stats.json')}
                shutil.copyfile(checkpoint_dir / 'training_stats.json', directory / 'training_stats.json')
                atomic_json(checkpoint_receipt, receipt)
            hashes = _evaluate(config, model, tokenizer, splits['eval'], directory,
                               receipt['checkpoint_identity'], seed, method, round_index, resume)
            hashes['checkpoint.json'] = file_sha(checkpoint_receipt)
            hashes['synthetic.jsonl'] = file_sha(directory / 'synthetic.jsonl')
            hashes['training_stats.json'] = file_sha(directory / 'training_stats.json')
            atomic_json(directory / 'complete.json', {'identity': round_binding, 'output_hashes': hashes})
            if config.get('checkpoint_retention', 'all') == 'latest' and parent_path is not None:
                previous = method_root / f'round_{round_index - 1}'
                if Path(parent_path).resolve() != (previous / 'model').resolve():
                    raise ValueError('Refusing to prune an out-of-lineage checkpoint')
                if checkpoint_fingerprint(parent_path) != parent_identity:
                    raise ValueError('Refusing to prune a changed parent checkpoint')
                atomic_json(previous / 'checkpoint_pruned.json', {
                    'checkpoint_identity': parent_identity,
                    'replaced_by_checkpoint_identity': receipt['checkpoint_identity'],
                    'replaced_by_complete_sha256': file_sha(directory / 'complete.json'),
                    'policy': 'latest: only after descendant checkpoint and evaluation are sealed'})
                shutil.rmtree(parent_path)
            parent_path, parent_identity = checkpoint_dir, receipt['checkpoint_identity']
            del model, tokenizer
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        return text_report(config)


def text_report(config):
    """Retain missing cells explicitly; do not infer liveness from saved files."""
    root = Path(config['output_dir'])
    study_manifest = root / 'study_manifest.json'
    if study_manifest.exists() and json.loads(study_manifest.read_text())['config'] != config:
        raise ValueError('Report config differs from the frozen cross-method study')
    rows = []
    for method in METHODS:
        rounds = [0] if method == 'base' else range(1, config['rounds'] + 1)
        for round_index in rounds:
            directory = root / method / f'round_{round_index}'
            path = directory / 'metrics.json'
            complete = (directory / 'complete.json').exists()
            if complete:
                saved = json.loads((directory / 'complete.json').read_text())
                _check_completed(directory, saved['identity'])
            rows.append({'method': method, 'round': round_index,
                         'status': 'completed' if complete else 'incomplete' if path.exists() else 'pending',
                         'metrics': json.loads(path.read_text()) if path.exists() else None})
    comparisons = []
    final = {r['method']: r for r in rows if r['status'] == 'completed' and r['round'] == config['rounds']}
    candidate = final.get('spectral_soft')
    if candidate:
        import numpy as np
        seed = private_seed(config['seed_file'])
        for reference_name in ('plain', 'ssd'):
            reference = final.get(reference_name)
            if reference is None:
                continue
            for benchmark, candidate_metrics in candidate['metrics'].items():
                metric_names = ['pass@1', 'pass@4', 'pass@16'] if benchmark == 'math500' else ['accuracy']
                for metric_name in metric_names:
                    field = 'per_task_' + metric_name
                    candidate_tasks = candidate_metrics[field]
                    reference_tasks = reference['metrics'][benchmark][field]
                    if set(candidate_tasks) != set(reference_tasks):
                        raise ValueError('Paired text report requires identical full task populations')
                    task_ids = sorted(candidate_tasks)
                    difference = np.array([candidate_tasks[k] - reference_tasks[k] for k in task_ids])
                    rng = np.random.default_rng(int(stable_hash([seed, benchmark, reference_name, metric_name])[:16], 16))
                    replicates = np.array([rng.choice(difference, size=len(difference), replace=True).mean()
                                           for _ in range(1000)])
                    comparisons.append({'candidate': 'spectral_soft', 'reference': reference_name,
                        'round': config['rounds'], 'benchmark': benchmark, 'metric': metric_name,
                        'paired_difference': float(difference.mean()),
                        'task_bootstrap_ci95': [float(x) for x in np.quantile(replicates, [.025, .975])],
                        'tasks': len(task_ids), 'bootstrap_replicates': 1000,
                        'uncertainty_scope': 'paired tasks conditional on one trained trajectory; not training-run variability'})
    report = {'domain': config['domain'], 'model': config['model']['name'],
              'training_trajectories_per_method': 1, 'temperature_sweep': False,
              'claims': 'within-model method effects; independent math/QA starting checkpoints',
              'rows': rows, 'final_paired_comparisons': comparisons}
    atomic_json(root / 'report.json', report)
    return report
