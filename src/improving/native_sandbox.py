"""Native Linux code execution in an explicitly constructed bubblewrap boundary.

Only the interpreter/runtime, explicit input files and optional empty result
directory are mounted. No home, repository, credential, network or GPU mount is
inherited. Limits are per process; this is not an aggregate cgroup memory limit.
The outer admitted workload must retain its host CPU/RAM/time allocation.
"""
from __future__ import annotations

import hashlib
import ctypes
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import sysconfig
import tempfile
from typing import Mapping

PROTOCOL = "spectrum-bwrap-native-v1"
READY = "__SPECTRUM_NATIVE_READY__"


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def _runtime_mounts():
    """Exact interpreter and library roots; never bind a prefix's parent/home."""
    # Preserve a venv's lexical executable path and pyvenv.cfg. Resolving the
    # executable symlink here would silently launch the base interpreter.
    executable = Path(os.path.abspath(sys.executable))
    executable.resolve(strict=True)
    paths = [executable, Path(os.path.abspath(sysconfig.get_path("stdlib")))]
    for value in (sys.prefix, sys.base_prefix):
        prefix = Path(os.path.abspath(value))
        prefix.resolve(strict=True)
        if (prefix / 'pyvenv.cfg').is_file():
            paths.append(prefix / 'pyvenv.cfg')
        for suffix in ("lib", "lib64"):
            path = prefix / suffix
            if path.is_dir():
                paths.append(path)
    for name in ("/usr/lib", "/usr/lib64", "/lib", "/lib64", "/etc/ld.so.cache"):
        path = Path(name)
        if path.exists():
            paths.append(path)
    mounts = []
    for path in paths:
        # Preserve lexical loader paths (/lib64 etc.) while validating sources.
        lexical = Path(os.path.abspath(path))
        if str(lexical) in {"/", "/home", "/root", "/tmp", "/workspace", "/opt"}:
            raise ValueError(f"Refusing broad runtime mount: {lexical}")
        if not any(lexical == earlier or lexical.is_relative_to(earlier)
                   for earlier in mounts if earlier.is_dir()):
            mounts.append(lexical)
    return str(executable), [(str(p), str(p)) for p in mounts]


def runtime_identity():
    if sys.platform != "linux":
        raise RuntimeError("Native sandbox requires Linux")
    binary = shutil.which("bwrap")
    if not binary:
        raise RuntimeError("Install the distribution's bubblewrap package; no unsafe fallback is enabled")
    binary = str(Path(binary).resolve(strict=True))
    executable, mounts = _runtime_mounts()
    version = subprocess.run([binary, "--version"], capture_output=True,
                             text=True, timeout=10, check=True).stdout.strip()
    help_text = subprocess.run([binary, "--help"], capture_output=True,
                               text=True, timeout=10, check=True).stdout
    required = ("--unshare-user", "--unshare-pid", "--unshare-net", "--disable-userns",
                "--remount-ro", "--size", "--clearenv", "--new-session")
    if any(flag not in help_text for flag in required):
        raise RuntimeError("Installed bubblewrap lacks required namespace/mount features; install a current distribution build")
    try:
        library = ctypes.CDLL("libseccomp.so.2")
    except OSError as error:
        raise RuntimeError("Install the distribution's libseccomp2 package for per-sample process limits") from error
    mapped = {line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
              if '/libseccomp.so.' in line and line.split()[-1].startswith('/')}
    if len(mapped) != 1:
        raise RuntimeError("Cannot identify the loaded libseccomp runtime")
    seccomp_path = str(Path(mapped.pop()).resolve(strict=True))
    return {"protocol": PROTOCOL, "binary": binary, "binary_sha256": _sha(binary),
            "version": version, "python": executable, "python_realpath": str(Path(executable).resolve()),
            "python_sha256": _sha(executable),
            "python_version": sys.version, "readonly_runtime_mounts": mounts,
            "launcher_sha256": hashlib.sha256(_LAUNCHER.encode()).hexdigest(),
            "module_sha256": _sha(__file__), "network": "new_network_namespace",
            "seccomp_library": seccomp_path, "seccomp_sha256": _sha(seccomp_path),
            "limit_scope": "per_process_rlimits_plus_outer_admitted_host_allocation"}


PROCESS_FILTER_SOURCE = r'''import ctypes
def spectrum_deny_process_creation(library_path):
    library = ctypes.CDLL(library_path)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    library.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    library.seccomp_load.argtypes = [ctypes.c_void_p]
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    context = library.seccomp_init(0x7fff0000)
    if not context:
        raise RuntimeError('seccomp_init failed')
    try:
        for name in (b'fork', b'vfork', b'clone', b'clone3'):
            number = library.seccomp_syscall_resolve_name(name)
            if number >= 0 and library.seccomp_rule_add(context, 0x00050001, number, 0) != 0:
                raise RuntimeError('seccomp process rule failed')
        if library.seccomp_load(context) != 0:
            raise RuntimeError('seccomp_load failed')
    finally:
        library.seccomp_release(context)
'''

