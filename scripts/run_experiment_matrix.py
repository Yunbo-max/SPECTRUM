#!/usr/bin/env python3
"""Plan and explicitly run independent ten-round cases. Planning never launches GPUs."""
import argparse
from contextlib import contextmanager
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
METHODS = ('plain', 'ssd', 'spectral_soft')
MODELS = ('qwen7b', 'llama8b', 'deepseek6.7b')
BENCHMARKS = ('humanevalplus', 'apps_intro', 'codecontests', 'livecodebench')
sys.path.insert(0, str(REPO/'src'))
_verified_files = {}
_verified_checkpoints = {}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj, indent=2)+'\n')
    os.replace(tmp, path)


def case_specs():
    jobs = []
    def add(id, kind, model, dataset, method, rounds, deps=(), availability='enabled', reason='', source_round=None):
        jobs.append(dict(id=id, kind=kind, model=model, dataset=dataset, method=method,
                         rounds=rounds, source_round=source_round, depends_on=list(deps),
                         availability=availability, reason=reason))
    for model in MODELS:
        stem = f'code.{model}.mbpp'
        availability = 'external_required' if model == 'qwen7b' else 'enabled'
        reason = 'User requested reuse of historical Qwen/MBPP; exact checkpoints and provenance must be bound before transfer.' if model == 'qwen7b' else ''
        add(stem+'.base', 'code_base', model, 'mbpp', 'base', 0,
            availability=availability, reason=reason)
        for method in METHODS:
            add(stem+'.'+method, 'code_train', model, 'mbpp', method, 10, [stem+'.base'], availability, reason)
        for bench in BENCHMARKS:
            add(f'eval.{model}.{bench}.base', 'code_eval', model, bench, 'base', 0,
                [] if model == 'qwen7b' else [stem+'.base'])
            for method in METHODS:
                add(f'eval.{model}.{bench}.{method}', 'code_eval', model, bench, method, 0,
                    [stem+'.'+method], source_round=10)
    for domain, dataset in [('math','math500'),('qa','mmlu_pro')]:
        stem = 'text.'+domain
        add(stem+'.base', 'text_base', 'qwen25-7b', dataset, 'base', 0)
        for method in METHODS:
            add(stem+'.'+method, 'text_train', 'qwen25-7b', dataset, method, 10, [stem+'.base'])
    reason = 'ARC native 27B long-context qualification and successful replay-verified calibration are not available.'
    add('arc.base','arc_base','qwen38-27b','arc_agi3','base',0, availability='blocked',reason=reason)
    for method in METHODS:
        add('arc.'+method,'arc_train','qwen38-27b','arc_agi3',method,10,['arc.base'],'blocked',reason)
    return jobs


def ready_cases(jobs, done):
    return [j for j in jobs if j['availability']=='enabled' and j['id'] not in done
            and set(j['depends_on']) <= done]


def source_hashes():
    paths = list((REPO/'src/improving').rglob('*.py')) + [Path(__file__).resolve()]
    return {str(p):sha(p) for p in paths}


