#!/usr/bin/env python3
"""CPU-free static preflight for the opt-in learned full matrix.

Stdlib only. No model loads, network, training, benchmark runs, or new files.
This is NOT a substitute for pytest, native CUDA qualification or Docker sandbox
inspection. Exits nonzero on malformed Python, JSON, shell or protocol.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PYTHON_SOURCES=(
    "src/improving/pipeline.py",
    "src/improving/text_study.py",
    "src/improving/gain_pipeline.py",
    "src/improving/learned_gains.py",
    "scripts/run_crossfamily_study.py",
    "scripts/run_learned_extra_transfers.py",
    "scripts/qualify_learned_matrix.py",
    "scripts/plan_learned_full_matrix.py",
    "scripts/run_text_study.py",
    "scripts/prepare_text_data.py",
    "tests/test_crossfamily_learned.py",
    "tests/test_text_learned.py",
    "tests/test_learned_extra_transfers.py",
    "tests/test_qualify_learned_matrix.py",
    "tests/test_learned_full_matrix.py",
)
JSON_CONFIGS=(
    "configs/crossfamily/protocol_learned_4096.json",
    "configs/multidomain/text_math_learned.json",
    "configs/multidomain/text_qa_learned.json",
    "configs/multidomain/text_qa_gpqa_learned.json",
)
BASH_SOURCES=("scripts/run_learned_full_matrix.sh",)


def check():
    validated=[]
    for relative in PYTHON_SOURCES:
        source=(ROOT/relative).read_text(encoding="utf-8")
        ast.parse(source,filename=relative)
        validated.append(relative)
    for relative in BASH_SOURCES:
        subprocess.run(["bash","-n",str(ROOT/relative)],check=True)
        validated.append(relative)
    configs={}
    for relative in JSON_CONFIGS:
        cfg=json.loads((ROOT/relative).read_text(encoding="utf-8"))
        configs[relative]=cfg
        validated.append(relative)
    code=configs[JSON_CONFIGS[0]]
    from_order=["plain","ssd","spectral_soft","spectral_learned"]
    if code.get("methods") != from_order or code.get("models") != [
        "qwen7b","llama8b","deepseek6.7b"]:
        raise ValueError("Learned code model and baseline order changed")
    if code["evaluation"].get("backend") != "docker" or code["evaluation"].get("allow_unsafe_local"):
        raise ValueError("Unsafe verifier configuration")
    if code["train"]["max_length"] < (
        code["generation"]["max_new_tokens"]+code["generation"]["max_prompt_tokens"]):
        raise ValueError("Generated response could be truncated by SFT")
    gc=code["calibration"]
    if gc["max_examples"] != 50 or gc["matched_reference_fit_examples"] != 40 or gc["gain_learning"]["guard_examples"] != 10:
        raise ValueError("Coding gain fit/guard counts diverged")
    for relative in JSON_CONFIGS[1:]:
        c=configs[relative]
        if c.get("methods") != ["base",*from_order]:
            raise ValueError(f"{relative} lost learned/control comparison")
        cc=c["calibration"]
        if (cc["max_examples"],cc["matched_reference_fit_examples"],
                cc["gain_learning"]["guard_examples"]) != (64,54,10):
            raise ValueError(f"{relative} changed matched references")
        if c["train"]["max_length"] < c["synthesis"]["max_prompt_tokens"]+c["synthesis"]["max_new_tokens"]:
            raise ValueError(f"{relative} truncates generated targets")
    if configs[JSON_CONFIGS[3]].get("include_gpqa") is not True or configs[JSON_CONFIGS[2]].get("include_gpqa",False):
        raise ValueError("Optional GPQA must not silently change default QA")
    return {
        "status":"static_preflight_passed",
        "python_files":len(PYTHON_SOURCES),
        "json_configs":len(JSON_CONFIGS),
        "bash_scripts":len(BASH_SOURCES),
        "isolation":"docker-default",
        "gpu_checked":False,"dataset_downloaded":False,"pytest_run":False,
        "scientific_results":False,
        "next":"run real pytest, native model qualification and Docker preflight on the host"
    }


if __name__=="__main__":
    try:
        print(json.dumps(check(),indent=2,ensure_ascii=False))
    except (SyntaxError,ValueError,FileNotFoundError,subprocess.CalledProcessError) as exc:
        print(f"STATIC PREFLIGHT FAILED: {exc}",file=sys.stderr)
        sys.exit(2)
