#!/usr/bin/env python3
"""Plan, explicitly run, or report one isolated continual-gain case.

Planning is standard-library only. It does not import torch, load a model,
prepare/download data, create a seed, or launch a study. All experiment source
and authored tests are generated_unexecuted until separately run by Local.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import traceback
import unicodedata
from uuid import uuid4


REPO = Path(__file__).resolve().parents[1]
PROTOCOL = "spectrum-continual-gains-v1"
CASE_PROTOCOL = "spectrum-continual-gains-case-isolation-v1"
DEFAULT_ROOT = "runs/continual_gains_isolated_v1"
METHODS = ("native", "sequential", "retention", "conflict")
SPLITS = ("train", "calibration", "validation", "eval")
NATIVE_EVALUATION_COUNTS = {"math": {"math500": 500}, "qa": {"mmlu_pro": 12032}}
MODEL_SUFFIXES = {".safetensors", ".bin", ".json", ".txt", ".model", ".jinja", ".tiktoken"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    # Match improving.utils.stable_hash, including JSON whitespace, for the
    # private-seed identity already sealed by prepare_text_data.
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode("utf-8")).hexdigest()


def file_sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def absolute(value):
    path = Path(value).expanduser()
    return (path if path.is_absolute() else REPO / path).resolve()


def store_once(path, value):
    """Publish complete immutable JSON; never replace an existing seal."""
    path = Path(path)
    contents = json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != contents:
                raise ValueError(f"Frozen file changed; use a fresh case root: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def load_spec():
    spec = read_json(REPO / "experiments/continual_gains/cases.json")
    if spec.get("protocol") != CASE_PROTOCOL or spec.get("study_protocol") != PROTOCOL:
        raise ValueError("Unexpected continual-gain catalog protocol")
    cases = spec["cases"]
    if [row["id"] for row in cases] != [f"cg{i:02d}" for i in range(16)]:
        raise ValueError("Continual-gain IDs must remain cg00..cg15")
    variants = [("frozen", ["math", "qa"]), ("frozen", ["qa", "math"]),
                ("self_distill", ["math", "qa"]), ("self_distill", ["qa", "math"])]
    for index, case in enumerate(cases):
        backbone, order = variants[index // 4]
        if (case["method"] != METHODS[index % 4] or case["backbone_update"] != backbone
                or case["order"] != order or case["rounds_per_domain"] != 1
                or case["output_leaf"] != case["id"]):
            raise ValueError(f"Case meaning changed: {case['id']}")
    return spec


def one_case(case_id):
    for case in load_spec()["cases"]:
        if case["id"] == case_id:
            return case
    raise ValueError(f"Unknown continual-gain case: {case_id}")


def case_directory(case, args):
    root = absolute(args.root)
    directory = root / case["id"]
    if directory.is_symlink() or directory.resolve() != directory:
        raise ValueError("Case directory must not alias another output directory")
    if (directory / "study").is_symlink():
        raise ValueError("Study output must not alias another lineage")
    return directory


@contextmanager
def exclusive(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the inode permanently: unlinking a lock permits a second live owner.
    with path.open("a+", encoding="utf-8") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"Another process owns this case: {path}") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def source_identity():
    paths = list((REPO / "src/improving").rglob("*.py"))
    paths += list((REPO / "scripts/continual_gain_cases").glob("cg*.py"))
    paths += list((REPO / "configs/continual_gains").glob("*.json"))
    paths += list(REPO.glob("requirements*.txt"))
    paths += [REPO / "scripts/run_continual_gains.py",
              REPO / "scripts/prepare_text_data.py",
              REPO / "configs/multidomain/text_math_learned.json",
              REPO / "configs/multidomain/text_qa_learned.json",
              REPO / "experiments/continual_gains/cases.json",
              REPO / "rounds/20261108-continual-gains/METHOD.md",
              REPO / "pyproject.toml"]
    files = {str(path.relative_to(REPO)): file_sha(path) for path in sorted(set(paths))}
    return {"files": files, "sha256": digest(files)}


def validate_config(config, case):
    """Preserve both original domain recipes; only host paths may differ."""
    if (config.get("protocol") != PROTOCOL or set(config.get("domains", {})) != {"math", "qa"}
            or config.get("order") != case["order"]
            or config.get("backbone_update") != case["backbone_update"]
            or config.get("rounds_per_domain") != case["rounds_per_domain"]):
        raise ValueError("Config order/backbone/protocol differs from the fixed case")
    for domain in ("math", "qa"):
        original = read_json(REPO / f"configs/multidomain/text_{domain}_learned.json")
        current = deepcopy(config["domains"][domain])
        if current.get("domain") != domain or current.get("seed_file") != config["seed_file"]:
            raise ValueError("Domain and shared private seed must agree")
        current["model"]["name"] = original["model"]["name"]
        current["data"]["output_dir"] = original["data"]["output_dir"]
        current["seed_file"] = original["seed_file"]
        if current != original:
            raise ValueError(f"Original {domain} training/data/calibration/evaluation recipe changed")
    if config["domains"]["math"]["model"] != config["domains"]["qa"]["model"]:
        raise ValueError("Both domains must use the same backbone settings")
    expected_controller = {"projection_max_cycles": 128, "projection_tolerance": 1e-10,
                           "retention_tolerance": 0.0}
    if config.get("controller") != expected_controller:
        raise ValueError("Controller budget differs from the authored case protocol")
    return config


def config_for(case, args, directory):
    config = read_json(REPO / case["config"])
    config["output_dir"] = str(directory / "study")
    if args.seed_file is not None:
        config["seed_file"] = args.seed_file
    for domain in ("math", "qa"):
        current = config["domains"][domain]
        current["seed_file"] = config["seed_file"]
        if args.model_path is not None:
            current["model"]["name"] = str(absolute(args.model_path))
        data_override = getattr(args, f"{domain}_data_root")
        if data_override is not None:
            # Keep the exact spelling used to prepare the source manifest.
            current["data"]["output_dir"] = data_override
    return validate_config(config, case)


def seed_identity(config):
    path = absolute(config["seed_file"])
    before = file_sha(path)
    record = read_json(path)
    seed = record.get("seed")
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError("Invalid private seed record; prepare inputs first")
    if file_sha(path) != before:
        raise ValueError("Private seed changed while planning")
    # Never copy the seed value into public configuration, logs, or a report.
    return {"path": str(path), "file_sha256": before, "seed_sha256": digest(seed)}


def normalized_prompt(value):
    return " ".join(unicodedata.normalize("NFKC", value).split())


def prepared_identity(config, seed):
    identities = {}
    global_identifiers, global_prompts = set(), {}
    for domain in ("math", "qa"):
        current = config["domains"][domain]
        root = absolute(current["data"]["output_dir"])
        manifest_path = root / "manifest.json"
        before = file_sha(manifest_path)
        manifest = read_json(manifest_path)
        identity = manifest["identity"]
        if (identity.get("domain") != domain or identity.get("data") != current["data"]
                or identity.get("seed_sha256") != seed["seed_sha256"]):
            raise ValueError(f"Prepared {domain} domain/data/seed binding differs")
        if identity.get("builder_sha256") != file_sha(REPO / "src/improving/text_tasks.py"):
            raise ValueError(f"Prepared {domain} data builder changed")
        expected_eval = NATIVE_EVALUATION_COUNTS[domain]
        expected_counts = {split: current["data"][split + "_size"] for split in SPLITS[:-1]}
        expected_counts["eval"] = sum(expected_eval.values())
        if (manifest.get("counts") != expected_counts
                or manifest.get("evaluation_counts") != expected_eval
                or set(manifest.get("output_hashes", {})) != {f"{split}.jsonl" for split in SPLITS}):
            raise ValueError(f"Prepared {domain} population differs from the complete native study")
        files, identifiers, prompts = {}, set(), {}
        for split in SPLITS:
            path = root / f"{split}.jsonl"
            sha = file_sha(path)
            if sha != manifest["output_hashes"][path.name]:
                raise ValueError(f"Prepared data changed: {path}")
            with path.open(encoding="utf-8") as stream:
                rows = [json.loads(line) for line in stream if line.strip()]
            if any(not isinstance(row, dict) for row in rows):
                raise ValueError(f"Non-object prepared task: {path}")
            ids = [row.get("task_id") for row in rows]
            if (len(rows) != expected_counts[split]
                    or any(not isinstance(item, str) or not item for item in ids)
                    or len(set(ids)) != len(ids)):
                raise ValueError(f"Prepared task IDs or count changed: {path}")
            if identifiers.intersection(ids) or global_identifiers.intersection(ids):
                raise ValueError(f"Cross-split task overlap in {domain}")
            identifiers.update(ids)
            global_identifiers.update(ids)
            for row in rows:
                if row.get("split") != split or not isinstance(row.get("prompt"), str) or not row["prompt"]:
                    raise ValueError(f"Malformed prepared task in {path}")
                text = row.get("original_prompt", row["prompt"])
                if not isinstance(text, str) or not text:
                    raise ValueError(f"Missing original prompt in {path}")
                key = normalized_prompt(text)
                if key in prompts and prompts[key] != split:
                    raise ValueError(f"Cross-split prompt overlap in {domain}")
                prompts[key] = split
                for prompt in (text, row["prompt"]):
                    normalized = normalized_prompt(prompt)
                    if normalized in global_prompts and global_prompts[normalized] != split:
                        raise ValueError("Cross-domain/split prompt overlap")
                    global_prompts[normalized] = split
                if split == "calibration" and (not isinstance(row.get("reference"), str)
                                                 or not row["reference"]):
                    raise ValueError(f"Calibration reference missing in {path}")
            if split == "eval" and dict(Counter(row.get("benchmark") for row in rows)) != expected_eval:
                raise ValueError(f"Native benchmark denominator mismatch in {domain}")
            if file_sha(path) != sha:
                raise ValueError(f"Prepared tasks changed while planning: {path}")
            files[split] = {"path": str(path), "sha256": sha, "count": len(rows),
                            "ordered_task_ids_sha256": digest(ids)}
        native_sources = {}
        if domain == "math":
            for relative, receipt in manifest.get("sources", {}).get("prm800k", {}).items():
                logical = PurePosixPath(relative)
                if logical.is_absolute() or ".." in logical.parts:
                    raise ValueError("Unsafe prepared native-source path")
                path = root / "sources/prm800k" / relative
                actual = file_sha(path)
                if actual != receipt.get("sha256"):
                    raise ValueError(f"Native math source changed: {path}")
                native_sources[relative] = {"path": str(path), "sha256": actual}
            if not {"prm800k/grading/grader.py", "prm800k/grading/math_normalize.py"}.issubset(native_sources):
                raise ValueError("Prepared math inputs lack sealed native grading sources")
        if file_sha(manifest_path) != before:
            raise ValueError("Prepared data manifest changed while planning")
        identities[domain] = {"manifest": str(manifest_path), "manifest_sha256": before,
                              "files": files, "native_sources": native_sources}
    return identities


def model_identity(config):
    settings = config["domains"]["math"]["model"]
    root = absolute(settings["name"])
    if not root.is_dir() or not (root / "config.json").is_file():
        raise FileNotFoundError("Plan requires an existing local model snapshot; use --model-path")
    indexes = sorted(root.glob("*.safetensors.index.json"))
    if not indexes:
        raise ValueError("Expected the complete sharded official backbone snapshot")
    for path in indexes:
        shards = set(read_json(path)["weight_map"].values())
        if not shards:
            raise ValueError("Empty model shard index")
        for shard in shards:
            logical = PurePosixPath(shard)
            if logical.is_absolute() or ".." in logical.parts or not (root / shard).is_file():
                raise ValueError("Missing or unsafe model shard in the official snapshot")
    files = {str(path.relative_to(root)): file_sha(path)
             for path in sorted(root.rglob("*")) if path.is_file() and path.suffix in MODEL_SUFFIXES}
    if not any(name.startswith("tokenizer") for name in files):
        raise ValueError("Model snapshot has no tokenizer artifacts")
    return {"path": str(root), "files": files, "sha256": digest(files)}


def validate_paths(config, directory):
    inputs = [absolute(config["domains"][domain]["data"]["output_dir"]) for domain in ("math", "qa")]
    inputs += [absolute(config["domains"]["math"]["model"]["name"])]
    inputs += [REPO / name for name in ("src", "scripts", "configs", "experiments", "rounds")]
    for path in inputs:
        path = path.resolve()
        if directory == path or directory.is_relative_to(path) or path.is_relative_to(directory):
            raise ValueError("Case output overlaps a source/input directory")
    if absolute(config["seed_file"]).is_relative_to(directory):
        raise ValueError("Private seed must exist outside case outputs")


def _check_selectors(config, args):
    if args.seed_file is not None and args.seed_file != config["seed_file"]:
        raise ValueError("Seed selector differs from the frozen plan")
    if args.model_path is not None and absolute(args.model_path) != absolute(config["domains"]["math"]["model"]["name"]):
        raise ValueError("Model selector differs from the frozen plan")
    for domain in ("math", "qa"):
        value = getattr(args, f"{domain}_data_root")
        if value is not None and value != config["domains"][domain]["data"]["output_dir"]:
            raise ValueError("Data selector differs from the frozen plan")


def read_plan(case, args):
    directory = case_directory(case, args)
    path = directory / "plan.json"
    if read_json(directory / "plan.sha256.json") != {"sha256": file_sha(path)}:
        raise ValueError("Frozen plan hash changed")
    plan = read_json(path)
    if (plan.get("protocol") != CASE_PROTOCOL or plan.get("case") != case
            or plan.get("root") != str(directory)
            or plan.get("working_directory") != str(REPO)
            or plan.get("config_file") != str(directory / "config.json")):
        raise ValueError("Frozen plan points at another case or protocol")
    config_path = directory / "config.json"
    if file_sha(config_path) != plan["config_sha256"]:
        raise ValueError("Frozen config changed")
    config = validate_config(read_json(config_path), case)
    if config["output_dir"] != str(directory / "study"):
        raise ValueError("Frozen study output points at another case")
    validate_paths(config, directory)
    _check_selectors(config, args)
    if source_identity() != plan["source"]:
        raise ValueError("Executable source changed; use the original revision or a new case root")
    seed = seed_identity(config)
    if seed != plan["inputs"]["seed"]:
        raise ValueError("Private seed changed after planning")
    if prepared_identity(config, seed) != plan["inputs"]["data"]:
        raise ValueError("Prepared data changed after planning")
    if model_identity(config) != plan["inputs"]["model"]:
        raise ValueError("Model snapshot changed after planning")
    return plan


def build_plan(case, args):
    directory = case_directory(case, args)
    with exclusive(directory / ".case.lock"):
        if (directory / "plan.json").exists():
            return read_plan(case, args)
        if (directory / "study").exists():
            raise ValueError("Unplanned study outputs exist; retain them and choose a fresh root")
        config = config_for(case, args, directory)
        validate_paths(config, directory)
        seed = seed_identity(config)
        inputs = {"seed": seed, "data": prepared_identity(config, seed), "model": model_identity(config)}
        source = source_identity()
        config_path = directory / "config.json"
        store_once(config_path, config)
        plan = {"schema": 1, "protocol": CASE_PROTOCOL, "status": "generated_unexecuted",
                "parent_revision": load_spec()["parent_revision"], "case": case,
                "root": str(directory), "working_directory": str(REPO),
                "config_file": str(config_path), "config_sha256": file_sha(config_path),
                "source": source, "inputs": inputs,
                "geometry_policy": "first_domain_fit_once_then_frozen",
                "guard_policy": "final_candidate_veto_only",
                "memory_policy": "seen_domain_fit_references_not_student_sft",
                "execution_requires": "run --execute"}
        store_once(directory / "plan.json", plan)
        store_once(directory / "plan.sha256.json", {"sha256": file_sha(directory / "plan.json")})
        return plan


def _study_api():
    """The only project import; planning never reaches this function."""
    sys.path.insert(0, str(REPO / "src"))
    from improving.continual_gain_study import run_continual_gain_study, summarize_continual_gain_study
    return run_continual_gain_study, summarize_continual_gain_study


@contextmanager
def repository_cwd():
    previous = Path.cwd()
    os.chdir(REPO)
    try:
        yield
    finally:
        os.chdir(previous)


def append_attempt(directory, record):
    with (directory / "attempt.log").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def now():
    return datetime.now(timezone.utc).isoformat()


def execute_case(case, args):
    directory = case_directory(case, args)
    if not (directory / "plan.json").exists():
        build_plan(case, args)
    if not args.execute:
        plan = read_plan(case, args)
        return {"status": "planned", "dry_run": True, "case": case["id"],
                "plan": str(directory / "plan.json"), "output_dir": str(directory / "study"),
                "source_sha256": plan["source"]["sha256"]}
    with exclusive(directory / ".case.lock"):
        plan = read_plan(case, args)
        config = read_json(plan["config_file"])
        identifier = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid4().hex[:8]
        attempt = directory / "attempts" / identifier
        attempt.mkdir(parents=True, exist_ok=False)
        base = {"attempt": identifier, "case": case["id"], "method": case["method"],
                "plan_sha256": file_sha(directory / "plan.json"),
                "config_sha256": plan["config_sha256"], "source_sha256": plan["source"]["sha256"],
                "started_at": now(), "pid": os.getpid(), "resume": bool(args.resume)}
        store_once(attempt / "started.json", base)
        append_attempt(directory, {**base, "event": "started"})
        outcome, error_text = None, None
        try:
            with (attempt / "stdout.log").open("x", encoding="utf-8") as stdout, \
                    (attempt / "stderr.log").open("x", encoding="utf-8") as stderr:
                with redirect_stdout(stdout), redirect_stderr(stderr), repository_cwd():
                    try:
                        run, summarize = _study_api()
                        result = run(config, case["method"], resume=args.resume)
                        # The real runner has already fully verified its report.
                        # Avoid a second pass over every model and raw record.
                        report = result["report"] if "report" in result else summarize(config)
                        if result.get("status") != "completed" or report.get("status") != "complete":
                            raise RuntimeError("Runner returned without a complete, verified study")
                        outcome = {"status": "completed", "case": case["id"],
                                   "result": result, "report": report}
                    except BaseException:
                        traceback.print_exc(file=stderr)
                        raise
            store_once(attempt / "result.json", outcome)
            return outcome
        except BaseException as error:
            error_text = f"{type(error).__name__}: {error}"
            raise
        finally:
            receipt = {**base, "ended_at": now(), "event": "completed" if outcome is not None and error_text is None else "failed",
                       "error": error_text,
                       "stdout_sha256": file_sha(attempt / "stdout.log") if (attempt / "stdout.log").is_file() else None,
                       "stderr_sha256": file_sha(attempt / "stderr.log") if (attempt / "stderr.log").is_file() else None}
            if (attempt / "result.json").is_file():
                receipt["result_sha256"] = file_sha(attempt / "result.json")
            store_once(attempt / "exit.json", receipt)
            append_attempt(directory, receipt)


def report_case(case, args):
    directory = case_directory(case, args)
    if not (directory / "plan.json").exists():
        return {"case": case["id"], "status": "unplanned", "root": str(directory)}
    plan = read_plan(case, args)
    config = read_json(plan["config_file"])
    with repository_cwd():
        _, summarize = _study_api()
        report = summarize(config)
    return {"case": case["id"], "root": str(directory), "plan_sha256": file_sha(directory / "plan.json"),
            "report": report}


def make_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "run", "report"):
        child = subparsers.add_parser(command)
        child.add_argument("--case", help="Fixed cg00..cg15 case (wrapper supplies it)")
        child.add_argument("--root", default=DEFAULT_ROOT)
        child.add_argument("--model-path", default=None, help="Existing local sharded model snapshot")
        child.add_argument("--seed-file", default=None, help="Existing private seed; never created here")
        child.add_argument("--math-data-root", default=None, help="Exact output_dir spelling in the prepared math manifest")
        child.add_argument("--qa-data-root", default=None, help="Exact output_dir spelling in the prepared QA manifest")
        if command == "run":
            child.add_argument("--execute", action="store_true", help="Explicitly permit this single study execution")
            child.add_argument("--resume", action="store_true", help="Reuse only exactly bound, verified stage receipts")
    return parser


def main(argv=None, *, fixed_case=None):
    parser = make_parser()
    args = parser.parse_args(argv)
    if fixed_case is not None:
        if args.case is not None:
            parser.error("This wrapper owns its fixed case ID; do not pass --case")
        args.case = fixed_case
    if args.case is None and args.command != "report":
        parser.error("--case is required for plan/run; each invocation handles one case")
    if args.command == "report" and args.case is None:
        result = {"protocol": CASE_PROTOCOL,
                  "cases": [report_case(case, args) for case in load_spec()["cases"]]}
    else:
        case = one_case(args.case)
        if args.command == "plan":
            plan = build_plan(case, args)
            result = {"status": "planned", "case": case["id"],
                      "plan": str(case_directory(case, args) / "plan.json"),
                      "source_sha256": plan["source"]["sha256"]}
        elif args.command == "run":
            result = execute_case(case, args)
        else:
            result = report_case(case, args)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
