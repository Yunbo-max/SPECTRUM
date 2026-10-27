#!/usr/bin/env python3
"""Acquire and verify the exact complete reasoning-model snapshot, without loading it.

Run on the user's native preparation host. No model weights are downloaded by
the Web source-authoring session. The resulting manifest lives in ignored data/.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def verify_inventory(snapshot: Path, files: dict) -> set[str]:
    required = {'config.json', 'generation_config.json', 'tokenizer_config.json', 'tokenizer.json'}
    if not required.issubset(files):
        raise ValueError('Snapshot inventory omits required model/tokenizer/generation metadata')
    tokenizer_config = json.loads((snapshot / 'tokenizer_config.json').read_text())
    if not tokenizer_config.get('chat_template') and 'chat_template.jinja' not in files:
        raise ValueError('Snapshot has no native chat template')
    index = snapshot / 'model.safetensors.index.json'
    if index.is_file():
        required.add('model.safetensors.index.json')
        weights = set(json.loads(index.read_text())['weight_map'].values())
    else:
        weights = {'model.safetensors'}
    if not weights or any(Path(name).is_absolute() or '..' in Path(name).parts for name in weights):
        raise ValueError('Empty/invalid weight-index paths')
    if not (required | weights).issubset(files):
        raise ValueError('Frozen inventory does not cover the complete indexed model')
    for name in required | weights:
        if not (snapshot / name).is_file() or (snapshot / name).stat().st_size < 1:
            raise ValueError(f'Missing/empty required input: {name}')
    return weights


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='configs/multidomain/text_math.json')
    parser.add_argument('--manifest', default='data/multidomain/reasoning-model.json')
    parser.add_argument('--verify-only', action='store_true',
                        help='Verify the frozen manifest locally; do not access the network')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    model = config['model']
    repo_id, revision = model['name'], model['revision']
    if not re.fullmatch(r'[a-f0-9]{40}', revision):
        raise ValueError('A complete immutable Hugging Face revision is required')
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = manifest_path.parent / '.reasoning-model.lock'
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.verify_only:
            manifest = json.loads(manifest_path.read_text())
            if (manifest['repo_id'], manifest['revision']) != (repo_id, revision):
                raise ValueError('Manifest and requested model identity differ')
            snapshot = Path(manifest['snapshot_path'])
            verify_inventory(snapshot, manifest['files'])
            for relative, expected in manifest['files'].items():
                path = snapshot / relative
                if (not path.is_file() or path.stat().st_size != expected['bytes']
                        or sha256(path) != expected['sha256']):
                    raise ValueError(f'Snapshot file changed or missing: {relative}')
            print(f'Verified {len(manifest["files"])} files: {repo_id}@{revision}')
            return

        from huggingface_hub import HfApi, snapshot_download
        info = HfApi().model_info(repo_id, revision=revision, files_metadata=True)
        if info.sha != revision:
            raise ValueError('Hugging Face did not resolve the requested immutable revision')
        siblings = {item.rfilename: item for item in info.siblings}
        total = sum(item.size or 0 for item in siblings.values())
        # Display capacity information; existing cache files may already hold most
        # bytes, so a simplistic free-space comparison would reject valid resumes.
        cache_root = Path(os.environ.get('HF_HUB_CACHE',
                          str(Path(os.environ.get('HF_HOME', '~/.cache/huggingface')).expanduser() / 'hub'))).expanduser()
        capacity_root = cache_root
        while not capacity_root.exists():
            capacity_root = capacity_root.parent
        print(json.dumps({'repo_id': repo_id, 'revision': revision,
                          'upstream_total_bytes': total,
                          'cache_filesystem_free_bytes': shutil.disk_usage(capacity_root).free,
                          'checkpoint_storage_is_additional': True}))
        snapshot = Path(snapshot_download(repo_id=repo_id, revision=revision)).absolute()
        required = {'config.json', 'tokenizer_config.json', 'generation_config.json'}
        if not required.issubset(siblings):
            raise ValueError('Released config/tokenizer metadata is incomplete')
        if not (snapshot / 'tokenizer.json').is_file():
            raise ValueError('The configured fast tokenizer snapshot is incomplete')
        index_path = snapshot / 'model.safetensors.index.json'
        if index_path.is_file():
            weight_files = set(json.loads(index_path.read_text())['weight_map'].values())
        elif (snapshot / 'model.safetensors').is_file():
            weight_files = {'model.safetensors'}
        else:
            raise ValueError('No complete native safetensors weights/index found')
        if any(Path(name).is_absolute() or '..' in Path(name).parts for name in weight_files):
            raise ValueError('Invalid weight-index path')
        if not weight_files.issubset(siblings):
            raise ValueError('Weight index references files absent from upstream metadata')
        verified = {}
        for name, upstream in sorted(siblings.items()):
            path = snapshot / name
            if not path.is_file():
                raise ValueError(f'Incomplete snapshot: {name}')
            size = path.stat().st_size
            if upstream.size is not None and size != upstream.size:
                raise ValueError(f'File size does not match upstream metadata: {name}')
            if name in weight_files or name in required or name == 'tokenizer.json':
                with path.open('rb') as stream:
                    head = stream.read(512).lstrip()
                if head.startswith((b'version https://git-lfs.github.com/spec/', b'<!DOCTYPE html', b'<html')):
                    raise ValueError(f'Pointer/HTML is not a downloaded input: {name}')
            digest = sha256(path)
            lfs = getattr(upstream, 'lfs', None)
            expected = (lfs.get('sha256') if isinstance(lfs, dict)
                        else getattr(lfs, 'sha256', None)) if lfs else None
            if expected and digest != expected:
                raise ValueError(f'SHA256 does not match upstream LFS metadata: {name}')
            verified[name] = {'bytes': size, 'sha256': digest,
                              'upstream_lfs_sha256': expected}
        verify_inventory(snapshot, verified)
        manifest = {'schema': 1, 'repo_id': repo_id, 'revision': revision,
                    'snapshot_path': str(snapshot), 'files': verified,
                    'weight_files': sorted(weight_files),
                    'total_bytes': sum(row['bytes'] for row in verified.values()),
                    'loader': model.get('loader', 'causal_lm'),
                    'status': 'downloaded_and_file_verified_not_runtime_qualified'}
        if manifest_path.exists():
            previous = json.loads(manifest_path.read_text())
            if (previous['repo_id'], previous['revision'], previous['files']) != (
                    manifest['repo_id'], manifest['revision'], manifest['files']):
                raise ValueError('Existing manifest binds different input bytes; choose a new manifest path')
        atomic_json(manifest_path, manifest)
        print(f'Verified full snapshot; saved {manifest_path}')


if __name__ == '__main__':
    main()
