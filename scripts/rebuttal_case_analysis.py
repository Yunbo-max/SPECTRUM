#!/usr/bin/env python3
"""Read-only, task-paired rebuttal table builder for sealed MBPP native metrics.

Use --input cNN=/path/to/evaluation.metrics.json to bind recovered historical
evidence; otherwise read each new independent case root. No training, no
execution, no model calls; never compare n16 with n64 or 512 with 4096.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "experiments/iclr2027_rebuttal/cases.json"

PAIRS = [
    ("c36","c01"), ("c01","c02"), ("c01","c03"), ("c01","c04"), ("c06","c07"),
    ("c08","c09"), ("c10","c11"), ("c01","c05"), ("c01","c27"),
    ("c01","c12"), ("c01","c13"), ("c14","c15"), ("c18","c19"),
    ("c01","c31"), ("c01","c23"), ("c01","c24"), ("c01","c28"),
    ("c01","c29"), ("c01","c30"),
]


def hash_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda:f.read(1<<20),b""):
            result.update(data)
    return result.hexdigest()


def metric_file(case_id, root: Path, cases: dict, explicit: dict) -> Path:
    if case_id in explicit:
        return explicit[case_id]
    row = cases[case_id]
    if row["kind"] != "train":
        raise ValueError(f"{case_id} is not a native training case")
    return root / case_id / "run" / row["method"] / f"round_{row['rounds']}" / "evaluation.metrics.json"


def load_metric(path: Path, case: dict) -> dict:
    marker = path.parent / "complete.json"
    if not marker.is_file():
        raise ValueError(f"Unsealed metrics; require a native completed round: {path}")
    seal = json.loads(marker.read_text(encoding="utf-8"))
    if (seal.get("status") != "completed"
            or seal.get("files", {}).get(path.name) != hash_file(path)
            or not (path.parent / "evaluation.verified.jsonl").is_file()):
        raise ValueError(f"Metrics hash/checkpoint receipt/verified outcomes missing: {path}")
    source_manifest = path.parents[2] / "manifest.json"
    if not source_manifest.is_file():
        raise ValueError(f"Missing training provenance in {path.parents[2]}")
    source = json.loads(source_manifest.read_text(encoding="utf-8"))["config"]
    original = json.loads((ROOT/"configs/final/assets.json").read_text(encoding="utf-8"))["models"]
    model_alias = original[case["model"]]["repo_id"]
    if (not str(source["model"]["name"]).endswith(model_alias)
            or source["model"].get("revision") not in (None,original[case["model"]]["revision"])
            or int(source.get("seed", -1)) != case["seed"]
            or source.get("generation", {}).get("train_samples") != case["train_samples"]
            or source.get("generation", {}).get("max_new_tokens") != case["max_new_tokens"]
            or source.get("generation", {}).get("eval_samples") != 64
            or case["method"] not in source.get("methods", [])
            or path.parent.parent.name != case["method"]
            or path.parent.name != f"round_{case['rounds']}"):
        raise ValueError(f"Claimed method/model/seed/sampling mismatch: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    protocol = obj.get("protocol", {})
    agg = obj.get("aggregate", {})
    if (protocol.get("expected_samples") != 64 or agg.get("task_count") != 500
            or agg.get("sample_count") != 32000 or len(obj.get("per_task", {})) != 500):
        raise ValueError(f"{path}: requires exactly 500 MBPP tasks x 64 verified samples")
    required = {"1", "16", "64"}
    if (not required <= set(agg.get("pass_at_k", {}))
            or "64" not in agg.get("implementation_proxy", {}).get("coverage_at_k", {})):
        raise ValueError(f"{path}: mandatory success and AST metrics missing")
    return obj


def _task_value(entry: dict, field: str):
    if field.startswith("pass@"):
        return entry["pass_at_k"].get(field.split("@")[1])
    proxy = entry.get("implementation_proxy", {})
    if field == "C64":
        return proxy.get("coverage_at_k", {}).get("64")
    if field == "D4":
        return proxy.get("correct_matched_coverage_at_budgets", {}).get("4")
    raise ValueError(field)


def paired(a: dict, b: dict, *, nboot=2000, seed=20261107) -> dict:
    common = sorted(set(a["per_task"]) & set(b["per_task"]))
    if len(common) != 500 or set(a["per_task"]) != set(b["per_task"]):
        raise ValueError("Paired comparisons require identical 500-task identities")
    out = {"paired_task_count":500, "bootstrap_unit":"task_not_independent_training_seed"}
    for field in ("pass@1","pass@16","pass@64","C64","D4"):
        va = [_task_value(a["per_task"][k],field) for k in common]
        vb = [_task_value(b["per_task"][k],field) for k in common]
        both = [i for i in range(len(common)) if va[i] is not None and vb[i] is not None]
        only_a = sum(va[i] is not None and vb[i] is None for i in range(len(common)))
        only_b = sum(va[i] is None and vb[i] is not None for i in range(len(common)))
        neither = len(common)-len(both)-only_a-only_b
        if field != "D4" and (len(both) != 500 or any(not isinstance(va[i],(int,float))
                                                     or not isinstance(vb[i],(int,float)) for i in both)):
            raise ValueError(f"Incomplete or nonnumeric field {field}")
        if not both:
            out[field] = {"estimate":None,"CI95":None,"eligible_both":0,
                          "only_left":only_a,"only_right":only_b,"neither":neither}
            continue
        differences = [float(vb[i])-float(va[i]) for i in both]
        mean = sum(differences)/len(differences)
        rng = random.Random(seed + {"pass@1":1,"pass@16":16,"pass@64":64,"C64":1064,"D4":2004}[field])
        boot = []
        for _ in range(nboot):
            boot.append(sum(differences[rng.randrange(len(differences))]
                            for _ in differences)/len(differences))
        boot.sort()
        out[field] = {
            "estimate_right_minus_left":mean,
            "ci95_task_bootstrap":[boot[int(0.025*(nboot-1))],
                                   boot[int(0.975*(nboot-1))]],
            "eligible_both":len(both),"only_left":only_a,
            "only_right":only_b,"neither":neither,
        }
    return out


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",default="runs/iclr2027_rebuttal_isolated_v1")
    parser.add_argument("--output-dir",required=True)
    parser.add_argument("--input",action="append",default=[],
                        help="CASE=/absolute/sealed/evaluation.metrics.json (recovered historical result)")
    parser.add_argument("--pair",action="append",default=[],
                        help="LEFT:RIGHT case comparison; if omitted use fixed canonical pair set")
    parser.add_argument("--bootstrap",type=int,default=2000)
    args=parser.parse_args(argv)
    if args.bootstrap < 100:
        raise ValueError("At least 100 task bootstrap draws required")
    rows=json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    cases={x["id"]:x for x in rows}
    external={}
    for raw in args.input:
        if "=" not in raw:
            raise ValueError(f"Expected CASE=/path, got {raw}")
        key,path=raw.split("=",1)
        if key not in cases or key in external:
            raise ValueError("Unknown or repeated explicit case input")
        external[key]=Path(path).expanduser().resolve()
    pairs=[]
    for raw in args.pair:
        if ":" not in raw:raise ValueError("Use LEFT:RIGHT --pair syntax")
        left,right=raw.split(":",1)
        if left not in cases or right not in cases or left==right:
            raise ValueError("Unknown or identical pair ID")
        pairs.append((left,right))
    if not pairs:
        pairs=PAIRS
    root=Path(args.root).expanduser().resolve()
    sources={}
    for left,right in pairs:
        for ident in (left,right):
            if ident in sources:
                continue
            path=metric_file(ident,root,cases,external)
            if not path.is_file():
                sources[ident]={"status":"missing","path":str(path)}
                continue
            metric=load_metric(path, cases[ident])
            sources[ident]={"status":"validated","path":str(path),
                            "sha256":hash_file(path),"metric":metric}
    results=[]
    for left,right in pairs:
        if sources[left]["status"] != "validated" or sources[right]["status"] != "validated":
            results.append({"left":left,"right":right,"status":"missing_source",
                            "left_status":sources[left]["status"],"right_status":sources[right]["status"]})
            continue
        # Protocol-level comparability is validated explicitly by the reviewer
        # case spec; different model, seed, data/length should not be paired here.
        aa,bb=cases[left],cases[right]
        if aa["model"]!=bb["model"] or aa["seed"]!=bb["seed"] or aa["max_new_tokens"]!=bb["max_new_tokens"]:
            raise ValueError(f"Cannot pair mismatched model/seed/length: {left} vs {right}")
        result=paired(sources[left]["metric"],sources[right]["metric"],
                      nboot=args.bootstrap)
        results.append({"left":left,"right":right,"status":"paired_500_tasks",**result})
    out=Path(args.output_dir).expanduser().resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Use a fresh empty --output-dir; never overwrite prior evidence analysis")
    out.mkdir(parents=True,exist_ok=True)
    payload={"protocol":"iclr2027-100percent-readonly-task-paired-v1",
             "status":"observed_where_validated_not_imputed",
             "sources":{k:{k2:v2 for k2,v2 in v.items() if k2!="metric"} for k,v in sources.items()},
             "comparisons":results,
             "limitations":["Within-run task bootstrap is not independent training variation.",
                            "Correct-conditioned D4 is evaluated on common eligible tasks only.",
                            "Different benchmark versions/generation policies cannot be combined."],
             }
    (out/"pairwise.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    with (out/"pairwise.csv").open("w",newline="",encoding="utf-8") as handle:
        w=csv.DictWriter(handle,fieldnames=["left","right","status","metric",
                                            "right_minus_left","ci95_low","ci95_high",
                                            "eligible_both","only_left","only_right","neither"])
        w.writeheader()
        for row in results:
            if row["status"]!="paired_500_tasks":
                w.writerow({"left":row["left"],"right":row["right"],"status":row["status"]})
                continue
            for key in ("pass@1","pass@16","pass@64","C64","D4"):
                value=row[key]
                bounds=value.get("ci95_task_bootstrap") or [None,None]
                w.writerow({"left":row["left"],"right":row["right"],"status":row["status"],
                            "metric":key,"right_minus_left":value.get("estimate_right_minus_left"),
                            "ci95_low":bounds[0],"ci95_high":bounds[1],
                            "eligible_both":value["eligible_both"],
                            "only_left":value["only_left"],"only_right":value["only_right"],
                            "neither":value["neither"]})
    print(json.dumps({"output_dir":str(out),"compared":sum(r["status"]=="paired_500_tasks" for r in results),
                      "missing":sum(r["status"]=="missing_source" for r in results)}))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
