"""Authored, unexecuted B02 single-stage bridge. Not an admission authority.

Requires a future independently admitted b02-native-stage spec (see validate_spec).
Never runs tests, scoring, arbitrary commands, or an automatic stage sequence.
Archive format is concatenated raw member bytes; index offsets reconstruct members.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

PART_BYTES = 256 * 1024 * 1024
PART_COUNT = 8
CHUNK = 1024 * 1024
ROLES = {'F': 'baseline', 'P': 'treatment', 'A': 'anchor_control'}
STAGES = {'prepare', 'calibrate-inference', 'freeze-profile', 'generate-train',
          'calibrate-training', 'train', 'generate-eval'}


class ContractError(ValueError):
    pass


class PackagingError(ContractError):
    pass


def safe_path(root, relative):
    root = Path(root).absolute()
    if any(x in ('', '.', '..') for x in str(relative).split('/')):
        raise ContractError('Noncanonical relative path')
    relative = Path(relative)
    if relative.is_absolute() or not relative.parts or any(x in ('..', '.') for x in relative.parts):
        raise ContractError('Expected confined relative path')
    result = root / relative
    for part in (root, *root.parents, result, *result.parents):
        if part.is_symlink():
            raise ContractError(f'Symlink forbidden: {part}')
    if not result.resolve().is_relative_to(root.resolve()):
        raise ContractError('Path escaped root')
    return result


def hash_file(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ContractError(f'Not an ordinary file: {path}')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(CHUNK), b''):
            digest.update(data)
    return digest.hexdigest()


def read_json(path):
    with Path(path).open(encoding='utf-8') as stream:
        return json.load(stream)


def checked_ref(root, ref):
    if set(ref) != {'path', 'sha256'} or not re.fullmatch('[a-f0-9]{64}', ref['sha256']):
        raise ContractError('Invalid file pin')
    path = safe_path(root, ref['path'])
    if hash_file(path) != ref['sha256']:
        raise ContractError(f'Changed file: {ref["path"]}')
    return path


def write_new(path, value):
    path = Path(path)
    safe_path(path.parent, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def file_record(path):
    return {'path': str(Path(path).absolute()), 'sha256': hash_file(path),
            'size': Path(path).stat().st_size}


def inventory(root):
    root = Path(root)
    if not root.exists():
        return []
    result = []
    for path in sorted(root.rglob('*')):
        safe_path(root, path.relative_to(root))
        if path.is_file():
            result.append(file_record(path))
    return result


def mirror_file(origin, root, relative, identity):
    """Exclusive streaming copy; reuse requires exact origin AND producer identity."""
    origin = Path(origin).absolute()
    safe_path(origin.parent, origin.name)
    before = file_record(origin)
    destination = safe_path(root, relative)
    sidecar = safe_path(root, str(relative) + '.provenance.json')
    expected = {'origin': before, 'identity': identity}
    if destination.exists() or sidecar.exists():
        if not destination.exists() or not sidecar.exists() or read_json(sidecar) != expected:
            raise PackagingError('Existing mirror has unrelated or incomplete provenance')
        if hash_file(destination) != before['sha256']:
            raise PackagingError('Existing mirror bytes conflict')
        if file_record(origin) != before:
            raise PackagingError('Origin changed during verification')
        return dict(expected, destination=str(destination), reused=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with origin.open('rb') as src, destination.open('xb') as dst:
        shutil.copyfileobj(src, dst, CHUNK)
        dst.flush()
        os.fsync(dst.fileno())
    if file_record(origin) != before or hash_file(destination) != before['sha256']:
        raise PackagingError('Origin changed during mirror; partial copy retained')
    write_new(sidecar, expected)
    return dict(expected, destination=str(destination), reused=False)


def archive_members(members, output_dir):
    """Stream fixed eight parts, including empty slots; preserve originals on overflow."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    entries = [file_record(p) for p in sorted(map(Path, members))]
    if len({e['path'] for e in entries}) != len(entries):
        raise PackagingError('Duplicate archive member')
    if sum(e['size'] for e in entries) > PART_COUNT * PART_BYTES:
        raise PackagingError('Auxiliary archive exceeds 8 x 256MiB; retain originals')
    streams = []
    offsets = [0] * PART_COUNT
    index = []
    try:
        for part in range(PART_COUNT):
            streams.append(safe_path(output_dir, f'archive-{part:02d}.bin').open('xb'))
        part = 0
        for entry in entries:
            spans = []
            with Path(entry['path']).open('rb') as src:
                position = 0
                while position < entry['size']:
                    if offsets[part] == PART_BYTES:
                        part += 1
                    data = src.read(min(CHUNK, PART_BYTES - offsets[part], entry['size'] - position))
                    if not data:
                        raise PackagingError('Archive source truncated')
                    spans.append({'part': part, 'offset': offsets[part], 'member_offset': position,
                                  'length': len(data)})
                    streams[part].write(data)
                    offsets[part] += len(data)
                    position += len(data)
            if file_record(entry['path']) != entry:
                raise PackagingError('Archive source changed')
            index.append(dict(entry, spans=spans))
    finally:
        for stream in streams:
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
    result = {'format': 'concatenated-raw-members-v1', 'members': index,
              'parts': [dict(file_record(output_dir / f'archive-{i:02d}.bin'), unused=offsets[i] == 0)
                        for i in range(PART_COUNT)]}
    write_new(output_dir / 'archive-index.json', result)
    return result


