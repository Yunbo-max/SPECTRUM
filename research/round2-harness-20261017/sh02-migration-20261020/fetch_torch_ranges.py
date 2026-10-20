"""Bounded transfer of pinned bytes; validate ranges and full SHA before use."""
import concurrent.futures
import fcntl
import hashlib
import pathlib
import re
import subprocess
from fetch_assets import ROOT, STATE, sha
import json
META = json.loads((STATE/'torch-wheel-source.json').read_text())
def verify_sources():
    (STATE/'torch-wheel-verified.json').write_text(json.dumps(META, indent=2)+'\n')

SIZE = META['size']
DIGEST = META['digests']['sha256']
URL = META['url']

def main():
    target = ROOT.parent/'cache/sh02-wheels'/META['filename']
    with (STATE/'torch-download.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if target.exists():
            assert target.stat().st_size == SIZE and sha(target) == DIGEST
            verify_sources()
            return
        parts = target.parent/'torch-ranges'
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
                            '600', '--speed-limit', '1024', '--speed-time', '45',
                            '--retry', '3', '--retry-all-errors', '--range', f'{low}-{high}',
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

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
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
