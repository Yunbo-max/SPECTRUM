import hashlib,json,shutil,subprocess
from pathlib import Path
r=Path(__file__).resolve().parents[1];source=r/'source-export-metadata-v1';market=Path('/Users/yunbo/.codex/local-marketplaces/research-autopilot-six/plugins');target=market/'research-autopilot-harness'
others={str(p.relative_to(market)):hashlib.sha256(p.read_bytes()).hexdigest() for p in market.glob('*/.codex-plugin/plugin.json') if p.parent.parent!=target}
# Explicit source-owned files; preserve the local marketplace identity overlay.
for name in ('skills','.codex-plugin','plugin.json','EDITION.json','SOURCE_PUBLICATION.json','EXPORT_MANIFEST.json'):
 src=source/name;dst=target/name
 if src.is_dir():shutil.copytree(src,dst,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 else:shutil.copy2(src,dst)
for name in ('.codex-plugin/plugin.json','plugin.json'):
 p=target/name;v=json.loads(p.read_text());v['name']='research-autopilot-harness'
 if 'interface' in v:v['interface']['displayName']='Autopilot Harness'
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
assert all(hashlib.sha256((market/k).read_bytes()).hexdigest()==v for k,v in others.items())
(r/'ops/export-metadata-install-before.json').write_text(json.dumps({'other_plugin_manifests':others},indent=2)+'\n')
print('Updated only the local Harness marketplace source; official installation is next.')
