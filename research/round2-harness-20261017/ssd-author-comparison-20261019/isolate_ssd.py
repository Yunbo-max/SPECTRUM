"""OS boundary and input/output plumbing for the pinned SSD author evaluator."""
import argparse,ctypes,ctypes.util,errno,importlib,json,os,pathlib,resource,shutil,socket,subprocess,sys,sysconfig
ROOT=pathlib.Path('/root/rivermind-data/spectrum-harness/project')
S=ROOT/'research-state/ssd-author-comparison-20261019'
UID=61044

def prepare(rootfs):
    # Reuse already prepared, read-only standard library/native libraries; omit work/cache/data.
    old=ROOT/'research-state/upstream-evaluation-20261018/evaluation-rootfs'
    rootfs.mkdir(exist_ok=False)
    for name in ['opt','usr','lib','lib64','packages']:
        src=old/name
        if src.exists():shutil.copytree(src,rootfs/name)
    packages=rootfs/'packages';os.chmod(packages,0o755)
    for name in ['pandas','dateutil','pytz','tzdata','six']:
        try:module=importlib.import_module(name)
        except ModuleNotFoundError:
            if name in ['pytz','tzdata']:continue
            raise
        src=pathlib.Path(module.__file__).resolve()
        if src.name=='__init__.py':shutil.copytree(src.parent,packages/src.parent.name,ignore=shutil.ignore_patterns('__pycache__','tests'))
        else:shutil.copy2(src,packages/src.name)
        libs=src.parent.parent/(name+'.libs')
        if libs.exists():shutil.copytree(libs,packages/libs.name)
    shutil.copytree(S/'adapted',rootfs/'upstream')
    for binary in packages.rglob('*.so*'):
        r=subprocess.run(['ldd',str(binary)],capture_output=True,text=True)
        for word in r.stdout.split():
            if word.startswith('/') and pathlib.Path(word).is_file():
                src=pathlib.Path(word)
                if src.is_relative_to(rootfs):continue
                target=rootfs/src.relative_to('/')
                if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
    for folder,dirs,files in os.walk(rootfs):
        for name in files:os.chmod(pathlib.Path(folder)/name,0o444)
        os.chmod(folder,0o555)
    for name in ['tmp','dev/shm','work']:
        p=rootfs/name;p.mkdir(parents=True,exist_ok=True);os.chmod(p,0o700);os.chown(p,UID,UID)
    os.chmod(rootfs/'dev',0o555)

def boundary(rootfs):
    sec=ctypes.CDLL(ctypes.util.find_library('seccomp'),use_errno=True)
    class Cmp(ctypes.Structure):
        _fields_=[('arg',ctypes.c_uint),('op',ctypes.c_int),('datum_a',ctypes.c_uint64),('datum_b',ctypes.c_uint64)]
    sec.seccomp_init.argtypes=[ctypes.c_uint32];sec.seccomp_init.restype=ctypes.c_void_p
    sec.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];sec.seccomp_syscall_resolve_name.restype=ctypes.c_int
    sec.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
    sec.seccomp_rule_add_array.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint,ctypes.POINTER(Cmp)]
    sec.seccomp_load.argtypes=[ctypes.c_void_p]
    ctx=sec.seccomp_init(0x7fff0000);deny=0x50000|errno.EPERM
    for name in ['execve','execveat','ptrace','mount','umount2','unshare','setns','process_vm_readv','process_vm_writev','bpf','io_uring_setup']:
        n=sec.seccomp_syscall_resolve_name(name.encode())
        if n>=0 and sec.seccomp_rule_add(ctx,deny,n,0):raise RuntimeError(name)
    # Only AF_UNIX sockets; no inherited sockets. Needed for author multiprocessing.Manager.
    for name in ['socket','socketpair']:
        cmp=Cmp(0,1,socket.AF_UNIX,0) # SCMP_CMP_NE
        n=sec.seccomp_syscall_resolve_name(name.encode())
        if sec.seccomp_rule_add_array(ctx,deny,n,1,ctypes.byref(cmp)):raise RuntimeError(name)
    for fd in range(3,min(resource.getrlimit(resource.RLIMIT_NOFILE)[0],65536)):
        try:os.close(fd)
        except OSError:pass
    os.environ.clear();os.environ.update(HOME='/work',TMPDIR='/tmp',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    os.chroot(rootfs);os.chdir('/work');os.setgroups([]);os.setgid(UID);os.setuid(UID)
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_NPROC,(128,128))
    resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024**3,4*1024**3))
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    if sec.seccomp_load(ctx):raise RuntimeError('seccomp load')
    lib=sysconfig.get_path('stdlib');sys.path[:]=['/upstream','/packages',lib,lib+'/lib-dynload']

def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--probe',action='store_true');p.add_argument('--decode',action='store_true');p.add_argument('--input');p.add_argument('--output',required=True)
    args=p.parse_args();rootfs=S/'evaluation-rootfs'
    if args.prepare:prepare(rootfs);return
    output=pathlib.Path(args.output);assert output.name==args.output
    if args.input:
        target=rootfs/'work'/(output.name+'.input.json');assert not target.exists()
        shutil.copy2(args.input,target);os.chmod(target,0o444)
    assert not (rootfs/'work'/output).exists()
    boundary(rootfs)
    from evaluation import livecodebench_utils as util
    if args.probe:
        assert not pathlib.Path('/root/rivermind-data').exists()
        for family in [socket.AF_INET,socket.AF_INET6]:
            try:socket.socket(family)
            except PermissionError:pass
            else:raise AssertionError('IP network accessible')
        try:pathlib.Path('/upstream/test').write_text('x')
        except PermissionError:pass
        else:raise AssertionError('Runtime writable')
        import multiprocessing
        with multiprocessing.Manager() as m:
            values=m.list([1]);assert values[0]==1
        problem={'test':[{'input':'2\n','output':'3\n','testtype':'stdin'}],'is_stdin':True,'metadata':{},'entry_point':''}
        checks={}
        for label,code in [('pass','print(int(input())+1)'),('incorrect','print(0)'),('exception','raise ValueError("probe")')]:
            results=list(util.lcb_run(problem,code,6,False));checks[label]=[bool(r[0]) for r in results]
        assert checks=={'pass':[True],'incorrect':[False],'exception':[False]},checks
        pathlib.Path(output).write_text(json.dumps({'uid':os.getuid(),'host_files_absent':True,'IP_network_denied':True,'unix_IPC_enabled':True,'runtime_readonly':True,'software_probes':checks},indent=2)+'\n')
    elif args.decode:
        rows=[json.loads(line) for line in pathlib.Path(str(output)+'.input.json').open()]
        selected=[r for r in rows if r['contest_date'][:7] in ['2025-02','2025-03','2025-04','2025-05']]
        examples=[]
        # Same four-shard order as Dataset.shard(contiguous=True), then concatenation.
        for row in selected:
            row['private_test_cases']=util.translate_private_test_cases(row['private_test_cases']);examples.append(util.map_to_example(row))
        pathlib.Path(output).write_text(json.dumps(examples)+'\n')
    else:
        from evaluation.benchmark import LiveCodeBenchV6
        examples=json.loads(pathlib.Path(str(output)+'.input.json').read_text())
        repeats=len(examples[0]['model_outputs'])
        evaluator=LiveCodeBenchV6(None,None,n_repeat=repeats)
        result=evaluator.evaluate(examples)
        pathlib.Path(output).write_text(json.dumps(result,default=str)+'\n')
if __name__=='__main__':main()
