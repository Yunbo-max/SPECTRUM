"""Restore pinned SSD author source and LCB bytes; never execute benchmark code."""
import datetime
import json
import pathlib
import subprocess
import tarfile
from fetch_assets import ROOT, STATE, OLD, fetch, sha

def main():
    resolution = json.loads((OLD/'ssd-source-resolution.json').read_text())
    commit = resolution['commit']
    archive = ROOT.parent/'cache'/f'ml-ssd-{commit}.tar.gz'
    if not archive.exists():
        temporary = archive.with_suffix('.partial')
        subprocess.run(['curl', '-fLsS', '--retry', '2', '--connect-timeout', '20',
                        '--max-time', '300', '-o', str(temporary),
                        f'https://codeload.github.com/apple-aiml-research/ml-ssd/tar.gz/{commit}'],
                       check=True)
        assert sha(temporary) == resolution['archive_sha256']
        temporary.rename(archive)
    assert sha(archive) == resolution['archive_sha256']
    source = ROOT/'upstreams'/f'ml-ssd-{commit}'
    if not source.exists():
        with tarfile.open(archive) as stream:
            stream.extractall(ROOT/'upstreams', filter='data')
    for name, digest in resolution['files'].items():
        assert sha(source/name) == digest, name
    dataset = ROOT.parent/'cache/lcb-0fe84c3/test6.jsonl'
    fetch('https://hf-mirror.com/datasets/livecodebench/code_generation_lite/resolve/'
          '0fe84c3912ea0c4d4a78037083943e8f0c4dd505/test6.jsonl',
          dataset, 134303240,
          'bb4c364f71921c4495a6ad15abe1a927350b720009f4933e2e71f8af0f6fd1f5')
    (STATE/'source-data-verification.json').write_text(json.dumps({
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source': resolution, 'dataset': str(dataset), 'dataset_sha256': sha(dataset),
        'private_tests_decoded': False,
    }, indent=2)+'\n')
    print('Pinned source and benchmark bytes verified.', flush=True)

if __name__ == '__main__':
    main()
