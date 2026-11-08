"""Fresh joint Math/MMLU-Pro snapshots without changing historical inputs.

Uses native text_tasks normalization and source conversion; this module owns the
joint selection and records its separate hash, parents and replacements.
"""
from copy import deepcopy
import json
from pathlib import Path
import random
import shutil
import unicodedata

from . import text_tasks
from .data import read_jsonl, write_jsonl, assert_disjoint_splits
from .utils import stable_hash

SPLITS = ('train', 'calibration', 'validation', 'eval')


def normalize(prompt):
    return ' '.join(unicodedata.normalize('NFKC', prompt).split())


def verify_hashes(root, hashes):
    root = Path(root).resolve()
    for relative, expected in hashes.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or text_tasks.file_sha(path) != expected:
            raise ValueError(f'Input hash mismatch: {relative}')


def replace_leaks(datasets, pool, seed):
    """Replace Math training-side overlaps only; selection never reads answers."""
    output = deepcopy(datasets)
    used_ids, used_prompts = set(), set()
    locations = {}
    for domain, splits in datasets.items():
        for split, rows in splits.items():
            for row in rows:
                used_ids.add(row['task_id'])
                for field in ('original_prompt', 'prompt'):
                    key = normalize(row[field])
                    used_prompts.add(key)
                    locations.setdefault(key, set()).add((domain, split))
    candidates = list(pool)
    random.Random(seed).shuffle(candidates)
    candidates = iter(candidates)
    audit = []
    for split in SPLITS[:-1]:
        for index, row in enumerate(datasets['math'][split]):
            collisions = set()
            for field in ('original_prompt', 'prompt'):
                collisions.update(locations[normalize(row[field])] - {('math', split)})
            if not collisions:
                continue
            for candidate in candidates:
                keys = {normalize(candidate[f]) for f in ('original_prompt', 'prompt')}
                if candidate['task_id'] in used_ids or keys & used_prompts:
                    continue
                replacement = dict(candidate, split=split)
                used_ids.add(candidate['task_id'])
                used_prompts.update(keys)
                output['math'][split][index] = replacement
                audit.append({'split': split, 'index': index,
                              'excluded_task_id': row['task_id'],
                              'replacement_task_id': candidate['task_id'],
                              'overlap_locations': sorted([list(x) for x in collisions]),
                              'reason': 'normalized_cross_domain_prompt_overlap'})
                break
            else:
                raise ValueError('Insufficient eligible native PRM replacements')
    # Evaluation/evaluation shared questions remain in both complete populations.
    prompt_splits = {}
    ids = set()
    for splits in output.values():
        for split, rows in splits.items():
            for row in rows:
                if row['task_id'] in ids:
                    raise ValueError('Joint task ID overlap')
                ids.add(row['task_id'])
                for field in ('original_prompt', 'prompt'):
                    key = normalize(row[field])
                    if key in prompt_splits and prompt_splits[key] != split:
                        raise ValueError('Unresolved joint cross-split overlap')
                    prompt_splits[key] = split
    return output, audit


def prepare_joint(parent_root, output_root, seed_file):
    parent_root, output_root = Path(parent_root).resolve(), Path(output_root).resolve()
    seed = text_tasks.private_seed(seed_file)
    datasets, manifests, parents = {}, {}, {}
    for domain in ('math', 'qa'):
        root = parent_root / f'{domain}_full_20261106'
        splits, manifest = text_tasks.verify_prepared_data(root)
        identity = manifest['identity']
        if identity['seed_sha256'] != stable_hash(seed):
            raise ValueError('Private seed does not match parent')
        if identity['builder_sha256'] != text_tasks.file_sha(text_tasks.__file__):
            raise ValueError('Native parent builder mismatch')
        expected = {'train': 1024, 'calibration': 64, 'validation': 64,
                    'eval': 500 if domain == 'math' else 12032}
        if manifest['counts'] != expected:
            raise ValueError('Unexpected parent population')
        if manifest['evaluation_counts'] != ({'math500': 500} if domain == 'math' else {'mmlu_pro': 12032}):
            raise ValueError('Unexpected evaluation benchmark')
        datasets[domain], manifests[domain] = splits, manifest
        parents[domain] = {'root': str(root), 'manifest_sha256': text_tasks.file_sha(root / 'manifest.json'),
                           'output_hashes': manifest['output_hashes'], 'identity': identity}
    native_root = parent_root / 'math_full_20261106/sources/prm800k'
    for relative, spec in text_tasks.PRM_FILES.items():
        text_tasks._verify_prm(native_root / relative, spec)
    raw = read_jsonl(native_root / 'prm800k/math_splits/train.jsonl')
    if len(raw) != 12000:
        raise ValueError('Expected native PRM 12000-row training pool')
    pool = [text_tasks._math_task(row, 'train') for row in raw]
    selected, audit = replace_leaks(datasets, pool, seed)
    if output_root.exists():
        raise FileExistsError('Fresh output root required; preserve previous snapshots')
    output_root.mkdir(parents=True)
    joint = {'schema': 1, 'joint_builder_sha256': text_tasks.file_sha(__file__),
             'native_builder_sha256': text_tasks.file_sha(text_tasks.__file__),
             'parent_snapshots': parents, 'seed_sha256': stable_hash(seed),
             'selection': 'seeded native PRM permutation; prompt/ID eligibility only; no answer or outcome selection',
             'evaluation_policy': 'parent eval files copied byte-for-byte; shared eval questions retained',
             'replacements': audit, 'replacement_count': len(audit)}
    for domain in ('math', 'qa'):
        root = output_root / domain
        root.mkdir()
        parent = Path(parents[domain]['root'])
        for split in SPLITS:
            destination = root / f'{split}.jsonl'
            if domain == 'qa' or split == 'eval':
                shutil.copyfile(parent / destination.name, destination)
            else:
                write_jsonl(destination, selected[domain][split])
        if domain == 'math':
            for relative in text_tasks.PRM_FILES:
                target = root / 'sources/prm800k' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(native_root / relative, target)
        manifest = deepcopy(manifests[domain])
        manifest['identity']['data']['output_dir'] = str(root)
        # Native builder identity remains explicit; joint preparation never claims
        # to be a direct run of prepare_text_data.
        manifest['identity']['joint_builder_sha256'] = joint['joint_builder_sha256']
        manifest['preparation_method'] = 'continual_joint_decontamination_v1'
        manifest['joint_preparation'] = joint
        manifest['parent_preparation_audit'] = manifest.pop('audit', {})
        manifest['audit'] = {'replacement_count': sum(x['split'] in SPLITS and domain == 'math' for x in audit),
                             'replacements': audit if domain == 'math' else [],
                             'selection': joint['selection']}
        manifest['output_hashes'] = {f'{s}.jsonl': text_tasks.file_sha(root / f'{s}.jsonl') for s in SPLITS}
        (root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        text_tasks.verify_prepared_data(root)
        if text_tasks.file_sha(root / 'eval.jsonl') != parents[domain]['output_hashes']['eval.jsonl']:
            raise ValueError('Evaluation bytes changed')
    (output_root / 'joint_manifest.json').write_text(json.dumps(joint, indent=2) + '\n')
    combined = {s: selected['math'][s] + selected['qa'][s] for s in SPLITS}
    assert_disjoint_splits(combined)
    return joint