def stage_name(spec):
    stage, params = spec['stage'], spec['parameters']
    if stage == 'generate-eval':
        return f'{stage}-{params["arm"]}-{params["seed"]}'
    if stage == 'train':
        return f'{stage}-{params["arm"]}'
    if stage == 'calibrate-inference':
        return f'{stage}-{params["batch"]}'
    return stage


def required_predecessors(spec):
    """Exact immediate dependencies; inherited receipts retain their own seals."""
    stage, params = spec['stage'], spec['parameters']
    required = set() if stage == 'prepare' else {'prepare'}
    if stage == 'calibrate-inference':
        sizes = [64, 32, 16, 8, 4, 2, 1]
        pos = sizes.index(params['batch'])
        if pos:
            required.add(f'calibrate-inference-{sizes[pos - 1]}')
    elif stage == 'freeze-profile':
        required.add(f'calibrate-inference-{params["batch"]}')
    elif stage in ('generate-train', 'generate-eval', 'calibrate-training', 'train'):
        required.add('freeze-profile')
        if stage in ('calibrate-training', 'train'):
            required.add('generate-train')
        if stage == 'train':
            required.add('calibrate-training')
        if stage == 'generate-eval' and params['arm'] != 'F':
            required.add(f'train-{params["arm"]}')
    return required


def validate_numbers(spec):
    timeout = spec.get('timeout_seconds')
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ContractError('Timeout must be finite positive numeric value')
    for key in ('estimated_new_original_bytes', 'estimated_core_bytes', 'disk_margin_bytes'):
        if type(spec.get(key)) is not int or spec[key] < 0:
            raise ContractError('Byte estimates must be nonnegative integers')


