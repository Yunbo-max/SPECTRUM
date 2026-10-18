import copy,json,sqlite3,subprocess
from contextlib import closing
from pathlib import Path
from research_autopilot.controller import Controller
from research_autopilot.program import ResearchProgram
from research_autopilot.artifacts import pin_file,digest_tree,canonical_json,contract_hash
from research_autopilot.models import validate_project
r=Path(__file__).resolve().parents[1];source=r/'source-experiment-autonomy-v1';pid='spectrum-round2-work-harness';c=Controller(r/'runtime/controller.sqlite');p=ResearchProgram(c);prior=p.status(pid);old=c.get_project(pid)
assert prior['state']['phase']=='paused'
with closing(c._connect()) as db:
 assert not db.execute("SELECT 1 FROM tasks WHERE project_id=? AND state NOT IN ('completed','failed','cancelled')",(pid,)).fetchone()
 with closing(sqlite3.connect(r/'runtime/controller.before-supervised-experiments-20261018.sqlite')) as backup:db.backup(backup)
state=copy.deepcopy(prior['state']);config=copy.deepcopy(prior['contract']);project=copy.deepcopy(old)
project['skill_root']=str(source/'skills/research-autopilot');project['skill_digest']=digest_tree(project['skill_root']);project=validate_project(project)
rev=subprocess.check_output(['git','-C',str(r/'b01-setup'),'rev-parse','HEAD'],text=True).strip()
config['policy']={'edition':'autonomous-rsi-harness','version':'0.4.0-harness.16','source_revision':rev,'skill_digest':project['skill_digest']};p._policy(project,config)
ref=pin_file(old['root'],'research-state/restore-harness-experiment-autonomy-20261018.md')
state['experiment_autonomy']={'enabled':True,'scope':'BCDE','model':'gpt-6-astra','instruction_ref':ref,'attempt':0,'elapsed_seconds':0,'status':'ready','legacy_stage':state['stage'],'legacy_planner_task_id':state.get('planner_task_id')}
state.update(stage='experiment_autonomy',not_before=0,reason='Owner correction: retain Harness lifecycle; autonomous experimental design and execution')
with c._transaction() as db:
 actual=db.execute('SELECT revision FROM research_programs WHERE project_id=?',(pid,)).fetchone();assert actual[0]==prior['revision']
 db.execute('UPDATE projects SET contract=?,digest=? WHERE project_id=?',(canonical_json(project),contract_hash(project),pid))
 db.execute('UPDATE research_programs SET contract=? WHERE project_id=?',(canonical_json(config),pid))
# Preserve all old sequence acceptance and budgets; transition through normal event history.
p._update(prior,state,'experiment_autonomy_adopted')
result=p.resume(pid,ref)
(r/'ops/experiment-supervisor-adoption.json').write_text(json.dumps({'source_revision':rev,'policy':config['policy'],'revision':result['revision'],'phase':result['state']['phase'],'mode':result['state']['stage'],'legacy_sequence_step':state['sequence']['step_id'],'instruction_ref':ref,'prior_revision':prior['revision']},indent=2)+'\n')
print(json.dumps({'revision':result['revision'],'phase':result['state']['phase'],'mode':result['state']['stage']}))
