import hashlib,json,sys
from pathlib import Path
r=Path(__file__).resolve().parents[1];source=r/'source-question-led-v1';version='0.4.0-harness.12'
import research_autopilot
installed=Path(research_autopilot.__file__).parent
count=0
for p in (source/'src/research_autopilot').rglob('*.py'):
 assert p.read_bytes()==(installed/p.relative_to(source/'src/research_autopilot')).read_bytes(),p.name
 count+=1
profiles=[]
for name,home in [('main',Path('/Users/yunbo/.codex')),('private',r/'codex-profile')]:
 cache=home/'plugins/cache/research-autopilot-six/research-autopilot-harness'/version
 marker=json.loads((cache/'.codex-plugin/plugin.json').read_text());assert marker['version']==version
 n=0
 for p in (source/'skills').rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}:
   assert p.read_bytes()==(cache/p.relative_to(source)).read_bytes(),str(p)
   n+=1
 profiles.append({'profile':name,'version':version,'files_verified':n})
wheel=r/'artifacts/question-led-selection/research_autopilot_runtime-0.4.0a2-py3-none-any.whl'
value={'runtime_modules_verified':count,'profiles':profiles,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest()}
(r/'ops/question-led-install-receipt.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
