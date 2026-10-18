"""Profile exact author prompts and tokenizers on hn01 before model initialization."""
import sys,json,hashlib,math
from pathlib import Path
from transformers import AutoTokenizer
S=Path('/root/rivermind-data/spectrum-harness/project/research-state/ssd-author-comparison-20261019')
sys.path.insert(0,str(S/'adapted'))
from evaluation.benchmark import LCB_PROMPT_WITHOUT_STARTER_CODE,LCB_PROMPT_WITH_STARTER_CODE
examples=json.loads((S/'evaluation-rootfs/work/examples.json').read_text());out={}
for folder in sorted((S/'tokenizer-inspection').iterdir()):
    tok=AutoTokenizer.from_pretrained(str(folder),local_files_only=True,trust_remote_code=False)
    prompts=[];lengths=[]
    for e in examples:
        text=LCB_PROMPT_WITHOUT_STARTER_CODE.format(problem_description=e['prompt']) if e['is_stdin'] else LCB_PROMPT_WITH_STARTER_CODE.format(problem_description=e['prompt'],entry_point=e['entry_point'])
        p=tok.apply_chat_template([{'role':'user','content':text}],tokenize=False,add_generation_prompt=True)
        prompts.append(p);lengths.append(len(tok(p)['input_ids']))
    cfg=json.loads((folder/'config.json').read_text());kv_per_token=2*cfg['num_hidden_layers']*cfg['num_key_value_heads']*cfg['head_dim']*2
    context=math.ceil((65536+max(lengths))/256)*256
    out[folder.name]={'task_count':len(examples),'max_prompt_tokens':max(lengths),'min_prompt_tokens':min(lengths),'context_for_65536_new_tokens':context,'kv_bytes_per_token_bf16':kv_per_token,'kv_GiB_one_full_sequence':context*kv_per_token/1024**3,'prompt_sha256':hashlib.sha256(json.dumps(prompts).encode()).hexdigest(),'chat_template_sha256':hashlib.sha256(tok.chat_template.encode()).hexdigest(),'eos_token_id':tok.eos_token_id,'prompt_lengths':lengths}
(S/'prompt-capacity-profile.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:{a:b for a,b in v.items() if a!='prompt_lengths'} for k,v in out.items()},indent=2))
