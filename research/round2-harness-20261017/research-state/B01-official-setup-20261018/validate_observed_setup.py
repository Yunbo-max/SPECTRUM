import hashlib,json
from pathlib import Path
from research_autopilot.b01_setup import validate_policy,context
root=Path('/root/rivermind-data/spectrum-harness/code-tests/b01-setup-observed-project')
def pin(name):return {'path':name,'sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()}
contract={'goal_id':'spectrum-round2','native_target_ref':pin('research-state/native-gpu-target-hn01-20261018.json'),'sequence':{'b01_setup_ref':pin('research-state/B01-official-setup-20261018/setup-policy.json')}}
project={'project_id':'spectrum-round2-work-harness','root':str(root)}
p=validate_policy(project,contract)
c=context(project,contract,{'id':'B01'})
assert c['mode']=='configuration_only' and p['report']['startup']['exit_code']==0
print(json.dumps({'actual_setup_report_validated':True,'policy_ref':p['reference'],'report_ref':p['report_ref'],'mode':c['mode'],'scoring_status':p['report']['scoring_status']},indent=2))
