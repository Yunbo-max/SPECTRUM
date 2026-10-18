"""B02 staged diagnostic. Authored, unexecuted; invoke only via admitted hn01 work.
No pipeline/all stage, no scorer, no generated-program execution.
"""
from __future__ import annotations
import argparse
import contextlib
import copy
import fcntl
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import resource
import signal
import socket
import sys
import time
import traceback


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.replace(temp, path)


def pin(path):
    return {'path': str(Path(path).resolve()), 'sha256': sha(path)}


def checked(ref, root=None):
    p = Path(ref['path'])
    if not p.is_absolute():
        p = Path(root or '.') / p
    if sha(p) != ref['sha256']:
        raise ValueError(f'Input identity mismatch: {p}')
    return p


def project_pin(ref, root):
    """Strict project-relative pin; never resolve traversal or symlinks away."""
    if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}:
        raise ValueError('Expected exact path/sha256 pin')
    raw = ref['path']
    if not isinstance(raw, str) or not raw or '\\' in raw:
        raise ValueError('Invalid project-relative path')
    parts = raw.split('/')
    if any(x in ('', '.', '..') for x in parts) or Path(raw).is_absolute():
        raise ValueError('Project-relative normalized path required')
    digest = ref['sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Invalid SHA256')
    root = Path(root).absolute()
    cursor = Path(root.anchor)
    for part in root.parts[1:] + tuple(parts):
        cursor /= part
        if cursor.is_symlink():
            raise ValueError(f'Symlink forbidden in pinned input: {cursor}')
    if not cursor.is_file() or sha(cursor) != digest:
        raise ValueError(f'Input identity mismatch: {cursor}')
    return cursor


def validate_cd_evidence(ref, root, protocol, goal_id, candidate_id):
    path = project_pin(ref, root)
    evidence = read(path)
    expected = {'kind': 'research-cd-experiment', 'schema_version': 1,
                'flow_profile': 'work-harness-cd-v1', 'stage': 'diagnosis',
                'goal_id': goal_id, 'candidate_id': candidate_id}
    if not goal_id or not candidate_id or any(evidence.get(k) != v for k, v in expected.items()):
        raise ValueError('Wrong experiment kind/schema/profile/stage/goal/candidate')
    if type(evidence.get('schema_version')) is not int:
        raise ValueError('Experiment schema_version must be integer 1')
    if protocol.get('evidence_mode') != 'developmental' or protocol.get('cd_development') != {
            'flow_profile': 'work-harness-cd-v1', 'stage': 'diagnosis', 'cd_evidence_ref': ref}:
        raise ValueError('Requires exact reviewed C/D experiment pin in protocol')
    return evidence


def validate_deployment(ref, root, code_root, config_path):
    """Manifest is external to its files: no experiment/config/source hash cycle."""
    path = project_pin(ref, root)
    manifest = read(path)
    if manifest.get('kind') != 'b02-stable-deployment' or type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1:
        raise ValueError('Wrong deployment manifest')
    files = manifest.get('files')
    if not isinstance(files, list) or not files:
        raise ValueError('Missing deployment files')
    seen = set()
    for item in files:
        p = project_pin(item, root)
        if p == path or item['path'] in seen:
            raise ValueError('Self-reference or duplicate deployment pin')
        seen.add(item['path'])
    code_root = Path(code_root).absolute()
    required = {str(Path(config_path).absolute().relative_to(Path(root).absolute()))}
    for p in code_root.rglob('*'):
        if p.is_symlink():
            raise ValueError('Deployment tree contains symlink')
        if p.is_file() and p.suffix == '.py':
            required.add(str(p.relative_to(Path(root).absolute())))
    if not required.issubset(seen):
        raise ValueError('Deployment manifest omits code/config dependency')
    return files


def validate_upstream_deployment(manifest, cfg):
    """Require actual package inventory, including initialization, before import."""
    source = Path(cfg['source_root']).absolute()
    refs = manifest.get('upstream_files', [])
    if not isinstance(refs, list) or not refs:
        raise ValueError('Complete upstream_files manifest required')
    by_path = {}
    for ref in refs:
        project_pin(ref, source)
        if ref['path'] in by_path:
            raise ValueError('Duplicate upstream dependency')
        by_path[ref['path']] = ref['sha256']
    package = source / 'src/improving'
    required = {'src/improving/__init__.py'}
    for path in package.rglob('*'):
        if path.is_symlink():
            raise ValueError('Upstream package symlink forbidden')
        if path.is_file() and path.suffix == '.py':
            required.add(str(path.relative_to(source)))
    if not required.issubset(by_path):
        raise ValueError('Unpinned upstream Python dependency')
    if any(by_path.get(name) != digest for name, digest in cfg['source_hashes'].items()):
        raise ValueError('Upstream manifest/config mismatch')
    return refs


