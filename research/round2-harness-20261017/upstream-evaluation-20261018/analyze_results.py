"""Analyze upstream-emitted statuses. Does not execute or score model code."""
import ast
import collections
import hashlib
import json
import pathlib
import random
import sys

ROOT=pathlib.Path('/root/rivermind-data/spectrum-harness/project')
S=ROOT/'research-state/upstream-evaluation-20261018'
sys.path.insert(0,str(ROOT/'upstreams/evalplus'))
from evalplus.data import get_mbpp_plus

def interval(values,seed):
    rng=random.Random(seed)
    means=sorted(sum(rng.choices(values,k=len(values)))/len(values) for _ in range(5000))
    return [means[124],means[4874]]

def main():
    data=get_mbpp_plus()
    raw=S/'official-qwen-greedy/mbpp/qwen2_chat_temp_0.0'
    sanitized=raw.with_name(raw.name+'-sanitized')
    results={}
    for name,folder in [('raw',raw),('sanitized',sanitized)]:
        result_path=S/'evaluation-rootfs/work'/folder.name/'eval_results.json'
        result=json.loads(result_path.read_text())
        assert set(result['eval'])==set(data) and all(len(v)==1 for v in result['eval'].values())
        results[name]={k:v[0] for k,v in result['eval'].items()}
        (S/(name+'-eval_results.json')).write_bytes(result_path.read_bytes())
    engine=[json.loads(s) for s in (S/'generation-engine-raw.jsonl').read_text().splitlines()]
    assert len(engine)==len(data)==378
    identity={}
    imports=collections.Counter()
    for (task_id,task),row in zip(data.items(),engine):
        assert task['prompt'].strip() in row['prompt']
        assert len(row['outputs'])==1
        output=row['outputs'][0]
        emitted=output['text'].replace('\t','    ')
        if '```' in emitted:emitted=emitted.split('```')[0]
        source=raw/task_id.replace('/','_')/'0.py'
        assert source.read_text()==emitted
        clean=sanitized/task_id.replace('/','_')/'0.py'
        assert results['raw'][task_id]['solution']==source.read_text()
        assert results['sanitized'][task_id]['solution']==clean.read_text()
        try:
            tree=ast.parse(source.read_text());syntax=True
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):imports.update(a.name.split('.')[0] for a in n.names)
                elif isinstance(n,ast.ImportFrom) and n.module:imports[n.module.split('.')[0]]+=1
        except SyntaxError:syntax=False
        identity[task_id]={'task_id':task_id,'finish_reason':output['finish_reason'],'stop_reason':output['stop_reason'],
                           'prompt_tokens':len(row['prompt_token_ids']),'generation_tokens':len(output['token_ids']),
                           'sanitizer_changed':source.read_bytes()!=clean.read_bytes(),'raw_syntax_valid':syntax,
                           'raw_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                           'sanitized_sha256':hashlib.sha256(clean.read_bytes()).hexdigest()}
    summary={'tasks':len(data),'samples_per_task':1,'protocol':'Qwen-author greedy generation and pinned EvalPlus899b2b3',
             'endpoint_notes':'plus requires BOTH base and extended tests to pass; statuses come from unmodified upstream evaluator',
             'uncertainty_notes':'Task bootstrap only; one greedy sample per task, not training/generation-seed variability or untouched confirmation',
             'sanitizer_changed_files':sum(r['sanitizer_changed'] for r in identity.values()),
             'raw_syntax_valid':sum(r['raw_syntax_valid'] for r in identity.values()),
             'finish_reasons':dict(collections.Counter(r['finish_reason'] for r in identity.values())),
             'imports':dict(imports),'endpoints':{}}
    ids=list(data)
    for name,statuses in results.items():
        base=[int(statuses[k]['base_status']=='pass') for k in ids]
        plus=[int(statuses[k]['base_status']==statuses[k]['plus_status']=='pass') for k in ids]
        summary['endpoints'][name]={'base_passed':sum(base),'base_pass_at_1':sum(base)/len(ids),'base_task_bootstrap_ci95':interval(base,1810),
                                  'plus_passed':sum(plus),'plus_pass_at_1':sum(plus)/len(ids),'plus_task_bootstrap_ci95':interval(plus,1811),
                                  'base_pass_plus_fail':sum(b-p for b,p in zip(base,plus)),
                                  'base_statuses':dict(collections.Counter(r['base_status'] for r in statuses.values())),
                                  'extended_statuses':dict(collections.Counter(r['plus_status'] for r in statuses.values())),
                                  'length_capped_base_failures':[k for k in ids if identity[k]['finish_reason']=='length' and statuses[k]['base_status']!='pass'],
                                  'length_capped_plus_failures':[k for k in ids if identity[k]['finish_reason']=='length' and not statuses[k]['base_status']==statuses[k]['plus_status']=='pass']}
    summary['sanitization_outcome_changes']={metric:[k for k in ids if results['raw'][k][metric]!=results['sanitized'][k][metric]] for metric in ['base_status','plus_status']}
    for k in ids:
        identity[k].update(raw_base=results['raw'][k]['base_status'],raw_extended=results['raw'][k]['plus_status'],sanitized_base=results['sanitized'][k]['base_status'],sanitized_extended=results['sanitized'][k]['plus_status'])
    (S/'per-task-analysis.json').write_text(json.dumps(list(identity.values()),indent=2)+'\n')
    (S/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
