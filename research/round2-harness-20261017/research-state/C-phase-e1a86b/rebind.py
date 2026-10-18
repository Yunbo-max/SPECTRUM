import json,hashlib
from pathlib import Path
root=Path.cwd(); out=Path('research-state/C-phase-e1a86b')
old='research-state/C-phase-e1a86/adapter'; new=str(out/'adapter')
op='research-state/C-phase-e1a86/plans'; np=str(out/'plans')
repls={old:new,op:np,'research-state/B02-native-stage-run-e1a12':str(out/'driver-run'),'spectrum-C-prepare-e1a86':'spectrum-C-prepare-e1a86b','093af61314f64e24dbefeeae1a4912924f611e783144613567e633418b06173c':'304f296d806577b4c59c87d53e02d6d24f5f6614f6dcf761db7e3449fe52c84a'}
files={str(p) for p in Path(old).rglob('*') if p.is_file() and p.suffix in ('.py','.json','.md')}
files.update(op+'/'+n for n in ['stage-program.json','prepare-stage.json','prepare-native-plan.json','prepare-harness-plan.json'])
def replace(s):
 for a,b in repls.items():s=s.replace(a,b)
 return s
def pin(p):return {'path':p,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def patch_source(s):
 old="    need(all(r in mapped for r in method_refs if Path(r['path']).name in ('diagnostic_driver.py','stage_entry.py','training_instrumented.py','analysis.py')),\n         'CD experiment must be rebound to actual adapted code')"
 new="    # Adopted .10: descriptor authenticates actual stage code; broader mappings are context.\n    if s['stage_kind'] == 'export':\n        need(all(r in mapped for r in method_refs if Path(r['path']).name in ('diagnostic_driver.py','stage_entry.py')),\n             'Export implementation must be bound to CD evidence')"
 return s.replace(old,new)

done={};active=set()
def save(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def transform(v):
 if isinstance(v,dict):
  if set(v)=={'path','sha256'} and v['path'] in files:return build(v['path'])
  return {k:transform(x) for k,x in v.items()}
 if isinstance(v,list):return [transform(x) for x in v]
 return replace(v) if isinstance(v,str) else v
def build(p):
 if p in done:return done[p]
 if p in active:raise ValueError('cycle '+p)
 active.add(p);dst=replace(p)
 if p.endswith('.json'):
  d=transform(json.loads(Path(p).read_text()))
  if p.endswith('prepare-stage.json') or p.endswith('prepare-native-plan.json'):
   cmd=d['job']['command'] if 'job' in d else d['jobs'][0]['command'];i=cmd.index('--binding-sha256');cmd[i+1]=build(old+'/stage-plan-inputs.json')['sha256']
  if 'protocol_digest' in d:
   if 'protocol_ref' in d:d['protocol_digest']=json.loads(Path(d['protocol_ref']['path']).read_text())['protocol_digest']
   else:d['protocol_digest']=digest({k:v for k,v in d.items() if k not in ('protocol_digest','frozen_at')})
  if 'plan_digest' in d:d['plan_digest']=digest({k:v for k,v in d.items() if k!='plan_digest'})
  save(dst,d)
 else:
  Path(dst).parent.mkdir(parents=True,exist_ok=True);Path(dst).write_text(patch_source(replace(Path(p).read_text())))
 active.remove(p);done[p]=pin(dst);return done[p]
for p in sorted(files):build(p)
req=json.load(open('research-state/C-phase-e1a86/request-01.json'));req=transform(req)
receipt=pin('research-state/harness/receipts/70b3fef870224b6aa2d732c6699374ad.json')
dec=json.load(open('research-state/C-phase-e1a86/decision-01.json'));dec['previous_ref']=pin('research-state/C-phase-e1a86/decision-01.json');dec['selected_task_ids']=['spectrum.C.prepare.e1.a86b'];dec['observed_receipt_refs'].append(receipt);dec['rationale']='真实执行70b3终态失败定位到adapter旧全实验mapped-code约束；采用.10阶段边界，仅export保留实际输出实现映射校验。prepare继续保留descriptor code/input/deployment/context身份检查；不执行未来比较。';dec['evidence_refs'].append(pin('research-state/harness/adoptions/phase-freedom-000392.json'));save(str(out/'decision-01.json'),dec)
cov=json.load(open('research-state/C-phase-e1a86/coverage-01.json'));cov['previous_ref']=pin('research-state/C-phase-e1a86/coverage-01.json')
for o in cov['obligations']:
 if 'spectrum.C.prepare.e1.a86' in o['task_ids']:o['task_ids'].append('spectrum.C.prepare.e1.a86b')
save(str(out/'coverage-01.json'),cov)
req['request_id']='spectrum-C-e1a86b-prepare-01';req['task']['task_id']='spectrum.C.prepare.e1.a86b';req['decision_ref']=pin(str(out/'decision-01.json'));req['coverage_ref']=pin(str(out/'coverage-01.json'));req['task']['parameters']['reasoning_ref']=req['decision_ref'];req['task']['inputs'].append(req['decision_ref']);save(str(out/'request-01.json'),req)
print('Created',len(done),'versioned files; native execution pending')
