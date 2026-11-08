#!/usr/bin/env python3
"""CPU-only SPD14B data preparation. No downloads, model loading or training.

Reuses verified external PRM800K/MMLU auxiliary training snapshots; evaluation
uses pinned MATH500 and GPQA Diamond. SafeChain responses remain byte-for-byte
identical as decoded strings. Spans are half-open character offsets in reference.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from improving.text_tasks import _math_task, _gpqa_task, file_sha

SIZES = {'train': 1024, 'calibration': 50, 'validation': 64}
SEED = 20261108


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).split())


def assert_disjoint(splits):
    seen = set()
    for rows in splits.values():
        for row in rows:
            key = normalized(row['original_prompt'])
            if key in seen:
                raise ValueError('Duplicate normalized prompt within or across splits')
            seen.add(key)


def boxed_span(reference):
    start = reference.rfind('\\boxed{')
    if start < 0:
        raise ValueError('Reference lacks final boxed answer')
    start += len('\\boxed{')
    depth = 1
    for end in range(start, len(reference)):
        if reference[end] == '{':
            depth += 1
        elif reference[end] == '}':
            depth -= 1
            if depth == 0:
                if start == end:
                    raise ValueError('Empty boxed answer')
                return [start, end]
    raise ValueError('Unbalanced final boxed answer')


def add_spans(row, domain):
    row = dict(row)
    if domain == 'math':
        spans = [boxed_span(row['reference'])]
    else:
        match = re.search(r'\(([A-P])\)\.?\s*$', row['reference'])
        if not match or match.group(1) != row['answer']:
            raise ValueError('QA reference does not end in its answer letter')
        spans = [list(match.span(1))]
    row['calibration_spans'] = spans
    return row


def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def external_splits(root, domain, evaluation, protected_questions=()):
    manifest_path = root / 'manifest.json'
    old = json.loads(manifest_path.read_text())
    protected = {normalized(r['original_prompt']) for r in evaluation}
    protected.update(normalized(q) for q in protected_questions)
    seen = set()
    output, files = {}, {}
    audit = Counter()
    for split, size in SIZES.items():
        path = root / (split + '.jsonl')
        digest = file_sha(path)
        if digest != old['output_hashes'][path.name]:
            raise ValueError(f'External snapshot hash mismatch: {path}')
        rows = read_jsonl(path)
        if len(rows) != old['counts'][split]:
            raise ValueError(f'External count mismatch: {path}')
        selected = []
        for row in rows:
            if row['benchmark'] != ('math_train' if domain == 'math' else 'qa_train'):
                raise ValueError('Evaluation source in external training pool')
            if domain == 'qa' and row['original_split'] != 'auxiliary_train':
                raise ValueError('Expected MMLU auxiliary training split')
            key = normalized(row['original_prompt'])
            if key in protected:
                audit['heldout_overlap'] += 1
                continue
            if key in seen:
                audit['duplicate_prompts'] += 1
                continue
            seen.add(key)
            row['split'] = split
            selected.append(row)
        if len(selected) < size:
            raise ValueError(f'Insufficient disjoint external {domain}/{split}')
        audit['unused_verified_rows'] += len(selected) - size
        output[split] = [add_spans(r, domain) for r in selected[:size]]
        files[str(path)] = {'sha256': digest, 'count': len(rows)}
    output['eval'] = evaluation
    assert_disjoint(output)
    return output, {'root': str(root), 'manifest_sha256': file_sha(manifest_path),
                    'files': files, 'upstream_sources': old['sources'],
                    'upstream_identity': old['identity'], 'exclusions': dict(audit)}


def safety_splits(rows, sizes, seed):
    groups = defaultdict(list)
    seen = set()
    audit = Counter({'duplicate_prompts': 0})
    for i, row in enumerate(rows):
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in ('instruction', 'response')):
            raise ValueError('Invalid SafeChain schema or empty string')
        key = normalized(row['instruction'])
        if key in seen:
            audit['duplicate_prompts'] += 1
            continue
        seen.add(key)
        label = str(row['label'])
        groups[label].append({'task_id': f'SafeChain/{i}', 'source': 'UWNSL/SafeChain',
            'original_split': 'train', 'original_prompt': row['instruction'],
            'prompt': row['instruction'], 'reference': row['response'], 'label': label,
            'answer': label, 'benchmark': 'safechain', 'calibration_spans': [],
            'calibration_annotation_status': 'pending_cal_only_model_annotation'})
    total = sum(map(len, groups.values()))
    proportions = {label: len(group) / total for label, group in groups.items()}
    for label in sorted(groups):
        random.Random(f'{seed}/safechain/{label}').shuffle(groups[label])
    output = {}
    for split, size in sizes.items():
        quotas = {label: int(size * prop) for label, prop in proportions.items()}
        order = sorted(quotas, key=lambda label: (-(size * proportions[label] - quotas[label]), label))
        for label in order[:size - sum(quotas.values())]:
            quotas[label] += 1
        selected = []
        for label, count in quotas.items():
            if len(groups[label]) < count:
                raise ValueError('Insufficient rows in SafeChain stratum')
            selected.extend(dict(row, split=split, calibration_annotation_status=('pending_cal_only_model_annotation' if split == 'calibration' else 'not_applicable')) for row in groups[label][:count])
            del groups[label][:count]
        random.Random(f'{seed}/{split}').shuffle(selected)
        output[split] = selected
    assert_disjoint(output)
    audit['source_rows'] = len(rows)
    audit['unique_rows'] = total
    audit['unused_unique_rows'] = total - sum(sizes.values())
    return output, dict(audit)


def verify_assets(asset_root):
    pins = json.loads((asset_root / 'assets.json').read_text())
    receipts = []
    for pin in pins:
        if pin['repo_type'] != 'dataset':
            continue
        files = []
        for entry in pin['files']:
            path = Path(pin['path']) / entry['name']
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if len(data) != entry['size'] or (entry.get('lfs_sha256') and digest != entry['lfs_sha256']) or (not entry.get('lfs_sha256') and blob != entry['blob_id']):
                raise ValueError(f'Pinned input verification failed: {path}')
            files.append({'path': str(path), 'sha256': digest, 'bytes': len(data)})
        receipts.append({k: pin[k] for k in ('repo_id', 'revision', 'path')} | {'files': files})
    return receipts


def prepare(asset_root, external_root, output):
    receipts = verify_assets(asset_root)
    raw = asset_root / 'raw'
    math_eval = [_math_task(r, 'eval') for r in read_jsonl(raw / 'math500/test.jsonl')]
    for row in math_eval:
        row['source'] = 'HuggingFaceH4/MATH-500'
        row['revision'] = next(r['revision'] for r in receipts if r['repo_id'] == row['source'])
        row['calibration_spans'] = []
    with (raw / 'gpqa/gpqa_diamond.csv').open(newline='', encoding='utf-8') as stream:
        qa_eval = [_gpqa_task(r, i, SEED) for i, r in enumerate(csv.DictReader(stream))]
    for row in qa_eval:
        row['reference'] = f"The correct answer is ({row['answer']})."
        row['calibration_spans'] = []
    protected = []
    for name in ('gpqa_main.csv', 'gpqa_extended.csv'):
        with (raw / 'gpqa' / name).open(newline='', encoding='utf-8') as stream:
            protected.extend(r['Question'] for r in csv.DictReader(stream))
    if len(math_eval) != 500 or len(qa_eval) != 198:
        raise ValueError('Official evaluation counts changed')
    datasets, external = {}, {}
    for domain, evaluation in [('math', math_eval), ('qa', qa_eval)]:
        datasets[domain], external[domain] = external_splits(
            external_root / f'{domain}_full_20261106', domain, evaluation,
            protected if domain == 'qa' else ())
    import pyarrow.parquet as pq
    rows = pq.read_table(raw / 'safechain/data/train-00000-of-00001.parquet').to_pylist()
    datasets['safety'], safety_audit = safety_splits(rows, SIZES | {'eval': 500}, SEED)
    safety_revision = next(r['revision'] for r in receipts if r['repo_id'] == 'UWNSL/SafeChain')
    for group in datasets['safety'].values():
        for row in group:
            row['revision'] = safety_revision
    # Check cross-domain as well as within-domain normalized prompts.
    assert_disjoint({f'{domain}/{split}': group for domain, splits in datasets.items() for split, group in splits.items()})
    manifest = {'schema': 1, 'builder_sha256': file_sha(__file__), 'seed': SEED,
        'sources': receipts, 'external_training_snapshots': external, 'safety_audit': safety_audit,
        'overlap_rule': 'exact NFKC + collapsed whitespace; no semantic decontamination',
        'span_unit': 'half-open Unicode character offsets relative to reference',
        'safety_annotation': 'pending; annotate calibration only; responses untruncated',
        'protocol': {'rounds': 5, 'epochs': 2, 'max_new_tokens': 4096, 'batch_size': 2},
        'files': {}, 'counts': {}, 'safety_label_counts': {}}
    for domain, splits in datasets.items():
        manifest['counts'][domain] = {}
        for split, group in splits.items():
            path = output / domain / (split + '.jsonl')
            path.parent.mkdir(parents=True, exist_ok=True)
            data = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in group).encode('utf-8')
            if path.exists() and path.read_bytes() != data:
                raise ValueError(f'Refusing to overwrite differing prepared data: {path}')
            path.write_bytes(data)
            manifest['files'][str(path.relative_to(output))] = {'sha256': file_sha(path), 'count': len(group), 'bytes': len(data)}
            manifest['counts'][domain][split] = len(group)
            if domain == 'safety':
                manifest['safety_label_counts'][split] = dict(Counter(r['label'] for r in group))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset-root', type=Path, default=Path('/root/ai-assets/spd14b-20261108'))
    parser.add_argument('--external-root', type=Path, default=Path('/root/spectrum-prep-20261106/data/multidomain'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = prepare(args.asset_root, args.external_root, args.output or args.asset_root / 'prepared')
    print(json.dumps({'counts': result['counts'], 'safety_audit': result['safety_audit'], 'safety_label_counts': result['safety_label_counts']}, indent=2))

if __name__ == '__main__':
    main()
