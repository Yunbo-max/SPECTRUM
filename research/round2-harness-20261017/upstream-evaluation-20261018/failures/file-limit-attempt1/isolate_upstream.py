"""OS containment for the unmodified pinned EvalPlus evaluator.

This launcher contains no extraction, tests, oracle, timeout, or metric logic.
The evaluator runs in a minimal read-only runtime, without host files/network,
as a dedicated unprivileged UID. Its own multiprocessing remains available.
"""
import argparse
import ctypes
import ctypes.util
import errno
import hashlib
import importlib
import json
import os
import pathlib
import resource
import shutil
import socket
import subprocess
import sys
import sysconfig

ROOT = pathlib.Path('/root/rivermind-data/spectrum-harness/project')
STATE = ROOT/'research-state/upstream-evaluation-20261018'
UPSTREAM = ROOT/'upstreams/evalplus'
UID = 61043

def copy_runtime(destination):
    destination.mkdir(exist_ok=False)
    stdlib = pathlib.Path(sysconfig.get_path('stdlib')).resolve()
    ignore = shutil.ignore_patterns('site-packages','__pycache__','tests','test','idlelib','ensurepip','tkinter','turtledemo')
    shutil.copytree(stdlib,destination/stdlib.relative_to('/'),ignore=ignore)
    packages = destination/'packages'; packages.mkdir()
    for name in ['numpy','tqdm','termcolor','appdirs','wget','tempdir','multipledispatch']:
        module = importlib.import_module(name)
        source = pathlib.Path(module.__file__).resolve()
        if source.name == '__init__.py':
            shutil.copytree(source.parent,packages/source.parent.name,ignore=shutil.ignore_patterns('__pycache__','tests','test'))
        else:
            shutil.copy2(source,packages/source.name)
        if name == 'numpy':
            libs = source.parent.parent/'numpy.libs'
            if libs.exists():shutil.copytree(libs,packages/libs.name)
    shutil.copytree(UPSTREAM/'evalplus',destination/'upstream/evalplus',ignore=shutil.ignore_patterns('__pycache__'))
    extensions = list((destination/stdlib.relative_to('/')).rglob('*.so')) + list(packages.rglob('*.so*'))
    for binary in extensions:
        result = subprocess.run(['ldd',str(binary)],capture_output=True,text=True,check=False)
        if result.returncode:continue
        for line in result.stdout.splitlines():
            for word in line.split():
                if word.startswith('/') and pathlib.Path(word).is_file():
                    src = pathlib.Path(word)
                    if src.is_relative_to(destination):continue
                    target = destination/src.relative_to('/')
                    if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
    for folder, dirs, files in os.walk(destination):
        for name in files:os.chmod(pathlib.Path(folder)/name,0o444)
        os.chmod(folder,0o555)
    for name in ['tmp','dev/shm','work','cache']:
        p=destination/name;p.mkdir(parents=True,exist_ok=True);os.chmod(p,0o700);os.chown(p,UID,UID)
    os.chmod(destination/'dev',0o555)
    (destination/'data').mkdir()
    data = pathlib.Path(json.loads((STATE/'resolved-implementation.json').read_text())['dataset_path'])
    shutil.copy2(data,destination/'data/mbpp.jsonl')
    os.chmod(destination/'data/mbpp.jsonl',0o444);os.chmod(destination/'data',0o555)
    return stdlib

def boundary(rootfs):
    sec=ctypes.CDLL(ctypes.util.find_library('seccomp'),use_errno=True)
    sec.seccomp_init.argtypes=[ctypes.c_uint32];sec.seccomp_init.restype=ctypes.c_void_p
    sec.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];sec.seccomp_syscall_resolve_name.restype=ctypes.c_int
    sec.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
    sec.seccomp_load.argtypes=[ctypes.c_void_p]
    context=sec.seccomp_init(0x7fff0000)
    for name in ['socket','socketpair','connect','execve','execveat','ptrace','mount','umount2','unshare','setns','process_vm_readv','process_vm_writev','bpf','io_uring_setup']:
        number=sec.seccomp_syscall_resolve_name(name.encode())
        if number>=0 and sec.seccomp_rule_add(context,0x50000|errno.EPERM,number,0):raise RuntimeError('seccomp rule failed')
    # No inherited project/data descriptors; only standard streams survive.
    for fd in range(3,min(resource.getrlimit(resource.RLIMIT_NOFILE)[0],65536)):
        try:os.close(fd)
        except OSError:pass
    os.environ.clear()
    os.environ.update({'HOME':'/work','XDG_CACHE_HOME':'/cache','MBPP_OVERRIDE_PATH':'/data/mbpp.jsonl','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
    os.chroot(rootfs);os.chdir('/work');os.setgroups([]);os.setgid(UID);os.setuid(UID)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_NPROC,(128,128))
    resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024*1024,256*1024*1024))
    if sec.seccomp_load(context):raise RuntimeError('seccomp load failed')
    stdlib=sysconfig.get_path('stdlib')
    sys.path[:]=['/upstream','/packages',stdlib,stdlib+'/lib-dynload']

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--rootfs',required=True)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--probe',action='store_true')
    parser.add_argument('--samples')
    args=parser.parse_args()
    rootfs=pathlib.Path(args.rootfs).resolve()
    if args.prepare:
        copy_runtime(rootfs)
        print('Runtime prepared',rootfs,flush=True)
        return
    if args.samples:
        source=pathlib.Path(args.samples).resolve()
        assert source.is_dir()
        dest=rootfs/'work'/source.name
        assert not dest.exists(),'Preserve previous sandbox inputs/results'
        shutil.copytree(source,dest)
        for p in [dest]+list(dest.rglob('*')):
            os.chown(p,UID,UID)
    boundary(rootfs)
    if args.probe:
        assert not pathlib.Path('/root/rivermind-data').exists()
        assert not pathlib.Path('/etc/passwd').exists()
        try:socket.socket()
        except PermissionError:pass
        else:raise AssertionError('Network boundary failed')
        try:pathlib.Path('/upstream/probe-write').write_text('no')
        except PermissionError:pass
        else:raise AssertionError('Runtime write boundary failed')
        import multiprocessing
        shared=multiprocessing.Value('i',0)
        def child():shared.value=1
        p=multiprocessing.Process(target=child);p.start();p.join(10)
        assert p.exitcode==0 and shared.value==1
        import evalplus.evaluate
        print(json.dumps({'uid':os.getuid(),'host_files_absent':True,'network_denied':True,'runtime_readonly':True,'multiprocessing_works':True,'evaluator':evalplus.evaluate.__file__}),flush=True)
        return
    from evalplus.evaluate import main as upstream_main
    sys.argv=['evalplus.evaluate','--dataset','mbpp','--samples','/work/'+source.name,'--parallel','2']
    upstream_main()

if __name__=='__main__':main()