def validate_predecessors(spec, refs):
    project, run = Path(spec['project_root']), Path(spec['run_root'])
    expected = required_predecessors(spec)
    supplied = {}
    for ref in spec['predecessor_refs']:
        path = checked_ref(project, ref)
        if path.name != 'receipt.json' or path.parent.parent != run / 'stages':
            raise ContractError('Predecessor receipt must be canonical same-run stage receipt')
        name = path.parent.name
        if name not in expected or name in supplied:
            raise ContractError('Unexpected/duplicate predecessor')
        supplied[name] = (path, ref)
    if set(supplied) != expected:
        raise ContractError('Missing mandatory stage prerequisites')
    if not expected:
        return
    run_identity = read_json(safe_path(run, 'identity.json'))
    for key in ('config_sha256', 'cd_evidence_ref', 'deployment_manifest_ref', 'goal_id', 'candidate_id'):
        value = spec['config_ref']['sha256'] if key == 'config_sha256' else spec[key]
        if run_identity.get(key) != value:
            raise ContractError('Run identity mismatch')
    protocol = {'path': str(refs['protocol_ref']), 'sha256': spec['protocol_ref']['sha256']}
    if run_identity.get('protocol_ref') != protocol:
        raise ContractError('Run protocol mismatch')
    if run_identity.get('deployment_code_refs') != read_json(refs['deployment_manifest_ref'])['files']:
        raise ContractError('Run deployment code mismatch')
    for name, (path, ref) in supplied.items():
        receipt = read_json(path)
        request = read_json(safe_path(path.parent, 'request.json'))
        if {k: v for k, v in request.items() if k != 'stage_parameters'} != dict(run_identity, stage=name):
            raise ContractError('Predecessor request does not belong to stable run')
        execution = receipt.get('execution_identity')
        if not isinstance(execution, dict) or set(execution) != {'task_id', 'run_id', 'attempt_id'}:
            raise ContractError('Predecessor execution identity missing')
        if any(not isinstance(v, str) or not re.fullmatch('[A-Za-z0-9_.-]+', v) for v in execution.values()):
            raise ContractError('Invalid predecessor execution identity')
        if request['stage_parameters'].get('execution_identity') != execution:
            raise ContractError('Predecessor task/attempt mismatch')
        if (receipt.get('stage') != name or receipt.get('protocol_ref') != protocol or
            receipt.get('config_ref') != {'path': str(refs['config_ref']), 'sha256': spec['config_ref']['sha256']} or
            any(receipt.get(key) != spec[key] for key in ('cd_evidence_ref', 'deployment_manifest_ref'))):
            raise ContractError('Predecessor receipt source/protocol mismatch')
        immediate_oom = (spec['stage'] == 'calibrate-inference' and name.startswith('calibrate-inference-') and
                         receipt.get('status') == 'failed' and receipt.get('error_class') == 'resource_oom')
        if receipt.get('status') != 'completed' and not immediate_oom:
            raise ContractError('Unsuccessful predecessor')
        actual = [{'path': str(Path(e['path']).relative_to(path.parent / 'outputs')),
                   'sha256': e['sha256'], 'bytes': e['size']} for e in inventory(path.parent / 'outputs')]
        if actual != receipt.get('partial_outputs' if immediate_oom else 'outputs'):
            raise ContractError('Predecessor complete inventory mismatch')
        if spec['stage'] == 'calibrate-inference' and name.startswith('calibrate-inference-') and not immediate_oom:
            if read_json(safe_path(path.parent, 'outputs/profile.json')).get('eligible') is not False:
                raise ContractError('Descending calibration requires explicit prior ineligibility')
        attempt = safe_path(run, f'wrapper-attempts/{execution["attempt_id"]}')
        seal_path = safe_path(attempt, 'sealed.json')
        seal_ref = {'path': str(seal_path.relative_to(project)), 'sha256': hash_file(seal_path)}
        if seal_ref not in spec['input_refs']:
            raise ContractError('Predecessor wrapper seal must be pinned in input_refs')
        sealed = read_json(checked_ref(project, seal_ref))
        summary_path = safe_path(attempt, 'seal/stage-summary.json')
        if sealed.get('summary') != file_record(summary_path):
            raise ContractError('Predecessor sealed summary mismatch')
        summary = read_json(summary_path)
        wrapper_request = read_json(safe_path(attempt, 'request.json'))
        if summary.get('identity') != wrapper_request or any(wrapper_request.get(k) != v for k, v in execution.items()):
            raise ContractError('Predecessor wrapper attempt mismatch')
        if (wrapper_request.get('stage') != name or
            any(wrapper_request.get(k) != v for k, v in stable_identity(spec).items()) or
            summary.get('driver_receipt') != receipt or summary.get('driver_receipt_ref') != ref or
            sealed.get('status') != ('failed' if immediate_oom else 'completed') or
            summary.get('status') != sealed.get('status')):
            raise ContractError('Predecessor unsealed or unrelated packaging')


