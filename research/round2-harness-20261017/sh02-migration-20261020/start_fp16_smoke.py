"""Explicit GPU smoke/resume checks; never starts formal scoring."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time

from generate_condition import STATE, atomic_json

PYTHON = '/root/rivermind-data/spectrum-harness/venv-sh02/bin/python'


def run(label, command, expected=0):
    attempts = STATE/'integration'
    attempts.mkdir(exist_ok=True)
    index = len(list(attempts.glob(label+'-*-command.json')))+1
    prefix = attempts/f'{label}-{index}'
    atomic_json(prefix.with_name(prefix.name+'-command.json'), command)
    start = time.monotonic()
    with prefix.with_suffix('.log').open('x') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    atomic_json(prefix.with_name(prefix.name+'-exit.json'), {
        'returncode': result.returncode, 'expected': expected,
        'elapsed_seconds': time.monotonic()-start,
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    if result.returncode != expected:
        raise RuntimeError(f'{label} exited {result.returncode}; inspect {prefix}.log')
    return prefix


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if not (STATE/'preparation-completed.json').exists():
        raise RuntimeError('Run bootstrap_and_base.py to prepare the environment first.')

    run('gpu-environment', [PYTHON, str(STATE/'inspect_environment.py')])
    environment = json.loads((STATE/'environment.json').read_text())
    if not environment['gpu_available']:
        raise RuntimeError('No GPU is attached; smoke checks were not started.')
    if environment['device_capability'] != [7, 5] or environment['native_bf16']:
        raise RuntimeError('This FP16 protocol expects the verified T4 (SM 7.5), without native BF16.')
    if 'T4' not in environment['device_name']:
        raise RuntimeError(f"Unexpected GPU for this protocol: {environment['device_name']}")

    smoke = 'smoke-base-fp16-2048'
    command = [PYTHON, '-u', str(STATE/'run_condition.py'), '--model', 'base',
               '--temperature', '0.7', '--max-tokens', '2048',
               '--max-model-len', '17920', '--name', smoke, '--smoke-tasks', '3']
    run('smoke', command)
    raw = STATE/smoke/'repeat-00.jsonl'
    native = json.loads((STATE/smoke/'results.json').read_text())['all_repeat_results']
    if len(native) != 1 or len(native[0]) != 3:
        raise RuntimeError('Smoke output does not contain exactly 3 samples.')
    before = digest(raw)

    next_attempt = len(list((STATE/smoke).glob('generate-attempt-*-command.json')))+1
    run('resume', command)
    if digest(raw) != before:
        raise RuntimeError('Resume changed existing sample output.')
    resume_log = (STATE/smoke/f'generate-attempt-{next_attempt}.log').read_text()
    if resume_log.count('Reusing ') != 3 or 'Saved ' in resume_log:
        raise RuntimeError('Resume did not reuse exactly the three saved samples.')

    incompatible = [PYTHON, '-u', str(STATE/'generate_condition.py'),
                    '--model', 'base', '--temperature', '0.7', '--max-tokens', '2049',
                    '--max-model-len', '17920', '--name', smoke, '--smoke-tasks', '3']
    rejection = run('reject-incompatible-resume', incompatible, expected=1)
    if 'Condition configuration changed' not in rejection.with_suffix('.log').read_text():
        raise RuntimeError('Changed configuration was not rejected as expected.')
    if digest(raw) != before:
        raise RuntimeError('Rejected configuration changed the saved samples.')

    atomic_json(STATE/'fp16-smoke-completed.json', {
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'smoke_samples': 3, 'raw_sha256': before, 'resume_reused_samples': 3,
        'incompatible_config_rejected': True, 'scientific_result': False,
        'formal_scoring_started': False,
        'formal_budget': {
            'max_tokens': 16384, 'max_model_len': 17920, 'dtype': 'float16',
            'limitation': 'Shorter than the author 65536 output budget; report length termination and truncation bounds.',
        },
    })


if __name__ == '__main__':
    main()
