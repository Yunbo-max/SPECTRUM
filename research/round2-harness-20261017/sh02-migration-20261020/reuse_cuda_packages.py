"""Copy RECORD-verified compatible CUDA distributions into the isolated venv."""
import base64,hashlib,importlib.metadata as metadata,json,pathlib,shutil
STATE=pathlib.Path('/root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020')
TARGET=STATE.parent.parent.parent/'venv-sh02/lib/python3.12/site-packages'
records=[]
for row in {r['name']:r for r in json.loads((STATE/'base-cuda-reuse-audit.json').read_text())}.values():
    assert row['satisfies'] and not row['outside_files']
    dist=metadata.distribution(row['name'])
    assert dist.version==row['version']
    files=[]
    for item in dist.files:
        assert '..' not in item.parts and not item.is_absolute()
        source=pathlib.Path(dist.locate_file(item));target=TARGET/item
        if not source.exists():
            assert item.hash is None
            continue
        if item.hash:
            h=hashlib.new(item.hash.mode)
            with source.open('rb') as stream:
                for block in iter(lambda:stream.read(8*1024**2),b''):h.update(block)
            assert base64.urlsafe_b64encode(h.digest()).decode().rstrip('=')==item.hash.value,str(source)
        files.append((source,target))
    for source,target in files:
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert target.read_bytes()==source.read_bytes()
        else:shutil.copy2(source,target)
    records.append(dict(name=row['name'],version=row['version'],files=len(files),source_RECORD_verified=True))
    print('Reused',row['name'],row['version'],flush=True)
(STATE/'cuda-packages-reused.json').write_text(json.dumps(records,indent=2)+'\n')
