import json,hashlib
from pathlib import Path
O=Path('research-state/C-phase-e1a86b')
def read(p):return json.loads(Path(p).read_text())
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def save(p,d):Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');return pin(p)
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
rid='spectrum-C-freeze-e1a86b';tid='spectrum.C.freeze.e1.a86b';rr=pin('research-state/harness/receipts/a5b3c5086b304e4ab2e3ab4e79446e0a.json')
s=read(O/'plans/calibrate64-stage.json');s.update(stage_id='freeze-profile',stage_kind='prepare',required_predecessor_ids=['prepare','calibrate-inference-64']);s['predecessor_receipt_refs'].append(rr);j=s['job'];j['trial_id']='freeze';j['command']=[x.replace('calibrate-inference','freeze-profile') for x in j['command']];j['output_paths']=[p.replace('spectrum-C-calibrate64-e1a86b',rid) for p in j['output_paths']];j['input_refs'] += [rr,pin('runs/stage-outputs/spectrum-C-calibrate64-e1a86b/stage-summary.json')];sr=save(O/'plans/freeze-stage.json',s)
n=read(O/'plans/calibrate64-native-plan.json');n.update(run_id=rid,jobs=[j]);n['provenance']['native_stage_ref']=sr;n['plan_digest']=digest({k:v for k,v in n.items() if k!='plan_digest'});nr=save(O/'plans/freeze-native-plan.json',n)
h=read(O/'plans/prepare-harness-plan.json');h['batch_id']=rid;h['tasks'][0].update(task_id='freeze',plan_ref=nr);h['plan_digest']=digest({k:v for k,v in h.items() if k!='plan_digest'});hr=save(O/'plans/freeze-harness-plan.json',h)
d=read(O/'decision-02.json');d.update(previous_ref=pin(O/'decision-02.json'),selected_task_ids=[tid],rationale='真实batch64资源校准eligible，固定该操作批量避免无依据重复更小batch；仅资源profile，不是E科学freeze或评分资格。');d['observed_receipt_refs'].append(rr);dr=save(O/'decision-03.json',d)
c=read(O/'coverage-02.json');c['previous_ref']=pin(O/'coverage-02.json')
for ob in c['obligations']:
 if 'spectrum.C.calibrate64.e1.a86b' in ob['task_ids']:ob['task_ids'].append(tid)
cr=save(O/'coverage-03.json',c)
r=read(O/'request-03.json');t=r['task'];t['task_id']=tid;t['inputs']=list({p['path']:p for p in j['input_refs']+j['code_refs']+[sr,nr,hr,dr,pin('research-state/native-gpu-target-hn01-20261018.json')]}.values());t['outputs']=j['output_paths']+['runs/attempts/'+rid+'/receipt.json'];t['parameters'].update(harness_plan_ref=hr,reasoning_ref=dr);r.update(request_id='spectrum-C-e1a86b-freeze',decision_ref=dr,coverage_ref=cr);save(O/'request-04.json',r)
