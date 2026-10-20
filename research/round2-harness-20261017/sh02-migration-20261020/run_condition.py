"""Serial SH02 generation then upstream isolated evaluation; durable attempts."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from generate_condition import atomic_json, STATE, SOURCE

def identity(pid):
    return dict(pid=pid, proc_stat=pathlib.Path(f'/proc/{pid}/stat').read_text(),
                boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                utc=datetime.datetime.now(datetime.timezone.utc).isoformat())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['base', 'ssd'], required=True)
    parser.add_argument('--temperature', type=float, required=True)
    parser.add_argument('--max-tokens', type=int, required=True)
    parser.add_argument('--max-model-len', type=int, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--smoke-tasks', type=int, default=0)
    args = parser.parse_args()
    assert pathlib.Path(args.name).name == args.name
    condition = STATE/args.name
    condition.mkdir(exist_ok=True)
    with (STATE/'pipeline.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        history = condition/'launches'
        history.mkdir(exist_ok=True)
        atomic_json(history/f'{time.time_ns()}-process.json', identity(os.getpid()))
        atomic_json(condition/'process.json', identity(os.getpid()))
        generation = [sys.executable, '-u', str(STATE/'generate_condition.py')]
        for key, value in vars(args).items():
            generation += ['--'+key.replace('_', '-'), str(value)]
        generation += ['--lock-fd', str(lock.fileno())]
        # Always validate/reconstruct from committed samples; cached samples require no GPU.
        for stage in ('generate', 'evaluate'):
            attempt = len(list(condition.glob(stage+'-attempt-*-command.json')))+1
            prefix = condition/f'{stage}-attempt-{attempt}'
            if stage == 'generate':
                command = generation
            else:
                generated = json.loads((condition/'generation-completed.json').read_text())
                input_hash = hashlib.sha256((condition/'evaluation-input.json').read_bytes()).hexdigest()
                assert input_hash == generated['input_sha256']
                if (condition/'results.json').exists():
                    binding = json.loads((condition/'results-binding.json').read_text())
                    assert binding['input_sha256'] == input_hash
                    assert binding['results_sha256'] == hashlib.sha256((condition/'results.json').read_bytes()).hexdigest()
                    continue
                result_name = f'{args.name}-attempt{attempt}-results.json'
                command = [sys.executable, '-u', str(SOURCE/'isolate_ssd.py'),
                           '--input', str(condition/'evaluation-input.json'),
                           '--output', result_name]
            atomic_json(prefix.with_name(prefix.name+'-command.json'), command)
            start = time.monotonic()
            with prefix.with_suffix('.log').open('x') as log:
                child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                         pass_fds=(lock.fileno(),))
                atomic_json(condition/'active-stage.json', dict(stage=stage, **identity(child.pid)))
                code = child.wait()
            atomic_json(prefix.with_name(prefix.name+'-exit.json'),
                        dict(returncode=code, elapsed_seconds=time.monotonic()-start,
                             utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
            if code:
                raise RuntimeError(f'{stage} failed; inspect preserved attempt {attempt}')
            if stage == 'evaluate':
                result = SOURCE/'evaluation-rootfs/work'/result_name
                shutil.copy2(result, condition/'results.json')
                atomic_json(condition/'results-binding.json', {
                    'input_sha256': input_hash,
                    'results_sha256': hashlib.sha256(result.read_bytes()).hexdigest(),
                    'upstream_evaluator': str(SOURCE/'isolate_ssd.py'),
                    'attempt': attempt,
                })
        atomic_json(condition/'pipeline-completed.json', {
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status': 'condition complete; scientific research remains active',
        })

if __name__ == '__main__':
    main()
