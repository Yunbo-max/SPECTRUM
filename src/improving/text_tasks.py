"""Pinned native math/QA data, author answer parsing, and complete denominators.

Preparation is explicit. No download or model import occurs on module import.
Math equivalence delegates to OpenAI's unchanged PRM800K grader inside the native
OS execution boundary; it is never evaluated in the training process.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import tempfile
import urllib.request

from .data import (assert_disjoint_splits, prompt_fingerprint, read_jsonl,
                   validate_completions, validate_tasks, write_jsonl)
from .utils import atomic_json, stable_hash

PRM_REVISION = '7ecc794703b2877f63226f2477a49b34f9b25163'
MMLU_PRO_CODE = 'f418b116db00b065c2aea046518d8fcf74d39872'
GPQA_CODE = '56686c06f5e19865c153de0fdb11be3890014df7'
HF_INPUTS = {
    'mmlu_aux': {'repo_id': 'cais/mmlu', 'revision': 'c30699e8356da336a370243923dbaf21066bb9fe'},
    'mmlu_pro': {'repo_id': 'TIGER-Lab/MMLU-Pro', 'revision': 'b189ec765aa7ed75c8acfea42df31fdae71f97be'},
    'gpqa': {'repo_id': 'Idavidrein/gpqa', 'revision': '83022cefff930aea54f654c0b282e74b9eeda5c6'},
}
PRM_FILES = {
    'prm800k/math_splits/train.jsonl': {'sha256': '90d96daeac3fe343ebb1e22ce93dd99690f75983e957f88de42f87cffe1e8076', 'size': 10896985, 'lfs': True},
    'prm800k/math_splits/test.jsonl': {'sha256': '35dc41080a3680858b27fa7e0533d2d547825316fc5dafe5d316f4ccc5a06132', 'size': 446564, 'lfs': True},
    'prm800k/grading/grader.py': {'git_blob': '3efea1e8f7f440bb1b852630a725a031a1af4704', 'size': 8101},
    'prm800k/grading/math_normalize.py': {'git_blob': '4bb753b984a0349d611175f19cb460bb19d65309', 'size': 4598},
    'LICENSE': {'git_blob': '4ccc7f8dba5cb9f5dc77f14778602ef4c0a585b2', 'size': 1062},
}
LETTERS = 'ABCDEFGHIJKLMNOP'
INITIAL_MMLU = ('The following are multiple choice questions (with answers) about {$}. '
                'Think step by step and then finish your answer with "the answer is (X)" '
                'where X is the correct letter choice.\n\n\n')


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def private_seed(path, *, create=False):
    """One stored randomization identity, not a multi-seed experiment."""
    path = Path(path)
    if not path.exists():
        if not create:
            raise FileNotFoundError(f'Prepare data first; missing private randomization: {path}')
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as stream:
            json.dump({'schema': 1, 'seed': int.from_bytes(os.urandom(8), 'big') % (2**31)}, stream)
            stream.write('\n')
    seed = json.loads(path.read_text())['seed']
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError('Invalid private seed record')
    return seed


def _verify_prm(path, spec):
    content = path.read_bytes()
    if len(content) != spec['size'] or content.startswith(b'version https://git-lfs'):
        raise ValueError(f'Incomplete/native-source size mismatch: {path}')
    if 'sha256' in spec and hashlib.sha256(content).hexdigest() != spec['sha256']:
        raise ValueError(f'Native source SHA256 mismatch: {path}')
    blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
    if 'git_blob' in spec and blob != spec['git_blob']:
        raise ValueError(f'Native source Git blob mismatch: {path}')


def acquire_prm(destination):
    """Acquire only exact released splits and grading sources, verify before use."""
    root = Path(destination)
    receipts = {}
    for relative, spec in PRM_FILES.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            host = 'media.githubusercontent.com/media' if spec.get('lfs') else 'raw.githubusercontent.com'
            url = f'https://{host}/openai/prm800k/{PRM_REVISION}/{relative}'
            # A failed transfer leaves its .partial evidence and never publishes the final path.
            partial = target.with_suffix(target.suffix + '.partial')
            with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            _verify_prm(partial, spec)
            os.replace(partial, target)
        _verify_prm(target, spec)
        receipts[relative] = {'sha256': file_sha(target), 'size': target.stat().st_size, **spec}
    return receipts


def _math_task(row, split):
    required = ('problem', 'solution', 'answer', 'unique_id')
    if any(not isinstance(row.get(k), str) for k in required):
        raise ValueError('PRM MATH native schema changed')
    return {'task_id': 'MATH/' + row['unique_id'], 'source': 'openai/prm800k',
            'revision': PRM_REVISION, 'split': split, 'original_split': row['unique_id'].split('/')[0],
            'original_prompt': row['problem'],
            'prompt': row['problem'] + '\n\nSolve the problem step by step. Put your final answer inside \\boxed{}.',
            'reference': row['solution'], 'answer': row['answer'],
            'category': row.get('subject', ''), 'level': row.get('level'),
            'benchmark': 'math500' if split == 'eval' else 'math_train',
            'prompt_protocol': 'spectrum-math-boxed-v1',
            'chat_template_kwargs': {'enable_thinking': False}}


def _mmlu_example(row, include_answer=False):
    options = [option for option in row['options'] if option != 'N/A']
    result = 'Question:\n' + row['question'] + '\nOptions:\n'
    result += ''.join(f'{LETTERS[i]}. {option}\n' for i, option in enumerate(options))
    if include_answer:
        return result + row['cot_content'].replace("A: Let's think step by step.",
                                                   "Answer: Let's think step by step.") + '\n\n'
    return result + "Answer: Let's think step by step."


def _mmlu_pro_task(row, demonstrations):
    options = [x for x in row['options'] if x != 'N/A']
    answer = row['answer']
    # Upstream removes N/A options without remapping answer_index. Assert the
    # released rows preserve their answer position instead of silently relabeling.
    if not 0 <= int(row['answer_index']) < len(options) or LETTERS[int(row['answer_index'])] != answer:
        raise ValueError('MMLU-Pro answer position no longer follows official preprocessing')
    demos = [x for x in demonstrations if x['category'] == row['category']][:5]
    if len(demos) != 5:
        raise ValueError('MMLU-Pro requires five released category demonstrations')
    prompt = INITIAL_MMLU.replace('{$}', row['category']) + '\n'
    prompt += ''.join(_mmlu_example(x, True) for x in demos) + _mmlu_example(row)
    return {'task_id': f'MMLUPro/{row["category"]}/{row["question_id"]}',
            'source': HF_INPUTS['mmlu_pro']['repo_id'], 'revision': HF_INPUTS['mmlu_pro']['revision'],
            'split': 'eval', 'original_split': 'test', 'original_prompt': row['question'],
            'prompt': prompt, 'answer': answer, 'options': options, 'category': row['category'],
            'benchmark': 'mmlu_pro', 'prompt_protocol': 'mmlu-pro-author-5shot-cot-native-chat-v1',
            'prompt_source_revision': MMLU_PRO_CODE, 'chat_template_kwargs': {'enable_thinking': False}}


def _gpqa_task(row, index, seed):
    choices = [row['Correct Answer'], *(row[f'Incorrect Answer {i}'] for i in (1, 2, 3))]
    order = list(range(4))
    key = row.get('Record ID') or str(index)
    random.Random(int(stable_hash([seed, 'gpqa-choice-order', key])[:16], 16)).shuffle(order)
    options = [choices[i] for i in order]
    prompt = 'What is the correct answer to this question: ' + row['Question']
    prompt += '\n\nChoices:\n' + '\n'.join(f'({LETTERS[i]}) {x}' for i, x in enumerate(options))
    prompt += '\n\nGive step by step reasoning before you answer, and when you\'re ready to answer, please use the format "The correct answer is (insert answer here)":\n'
    return {'task_id': 'GPQADiamond/' + key, 'source': HF_INPUTS['gpqa']['repo_id'],
            'revision': HF_INPUTS['gpqa']['revision'], 'split': 'eval', 'original_split': 'train',
            'original_prompt': row['Question'], 'prompt': prompt, 'answer': LETTERS[order.index(0)],
            'options': options, 'option_permutation': order, 'category': row.get('High-level domain', ''),
            'benchmark': 'gpqa_diamond', 'prompt_protocol': 'gpqa-author-base-zero-shot-cot-adaptation-v1',
            'prompt_source_revision': GPQA_CODE, 'chat_template_kwargs': {'enable_thinking': False}}


def _aux_task(row, index):
    options = row['choices']
    answer = LETTERS[int(row['answer'])]
    prompt = 'Question:\n' + row['question'] + '\nOptions:\n'
    prompt += ''.join(f'{LETTERS[i]}. {option}\n' for i, option in enumerate(options))
    prompt += 'Think step by step and finish your answer with "the answer is (X)".'
    return {'task_id': f'MMLUAux/{index}', 'source': HF_INPUTS['mmlu_aux']['repo_id'],
            'revision': HF_INPUTS['mmlu_aux']['revision'], 'split': 'train',
            'original_split': 'auxiliary_train', 'original_prompt': row['question'],
            'prompt': prompt, 'reference': f'The answer is ({answer}).', 'answer': answer,
            'options': options, 'benchmark': 'qa_train', 'category': row.get('subject', ''),
            'prompt_protocol': 'spectrum-qa-training-v1', 'chat_template_kwargs': {'enable_thinking': False}}


def _partition(pool, evaluation, settings, seed):
    # Evaluation rows stay unchanged. Only training-pool overlaps/duplicates are removed.
    heldout = {prompt_fingerprint(x['original_prompt']) for x in evaluation}
    retained, exclusions, seen = [], [], set()
    for row in pool:
        key = prompt_fingerprint(row['original_prompt'])
        if key in heldout or key in seen:
            exclusions.append({'task_id': row['task_id'], 'reason': 'heldout_overlap' if key in heldout else 'train_duplicate'})
        else:
            seen.add(key)
            retained.append(row)
    random.Random(seed).shuffle(retained)
    sizes = {k: int(settings[k + '_size']) for k in ('train', 'calibration', 'validation')}
    if any(x < 1 for x in sizes.values()) or sum(sizes.values()) > len(retained):
        raise ValueError('Invalid fixed training/calibration/validation sample sizes')
    output, offset = {}, 0
    for split in ('calibration', 'validation', 'train'):
        output[split] = [dict(x, split=split) for x in retained[offset:offset + sizes[split]]]
        offset += sizes[split]
    output['eval'] = evaluation
    assert_disjoint_splits(output)
    return output, {'source_pool': len(pool), 'decontaminated_pool': len(retained),
                    'exclusions': exclusions, 'unused_training_pool': len(retained) - offset,
                    'selection': 'single_private_permutation_before_outcomes',
                    'overlap_detection': 'exact_NFKC_whitespace_normalized_question; not semantic decontamination'}


def prepare_text_data(config):
    seed = private_seed(config['seed_file'], create=True)
    root = Path(config['data']['output_dir'])
    manifest_path = root / 'manifest.json'
    identity = {'domain': config['domain'], 'data': config['data'],
                'seed_sha256': stable_hash(seed), 'builder_sha256': file_sha(__file__)}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest['identity'] != identity:
            raise ValueError('Prepared data protocol changed: use a new data directory')
        verify_prepared_data(root)
        return manifest
    if root.exists() and any((root / (name + '.jsonl')).exists() for name in ('train', 'calibration', 'validation', 'eval')):
        raise ValueError('Partial prepared outputs have no manifest; retain them and use a new data directory')
    sources = {}
    if config['domain'] == 'math':
        sources['prm800k'] = acquire_prm(root / 'sources' / 'prm800k')
        native = root / 'sources' / 'prm800k' / 'prm800k' / 'math_splits'
        pool = [_math_task(row, 'train') for row in read_jsonl(native / 'train.jsonl')]
        evaluation = [_math_task(row, 'eval') for row in read_jsonl(native / 'test.jsonl')]
        if len(pool) != 12000 or len(evaluation) != 500:
            raise ValueError('Expected official PRM MATH 12000/500 split')
    elif config['domain'] == 'qa':
        from datasets import load_dataset
        from huggingface_hub import hf_hub_download
        auxiliary = load_dataset(HF_INPUTS['mmlu_aux']['repo_id'], 'all',
                                 revision=HF_INPUTS['mmlu_aux']['revision'], split='auxiliary_train')
        pro = load_dataset(HF_INPUTS['mmlu_pro']['repo_id'], revision=HF_INPUTS['mmlu_pro']['revision'])
        if len(pro['test']) != 12032 or len(pro['validation']) != 70:
            raise ValueError('Native MMLU-Pro denominator changed')
        include_gpqa = bool(config.get('include_gpqa', False))
        pool = [_aux_task(row, i) for i, row in enumerate(auxiliary)]
        evaluation = [_mmlu_pro_task(row, pro['validation']) for row in pro['test']]
        sources = {'hf': HF_INPUTS, 'native_counts': {'auxiliary_train': len(auxiliary), 'mmlu_pro': 12032},
                   'dataset_fingerprints': {'aux': auxiliary._fingerprint, 'pro': pro['test']._fingerprint},
                   'include_gpqa': include_gpqa}
        if include_gpqa:
            gpqa_file = hf_hub_download(repo_type='dataset', filename='gpqa_diamond.csv', **HF_INPUTS['gpqa'])
            diamond = load_dataset('csv', data_files=gpqa_file, split='train')
            if len(diamond) != 198:
                raise ValueError('Native GPQA Diamond denominator changed')
            evaluation += [_gpqa_task(row, i, seed) for i, row in enumerate(diamond)]
            sources['gpqa_file_sha256'] = file_sha(gpqa_file)
            sources['native_counts']['gpqa_diamond'] = 198
            sources['dataset_fingerprints']['diamond'] = diamond._fingerprint
    else:
        raise ValueError('domain must be math or qa')
    splits, audit = _partition(pool, evaluation, config['data'], seed)
    for split, rows in splits.items():
        write_jsonl(root / f'{split}.jsonl', rows)
    manifest = {'schema': 1, 'identity': identity, 'sources': sources, 'audit': audit,
                'counts': {k: len(v) for k, v in splits.items()},
                'output_hashes': {k + '.jsonl': file_sha(root / f'{k}.jsonl') for k in splits},
                'evaluation_counts': {name: sum(x['benchmark'] == name for x in evaluation)
                                      for name in sorted({x['benchmark'] for x in evaluation})}}
    atomic_json(manifest_path, manifest)
    return manifest


def verify_prepared_data(root):
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_text())
    for path, expected in manifest['output_hashes'].items():
        if file_sha(root / path) != expected:
            raise ValueError(f'Prepared data changed: {path}')
    splits = {name: validate_tasks(read_jsonl(root / f'{name}.jsonl'))
              for name in ('train', 'calibration', 'validation', 'eval')}
    assert_disjoint_splits(splits)
    if {k: len(v) for k, v in splits.items()} != manifest['counts']:
        raise ValueError('Prepared denominator mismatch')
    return splits, manifest


def extract_math_answer(text):
    """A declared final-box extraction protocol, separate from native equivalence."""
    start = text.rfind('\\boxed{')
    if start < 0:
        return None
    start += len('\\boxed{')
    depth = 1
    for end in range(start, len(text)):
        if text[end] == '{':
            depth += 1
        elif text[end] == '}':
            depth -= 1
            if depth == 0:
                return text[start:end]
    return None


def extract_mmlu_pro(text):
    """Exact three-stage extraction from pinned author evaluate_from_local.py."""
    match = re.search(r'answer is \(?([A-J])\)?', text)
    if not match:
        match = re.search(r'.*[aA]nswer:\s*([A-J])', text)
    if not match:
        match = re.search(r'\b[A-J]\b(?!.*\b[A-J]\b)', text, re.DOTALL)
    return match.group(1) if match and match.lastindex else match.group(0) if match else None


def extract_gpqa(text):
    """Pinned GPQA AnswerPredictor.parse_sampled_answer patterns and ordering."""
    for pattern in (r'answer is \((.)\)', r'Answer: \((.)\)', r'answer: \((.)\)', r'answer \((.)\)', r'\((.)\)'):
        match = re.search(pattern, text)
        if match and match.group(1) in 'ABCD':
            return match.group(1)
    return None


def score_text_records(tasks, records, *, expected_samples, grader_root=None, sandbox=None, seed=0):
    """Strict full-population accuracy; no any-hit pass@k for multiple choice."""
    task_map = {x['task_id']: x for x in validate_tasks(tasks)}
    records = validate_completions(records, tasks)
    expected = {(task, sample) for task in task_map for sample in range(expected_samples)}
    if {(r['task_id'], r['sample_id']) for r in records} != expected:
        raise ValueError('Scoring requires every expected task/sample exactly once')
    native_identity = grader_context = None
    if any(task['benchmark'] == 'math500' for task in task_map.values()):
        if not (isinstance(sandbox, dict) and sandbox.get('backend') == 'local'):
            from .native_sandbox import runtime_identity
            # Scoped to this scoring invocation, never a process-global stale cache.
            # Eight thousand answers must not re-run binary/version probes per item.
            native_identity = runtime_identity()
        grader_context = _verified_math_grader(grader_root)
    scored = []
    for record in records:
        task = task_map[record['task_id']]
        benchmark = task['benchmark']
        if benchmark == 'math500':
            answer = extract_math_answer(record['completion'])
            if answer is None:
                correctness, status = False, 'unparsed'
            else:
                correctness, status = grade_math_sandboxed(
                    answer, task['answer'], grader_root, sandbox,
                    native_identity=native_identity, grader_context=grader_context)
        else:
            parser = extract_gpqa if benchmark == 'gpqa_diamond' else extract_mmlu_pro
            answer = parser(record['completion'])
            correctness = answer == task['answer']
            status = 'parsed' if answer is not None else 'unparsed'
        result = {**record, 'benchmark': benchmark, 'category': task.get('category', ''),
                  'answer': answer, 'correct': bool(correctness), 'grading_status': status}
        # Preserve the author's random-guess fallback only as an explicitly named
        # secondary measure; primary strict accuracy counts unparsed answers wrong.
        if benchmark == 'mmlu_pro':
            fallback = LETTERS[random.Random(int(stable_hash([seed, record['task_id'], record['sample_id'], 'author-fallback'])[:16], 16)).randrange(len(task['options']))]
            result['author_fallback_correct'] = (answer or fallback) == task['answer']
        scored.append(result)
    metrics = {}
    for benchmark in sorted({x['benchmark'] for x in scored}):
        population = [x for x in scored if x['benchmark'] == benchmark]
        per_task = {}
        for row in population:
            per_task.setdefault(row['task_id'], []).append(row)
        metrics[benchmark] = {
            'accuracy': sum(x['correct'] for x in population) / len(population),
            'tasks': len(per_task), 'samples': len(population), 'samples_per_task': expected_samples,
            'unparsed_samples': sum(x['grading_status'] == 'unparsed' for x in population),
            'grader_timeouts': sum(x['grading_status'] == 'timeout' for x in population),
            'length_capped_samples': sum(x.get('finish_reason') == 'length' for x in population),
            'generation_tokens': sum(x.get('generation_tokens', 0) for x in population),
            'per_task_accuracy': {k: sum(x['correct'] for x in v) / len(v) for k, v in per_task.items()},
            'scoring_protocol': ('openai-prm800k-native-equivalence-final-box-v1' if benchmark == 'math500'
                                 else 'author-extraction-strict-accuracy-v1'),
            'leaderboard_equivalence': False,
        }
        if benchmark == 'mmlu_pro':
            metrics[benchmark]['author_random_fallback_accuracy_secondary'] = sum(x['author_fallback_correct'] for x in population) / len(population)
        if benchmark == 'math500':
            for budget in (1, 4, 16):
                if budget > expected_samples:
                    continue
                estimates = {}
                for task_id, responses in per_task.items():
                    correct = sum(x['correct'] for x in responses)
                    failures = expected_samples - correct
                    estimates[task_id] = (1.0 if failures < budget else
                        1.0 - math.comb(failures, budget) / math.comb(expected_samples, budget))
                metrics[benchmark][f'pass@{budget}'] = sum(estimates.values()) / len(estimates)
                metrics[benchmark][f'per_task_pass@{budget}'] = estimates
            metrics[benchmark]['coverage_definition'] = 'unbiased pass@k from 16 responses; task solving coverage, not semantic strategy diversity'
            # Correct-answer lexical diversity: distinct final-box expressions and
            # pairwise derivation-token Jaccard distance, computed per task then averaged.
            unique_fractions, jaccards = [], []
            for task_id, responses in per_task.items():
                correct = [x for x in responses if x['correct']]
                if not correct:
                    continue
                answers = [x.get('answer') for x in correct]
                unique_fractions.append(len({a for a in answers if a is not None}) / len(correct))
                completions = [x.get('completion', '') for x in correct]
                distance = _pairwise_jaccard_distance(completions)
                if distance is not None:
                    jaccards.append(distance)
            metrics[benchmark]['correct_answer_diversity'] = {
                'unique_answer_fraction': sum(unique_fractions) / len(unique_fractions) if unique_fractions else None,
                'pairwise_completion_jaccard_distance': sum(jaccards) / len(jaccards) if jaccards else None,
                'eligible_tasks': len(unique_fractions),
                'jaccard_eligible_tasks': len(jaccards),
                'definition': 'correct responses only; distinct final-box expression fraction and derivation-token Jaccard distance'}
        elif benchmark in ('mmlu_pro', 'gpqa_diamond'):
            # Multiple-choice answer-distribution entropy over all samples.
            answer_counter = {}
            for row in population:
                answer = row.get('answer')
                answer_counter[answer] = answer_counter.get(answer, 0) + 1
            metrics[benchmark]['answer_distribution_entropy'] = _entropy(list(answer_counter.values()))
            metrics[benchmark]['answer_distribution'] = {str(k): v for k, v in sorted(
                answer_counter.items(), key=lambda kv: (kv[0] is None, str(kv[0])))}
            metrics[benchmark]['diversity_definition'] = 'answer-choice Shannon entropy; no semantic solution diversity claimed for multiple choice'
    return scored, metrics


def _token_set(text):
    """Whitespace-normalized token set for answer-expression lexical diversity."""
    if not text:
        return frozenset()
    return frozenset(re.findall(r'[A-Za-z0-9_]+', text.lower()))


def _pairwise_jaccard_distance(items):
    """Mean pairwise Jaccard distance over token sets; None when fewer than two items."""
    sets = [_token_set(x) for x in items]
    pairs = [(a, b) for i, a in enumerate(sets) for b in sets[i + 1:]]
    if not pairs:
        return None
    distances = []
    for a, b in pairs:
        union = a | b
        if not union:
            continue
        distances.append(1.0 - len(a & b) / len(union))
    return sum(distances) / len(distances) if distances else None


def _entropy(counts):
    total = sum(counts)
    if total <= 0:
        return 0.0
    return -sum((c / total) * math.log(c / total) for c in counts if c > 0)


def _verified_math_grader(grader_root):
    if grader_root is None:
        raise ValueError('Math scoring needs the pinned PRM grader')
    root = Path(grader_root).resolve()
    for relative in ('prm800k/grading/grader.py', 'prm800k/grading/math_normalize.py'):
        _verify_prm(root / relative, PRM_FILES[relative])
    return {'root': str(root),
            'readonly': {f'/input/prm/grading/{name}': str(root / 'prm800k' / 'grading' / name)
                         for name in ('grader.py', 'math_normalize.py')}}


def grade_math_sandboxed(answer, expected, grader_root, sandbox, *, native_identity=None,
                       grader_context=None):
    # Default is the native bubblewrap boundary; an explicitly declared local
    # backend runs the pinned author grader in a plain subprocess with a timeout
    # when the host cannot provide user/mount namespaces (e.g. a nested
    # container without CAP_SYS_ADMIN). Local execution is not a sandbox.
    import subprocess
    if grader_root is None or not sandbox:
        raise ValueError('Math scoring needs the pinned PRM grader and sandbox settings')
    context = grader_context if grader_context is not None else _verified_math_grader(grader_root)
    if context['root'] != str(Path(grader_root).resolve()):
        raise ValueError('Verified grader context belongs to a different source directory')
    worker = """import json,sys
