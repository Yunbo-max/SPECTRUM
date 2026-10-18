"""Sequential, hash-verified mirror downloads for the next author-checkpoint comparison."""
import datetime
import fcntl
import hashlib
import json
import pathlib
import shutil
import subprocess
import time
import urllib.parse

S=pathlib.Path('/root/rivermind-data/spectrum-harness/project/research-state/upstream-evaluation-20261018')
CACHE=pathlib.Path('/root/rivermind-data/spectrum-harness/cache/modelscope-author-pair-20261018')
MODELS=['Qwen/Qwen3-4B-Instruct-2507','apple/SimpleSD-4B-instruct']

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    with (S/'pipeline.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert (S/'pipeline-completed.txt').exists()
        assert json.loads((S/'sanitizer-helper-diagnostic/exit.json').read_text())['returncode']==0
        CACHE.mkdir(exist_ok=True)
        manifest={}
        for model in MODELS:
            data=json.loads((S/'next-condition-sources'/(model.replace('/','--')+'--modelscope-files.json')).read_text())
            selected=[{k:f[k] for k in ['Path','Revision','Sha256','Size']} for f in data['Data']['Files'] if f['Type']=='blob' and (f['Path'].endswith(('.json','.safetensors','.txt','.jinja','.md')) or f['Path']=='LICENSE')]
            assert selected and all('..' not in pathlib.PurePosixPath(f['Path']).parts and not f['Path'].startswith('/') for f in selected)
            manifest[model]=selected
        (S/'author-pair-file-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        needed=sum(f['Size'] for files in manifest.values() for f in files)
        assert shutil.disk_usage(CACHE).free>needed+2*1024**3,'Insufficient disk space for both model snapshots'
        completed=[]
        for model,files in manifest.items():
            target=CACHE/model.replace('/','--');target.mkdir(exist_ok=True)
            for entry in files:
                path=target/entry['Path'];path.parent.mkdir(parents=True,exist_ok=True)
                if path.exists():
                    assert path.stat().st_size==entry['Size'] and digest(path)==entry['Sha256']
                    print('Verified existing',model,entry['Path'],flush=True)
                    continue
                partial=path.with_name(path.name+'.partial')
                print('Fetching',model,entry['Path'],entry['Size'],flush=True)
                url='https://modelscope.cn/models/'+model+'/resolve/'+entry['Revision']+'/'+urllib.parse.quote(entry['Path'])
                command=['curl','-fLsS','--connect-timeout','20','--max-time','3600','--retry','2','--continue-at','-','--output',str(partial),url]
                if not (partial.exists() and partial.stat().st_size==entry['Size']):subprocess.run(command,check=True)
                assert partial.stat().st_size==entry['Size'], 'Download size differs from captured mirror manifest'
                assert digest(partial)==entry['Sha256'], 'Download digest differs from captured mirror manifest'
                partial.rename(path)
                print('Verified',model,entry['Path'],flush=True)
            completed.append({'model':model,'directory':str(target),'files':len(files)})
            (S/'author-pair-download-progress.json').write_text(json.dumps(completed,indent=2)+'\n')
        return completed

if __name__=='__main__':
    start=time.monotonic()
    try:
        completed=main();result={'returncode':0,'models':completed}
    except Exception as error:
        result={'returncode':1,'error_type':type(error).__name__}
        raise
    finally:
        result.update(elapsed_seconds=time.monotonic()-start,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        (S/'author-pair-download-exit.json').write_text(json.dumps(result,indent=2)+'\n')
