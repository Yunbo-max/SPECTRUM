"""Quiet owner-authorized .14 adoption, retaining scientific history and budgets."""
import copy,json,sqlite3,sys,time
from contextlib import closing
from pathlib import Path
from research_autopilot.controller import Controller
from research_autopilot.program import ResearchProgram,save_artifact
from research_autopilot.artifacts import canonical_json,digest_tree,pin_file,contract_hash
from research_autopilot.models import validate_project
from research_autopilot import cd_flow,skill_sequence
root=Path(__file__).resolve().parents[1];source=Path(sys.argv[1]).resolve();revision=sys.argv[2]
c=Controller(root/'runtime/controller.sqlite');p=ResearchProgram(c);pid='spectrum-round2-work-harness'
prior=p.status(pid);old=c.get_project(pid);state=copy.deepcopy(prior['state']);config=copy.deepcopy(prior['contract'])
previous_revision=prior['revision'];next_revision=previous_revision+1
assert state['phase']=='paused' and state['sequence']['step_id']=='B02'
observed=c.status(pid);assert not any(t['state'] not in {'completed','failed','cancelled'} for t in observed['tasks'])
p._snapshot(old,observed)
new=copy.deepcopy(old);new['skill_root']=str(source/'skills/research-autopilot');new['skill_digest']=digest_tree(new['skill_root']);new=validate_project(new)
marker=json.loads((Path(new['skill_root'])/'assets/harness-policy.json').read_text());assert marker['version']=='0.4.0-harness.14'
config['policy']={'edition':marker['edition'],'version':marker['version'],'source_revision':revision,'skill_digest':new['skill_digest']}
p._policy(new,config);catalog,step=skill_sequence._cursor(new,{'state':state,'contract':config})
assert step['milestone_ids']==['B02','B03','B04','B05']
backup=root/'runtime/controller.before-export-metadata-source-20261018.sqlite';assert not backup.exists()
with closing(c._connect()) as src,closing(sqlite3.connect(backup)) as dst:src.backup(dst)
ref=save_artifact(old['root'],f'research-state/harness/adoptions/export-metadata-{next_revision:06d}.json',{
 'kind':'research-source-adoption','schema_version':1,'previous_project':old,'adopted_project':new,
 'previous_contract':prior['contract'],'adopted_contract':config,'previous_state':prior['state'],
 'previous_revision':previous_revision,'revision':next_revision,'source_revision':revision,
 'instruction_ref':pin_file(old['root'],'research-state/export-metadata-installed-resume-20261018.md'),
 'reason':'Owner-approved export-metadata B/C/D/E scientific selection; preserve all actual research history, target and budgets'})
cd_flow.reset_transport(state);state.update(not_before=0,reason='Legacy export metadata compatibility installed/adopted; resume under owner instruction',runtime_source_adoption_ref=ref)
state['sequence']['result_ref']=None;state['sequence']['inspect_task_ids']=[];state['sequence']['inspection_refs']=[]
with c._transaction() as db:
 actual=db.execute('SELECT contract,state,revision FROM research_programs WHERE project_id=?',(pid,)).fetchone()
 assert actual['revision']==previous_revision and json.loads(actual['state'])==prior['state'] and json.loads(actual['contract'])==prior['contract']
 assert c._project(db,pid)[1]==old
 for table in ('tasks','runs'):
  assert not db.execute(f"SELECT 1 FROM {table} WHERE project_id=? AND state NOT IN ('completed','failed','cancelled')",(pid,)).fetchone()
 db.execute('UPDATE projects SET contract=?,digest=? WHERE project_id=?',(canonical_json(new),contract_hash(new),pid))
 db.execute('UPDATE research_programs SET contract=?,state=?,revision=? WHERE project_id=?',(canonical_json(config),canonical_json(state),next_revision,pid))
 db.execute('INSERT INTO research_program_events VALUES(?,?,?,?,?)',(pid,next_revision,'export_metadata_source_adopted',canonical_json(state),time.time()))
receipt={'kind':'export-metadata-live-adoption','version':marker['version'],'source_revision':revision,'skill_digest':new['skill_digest'],'adoption_ref':ref,'revision':next_revision,'phase':state['phase'],'budget_preserved':c.status(pid)['budget']==observed['budget'],'accepted_evidence_preserved':state['sequence']['accepted']==prior['state']['sequence']['accepted']}
assert receipt['budget_preserved'] and receipt['accepted_evidence_preserved']
(root/'ops/export-metadata-live-adoption-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(root/'project/program.export-metadata-20261018.json').write_text(json.dumps(config,indent=2)+'\n')
print(json.dumps(receipt))