def validate_spec(spec, project_root, stable_code_root, run_root, export_root,
                  task_id, run_id, attempt_id):
    """Check explicit specs; admission_ref is evidence, never a permission grant.

    Required external owner records: admission_ref has identity/stage/protocol_ref,
    status=admitted and native_stage_contract=1. resource_observation_ref has
    host, observed_at_unix, unknown_jobs=[], experiment_slot_available=true,
    min_free_disk_bytes and allocation details. They must be real reviewed inputs.
    """
    if spec.get('kind') != 'b02-native-stage' or type(spec.get('schema_version')) is not int or spec.get('schema_version') != 1:
        raise ContractError('Expected versioned b02-native-stage spec')
    for key, value in [('project_root', project_root), ('stable_code_root', stable_code_root),
                       ('run_root', run_root), ('export_root', export_root),
                       ('task_id', task_id), ('run_id', run_id), ('attempt_id', attempt_id)]:
        if spec.get(key) != str(value):
            raise ContractError(f'Invocation mismatch: {key}')
    for key in ('task_id', 'run_id', 'attempt_id'):
        if not re.fullmatch('[A-Za-z0-9_.-]+', spec[key]):
            raise ContractError('Unsafe identity')
    project = Path(project_root).absolute()
    for key in ('stable_code_root', 'run_root', 'export_root'):
        path = Path(spec[key]).absolute()
        if not path.is_relative_to(project):
            raise ContractError('Stable roots must be in project')
        safe_path(project, path.relative_to(project))
    roots = [Path(spec[k]) for k in ('stable_code_root', 'run_root', 'export_root')]
    if any(a.is_relative_to(b) or b.is_relative_to(a) for i, a in enumerate(roots) for b in roots[i+1:]):
        raise ContractError('Stable code/run/export roots must be disjoint')
    stage = spec['stage']
    if stage not in STAGES:
        raise ContractError('No shell/tests/scoring/sequence stage supported')
    params = spec['parameters']
    allowed = {'batch'} if stage in ('calibrate-inference', 'freeze-profile') else (
        {'arm', 'seed'} if stage == 'generate-eval' else {'arm'} if stage == 'train' else set())
    if set(params) != allowed:
        raise ContractError('Exact enumerated stage parameters required')
    if 'batch' in params and (type(params['batch']) is not int or params['batch'] not in (64, 32, 16, 8, 4, 2, 1)):
        raise ContractError('Unsupported batch')
    if 'arm' in params and params['arm'] not in (('P', 'A') if stage == 'train' else ROLES):
        raise ContractError('Wrong arm')
    if 'seed' in params and (type(params['seed']) is not int or params['seed'] not in (43, 45)):
        raise ContractError('Wrong seed')
    validate_numbers(spec)
    expected_role = ROLES[params['arm']] if stage == 'generate-eval' else None
    if spec.get('arm_role') != expected_role or spec.get('group') != ('mbpp_full_test500' if expected_role else None):
        raise ContractError('Wrong role/group; preparation cannot masquerade as an arm')
    refs = {key: checked_ref(project, spec[key]) for key in (
        'config_ref', 'protocol_ref', 'cd_evidence_ref', 'deployment_manifest_ref',
        'admission_ref', 'resource_observation_ref')}
    for ref in spec['input_refs'] + spec['predecessor_refs']:
        checked_ref(project, ref)
    cfg, protocol, experiment = (read_json(refs[k]) for k in ('config_ref', 'protocol_ref', 'cd_evidence_ref'))
    if type(experiment.get('schema_version')) is not int or (experiment.get('kind'), experiment.get('schema_version'), experiment.get('flow_profile'),
        experiment.get('stage'), experiment.get('goal_id'), experiment.get('candidate_id')) != (
        'research-cd-experiment', 1, 'work-harness-cd-v1', 'diagnosis', spec['goal_id'], spec['candidate_id']):
        raise ContractError('Wrong experiment pin (design is not experiment)')
    if protocol.get('evidence_mode') != 'developmental' or protocol.get('cd_development') != {
        'flow_profile': 'work-harness-cd-v1', 'stage': 'diagnosis', 'cd_evidence_ref': spec['cd_evidence_ref']}:
        raise ContractError('Protocol/experiment mismatch')
    if cfg['backend'] != 'none' or cfg['generated_code_execution_enabled'] is not False:
        raise ContractError('Scoring/code execution forbidden')
    if spec['interpreter'] != cfg['interpreter']:
        raise ContractError('Wrong project venv')
    manifest = read_json(refs['deployment_manifest_ref'])
    if manifest.get('kind') != 'b02-stable-deployment' or type(manifest.get('schema_version')) is not int or manifest.get('schema_version') != 1:
        raise ContractError('Wrong deployment manifest')
    deployed = {str(checked_ref(project, ref)) for ref in manifest['files']}
    stable = Path(stable_code_root)
    required = {str(p) for p in stable.rglob('*.py')} | {str(refs['config_ref'])}
    if not required <= deployed or str(stable / 'diagnostic_driver.py') not in deployed or str(stable / 'native_wrapper.py') not in deployed:
        raise ContractError('Incomplete stable deployment')
    for name, digest in cfg['source_hashes'].items():
        if hash_file(safe_path(cfg['source_root'], name)) != digest:
            raise ContractError('Upstream deployment changed')
    upstream = manifest.get('upstream_files', [])
    upstream_paths = {str(checked_ref(cfg['source_root'], ref)) for ref in upstream}
    package = Path(cfg['source_root']) / 'src/improving'
    if not package.is_dir() or not {str(p) for p in package.rglob('*.py')} <= upstream_paths:
        raise ContractError('Complete actual upstream Python package pins required, including __init__.py')
    admission = read_json(refs['admission_ref'])
    for key in ('task_id', 'run_id', 'attempt_id', 'stage', 'protocol_ref'):
        if admission.get(key) != spec[key]:
            raise ContractError('Admission identity mismatch')
    if admission.get('status') != 'admitted' or admission.get('native_stage_contract') != 1:
        raise ContractError('Owner stage admission missing; no fallback route')
    observation = read_json(refs['resource_observation_ref'])
    observed = observation.get('observed_at_unix')
    if type(observed) not in (int, float) or not math.isfinite(observed):
        raise ContractError('Resource timestamp must be finite numeric value')
    if (observation.get('host') != socket.gethostname() or observation.get('unknown_jobs') != [] or
        observation.get('experiment_slot_available') is not True or
        not 0 <= time.time() - observation['observed_at_unix'] <= 300):
        raise ContractError('Current job/resource reconciliation required')
    if spec['timeout_seconds'] <= 0 or spec['timeout_seconds'] > (300 if stage == 'calibrate-inference' else cfg['stage_watchdogs'][stage]) + 60:
        raise ContractError('Invalid bounded timeout')
    validate_predecessors(spec, refs)
    # Exact names are derived, not user-selected arbitrary file origins.
    expected = declared_outputs(spec)
    if sorted(spec['output_paths']) != sorted(expected):
        raise ContractError('Incomplete or extraneous declared outputs')
    return refs, cfg


