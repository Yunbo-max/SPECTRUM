"""Record actual installed runtime and native device capabilities on SH02."""
import datetime
import importlib.metadata
import json
import pathlib
import platform
import subprocess
import sys
import torch
import vllm

state = pathlib.Path('/root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020')
check = subprocess.run([sys.executable, '-m', 'pip', 'check'], capture_output=True, text=True)
(state/'dependency-check.json').write_text(json.dumps({'returncode': check.returncode, 'stdout': check.stdout, 'stderr': check.stderr}, indent=2)+'\n')
assert check.returncode == 0, check.stdout + check.stderr
gpu_available = torch.cuda.is_available()
capability = torch.cuda.get_device_capability() if gpu_available else None
native_bf16 = (torch.cuda.is_bf16_supported(including_emulation=False)
               if gpu_available else None)
try:
    gpu_query = subprocess.run(
        ['nvidia-smi', '--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu',
         '--format=csv,noheader'], capture_output=True, text=True)
    gpu_query_record = {
        'returncode': gpu_query.returncode, 'stdout': gpu_query.stdout.strip(),
        'stderr': gpu_query.stderr.strip(),
    }
except OSError as error:
    gpu_query_record = {
        'returncode': None, 'stdout': '',
        'stderr': f'{type(error).__name__}: {error}',
    }
report = {
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'python': platform.python_version(),
    'packages': {name: importlib.metadata.version(name) for name in
                 ['torch', 'vllm', 'transformers', 'numpy', 'pandas', 'triton']},
    'all_installed_distributions': sorted([{'name': d.metadata['Name'], 'version': d.version} for d in importlib.metadata.distributions()], key=lambda d: d['name'].lower()),
    'torch_cuda': torch.version.cuda,
    'torch_arch_list': torch.cuda.get_arch_list(),
    'gpu_available': gpu_available,
    'device_name': torch.cuda.get_device_name() if gpu_available else None,
    'device_capability': capability,
    'native_bf16': native_bf16,
    'emulated_bf16_query': torch.cuda.is_bf16_supported() if gpu_available else None,
    'vllm_import_path': vllm.__file__,
    'nvidia_smi_returncode': gpu_query_record['returncode'],
    'gpu': gpu_query_record['stdout'],
    'nvidia_smi_stderr': gpu_query_record['stderr'],
    't4_match': capability == (7, 5) if gpu_available else None,
    'engine_initialization_tested': False,
}
(state/'environment.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2), flush=True)
