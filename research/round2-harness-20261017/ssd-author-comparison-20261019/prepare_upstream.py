"""Copy the author benchmark with capacity/import/logging adaptations only."""
from pathlib import Path
import difflib,hashlib,json
ROOT=Path('/root/rivermind-data/spectrum-harness/project')
S=ROOT/'research-state/ssd-author-comparison-20261019'
U=ROOT/'upstreams/ml-ssd-2637d2021f1bc523385b48a1f88ea9aa4812b0a9'
S.mkdir(exist_ok=True)
out=S/'adapted/evaluation';out.mkdir(parents=True,exist_ok=True)
original=(U/'evaluation/benchmark.py').read_text()
modified='from __future__ import annotations\n'+original
modified=modified.replace('from datasets import Dataset, concatenate_datasets, load_dataset\n','')
modified=modified.replace('from vllm import SamplingParams\n','')
modified=modified.replace('        all_outputs = []','        from vllm import SamplingParams\n        all_outputs = []')
modified=modified.replace('        cpu_count = os.cpu_count()','        from datasets import concatenate_datasets, load_dataset\n        cpu_count = 2')
modified=modified.replace('ThreadPoolExecutor(max_workers=32)','ThreadPoolExecutor(max_workers=2)')
modified=modified.replace('        final_metrics["examples"] = [result for result, _ in results]','        final_metrics["all_repeat_results"] = [[result for result, _ in repeat] for repeat in all_repeat_results]\n        final_metrics["examples"] = [result for result, _ in results]')
(out/'benchmark.py').write_text(modified)
for name in ['__init__.py','livecodebench_utils.py']:(out/name).write_bytes((U/'evaluation'/name).read_bytes())
(S/'benchmark-capacity-and-recording.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),modified.splitlines(True),fromfile='upstream/benchmark.py',tofile='adapted/benchmark.py')))
(S/'source-manifest.json').write_text(json.dumps({'commit':U.name.split('ml-ssd-')[1], 'files':{str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.py')}},indent=2)+'\n')
print('Prepared author benchmark; test utilities unchanged.')