def export_relative(spec):
    return str(Path(spec['export_root']).relative_to(spec['project_root']) / stage_name(spec) / spec['attempt_id'])


def declared_outputs(spec):
    names = ['stage-summary.json', 'inventory.json', 'origin-map.json', 'stdout.log', 'stderr.log',
             'checkpoint-inventory.json', 'archive-index.json']
    names += [f'archive-{i:02d}.bin' for i in range(PART_COUNT)]
    if spec['stage'] == 'generate-eval':
        names += ['predictions.jsonl', 'identity.json', 'prompts.json', 'generation-manifest.json',
                  'generation-budget.json', 'driver-receipt.json', 'driver-request.json']
    base = export_relative(spec)
    # provenance companions are transport evidence and are also explicitly declared.
    return [f'{base}/{name}' for name in names] + [f'{base}/{name}.provenance.json' for name in names]


def build_argv(spec, refs):
    argv = [spec['interpreter'], str(Path(spec['stable_code_root']) / 'diagnostic_driver.py'), spec['stage']]
    for key, value in sorted(spec['parameters'].items()):
        argv += ['--' + key, str(value)]
    for field, flag in [('config_ref', 'config'), ('protocol_ref', 'protocol'),
                        ('cd_evidence_ref', 'cd-evidence'), ('deployment_manifest_ref', 'deployment-manifest')]:
        value = spec[field]['path'] if field in ('cd_evidence_ref', 'deployment_manifest_ref') else str(refs[field])
        argv += ['--' + flag, value, '--' + flag + '-sha256', spec[field]['sha256']]
    argv += ['--project-root', spec['project_root'], '--run-root', spec['run_root'],
             '--goal-id', spec['goal_id'], '--candidate-id', spec['candidate_id'],
             '--task-id', spec['task_id'], '--run-id', spec['run_id'], '--attempt-id', spec['attempt_id']]
    return argv


