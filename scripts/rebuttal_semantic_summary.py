#!/usr/bin/env python3
"""Summarize human labels for the predeclared c26 blinded packet, without models.

This is a sampled-correct-program human D4 audit on 40 prospectively selected
tasks. It is not semantic pass@64/coverage on all 500 MBPP tasks. Uncertain or
unreviewed labels remain missing; no AST hash becomes a human strategy label.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
from itertools import combinations
import json
from math import comb
from pathlib import Path
import random


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expected_richness(labels, budget=4):
    """Uniform without-replacement expected distinct human families."""
    if len(labels) < budget or any(label is None for label in labels):
        return None
    denominator = comb(len(labels), budget)
    return sum(1.0 - (comb(len(labels) - count, budget) / denominator
                      if len(labels) - count >= budget else 0.0)
               for count in Counter(labels).values())


def paired_interval(values, seed=20261107, draws=2000):
    if not values:
        return {"mean": None, "ci_low": None, "ci_high": None, "eligible_tasks": 0}
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws))
    return {"mean": sum(values) / n, "ci_low": means[int(.025 * (draws - 1))],
            "ci_high": means[int(.975 * (draws - 1))], "eligible_tasks": n}


def summarize(packet_dir, annotations):
    root = Path(packet_dir).resolve()
    status = json.loads((root / "annotation_status.json").read_text())
    sealed = status.get("sealed_files", {})
    required = {"annotation_packet.jsonl", "private_method_key.jsonl", "coverage.csv"}
    if not required <= set(sealed):
        raise ValueError("Use the v2 sealed c26 packet; historical unsealed packets are not admissible")
    for name, expected in sealed.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha(path) != expected:
            raise ValueError(f"Blinded source packet changed: {name}")
    packet_rows = rows(root / "annotation_packet.jsonl")
    packet = {r["anonymous_id"]: r for r in packet_rows}
    key_rows = rows(root / "private_method_key.jsonl")
    key = {r["anonymous_id"]: r for r in key_rows}
    if len(packet) != len(packet_rows) or len(key) != len(key_rows) or set(key) != set(packet):
        raise ValueError("Packet and private method key do not have the same unique IDs")
    with (root / "coverage.csv").open(newline="", encoding="utf-8") as stream:
        coverage = list(csv.DictReader(stream))
    tasks = [r["task_id"] for r in coverage]
    if len(tasks) != 40 or len(set(tasks)) != 40:
        raise ValueError("Semantic audit requires exactly the original 40 selected tasks")
    methods = sorted(name.removesuffix("_selected") for name in coverage[0] if name.endswith("_selected"))
    if len(methods) < 2:
        raise ValueError("Semantic comparison requires at least two source arms")
    labels, reviewers = {}, set()
    for row in rows(annotations):
        ident = row.get("anonymous_id")
        if ident not in packet or ident in labels:
            raise ValueError("Annotation has an unknown or repeated anonymous ID")
        if row.get("human_reviewed") is not True or not isinstance(row.get("annotator_id"), str) or not row["annotator_id"].strip():
            raise ValueError("Each supplied label needs human_reviewed=true and an annotator/adjudicator ID")
        if "human_strategy_class" not in row:
            raise ValueError("Supply human_strategy_class, with null for unresolved judgments")
        label = row["human_strategy_class"]
        if label is not None and (not isinstance(label, str) or not label.strip()):
            raise ValueError("A semantic family must be a nonempty string or null")
        labels[ident] = label
        reviewers.add(row["annotator_id"])
    groups = defaultdict(list)
    exports = {method: [] for method in methods}
    for ident, original in packet.items():
        source = key[ident]
        if source["task_id"] != original["task_id"] or source["method"] not in methods:
            raise ValueError("Private source mapping differs from blinded packet")
        label = labels.get(ident)
        groups[(source["task_id"], source["method"])].append(label)
        exports[source["method"]].append({"task_id": source["task_id"],
            "sample_id": source["sample_id"], "strategy_id": label})
    by_task = {}
    for row in coverage:
        task = row["task_id"]
        by_task[task] = {}
        for method in methods:
            current = groups[(task, method)]
            expected = int(row[f"{method}_selected"])
            if len(current) != expected or expected > 8:
                raise ValueError("Label population differs from the sealed sampled-correct pool")
            by_task[task][method] = {"selected_correct_programs": len(current),
                "labeled_programs": sum(v is not None for v in current),
                "human_D4": expected_richness(current)}
    pairs = []
    for left, right in combinations(methods, 2):
        eligible = [task for task in tasks if all(by_task[task][m]["human_D4"] is not None for m in (left, right))]
        differences = [by_task[t][right]["human_D4"] - by_task[t][left]["human_D4"] for t in eligible]
        pairs.append({"left": left, "right": right, "difference": "right_minus_left",
            "common_eligible_task_ids": eligible, "total_selected_tasks": 40,
            "sampled_correct_human_D4": paired_interval(differences)})
    return {"status": "human_labels_complete" if len(labels) == len(packet) and all(v is not None for v in labels.values()) else "human_labels_incomplete",
        "scope": "sampled_correct_human_D4_on_preselected_40_tasks",
        "source_packet_sha256": sha(root / "annotation_packet.jsonl"),
        "annotations_sha256": sha(annotations), "annotator_ids": sorted(reviewers),
        "total_selected_tasks": 40, "total_selected_programs": len(packet),
        "reviewed_programs": len(labels), "resolved_programs": sum(v is not None for v in labels.values()),
        "uncertainty": "paired task bootstrap, 2000 draws; not training-seed uncertainty",
        "semantic_pass_at_64_estimated": False, "per_task": by_task, "comparisons": pairs,
        "limitations": ["At most eight verified correct outputs per arm/task were annotated.",
            "The audit does not label all 64 outputs or all 500 MBPP tasks.",
            "Shared task-level family names require independent annotation and adjudication.",
            "Missing/unresolved labels exclude that task-arm from D4; all denominators remain visible."]}, exports


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-dir", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    source, output = Path(args.packet_dir).resolve(), Path(args.output_dir).resolve()
    if source == output or source in output.parents or output in source.parents:
        raise ValueError("Annotated summary must use a separate nonnested output directory")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Choose a fresh annotation-summary output directory")
    result, exports = summarize(source, args.annotations)
    output.mkdir(parents=True, exist_ok=True)
    (output / "semantic_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    # These joins deliberately leave all unsampled correct outputs unlabelled.
    # Full-output strategy metrics must remain unavailable for incomplete tasks.
    for index, (method, records) in enumerate(sorted(exports.items())):
        filename = f"arm_{index}_strategy_annotations.jsonl"
        (output / filename).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records))
        result.setdefault("native_annotation_exports", {})[method] = filename
    (output / "semantic_summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "output": str(output), "semantic_pass_at_64_estimated": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
