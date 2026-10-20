"""Serial migration integration checks followed by the new FP16 base condition.

Preparation is not a scientific result. Any failed stage stops this program with
its log retained for the same research worker to debug. No Harness state changes.
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
        smoke = 'smoke-base-fp16-2048'
        command = [PYTHON, '-u', str(STATE/'run_condition.py'), '--model', 'base',
                   '--temperature', '0.7', '--max-tokens', '2048',
                   '--max-model-len', '17920', '--name', smoke, '--smoke-tasks', '3']
        run('smoke', command)
        raw = STATE/smoke/'repeat-00.jsonl'
        native_smoke = json.loads((STATE/smoke/'results.json').read_text())['all_repeat_results']
        assert len(native_smoke) == 1 and len(native_smoke[0]) == 3
        before = digest(raw)
        next_generate_attempt = len(list((STATE/smoke).glob('generate-attempt-*-command.json')))+1
        run('resume', command)
        assert digest(raw) == before
        log = (STATE/smoke/f'generate-attempt-{next_generate_attempt}.log').read_text()
        assert log.count('Reusing ') == 3 and 'Saved ' not in log
        incompatible = [PYTHON, '-u', str(STATE/'generate_condition.py'),
                        '--model', 'base', '--temperature', '0.7', '--max-tokens', '2049',
                        '--max-model-len', '17920', '--name', smoke, '--smoke-tasks', '3']
        run('reject-incompatible-resume', incompatible, expected=1)
        rejection_logs = sorted((STATE/'integration').glob('reject-incompatible-resume-*.log'),
                                key=lambda path: path.stat().st_mtime_ns)
        assert 'Condition configuration changed' in rejection_logs[-1].read_text()
        assert digest(raw) == before
        atomic_json(STATE/'integration-completed.json', {
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'smoke_samples': 3, 'raw_sha256': before, 'resume_reused_samples': 3,
            'incompatible_config_rejected': True, 'scientific_result': False,
            'formal_budget': {
                'max_tokens': 16384, 'max_model_len': 17920, 'dtype': 'float16',
                'rationale': 'Same engine context successfully initialized in smoke; full task prompt maximum is 1410 tokens, below the 1536-token reserve.',
                'limitation': 'Shorter than author 65536 output budget; report length termination and optimistic truncation bounds. Not full-budget reproduction.',
            },
        })
        run('formal-base', [PYTHON, '-u', str(STATE/'run_condition.py'),
                            '--model', 'base', '--temperature', '0.7',
                            '--max-tokens', '16384', '--max-model-len', '17920',
                            '--name', 'base-fp16-t0.7-cap16384'])
        atomic_json(STATE/'base-stage-completed.json', {
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'research_complete': False,
            'next': 'Inspect actual native results and truncation, then continue matched SSD comparison.',
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
