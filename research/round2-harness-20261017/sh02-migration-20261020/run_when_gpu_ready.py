"""Wait for the prepared SH02 T4, then run smoke and formal base sequentially."""
import datetime
import json
import pathlib
import subprocess
import sys
import time

from generate_condition import STATE, atomic_json

PYTHON = '/root/rivermind-data/spectrum-harness/venv-sh02/bin/python'
POLL_SECONDS = 60


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def record(status, **extra):
    atomic_json(STATE/'gpu-auto-runner.json', {
        'utc': now(), 'status': status, 'poll_seconds': POLL_SECONDS, **extra,
    })


def gpu_ready():
    probe = subprocess.run([PYTHON, '-c',
        'import torch; print(torch.cuda.is_available()); '
        'print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")'],
        capture_output=True, text=True)
    if probe.returncode:
        return False, probe.stderr[-1000:]
    lines = probe.stdout.strip().splitlines()
    return len(lines) >= 2 and lines[0].strip() == 'True', lines[-1] if lines else ''


def run(script, *args):
    path = STATE/script
    with (STATE/'integration'/f'auto-{path.stem}.log').open('a') as log:
        result = subprocess.run([PYTHON, '-u', str(path), *args],
                                 stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'{script} exited {result.returncode}; inspect integration/auto-{path.stem}.log')


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE/'integration').mkdir(exist_ok=True)
    if (STATE/'base-stage-completed.json').exists():
        record('formal-base-already-completed')
        return
    while not (STATE/'preparation-completed.json').exists():
        record('waiting-for-preparation')
        time.sleep(POLL_SECONDS)

    while True:
        ready, detail = gpu_ready()
        if ready:
            record('gpu-visible', device=detail)
            break
        record('waiting-for-gpu', probe=detail)
        time.sleep(POLL_SECONDS)

    try:
        if not (STATE/'fp16-smoke-completed.json').exists():
            record('running-fp16-smoke', device=detail)
            run('start_fp16_smoke.py')
        if not (STATE/'base-stage-completed.json').exists():
            record('running-formal-base', device=detail)
            run('start_formal_base.py', '--start')
        record('complete', device=detail,
               fp16_smoke_completed=(STATE/'fp16-smoke-completed.json').exists(),
               base_stage_completed=(STATE/'base-stage-completed.json').exists())
    except Exception as exc:
        record('failed', device=detail, error=str(exc))
        raise


if __name__ == '__main__':
    main()
