"""One serial generation/evaluation condition, with exclusive lock and process logs."""
import argparse,datetime,fcntl,json,os,pathlib,subprocess,sys,time,shutil
S=pathlib.Path('/root/rivermind-data/spectrum-harness/project/research-state/ssd-author-comparison-20261019')
OLD=S.parent/'upstream-evaluation-20261018'
def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=['base','ssd'],required=True);p.add_argument('--temperature',type=float,required=True);a=p.parse_args()
    condition=S/f'{a.model}-temperature-{a.temperature}';condition.mkdir(exist_ok=True)
    with (OLD/'pipeline.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (condition/'pipeline-completed.json').exists():print('Completed condition preserved.');return
        stages=[('generate',[sys.executable,str(S/'generate_condition.py'),'--model',a.model,'--temperature',str(a.temperature),'--lock-fd',str(lock.fileno())]),('evaluate',[sys.executable,str(S/'isolate_ssd.py'),'--input',str(condition/'evaluation-input.json'),'--output',condition.name+'-results.json'])]
        for name,command in stages:
            if name=='generate' and (condition/'generation-completed.json').exists():continue
            if name=='evaluate' and (condition/'results.json').exists():continue
            attempt=len(list(condition.glob(name+'-attempt-*-exit.json')))+1
            prefix=condition/f'{name}-attempt-{attempt}'
            prefix.with_name(prefix.name+'-command.json').write_text(json.dumps(command,indent=2)+'\n')
            start=time.monotonic()
            with prefix.with_suffix('.log').open('a') as log:
                child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lock.fileno(),))
                (condition/'active-stage.json').write_text(json.dumps({'stage':name,'pid':child.pid,'proc_stat':pathlib.Path(f'/proc/{child.pid}/stat').read_text(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
                code=child.wait()
            prefix.with_name(prefix.name+'-exit.json').write_text(json.dumps({'returncode':code,'elapsed_seconds':time.monotonic()-start,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
            if code:raise RuntimeError(f'{name} failed with exit {code}; inspect preserved logs before retrying')
            if name=='evaluate':shutil.copy2(S/'evaluation-rootfs/work'/(condition.name+'-results.json'),condition/'results.json')
        (condition/'pipeline-completed.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'condition completed; research objective remains active'},indent=2)+'\n')
if __name__=='__main__':main()