def plan(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty plan directory; immutable manifests are never overwritten')
    output.mkdir(parents=True, exist_ok=True)
    configs, inputs = {}, {}
    for model in MODELS:
        p=source/f'runs/crossfamily_code_v1_20261107/plan/configs/{model}.json'
        c=read(p)
        c.update(rounds=10, methods=list(METHODS), label=f'ten-round-{model}',
                 output_dir=str(output/'studies/code'/model))
        configs[model]=c
        for path in c['data'].values(): inputs[path]=sha(path)
    for domain in ('math','qa'):
        c=read(source/f'runs/private/full_20261106/text_{domain}.json')
        c.update(rounds=10, output_dir=str(output/'studies/text'/domain))
        c['seed_file']=str(source/c['seed_file'])
        inputs[c['seed_file']]=sha(c['seed_file'])
        for p in (source/c['data']['output_dir']).glob('*.json*'): inputs[str(p)]=sha(p)
        configs['text_'+domain]=c
    arc=read(source/'configs/multidomain/arc3.json')
    arc.update(rounds=10, output_dir=str(output/'studies/arc'))
    configs['arc']=arc
    config_files={}
    for key,value in configs.items():
        path=output/'configs'/(key+'.json'); save(path,value)
        config_files[key]={'path':str(path),'sha256':sha(path)}
    registry=read(source/'data/final/benchmark_registry.json')
    if not registry.get('complete'): raise ValueError('Prepared coding registry is incomplete')
    benchmarks={}
    for name in BENCHMARKS:
        item=registry['benchmarks'][name]
        benchmarks[name]=item
        manifest=read(item['manifest'])
        inputs[item['manifest']]=sha(item['manifest'])
        for filename,expected in manifest['output_files'].items():
            p=Path(item['directory'])/filename
            if sha(p)!=expected['sha256']: raise ValueError('Prepared benchmark changed')
            inputs[str(p)]=expected['sha256']
    jobs=case_specs()
    for job in jobs:
        kind=job['kind']
        if kind.startswith('code_'):
            job['config']=config_files[job['model']]['path']
            job['source_run']=configs[job['model']]['output_dir']
            if kind=='code_eval':
                job['tasks']=benchmarks[job['dataset']]['tasks']
                job['output_dir']=str(output/'evaluations'/job['model']/job['dataset']/job['method'])
                if job['model']=='qwen7b' and job['method']=='base':
                    job['source_run']=str(source/'runs/crossfamily_code_v1_20261107/jobs/qwen7b')
                    p=Path(job['source_run'])/'manifest.json'; inputs[str(p)]=sha(p)
            else:
                job['output_dir']=configs[job['model']]['output_dir']
        elif kind.startswith('text_'):
            domain='math' if job['dataset']=='math500' else 'qa'
            job['config']=config_files['text_'+domain]['path']
            job['output_dir']=configs['text_'+domain]['output_dir']
        else:
            job['config']=config_files['arc']['path']; job['output_dir']=arc['output_dir']
        job['reserve_mib']=60000 if kind=='text_train' else 40000 if kind.endswith('_train') else 30000
        job['priority']=0 if kind.endswith('_base') else 1 if kind.endswith('_train') else 2 if job['method']=='base' else 3
    manifest=dict(schema=1, protocol='independent-ten-round-cases-v1', root=str(output), repo=str(REPO),
                  source_root=str(source), source_files=source_hashes(), inputs=inputs,
                  configs=config_files, jobs=jobs, launch_state='not_started',
                  note='Training cases have one method and ten rounds; base and frozen transfer are evaluations only.')
    manifest['fingerprint']=digest(manifest)
    save(output/'experiment_list.json',manifest)
    fields=['id','kind','model','dataset','method','rounds','source_round','availability','depends_on','reason']
    with (output/'experiment_list.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for job in jobs: writer.writerow({k:','.join(job[k]) if k=='depends_on' else job[k] for k in fields})
    commands=['# Explicit run commands; blocked and external cases refuse execution.']
    for job in jobs:
        commands.append(shlex.join([sys.executable,str(Path(__file__).resolve()),'run','--manifest',
                                   str(output/'experiment_list.json'),'--job',job['id']]))
    (output/'commands.sh').write_text('\n'.join(commands)+'\n')
    return {'manifest':str(output/'experiment_list.json'),'cases':len(jobs),
            'enabled_training_cases':sum(j['kind'].endswith('_train') and j['availability']=='enabled' for j in jobs),
            'launched':False}


def load_plan(path, verify=False):
    m=read(path); fingerprint=m.pop('fingerprint')
    if digest(m)!=fingerprint: raise ValueError('Plan changed after freezing')
    m['fingerprint']=fingerprint
    if Path(m['repo'])!=REPO: raise ValueError('Use the plan-pinned source checkout')
    if verify:
        for group in (m['source_files'], m['inputs'], {x['path']:x['sha256'] for x in m['configs'].values()}):
            for p,expected in group.items():
                if sha(p)!=expected: raise ValueError('Frozen source/input changed: '+p)
    return m


def file_state(path):
    s=Path(path).stat()
    return (s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def verify_file(path, expected):
    path=Path(path)
    key=(str(path.resolve()),expected)
    state=file_state(path)
    if _verified_files.get(key)!=state:
        if sha(path)!=expected: raise ValueError('Completed output changed: '+str(path))
        _verified_files[key]=state


def verify_native_marker(marker, expected):
    marker=Path(marker); verify_file(marker,expected)
    native=read(marker)
    files=native.get('files',native.get('output_hashes'))
    if not isinstance(files,dict) or not files: raise ValueError('Native marker omits output hashes')
    for name,h in files.items():
        p=(marker.parent/name).resolve()
        if not p.is_relative_to(marker.parent.resolve()): raise ValueError('Marker references external output')
        verify_file(p,h)
    if 'checkpoint.json' in files:
        receipt=read(marker.parent/'checkpoint.json')
        directory=marker.parent/'model'
        key=(str(directory.resolve()),receipt['checkpoint_identity'])
        state=tuple((str(p.relative_to(directory)),file_state(p)) for p in sorted(directory.rglob('*')) if p.is_file())
        if not state: raise ValueError('Final checkpoint missing')
        if _verified_checkpoints.get(key)!=state:
            from improving.pipeline import checkpoint_fingerprint
            if checkpoint_fingerprint(directory)!=receipt['checkpoint_identity']:
                raise ValueError('Completed text checkpoint changed')
            _verified_checkpoints[key]=state


def completed(m):
    done=set()
    for j in m['jobs']:
        p=Path(m['root'])/'cases'/j['id']/'complete.json'
        if p.is_file():
            d=read(p)
            if d['plan_fingerprint']!=m['fingerprint']: raise ValueError('Completion belongs to another plan')
            for marker,h in d['markers'].items(): verify_native_marker(marker,h)
            done.add(j['id'])
    return done


@contextmanager
def lock(path):
    import fcntl
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try: yield
        finally: fcntl.flock(stream,fcntl.LOCK_UN)


def run_case(manifest, case_id):
    m=load_plan(manifest,verify=True)
    os.chdir(m['source_root'])  # Prepared text manifests bind the original relative data path.
    j=next((x for x in m['jobs'] if x['id']==case_id),None)
    if j is None: raise ValueError('Unknown case')
    if j['availability']!='enabled': raise ValueError(j['reason'])
    done=completed(m)
    if not set(j['depends_on'])<=done: raise ValueError('Source/base case is not complete: '+str(j['depends_on']))
    if case_id in done: return {'case':case_id,'status':'already_complete'}
    root=Path(m['root']); output=Path(j['output_dir']); c=read(j['config'])
    with lock(root/'locks'/(case_id+'.lock')):
        if j['kind'] in ('code_base','code_train'):
            from improving.pipeline import run_experiment
            result=run_experiment(c,resume=True,base_only=j['kind']=='code_base',
                                  method=j['method'] if j['kind']=='code_train' else None)
            marker=output/'base/complete.json' if j['kind']=='code_base' else output/j['method']/'round_10/complete.json'
        elif j['kind'].startswith('text_'):
            from improving.text_study import run_text_study
            result=run_text_study(c,j['method'],resume=True)
            marker=output/j['method']/('round_0' if j['method']=='base' else 'round_10')/'complete.json'
        elif j['kind']=='code_eval':
            from improving.longitudinal import evaluate_checkpoints
            callback,identity=None,None
            if j['dataset']=='humanevalplus':
                from improving.benchmarks import make_humanevalplus_evaluator
                callback,identity=make_humanevalplus_evaluator(j['tasks'],settings={
                    'backend':'local','allow_unsafe_local':True,'parallel':4})
            source=read(Path(j['source_run'])/'manifest.json')
            base=j['method']=='base'
            result=evaluate_checkpoints(j['source_run'],output, samples=64,
                methods=[] if base else [j['method']], rounds=[min(10,source['config']['rounds'])] if base else [10],
                include_base=base, eval_tasks_path=j['tasks'],
                generation_overrides={'batch_size':8,'sequence_batch_size':8,'task_batch_size':1,
                                      'max_prompt_tokens':4096,'max_new_tokens':1024},
                evaluation_overrides={'backend':'local','allow_unsafe_local':True,'timeout':30,'memory_mb':1024},
                bootstrap_samples=2000,resume=True,evaluator=callback,evaluator_identity=identity)
            if result['status']!='completed': raise RuntimeError('Evaluation did not complete')
            marker=output/'base/complete.json' if base else output/j['method']/'round_10/complete.json'
        else: raise ValueError('Blocked execution kind')
        if not marker.is_file(): raise RuntimeError('Native completion marker missing')
        save(root/'cases'/case_id/'complete.json',{'case':case_id,'plan_fingerprint':m['fingerprint'],
                                                'markers':{str(marker):sha(marker)},'finished':time.time()})
        return {'case':case_id,'status':'complete','method':j['method'],'rounds':j['rounds']}


def terminate_queue(signum, frame):
    raise KeyboardInterrupt('Scheduler termination requested')


def queue(manifest, gpus, limit, workers):
    m=load_plan(manifest,verify=True); root=Path(m['root']); active={}; attempts={}; failed={}
    def memory():
        raw=subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=index,memory.used',
                                     '--format=csv,noheader,nounits'],text=True)
        return {int(a):int(b) for a,b in (line.split(',') for line in raw.splitlines())}
    def signal_child(item,sig):
        if item['process'].poll() is None: os.killpg(item['process'].pid,sig)
    def status(state):
        save(root/'queue_status.json',dict(state=state,pid=os.getpid(),limit_mib=limit,updated=time.time(),
            active={k:{'pid':v['process'].pid,'gpu':v['gpu']} for k,v in active.items()},failed=failed,
            completed=sorted(completed(m))))
    with lock(root/'locks/scheduler.lock'):
        previous_term=signal.signal(signal.SIGTERM,terminate_queue)
        last_launch=0
        try:
            while True:
                for name,item in list(active.items()):
                    code=item['process'].poll()
                    if code is not None:
                        if code!=0: failed[name]={'exit_code':code,'log':item['log']}
                        elif name not in completed(m): failed[name]={'reason':'success without receipt'}
                        del active[name]
                used=memory()
                for gpu in gpus:
                    items=[(n,x) for n,x in active.items() if x['gpu']==gpu]
                    stopping=[x for _,x in items if x.get('stop_at')]
                    if used[gpu]>=limit and items and not stopping:
                        name,item=max(items,key=lambda pair:pair[1]['started'])
                        signal_child(item,signal.SIGINT);item['stop_at']=time.time()
                        failed[name]={'reason':'memory ceiling; resumable, no automatic repeated restart'}
                    for item in stopping:
                        elapsed=time.time()-item['stop_at']
                        if elapsed>40: signal_child(item,signal.SIGKILL)
                        elif elapsed>20: signal_child(item,signal.SIGTERM)
                done=completed(m)
                ready=sorted((j for j in ready_cases(m['jobs'],done) if j['id'] not in active and j['id'] not in failed),
                             key=lambda j:(j['priority'],j['id']))
                launched=False
                if time.time()-last_launch>=90:
                    for j in ready:
                        for gpu in sorted(gpus,key=lambda x:used[x]):
                            on_gpu=[x for x in active.values() if x['gpu']==gpu]
                            if len(on_gpu)>=workers or any(x.get('stop_at') for x in on_gpu): continue
                            if used[gpu]+j['reserve_mib']>=limit: continue
                            logpath=root/'logs'/(j['id']+'.'+str(int(time.time()))+'.log')
                            logpath.parent.mkdir(parents=True,exist_ok=True)
                            env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES=str(gpu),PYTHONPATH=str(REPO/'src'),
                                OMP_NUM_THREADS='2',TOKENIZERS_PARALLELISM='false',PYTHONUNBUFFERED='1')
                            with logpath.open('x') as log:
                                child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'run',
                                    '--manifest',str(Path(manifest).resolve()),'--job',j['id']],cwd=REPO,env=env,
                                    stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                            active[j['id']]={'process':child,'gpu':gpu,'started':time.time(),'log':str(logpath)}
                            last_launch=time.time();launched=True;break
                        if launched:break
                status('running')
                if not active and not ready:
                    status('complete' if len(done)==len(m['jobs']) else 'awaiting_blocked_or_failed_cases')
                    return {'completed':len(done),'total':len(m['jobs']),'failed':failed}
                time.sleep(2)
        finally:
            for item in active.values(): signal_child(item,signal.SIGINT)
            for item in active.values():
                try: item['process'].wait(timeout=20)
                except subprocess.TimeoutExpired:
                    signal_child(item,signal.SIGTERM)
                    try: item['process'].wait(timeout=10)
                    except subprocess.TimeoutExpired: signal_child(item,signal.SIGKILL)
            if active: status('stopped')
            signal.signal(signal.SIGTERM,previous_term)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('plan');q.add_argument('--source-root',required=True);q.add_argument('--output',required=True)
    for action in ('list','check','run','queue'):
        q=sub.add_parser(action);q.add_argument('--manifest',required=True)
        if action=='run': q.add_argument('--job',required=True)
        if action=='queue':
            q.add_argument('--gpus',default='0,1');q.add_argument('--limit-mib',type=int,default=85000)
            q.add_argument('--workers-per-gpu',type=int,choices=(1,2),default=1)
    args=p.parse_args()
    if args.action=='plan': result=plan(args.source_root,args.output)
    elif args.action=='run': result=run_case(args.manifest,args.job)
    elif args.action=='queue': result=queue(args.manifest,[int(x) for x in args.gpus.split(',')],args.limit_mib,args.workers_per_gpu)
    else:
        m=load_plan(args.manifest,verify=args.action=='check');done=completed(m)
        if args.action=='check':
            from improving.pipeline import validate_config
            from improving.text_study import validate_text_config,validate_prepared_binding
            from improving.text_tasks import private_seed,verify_prepared_data
            os.chdir(m['source_root'])
            for key,item in m['configs'].items():
                if key in MODELS: validate_config(read(item['path']))
                elif key.startswith('text_'):
                    c=validate_text_config(read(item['path']))
                    _,prepared=verify_prepared_data(c['data']['output_dir'])
                    validate_prepared_binding(c,prepared,private_seed(c['seed_file']))
            result={'verified':True,'cases':len(m['jobs']),'completed':len(done),'gpu_work_started':False}
        else:
            result=[{k:j[k] for k in ('id','method','rounds','source_round','depends_on','availability')} for j in m['jobs']]
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
