"""Start the formal base run only after an explicit --start invocation."""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys
import time

from generate_condition import STATE, atomic_json

PYTHON = '/root/rivermind-data/spectrum-harness/venv-sh02/bin/python'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', action='store_true', required=True,
                        help='Explicitly authorize starting the formal FP16 base condition.')
    args = parser.parse_args()
    if not args.start:
        raise RuntimeError('Pass --start only when ready to begin formal scoring.')
    if not (STATE/'fp16-smoke-completed.json').exists():
        raise RuntimeError('Complete start_fp16_smoke.py successfully first.')
    if (STATE/'base-stage-completed.json').exists():
        raise RuntimeError('Formal base stage is already marked complete; inspect its artifacts.')
    preflight = subprocess.run([PYTHON, str(STATE/'inspect_environment.py')],
                               capture_output=True, text=True)
    if preflight.returncode:
        raise RuntimeError(f'GPU/runtime preflight failed: {preflight.stderr[-2000:]}')
    environment = json.loads((STATE/'environment.json').read_text())
    if (not environment['gpu_available'] or environment['device_capability'] != [7, 5]
            or environment['native_bf16'] or 'T4' not in environment['device_name']):
        raise RuntimeError(f"Formal FP16 base requires the verified T4, observed {environment.get('device_name')}.")

    log_dir = STATE/'integration'
    log_dir.mkdir(exist_ok=True)
    index = len(list(log_dir.glob('formal-base-*-command.json')))+1
    prefix = log_dir/f'formal-base-{index}'
    command = [PYTHON, '-u', str(STATE/'run_condition.py'), '--model', 'base',
               '--temperature', '0.7', '--max-tokens', '16384',
               '--max-model-len', '17920', '--name', 'base-fp16-t0.7-cap16384']
    atomic_json(prefix.with_name(prefix.name+'-command.json'), command)
    start = time.monotonic()
    with prefix.with_suffix('.log').open('x') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    atomic_json(prefix.with_name(prefix.name+'-exit.json'), {
        'returncode': result.returncode, 'elapsed_seconds': time.monotonic()-start,
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    if result.returncode:
        raise RuntimeError(f'Formal base failed; inspect {prefix}.log')
    atomic_json(STATE/'base-stage-completed.json', {
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'research_complete': False,
        'next': 'Inspect native results and truncation, then continue the matched SSD comparison.',
    })


if __name__ == '__main__':
    main()
