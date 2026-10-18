"""Test a minimal, explicitly separate repair to upstream sanitizer function retention."""
import fcntl
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT=pathlib.Path('/root/rivermind-data/spectrum-harness/project')
S=ROOT/'research-state/upstream-evaluation-20261018'
D=S/'sanitizer-helper-diagnostic'
PY='/root/rivermind-data/spectrum-harness/venv/bin/python'

def main():
    assert (S/'pipeline-completed.txt').exists(), 'Finish official run first'
    with (S/'pipeline.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert not (D/'exit.json').exists()
        sys.path[:0]=[str(S/'eval-deps'),str(ROOT/'upstreams/evalplus')]
        spec=importlib.util.spec_from_file_location('sanitize_keep_helpers',D/'sanitize_keep_helpers.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        raw=S/'official-qwen-greedy/mbpp/qwen2_chat_temp_0.0'
        alias=raw.with_name('qwen2_chat_temp_0.0-keep-helpers')
        alias.symlink_to(raw,target_is_directory=True)
        module.script(samples=str(alias))
        patched=alias.with_name(alias.name+'-sanitized')
        command=[PY,'-u',str(S/'isolate_upstream.py'),'--rootfs',str(S/'evaluation-rootfs'),'--samples',str(patched)]
        (D/'evaluate-command.json').write_text(json.dumps(command,indent=2)+'\n')
        start=time.monotonic()
        code=subprocess.call(command,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
        (D/'exit.json').write_text(json.dumps({'returncode':code,'elapsed_seconds':time.monotonic()-start},indent=2)+'\n')
        assert code==0
        p=S/'evaluation-rootfs/work'/patched.name/'eval_results.json'
        (D/'eval_results.json').write_bytes(p.read_bytes())
        repaired=json.loads(p.read_text())['eval']
        original=json.loads((S/'evaluation-rootfs/work/qwen2_chat_temp_0.0-sanitized/eval_results.json').read_text())['eval']
        assert set(repaired)==set(original) and len(repaired)==378
        changed={k:{'original':original[k][0],'repaired':repaired[k][0]} for k in repaired if any(original[k][0][m]!=repaired[k][0][m] for m in ['base_status','plus_status'])}
        summary={'scope':'Diagnostic upstream sanitizer repair, not the original official result',
                 'tasks':len(repaired),'base_passed':sum(v[0]['base_status']=='pass' for v in repaired.values()),
                 'plus_passed':sum(v[0]['base_status']==v[0]['plus_status']=='pass' for v in repaired.values()),
                 'changed_outcome_tasks':changed}
        (D/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
