#!/usr/bin/env python3
"""Bounded native Qwen2.5-14B math/QA/safety study; never starts on import."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from improving.data import read_jsonl, write_jsonl
from improving.utils import atomic_json, stable_hash


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def tree_hashes(path):
    path = Path(path)
    files = [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file())
    return {str(p.relative_to(path) if path.is_dir() else p.name): sha_file(p) for p in files}


@contextmanager
def run_lock(root):
    import fcntl
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.run.lock').open('a+') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('Another process owns this study output directory') from error
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps({'pid':os.getpid(), 'started':time.time()}))
        handle.flush()
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


class StageStore:
    def __init__(self, root, manifest, *, resume):
        self.root = Path(root).resolve()
        self.identity = stable_hash(manifest)
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / 'manifest.json'
        if target.exists():
            if not resume:
                raise FileExistsError('Existing study requires --resume')
            if json.loads(target.read_text()) != manifest:
                raise ValueError('Study source/data/model/settings identity drift')
        else:
            if any(p.name != '.run.lock' for p in self.root.iterdir()):
                raise ValueError('Unsealed output directory; use a fresh study directory')
            atomic_json(target, manifest)
        (self.root / 'receipts').mkdir(exist_ok=True)

    def receipt_path(self, name):
        return self.root / 'receipts' / (name + '.complete.json')

    def is_done(self, name):
        path = self.receipt_path(name)
        if not path.exists():
            return False
        record = json.loads(path.read_text())
        if record['run_identity'] != self.identity:
            raise ValueError('Stage identity drift: ' + name)
        for relative, digest in record['artifacts'].items():
            target = self.root / relative
            if not target.is_file() or sha_file(target) != digest:
                raise ValueError('Missing or changed sealed artifact: ' + relative)
        return True

    def execute(self, name, action, artifacts):
        if self.is_done(name):
            return None
        import torch
        started = time.time()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        print(json.dumps({'stage':name, 'status':'running'}), flush=True)
        try:
            result = action()
            hashes = {}
            for artifact in artifacts:
                path = Path(artifact).resolve()
                if not path.exists() or not path.is_relative_to(self.root):
                    raise ValueError('Stage artifact missing or outside owned output root')
                files = [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file())
                for file in files:
                    hashes[str(file.relative_to(self.root))] = sha_file(file)
            receipt = {'stage':name, 'run_identity':self.identity, 'status':'complete',
                       'started':started, 'elapsed_seconds':time.time()-started,
                       'artifacts':hashes, **memory_receipt()}
            atomic_json(self.receipt_path(name), receipt)
            print(json.dumps({'stage':name, 'status':'complete', 'elapsed_seconds':receipt['elapsed_seconds']}), flush=True)
            return result
        except BaseException as error:
            atomic_json(self.root / 'receipts' / f'{name}.failure.{time.time_ns()}.json', {
                'stage':name, 'run_identity':self.identity, 'status':'failed',
                'elapsed_seconds':time.time()-started, 'error':repr(error),
                'traceback':traceback.format_exc(), **memory_receipt()})
            raise


def memory_receipt():
    import torch
    if not torch.cuda.is_available():
        return {'cuda_available':False}
    return {'cuda_available':True, 'device':torch.cuda.get_device_name(),
            'peak_allocated_bytes':torch.cuda.max_memory_allocated(),
            'peak_reserved_bytes':torch.cuda.max_memory_reserved()}


def task_views(tasks):
    """Generation/SFT do not consume reference span metadata."""
    return [{k:v for k,v in task.items() if k != 'calibration_spans'} for task in tasks]


def interval_tasks(tasks):
    result = []
    for task in tasks:
        spans = sorted((s['start'], s['end']) if isinstance(s, dict) else tuple(s)
                       for s in task['calibration_spans'])
        intervals = []
        for start, end in spans:
            if intervals and start <= intervals[-1][1]:
                intervals[-1][1] = max(intervals[-1][1], end)
            else:
                intervals.append([start, end])
        result.append(dict(task, calibration_spans=intervals))
    return result


def study_settings(args):
    return {'domain':args.domain, 'method':args.method, 'smoke':args.smoke,
            'rounds':1 if args.smoke else 5, 'seed':args.seed,
            'reserve_gib':args.reserve_gib, 'memory_budget_gib':args.memory_budget_gib,
            'model':{'name':str(Path(args.model).resolve()), 'device':'cuda',
                     'dtype':'bfloat16', 'local_files_only':True, 'attn_implementation':'sdpa'},
            'generation':{'samples':1, 'batch_size':2, 'task_batch_size':2,
                          'sequence_batch_size':2, 'max_new_tokens':4096,
                          'max_prompt_tokens':4096, 'temperature':0.7, 'top_p':0.95, 'top_k':0},
            'train':{'epochs':2, 'batch_size':2, 'gradient_accumulation_steps':1,
                     'max_length':8192, 'require_full_completion_targets':True,
                     'loss_scope':'all', 'learning_rate':1e-5, 'lora_rank':8,
                     'lora_alpha':8, 'lora_dropout':0.05, 'gradient_checkpointing':True},
            'calibration':{'layers':[24,47], 'rank_fraction':0.5, 'max_length':4096,
                           'max_examples':2 if args.smoke else 50},
            'grader_root':str(Path(args.grader_root).resolve()) if args.grader_root else None,
            'sandbox':{'backend':args.grader_backend, 'timeout':10, 'memory_mb':2048}}


def prune_checkpoints(store, successor):
    """Delete only own older checkpoint directories after successor eval is sealed."""
    prefix = f'round{successor:03d}'
    if not store.is_done(prefix + '.train') or not store.is_done(prefix + '.evaluate'):
        raise ValueError('Successor checkpoint and evaluation must be sealed before pruning')
    for number in range(1, successor):
        path = store.root / f'round{number:03d}' / 'checkpoint'
        if not path.exists():
            continue
        resolved = path.resolve()
        if path.is_symlink() or not resolved.is_relative_to(store.root):
            raise ValueError('Refusing to prune checkpoint outside owned study')
        marker = path / 'owner.json'
        if not marker.exists() or json.loads(marker.read_text()).get('run_identity') != store.identity:
            raise ValueError('Refusing to prune a checkpoint without matching ownership')
        atomic_json(store.root / 'receipts' / f'round{number:03d}.pruned.json', {
            'run_identity':store.identity, 'checkpoint':str(path.relative_to(store.root)),
            'sealed_successor':successor, 'timestamp':time.time()})
        shutil.rmtree(path)


def _evaluate(domain, tasks, records, settings, directory):
    if domain == 'safety':
        # SafeChain source labels are not independent judgments of new completions.
        metrics = {'status':'generated_unscored', 'tasks':len(tasks), 'samples':len(records),
                   'accuracy':None, 'reason':'No independent safety correctness judge supplied'}
    else:
        from improving.text_tasks import score_text_records
        scored, metrics = score_text_records(task_views(tasks), records, expected_samples=1,
            grader_root=settings['grader_root'], sandbox=settings['sandbox'], seed=settings['seed'])
        if 'math500' in metrics:
            metrics['math500']['coverage_definition'] = 'pass@1 from one response per task; no multi-response diversity estimate'
        write_jsonl(directory / 'scored.jsonl', scored)
    atomic_json(directory / 'metrics.json', metrics)


def study_runtime_identity(settings):
    """Bind installed training libraries and the actual grading execution path."""
    from importlib.metadata import PackageNotFoundError, version
    from improving.pipeline import training_runtime_identity, execution_runtime_identity
    result = {'training': training_runtime_identity()}
    if settings['domain'] == 'math':
        result['evaluation'] = execution_runtime_identity(settings['sandbox'])
        dependencies = {}
        for package in ('sympy', 'antlr4-python3-runtime', 'latex2sympy2'):
            try:
                dependencies[package] = version(package)
            except PackageNotFoundError:
                dependencies[package] = None
        result['grading_dependencies'] = dependencies
    else:
        result['evaluation'] = {'backend': 'python-choice-parser' if settings['domain'] == 'qa'
                                else 'unscored'}
    return result


def prepare_training_attempt(store, name, checkpoint, parent_identity, records, settings, seed):
    """Persist lineage before training; preserve unsealed owned saves for diagnosis.

    Training's atomic save can finish before the stage receipt. Such a checkpoint
    is never guessed to be complete: quarantine it and deterministically retrain
    from the sealed predecessor. No unknown checkpoint is adopted or deleted.
    """
    checkpoint = Path(checkpoint)
    expected = store.root / name / 'checkpoint'
    if checkpoint.is_symlink() or checkpoint.resolve() != expected or not expected.is_relative_to(store.root):
        raise ValueError('Training checkpoint must be inside its owned round directory')
    intent_path = store.root / name / 'training_intent.json'
    intent = {'format': 1, 'run_identity': store.identity, 'stage': name + '.train',
              'checkpoint': str(expected.relative_to(store.root)),
              'parent_model_identity': parent_identity, 'records_sha256': stable_hash(records),
              'training_settings': settings, 'seed': seed}
    if intent_path.exists():
        if json.loads(intent_path.read_text()) != intent:
            raise ValueError('Training intent/model lineage mismatch')
    else:
        if checkpoint.exists():
            raise ValueError('Unsealed checkpoint has no prior ownership/lineage intent')
        atomic_json(intent_path, intent)
    if not checkpoint.exists():
        return
    if store.receipt_path(name + '.train').exists():
        raise ValueError('Refusing to quarantine a sealed checkpoint')
    if not checkpoint.is_dir():
        raise ValueError('Unsealed checkpoint is not a directory')
    owner_path = checkpoint / 'owner.json'
    if owner_path.exists() and json.loads(owner_path.read_text()).get('run_identity') != store.identity:
        raise ValueError('Unsealed checkpoint ownership mismatch')
    stats_path = checkpoint / 'training_stats.json'
    if stats_path.exists():
        stats = json.loads(stats_path.read_text())
        if (stats.get('seed') != seed or stats.get('configured_epochs') != settings['epochs']
                or stats.get('training_records_received') != len(records)):
            raise ValueError('Unsealed checkpoint training statistics contradict lineage intent')
    from uuid import uuid4
    quarantine = store.root / 'quarantine' / (name + '.' + uuid4().hex)
    quarantine.mkdir(parents=True)
    atomic_json(quarantine / 'recovery.json', {'action': 'preserve_unsealed_checkpoint_and_retrain',
                'training_intent': intent, 'checkpoint_files': tree_hashes(checkpoint)})
    checkpoint.rename(quarantine / 'checkpoint')


def audit_history(store):
    """Verify every retained stage artifact, allowing only recorded checkpoint pruning."""
    for receipt_path in sorted((store.root / 'receipts').glob('*.complete.json')):
        receipt = json.loads(receipt_path.read_text())
        if receipt.get('run_identity') != store.identity or receipt.get('status') != 'complete':
            raise ValueError('Historical stage identity/status drift')
        for relative, digest in receipt['artifacts'].items():
            target = store.root / relative
            if not target.resolve().is_relative_to(store.root):
                raise ValueError('Historical artifact escapes study directory')
            if target.is_file():
                if sha_file(target) != digest:
                    raise ValueError('Changed historical artifact: ' + relative)
                continue
            parts = Path(relative).parts
            name = parts[0] if parts else ''
            pruned_path = store.root / 'receipts' / (name + '.pruned.json')
            if (len(parts) < 3 or parts[1] != 'checkpoint'
                    or receipt.get('stage') != name + '.train' or not pruned_path.is_file()):
                raise ValueError('Missing historical artifact: ' + relative)
            pruned = json.loads(pruned_path.read_text())
            successor = pruned.get('sealed_successor')
            if (pruned.get('run_identity') != store.identity
                    or pruned.get('checkpoint') != name + '/checkpoint'
                    or not name.startswith('round') or not name[5:].isdigit()
                    or type(successor) is not int or successor <= int(name[5:])):
                raise ValueError('Invalid checkpoint pruning lineage')
            for suffix in ('.train', '.evaluate'):
                successor_receipt = store.receipt_path(f'round{successor:03d}' + suffix)
                if not successor_receipt.is_file():
                    raise ValueError('Pruning successor seal missing')
                seal = json.loads(successor_receipt.read_text())
                if seal.get('run_identity') != store.identity or seal.get('status') != 'complete':
                    raise ValueError('Pruning successor identity drift')


def run_study(args):
    import torch
    from improving.modeling import load_model
    from improving.generation import generate_to_file
    from improving.training import train_on_records, validate_full_completion_targets
    from improving.spectral import folded_operators
    from improving.spd_domains import calibrate_domains
    from improving.spd_safety import annotate_safety_tasks

    if not torch.cuda.is_available():
        raise RuntimeError('This runner requires an actual CUDA GPU')
    settings = study_settings(args)
    if args.domain == 'math':
        from improving.text_tasks import _verified_math_grader
        _verified_math_grader(args.grader_root)
    validate_full_completion_targets(settings['train'], settings['generation'])
    data_root = Path(args.prepared) / args.domain
    files = {split:data_root / (split + '.jsonl') for split in ('train','calibration','validation','eval')}
    tasks = {split:read_jsonl(path) for split,path in files.items()}
    if args.smoke:
        tasks = {split:rows[:2] for split,rows in tasks.items()}
    if any(not rows for rows in tasks.values()):
        raise ValueError('All prepared splits must be nonempty')
    if len(tasks['calibration']) != (2 if args.smoke else 50):
        raise ValueError('Study requires fixed 50 calibration tasks (2 in smoke)')
    if any(row.get('split') != split for split,rows in tasks.items() for row in rows):
        raise ValueError('Prepared split metadata mismatch')
    from improving.data import assert_disjoint_splits
    assert_disjoint_splits({split:task_views(rows) for split,rows in tasks.items()})
    source = {str(p.relative_to(ROOT)):sha_file(p) for p in sorted((ROOT/'src/improving').glob('*.py'))}
    source['scripts/run_spd14b.py'] = sha_file(__file__)
    print('Fingerprinting exact initial model weights and prepared sources', flush=True)
    model_files = tree_hashes(Path(args.model))
    if not model_files or not any(name.endswith('.safetensors') for name in model_files):
        raise ValueError('Initial model requires local safetensors weights')
    initial_identity = stable_hash(model_files)
    grader_files = tree_hashes(Path(args.grader_root)/'prm800k/grading') if args.grader_root else {}
    manifest = {'format':1, 'settings':settings, 'initial_model_identity':initial_identity,
                'model_files':model_files, 'source':source, 'grader_files':grader_files,
                'runtime':study_runtime_identity(settings),
                'data':{split:sha_file(path) for split,path in files.items()},
                'selected_tasks_sha256':stable_hash(tasks),
                'safety_annotation_contract':'initial-model-selected relevance, fixed across rounds, not ground truth'}
    root = Path(args.output_dir).resolve()
    with run_lock(root):
        store = StageStore(root, manifest, resume=args.resume)
        audit_history(store)
        # Start from newest sealed training output; old checkpoint weights may be pruned.
        completed = [i for i in range(1,settings['rounds']+1)
                     if store.receipt_path(f'round{i:03d}.train').exists()]
        latest = max(completed, default=0)
        if completed != list(range(1,latest+1)):
            raise ValueError('Noncontiguous sealed round history')
        checkpoint = root/f'round{latest:03d}'/'checkpoint' if latest else None
        if latest and not store.is_done(f'round{latest:03d}.train'):
            raise ValueError('Latest checkpoint is not sealed')
        free, total = torch.cuda.mem_get_info()
        budget = memory_budget(total, free, args.reserve_gib, args.memory_budget_gib)
        torch.cuda.set_per_process_memory_fraction(budget / total)
        atomic_json(root/'receipts'/f'gpu_admission.{time.time_ns()}.json', {
            'total_bytes':total, 'free_bytes_before_load':free, 'allocator_budget_bytes':budget,
            'reserve_gib':args.reserve_gib, 'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),
            'device':torch.cuda.get_device_name()})
        print(json.dumps({'gpu_allocator_budget_gib':budget/2**30, 'reserved_free_gib':args.reserve_gib}),flush=True)
        model, tokenizer = store.execute(f'model_load.{time.time_ns()}',
            lambda:load_model(settings['model'], checkpoint=checkpoint), [])
        model_identity = (stable_hash(tree_hashes(checkpoint)) if latest else initial_identity)
        calibration = tasks['calibration']
        if args.domain == 'safety' and args.method == 'spd':
            annotation_path = root/'initial_safety_annotations.jsonl'
            if not store.is_done('initial_annotation'):
                if latest:
                    raise ValueError('Cannot annotate with evolved weights; initial annotations missing')
                def annotate():
                    selected = annotate_safety_tasks(model,tokenizer,calibration,root/'annotation_raw.json',
                        initial_model_identity=initial_identity,batch_size=2,max_new_tokens=4096,seed=args.seed)
                    write_jsonl(annotation_path, selected)
                store.execute('initial_annotation',annotate,[annotation_path,root/'annotation_raw.json'])
            calibration = read_jsonl(annotation_path)
        fixed_calibration_hash = stable_hash(calibration)

        def generation(name, directory, population, *, projected=None, round_index=0):
            destination = directory/'completions.jsonl'
            def action():
                with folded_operators(model,projected) if projected is not None else nullcontext():
                    generate_to_file(model,tokenizer,task_views(population),destination,settings['generation'],
                        seed=args.seed,model_identity=model_identity,method=args.method,
                        round_index=round_index,stage=name,resume=(destination.with_suffix('.jsonl.parts')/'manifest.json').exists())
            store.execute(name,action,[destination,destination.with_suffix('.jsonl.budget.json')])
            return read_jsonl(destination)

        def evaluate(round_index):
            name = 'baseline' if round_index == 0 else f'round{round_index:03d}'
            directory = root/name/'evaluation'
            records = generation(name+'.eval_generation',directory,tasks['eval'],round_index=round_index)
            artifacts = [directory/'metrics.json']
            if args.domain != 'safety': artifacts.append(directory/'scored.jsonl')
            store.execute(name+'.evaluate',lambda:_evaluate(args.domain,tasks['eval'],records,settings,directory),artifacts)

        if latest:
            if not store.is_done('baseline.evaluate'):
                raise ValueError('Sealed checkpoint missing baseline evaluation')
            evaluate(latest)
            prune_checkpoints(store,latest)
        else:
            evaluate(0)
        for round_index in range(latest+1,settings['rounds']+1):
            name = f'round{round_index:03d}'
            directory = root/name
            if stable_hash(calibration) != fixed_calibration_hash:
                raise ValueError('Calibration records changed across rounds')
            operators = None
            if args.method == 'spd':
                # Covariance is recomputed for each evolved checkpoint, with fixed tasks/spans.
                calibration_dir = directory/'calibration'
                result = {}
                def calibrate():
                    result['operators'] = calibrate_domains(model,tokenizer,calibration,
                        settings['calibration'],calibration_dir,model_identity=model_identity)
                store.execute(name+'.calibrate',calibrate,[calibration_dir/'calibration.pt'])
                operators = result.pop('operators', None)
                if operators is None:
                    operators = calibrate_domains(model,tokenizer,calibration,settings['calibration'],
                                                   calibration_dir,model_identity=model_identity)
            records = generation(name+'.synthesis',directory/'synthesis',tasks['train'],
                                 projected=operators,round_index=round_index)
            del operators
            gc.collect()
            torch.cuda.empty_cache()
            next_checkpoint = directory/'checkpoint'
            def train():
                nonlocal model
                prepare_training_attempt(store,name,next_checkpoint,model_identity,records,
                                         settings['train'],args.seed+round_index)
                model, stats = train_on_records(model,tokenizer,task_views(tasks['train']),records,
                    settings['train'],next_checkpoint,seed=args.seed+round_index)
                atomic_json(next_checkpoint/'owner.json',{'run_identity':store.identity})
                atomic_json(directory/'training_receipt.json',stats)
            store.execute(name+'.train',train,[next_checkpoint,directory/'training_receipt.json',
                                               directory/'training_intent.json'])
            model_identity = stable_hash(tree_hashes(next_checkpoint))
            evaluate(round_index)
            prune_checkpoints(store,round_index)
        atomic_json(root/'complete.json',{'run_identity':store.identity,'rounds':settings['rounds'],
                    'smoke':args.smoke,'status':'complete','safety_scored':False,
                    'fixed_calibration_sha256':fixed_calibration_hash,**memory_receipt()})


def memory_budget(total_bytes, free_bytes, reserve_gib, requested_gib=None):
    if reserve_gib < 10 or requested_gib is not None and requested_gib <= 0:
        raise ValueError('Reserve must be at least 10 GiB and explicit budget positive')
    available = free_bytes - int(reserve_gib * 2**30)
    budget = min(available, int(requested_gib * 2**30)) if requested_gib is not None else available
    if not 0 < budget <= total_bytes:
        raise ValueError('No GPU budget remains after the free-memory reserve')
    return budget


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--domain',choices=['math','qa','safety'],required=True)
    result.add_argument('--method',choices=['base','spd'],default='spd')
    result.add_argument('--model',default='/root/ai-assets/models/qwen25-14b-instruct')
    result.add_argument('--prepared',default='/root/ai-assets/spd14b-20261108/prepared')
    result.add_argument('--output-dir',required=True)
    result.add_argument('--grader-root', default='/root/spectrum-prep-20261106/data/multidomain/math_full_20261106/sources/prm800k')
    result.add_argument('--grader-backend',choices=['bwrap','local'],default='bwrap')
    result.add_argument('--reserve-gib',type=float,default=12.0)
    result.add_argument('--memory-budget-gib',type=float)
    result.add_argument('--seed',type=int,default=42)
    result.add_argument('--resume',action='store_true')
    result.add_argument('--smoke',action='store_true')
    return result


if __name__ == '__main__':
    run_study(parser().parse_args())
