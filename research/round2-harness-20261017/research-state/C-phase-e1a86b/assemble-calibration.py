import json,hashlib,copy
from pathlib import Path
O=Path('research-state/C-phase-e1a86b')
def read(p):return json.loads(Path(p).read_text())
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def save(p,d):Path(p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n');return pin(p)
def digest(d):return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
rid='spectrum-C-calibrate64-e1a86b';tid='spectrum.C.calibrate64.e1.a86b'
rr=pin('research-state/harness/receipts/8a95ed560f384e939ea5d8b5948e6afd.json')
s=read(O/'plans/prepare-stage.json');s.update(stage_id='calibrate-inference-64',stage_kind='calibrate',predecessor_receipt_refs=[rr],required_predecessor_ids=['prepare'],selection_metric='resource_memory')
j=s['job'];j['trial_id']='calibrate64';j['command']=j['command'][:-1]+['calibrate-inference','--batch','64'];j['output_paths']=[p.replace('spectrum-C-prepare-e1a86b',rid) for p in j['output_paths'][:18]]
for p in ['stage-summary.json','calibration.jsonl','base-assets.json']:
 j['input_refs'].append(pin('runs/stage-outputs/spectrum-C-prepare-e1a86b/'+p))
j['input_refs'].append(rr)
sr=save(O/'plans/calibrate64-stage.json',s)
n=read(O/'plans/prepare-native-plan.json');n.update(run_id=rid,jobs=[j]);n['provenance']['native_stage_ref']=sr;n['plan_digest']=digest({k:v for k,v in n.items() if k!='plan_digest'});nr=save(O/'plans/calibrate64-native-plan.json',n)
h=read(O/'plans/prepare-harness-plan.json');h['batch_id']=rid;h['tasks'][0].update(task_id='calibrate64',plan_ref=nr);h['tasks'][0]['resources'].update(gpu_count=1,gpu_peak_mib=22000,ram_mib=8192);h['limits'].update(ram_mib=8192,max_gpu_task_seconds=1020);h['gpus']['uuids']=[];h['plan_digest']=digest({k:v for k,v in h.items() if k!='plan_digest'});hr=save(O/'plans/calibrate64-harness-plan.json',h)
d=read(O/'decision-01.json');d.update(previous_ref=pin(O/'decision-01.json'),selected_task_ids=[tid],rationale='prepare真实完成并归档，物化291/50/30/500；在同一固定模型与原生输入上从64开始测生成资源，非科学比较、不选择旧F/P/A。');d['observed_receipt_refs'].append(rr);d['evidence_refs'] += [pin('runs/stage-outputs/spectrum-C-prepare-e1a86b/stage-summary.json')];dr=save(O/'decision-02.json',d)
c=read(O/'coverage-01.json');c['previous_ref']=pin(O/'coverage-01.json')
for ob in c['obligations']:
 if 'spectrum.C.prepare.e1.a86b' in ob['task_ids']:ob['task_ids'].append(tid)
cr=save(O/'coverage-02.json',c)
r=read(O/'request-01.json');t=r['task'];t['task_id']=tid;t['inputs']=list({p['path']:p for p in j['input_refs']+j['code_refs']+[sr,nr,hr,dr,pin('research-state/native-gpu-target-hn01-20261018.json')]}.values());t['outputs']=j['output_paths']+['runs/attempts/'+rid+'/receipt.json'];t['parameters'].update(harness_plan_ref=hr,reasoning_ref=dr);r.update(request_id='spectrum-C-e1a86b-calibrate64',decision_ref=dr,coverage_ref=cr);save(O/'request-02.json',r)
print('calibration request authored; actual execution pending')
