"""SH02 native FP16 author generation, with durable per-sample resumption.

Author prompt construction, seed sequence and extraction remain in benchmark.py.
One request per generate call is a recorded execution adaptation, shared by all
new conditions. Old BF16 completions are never read by this program.
"""
import argparse
import datetime
import fcntl
import hashlib
import importlib.metadata
import json
import os
import pathlib
import sys
import time
import types

ROOT = pathlib.Path('/root/rivermind-data/spectrum-harness/project')
STATE = ROOT/'research-state/sh02-migration-20261020'
SOURCE = ROOT/'research-state/ssd-author-comparison-20261019'

def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()

def atomic_json(path, value):
    temporary = path.with_name(path.name+f'.{os.getpid()}.partial')
    with temporary.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['base', 'ssd'], required=True)
    parser.add_argument('--temperature', type=float, required=True)
    parser.add_argument('--max-tokens', type=int, required=True)
    parser.add_argument('--max-model-len', type=int, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--smoke-tasks', type=int, default=0)
    parser.add_argument('--lock-fd', type=int)
    args = parser.parse_args()
    assert pathlib.Path(args.name).name == args.name
    condition = STATE/args.name
    condition.mkdir(exist_ok=True)
    with (os.fdopen(os.dup(args.lock_fd), 'a') if args.lock_fd is not None
          else (STATE/'pipeline.lock').open('a')) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assets = json.loads((STATE/(args.model+'-assets-verified.json')).read_text())
        model_path = pathlib.Path(assets['directory'])
        # Verify the exact snapshot before initializing the engine, including resumed runs.
        from fetch_assets import sha
        for entry in assets['files']:
            path = model_path/entry['Path']
            assert path.stat().st_size == entry['Size'] and sha(path) == entry['Sha256']
        sys.path.insert(0, str(SOURCE/'adapted'))
        from transformers import AutoTokenizer
        from evaluation.benchmark import LiveCodeBenchV6
        tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True,
                                                 trust_remote_code=False)
        profile = json.loads((SOURCE/'prompt-capacity-profile.json').read_text())[model_path.name]
        assert sha_bytes(tokenizer.chat_template.encode()) == profile['chat_template_sha256']
        dataset = SOURCE/'evaluation-rootfs/work/examples.json'
        expected_dataset = json.loads((SOURCE/'base-temperature-0.7/config.json').read_text())['dataset_sha256']
        assert sha_bytes(dataset.read_bytes()) == expected_dataset
        examples = json.loads(dataset.read_text())
        if args.smoke_tasks:
            assert 0 < args.smoke_tasks <= len(examples)
            examples = examples[:args.smoke_tasks]
        repeats = 1 if args.smoke_tasks else 10
        options = dict(dtype='float16', max_model_len=args.max_model_len,
                       tensor_parallel_size=1, max_num_seqs=1,
                       max_num_batched_tokens=2048, gpu_memory_utilization=.90,
                       enforce_eager=True, enable_chunked_prefill=True,
                       enable_prefix_caching=False)
        config = dict(model=args.model, model_path=str(model_path),
                      model_files=assets['files'], temperature=args.temperature,
                      top_p=.8, top_k=20, min_p=0., n_repeat=repeats,
                      seeds=list(range(repeats)), max_tokens=args.max_tokens,
                      dataset_sha256=sha_bytes(dataset.read_bytes()),
                      task_ids=[e['task_id'] for e in examples],
                      chat_template_sha256=sha_bytes(tokenizer.chat_template.encode()),
                      source_commit='2637d2021f1bc523385b48a1f88ea9aa4812b0a9',
                      benchmark_sha256=sha(SOURCE/'adapted/evaluation/benchmark.py'),
                      runtime={name: importlib.metadata.version(name) for name in
                               ['vllm', 'torch', 'transformers', 'numpy', 'pandas']},
                      execution='single request per call; per-repeat author seed',
                      host='sh02', smoke=bool(args.smoke_tasks), **options)
        config_path = condition/'config.json'
        if config_path.exists():
            assert json.loads(config_path.read_text()) == config, 'Condition configuration changed'
        else:
            atomic_json(config_path, config)
        config_hash = sha_bytes(json.dumps(config, sort_keys=True).encode())
        sample_dir = condition/'samples'
        sample_dir.mkdir(exist_ok=True)

        class RecordingLLM:
            def __init__(self):
                self.engine = None
                self.repeat = 0

            def generate(self, prompts, sampling_params):
                repeat = self.repeat
                self.repeat += 1
                assert sampling_params.seed == repeat
                assert len(prompts) == len(examples)
                if not args.smoke_tasks:
                    assert sha_bytes(json.dumps(prompts).encode()) == profile['prompt_sha256']
                outputs, rows = [], []
                for task_index, (example, prompt) in enumerate(zip(examples, prompts)):
                    binding = dict(task_id=example['task_id'], seed=repeat,
                                   prompt_sha256=sha_bytes(prompt.encode()),
                                   config_sha256=config_hash, task_index=task_index)
                    path = sample_dir/f'r{repeat:02d}-t{task_index:03d}.json'
                    if path.exists():
                        row = json.loads(path.read_text())
                        assert all(row[key] == value for key, value in binding.items())
                        assert row['finish_reason'] in ('stop', 'length')
                        print('Reusing', repeat, task_index, row['task_id'], flush=True)
                    else:
                        prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
                        assert len(prompt_ids)+args.max_tokens <= args.max_model_len
                        if self.engine is None:
                            from vllm import LLM
                            self.engine = LLM(model=str(model_path), trust_remote_code=False, **options)
                            atomic_json(condition/'engine-initialized.json', {
                                'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                'options': options,
                            })
                        start = time.monotonic()
                        output = self.engine.generate([prompt], sampling_params, use_tqdm=False)[0]
                        item = output.outputs[0]
                        assert item.finish_reason in ('stop', 'length')
                        row = dict(**binding, text=item.text, token_ids=list(item.token_ids),
                                   prompt_token_ids=list(output.prompt_token_ids),
                                   finish_reason=item.finish_reason, stop_reason=item.stop_reason,
                                   elapsed_seconds=time.monotonic()-start,
                                   utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
                        assert len(row['token_ids']) <= args.max_tokens
                        atomic_json(path, row)
                        print('Saved', repeat, task_index, row['task_id'],
                              len(row['token_ids']), row['finish_reason'], flush=True)
                    rows.append(row)
                    outputs.append(types.SimpleNamespace(outputs=[types.SimpleNamespace(text=row['text'])]))
                path = condition/f'repeat-{repeat:02d}.jsonl'
                content = ''.join(json.dumps(row)+'\n' for row in rows)
                if path.exists():
                    assert path.read_text() == content
                else:
                    temporary = path.with_suffix(f'.{os.getpid()}.partial')
                    with temporary.open('x') as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    temporary.rename(path)
                return outputs

        proxy = RecordingLLM()
        benchmark = LiveCodeBenchV6(proxy, tokenizer, max_tokens=args.max_tokens,
                                   n_repeat=repeats,
                                   sampling_params=dict(temperature=args.temperature, top_p=.8,
                                                        top_k=20, min_p=0.),
                                   seed=[0, 1234, 1234, 1234])
        benchmark.generate(examples)
        atomic_json(condition/'evaluation-input.json', examples)
        atomic_json(condition/'generation-completed.json', {
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'tasks': len(examples), 'samples': len(examples)*repeats,
            'config_sha256': config_hash, 'input_sha256': sha(condition/'evaluation-input.json'),
        })

if __name__ == '__main__':
    main()
