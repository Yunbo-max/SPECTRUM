#!/usr/bin/env python3
"""Make a prospective, blinded human algorithm-label packet from verified programs.

Never infer strategy equivalence automatically from an AST fingerprint.
Task sampling is fixed BEFORE reading method outcomes. Human annotation is
still required; this creates NO fabricated semantic-diversity scores.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
from pathlib import Path


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def sha(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def save_new(path: Path, text: str, private: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise ValueError(f"Refusing to overwrite changed annotation packet {path}")
        return
    if private:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        with path.open("x", encoding="utf-8") as f:
            f.write(text)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args(argv)
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    case = plan["case"]
    if case["id"] != "c26" or case["kind"] != "semantic":
        raise ValueError("This tool only accepts the c26 sealed semantic plan")
    taskfile = Path(plan["task_file"])
    if sha(taskfile) != plan["task_file_sha256"]:
        raise ValueError("Original task pool changed after prospective selection")
    tasks = list(read_jsonl(taskfile))
    universe = {}
    for item in tasks:
        ident = item["task_id"]
        if ident in universe:
            raise ValueError("Duplicate task ID in task pool")
        universe[ident] = item
    if len(tasks) < case["task_count"]:
        raise ValueError("Cannot select the requested number of unique tasks")
    selected = sorted(universe, key=lambda k: hashlib.sha256(
        ("ICLR2027-semantic-blind-v1|" + k).encode()).hexdigest())[:case["task_count"]]
    chosen = set(selected)
    contents = {}
    for inp in plan["semantic_inputs"]:
        source = Path(inp["path"])
        if sha(source) != inp["sha256"]:
            raise ValueError(f"Verified code source changed: {source}")
        marker = source.parent / "complete.json"
        if not marker.is_file():
            raise FileNotFoundError(f"Missing completed evaluator receipt: {marker}")
        seal = json.loads(marker.read_text(encoding="utf-8"))
        if seal.get("files", {}).get(source.name) != inp["sha256"]:
            raise ValueError(f"Source program pool is not sealed by evaluator: {source}")
        per_task = {task: [] for task in selected}
        seen = set()
        for record in read_jsonl(source):
            task = record.get("task_id")
            if task not in chosen:
                continue
            key = (task, record.get("sample_id"))
            if key in seen:
                raise ValueError(f"Duplicated verifier sample in {source}")
            seen.add(key)
            if type(record.get("correct")) is not bool:
                raise ValueError(f"Missing verified correctness in {source}")
            if not record["correct"]:
                continue
            code = record.get("code")
            if not isinstance(code, str) or not code.strip():
                raise ValueError("Verified correct output has no extracted Python source")
            try:
                ast.parse(code)
            except SyntaxError as exc:
                raise ValueError(f"Verified correct candidate has invalid Python AST: {key}") from exc
            per_task[task].append((record["sample_id"], code))
        contents[inp["method"]] = per_task
    packet, private, coverage = [], [], []
    for task in selected:
        picked = []
        row = {"task_id": task}
        for method, by_task in contents.items():
            entries = sorted(by_task[task], key=lambda v: hashlib.sha256(
                f"ICLR2027-blind-samples-v1|{task}|{method}|{v[0]}".encode()).hexdigest())
            subset = entries[:case["per_arm_correct"]]
            row[f"{method}_correct"] = len(entries)
            row[f"{method}_selected"] = len(subset)
            for sample_id, code in subset:
                label = hashlib.sha256(
                    f"ICLR2027-blind-label-v1|{task}|{method}|{sample_id}".encode()
                ).hexdigest()[:16]
                picked.append((label, method, sample_id, code))
        # Method ordering is blinded and independent of code correctness.
        picked.sort(key=lambda v: v[0])
        coverage.append(row)
        for anonymous_id, method, sample_id, code in picked:
            packet.append({
                "anonymous_id": anonymous_id,
                "task_id": task,
                "problem_statement": universe[task].get("prompt", ""),
                "correct_by_native_verifier": True,
                "code": code,
                "human_strategy_class": None,
                "annotation_instructions": "Assign semantic algorithm family, not AST/syntax style. Record uncertainty.",
            })
            private.append({"anonymous_id": anonymous_id, "task_id": task,
                            "method": method, "sample_id": sample_id})
    root = Path(args.output_dir)
    save_new(root / "annotation_packet.jsonl", "".join(
        json.dumps(p, ensure_ascii=False) + "\n" for p in packet))
    save_new(root / "private_method_key.jsonl", "".join(
        json.dumps(row) + "\n" for row in private), private=True)
    fields = ["task_id"] + [f"{method}_{suffix}" for method in contents for suffix in ("correct","selected")]
    import io
    f = io.StringIO()
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(coverage)
    save_new(root / "coverage.csv", f.getvalue())
    save_new(root / "annotation_status.json", json.dumps({
        "status": "packet_created_no_human_labels",
        "selected_tasks": len(selected),
        "selected_correct_programs": len(packet),
        "strategy_annotation_completed": False,
        "semantic_effect_established": False,
        "evidence_sha256": {v["method"]: v["sha256"] for v in plan["semantic_inputs"]},
    }, indent=2) + "\n")
    print(json.dumps({"task_count": len(selected), "programs": len(packet),
                      "annotation_required": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
