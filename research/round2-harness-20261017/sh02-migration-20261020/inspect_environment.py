"""Record actual installed runtime and native device capabilities on SH02."""
import datetime
import importlib.metadata
import json
import pathlib
import platform
import subprocess
import torch
import vllm

state = pathlib.Path('/root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020')
assert torch.cuda.get_device_capability() == (7, 5)
assert not torch.cuda.is_bf16_supported(including_emulation=False)
report = {
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'python': platform.python_version(),
    'packages': {name: importlib.metadata.version(name) for name in
                 ['torch', 'vllm', 'transformers', 'numpy', 'pandas', 'triton']},
    'torch_cuda': torch.version.cuda,
    'torch_arch_list': torch.cuda.get_arch_list(),
    'device_name': torch.cuda.get_device_name(),
    'device_capability': torch.cuda.get_device_capability(),
    'native_bf16': torch.cuda.is_bf16_supported(including_emulation=False),
    'emulated_bf16_query': torch.cuda.is_bf16_supported(),
    'vllm_import_path': vllm.__file__,
    'gpu': subprocess.check_output(
        ['nvidia-smi', '--query-gpu=name,driver_version,memory.total,memory.used,utilization.gpu',
         '--format=csv,noheader'], text=True).strip(),
    'engine_initialization_tested': False,
}
(state/'environment.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2), flush=True)