_LAUNCHER = PROCESS_FILTER_SOURCE + r'''
import json, math, os, resource, runpy, sys
with open('/sandbox/limits.json') as stream:
    limits = json.load(stream)
resource.setrlimit(resource.RLIMIT_AS, (limits['memory'], limits['memory']))
cpu = max(1, math.ceil(limits['cpu_seconds']))
resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
resource.setrlimit(resource.RLIMIT_NPROC, (limits['pids'], limits['pids']))
resource.setrlimit(resource.RLIMIT_FSIZE, (limits['file_bytes'], limits['file_bytes']))
resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
if not limits['allow_processes']:
    spectrum_deny_process_creation(limits['seccomp_library'])
print('__SPECTRUM_NATIVE_READY__', flush=True)
sys.argv = ['/sandbox/program.py'] + sys.argv[1:]
runpy.run_path('/sandbox/program.py', run_name='__main__')
'''


def run_python(source: str, args=(), *, readonly: Mapping[str, str | Path] | None = None,
               output_dir: str | Path | None = None, environment: Mapping[str, str] | None = None,
               timeout: float = 30, memory_mb: int = 512, pids_limit: int = 64,
               file_bytes: int = 1048576, tmpfs_mb: int = 64, output=None,
               identity: dict | None = None, allow_processes: bool = False,
               trusted_guarded_coordinator: bool = False):
    """Run source; only caller-supplied /input/* files and /output are exposed.

    Returns a CompletedProcess with output bytes unless an output file was
    supplied. A timeout kills the entire bubblewrap process group/PID namespace.
    Infrastructure errors before the trusted ready marker raise explicitly.
    ``trusted_guarded_coordinator`` is only for our pinned EvalPlus coordinator,
    which installs the same fork filter in every candidate-executing child.
    RLIMIT_NPROC alone is not a process bound for a host UID-0 invocation.
    """
    if not isinstance(source, str) or not source:
        raise ValueError("Sandbox program must be nonempty source")
    if not math.isfinite(timeout) or timeout <= 0 or any(
            type(n) is not int or n <= 0 for n in (memory_mb, pids_limit, file_bytes, tmpfs_mb)):
        raise ValueError("Sandbox limits must be positive")
    identity = identity or runtime_identity()
    if allow_processes and os.geteuid() == 0 and not trusted_guarded_coordinator:
        raise RuntimeError('Multiprocess native scoring requires a non-root host account: Linux exempts host UID 0 from RLIMIT_NPROC. Run the CPU scorer as an ordinary account; no unsafe fallback.')
    readonly = dict(readonly or {})
    for destination, source_path in readonly.items():
        path = Path(destination)
        if not path.is_absolute() or path.parts[:2] != ("/", "input") or ".." in path.parts:
            raise ValueError("Additional readonly files must be mounted beneath /input")
        if not Path(source_path).is_file():
            raise ValueError("Additional mounts must be individual regular files")
    if output_dir is not None:
        output_dir = Path(output_dir).resolve(strict=True)
        if not output_dir.is_dir() or any(output_dir.iterdir()):
            raise ValueError("Sandbox result directory must exist and be empty")
    allowed_environment = {"HUMANEVAL_OVERRIDE_PATH", "MBPP_OVERRIDE_PATH", "EVALPLUS_MAX_MEMORY_BYTES"}
    if set(environment or {}) - allowed_environment:
        raise ValueError("Unexpected sandbox environment variable")
    with tempfile.TemporaryDirectory(prefix="spectrum-native-") as temporary, tempfile.TemporaryFile() as captured:
        staging = Path(temporary)
        staging.chmod(0o755)
        (staging / "program.py").write_text(source)
        (staging / "launcher.py").write_text(_LAUNCHER)
        (staging / "limits.json").write_text(json.dumps({"memory": memory_mb * 2**20,
            "cpu_seconds": timeout, "pids": pids_limit, "file_bytes": file_bytes,
            "allow_processes": allow_processes, "seccomp_library": identity['seccomp_library']}))
        for entry in staging.iterdir():
            entry.chmod(0o444)
        command = [identity["binary"], "--die-with-parent", "--new-session",
                   "--unshare-user", "--unshare-pid", "--unshare-net", "--unshare-ipc",
                   "--unshare-uts", "--disable-userns", "--uid", "65534", "--gid", "65534",
                   "--cap-drop", "ALL", "--clearenv"]
        for original, destination in identity["readonly_runtime_mounts"]:
            command += ["--ro-bind", original, destination]
        command += ["--proc", "/proc", "--dev", "/dev", "--dir", "/input",
                    "--size", str(64 * 2**20), "--tmpfs", "/dev/shm",
                    "--size", str(tmpfs_mb * 2**20), "--tmpfs", "/tmp",
                    "--size", str(tmpfs_mb * 2**20), "--tmpfs", "/work",
                    "--ro-bind", str(staging), "/sandbox"]
        for destination, original in sorted(readonly.items()):
            # Stage mode-0600 user inputs without exposing their parent folders.
            staged = staging / ("input-" + hashlib.sha256(destination.encode()).hexdigest())
            shutil.copyfile(original, staged)
            staged.chmod(0o444)
            command += ["--ro-bind", str(staged), destination]
        if output_dir is not None:
            # UID 65534 in the user namespace maps to the invoking host user.
            command += ["--bind", str(output_dir), "/output"]
        command += ["--remount-ro", "/", "--chdir", "/work"]
        env = {"PATH": str(Path(identity["python"]).parent), "HOME": "/tmp",
               "LANG": "C.UTF-8", "XDG_CACHE_HOME": "/tmp/cache",
               "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
               **dict(environment or {})}
        for name, value in env.items():
            command += ["--setenv", name, str(value)]
        command += ["--", identity["python"], "-I", "/sandbox/launcher.py", *map(str, args)]
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=captured,
                                   stderr=captured, start_new_session=True, close_fds=True,
                                   env={"PATH": os.defpath, "LANG": "C.UTF-8"})
        timed_out = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        captured.seek(0)
        content = captured.read(min(file_bytes + 65536, 2**30))
        if READY.encode() not in content:
            raise RuntimeError("Native sandbox could not start its trusted runner: " + content[:4096].decode(errors="replace"))
        if output is not None:
            output.write(content)
            output.flush()
        if timed_out:
            raise subprocess.TimeoutExpired(command[:1], timeout, output=content)
        return subprocess.CompletedProcess(command[:1], process.returncode, content)


