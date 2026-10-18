import ast,json,subprocess,shlex
from pathlib import Path
src=Path('/Users/yunbo/Documents/ssdforever/harness-runs/spectrum-round2-20261017/source-freedom-v1/src/research_autopilot/remote.py').read_text()
vals={}
for n in ast.parse(src).body:
 if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('BOOTSTRAP','PROBE_BODY'):vals[n.targets[0].id]=ast.literal_eval(n.value)
x=json.load(open('research-state/C-phase-e1a84/mailbox-result-01.json'))
identity=x['attempt']['session_id']
r=subprocess.run(['ssh','-oBatchMode=yes','-oConnectTimeout=15','spectrum-harness-gpu-hn01',shlex.join(['/opt/conda/bin/python','-',identity])],input=vals['BOOTSTRAP']+vals['PROBE_BODY'],capture_output=True,text=True,timeout=45)
out={'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
Path('research-state/C-phase-e1a84/remote-observation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
