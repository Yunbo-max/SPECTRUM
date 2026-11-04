#!/usr/bin/env python3
"""Frozen, foreground ICLR rebuttal study. No training without --execute.

Original soft SPECTRUM and the learned extension are separate rows. This driver
adds experiments and receipts, not a different learning objective to main arms.
Numeric seeds stay in the ignored local run root. No PI/GUI or test feedback.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import importlib.util
import json
from pathlib import Path
import secrets
import statistics
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
_spec = importlib.util.spec_from_file_location('crossfamily_rebuttal_helper', ROOT/'scripts/run_crossfamily_study.py')
cf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cf)
PROTOCOL = 'spectrum-iclr-rebuttal-v1'
ASSETS = ROOT/'configs/crossfamily/assets.json'
TEMPLATE = ROOT/'configs/crossfamily/protocol_learned_4096.json'
REFERENCE = ROOT/'configs/spectrum_7b/spectrum_7b_r10_learned_4096.yaml'
BLOCKS = ('core', 'crossfamily', 'mechanism', 'objective')


def initialize(root, backend=None, allow_unsafe_local=False):
    root = Path(root).resolve()
    choices_path = root/'runtime_choices.json'
    if backend == 'local' and not allow_unsafe_local:
        raise ValueError('Local execution is unsafe; explicitly pass --allow-unsafe-local or use isolation')
    if allow_unsafe_local and backend != 'local':
        raise ValueError('--allow-unsafe-local requires --backend local')
    if backend is not None or not choices_path.exists():
        cf.save(choices_path, {'backend':backend or 'docker',
                'allow_unsafe_local':bool(allow_unsafe_local)}, immutable=True)
    target = root/'private_seeds.json'
    if not target.exists():
        import yaml
        original = yaml.safe_load(REFERENCE.read_text())
        seeds = set()
        while len(seeds) < 3:
            seeds.add(secrets.randbits(31))
        cf.save(target, {'protocol': PROTOCOL, 'data_seed': original['data_seed'],
                         'training_seeds': sorted(seeds),
                         'data_split_source': str(REFERENCE.relative_to(ROOT))}, immutable=True)
        target.chmod(0o600)
    values = cf.read(target)
    if (values.get('protocol') != PROTOCOL or type(values.get('data_seed')) is not int
            or not isinstance(values.get('training_seeds'), list)
            or len(values['training_seeds']) != 3
            or any(type(s) is not int or s < 0 for s in values['training_seeds'])
            or len(set(values['training_seeds'])) != 3):
        raise ValueError('Invalid frozen private seeds; do not replace an existing study')
    legacy = root/'data_seed_contract.json'
    cf.save(legacy, {'protocol': cf.PROTOCOL, 'data_seed': values['data_seed'],
                    'training_seed': values['training_seeds'][0],
                    'trajectory_label': 'shared-data'}, immutable=True)
    legacy.chmod(0o600)
    return {'status': 'initialized', 'root': str(root), 'replicates': ['r1','r2','r3']}


def build_configs(root, seeds, runtime=None):
    """Pure config construction: no model, data download, grading or RNG mutation."""
    root = Path(root).resolve()
    assets, protocol = cf.read(ASSETS), cf.read(TEMPLATE)
    jobs = {}

    def add(key, block, alias, rep, rounds, methods=None, change=None):
        model = assets['models'][alias]
        cfg = {k: deepcopy(protocol[k]) for k in
               ('methods','calibration','generation','train','evaluation','diagnostics')}
        cfg.update(label=key, seed=seeds['training_seeds'][rep-1], data_seed=seeds['data_seed'],
                   rounds=rounds, checkpoint_retention='latest', data_limits={},
                   output_dir=str(root/'jobs'/key),
                   data={s: str(root/'data/mbpp'/f'{s}.jsonl') for s in cf.COUNTS},
                   model={'name': model['repo_id'], 'revision': model['revision'],
                          'local_files_only': True, 'device': 'auto',
                          'dtype': 'bfloat16', 'attn_implementation': 'sdpa'})
        if runtime is not None:
            cfg['evaluation'].update(runtime)
        # Qwen native uses all layers. Cross-family retains its declared two-layer
        # placement, not an undocumented claim of identical layer coverage.
        cfg['calibration']['layers'] = None if alias == 'qwen7b' else model['layers']
        if methods is not None:
            cfg['methods'] = methods
        if 'spectral_learned' not in cfg['methods']:
            cfg['calibration'].pop('gain_learning', None)
            cfg['calibration'].pop('matched_reference_fit_examples', None)
            cfg['calibration']['max_examples'] = 40
        chosen = [r for r in (1,5,8,10) if r <= rounds]
        cfg['diagnostics'] = {'evaluate_generation_policy': False, 'transfer_gap': {
            'enabled': True, 'rounds': chosen, 'samples': 64, 'validation_task_count': 30,
            'batch_size': 1, 'task_batch_size': 1, 'sequence_batch_size': 1,
            'max_prompt_tokens': cfg['generation']['max_prompt_tokens'],
            'max_new_tokens': cfg['generation']['max_new_tokens'],
            'reference_nll_each_round': True}}
        if change:
            change(cfg)
        jobs[key] = {'block': block, 'model': alias, 'replicate': f'r{rep}', 'config': cfg}

    for rep in range(1,4):
        add(f'core-qwen7b-r{rep}', 'core', 'qwen7b', rep, 10)
    for alias in ('llama8b','deepseek6.7b'):
        add(f'crossfamily-{alias}-r1', 'crossfamily', alias, 1, 5)
    add('mechanism-qwen7b-r1', 'mechanism', 'qwen7b', 1, 5,
        ['spd_hard','random_soft','isotropic_soft'])
    add('fixed50-qwen7b-r1', 'mechanism', 'qwen7b', 1, 5, ['spectral_soft'],
        lambda c: c['calibration'].update(max_examples=50))
    add('replay50-qwen7b-r1', 'mechanism', 'qwen7b', 1, 5, ['plain'],
        lambda c: (c['calibration'].update(max_examples=50), c['train'].update(fixed_anchor_replay=True)))
    add('completion-qwen7b-r1', 'objective', 'qwen7b', 1, 10,
        change=lambda c: c['train'].update(loss_scope='completion'))
    return jobs


def budget(cfg):
    n, rounds = len(cfg['methods']), cfg['rounds']
    g, diag = cfg['generation'], cfg['diagnostics']['transfer_gap']
    return {'training_completions': 291*g['train_samples']*rounds*n,
            'test_completions': 500*g['eval_samples']*(1+rounds*n),
            'dev_completions': 30*diag['samples']*3*len(diag['rounds'])*n,
            'probe_completions': (cfg['calibration']['gain_learning']['probe_examples']*rounds
                                  if 'spectral_learned' in cfg['methods'] else 0),
            'method_trajectories': n, 'sft_rounds': n*rounds,
            'note': 'Counts are samples, NOT GPU hours; replay references and repeated fit passes are extra.'}


def select_jobs(jobs, *, block='all', model='all', replicate='all'):
    selected = {k:v for k,v in jobs.items()
                if (block=='all' or v['block']==block)
                and (model=='all' or v['model']==model)
                and (replicate=='all' or v['replicate']==replicate)}
    if not selected:
        raise ValueError('No jobs match the requested block/model/replicate')
    return selected


def source_files():
    files = cf.sources()
    for p in [Path(__file__), ASSETS, TEMPLATE, REFERENCE,
              ROOT/'scripts/report_transfer_gap.py', ROOT/'scripts/qualify_learned_gains.py']:
        files[str(p.relative_to(ROOT))] = cf.sha(p)
    return files


def preparation_args(root, model):
    return SimpleNamespace(assets=str(ASSETS), run_root=str(root), data_root=str(root/'data'),
                           seed_file=str(root/'data_seed_contract.json'), model=model)


def prepare(root, model, execute):
    if not execute:
        return {'status': 'dry_run', 'action': 'download_pinned_models_and_prepare_shared_data',
                'model': model, 'execute_required': True}
    initialize(root)
    # Preserve the original upstream/hash receipt across partial-prepare retries.
    # Re-downloading from an offline cache can omit upstream LFS metadata and
    # must not replace the stronger immutable receipt from the first download.
    mapping = cf.assets(ASSETS)
    for alias in (cf.MODELS if model == 'all' else (model,)):
        if (root/'assets'/f'{alias}.json').is_file():
            cf.verify_model({'assets': mapping, 'run_root': str(root)}, alias)
        else:
            cf.download(preparation_args(root, alias))
    return cf.prepare(preparation_args(root, model))


def make_plan(root):
    from improving.pipeline import validate_config
    seeds = cf.read(root/'private_seeds.json')
    prepared, inputs = cf.snapshot_prepared(root/'data')
    if (prepared['assets_sha256'] != cf.digest(cf.read(ASSETS))
            or prepared['seed_file_sha256'] != cf.sha(root/'data_seed_contract.json')):
        raise ValueError('Shared dataset was prepared with different assets or randomization')
    jobs = build_configs(root, seeds, cf.read(root/'runtime_choices.json'))
    for key, entry in jobs.items():
        validate_config(entry['config'])
        path = root/'plan/configs'/f'{key}.json'
        cf.save(path, entry['config'], immutable=True)
        entry.update(config_path=str(path), config_sha256=cf.sha(path), budget=budget(entry['config']))
    manifest = {'protocol': PROTOCOL, 'status': 'planned_not_run', 'source_files': source_files(),
                'root': str(root), 'data_files': inputs,
                'private_files': {str(root/name): cf.sha(root/name)
                                  for name in ('private_seeds.json','data_seed_contract.json','runtime_choices.json')},
                'jobs': jobs, 'test_based_selection': False,
                'primary_endpoints': {'core': [5,10], 'crossfamily':[5], 'mechanism':[5], 'objective':[5,10]},
                'uncertainty': 'Task-paired CIs conditional on a run; training-replicate SD reported separately.'}
    cf.save(root/'plan/manifest.json', manifest, immutable=True)
    return {'status': 'planned_not_run', 'jobs': {k: {'block':v['block'], 'model':v['model'],
            'replicate':v['replicate'], 'budget':v['budget']} for k,v in jobs.items()}}


def load_plan(root):
    manifest = cf.read(root/'plan/manifest.json')
    if manifest.get('protocol') != PROTOCOL or manifest['source_files'] != source_files():
        raise ValueError('Frozen source changed: use the pinned checkout or a NEW study root')
    for path, expected in {**manifest['data_files'], **manifest['private_files']}.items():
        if not Path(path).is_file() or cf.sha(path) != expected:
            raise ValueError(f'Frozen input integrity failure: {path}')
    for job in manifest['jobs'].values():
        if (cf.sha(job['config_path']) != job['config_sha256']
                or cf.read(job['config_path']) != job['config']):
            raise ValueError('Frozen job config changed')
    return manifest


def sealed(directory, *, base=False):
    """Validate receipts and every retained file, not just marker existence."""
    marker = directory/'complete.json'
    if not marker.is_file():
        return False
    state = cf.read(marker)
    files = state.get('files', {})
    if 'evaluation.metrics.json' not in files or not files:
        raise ValueError(f'Incomplete evidence integrity receipt: {directory}')
    for relative, digest in files.items():
        path = (directory/relative).resolve()
        if (not path.is_relative_to(directory.resolve()) or not path.is_file()
                or cf.sha(path) != digest):
            raise ValueError(f'Evidence integrity failure: {directory}/{relative}')
    if not base and state.get('status') != 'completed':
        raise ValueError(f'Uncompleted evidence receipt: {directory}')
    return True


def metrics(summary):
    a = summary['aggregate']
    impl = a['implementation_proxy']
    return {'pass@1': a['pass_at_k']['1']['mean'], 'pass@16': a['pass_at_k']['16']['mean'],
            'pass@64': a['pass_at_k']['64']['mean'],
            'C64_AST': impl['coverage_at_k']['64']['mean'],
            'D4_AST': impl['correct_matched_coverage_at_budgets']['4']['mean'],
            'D4_eligible_tasks': impl['correct_matched_coverage_at_budgets']['4']['eligible_tasks']}


def round_evidence(directory, *, method, round_index):
    directory = Path(directory)
    result = {'method': method, 'round': round_index, 'status': 'missing', 'metrics': None}
    if not sealed(directory, base=(method=='base')):
        return result
    summary = cf.read(directory/'evaluation.metrics.json')
    result.update(status='complete', metrics=metrics(summary))
    result['task_bootstrap'] = summary['aggregate']
    if (directory/'training_stats.json').is_file():
        s=cf.read(directory/'training_stats.json')
        result['training'] = {k:s.get(k) for k in ('actual_supervised_target_tokens','optimizer_steps',
            'all_raw_records_retained','truncated_tokens','loss_scope','anchor_reference_records')}
    if (directory/'learned_gains.json').is_file():
        a=cf.read(directory/'learned_gains.json')
        result['controller']={k:a.get(k) for k in ('selected_identity','fallback_reason','accepted_steps','selected')}
    if (directory/'transfer_gap/report.json').is_file():
        result['transfer_gap']=cf.read(directory/'transfer_gap/report.json')
    result['resources']={p.name:cf.read(p) for p in directory.glob('*.resources.json')}
    return result


def seed_summary(rows, expected):
    values = [r['value'] for r in rows if r['value'] is not None]
    if len({r['replicate'] for r in rows}) != len(rows):
        raise ValueError('Duplicate independent training replicate')
    return {'status':'complete' if len(values)==expected else 'incomplete',
            'expected_replicates':expected, 'n_completed':len(values),
            'mean':statistics.mean(values) if values else None,
            'sample_sd':statistics.stdev(values) if len(values)>1 else None,
            'replicates':rows, 'uncertainty_unit':'independent_training_run_not_tasks'}


def report(root):
    from improving.metrics import compare_summaries
    manifest=load_plan(root)
    trajectories, paired, flat = {}, {}, []
    seeds=cf.read(root/'private_seeds.json')
    for key, entry in manifest['jobs'].items():
        cfg=entry['config']; directory=Path(cfg['output_dir'])
        rows=[round_evidence(directory/'base', method='base', round_index=0)]
        for method in cfg['methods']:
            rows.extend(round_evidence(directory/method/f'round_{r}', method=method, round_index=r)
                        for r in range(1,cfg['rounds']+1))
        base=rows[0]['metrics']
        for row in rows:
            row['retention_C64_vs_round0']=(row['metrics']['C64_AST']/base['C64_AST']
                if row['metrics'] and base and base['C64_AST']>0 else None)
            flat.append({'job':key, 'block':entry['block'], 'model':entry['model'],
                         'replicate':entry['replicate'], 'method':row['method'], 'round':row['round'],
                         'status':row['status'], **(row['metrics'] or {}),
                         'retention_C64_vs_round0':row['retention_C64_vs_round0']})
        trajectories[key]=rows
        paired[key]={}
        if 'ssd' in cfg['methods']:
            for r in manifest['primary_endpoints'][entry['block']]:
                for method in ('spectral_soft','spectral_learned'):
                    if method not in cfg['methods']:
                        continue
                    left=directory/'ssd'/f'round_{r}'
                    right=directory/method/f'round_{r}'
                    pair=f'{method}_minus_ssd_round_{r}'
                    if sealed(left) and sealed(right):
                        paired[key][pair]=compare_summaries(cf.read(left/'evaluation.metrics.json'),
                            cf.read(right/'evaluation.metrics.json'), bootstrap_samples=2000,
                            seed=seeds['training_seeds'][0])
                    else:
                        paired[key][pair]={'status':'missing_or_incomplete'}
    across={}
    for r in (5,10):
        for method in ('plain','ssd','spectral_soft','spectral_learned'):
            for metric in ('pass@1','pass@64','C64_AST','D4_AST'):
                values=[]
                for rep in ('r1','r2','r3'):
                    row=next(x for x in trajectories[f'core-qwen7b-{rep}'] if x['method']==method and x['round']==r)
                    values.append({'replicate':rep, 'value':row['metrics'].get(metric) if row['metrics'] else None})
                across[f'{method}/round_{r}/{metric}']=seed_summary(values,3)
    result={'protocol':PROTOCOL, 'trajectories':trajectories, 'paired_differences':paired,
            'across_training_runs':across, 'no_best_round_selection':True,
            'limitations':['AST categories are implementation proxies, not semantic strategy labels.',
                          'Cross-family and mechanism blocks have one training replicate each.',
                          'Native short-prefix KL is not a whole-trajectory guarantee.',
                          'Original fixed-soft and Learned extension are separate methods.',
                          'Replay50 adds supervised targets and is not compute-matched.',
                          'Completion-only changes effective target exposure; compare all four arms.']}
    output=root/'report'; cf.save(output/'report.json',result)
    fields=['job','block','model','replicate','method','round','status','pass@1','pass@16','pass@64',
            'C64_AST','D4_AST','D4_eligible_tasks','retention_C64_vs_round0']
    with (output/'trajectories.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(flat)
    complete=sum(x['status']=='complete' for x in flat)
    (output/'README.md').write_text(f'# Rebuttal evidence\n\n{complete}/{len(flat)} planned base/round cells complete.\n'
        'Missing cells are empty, never zero. CSV contains every predeclared round.\n'
        'JSON contains task-paired CIs, separate across-run mean/SD, resources and controller receipts.\n'
        'Do not publish private seeds or claim missing training/transfer results.\n')
    return {'report':str(output), 'completed_cells':complete, 'planned_cells':len(flat)}


def transfer_proxy(root, entry):
    cfg = entry['config']
    settings = deepcopy(cf.read(TEMPLATE))
    settings['rounds'] = cfg['rounds']
    settings['transfer']['round'] = cfg['rounds']
    settings['methods'] = cfg['methods']
    settings['evaluation'] = cfg['evaluation']
    return {'run_root':str(root), 'data_root':str(root/'data'), 'settings':settings}


def run_jobs(root, jobs, stage, execute):
    if not execute:
        return {'status':'dry_run', 'stage':stage, 'jobs':list(jobs),
                'budgets':{k:budget(v['config']) for k,v in jobs.items()}}
    from improving.pipeline import run_experiment, _preflight_verification
    from improving.longitudinal import export_longitudinal
    mapping=cf.read(ASSETS)
    results=[]
    for key, entry in jobs.items():
        cfg=entry['config']
        with cf.lock(root,key):
            _preflight_verification(cfg['evaluation'])
            if stage in ('transfer','all') and entry['block'] in ('core','crossfamily'):
                from improving.benchmarks import make_humanevalplus_evaluator
                tasks=root/'data/humanevalplus/eval.jsonl'
                make_humanevalplus_evaluator(tasks, settings={
                    'backend':cfg['evaluation']['backend'],
                    'allow_unsafe_local':cfg['evaluation'].get('allow_unsafe_local',False),
                    'prepared_dataset_dir':str(tasks.parent)})
            cf.verify_model({'assets':mapping,'run_root':str(root)},entry['model'])
            if stage in ('qualify','all') and 'spectral_learned' in cfg['methods']:
                qcfg=deepcopy(cfg); qcfg['methods']=['spectral_learned']
                qpath=root/'plan/qualification'/f'{key}.json'
                cf.save(qpath,qcfg,immutable=True)
                subprocess.run([sys.executable,str(ROOT/'scripts/qualify_learned_gains.py'),
                    '--config',str(qpath),'--output-dir',str(root/'qualification'/key),'--resume'],check=True)
            if stage in ('train','all'):
                result=run_experiment(cfg,resume=True)
                if result.get('status')!='completed':
                    raise RuntimeError(f'Incomplete training: {key}')
                export_longitudinal(cfg['output_dir'],bootstrap_samples=2000)
                results.append({'job':key,'stage':'train','status':'completed'})
            if stage in ('transfer','all') and entry['block'] in ('core','crossfamily'):
                cf.transfer(transfer_proxy(root,entry),key)
                results.append({'job':key,'stage':'humanevalplus','status':'completed'})
    return {'results':results}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('init','preview','prepare','plan','run','report'))
    p.add_argument('--root',default='runs/iclr_rebuttal_v1')
    p.add_argument('--block',choices=('all',*BLOCKS),default='all')
    p.add_argument('--model',choices=('all',*cf.MODELS),default='all')
    p.add_argument('--replicate',choices=('all','r1','r2','r3'),default='all')
    p.add_argument('--stage',choices=('qualify','train','transfer','all'),default='all')
    p.add_argument('--execute',action='store_true')
    p.add_argument('--backend',choices=('docker','bwrap','local'),help='init only; frozen for this study')
    p.add_argument('--allow-unsafe-local',action='store_true')
    a=p.parse_args(argv); root=Path(a.root).expanduser().resolve()
    if a.command!='init' and (a.backend is not None or a.allow_unsafe_local):
        p.error('Set the evaluation backend only at init, before freezing a plan')
    if a.command=='init':
        result=initialize(root,a.backend,a.allow_unsafe_local)
    elif a.command=='prepare':
        result=prepare(root,a.model,a.execute)
    elif a.command=='plan':
        result=make_plan(root)
    elif a.command=='preview':
        jobs=build_configs(root,cf.read(root/'private_seeds.json'),cf.read(root/'runtime_choices.json'))
        jobs=select_jobs(jobs,block=a.block,model=a.model,replicate=a.replicate)
        result=run_jobs(root,jobs,a.stage,False)
    elif a.command=='report':
        result=report(root)
    else:
        jobs=load_plan(root)['jobs']
        jobs=select_jobs(jobs,block=a.block,model=a.model,replicate=a.replicate)
        result=run_jobs(root,jobs,a.stage,a.execute)
    print(json.dumps(result,indent=2,allow_nan=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