def verify_driver(spec, refs, child_pid, started):
    folder = Path(spec['run_root']) / 'stages' / stage_name(spec)
    request, receipt = read_json(folder / 'request.json'), read_json(folder / 'receipt.json')
    if receipt.get('stage') != stage_name(spec) or receipt.get('pid') != child_pid or receipt.get('started_at_unix', 0) < started:
        raise ContractError('Unrelated driver attempt')
    execution_identity = {key: spec[key] for key in ('task_id', 'run_id', 'attempt_id')}
    if receipt.get('execution_identity') != execution_identity:
        raise ContractError('Wrong execution task/run/attempt')
    if request.get('stage') != stage_name(spec) or request.get('stage_parameters') != {
        'batch': spec['parameters'].get('batch'), 'arm': spec['parameters'].get('arm'),
        'seed': spec['parameters'].get('seed'), 'execution_identity': execution_identity}:
        raise ContractError('Driver request parameters mismatch')
    expected_protocol = {'path': str(refs['protocol_ref']), 'sha256': spec['protocol_ref']['sha256']}
    if receipt.get('protocol_ref') != expected_protocol or request.get('cd_evidence_ref') != spec['cd_evidence_ref']:
        raise ContractError('Driver receipt protocol/experiment mismatch')
    if receipt.get('config_ref') != {'path': str(refs['config_ref']), 'sha256': spec['config_ref']['sha256']}:
        raise ContractError('Driver config mismatch')
    for key in ('cd_evidence_ref', 'deployment_manifest_ref'):
        if request.get(key) != spec[key] or receipt.get(key) != spec[key]:
            raise ContractError('Driver CD/deployment mismatch')
    deployment = read_json(refs['deployment_manifest_ref'])
    expected_deployment = deployment['files']
    for ref in expected_deployment:
        checked_ref(spec['project_root'], ref)
    if request.get('deployment_code_refs') != expected_deployment:
        raise ContractError('Driver deployed source identity mismatch')
    declared = receipt.get('outputs' if receipt.get('status') == 'completed' else 'partial_outputs', [])
    actual = [{'path': str(Path(e['path']).relative_to(folder / 'outputs')),
               'sha256': e['sha256'], 'bytes': e['size']} for e in inventory(folder / 'outputs')]
    if actual != declared:
        raise ContractError('Driver output inventory mismatch')
    if spec['stage'] == 'generate-eval' and receipt.get('status') == 'completed':
        identity = read_json(folder / 'outputs/identity.json')
        if (identity['arm'], identity['seed'], identity['stage'], identity['protocol_ref']) != (
            spec['parameters']['arm'], spec['parameters']['seed'], 'evaluation', expected_protocol):
            raise ContractError('Wrong prediction origin/role/seed/protocol')
        raw = folder / 'outputs/predictions.jsonl'
        if identity['raw_ref'] != {'path': str(raw.resolve()), 'sha256': hash_file(raw)}:
            raise ContractError('Raw origin mismatch even if same bytes')
        with raw.open('rb') as stream:
            if sum(1 for _ in stream) != 8000:
                raise ContractError('Incomplete 500 x 16 prediction denominator')
    return receipt


def stable_identity(spec):
    """Workspace and stage attempt are deliberately absent; deployment path is not."""
    return {key: spec[key] for key in ('project_root', 'stable_code_root', 'run_root',
        'config_ref', 'protocol_ref', 'cd_evidence_ref', 'deployment_manifest_ref', 'goal_id', 'candidate_id')}


