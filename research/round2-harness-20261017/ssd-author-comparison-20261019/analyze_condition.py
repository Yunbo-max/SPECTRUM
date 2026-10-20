"""Audit completed author results and raw samples; never execute or rescore code."""
import argparse,ast,collections,hashlib,json,math,pathlib,random,statistics,sys
S=pathlib.Path('/root/rivermind-data/spectrum-harness/project/research-state/ssd-author-comparison-20261019')
DATA=S/'dataset-resolution.json'
sys.path.insert(0,str(S/'adapted'))
from evaluation.benchmark import has_code
from evaluation.livecodebench_utils import post_process_code

def pass_k(n,c,k):return 1-math.comb(n-c,k)/math.comb(n,k) if n-c>=k else 1.
def interval(values,seed=43):
    rng=random.Random(seed);n=len(values)
    means=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(5000))
    return [means[124],means[4874]]
def analyze(condition):
    path=S/condition;native=json.loads((path/'results.json').read_text());cfg=json.loads((path/'config.json').read_text())
    data=json.loads(DATA.read_text());ids=data['ordered_task_ids']
    if 'task_ids' in cfg:assert cfg['task_ids']==ids, 'Full-condition analysis requires the complete ordered benchmark'
    if (path/'results-binding.json').exists():
        binding=json.loads((path/'results-binding.json').read_text())
        assert binding['results_sha256']==hashlib.sha256((path/'results.json').read_bytes()).hexdigest()
        assert binding['input_sha256']==hashlib.sha256((path/'evaluation-input.json').read_bytes()).hexdigest()
    assert native['num_total']==len(ids) and native['num_repeat']==cfg['n_repeat']
    repeats=native['all_repeat_results'];n=cfg['n_repeat'];assert len(repeats)==n
    tasks={task:{'task_id':task,'correct':0,'failed_length':0,'samples':[]} for task in ids}
    finish=collections.Counter();fences=collections.Counter();syntax=collections.Counter();errors=collections.Counter();tokens=[]
    for index,results in enumerate(repeats):
        assert [r['task_id'] for r in results]==ids
        raw=[json.loads(line) for line in (path/f'repeat-{index:02d}.jsonl').open()]
        assert [r['task_id'] for r in raw]==ids
        for item,result in zip(raw,results):
            assert item['seed']==index
            entry=tasks[item['task_id']]
            if 'prompt_sha256' not in entry:entry['prompt_sha256']=item['prompt_sha256']
            assert entry['prompt_sha256']==item['prompt_sha256'], 'Prompt changed between repeats'
            blocks=has_code(item['text']);assert result['content']==blocks
            correct=bool(result['correctness']);tests=result['test_results']
            assert correct==bool(tests and all(tests)),(item['task_id'],index)
            entry=tasks[item['task_id']];entry['correct']+=correct
            failed_length=(item['finish_reason']=='length' and not correct);entry['failed_length']+=failed_length
            count=len(item['token_ids']);tokens.append(count);finish[item['finish_reason']]+=1
            fences[len(blocks)]+=1
            if blocks:
                try:ast.parse(post_process_code(blocks[-1]));syntax['parseable']+=1
                except SyntaxError:syntax['syntax_error']+=1
            else:syntax['no_code_block']+=1
            if not correct:errors[result.get('reason','')]+=1
            entry['difficulty']=result['difficulty']
            entry['samples'].append({'seed':index,'correct':correct,'tokens':count,'finish_reason':item['finish_reason'],'reason':result.get('reason',''),'tests_passed':result['num_tests_passed'],'tests_failed':result['num_tests_failed']})
    ks=[k for k in [1,5,10] if k<=n]
    for entry in tasks.values():
        entry['metrics']={f'pass@{k}':pass_k(n,entry['correct'],k) for k in ks}
        entry['optimistic_capped_failure_repair']={f'pass@{k}':pass_k(n,entry['correct']+entry['failed_length'],k) for k in ks}
    summary={}
    for k in ks:
        name=f'pass@{k}';values=[t['metrics'][name] for t in tasks.values()];value=statistics.mean(values)
        if name in native:assert math.isclose(value,native[name],abs_tol=1e-12),name
        summary[name]={'value':value,'task_bootstrap_95pct':interval(values),'official_metric_present':name in native,'maximum_uplift_if_all_failed_capped_samples_fixed':statistics.mean(t['optimistic_capped_failure_repair'][name] for t in tasks.values())-value}
    report={'condition':condition,'tasks':len(ids),'samples_per_task':n,'metrics':summary,'observed_zero_correct_tasks':sum(t['correct']==0 for t in tasks.values()),'observed_all_correct_tasks':sum(t['correct']==n for t in tasks.values()),'finish_reasons':dict(finish),'code_block_counts':dict(fences),'last_extracted_code_syntax':dict(syntax),'native_failure_reasons':dict(errors),'tokens':{'total':sum(tokens),'mean':statistics.mean(tokens),'median':statistics.median(tokens),'maximum':max(tokens)},'source_result_sha256':hashlib.sha256((path/'results.json').read_bytes()).hexdigest(),'limitations':['Zero or all observed correct samples do not establish true support zero/one.','Intervals resample tasks conditional on these samples; training and independent generation uncertainty are not captured.','Capped-failure repair is an optimistic bound, not a measured longer-budget effect.','pass@10, if absent from native output, is empirical any-success over ten samples computed from native correctness statuses, not a newly executed scorer.','Equal maximum tokens are not equal realized compute.','Native tests_failed includes unexecuted slots padded after early failure; padded timeout text is not a measured timeout count.']}
    (path/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    (path/'per-task-analysis.json').write_text(json.dumps(list(tasks.values()),indent=2)+'\n')
    return report

def compare(first,second):
    a={t['task_id']:t for t in json.loads((S/first/'per-task-analysis.json').read_text())};b={t['task_id']:t for t in json.loads((S/second/'per-task-analysis.json').read_text())};assert a.keys()==b.keys()
    ca=json.loads((S/first/'config.json').read_text());cb=json.loads((S/second/'config.json').read_text())
    for key in ['dataset_sha256','source_commit','n_repeat','max_tokens','top_p','top_k','min_p']:
        if ca[key]!=cb[key]:raise ValueError(f'Incompatible comparison setting: {key}')
    for key in ['dtype','host','runtime','execution','max_model_len','seeds',
                'benchmark_sha256','chat_template_sha256','task_ids',
                'tensor_parallel_size','max_num_seqs','max_num_batched_tokens',
                'gpu_memory_utilization','enforce_eager','enable_chunked_prefill',
                'enable_prefix_caching','smoke']:
        if ca.get(key)!=cb.get(key):raise ValueError(f'Incompatible comparison setting: {key}')
    for task in a:
        assert a[task]['prompt_sha256']==b[task]['prompt_sha256'], 'Prompt differs between conditions'
        assert a[task]['difficulty']==b[task]['difficulty']
    differences={key:{'first':ca.get(key),'second':cb.get(key)} for key in sorted(ca.keys()|cb.keys()) if ca.get(key)!=cb.get(key)}
    results={}
    for name in a[next(iter(a))]['metrics']:
        delta=[b[t]['metrics'][name]-a[t]['metrics'][name] for t in a]
        results[name]={'second_minus_first':statistics.mean(delta),'paired_task_bootstrap_95pct':interval(delta)}
    discordance=collections.Counter()
    for task in a:
        left=a[task]['correct']>0;right=b[task]['correct']>0
        discordance['both' if left and right else 'first_only' if left else 'second_only' if right else 'neither']+=1
    strata={}
    for difficulty in sorted({t['difficulty'] for t in a.values()}):
        selected=[task for task in a if a[task]['difficulty']==difficulty]
        strata[difficulty]={'tasks':len(selected),'second_minus_first':{name:statistics.mean(b[t]['metrics'][name]-a[t]['metrics'][name] for t in selected) for name in results}}
    return {'first':first,'second':second,'task_count':len(a),'configuration_differences':differences,'paired_differences':results,'any_success_discordance':{key:discordance[key] for key in ['both','first_only','second_only','neither']},'descriptive_difficulty_differences':strata,'interpretation':'Configuration differences identify weight, temperature or combined changes. Difficulty summaries are exploratory; any-success discordance is finite-sample evidence, not proof of support loss. These intervals do not establish causality or optimal decoder tuning.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('conditions',nargs='+');p.add_argument('--root',type=pathlib.Path,default=S);args=p.parse_args()
    S=args.root
    for condition in args.conditions:print(json.dumps(analyze(condition),indent=2))
    if len(args.conditions)==2:
        report=compare(*args.conditions);output=S/('comparison-'+args.conditions[0]+'-vs-'+args.conditions[1]+'.json');output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
