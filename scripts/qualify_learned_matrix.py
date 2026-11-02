#!/usr/bin/env python3
"""One real-model learned-gain calibration qualification for cross-family or text.

No SFT or benchmark evaluation. Does not claim the resulting spectral policy
improves correctness. Preserves failed/partial artifacts for diagnosis.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def settings_for(config):
    """Select exact train/reference and generation inputs without dataset download."""
    if "domain" in config:
        if config["domain"] not in {"math", "qa"}:
            raise ValueError("Only native math/QA studies are supported")
        from improving.text_study import validate_text_config
        validate_text_config(config)
        root=Path(config["data"]["output_dir"])
        inputs={name:root/f"{name}.jsonl"
                for name in ("train","calibration","validation","eval")}
        generation=config["synthesis"]
    else:
        from improving.pipeline import validate_config
        validate_config(config)
        inputs={name:Path(config["data"][name])
                for name in ("train","calibration","validation","eval")}
        generation=config["generation"]
    if "spectral_learned" not in config.get("methods", []):
        raise ValueError("The selected config does not include learned gains")
    return inputs,generation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",required=True)
    parser.add_argument("--output-dir",required=True)
    args=parser.parse_args()
    from improving.data import read_jsonl, assert_disjoint_splits
    from improving.gain_pipeline import calibrate_learned_round
    from improving.modeling import load_model
    from improving.pipeline import checkpoint_fingerprint, file_sha, record_stage
    from improving.utils import atomic_json, stable_hash
    import torch

    cfg=read(args.config)
    paths,generation=settings_for(cfg)
    output=Path(args.output_dir).resolve()
    source=Path(cfg["output_dir"]).resolve()
    if output==source or source in output.parents:
        raise ValueError("Qualification root must not be inside the training output root")
    if output.exists():
        raise FileExistsError("Qualification is single-attempt. Preserve old outputs and use a new directory")
    if any(not path.is_file() for path in paths.values()):
        raise FileNotFoundError("Missing prepared native study split files")
    tasks={name:read_jsonl(path) for name,path in paths.items()}
    assert_disjoint_splits(tasks)
    from improving.gain_pipeline import split_gain_settings
    _,integration=split_gain_settings(cfg["calibration"])
    if len(tasks["calibration"]) < cfg["calibration"]["max_examples"] or len(tasks["train"]) < integration["probe_examples"]:
        raise ValueError("Insufficient fit/guard references or unlabeled training probes")
    base=Path(cfg["model"]["name"])
    source_identity=(checkpoint_fingerprint(base) if base.is_dir() else None)
    manifest={
        "qualification":"full_spectrum_learned_real_model_only",
        "config":cfg,
        "split_hashes":{name:file_sha(path) for name,path in paths.items()},
        "local_base_sha256":source_identity,
        "no_sft":True,"no_benchmark_evaluation":True,
    }
    atomic_json(output/"qualification_manifest.json",manifest)
    with record_stage(output,"model_loading"):
        model,tokenizer=load_model(cfg["model"])
    try:
        model_id=stable_hash([cfg["model"],getattr(model.config,"_commit_hash",None),source_identity])
        operators, covariance, audit, receipt=calibrate_learned_round(
            model,tokenizer,tasks["calibration"],tasks["train"],
            cfg["calibration"],generation,output,model_id,
            seed=int(cfg.get("seed",42)),round_index=1,resume=False)
        report={
            "status":"real_model_calibration_completed",
            "selected_identity":audit["selected_identity"],
            "fallback_reason":audit.get("fallback_reason"),
            "gain_fit_accepted_steps":audit.get("accepted_steps",0),
            "model_identity":model_id,
            "calibration_operator_sha256":receipt["operator_sha256"],
            "qualification_only":True,
            "trained_model":False,
            "benchmark_scored":False,
            "scientific_gain":"unverified",
        }
        atomic_json(output/"qualification_result.json",report)
        print(json.dumps(report,indent=2,ensure_ascii=False))
    finally:
        del model,tokenizer
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


if __name__=="__main__":
    main()
