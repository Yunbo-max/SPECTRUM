"""Invoked ONLY inside improving.native_sandbox with fixed /input paths."""
from collections import defaultdict
import hashlib
from importlib.metadata import version
import json
import inspect
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys

_ORIGINAL_UNSAFE_EXECUTE = None


def guarded_unsafe_execute(*args, **kwargs):
    # Called after EvalPlus has created its candidate process, before any
    # candidate byte is compiled/executed. All native grading logic is retained.
    try:
        library = json.loads(Path('/sandbox/limits.json').read_text())['seccomp_library']
        spectrum_deny_process_creation(library)
    except BaseException:
        Path('/work/process-guard-failure').write_text('Candidate process guard failed')
        raise
    return _ORIGINAL_UNSAFE_EXECUTE(*args, **kwargs)


def _guard_probe(connection):
    try:
        library = json.loads(Path('/sandbox/limits.json').read_text())['seccomp_library']
        spectrum_deny_process_creation(library)
        try:
            os.fork()
        except PermissionError:
            connection.send(True)
        else:
            connection.send(False)
    except BaseException:
        connection.send(False)
    finally:
        connection.close()


def main():
    global _ORIGINAL_UNSAFE_EXECUTE
    if version("evalplus") != "0.3.1":
        raise ValueError("Official scorer must be evalplus==0.3.1")
    if os.environ.get("HUMANEVAL_OVERRIDE_PATH") != "/input/HumanEvalPlus.jsonl":
        raise ValueError("Native worker requires the explicit read-only pinned fixture")
    from evalplus.data import get_human_eval_plus
    tasks = get_human_eval_plus()
    metadata = json.loads(Path("/input/dataset_metadata.json").read_text())
    release = metadata["datasets"]["HumanEvalPlus"]
    if (len(tasks) != 164 or release["version"] != "v0.1.10" or
            hashlib.sha256(Path("/input/HumanEvalPlus.jsonl").read_bytes()).hexdigest() != release["sha256"]):
        raise ValueError("Native fixture differs from prepared release")
    groups = defaultdict(list)
    source = Path("/input/samples.jsonl")
    for line in source.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("task_id") not in tasks or not isinstance(row.get("solution"), str):
            raise ValueError("Unexpected task or non-string solution")
        groups[row["task_id"]].append(row["solution"])
    if set(groups) != set(tasks):
        raise ValueError("Require every HumanEval+ task")
    parallel = int(sys.argv[1])
    if not 1 <= parallel <= 16:
        raise ValueError('Native evaluator parallelism must be between 1 and 16')
    multiprocessing.set_start_method('fork', force=True)
    receiver, sender = multiprocessing.Pipe(duplex=False)
    probe = multiprocessing.Process(target=_guard_probe, args=(sender,))
    probe.start()
    sender.close()
    probe.join(timeout=10)
    if probe.is_alive():
        probe.kill()
        probe.join()
    if probe.exitcode or not receiver.poll(1) or receiver.recv() is not True:
        raise RuntimeError('Native candidate child guard qualification failed')
    receiver.close()
    import evalplus.eval as native_eval
    from evalplus.evaluate import evaluate
    expected_parameters = ('dataset', 'entry_point', 'code', 'inputs', 'expected', 'time_limits',
                           'atol', 'fast_check', 'stat', 'details', 'progress')
    if tuple(inspect.signature(native_eval.unsafe_execute).parameters) != expected_parameters:
        raise ValueError('Unexpected EvalPlus unsafe_execute API; refusing an unguarded scorer')
    _ORIGINAL_UNSAFE_EXECUTE = native_eval.unsafe_execute
    native_eval.unsafe_execute = guarded_unsafe_execute
    samples = Path("/work/samples.jsonl")
    shutil.copyfile(source, samples)
    evaluate(dataset='humaneval', samples=str(samples), parallel=parallel,
             min_time_limit=1.0, gt_time_limit_factor=4.0)
    if Path('/work/process-guard-failure').exists():
        raise RuntimeError('A native candidate guard failed; this attempt has no eligible scores')
    result_path = samples.with_name("samples_eval_results.json")
    results = json.loads(result_path.read_text())
    returned = results.get("eval", {})
    if set(returned) != set(groups):
        raise ValueError("Native evaluator changed task universe")
    for task_id, expected in groups.items():
        actual = returned[task_id]
        if len(actual) != len(expected) or any(row.get("task_id") != task_id or row.get("solution") != solution
                for row, solution in zip(actual, expected)):
            raise ValueError("Native evaluator lost or reordered samples")
    output = Path("/output")
    shutil.copyfile(result_path, output / "samples_eval_results.json")
    shutil.copyfile("/input/dataset_metadata.json", output / "dataset_metadata.json")
    run_metadata = {"evalplus_version": version("evalplus"), "dataset": "humaneval",
        "dataset_release": release, "dataset_hash": results.get("hash"),
        "samples_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "task_count": len(groups), "sample_count": sum(map(len, groups.values())),
        "parallel": parallel, "min_time_limit": 1.0, "gt_time_limit_factor": 4.0,
        "max_memory_bytes_per_sample": int(os.environ["EVALPLUS_MAX_MEMORY_BYTES"]),
        "protocol": "official-base-and-plus-tests-no-sanitization", "execution_backend": "bwrap",
        "candidate_process_guard": "seccomp-deny-fork-clone-before-official-unsafe_execute",
        "candidate_process_guard_probe": "passed"}
    (output / "evaluation_metadata.json").write_text(json.dumps(run_metadata, indent=2) + "\n")
    (output / "environment.txt").write_text(f"evalplus=={version('evalplus')}\npython=={sys.version}\n")


if __name__ == "__main__":
    main()
