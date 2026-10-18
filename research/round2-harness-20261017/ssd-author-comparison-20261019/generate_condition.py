"""Invoke author generation unchanged; record/cache each completed repeat.

No generated code executes here. Evaluation is a separate isolated subprocess.
"""
import argparse,datetime,fcntl,hashlib,json,os,pathlib,sys,time,types
S=pathlib.Path('/root/rivermind-data/spectrum-harness/project/research-state/ssd-author-comparison-20261019')
OLD=S.parent/'upstream-evaluation-20261018'
CACHE=pathlib.Path('/root/rivermind-data/spectrum-harness/cache/modelscope-author-pair-20261018')

def digest_json(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=['base','ssd'],required=True);p.add_argument('--temperature',type=float,required=True)
    p.add_argument('--lock-fd',type=int)
    args=p.parse_args()
    # Same lock as preparation: a launch during downloads fails before GPU initialization.
    with (os.fdopen(os.dup(args.lock_fd),'a') if args.lock_fd is not None else (OLD/'pipeline.lock').open('a')) as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        model='Qwen--Qwen3-4B-Instruct-2507' if args.model=='base' else 'apple--SimpleSD-4B-instruct'
        completed=json.loads((OLD/'author-pair-download-progress.json').read_text())
        expected_model='Qwen/Qwen3-4B-Instruct-2507' if args.model=='base' else 'apple/SimpleSD-4B-instruct'
        assert any(row['model']==expected_model for row in completed), 'Selected model snapshot not yet fully verified'
        model_path=CACHE/model
        profile=json.loads((S/'prompt-capacity-profile.json').read_text())[model]
        condition=S/f'{args.model}-temperature-{args.temperature}'
        condition.mkdir(exist_ok=True)
        if (condition/'generation-completed.json').exists():
            print('Completed condition preserved; no generation required.',flush=True);return
        sys.path.insert(0,str(S/'adapted'))
        from transformers import AutoTokenizer
        from evaluation.benchmark import LiveCodeBenchV6
        tokenizer=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True,trust_remote_code=False)
        assert hashlib.sha256(tokenizer.chat_template.encode()).hexdigest()==profile['chat_template_sha256']
        examples=json.loads((S/'evaluation-rootfs/work/examples.json').read_text())
        config={'model_path':str(model_path),'model':args.model,'temperature':args.temperature,'top_p':.8,'top_k':20,'min_p':0.,'n_repeat':10,'seeds':list(range(10)),'max_tokens':65536,'max_model_len':profile['context_for_65536_new_tokens'],'tensor_parallel_size':1,'dtype':'bfloat16','max_num_seqs':1,'max_num_batched_tokens':4096,'gpu_memory_utilization':.90,'enforce_eager':True,'enable_chunked_prefill':True,'dataset_sha256':hashlib.sha256((S/'evaluation-rootfs/work/examples.json').read_bytes()).hexdigest(),'source_commit':'2637d2021f1bc523385b48a1f88ea9aa4812b0a9'}
        config_path=condition/'config.json'
        if config_path.exists():assert json.loads(config_path.read_text())==config
        else:config_path.write_text(json.dumps(config,indent=2)+'\n')
        class RecordingLLM:
            def __init__(self):self.engine=None;self.repeat=0
            def generate(self,prompts,sampling_params):
                idx=self.repeat;self.repeat+=1
                assert sampling_params.seed==idx
                path=condition/f'repeat-{idx:02d}.jsonl'
                prompt_hash=hashlib.sha256(json.dumps(prompts).encode()).hexdigest()
                assert prompt_hash==profile['prompt_sha256']
                if path.exists():
                    rows=[json.loads(line) for line in path.open()]
                    assert len(rows)==len(examples)
                    assert all(row['task_id']==e['task_id'] and row['seed']==idx and row['prompt_sha256']==hashlib.sha256(prompt.encode()).hexdigest() for row,e,prompt in zip(rows,examples,prompts))
                    print('Reusing completed repeat',idx,flush=True)
                    return [types.SimpleNamespace(outputs=[types.SimpleNamespace(text=row['text'])]) for row in rows]
                if self.engine is None:
                    from vllm import LLM
                    options={k:config[k] for k in ['max_model_len','tensor_parallel_size','dtype','max_num_seqs','max_num_batched_tokens','gpu_memory_utilization','enforce_eager','enable_chunked_prefill']}
                    self.engine=LLM(model=str(model_path),trust_remote_code=False,**options)
                    (condition/'engine-initialized.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'options':options},indent=2)+'\n')
                start=time.monotonic();outputs=self.engine.generate(prompts,sampling_params)
                temporary=path.with_suffix('.partial')
                with temporary.open('w') as f:
                    for example,prompt,output in zip(examples,prompts,outputs):
                        o=output.outputs[0]
                        row={'task_id':example['task_id'],'seed':idx,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'prompt_token_ids':output.prompt_token_ids,'text':o.text,'token_ids':o.token_ids,'finish_reason':o.finish_reason,'stop_reason':o.stop_reason}
                        f.write(json.dumps(row)+'\n')
                    f.flush();os.fsync(f.fileno())
                assert len(outputs)==len(examples)
                temporary.rename(path)
                (condition/f'repeat-{idx:02d}-timing.json').write_text(json.dumps({'elapsed_seconds':time.monotonic()-start,'sampling_params':str(sampling_params)},indent=2)+'\n')
                return outputs
        proxy=RecordingLLM()
        bench=LiveCodeBenchV6(proxy,tokenizer,max_tokens=65536,n_repeat=10,sampling_params={'temperature':args.temperature,'top_p':.8,'top_k':20,'min_p':0.},seed=[0,1234,1234,1234])
        bench.generate(examples)
        # Test-heavy input stays remote; raw completions can be delivered separately.
        output=condition/'evaluation-input.json';temp=output.with_suffix('.partial')
        temp.write_text(json.dumps(examples)+'\n');temp.rename(output)
        (condition/'generation-completed.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tasks':len(examples),'samples':10*len(examples),'input_sha256':hashlib.sha256(output.read_bytes()).hexdigest()},indent=2)+'\n')
if __name__=='__main__':main()
