"""Install a coherent CUDA13 runtime in a separate venv, retaining command exits."""
import datetime
import json
import pathlib
import subprocess
import time

STATE = pathlib.Path('/root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020')
VENV = pathlib.Path('/root/rivermind-data/spectrum-harness/venv-sh02')
WHEEL = pathlib.Path('/root/rivermind-data/spectrum-harness/cache/sh02-wheels/vllm-0.32.0-cp38-abi3-manylinux_2_28_x86_64.whl')
MIRROR = 'https://pypi.tuna.tsinghua.edu.cn/simple'

def main():
    wheels = [str(WHEEL)]
    if (STATE/'torch-wheel-verified.json').exists():
        from fetch_assets import sha
        meta = json.loads((STATE/'torch-wheel-verified.json').read_text())
        torch_wheel = WHEEL.parent/meta['filename']
        assert torch_wheel.stat().st_size == meta['size']
        assert sha(torch_wheel) == meta['digests']['sha256']
        wheels.append(str(torch_wheel))
    commands = [
        [str(VENV/'bin/python'), '-m', 'pip', 'install', '--no-cache-dir',
         '--index-url', MIRROR, 'uv'],
        [str(VENV/'bin/uv'), 'pip', 'install', '--python', str(VENV/'bin/python'),
         '--cache-dir', str(VENV.parent/'cache/uv-sh02-retained'), '--index-url', MIRROR, *wheels, 'numpy==2.2.6', 'pandas==2.3.3'],
    ]
    records = []
    for command in commands:
        start = time.monotonic()
        print('COMMAND', command, flush=True)
        result = subprocess.run(command)
        records.append(dict(command=command, returncode=result.returncode,
                            elapsed_seconds=time.monotonic()-start))
        (STATE/'installation-commands.json').write_text(json.dumps(records, indent=2)+'\n')
        if result.returncode:
            break
    (STATE/'installation-exit.json').write_text(json.dumps({
        'returncode': result.returncode, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }, indent=2)+'\n')
    raise SystemExit(result.returncode)

if __name__ == '__main__':
    main()
