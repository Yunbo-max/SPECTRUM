"""Configuration/startup observation only; no candidate code or scoring is run."""
import hashlib, importlib, importlib.metadata, json, os, subprocess, sys, time
from pathlib import Path
root=Path('/root/rivermind-data/spectrum-harness')
sys.path.insert(0,str(root/'SPECTRUM/src'))
assets=json.loads((root/'setup/assets.json').read_text())
data=next(x for x in assets if x['repo_type']=='dataset')
model=next(x for x in assets if x['repo_type']=='model')
parquet=Path(data['path'])/'full/test-00000-of-00001.parquet'
import pyarrow.parquet as pq
rows=pq.read_table(parquet).to_pylist()
ids=[x['task_id'] for x in rows]
assert len(rows)==500 and sorted(ids)==list(range(11,511))
assert all(len(x['test_list'])==3 for x in rows)
modules={}
for name in ('torch','transformers','peft','accelerate','datasets','evalplus','improving.data','improving.verification'):
 m=importlib.import_module(name); f=Path(m.__file__); modules[name]={'path':str(f),'file_sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
env=dict(os.environ,PYTHONPATH=str(root/'SPECTRUM/src'))
help_result=subprocess.run([sys.executable,'-m','improving','--help'],env=env,capture_output=True,text=True,timeout=45)
assert help_result.returncode==0, help_result.stderr
print(json.dumps({'kind':'benchmark-setup-startup-observation','observed_at':time.time(),'interpreter':sys.executable,'packages':{n:importlib.metadata.version(n) for n in ('torch','transformers','peft','accelerate','datasets','evalplus')},'project_commit':subprocess.check_output(['git','-C',str(root/'SPECTRUM'),'rev-parse','HEAD'],text=True).strip(),'dataset':{**data,'config':'full','split':'test','count':len(rows),'ids':[min(ids),max(ids)],'parquet_sha256':hashlib.sha256(parquet.read_bytes()).hexdigest(),'setup_task_ids':[x['task_id'] for x in rows if x.get('test_setup_code','').strip()]},'model':{**model,'config_present':(Path(model['path'])/'config.json').is_file(),'weight_files':[p.name for p in Path(model['path']).glob('*.safetensors')]},'modules':modules,'cli':{'argv':[sys.executable,'-m','improving','--help'],'exit_code':help_result.returncode,'stdout':help_result.stdout},'scoring_executed':False,'candidate_code_executed':False,'scoring_status':'pending'},indent=2))
