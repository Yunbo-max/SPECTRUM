import os,sys,json,time,subprocess,traceback
from pathlib import Path
r=Path('/root/rivermind-data/spectrum-harness');s=r/'setup';started=time.time()
record={'pid':os.getpid(),'started_at':started,'status':'running'}
(s/'environment-status.json').write_text(json.dumps(record))
try:
 cmd=[str(r/'venv/bin/python'),'-m','pip','install','--no-cache-dir','--index-url','https://pypi.tuna.tsinghua.edu.cn/simple','torch==2.7.1','transformers==4.51.3','peft==0.15.2','accelerate==1.6.0','datasets==3.5.1','evalplus==0.3.1','pytest>=8,<9','-e',str(r/'SPECTRUM')]
 result=subprocess.run(cmd,timeout=2400)
 if result.returncode:raise RuntimeError('dependency install exit '+str(result.returncode))
 record['dependencies_exit_code']=result.returncode
 env=os.environ.copy();env.update(HF_ENDPOINT='https://hf-mirror.com',HF_HOME=str(r/'cache/huggingface'),HF_HUB_DISABLE_XET='1')
 download='''
import json
from pathlib import Path
from huggingface_hub import snapshot_download
items=[]
for repo,kind,rev in [('Qwen/Qwen2.5-Coder-1.5B-Instruct','model','2e1fd397ee46e1388853d2af2c993145b0f1098a'),('google-research-datasets/mbpp','dataset','4bb6404fdc6cacfda99d4ac4205087b89d32030c')]:
 path=snapshot_download(repo,repo_type=kind,revision=rev,max_workers=2)
 items.append(dict(repo_id=repo,repo_type=kind,revision=rev,path=path))
 Path('/root/rivermind-data/spectrum-harness/setup/assets.json').write_text(json.dumps(items,indent=2))
 print(repo,rev,path,flush=True)
'''
 result=subprocess.run([str(r/'venv/bin/python'),'-c',download],env=env,timeout=2400)
 record['assets_exit_code']=result.returncode
 if result.returncode:raise RuntimeError('asset download failed')
 record['status']='completed'
except Exception:
 record.update(status='failed',error=traceback.format_exc())
finally:
 record['finished_at']=time.time();(s/'environment-status.json').write_text(json.dumps(record,indent=2))
