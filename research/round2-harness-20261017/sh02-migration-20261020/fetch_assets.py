"""Acquire pinned author assets on SH02; verify bytes before recording completion."""
import argparse
import datetime
import fcntl
import hashlib
import json
import pathlib
import shutil
import subprocess
import urllib.parse

ROOT = pathlib.Path('/root/rivermind-data/spectrum-harness/project')
STATE = ROOT/'research-state/sh02-migration-20261020'
OLD = ROOT/'research-state/upstream-evaluation-20261018'
CACHE = ROOT.parent/'cache/modelscope-author-pair-20261018'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()

def fetch(url, path, size, digest):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.stat().st_size == size and sha(path) == digest, str(path)
        return
    partial = path.with_name(path.name+'.partial')
    if not (partial.exists() and partial.stat().st_size == size):
        subprocess.run(['curl', '-fLsS', '--connect-timeout', '20', '--max-time',
                        '3600', '--retry', '2', '--continue-at', '-', '-o',
                        str(partial), url], check=True)
    assert partial.stat().st_size == size and sha(partial) == digest, str(partial)
    partial.rename(path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['base', 'ssd'], required=True)
    args = parser.parse_args()
    with (STATE/'pipeline.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        model = 'Qwen/Qwen3-4B-Instruct-2507' if args.model == 'base' else 'apple/SimpleSD-4B-instruct'
        files = json.loads((OLD/'author-pair-file-manifest.json').read_text())[model]
        target = CACHE/model.replace('/', '--')
        missing = sum(f['Size'] for f in files if not (target/f['Path']).exists())
        assert shutil.disk_usage(ROOT.parent).free > missing + 2*1024**3
        for entry in files:
            name = entry['Path']
            assert '..' not in pathlib.PurePosixPath(name).parts and not name.startswith('/')
            print('Fetching/verifying', model, name, flush=True)
            url = 'https://modelscope.cn/models/'+model+'/resolve/'+entry['Revision']+'/'+urllib.parse.quote(name)
            fetch(url, target/name, entry['Size'], entry['Sha256'])
        (STATE/(args.model+'-assets-verified.json')).write_text(json.dumps({
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'model': model, 'directory': str(target), 'files': files,
        }, indent=2)+'\n')

if __name__ == '__main__':
    main()
