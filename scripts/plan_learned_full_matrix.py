#!/usr/bin/env python3
"""Standard-library candidate budget for the comprehensive learned SPECTRUM study.

This does not measure GPU-hours/tokens or start models. All numbers are
configured upper-population candidate counts, excluding tiny calibration probes.
"""
from __future__ import annotations

import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def _load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

def build_budget():
    cross=_load("configs/crossfamily/protocol_learned_4096.json")
    math=_load("configs/multidomain/text_math_learned.json")
    qa=_load("configs/multidomain/text_qa_learned.json")
    models, methods, rounds=len(cross["models"]),len(cross["methods"]),cross["rounds"]
    code={
        "models":cross["models"],"methods":cross["methods"],"rounds":rounds,
        "MBPP_train_completion_candidates":models*methods*rounds*291*cross["generation"]["train_samples"],
        "MBPP_evaluation_candidates":models*(1+methods*rounds)*500*cross["generation"]["eval_samples"],
        "HumanEvalPlus_candidates":models*(1+methods)*164*cross["transfer"]["samples"],
        "additional_transfer_candidates":{
            name:models*(1+methods)*n*cross["transfer"]["samples"]
            for name,n in {"apps_intro":200,"codecontests":165,"livecodebench":200}.items()
        },
        "code_generation_token_cap":cross["generation"]["max_new_tokens"],
        "code_SFT_total_token_cap":cross["train"]["max_length"],
    }
    code["total_code_completion_candidates"]=sum([
        code["MBPP_train_completion_candidates"],code["MBPP_evaluation_candidates"],
        code["HumanEvalPlus_candidates"],*code["additional_transfer_candidates"].values()])
    domain_budgets={}
    for domain,conf,n_eval in (("math",math,500),("qa",qa,12032)):
        arms=len(conf["methods"])-1
        domain_budgets[domain]={
            "train_generation_candidates":arms*conf["rounds"]*conf["data"]["train_size"]*conf["synthesis"]["samples"],
            "eval_generation_candidates":(1+arms*conf["rounds"])*n_eval*conf["evaluation"]["samples"],
            "eval_tasks":n_eval,"trained_methods":arms,"rounds":conf["rounds"],
            "synthesis_max_new_tokens":conf["synthesis"]["max_new_tokens"],
        }
    return {
        "status":"capacity_plan_only_no_training",
        "code":code,"text_domains":domain_budgets,
        "notes":[
            "Counts are generated candidates, not observed token lengths or measured GPU hours.",
            "Learned gain fitting/probing adds extra forwards not included above.",
            "Use an isolated evaluator; generated programs must not run unsandboxed on a shared machine.",
            "This full matrix is substantial: qualify one model/domain and verify storage before dispatch.",
            "ARC-AGI-3 learned adaptation and dedicated Physics data are not included in this code delivery.",
        ],
    }

if __name__=="__main__":
    print(json.dumps(build_budget(),indent=2,ensure_ascii=False))
