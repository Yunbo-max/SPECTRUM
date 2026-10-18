"""Read real retained data with isolated maintenance code; no scoring claims."""
import copy,json,sys,hashlib
from pathlib import Path
sys.path.insert(0,'/root/rivermind-data/spectrum-harness/code-tests/export-metadata-repair/skills/research-autopilot/scripts')
import native_stages as NS
import _native_eval as N
import _autoresearch as C
root=Path('/root/rivermind-data/spectrum-harness/project')
out=root/'research-state/export-metadata-maintenance-20261018';out.mkdir(exist_ok=True)
def pin(path):return C.reference(root,path)
def put(name,value):
 p=out/name;p.write_text(json.dumps(value,indent=2)+'\n');return pin(p)
gref=pin(root/'research-state/C-phase-e1a87/export-program.json');sref=pin(root/'research-state/C-phase-e1a87/stage-05.json')
g=NS.read(root,gref);stage=NS.read(root,sref);c=g['native_eval_contract']
pred=pin(root/'runs/stage-outputs/spectrum-C-base-export-e1a87/predictions.jsonl')
assert pred['sha256']=='6b103c3a5855a195f9df478d6297970a4044f1048662fc19684b80cf016ab7f8'
m=NS.read(root,c['sample_manifest_ref']);old=copy.deepcopy(m)
for k in ['benchmark_id','benchmark_revision','split','labels_or_tests_ref','sampling','budget']:m.setdefault(k,c[k])
m['denominator_rule']='sample_count';m.setdefault('denominator',len(m['sample_ids']))
mref=put('completed-manifest.json',m)
s=copy.deepcopy(g);s.update(native_stage_program_ref=gref,native_stage_exports=[{'native_stage_ref':sref,'execution_bindings':stage['execution_bindings']}])
f=s['native_eval_contract'];f['sample_manifest_ref']=mref;f.pop('selection',None);f['contrasts']['baseline']=c['arm_requirements']['baseline']['name'];s['contrasts']=copy.deepcopy(f['contrasts']);s['protocol_digest']=C.protocol_hash(s)
ref=put('compatibility-probe-protocol.json',s)
assert NS.matches_scored_protocol(root,gref,ref,sref)
samples=N._samples(root,f);N._prediction_ids(root,f,{'predictions_ref':pred},samples)
assert old['sample_ids']==m['sample_ids'] and old['predictions_per_sample']==m['predictions_per_sample']
assert pin(root/pred['path'])==pred
v={'scope':'real export metadata equivalence and prediction identity checks; not scorer qualification or model scoring','compatible':True,'samples':len(samples['sample_ids']),'predictions_per_sample':samples['predictions_per_sample'],'predictions_ref':pred,'generation_ref':gref,'stage_ref':sref,'old_manifest_ref':c['sample_manifest_ref'],'new_manifest_ref':mref,'probe_protocol_ref':ref,'scientific_verified':False}
put('probe-result.json',v);print(json.dumps(v))