def qualify_sandbox():
    """Harmless native namespace/read-only/host-file checks, never model code."""
    identity = runtime_identity()
    namespaces = {name: os.stat(f"/proc/self/ns/{name}").st_ino for name in ("mnt", "net", "pid", "user", "ipc")}
    with tempfile.NamedTemporaryFile(prefix="spectrum-host-private-") as sentinel:
        source = '''import json, os, pathlib, sys
host = json.loads(sys.argv[1])
assert sys.prefix == sys.argv[3], 'sandbox selected a different Python environment'
assert sys.version == sys.argv[4], 'sandbox Python version changed'
assert not pathlib.Path(sys.argv[2]).exists(), 'host file is visible'
assert os.getuid() == 65534, 'sandbox UID not isolated'
for name, inode in host.items():
    assert os.stat('/proc/self/ns/' + name).st_ino != inode, name
status = pathlib.Path('/proc/self/status').read_text()
assert int(next(line.split()[1] for line in status.splitlines() if line.startswith('CapEff:')), 16) == 0
assert int(next(line.split()[1] for line in status.splitlines() if line.startswith('NoNewPrivs:'))) == 1
assert not pathlib.Path('/root/.ssh').exists()
try:
    pathlib.Path('/sandbox/forbidden').write_text('x')
except OSError:
    pass
else:
    raise AssertionError('input mount is writable')
try:
    pathlib.Path('/forbidden').write_text('x')
except OSError:
    pass
else:
    raise AssertionError('root mount is writable')
assert len(pathlib.Path('/proc/net/route').read_text().splitlines()) == 1, 'unexpected network route'
try:
    os.fork()
except PermissionError:
    pass
else:
    raise AssertionError('process creation was not denied')
pathlib.Path('/work/allowed').write_text('ok')
print('SPECTRUM_SANDBOX_QUALIFIED', flush=True)
'''
        result = run_python(source, [json.dumps(namespaces), sentinel.name, sys.prefix, sys.version], timeout=20, identity=identity)
        if result.returncode or b"SPECTRUM_SANDBOX_QUALIFIED" not in result.stdout:
            raise RuntimeError("Native sandbox qualification failed: " + result.stdout.decode(errors="replace")[:4096])
    return {"status": "qualified", "identity": identity,
            "checks": ["mount/net/pid/user/ipc namespaces", "host sentinel hidden", "no capabilities",
                       "no_new_privs", "read-only root and input", "private writable work", "no network route", "seccomp fork denial"]}
