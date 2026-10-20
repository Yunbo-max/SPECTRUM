"""CPU-only checks using already executed native software probes; no code execution."""
import copy,hashlib,importlib.util,json,pathlib,tempfile
S=pathlib.Path('/root/rivermind-data/spectrum-harness/project/research-state/ssd-author-comparison-20261019')
spec=importlib.util.spec_from_file_location('analysis',S/'analyze_condition.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
native=json.loads((S/'software-probe-results.json').read_text())
rows=native['all_repeat_results'][0]
cfg=json.loads((S/'base-temperature-0.7/config.json').read_text());cfg['n_repeat']=1;cfg['dataset_sha256']='software-fixture-only'
checks={}
with tempfile.TemporaryDirectory(prefix='ssd-comparison-analysis-') as temporary:
 root=pathlib.Path(temporary);mod.S=root;mod.DATA=root/'dataset-resolution.json'
 (root/'dataset-resolution.json').write_text(json.dumps({'ordered_task_ids':[r['task_id'] for r in rows]}))
 for condition in ['first','second']:
  d=root/condition;d.mkdir();(d/'config.json').write_text(json.dumps(cfg));(d/'results.json').write_text(json.dumps(native))
  raw=[{'task_id':r['task_id'],'seed':0,'prompt_sha256':hashlib.sha256(r['prompt'].encode()).hexdigest(),'text':'```python\n'+r['content'][0]+'```','token_ids':[],'finish_reason':'stop'} for r in rows]
  (d/'repeat-00.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in raw));mod.analyze(condition)
 report=mod.compare('first','second');assert report['any_success_discordance']=={'both':2,'first_only':0,'second_only':0,'neither':3};assert report['paired_differences']['pass@1']['second_minus_first']==0
 checks['same_native_evidence_compares_correctly']=True
 changed=copy.deepcopy(cfg);changed['dataset_sha256']='different-data';(root/'second/config.json').write_text(json.dumps(changed))
 try:mod.compare('first','second')
 except ValueError:checks['different_dataset_rejected']=True
 else:raise AssertionError('Different dataset accepted')
 (root/'second/config.json').write_text(json.dumps(cfg));path=root/'second/per-task-analysis.json';data=json.loads(path.read_text());data[0]['prompt_sha256']='different-prompt';path.write_text(json.dumps(data))
 try:mod.compare('first','second')
 except AssertionError:checks['different_prompt_rejected']=True
 else:raise AssertionError('Different prompt accepted')
output={'software_only':True,'source':'Previously executed author software-probe-results.json; no generated code re-executed.','checks':checks,'same_evidence_comparison':report,'note':'The two fixture conditions contain identical software outcomes, not two model runs. Empty token arrays are placeholders.'}
p=S/'comparison-analysis-validation.json';assert not p.exists();p.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
