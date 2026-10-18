"""Serial execution of the Qwen-author MBPP commands with pinned EvalPlus."""
import datetime
import fcntl
import json
import os
import pathlib
import subprocess
import time

ROOT=pathlib.Path('/root/rivermind-data/spectrum-harness/project')
STATE=ROOT/'research-state/upstream-evaluation-20261018'
PY='/root/rivermind-data/spectrum-harness/venv/bin/python'
MODEL='/root/rivermind-data/spectrum-harness/cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-1.5B-Instruct/snapshots/2e1fd397ee46e1388853d2af2c993145b0f1098a'
OUT=STATE/'official-qwen-greedy'
RAW=OUT/'mbpp/qwen2_chat_temp_0.0'
SANITIZED=RAW.with_name(RAW.name+'-sanitized')
ENV={**os.environ,'HF_ENDPOINT':'https://hf-mirror.com','HF_HOME':'/root/rivermind-data/spectrum-harness/cache/huggingface',
     'PYTHONPATH':str(STATE/'eval-deps')+':'+str(ROOT/'upstreams/evalplus'),
     'SPECTRUM_GENERATION_LOG':str(STATE/'generation-engine-raw.jsonl'),
     'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','VLLM_NO_USAGE_STATS':'1','DO_NOT_TRACK':'1'}
COMMANDS=[
 ('generate',[PY,'-u',str(STATE/'qwen-execution/generate.py'),'--model_type','qwen2','--model_size','chat','--model_path',MODEL,'--bs','1','--temperature','0','--n_samples','1','--greedy','--root',str(OUT),'--dataset','mbpp','--tensor-parallel-size','1','--resume']),
 ('sanitize',[PY,'-u','-m','evalplus.sanitize','--samples',str(RAW)]),
 ('evaluate-raw',[PY,'-u',str(STATE/'isolate_upstream.py'),'--rootfs',str(STATE/'evaluation-rootfs'),'--samples',str(RAW)]),
 ('evaluate-sanitized',[PY,'-u',str(STATE/'isolate_upstream.py'),'--rootfs',str(STATE/'evaluation-rootfs'),'--samples',str(SANITIZED)]),
]

def main():
    with (STATE/'pipeline.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for stage,command in COMMANDS:
            if (STATE/(stage+'-exit.json')).exists():
                prior=json.loads((STATE/(stage+'-exit.json')).read_text())
                if prior['returncode']==0:
                    print('Reuse completed stage',stage,flush=True)
                    continue
                raise RuntimeError('Prior failed stage requires inspection: '+stage)
            (STATE/(stage+'-command.json')).write_text(json.dumps(command,indent=2)+'\n')
            started=time.monotonic()
            with (STATE/'logs'/(stage+'.log')).open('x') as log:
                p=subprocess.Popen(command,cwd=ROOT,env=ENV,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
                identity={'pid':p.pid,'proc_stat':pathlib.Path('/proc/'+str(p.pid)+'/stat').read_text(),'stage':stage,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
                (STATE/'active-stage.json').write_text(json.dumps(identity,indent=2)+'\n')
                print('Started',stage,p.pid,flush=True)
                code=p.wait()
            result={'stage':stage,'returncode':code,'elapsed_seconds':time.monotonic()-started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
            (STATE/(stage+'-exit.json')).write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(result),flush=True)
            if code:raise RuntimeError('Stage failed: '+stage)
        (STATE/'pipeline-completed.txt').write_text(datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n')

if __name__=='__main__':main()