def run_stage(spec, spec_ref, workspace_root, actual_identity):
    """One driver invocation only. Failed/unsealed attempts cannot be retried here."""
    project = Path(spec['project_root'])
    refs, cfg = validate_spec(spec, spec['project_root'], spec['stable_code_root'], spec['run_root'],
                              spec['export_root'], *actual_identity)
    workspace = Path(workspace_root).absolute()
    if (workspace == project or project.is_relative_to(workspace) or
        any(workspace.is_relative_to(Path(spec[k])) or Path(spec[k]).is_relative_to(workspace)
            for k in ('stable_code_root', 'run_root', 'export_root'))):
        raise ContractError('Workspace must be separate from project/run tree')
    safe_path(workspace, 'workspace-check')
    if (sys.platform != 'linux' or Path(sys.executable).absolute() != Path(spec['interpreter']).absolute()
        or Path(sys.prefix).absolute() != Path(spec['interpreter']).parent.parent.absolute()):
        raise ContractError('Use hn01 project venv')
    run = Path(spec['run_root'])
    run.mkdir(parents=True, exist_ok=True)
    # Covers originals, archive, both mirrors and provenance; measured disk is not reservation.
    required_disk = spec['estimated_new_original_bytes'] + 3 * (PART_COUNT * PART_BYTES + spec['estimated_core_bytes']) + spec['disk_margin_bytes']
    if required_disk < 16 * 1024**3:
        required_disk = 16 * 1024**3
    for root in (run, workspace):
        root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(root).free < required_disk:
            raise ContractError('Insufficient disk including original/archive/mirror copies')
    with safe_path(run, '.wrapper-serial.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stable_binding = stable_identity(spec)
        ident_path = run / 'wrapper-identity.json'
        if ident_path.exists():
            if read_json(ident_path) != stable_binding:
                raise ContractError('Stable run identity changed')
        else:
            write_new(ident_path, stable_binding)
        attempt = safe_path(run, f'wrapper-attempts/{spec["attempt_id"]}')
        stage_folder = run / 'stages' / stage_name(spec)
        if attempt.exists() or stage_folder.exists():
            raise ContractError('Existing/unknown stage: reconcile original; automatic retry forbidden')
        attempt.mkdir(parents=True)
        identity = dict(stable_binding, task_id=spec['task_id'], run_id=spec['run_id'],
                        attempt_id=spec['attempt_id'], stage=stage_name(spec), arm_role=spec.get('arm_role'),
                        group=spec.get('group'), seed=spec['parameters'].get('seed'), spec_ref=spec_ref)
        write_new(attempt / 'request.json', identity)
        argv = build_argv(spec, refs)
        started = time.time()
        write_new(attempt / 'unsealed.json', {'identity': identity, 'started_at_unix': started,
                    'host': socket.gethostname(), 'pid': os.getpid()})
        child = None
        exit_code = None
        failure = None
        driver_receipt = None
        env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'LC_ALL', 'HOME', 'CUDA_VISIBLE_DEVICES')}
        env.update(PYTHONPATH=cfg['source_root'] + '/src:' + spec['stable_code_root'],
                   HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1')
        with (attempt / 'stdout.log').open('xb') as stdout, (attempt / 'stderr.log').open('xb') as stderr:
            try:
                child = subprocess.Popen(argv, cwd=project, env=env, stdout=stdout, stderr=stderr,
                                         start_new_session=True)
                write_new(attempt / 'child.json', {'pid': child.pid, 'host': socket.gethostname(),
                          'observed_at_unix': time.time(), 'argv': argv})
                try:
                    exit_code = child.wait(timeout=spec['timeout_seconds'])
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        exit_code = child.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        exit_code = child.wait(timeout=15)
                    failure = 'timeout; no automatic retry'
                driver_receipt = verify_driver(spec, refs, child.pid, started)
                checked_ref(project, spec['deployment_manifest_ref'])
                deployment = read_json(refs['deployment_manifest_ref'])
                for ref in deployment['files']:
                    checked_ref(project, ref)
                for ref in deployment['upstream_files']:
                    checked_ref(cfg['source_root'], ref)
                if exit_code != 0 or driver_receipt.get('status') != 'completed':
                    failure = failure or 'driver failed'
            except BaseException as exc:
                failure = f'{type(exc).__name__}: {exc}'
                if child is not None and child.poll() is None:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        exit_code = child.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        exit_code = child.wait(timeout=15)
        # An actual kill cannot reach this path; unsealed marker remains authoritative.
        collected = inventory(stage_folder)
        checkpoints = [e for e in collected if any('checkpoint' in part or part == 'probe' or
                         (part.startswith('.') and '.saving-' in part)
                         for part in Path(e['path']).parts)]
        checkpoint_paths = {e['path'] for e in checkpoints}
        seal = attempt / 'seal'
        seal.mkdir()
        write_new(seal / 'checkpoint-inventory.json', {'downloaded': False, 'files': checkpoints})
        write_new(seal / 'inventory.json', {'files': collected, 'partial': failure is not None})
        shutil.copyfile(attempt / 'stdout.log', seal / 'stdout.log')
        shutil.copyfile(attempt / 'stderr.log', seal / 'stderr.log')
        code = 3 if failure else 0
        try:
            members = [Path(e['path']) for e in collected if e['path'] not in checkpoint_paths]
            members += [attempt / 'request.json', attempt / 'unsealed.json', attempt / 'stdout.log', attempt / 'stderr.log']
            members += [p for p in (run / 'identity.json', run / 'config.json', run / 'wrapper-identity.json') if p.is_file()]
            members += [checked_ref(project, ref) for ref in spec['predecessor_refs']]
            members = list(dict.fromkeys(members))
            if (attempt / 'child.json').exists():
                members.append(attempt / 'child.json')
            archive_members(members, seal)
            sources = {p.name: p for p in seal.iterdir() if p.is_file()}
            if spec['stage'] == 'generate-eval':
                mappings = {'predictions.jsonl':'outputs/predictions.jsonl', 'identity.json':'outputs/identity.json',
                    'prompts.json':'outputs/prompts.json', 'generation-manifest.json':'outputs/predictions.jsonl.parts/manifest.json',
                    'generation-budget.json':'outputs/predictions.jsonl.budget.json', 'driver-receipt.json':'receipt.json',
                    'driver-request.json':'request.json'}
                for name, relative in mappings.items():
                    src = safe_path(stage_folder, relative)
                    if src.is_file():
                        sources[name] = src
                    elif not failure:
                        raise PackagingError('Missing independently declared core output')
            total = sum(p.stat().st_size for p in sources.values())
            if total > 4 * 1024**3:
                raise PackagingError('Collection exceeds 4GiB; originals retained')
            maps = []
            base = export_relative(spec)
            for name, source in sorted(sources.items()):
                for root in (project, workspace):
                    maps.append(mirror_file(source, root, f'{base}/{name}', identity))
            write_new(seal / 'origin-map.json', {'identity': identity, 'mappings': maps,
                        'note': 'Original absolute receipts unchanged; no scorer receipt fabricated'})
            summary = {'identity': identity, 'status': 'failed' if failure else 'completed',
                       'scoring_status': 'pending', 'science_accepted': False, 'driver_receipt': driver_receipt,
                       'driver_receipt_ref': ({'path': str((stage_folder / 'receipt.json').relative_to(project)),
                                               'sha256': hash_file(stage_folder / 'receipt.json')}
                                              if driver_receipt is not None else None),
                       'argv': argv, 'cwd': str(project), 'started_at_unix': started, 'ended_at_unix': time.time(),
                       'exit_code': exit_code, 'failure': failure, 'host': socket.gethostname(),
                       'pid': os.getpid(), 'child_pid': child.pid if child else None,
                       'input_refs': spec['input_refs'], 'resource_observation_ref': spec['resource_observation_ref'],
                       'disk_estimate_bytes': required_disk, 'checkpoint_downloaded': False}
            write_new(seal / 'stage-summary.json', summary)
            for name in ('origin-map.json', 'stage-summary.json'):
                for root in (project, workspace):
                    mirror_file(seal / name, root, f'{base}/{name}', identity)
            if not failure:
                for root in (project, workspace):
                    for relative in spec['output_paths']:
                        if not safe_path(root, relative).is_file():
                            raise PackagingError('Declared output missing')
            for root in (project, workspace):
                transport_bytes = sum(safe_path(root, rel).stat().st_size for rel in spec['output_paths']
                                      if safe_path(root, rel).is_file())
                if transport_bytes > 4 * 1024**3:
                    raise PackagingError('Full declared collection exceeds 4GiB, including metadata')
            write_new(attempt / 'sealed.json', {'status': summary['status'], 'summary': file_record(seal / 'stage-summary.json')})
        except Exception as exc:
            code = 4
            write_new(attempt / 'packaging-failure.json', {'error': str(exc), 'originals_retained': True,
                       'scoring_status': 'pending', 'driver_exit_code': exit_code, 'driver_failure': failure})
        return {'exit_code': code, 'attempt_path': str(attempt), 'scoring_status': 'pending',
                'status': 'completed' if code == 0 else 'failed_or_unsealed', 'science_accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('stage-spec', 'stage-spec-sha256', 'project-root', 'workspace-root', 'stable-code-root',
                 'run-root', 'export-root', 'stage', 'task-id', 'run-id', 'attempt-id'):
        parser.add_argument('--' + flag, required=True)
    args = parser.parse_args()
    try:
        ref = {'path': args.stage_spec, 'sha256': args.stage_spec_sha256}
        spec = read_json(checked_ref(args.project_root, ref))
        if spec['stage'] != args.stage:
            raise ContractError('Requested stage mismatch')
        validate_spec(spec, args.project_root, args.stable_code_root, args.run_root, args.export_root,
                      args.task_id, args.run_id, args.attempt_id)
        result = run_stage(spec, ref, args.workspace_root, (args.task_id, args.run_id, args.attempt_id))
    except Exception as exc:
        result = {'exit_code': 2, 'status': 'contract_rejected', 'error': str(exc), 'science_accepted': False}
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(result['exit_code'])


if __name__ == '__main__':
    main()