sys.path.insert(0, {prm_dir!r})
from grading.grader import grade_answer
request=json.loads(sys.argv[1])
print(json.dumps({{'correct':bool(grade_answer(request['answer'],request['expected']))}}))
"""
    if sandbox.get('backend') == 'local':
        grader_dir = str(Path(grader_root).resolve() / 'prm800k')
        local_worker = worker.format(prm_dir=grader_dir)
        timeout = float(sandbox.get('timeout', 10))
        try:
            result = subprocess.run([sys.executable, '-c', local_worker,
                                     json.dumps({'answer': answer, 'expected': expected})],
                                    capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, 'timeout'
        if result.returncode != 0:
            raise RuntimeError('Local math grader failed; this is not a wrong model answer: ' + result.stderr.decode(errors='replace')[-1000:])
        parsed = json.loads(result.stdout.decode().splitlines()[-1])
        if type(parsed.get('correct')) is not bool:
            raise ValueError('Local math grader returned an invalid result')
        return parsed['correct'], 'parsed'
    from .native_sandbox import run_python
    worker = """import json,sys
sys.path.insert(0, '/input/prm')
from grading.grader import grade_answer
request=json.loads(sys.argv[1])
print(json.dumps({'correct':bool(grade_answer(request['answer'],request['expected']))}))
"""
    try:
        result = run_python(worker, args=[json.dumps({'answer': answer, 'expected': expected})],
                            readonly=context['readonly'], timeout=float(sandbox.get('timeout', 10)),
                            memory_mb=int(sandbox.get('memory_mb', 2048)), identity=native_identity)
    except subprocess.TimeoutExpired:
        return False, 'timeout'
    if result.returncode != 0:
        raise RuntimeError('Native math grader failed; this is not a wrong model answer: ' + result.stdout.decode(errors='replace')[-1000:])
    parsed = json.loads(result.stdout.decode().splitlines()[-1])
    if type(parsed.get('correct')) is not bool:
        raise ValueError('Native math grader returned an invalid result')
    return parsed['correct'], 'parsed'
