# Native scoring on the actual execution host

Status: source delivered, runtime qualification pending. This change introduces
`evaluation.backend: bwrap` for new studies; it does not change historical
Docker/local scores or qualify the host merely by installing dependencies.

The native Conda environment requires the distribution's **bubblewrap** and
**libseccomp2** system packages and working unprivileged user namespaces. On a
Debian/Ubuntu host the administrator installation command is:

```bash
sudo apt-get install bubblewrap libseccomp2
```

Do not change host security controls to work around a namespace denial. The
reported denial must be resolved by the host administrator, or scoring must run
on another admitted native CPU host with those facilities.

From the delivered repository in the actual native environment, qualify first:

```bash
python scripts/check_native_sandbox.py --output runs/private/native-sandbox.json
```

The receipt checks mount/network/PID/user/IPC namespace separation, hidden host
files, dropped capabilities, `no_new_privs`, read-only inputs/root, private writable
temporary space, no network routes and a seccomp-enforced process-creation denial.
Existing receipts are never overwritten. Pipeline preflight repeats qualification
and records interpreter, bubblewrap, libseccomp and wrapper identities.

Each MBPP sample receives a fresh filesystem and PID namespace, read-only Python
runtime and individual input files. The host home, repository, model cache,
credentials, GPU and network are absent. Its working directories are size-limited
tmpfs mounts. CPU, address-space, file-size and descriptor limits remain active;
seccomp denies `fork`, `vfork`, `clone` and `clone3`. This is an explicit
single-process candidate execution protocol. An infrastructure startup failure
raises; it is not counted as a model error, and there is no unsafe fallback.

HumanEval+ uses the original **EvalPlus 0.3.1** scorer with its complete
**v0.1.10 / 164-task** fixture. Cross-family preparation copies that fixture to
`data/crossfamily/humanevalplus/HumanEvalPlus.jsonl`; its hash must equal the prepared
`dataset_metadata.json`. The entire official scorer executes inside the native
boundary, with only three individual read-only input files and one dedicated
empty result directory mounted. The inherited host cache/environment is absent.

EvalPlus's trusted coordinator needs multiprocessing. The worker preserves its
official grading, tolerances and time limits, and wraps its `unsafe_execute`
entry point to install the same irreversible process-creation filter **inside
each candidate process before candidate execution**. A separate harmless child
probe checks that filter first. The coordinator checks the exact 0.3.1 signature,
sets a Linux `fork` multiprocessing context, and uses the declared fixed worker
count (1–16). A guard-installation failure invalidates the entire attempt. This
supports both ordinary-user and host-UID-0 callers without treating root-exempt
`RLIMIT_NPROC` as a security bound.

Resource limits are per process. The admitted outer host task must reserve the
aggregate RAM/CPU for its declared evaluator worker count; bubblewrap is not a
cgroup memory scheduler. A parent wall timeout kills the entire PID namespace.
All task/sample IDs and exported solution bytes are checked after official
scoring. Saved artifacts include official results, dataset/evaluation metadata,
environment, native runtime and stdout. No scorer can make hostile Python
self-verification into a tamper-proof correctness oracle; this boundary protects
the host and preserves the stated benchmark procedure.

Primary sources inspected:

- [Bubblewrap security model and namespace requirements](https://github.com/containers/bubblewrap/blob/main/README.md)
- [EvalPlus v0.3.1 candidate execution](https://github.com/evalplus/evalplus/blob/v0.3.1/evalplus/eval/__init__.py)
- [EvalPlus v0.3.1 evaluator and process pool](https://github.com/evalplus/evalplus/blob/v0.3.1/evalplus/evaluate.py)

The math grader can use `improving.native_sandbox.run_python` with individual
read-only pinned grader files and the default process-denial policy. Its input is
passed as an explicit JSON file/argument; no generated expression is imported or
evaluated in the host process.
