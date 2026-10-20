"""Prepare the SH02 runtime and evaluator, then stop before using a GPU.

GPU smoke and formal scoring have separate explicit entry points. This script
must remain safe to run while the instance has no GPU attached.
"""
import datetime
import fcntl
import hashlib
import json
import pathlib
import subprocess
import time
from generate_condition import STATE, SOURCE, atomic_json

PYTHON = '/root/rivermind-data/spectrum-harness/venv-sh02/bin/python'

def run(label, command, expected=0):
    attempts = STATE/'integration'
    attempts.mkdir(exist_ok=True)
    index = len(list(attempts.glob(label+'-*-command.json')))+1
    prefix = attempts/f'{label}-{index}'
    atomic_json(prefix.with_name(prefix.name+'-command.json'), command)
    start = time.monotonic()
    print('Starting', label, flush=True)
    with prefix.with_suffix('.log').open('x') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    atomic_json(prefix.with_name(prefix.name+'-exit.json'), {
        'returncode': result.returncode, 'expected': expected,
        'elapsed_seconds': time.monotonic()-start,
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    assert result.returncode == expected, f'{label} exited {result.returncode}; inspect {prefix}.log'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    with (STATE/'bootstrap.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        required = ['installation-exit.json', 'base-assets-verified.json',
                    'ssd-assets-verified.json', 'source-data-verification.json']
        while not all((STATE/name).exists() for name in required):
            if (STATE/'installation-exit.json').exists():
                assert json.loads((STATE/'installation-exit.json').read_text())['returncode'] == 0
            print('Waiting for', [name for name in required if not (STATE/name).exists()], flush=True)
            time.sleep(30)
        assert json.loads((STATE/'installation-exit.json').read_text())['returncode'] == 0
        # A downloader may have just written its completion marker before releasing its lock.
        with (STATE/'pipeline.lock').open('a') as pipeline_lock:
            fcntl.flock(pipeline_lock, fcntl.LOCK_EX)
        run('environment', [PYTHON, str(STATE/'inspect_environment.py')])
        if not (STATE/'runtime-preparation.json').exists():
            run('runtime', [PYTHON, str(STATE/'prepare_runtime.py')])
        work = SOURCE/'evaluation-rootfs/work'
        if not (work/'examples.json').exists():
            run('decode', [PYTHON, str(SOURCE/'isolate_ssd.py'), '--decode',
                           '--input', str(STATE.parent.parent.parent/'cache/lcb-0fe84c3/test6.jsonl'),
                           '--output', 'examples.json'])
        assert digest(work/'examples.json') == 'd95cab6feef0bea860315bb3a2273641351da96cd43b657ac981f4e51053a73a'
        if not (work/'sh02-isolation-probe.json').exists():
            run('boundary', [PYTHON, str(SOURCE/'isolate_ssd.py'), '--probe',
                             '--output', 'sh02-isolation-probe.json'])
        if not (work/'sh02-software-probe-results.json').exists():
            run('software', [PYTHON, str(SOURCE/'isolate_ssd.py'),
                             '--input', str(SOURCE/'software-probe-inputs.json'),
                             '--output', 'sh02-software-probe-results.json'])
        result = json.loads((work/'sh02-software-probe-results.json').read_text())
        outcomes = {row['task_id']: bool(row['correctness'])
                    for row in result['all_repeat_results'][0]}
        expected = json.loads((SOURCE/'software-probe-summary.json').read_text())['outcomes']
        assert outcomes == expected
        atomic_json(STATE/'software-validation.json', {
            'software_only': True, 'outcomes': outcomes, 'expected_outcomes_verified': True,
        })
        environment = json.loads((STATE/'environment.json').read_text())
        atomic_json(STATE/'preparation-completed.json', {
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scientific_result': False,
            'python_environment_installed': True,
            'official_evaluator_and_data_prepared': True,
            'software_validation_passed': True,
            'gpu_available_during_preparation': environment['gpu_available'],
            'gpu_smoke_started': False,
            'formal_scoring_started': False,
            'next': 'Attach/enable the intended GPU, then explicitly run start_fp16_smoke.py.',
        })

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        atomic_json(STATE/'bootstrap-error.json', {
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'error_type': type(error).__name__, 'message': str(error),
        })
        raise
