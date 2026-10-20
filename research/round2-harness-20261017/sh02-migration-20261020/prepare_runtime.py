"""Build a fresh minimal runtime for the existing SSD isolation boundary on SH02.

No scorer changes. This removes the preparation dependency on an old MBPP rootfs.
"""
import importlib
import json
import os
import pathlib
import shutil
import subprocess
import sysconfig

ROOT = pathlib.Path('/root/rivermind-data/spectrum-harness/project')
SOURCE = ROOT/'research-state/ssd-author-comparison-20261019'
STATE = ROOT/'research-state/sh02-migration-20261020'

def main():
    rootfs = SOURCE/'evaluation-rootfs'
    rootfs.mkdir(exist_ok=False)
    stdlib = pathlib.Path(sysconfig.get_path('stdlib')).resolve()
    ignore = shutil.ignore_patterns('site-packages', '__pycache__', 'tests', 'test',
                                    'idlelib', 'ensurepip', 'tkinter', 'turtledemo')
    shutil.copytree(stdlib, rootfs/stdlib.relative_to('/'), ignore=ignore)
    packages = rootfs/'packages'
    packages.mkdir()
    copied = {}
    for name in ['numpy', 'pandas', 'dateutil', 'six', 'pytz', 'tzdata']:
        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError:
            if name in ('pytz', 'tzdata'):
                continue
            raise
        source = pathlib.Path(module.__file__).resolve()
        copied[name] = str(source)
        if source.name == '__init__.py':
            shutil.copytree(source.parent, packages/source.parent.name, ignore=ignore)
        else:
            shutil.copy2(source, packages/source.name)
        libs = source.parent.parent/(name+'.libs')
        if libs.exists():
            shutil.copytree(libs, packages/libs.name)
    shutil.copytree(SOURCE/'adapted', rootfs/'upstream', ignore=ignore)
    for binary in rootfs.rglob('*.so*'):
        result = subprocess.run(['ldd', str(binary)], capture_output=True, text=True)
        for word in result.stdout.split():
            source = pathlib.Path(word)
            if word.startswith('/') and source.is_file() and not source.is_relative_to(rootfs):
                target = rootfs/source.relative_to('/')
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    for directory, _, files in os.walk(rootfs):
        for name in files:
            os.chmod(pathlib.Path(directory)/name, 0o444)
        os.chmod(directory, 0o555)
    for name in ['tmp', 'dev/shm', 'work']:
        path = rootfs/name
        path.mkdir(parents=True, exist_ok=True)
        os.chmod(path, 0o700)
        os.chown(path, 61044, 61044)
    os.chmod(rootfs/'dev', 0o555)
    (STATE/'runtime-preparation.json').write_text(json.dumps({
        'rootfs': str(rootfs), 'stdlib': str(stdlib), 'packages': copied,
        'boundary': 'existing isolate_ssd.py; uid61044; chroot; seccomp; read-only runtime',
    }, indent=2)+'\n')

if __name__ == '__main__':
    main()