def inventory(root):
    root = Path(root)
    if root.is_symlink() or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Output symlinks are not admissible inventory members')
    return [{'path': str(p.relative_to(root)), 'sha256': sha(p), 'bytes': p.stat().st_size}
            for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink()]


def verify_inventory(root, items):
    if inventory(root) != items:
        raise ValueError(f'Output inventory changed: {root}')


def classify_error(exc):
    # No guessed "CUDA" string classification; non-OOM faults must stop calibration.
    if isinstance(exc, TimeoutError): return 'timeout'
    if type(exc).__name__ == 'OutOfMemoryError': return 'resource_oom'
    if isinstance(exc, FileExistsError): return 'attempt_conflict'
    if isinstance(exc, (ValueError, KeyError)): return 'contract_error'
    return 'implementation_or_environment_error'


def batch_settings(size):
    if size not in [64, 32, 16, 8, 4, 2, 1]:
        raise ValueError('Unsupported calibration size')
    return {'batch_size': min(16, size), 'task_batch_size': max(1, size // 16),
            'sequence_batch_size': size}


def adapt_sources(train_capture, test_rows, revision):
    """Offline equivalent of prepare_mbpp, retaining all source fields separately."""
    from improving.data import _mbpp_interface, prompt_fingerprint, assert_disjoint_splits
    if not isinstance(train_capture, dict) or not isinstance(train_capture.get('raw_rows'), list):
        raise ValueError('train must be captured raw_rows object')
    if not isinstance(test_rows, list) or len(test_rows) != 500:
        raise ValueError('test must be original full/test500 array')
    train = train_capture['raw_rows']
    for rows in (train, test_rows):
        ids = [r['task_id'] for r in rows]
        if len(ids) != len(set(ids)): raise ValueError('Duplicate source ID')
    eval_prompts = {}
    for r in sorted(test_rows, key=lambda r: int(r['task_id'])):
        fp = prompt_fingerprint(r.get('original_prompt', r['text']))
        eval_prompts.setdefault(fp, []).append(f"Mbpp/{r['task_id']}")
    pool, exclusions, seen = [], [], {}
    for r in sorted(train, key=lambda r: int(r['task_id'])):
        fp = prompt_fingerprint(r.get('original_prompt', r['text']))
        reason = ('original_prompt_overlaps_official_test' if fp in eval_prompts else
                  'duplicate_original_prompt_in_train_pool' if fp in seen else None)
        if reason:
            exclusions.append({'task_id': f"Mbpp/{r['task_id']}", 'reason': reason,
                               'prompt_fingerprint': fp,
                               'matching_task_ids': eval_prompts.get(fp, [seen.get(fp)])})
        else:
            seen[fp] = f"Mbpp/{r['task_id']}"; pool.append(r)
    if len(pool) <= 80: raise ValueError('Insufficient official training pool')
    random.Random(42).shuffle(pool)
    groups = {'calibration': pool[:50], 'validation': pool[50:80],
              'train': pool[80:], 'eval': test_rows}
    prepared, fields = {}, []
    for split, rows in groups.items():
        prepared[split] = []
        for row in rows:
            task = dict(task_id=f"Mbpp/{row['task_id']}", original_task_id=row['task_id'],
                        **_mbpp_interface(row), reference=row['code'],
                        tests='\n'.join(filter(None, [row.get('test_setup_code', ''), *row['test_list']])),
                        source='google-research-datasets/mbpp', split=split,
                        original_split='test' if split == 'eval' else 'train', dataset_config='full',
                        revision=revision, split_seed=42, dataset_fingerprint=None)
            prepared[split].append(task)
            fields.append({'task_id': task['task_id'], 'split': split, 'source_fields': row})
    assert_disjoint_splits(prepared)
    manifest = {'preparation_protocol': 'mbpp-official-test-preserving-decontamination-v1',
                'adapter': 'offline-captured-raw-rows-v1', 'split_seed': 42,
                'dataset_revision': revision, 'dataset_fingerprint': None,
                'fingerprint_note': 'HF runtime fingerprint unavailable; exact raw files pinned instead',
                'source_counts': {'train': len(train), 'test': len(test_rows)},
                'clean_train_pool_count': len(pool), 'excluded_count': len(exclusions),
                'exclusions': exclusions, 'output_counts': {k: len(v) for k,v in prepared.items()},
                'output_task_ids': {k: [r['task_id'] for r in v] for k,v in prepared.items()}}
    return prepared, fields, manifest


def require_stage(run, name):
    stage = Path(run) / 'stages' / name
    identity = read(Path(run) / 'identity.json')
    request = read(stage / 'request.json')
    if {k:v for k,v in request.items() if k != 'stage_parameters'} != dict(identity, stage=name):
        raise ValueError(f'Dependency protocol/config/code changed: {name}')
    receipt = read(stage / 'receipt.json')
    if receipt['status'] != 'completed': raise ValueError(f'Incomplete dependency: {name}')
    verify_inventory(stage / 'outputs', receipt['outputs'])
    return stage / 'outputs', pin(stage / 'receipt.json')


def require_failed_calibration(run, name):
    """An OOM exception is reusable only with this run's sealed partial identity."""
    stage = Path(run) / 'stages' / name
    identity = read(Path(run) / 'identity.json')
    request = read(stage / 'request.json')
    if {k:v for k,v in request.items() if k != 'stage_parameters'} != dict(identity, stage=name):
        raise ValueError('Foreign failed calibration request')
    receipt = read(stage / 'receipt.json')
    if receipt.get('stage') != name or receipt.get('status') != 'failed' or receipt.get('error_class') != 'resource_oom':
        raise ValueError('Only the same-run OOM calibration is eligible')
    if receipt.get('execution_identity') != request['stage_parameters'].get('execution_identity'):
        raise ValueError('Failed calibration producer mismatch')
    for key in ('protocol_ref', 'cd_evidence_ref', 'deployment_manifest_ref'):
        if receipt.get(key) != identity[key]:
            raise ValueError('Failed calibration input mismatch')
    verify_inventory(stage / 'outputs', receipt['partial_outputs'])
    return receipt


def require_profile(run, cfg):
    path, receipt = require_stage(run, 'freeze-profile')
    profile = read(path / 'profile.json')
    if profile['config_sha256'] != cfg['_sha256'] or profile['status'] != 'qualified':
        raise ValueError('No matching measured/frozen profile')
    return profile, receipt


def verify_sources(cfg):
    """Verify bytes BEFORE importing improving; avoid importing stale installed package."""
    source = Path(cfg['source_root']).resolve()
    for rel, expected in cfg['source_hashes'].items():
        if sha(source / rel) != expected: raise ValueError(f'Upstream source mismatch {rel}')
    sys.path.insert(0, str(source / 'src'))
    import improving
    if not Path(improving.__file__).resolve().is_relative_to(source):
        raise ValueError('Wrong improving installation imported')


def asset_inventory(root):
    # HF snapshots use symlinks into content-addressed blobs. Hash actual bytes,
    # retain the snapshot-relative filenames, and never mistake an empty list for assets.
    root=Path(root)
    items=[{'path':str(p.relative_to(root)),'sha256':sha(p),'bytes':p.stat().st_size}
           for p in sorted(root.rglob('*')) if p.is_file()]
    names=[i['path'] for i in items]
    if 'config.json' not in names or not any(n.endswith('.safetensors') for n in names):
        raise ValueError('Missing local base weights/config; no download fallback')
    if not any(n.startswith('tokenizer') for n in names):
        raise ValueError('Missing tokenizer assets')
    return items


def load_base(cfg, run, checkpoint=None):
    from improving.modeling import load_model
    prepared,_=require_stage(run,'prepare')
    if asset_inventory(cfg['model']['name']) != read(prepared/'base-assets.json')['files']:
        raise ValueError('Base/tokenizer bytes changed since preparation')
    model, tokenizer = load_model(cfg['model'], checkpoint=checkpoint)
    if str(next(model.parameters()).device) != 'cuda:0':
        raise ValueError('Only authorized cuda:0 workload is supported')
    return model, tokenizer


def tasks_for(run, split):
    from improving.data import read_jsonl
    data, receipt = require_stage(run, 'prepare')
    return read_jsonl(data / f'{split}.jsonl'), receipt


def validate_generated(rows, tasks, seed, method):
    expected = [(t['task_id'], j) for t in tasks for j in range(16)]
    if [(r['task_id'], r['sample_id']) for r in rows] != expected:
        raise ValueError('Incomplete, duplicated or reordered generated outputs')
    if any(r['seed'] != seed or r['round'] != 1 or r['method'] != method for r in rows):
        raise ValueError('Generation identity mismatch')


def checkpoint_for(run, arm):
    if arm == 'F': return None, None
    folder, receipt = require_stage(run, f'train-{arm}')
    return folder / 'checkpoint', receipt


def prepare(args, cfg, out):
    from improving.data import write_jsonl
    train = checked(cfg['train_source_ref'], args.project_root)
    test = checked(cfg['test_source_ref'], args.project_root)
    groups, fields, manifest = adapt_sources(read(train), read(test), cfg['dataset_revision'])
    manifest['source_refs'] = [pin(train), pin(test)]
    for split, rows in groups.items(): write_jsonl(out / f'{split}.jsonl', rows)
    write_jsonl(out / 'source_fields.jsonl', fields)
    write_jsonl(out / 'preparation_manifest.jsonl', [manifest])
    write(out / 'task-manifest.json', {'task_ids': manifest['output_task_ids']['eval'],
                                      'population': 'MBPP full/test', 'denominator': 500})
    write(out / 'base-assets.json', {'revision':cfg['model_revision'],
                                    'files':asset_inventory(cfg['model']['name'])})
    return {'source_refs': manifest['source_refs'], 'measured_counts': manifest['output_counts']}


def generation(args, cfg, out):
    from improving.generation import generate_to_file
    from improving.modeling import render_prompt
    profile, profile_ref = require_profile(args.run_root, cfg)
    is_train = args.stage == 'generate-train'
    arm, seed = ('F', 43) if is_train else (args.arm, args.seed)
    tasks, data_ref = tasks_for(args.run_root, 'train' if is_train else 'eval')
    cp, cp_ref = checkpoint_for(args.run_root, arm)
    model, tokenizer = load_base(cfg, args.run_root, cp)
    settings = dict(cfg['generation'], **profile['batch_settings'])
    identity = cfg['model_revision'] if cp is None else cp_ref['sha256']
    stage = 'training' if is_train else 'evaluation'
    prompts = [{'task_id': t['task_id'], 'original_task_id': t['original_task_id'],
                'prompt': render_prompt(tokenizer, t),
                'prompt_ids':tokenizer.encode(render_prompt(tokenizer,t),add_special_tokens=False)} for t in tasks]
    prompts_path = out / 'prompts.json'
    if prompts_path.exists():
        if read(prompts_path) != prompts: raise ValueError('Prompt readback mismatch')
    else: write(prompts_path, prompts)
    rows = generate_to_file(model, tokenizer, tasks, out / 'predictions.jsonl', settings,
                            seed=seed, model_identity=identity, method=arm, round_index=1,
                            stage=stage, resume=args.resume)
    validate_generated(rows, tasks, seed, arm)
    meta = {'arm': arm, 'seed': seed, 'round': 1, 'stage': stage,
            'protocol_ref': args.protocol_ref, 'model_identity': identity,
            'checkpoint_receipt_ref': cp_ref, 'prepared_receipt_ref': data_ref,
            'profile_receipt_ref': profile_ref, 'prompts_ref': pin(prompts_path),
            'raw_ref': pin(out / 'predictions.jsonl'),
            'generation_manifest_ref': pin(out / 'predictions.jsonl.parts/manifest.json'),
            'scoring_status': 'pending', 'generated_code_execution_enabled': False}
    write(out / 'identity.json', meta)
    if not is_train and arm == 'F' and seed == 43:
        write(out / 'generation_policy.json', {'same_artifact_ref': pin(out / 'predictions.jsonl'),
              'not_independent': True, 'population': 'eval; not synthetic training corpus'})
    return meta


def training(args, cfg, out):
    from improving.data import read_jsonl, write_jsonl
    from training_instrumented import train_on_records
    profile, profile_ref = require_profile(args.run_root, cfg)
    qualified, training_profile_ref = require_stage(args.run_root, 'calibrate-training')
    training_profile = read(qualified / 'profile.json')
    if not training_profile['eligible'] or training_profile['config_sha256'] != cfg['_sha256']:
        raise ValueError('Training optimizer/merge/save peaks not qualified')
    tasks, data_ref = tasks_for(args.run_root, 'train')
    raw, synthetic_receipt = require_stage(args.run_root, 'generate-train')
    records = read_jsonl(raw / 'predictions.jsonl')
    validate_generated(records, tasks, 43, 'F')
    synthetic_ref = pin(raw / 'predictions.jsonl')
    settings = dict(cfg['train'], fixed_anchor_replay=args.arm == 'A')
    if args.arm == 'A':
        anchors, _ = tasks_for(args.run_root, 'calibration')
        if len(anchors) != 50 or any(not t['reference'].strip() for t in anchors):
            raise ValueError('Exactly fifty fixed original references required')
        reference_records = [{'task_id': t['task_id'], 'sample_id': 0, 'completion': t['reference'],
                              'round': 1, 'record_origin': 'fixed_anchor_reference'} for t in anchors]
        write_jsonl(out / 'anchor-records.jsonl', reference_records)
        write(out / 'anchor-provenance.json', {'calibration_receipt_ref': data_ref,
              'synthetic_ref': synthetic_ref, 'reference_count': 50, 'additional_information': True})
        tasks = tasks + anchors; records = records + reference_records
    # Always reload immutable base. Never warm-start A from P.
    model, tokenizer = load_base(cfg, args.run_root)
    _, stats = train_on_records(model, tokenizer, tasks, records, settings,
                               out / 'checkpoint', seed=44, telemetry_dir=out / 'telemetry')
    meta = {'arm': args.arm, 'training_seed': 44, 'base_revision': cfg['model_revision'],
            'synthetic_ref': synthetic_ref, 'synthetic_receipt_ref': synthetic_receipt,
            'profile_ref': profile_ref, 'training_profile_ref': training_profile_ref,
            'protocol_ref': args.protocol_ref, 'stats': stats}
    write(out / 'training-identity.json', meta)
    return meta


def calibrate_inference(args, cfg, out):
    import torch
    from improving.modeling import render_prompt, seed_everything
    from improving.generation import generate_to_file
    sizes = cfg['calibration']['sequence_candidates']
    previous_seconds = 0
    for receipt_file in (Path(args.run_root)/'stages').glob('calibrate-inference-*/receipt-*.json'):
        receipt = read(receipt_file)
        previous_seconds += receipt['ended_at_unix'] - receipt['started_at_unix']
    remaining = cfg['calibration']['whole_calibration_seconds'] - previous_seconds
    if remaining <= 0:
        raise ValueError('Inference calibration envelope exhausted; reviewed replan required')
    signal.alarm(max(1, min(300, int(remaining))))
    size = args.batch
    pos = sizes.index(size)
    # Each command probes one candidate only; descending predecessor receipt is required.
    if pos:
        previous = Path(args.run_root) / 'stages' / f'calibrate-inference-{sizes[pos-1]}' / 'receipt.json'
        record = read(previous)
        if record['status'] == 'failed':
            require_failed_calibration(args.run_root, f'calibrate-inference-{sizes[pos-1]}')
        else:
            prev_out, _ = require_stage(args.run_root, f'calibrate-inference-{sizes[pos-1]}')
            if read(prev_out / 'profile.json')['eligible']:
                raise ValueError('Larger stable setting already qualifies; no routine smaller probes')
    model, tokenizer = load_base(cfg, args.run_root)
    calibration, data_ref = tasks_for(args.run_root, 'calibration')
    # Freeze original calibration order; qualify worst observed prompt width separately.
    all_tasks = []
    for split in ('train','calibration','validation','eval'):
        rows, _ = tasks_for(args.run_root, split); all_tasks.extend(rows)
    lengths = [len(tokenizer.encode(render_prompt(tokenizer,t),add_special_tokens=False)) for t in all_tasks]
    if max(lengths) > 1024: raise ValueError('Overlong real prompt; cannot truncate tasks')
    mapping = batch_settings(size)
    group_count = mapping['task_batch_size']
    # For size <16, 1 task would cause >2 generator calls; use n=2*size pilot only.
    settings = dict(cfg['generation'], **mapping)
    settings['samples'] = min(16, size)
    pilot_tasks = calibration[:group_count]
    free_before, total = torch.cuda.mem_get_info()
    reserved_before = torch.cuda.memory_reserved()
    torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize()
    started = time.monotonic()
    old_min = model.generation_config.min_new_tokens
    old_max = model.generation_config.max_new_tokens
    try:
        # Calibration-only forced 512 outputs: do not confuse with formal random draw.
        model.generation_config.min_new_tokens = 512
        rows = generate_to_file(model, tokenizer, pilot_tasks, out/'pilot.jsonl', settings,
               seed=43, model_identity=cfg['model_revision'], method='calibration',
               round_index=1, stage='calibration', resume=False)
        # Shape-bound resource check using an actual longest prompt, no generated eval fixture.
        longest = all_tasks[lengths.index(max(lengths))]
        ids = tokenizer.encode(render_prompt(tokenizer,longest),add_special_tokens=False)
        inp = torch.tensor([ids] * group_count, device='cuda:0')
        seed_everything(43)
        with torch.inference_mode():
            bound = model.generate(input_ids=inp, attention_mask=torch.ones_like(inp),
                       do_sample=True, temperature=.8, top_p=.95, top_k=0,
                       num_return_sequences=mapping['batch_size'], min_new_tokens=512,
                       max_new_tokens=512, pad_token_id=tokenizer.pad_token_id,use_cache=True)
        torch.cuda.synchronize()
        finite = bool(torch.isfinite(bound).all().item())
        actual_shape = list(bound.shape)
        del bound, inp
    finally:
        model.generation_config.min_new_tokens = old_min
        model.generation_config.max_new_tokens = old_max
    elapsed = time.monotonic()-started
    allocated = torch.cuda.max_memory_allocated(); reserved = torch.cuda.max_memory_reserved()
    free_after, _ = torch.cuda.mem_get_info()
    measured_headroom = min(free_after, free_before-max(0,reserved-reserved_before))
    available_for_process = free_before + reserved_before
    eligible = (finite and actual_shape == [size, max(lengths)+512]
                and reserved <= .85 * available_for_process and measured_headroom >= 2*1024**3)
    p = {'config_sha256': cfg['_sha256'], 'batch_settings': mapping, 'sequence_batch_size': size,
         'actual_source_interface': 'generate_to_file batch_size/task_batch_size/sequence_batch_size',
         'actual_bound_shape': actual_shape, 'max_real_prompt_tokens': max(lengths),
         'forced_output_tokens': 512, 'formal_samples': 16, 'pilot_samples': len(rows),
         'elapsed_seconds': elapsed, 'pilot_tokens_per_second_including_bound_probe': sum(r['generation_tokens'] for r in rows)/elapsed,
         'peak_allocated_bytes': allocated, 'peak_reserved_bytes': reserved, 'total_vram_bytes': total,
         'free_before_bytes':free_before,'free_after_bytes':free_after,'headroom_bytes':measured_headroom,
         'finite': finite, 'eligible': eligible, 'prepared_receipt_ref':data_ref,
         'qualification_scope':'BF16 native inference; worst actual prompt + forced512; no score',
         'training_qualified':False}
    write(out/'profile.json',p)
    return p


def calibrate_training(args, cfg, out):
    import torch
    from training_instrumented import qualify_training
    from improving.data import read_jsonl
    from improving.modeling import encode_example, render_prompt
    raw, raw_ref = require_stage(args.run_root, 'generate-train')
    tasks, _ = tasks_for(args.run_root, 'train')
    rows = read_jsonl(raw/'predictions.jsonl')
    model, tokenizer = load_base(cfg, args.run_root)
    # Worst-length real records from the entire prospective P/A corpus, determined
    # without scoring, cover both synthetic completions and fixed anchor lengths.
    anchors, _ = tasks_for(args.run_root, 'calibration')
    records = rows + [{'task_id':t['task_id'],'sample_id':0,'completion':t['reference'],
                       'record_origin':'fixed_anchor_reference','round':1} for t in anchors]
    task_map = {t['task_id']:t for t in tasks+anchors}
    lengths=[]
    for r in records:
        e=encode_example(tokenizer,render_prompt(tokenizer,task_map[r['task_id']]),r['completion'],
             max_length=1536,loss_scope='all',completion_ids=r.get('completion_ids'),
             append_eos=r.get('completion_ids') is None and r.get('finish_reason')!='length')
        lengths.append(len(e['input_ids']))
    chosen=sorted(range(len(records)),key=lambda i:(-lengths[i],i))[:16]
    selected=[records[i] for i in chosen]
    selected_ids={r['task_id'] for r in selected}
    selected_tasks=[t for t in tasks+anchors if t['task_id'] in selected_ids]
    free_before,total=torch.cuda.mem_get_info(); reserved_before=torch.cuda.memory_reserved()
    settings=dict(cfg['train'],fixed_anchor_replay=any(r.get('record_origin')=='fixed_anchor_reference' for r in selected))
    _, stats = qualify_training(model,tokenizer,selected_tasks,selected,settings,out/'probe',seed=44)
    peaks=[o['cuda_peak_reserved_bytes'] for o in stats['phase_observations']]
    peak=max(peaks); free_after,_=torch.cuda.mem_get_info()
    headroom=min(free_after,free_before-max(0,peak-reserved_before))
    profile={'config_sha256':cfg['_sha256'],'raw_ref':raw_ref,'stats':stats,
             'selected_record_indices':chosen,'selection':'16 longest encoded real records before scores',
             'max_full_corpus_encoded_length':max(lengths),'peak_reserved_bytes':peak,
             'headroom_bytes':headroom,'total_vram_bytes':total,
             'eligible':peak<=.85*(free_before+reserved_before) and headroom>=2*1024**3,
             'scope':'one real optimizer update plus merge/save, no full runtime qualification'}
    write(out/'profile.json',profile)
    return profile


def freeze_profile(args, cfg, out):
    pdir, pref = require_stage(args.run_root,f'calibrate-inference-{args.batch}')
    p = read(pdir/'profile.json')
    if not p['eligible'] or p['config_sha256'] != cfg['_sha256']:
        raise ValueError('No eligible matching inference measurement')
    # Initial inference freeze permits corpus export, not training. Training qualification
    # produces a separate receipt subsequently consumed by training, avoiding a cycle.
    write(out/'profile.json',dict(p,status='qualified',inference_receipt_ref=pref,training_qualified=False))
    return {'inference_receipt_ref':pref, 'training_status':'pending'}


def stage_name(args):
    if args.stage == 'generate-eval': return f'generate-eval-{args.arm}-{args.seed}'
    if args.stage == 'train': return f'train-{args.arm}'
    if args.stage == 'calibrate-inference': return f'calibrate-inference-{args.batch}'
    return args.stage


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['prepare','calibrate-inference','freeze-profile','generate-train',
                                  'calibrate-training','train','generate-eval'])
    p.add_argument('--config',required=True); p.add_argument('--config-sha256',required=True)
    p.add_argument('--project-root',required=True); p.add_argument('--run-root',required=True)
    p.add_argument('--protocol',required=True); p.add_argument('--protocol-sha256',required=True)
    p.add_argument('--cd-evidence',required=True); p.add_argument('--cd-evidence-sha256',required=True)
    p.add_argument('--goal-id',required=True); p.add_argument('--candidate-id',required=True)
    p.add_argument('--deployment-manifest',required=True)
    p.add_argument('--deployment-manifest-sha256',required=True)
    p.add_argument('--task-id',required=True); p.add_argument('--run-id',required=True)
    p.add_argument('--attempt-id',required=True)
    p.add_argument('--arm',choices=['F','P','A']); p.add_argument('--seed',type=int,choices=[43,45])
    p.add_argument('--batch',type=int,choices=[64,32,16,8,4,2,1]); p.add_argument('--resume',action='store_true')
    args=p.parse_args()
    execution_identity={k:getattr(args,k) for k in ('task_id','run_id','attempt_id')}
    if any(not v or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-' for c in v)
           for v in execution_identity.values()):
        raise ValueError('Invalid execution identity')
    if sha(args.config)!=args.config_sha256: raise ValueError('Immutable config digest mismatch')
    cfg=read(args.config); cfg['_sha256']=args.config_sha256
    if cfg['generated_code_execution_enabled'] is not False or cfg['backend']!='none':
        raise ValueError('All code execution/scoring backends forbidden by this driver')
    args.protocol_ref={'path':str(Path(args.protocol).resolve()),'sha256':args.protocol_sha256}
    checked(args.protocol_ref)
    protocol=read(args.protocol)
    args.cd_evidence_ref={'path':args.cd_evidence,'sha256':args.cd_evidence_sha256}
    validate_cd_evidence(args.cd_evidence_ref,args.project_root,protocol,args.goal_id,args.candidate_id)
    deployment_ref={'path':args.deployment_manifest,'sha256':args.deployment_manifest_sha256}
    deployment_files=validate_deployment(deployment_ref,args.project_root,Path(__file__).parent,args.config)
    upstream_files=validate_upstream_deployment(read(project_pin(deployment_ref,args.project_root)),cfg)
    if args.stage in ('calibrate-inference','freeze-profile') and args.batch is None: p.error('--batch required')
    if args.stage=='train' and args.arm not in ('P','A'): p.error('--arm P/A required')
    if args.stage=='generate-eval' and (args.arm is None or args.seed is None): p.error('--arm and --seed required')
    if sys.platform!='linux': raise RuntimeError('Execution belongs to authorized hn01 Linux host')
    if (Path(sys.executable).absolute()!=Path(cfg['interpreter']).absolute()
            or Path(sys.prefix).absolute()!=Path(cfg['interpreter']).parent.parent):
        raise RuntimeError('Wrong project venv; shared symlink target is not interpreter identity')
    os.environ['HF_HUB_OFFLINE']='1'; os.environ['HF_DATASETS_OFFLINE']='1'
    verify_sources(cfg)
    project_pin(cfg['train_source_ref'],args.project_root)
    project_pin(cfg['test_source_ref'],args.project_root)
    project_pin(cfg['design_ref'],args.project_root)
    for ref in cfg['source_refs']:
        project_pin(ref,args.project_root)
    run=Path(args.run_root); run.mkdir(parents=True,exist_ok=True)
    with (run/'.serial.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (run/'config.json').exists():
            if sha(run/'config.json')!=args.config_sha256: raise ValueError('Run config changed')
        else: (run/'config.json').write_bytes(Path(args.config).read_bytes())
        name=stage_name(args); folder=run/'stages'/name
        identity={'config_sha256':args.config_sha256,'protocol_ref':args.protocol_ref,
                  'implementation':[pin(p) for p in sorted(Path(__file__).parent.rglob('*.py'))],
                  'cd_evidence_ref':args.cd_evidence_ref,'goal_id':args.goal_id,
                  'candidate_id':args.candidate_id,'deployment_manifest_ref':deployment_ref,
                  'deployment_code_refs':deployment_files,
                  'upstream_code_refs':upstream_files,
                  'source_root':cfg['source_root'],'source_hashes':cfg['source_hashes']}
        if (run/'identity.json').exists():
            if read(run/'identity.json') != identity: raise ValueError('Immutable run identity changed')
        else: write(run/'identity.json',identity)
        request=dict(identity,stage=name,stage_parameters={
            'execution_identity':execution_identity,
            'batch':args.batch if args.stage in ('calibrate-inference','freeze-profile') else None,
            'arm':args.arm if args.stage in ('train','generate-eval') else None,
            'seed':args.seed if args.stage=='generate-eval' else None})
        receipt_path=folder/'receipt.json'
        if folder.exists():
            if read(folder/'request.json')!=request: raise ValueError('Unknown attempt identity')
            if receipt_path.exists() and read(receipt_path)['status']=='completed':
                verify_inventory(folder/'outputs',read(receipt_path)['outputs'])
                print(json.dumps(read(receipt_path))); return
            if not args.resume or args.stage not in ('generate-train','generate-eval'):
                raise FileExistsError('Interrupted stage retained; new reviewed attempt required')
            if not receipt_path.exists() or read(receipt_path)['status'] != 'failed':
                raise ValueError('Unsealed interrupted chunks require reviewed recovery, not automatic resume')
            verify_inventory(folder/'outputs',read(receipt_path)['partial_outputs'])
            # Parent native process identity must have been reconciled before --resume.
        else:
            folder.mkdir(parents=True); write(folder/'request.json',request)
        out=folder/'outputs'; out.mkdir(exist_ok=True)
        if args.stage not in ('prepare', 'freeze-profile'):
            import shutil
            if shutil.disk_usage(run).free < 16*1024**3: raise RuntimeError('Need 16GiB free workspace')
        started=time.time()
        seconds=300 if args.stage=='calibrate-inference' else cfg['stage_watchdogs'][args.stage]
        def expired(signum, frame): raise TimeoutError('Stage watchdog expired; retain partial evidence')
        signal.signal(signal.SIGALRM,expired); signal.alarm(seconds)
        fn={'prepare':prepare,'calibrate-inference':calibrate_inference,'freeze-profile':freeze_profile,
            'generate-train':generation,'generate-eval':generation,'train':training,
            'calibrate-training':calibrate_training}[args.stage]
        try:
            result=fn(args,cfg,out)
            receipt={'status':'completed','result':result,'outputs':inventory(out)}
        except BaseException as exc:
            receipt={'status':'failed','error_class':classify_error(exc),'error':str(exc),
                     'traceback':traceback.format_exc(),'partial_outputs':inventory(out)}
            torch=sys.modules.get('torch')
            if torch is not None and torch.cuda.is_initialized():
                try:
                    receipt['failure_resources']={
                        'peak_allocated_bytes':torch.cuda.max_memory_allocated(),
                        'peak_reserved_bytes':torch.cuda.max_memory_reserved()}
                except Exception as resource_error:
                    receipt['failure_resource_observation_error']=str(resource_error)
            raise
        finally:
            signal.alarm(0)
            receipt.update(stage=name,started_at_unix=started,ended_at_unix=time.time(),
                           execution_identity=execution_identity,
                           host=socket.gethostname(),pid=os.getpid(),argv=sys.argv,cwd=os.getcwd(),
                           config_ref=pin(args.config),protocol_ref=args.protocol_ref,
                           cd_evidence_ref=args.cd_evidence_ref,
                           deployment_manifest_ref=deployment_ref,
                           process_max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                           implementation_refs=identity['implementation'])
            receipt['environment']={}
            for package in ('torch','transformers','peft','numpy','datasets'):
                try: receipt['environment'][package]=importlib.metadata.version(package)
                except importlib.metadata.PackageNotFoundError: receipt['environment'][package]=None
            torch=sys.modules.get('torch')
            if torch is not None and torch.cuda.is_initialized():
                try:
                    receipt['cuda']={'device_name':torch.cuda.get_device_name(0),
                        'peak_allocated_bytes':torch.cuda.max_memory_allocated(),
                        'peak_reserved_bytes':torch.cuda.max_memory_reserved()}
                except Exception as resource_error:
                    receipt['cuda_observation_error']=str(resource_error)
            # Retain every retry receipt; completed receipt is a readback index only.
            write(folder/f'receipt-{time.time_ns()}.json',receipt)
            if receipt_path.exists(): receipt_path.unlink()
            write(receipt_path,receipt)
        print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__': main()
