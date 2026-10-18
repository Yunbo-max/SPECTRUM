import copy,io,json,sqlite3,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from research_autopilot import prompt_experiments as m
with tempfile.TemporaryDirectory() as td:
 root=Path(td);(root/'instruction.md').write_text('Run existing experiment directly.');(root/'agents.json').write_text(json.dumps({'adapters':{'codex-local':{'argv':['codex','exec','--output-schema','OLD']}}}))
 db=sqlite3.connect(root/'state.db');db.executescript('CREATE TABLE tasks(project_id TEXT,state TEXT); CREATE TABLE projects(project_id TEXT,spent_seconds REAL); INSERT INTO projects VALUES("p",12);');db.commit();db.close()
 project={'root':str(root),'limits':{'max_seconds':None}}
 class C:
  def get_project(self,p):return project
  def _connect(self):return sqlite3.connect(root/'state.db')
 class P:
  def __init__(self):self.s={'state':{'phase':'active','experiment_autonomy':{'enabled':True,'instruction_ref':{'path':'instruction.md'},'model':'gpt-6-astra'}},'contract':{'agent_config_ref':{'path':'agents.json'},'planner':{'adapter':'codex-local'}}}
  def status(self,p):return copy.deepcopy(self.s)
  def _policy(self,*args):pass
  def _update(self,prior,state,kind):self.s['state']=copy.deepcopy(state);return self.status('p')
 p=P();calls=[]
 def spawn(argv,**kw):
  calls.append(argv);kw['stdout'].write(b'{"type":"thread.started","thread_id":"example-thread"}\n');kw['stdout'].flush()
  return SimpleNamespace(pid=123,stdin=io.BytesIO(),poll=lambda:0,returncode=0)
 args=SimpleNamespace(project='p',command='run',max_ticks=1);lease=SimpleNamespace(observed=lambda s:None)
 with patch.object(m,'verify_ref',lambda root,ref:root/ref['path']),patch.object(m.subprocess,'Popen',spawn):
  assert m.run(C(),p,args,lease)==0
  assert p.s['state']['experiment_autonomy']['thread_id']=='example-thread'
  assert '--output-schema' not in calls[0] and 'resume' not in calls[0]
  p.s['state']['experiment_autonomy']['not_before']=0
  assert m.run(C(),p,args,lease)==0
  assert 'resume' in calls[1] and 'example-thread' in calls[1]
  assert '--output-schema' not in calls[1]
  assert p.s['state']['experiment_autonomy']['attempt']==2
  p.s['state']['phase']='paused';assert m.run(C(),p,args,lease)==0;assert len(calls)==2
 assert not m.enabled({'state':{}})
 print('PASS: fresh unconstrained session, same-thread continuation, explicit pause, legacy mode unaffected. Mocked process, no model/GPU science results.')
