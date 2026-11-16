#!/usr/bin/env python3
"""CPU-only MBPP+ re-evaluation of existing generated completions.

Reuses the 64 generated samples per task from an existing evaluation.jsonl,
runs the EvalPlus MBPP+ tests locally (no GPU), and recomputes pass@k plus
the exact-program AST metrics (C64 coverage and budget-4 D4-style counts)
on the MBPP+-correct subset with the project's own metrics module.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", required=True, help="existing evaluation.jsonl with 64 samples/task")
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--parallel", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    from improving.data import read_jsonl
    from improving.metrics import summarize_records
    from improving.utils import atomic_json

    records = read_jsonl(Path(args.records))
    if not records:
        raise SystemExit(f"no records in {args.records}")
    per_task = {}
    for r in records:
        per_task.setdefault(r["task_id"], []).append(r)
    counts = {t: len(v) for t, v in per_task.items()}
    print(f"records: {len(records)} samples, {len(per_task)} tasks, samples/task = {set(counts.values())}", flush=True)

    # MBPP+ v0.2.0 covers a 378-task subset of the 500-task MBPP; evaluate only
    # tasks present in the official plus dataset and report that universe size.
    from evalplus.data import get_mbpp_plus
    mbppplus_tasks = set(get_mbpp_plus().keys())
    records = [r for r in records if r["task_id"] in mbppplus_tasks]
    if not records:
        raise SystemExit("no records fall inside the MBPP+ task universe")
    print(f"records inside MBPP+ universe: {len(records)}", flush=True)

    # Export to evalplus samples format (task_id + extracted solution code).
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    samples_path = outdir / "mbppplus_samples.jsonl"
    from improving.verification import _solution_code
    lines = []
    for r in records:
        code = _solution_code({"entry_point": r.get("entry_point", "solution"), "completion_mode": "completion"}, r.get("completion", ""), code_extraction="first_fence")
        lines.append(json.dumps({"task_id": r["task_id"], "solution": code}))
    # The official harness asserts samples cover the FULL MBPP+ universe; pad
    # missing tasks with an empty solution (fails, then discarded). Real metric
    # universe = the 224-task intersection, stated explicitly in the report.
    missing = sorted(mbppplus_tasks - {r["task_id"] for r in records})
    lines += [json.dumps({"task_id": tid, "solution": ""}) for tid in missing]
    samples_path.write_text("\n".join(lines) + "\n")
    print(f"samples exported: {samples_path} (padded {len(missing)} empty for full-universe assert)", flush=True)

    # Run the official MBPP+ harness locally (CPU subprocess execution).
    os_marker = outdir / "samples_eval_results.json"
    from evalplus.evaluate import evaluate
    evaluate(dataset="mbpp", samples=str(samples_path), parallel=args.parallel,
             i_just_wanna_run=True, min_time_limit=1.0)
    # evalplus writes the results next to the samples file with the fixed name.
    results_path = samples_path.with_name(samples_path.name.replace(".jsonl", "_eval_results.json"))
    if not results_path.is_file():
        results_path = outdir / "samples_eval_results.json"
    if not results_path.is_file():
        raise SystemExit("evalplus did not produce samples_eval_results.json")
    results = json.loads(results_path.read_text())
    if isinstance(results, dict):
        results = results.get("eval", [])
    if isinstance(results, dict):
        # evalplus 0.3.1: {"eval": {task_id: [rows]}} — flatten per-task lists.
        rows = []
        for lst in results.values():
            rows.extend(lst)
        results = rows
    print(f"results loaded: {len(results)} rows", flush=True)

    # Map back by (task_id, solution) and mark MBPP+-correct (plus tests pass).
    verdict = {}
    for row in results:
        key = (row["task_id"], row.get("solution", ""))
        verdict[key] = row
    verified = []
    mapped = 0
    for r in records:
        code = _solution_code({"entry_point": r.get("entry_point", "solution"), "completion_mode": "completion"}, r.get("completion", ""), code_extraction="first_fence")
        row = verdict.get((r["task_id"], code))
        if row is None:
            continue
        mapped += 1
        plus_ok = row.get("plus_status") == "pass"
        base_ok = row.get("base_status") == "pass"
        verified.append({**r, "code": code, "correct": bool(plus_ok), "status": "passed" if plus_ok else "failed",
                         "mbppplus_base_pass": bool(base_ok), "mbppplus_plus_pass": bool(plus_ok),
                         "evaluation_backend": "local", "evaluation_protocol": "mbppplus-v0.2.0-local"})
    print(f"mapped results: {mapped}/{len(records)}", flush=True)
    from improving.data import write_jsonl
    write_jsonl(outdir / "mbppplus_verified.jsonl", verified)

    evaluated_tasks = sorted({v["task_id"] for v in verified})
    expected = {t: 64 for t in evaluated_tasks}
    summary = summarize_records(verified, ks=[1, 4, 8, 16, 32, 64], correct_budget=4,
                                correct_budgets=[4, 8, 16, 32, 64],
                                bootstrap_samples=2000, seed=args.seed,
                                expected_samples=expected)
    atomic_json(outdir / "mbppplus_metrics.json", summary)
    agg = summary["aggregate"]
    pk = agg.get("pass_at_k", {})
    ex = agg.get("exact_program", {})
    print(json.dumps({
        "tasks": len(evaluated_tasks),
        "samples": len(verified),
        "pass@64": pk.get("64", {}).get("mean"),
        "pass@32": pk.get("32", {}).get("mean"),
        "pass@1": pk.get("1", {}).get("mean"),
        "C64_coverage": ex.get("coverage_at_k"),
        "D4_correct_matched_coverage": ex.get("correct_matched_coverage"),
        "unique_fraction": ex.get("unique_fraction"),
        "effective_label_count": ex.get("effective_label_count"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
