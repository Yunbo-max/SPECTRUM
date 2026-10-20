"""Bounded transfer of pinned bytes; validate ranges and full SHA before use."""
import concurrent.futures
import fcntl
import hashlib
import pathlib
import re
import subprocess
from fetch_assets import ROOT, STATE, sha
from prepare_sources import main as verify_sources

SIZE = 134303240
DIGEST = 'bb4c364f71921c4495a6ad15abe1a927350b720009f4933e2e71f8af0f6fd1f5'
URL = ('https://hf-mirror.com/datasets/livecodebench/code_generation_lite/resolve/'
       '0fe84c3912ea0c4d4a78037083943e8f0c4dd505/test6.jsonl')

def main():
    target = ROOT.parent/'cache/lcb-0fe84c3/test6.jsonl'
    with (STATE/'dataset-download.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if target.exists():
            assert target.stat().st_size == SIZE and sha(target) == DIGEST
            verify_sources()
            return
        parts = target.parent/'ranges'
        parts.mkdir(exist_ok=True)
        # Preserve and reuse the stopped sequential transfer as an immutable prefix.
        prefix = target.with_name(target.name+'.partial')
        start = prefix.stat().st_size if prefix.exists() else 0
        assert 0 <= start <= SIZE
        chunk = 4*1024**2
        ranges = [(i, min(i+chunk, SIZE)-1) for i in range(start, SIZE, chunk)]

        def fetch(bounds):
            low, high = bounds
            part = parts/f'{low}-{high}'
            if part.exists():
                assert part.stat().st_size == high-low+1
                return part
            pending = part.with_suffix('.partial')
            headers = part.with_suffix('.headers')
            subprocess.run(['curl', '-fLsS', '--connect-timeout', '30', '--max-time',
                            '600', '--retry', '2', '--range', f'{low}-{high}',
                            '-D', str(headers), '-o', str(pending), URL], check=True)
            content_ranges = re.findall(r'(?im)^content-range:\s*bytes (\d+)-(\d+)/(\d+)',
                                        headers.read_text())
            assert content_ranges and tuple(map(int, content_ranges[-1])) == (low, high, SIZE)
            assert pending.stat().st_size == high-low+1
            pending.rename(part)
            # Headers can contain transient signed locations; keep them out of evidence/Git.
            headers.unlink()
            print('Verified range', low, high, flush=True)
            return part

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            fetched = list(pool.map(fetch, ranges))
        assembled = target.with_suffix('.assembled')
        digest = hashlib.sha256()
        with assembled.open('wb') as output:
            for path in ([prefix] if start else []) + fetched:
                with path.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024**2), b''):
                        output.write(block)
                        digest.update(block)
        assert assembled.stat().st_size == SIZE and digest.hexdigest() == DIGEST
        assembled.rename(target)
        verify_sources()

if __name__ == '__main__':
    main()
