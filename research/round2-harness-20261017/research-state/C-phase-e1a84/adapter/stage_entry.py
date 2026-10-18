"""Explicit .7 entry, executed only by a reviewed native development_stage job.

This is an integrity check inside the trusted controller route, not an OS sandbox
or independent admission authority. No scoring, retry, or publication to project.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import native_wrapper as W

ROOT = Path('/root/rivermind-data/spectrum-harness/project')
SKILL = Path('/root/rivermind-data/spectrum-harness/skill')
SKILL_DIGEST = '304f296d806577b4c59c87d53e02d6d24f5f6614f6dcf761db7e3449fe52c84a'
CODE = 'research-state/C-phase-e1a84/adapter'
RUN = 'research-state/C-phase-e1a84/driver-run'
MAP = {'prepare': 'prepare', 'calibrate-inference': 'calibrate',
       'freeze-profile': 'prepare', 'generate-train': 'prepare',
       'calibrate-training': 'calibrate', 'train': 'train', 'generate-eval': 'export'}
BASE = ['stage-summary.json', 'inventory.json', 'origin-map.json', 'stdout.log',
        'stderr.log', 'checkpoint-inventory.json', 'archive-index.json',
        'resource-observation.json', 'driver-receipt.json', 'driver-request.json']
PREPARE = ['train.jsonl', 'calibration.jsonl', 'validation.jsonl', 'eval.jsonl', 'source_fields.jsonl',
           'preparation_manifest.jsonl', 'task-manifest.json', 'base-assets.json']
EXPORT = {'predictions.jsonl': 'predictions.jsonl', 'identity.json': 'identity.json',
          'prompts.json': 'prompts.json', 'generation-manifest.json': 'predictions.jsonl.parts/manifest.json',
          'generation-budget.json': 'predictions.jsonl.budget.json'}


def need(value, reason):
    if not value:
        raise W.ContractError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def outputs(run_id, stage):
    need(re.fullmatch(r'[A-Za-z0-9_.-]+', run_id), 'Invalid native run ID')
    names = BASE + [f'archive-{i:02d}.bin' for i in range(W.PART_COUNT)]
    names += PREPARE if stage == 'prepare' else list(EXPORT) if stage == 'generate-eval' else []
    return ['runs/stage-outputs/' + run_id + '/' + n for n in names]


def runtime():
    """Verify whole adopted Skill; import captured source, never cached bytecode."""
    excluded = {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
                '.venv', 'venv', '.runtime', 'runtime-state', 'node_modules'}
    files, sources = [], {}
    def error(exc):
        raise exc
    for directory, dirs, names in os.walk(SKILL, onerror=error):
        dirs[:] = sorted(n for n in dirs if n not in excluded)
        need(not any((Path(directory)/n).is_symlink() for n in dirs), 'Runtime symlink')
        for name in sorted(names):
            if name.endswith(('.pyc', '.pyo', '.db', '.sqlite', '.sqlite3', '-wal', '-shm')):
                continue
            p = Path(directory)/name
            need(not p.is_symlink() and p.is_file(), 'Runtime file required')
            relative = p.relative_to(SKILL).as_posix()
            data = p.read_bytes()
            files.append({'path': relative, 'sha256': hashlib.sha256(data).hexdigest()})
            if relative.startswith('scripts/') and relative.endswith('.py'):
                sources[relative] = data
    need(digest(files) == SKILL_DIGEST, 'Adopted runtime changed')
    class Loader(importlib.abc.Loader):
        def __init__(self, relative): self.relative = relative
        def create_module(self, spec): return None
        def exec_module(self, module):
            module.__file__ = str(SKILL/self.relative)
            exec(compile(sources[self.relative], module.__file__, 'exec'), module.__dict__)
    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            relative = 'scripts/' + fullname.replace('.', '/') + '.py'
            if relative in sources:
                return importlib.util.spec_from_loader(fullname, Loader(relative))
    need(not any(n in sys.modules for n in ('native_stages', '_autoresearch', 'run_experiments', 'host_resources')),
         'Runtime must not have been imported before verification')
    sys.meta_path.insert(0, Finder())
    import native_stages, run_experiments, host_resources
    return native_stages, run_experiments, host_resources


def context_identity(c, path, environ):
    fields = {'kind', 'schema_version', 'controller', 'run_id', 'attempt_id', 'trial_id',
              'stage_id', 'stage_kind', 'native_stage_ref', 'protocol_ref', 'plan_digest',
              'project_root', 'workspace_root', 'scientific_verified',
              'dispatch_identity_sha256', 'harness_context_ref'}
    need(set(c) == fields and c['kind'] == 'research-native-stage-context'
         and type(c['schema_version']) is int and c['schema_version'] == 1
         and c['scientific_verified'] is False, 'Wrong runtime context schema')
    controller = c['controller']
    need(set(controller) == {'task_id', 'run_id', 'owner', 'fence'}
         and type(controller['fence']) is int and controller['fence'] > 0, 'Controller identity absent')
    need(isinstance(controller['owner'], str) and controller['owner'], 'Owner required')
    for value in [controller[k] for k in ('task_id', 'run_id')] + [c[k] for k in ('run_id', 'trial_id', 'attempt_id', 'stage_id')]:
        need(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.-]+', value), 'Unsafe identity')
    need(json.loads(environ.get('RESEARCH_NATIVE_CONTROLLER_CONTEXT', 'null')) == controller,
         'Controller environment mismatch')
    need(isinstance(c['dispatch_identity_sha256'], str)
         and re.fullmatch('[a-f0-9]{64}', c['dispatch_identity_sha256'])
         and environ.get('RESEARCH_NATIVE_DISPATCH_SHA256') == c['dispatch_identity_sha256'],
         'Dispatch identity mismatch')
    root, workspace = Path(c['project_root']), Path(c['workspace_root'])
    need(root == ROOT and workspace == path.parent/'workspace' and path.name == 'native-stage-context.json'
         and path.parent.name == c['attempt_id'], 'Context location mismatch')
    W.safe_path(root, path.relative_to(root))
    return root, workspace


def stage_parameters(args, descriptor):
    stage = args.driver_stage
    need(stage in MAP and descriptor['stage_kind'] == MAP[stage], 'Stage mapping mismatch')
    params = {k: getattr(args, k) for k in ('batch', 'arm', 'seed') if getattr(args, k) is not None}
    expected = {'batch'} if stage in ('calibrate-inference', 'freeze-profile') else (
        {'arm', 'seed'} if stage == 'generate-eval' else {'arm'} if stage == 'train' else set())
    need(set(params) == expected, 'Exact stage parameters required')
    if 'batch' in params: need(params['batch'] in (64,32,16,8,4,2,1), 'Batch not supported')
    if 'arm' in params: need(params['arm'] in (('P','A') if stage == 'train' else W.ROLES), 'Wrong arm')
    if 'seed' in params: need(params['seed'] in (43,45), 'Wrong evaluation seed')
    j = descriptor['job']
    need((j['arm_role'], j['group'], j['seed']) ==
         ((W.ROLES[params['arm']], 'mbpp_full_test500', params['seed']) if stage == 'generate-eval'
          else ('prerequisite', 'prerequisite', 44 if stage in ('train','calibrate-training') else 43 if stage == 'generate-train' else 0)),
         'Stage role/group/seed mismatch')
    return params


def bind_context_plan(c, plan, s):
    job = s['job']
    for key, value in {'run_id':plan['run_id'], 'trial_id':job['trial_id'], 'stage_id':s['stage_id'],
                       'stage_kind':s['stage_kind'], 'native_stage_ref':plan['provenance']['native_stage_ref'],
                       'protocol_ref':plan['protocol_ref'], 'plan_digest':plan['plan_digest']}.items():
        need(c[key] == value, 'Context/plan mismatch: '+key)


def validate(args):
    path = Path(args.native_stage_context).absolute()
    c = W.read_json(path)
    root, workspace = context_identity(c, path, os.environ)
    N, R, H = runtime()
    # This is the runner's retained native plan, not a worker-created spec.
    plan = W.read_json(path.parent.parent/'plan.json')
    R.validate_plan(root, plan)
    s, program, _ = N.validate_plan(root, plan)
    job = s['job']
    bind_context_plan(c, plan, s)
    need(path.parent.parent == W.safe_path(root, plan['output_root'])/plan['run_id'], 'Attempt root mismatch')
    hpath = W.checked_ref(root, c['harness_context_ref'])
    need(os.environ.get('RESEARCH_NATIVE_HARNESS_CONTEXT') == str(hpath), 'Harness environment mismatch')
    h = W.read_json(hpath)
    need(h['native_plan_digest'] == c['plan_digest'] and h['gate_advanced'] is False
         and h['CUDA_VISIBLE_DEVICES'] == os.environ.get('CUDA_VISIBLE_DEVICES'), 'Harness identity mismatch')
    # Bind the actual task, retained batch plan and resource declaration as well.
    hp = W.read_json(hpath.parent.parent.parent/'plan.json')
    need(digest({k:v for k,v in hp.items() if k != 'plan_digest'}) == hp['plan_digest'] == h['batch_plan_digest'],
         'Harness plan digest mismatch')
    ht = next(t for t in hp['tasks'] if t['task_id'] == h['task_id'])
    need(W.read_json(W.checked_ref(root, ht['plan_ref'])) == plan and ht['resources'] == h['declared_resources'],
         'Harness task/resources mismatch')
    need(h['declared_resources']['allow_gpu_share'] is False, 'GPU sharing forbidden')
    binding_ref = {'path':args.binding_ref, 'sha256':args.binding_sha256}
    need(binding_ref in job['input_refs'], 'Binding is not reviewed job input')
    binding = W.read_json(W.checked_ref(root, binding_ref))
    need(binding['kind'] == 'b02-stage-plan-inputs' and binding['schema_version'] == 1, 'Wrong adapter binding')
    params = stage_parameters(args, s)
    need(program['required_groups'] == ['mbpp_full_test500'] and program['seed_policy']['seeds'] == [43,45],
         'Full F/P/A evaluation inventory required')
    contract = N.groups(program)['mbpp_full_test500']
    need(set(contract['arm_requirements']) == set(W.ROLES.values()), 'F/P/A arm omitted')
    for key, required in binding['initial_execution_bindings'].items():
        need(all(r in s['execution_bindings'][key] for r in required), 'Model/data/selection lineage omitted: '+key)
    need(s['dependency_analysis_ref'] == binding['dependency_analysis_ref'], 'Dependency analysis not bound')
    need(sorted(job['output_paths']) == sorted(outputs(c['run_id'], args.driver_stage)), 'Output namespace/inventory mismatch')
    need(len(job['output_paths']) == len(set(job['output_paths'])), 'Duplicate outputs')
    # Check staged copies separately from stable deployment; argv must be reviewed.
    replacements = {}
    for ref in job['input_refs'] + job['code_refs']:
        src = W.checked_ref(root, ref); dst = W.checked_ref(workspace, ref)
        replacements[str(src)] = str(dst)
    command = []
    for arg in job['command']:
        for src, dst in sorted(replacements.items(), key=lambda kv:-len(kv[0])):
            arg = arg.replace(src, dst)
        command.append(arg.replace('{NATIVE_STAGE_CONTEXT}', str(path)))
    need(command == [str(Path(sys.executable).absolute()), str(Path(__file__).absolute())] + sys.argv[1:],
         'Executed argv differs from reviewed job')
    need(Path(__file__).absolute() == workspace/CODE/'stage_entry.py', 'Must execute staged adapter copy')
    manifest_ref, config_ref = binding['deployment_manifest_ref'], binding['config_ref']
    need(manifest_ref in job['input_refs'] and config_ref in job['input_refs'], 'Deployment/config not bound')
    manifest = W.read_json(W.checked_ref(root, manifest_ref))
    cfg = W.read_json(W.checked_ref(root, config_ref))
    need(cfg['backend'] == 'none' and cfg['generated_code_execution_enabled'] is False, 'Scoring forbidden')
    need(Path(sys.executable).absolute() == Path(cfg['interpreter']).absolute()
         and Path(sys.prefix).absolute() == Path(cfg['interpreter']).parent.parent, 'Wrong venv')
    expected_files = {str(p.relative_to(root)) for p in (root/CODE).rglob('*.py')} | {config_ref['path']}
    need({r['path'] for r in manifest['files']} == expected_files, 'Incomplete or extraneous deployment')
    for ref in manifest['files']:
        need(ref in job['input_refs'] + job['code_refs'], 'Deployment member missing from job')
        W.checked_ref(root, ref); W.checked_ref(workspace, ref)
    need(all(r in job['code_refs'] for r in manifest['files'] if r['path'].endswith('.py')), 'Code pins missing')
    method_refs = [r for r in manifest['files'] if r['path'].endswith('.py') and '/test_' not in r['path']]
    for arm in contract['arm_requirements'].values():
        need(all(r in arm['implementation_refs'] for r in method_refs), 'Program uses obsolete implementation')
    evidence = W.read_json(W.checked_ref(root, s['cd_evidence_ref']))
    mapped = [b['code_ref'] for b in evidence['code_bindings']]
    need(all(r in mapped for r in method_refs if Path(r['path']).name in ('diagnostic_driver.py','stage_entry.py','training_instrumented.py','analysis.py')),
         'CD experiment must be rebound to actual adapted code')
    for ref in manifest['upstream_files']: W.checked_ref(cfg['source_root'], ref)
    upstream = {str(p.relative_to(cfg['source_root'])) for p in (Path(cfg['source_root'])/'src/improving').rglob('*.py')}
    need(upstream <= {r['path'] for r in manifest['upstream_files']}, 'Unpinned upstream package')
    for ref in [cfg['train_source_ref'], cfg['test_source_ref'], cfg['design_ref']] + cfg['source_refs']:
        need(ref in job['input_refs'], 'Config dependency not bound'); W.checked_ref(root, ref)
    need(binding['stable_run_relative'] == RUN and binding['stable_code_relative'] == CODE, 'Wrong stable roots')
    spec = dict(project_root=str(root), stable_code_root=str(root/CODE), run_root=str(root/RUN),
                config_ref=config_ref, protocol_ref=c['protocol_ref'], cd_evidence_ref=s['cd_evidence_ref'],
                deployment_manifest_ref=manifest_ref, goal_id=program['goal_id'], candidate_id=program['candidate_id'],
                stage=args.driver_stage, parameters=params, interpreter=cfg['interpreter'],
                task_id=c['controller']['task_id'], run_id=c['run_id'], attempt_id=c['attempt_id'])
    need(set(s['required_predecessor_ids']) == W.required_predecessors(spec), 'Immediate driver dependencies mismatch')
    need(s['stage_id'] == W.stage_name(spec), 'Driver stage ID mismatch')
    # Controller authenticates these registered receipts before dispatch. Recheck
    # archive linkage with canonical N.validate_plan and driver lineage here.
    check_predecessors(root, spec, s)
    refs = {key:W.checked_ref(root, spec[key]) for key in
            ('config_ref','protocol_ref','cd_evidence_ref','deployment_manifest_ref')}
    return c, s, program, plan, h, binding, cfg, spec, refs, H


def check_predecessors(root, spec, descriptor):
    summaries = {}
    for rr in descriptor['predecessor_receipt_refs']:
        receipt = W.read_json(W.checked_ref(root, rr))
        ctl = receipt['controller']
        need(ctl['state'] == 'completed' and ctl['task']['action'] == 'native_harness', 'Failed predecessor unsupported')
        for ref in ctl['outputs']:
            if ref['path'].endswith('/stage-summary.json'):
                summary = W.read_json(W.checked_ref(root, ref))
                need(summary['status'] == 'completed' and summary['scoring_status'] == 'pending', 'Invalid predecessor summary')
                need(summary['context']['controller']['task_id'] == ctl['task']['task_id'], 'Predecessor task mismatch')
                need(summary['context']['protocol_ref'] == spec['protocol_ref'], 'Predecessor program mismatch')
                need(summary['stable_identity'] == W.stable_identity(spec), 'Predecessor stable source mismatch')
                name = summary['context']['stage_id']
                need(name not in summaries, 'Duplicate predecessor summary')
                original = W.checked_ref(root, summary['driver_receipt_ref'])
                need(W.read_json(original) == summary['driver_receipt'], 'Changed driver receipt')
                need(original == Path(spec['run_root'])/'stages'/name/'receipt.json', 'Driver receipt origin mismatch')
                driver = summary['driver_receipt']
                actual = [{'path':str(Path(e['path']).relative_to(original.parent/'outputs')),
                           'sha256':e['sha256'], 'bytes':e['size']} for e in W.inventory(original.parent/'outputs')]
                need(driver['status'] == 'completed' and driver['outputs'] == actual, 'Predecessor output changed')
                if spec['stage'] == 'generate-eval' and name.startswith('train-'):
                    # Checkpoint files, not future checkpoint IDs, enter model lineage.
                    checkpoint = original.parent/'outputs/checkpoint'
                    model_refs = descriptor['execution_bindings']['model_refs']
                    for item in W.inventory(checkpoint):
                        ref = {'path':str(Path(item['path']).relative_to(root)), 'sha256':item['sha256']}
                        need(ref in model_refs and ref in descriptor['job']['input_refs'], 'Checkpoint not model-bound')
                summaries[name] = summary
    need(set(summaries) == set(descriptor['required_predecessor_ids']), 'Missing authenticated stage summary')


def observe(H, h, root):
    """Current read-only host telemetry, no smoke, install or generated execution."""
    cpu, memory, diagnostics = H.collect_cpu_memory()
    def query(fields, kind):
        result = subprocess.run(['nvidia-smi', '--query-'+kind+'='+fields, '--format=csv,noheader,nounits'],
                                capture_output=True, text=True, timeout=20, check=True)
        return result.stdout.strip()
    gpu = query('uuid,name,memory.total,memory.free', 'gpu')
    processes = query('gpu_uuid,pid,process_name,used_gpu_memory', 'compute-apps')
    ps = subprocess.run(['ps','-eo','pid=,ppid=,comm='], capture_output=True, text=True, check=True, timeout=20).stdout
    result = {'host':socket.gethostname(), 'observed_at_unix':time.time(), 'cpu':cpu, 'memory':memory,
              'diagnostics':diagnostics, 'gpu_inventory_csv':gpu, 'gpu_processes_csv':processes,
              'process_inventory':ps, 'disk_free_bytes':shutil.disk_usage(root).free,
              'harness_resources':h['declared_resources'], 'harness_devices':h['devices']}
    return result


def admit_resources(obs, h):
    r = h['declared_resources']
    need(obs['memory']['observed_headroom_bytes'] is not None and
         obs['memory']['observed_headroom_bytes'] >= r['ram_mib']*1024**2, 'RAM not available')
    need(obs['cpu']['capacity_upper_bound'] is not None and
         obs['cpu']['capacity_upper_bound'] >= r['cpu_cores'], 'CPU capacity unknown/insufficient')
    need(obs['disk_free_bytes'] >= 16*1024**3, 'Need 16 GiB free including scratch and streamed copies')
    need(not obs['gpu_processes_csv'], 'GPU processes present; preserve and reconcile, no launch')
    rows = [line.split(', ') for line in obs['gpu_inventory_csv'].splitlines()]
    need(len(rows) == 1 and '4090' in rows[0][1], 'Expected fixed hn01 4090')
    need(r['gpu_count'] in (0,1) and r['allow_gpu_share'] is False, 'Invalid allocation')
    if r['gpu_count']:
        need(h['devices'] == [rows[0][0]] and float(rows[0][3]) >= (r['gpu_peak_mib'] or 0), 'GPU allocation/headroom mismatch')
    # Unknown Python/scientific processes outside the current ancestor chain wait.
    parents = {}; commands = {}
    for line in obs['process_inventory'].splitlines():
        pid, ppid, comm = line.strip().split(None, 2)
        parents[int(pid)] = int(ppid); commands[int(pid)] = comm
    ancestors = {os.getpid()}; pid = os.getpid()
    while parents.get(pid, 0) and parents[pid] not in ancestors:
        pid = parents[pid]; ancestors.add(pid)
    unknown = [pid for pid, comm in commands.items() if pid not in ancestors and
               re.search(r'python|torchrun|accelerate|diagnostic', comm, re.I)]
    need(not unknown, 'Unknown compute-capable processes: '+str(unknown))


def copy_exclusive(source, target):
    before = W.file_record(source)
    target = Path(target); W.safe_path(target.parent, target.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    with Path(source).open('rb') as src, target.open('xb') as dst:
        shutil.copyfileobj(src, dst, W.CHUNK)
    need(W.file_record(source) == before and W.hash_file(target) == before['sha256'], 'Copy changed')
    return {'origin':before, 'destination':str(target), 'sha256':before['sha256']}


def execute(args):
    c,s,program,plan,h,binding,cfg,spec,refs,H = validate(args)
    root, workspace = Path(c['project_root']), Path(c['workspace_root'])
    run = root/RUN
    run.mkdir(parents=True, exist_ok=True)
    # Global within this project; native harness also retains the actual device lease.
    with (root/'research-state/.b02-native-stage.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        folder = run/'stages'/W.stage_name(spec)
        attempt = run/'stage-entry-attempts'/c['attempt_id']
        need(not folder.exists() and not attempt.exists(), 'Existing/unknown stage; reconcile without retry')
        for relative in s['job']['output_paths']:
            need(not W.safe_path(root,relative).exists() and not W.safe_path(workspace,relative).exists(),
                 'Output conflict; never overwrite')
        attempt.mkdir(parents=True)
        W.write_new(attempt/'context.json',c)
        observation = observe(H,h,root)
        W.write_new(attempt/'resource-observation.json',observation)
        need(H.memory_constraints_known(observation['cpu'],observation['memory']), 'Unknown cgroup constraints')
        admit_resources(observation,h)
        argv = W.build_argv(spec,refs)
        timeout = 300 if spec['stage'] == 'calibrate-inference' else cfg['stage_watchdogs'][spec['stage']]
        need(plan['limits']['attempt_timeout_seconds'] >= timeout+300, 'No packaging reserve')
        W.write_new(attempt/'request.json', {'context':c,'argv':argv,'stable_identity':W.stable_identity(spec)})
        env = dict(os.environ, PYTHONPATH=cfg['source_root']+'/src:'+spec['stable_code_root'],
                   HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1',
                   OMP_NUM_THREADS=str(max(1,int(h['declared_resources']['cpu_cores']))))
        started=time.time(); child=None; code=None; failure=None; driver=None
        with (attempt/'stdout.log').open('xb') as out, (attempt/'stderr.log').open('xb') as err:
            try:
                # Inherit runtime process group; outer watchdog can terminate all descendants.
                child=subprocess.Popen(argv,cwd=root,env=env,stdout=out,stderr=err)
                W.write_new(attempt/'child.json',{'pid':child.pid,'started_at_unix':time.time(),'argv':argv})
                try: code=child.wait(timeout=timeout+30)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    try: code=child.wait(timeout=15)
                    except subprocess.TimeoutExpired: child.kill(); code=child.wait(timeout=15)
                    failure='driver timeout; no retry'
                driver=W.verify_driver(spec,refs,child.pid,started)
                if code != 0 or driver['status'] != 'completed': failure=failure or 'driver failed'
            except BaseException as exc:
                failure=type(exc).__name__+': '+str(exc)
                if child is not None and child.poll() is None:
                    child.kill(); child.wait(timeout=15)
        collect(attempt,folder,run,workspace,c,s,spec,argv,started,code,failure,driver,observation)
        return 3 if failure else 0


def collect(attempt,folder,run,workspace,c,s,spec,argv,started,code,failure,driver,observation):
    collected=W.inventory(folder)
    checkpoints=[e for e in collected if any('checkpoint' in p or p=='probe' or '.saving-' in p for p in Path(e['path']).parts)]
    skip={e['path'] for e in checkpoints}
    seal=attempt/'seal'; seal.mkdir()
    W.write_new(seal/'inventory.json', {'files':collected,'partial':failure is not None})
    W.write_new(seal/'checkpoint-inventory.json', {'files':checkpoints,'downloaded':False})
    members=[Path(e['path']) for e in collected if e['path'] not in skip]
    members += [p for p in attempt.iterdir() if p.is_file()]
    members += [p for p in (run/'identity.json',run/'config.json') if p.is_file()]
    W.archive_members(members,seal)
    sources={p.name:p for p in seal.iterdir() if p.is_file()}
    sources.update({n:attempt/n for n in ('stdout.log','stderr.log','resource-observation.json')})
    for n,relative in {'driver-receipt.json':'receipt.json','driver-request.json':'request.json'}.items():
        if (folder/relative).is_file(): sources[n]=folder/relative
    for name,relative in ({n:n for n in PREPARE} if spec['stage']=='prepare' else EXPORT if spec['stage']=='generate-eval' else {}).items():
        if (folder/'outputs'/relative).is_file(): sources[name]=folder/'outputs'/relative
    summary={'context':c,'stable_identity':W.stable_identity(spec),'status':'failed' if failure else 'completed',
             'scoring_status':'pending','scientific_verified':False,'driver_receipt':driver,
             'driver_receipt_ref':({'path':str((folder/'receipt.json').relative_to(c['project_root'])),
                                    'sha256':W.hash_file(folder/'receipt.json')} if driver is not None else None),
             'argv':argv,'started_at_unix':started,'ended_at_unix':time.time(),'exit_code':code,'failure':failure,
             'resource_observation':observation,'checkpoint_downloaded':False}
    W.write_new(seal/'stage-summary.json',summary); sources['stage-summary.json']=seal/'stage-summary.json'
    expected={Path(p).name:p for p in s['job']['output_paths']}
    maps=[]; total=sum(p.stat().st_size for p in sources.values())
    need(total <= 4*1024**3, 'Collection exceeds 4 GiB; originals retained')
    for name,source in sorted(sources.items()):
        need(name in expected, 'Undeclared output')
        maps.append(copy_exclusive(source,W.safe_path(workspace,expected[name])))
    W.write_new(W.safe_path(workspace,expected['origin-map.json']), {'context':c,'mappings':maps,
                'publication_owner':'trusted native runner; adapter writes workspace only'})
    if failure is None:
        need(all(W.safe_path(workspace,p).is_file() for p in s['job']['output_paths']), 'Missing output')
    W.write_new(attempt/'sealed.json',{'status':summary['status'],'summary':W.file_record(seal/'stage-summary.json')})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-stage-context',required=True)
    parser.add_argument('--binding-ref',required=True); parser.add_argument('--binding-sha256',required=True)
    parser.add_argument('--driver-stage',required=True,choices=sorted(MAP))
    parser.add_argument('--batch',type=int); parser.add_argument('--arm'); parser.add_argument('--seed',type=int)
    args=parser.parse_args()
    try: return execute(args)
    except Exception as exc:
        print(json.dumps({'status':'failed_or_contract_rejected','error':type(exc).__name__+': '+str(exc),
                          'scientific_verified':False,'scoring_status':'pending'}))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
