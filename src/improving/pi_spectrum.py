"""Label-free privileged-self-teacher K/V spectral intervention.

Experimental arm only. Teacher = SAME frozen round checkpoint, conditioned on
a self-generated strategy note. Student = unconditioned round checkpoint on
its OWN rollout prefixes. No reference answers, program execution or reward.
Actual correctness/diversity improvement is an empirical hypothesis.

This module purposely reuses existing gradient-capture, spectral-gain and
folding primitives. It does not implement OPST's full optimizer or GDN memory.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import nullcontext
import math
import json
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

from .calibration import _CaptureLinear
from .gain_pipeline import _bind_json, _load_artifact, _save_artifact
from .generation import generate_to_file
from .learned_gains import (
    SpectralGainLinear, _frozen_native, _installed, _set_gains,
    forward_kl_sum, spectral_groups, validate_gain_settings,
)
from .modeling import render_prompt
from .spectral import _covariance_eigh, _native_linear, folded_operators, target_modules
from .utils import atomic_json, stable_hash


PI_DEFAULTS = {
    "fit_examples": 12,
    "guard_examples": 6,
    "probe_examples": 6,
    "plan_max_new_tokens": 96,
    "rollout_max_new_tokens": 64,
    "max_length": 2048,
    "plan_temperature": 0.8,
    "rollout_temperature": 1.0,
    "top_p": 0.95,
    "top_k": 0,
    "layers": None,
}


def validate_pi_settings(settings):
    """Strict, explicit resource/identity contract for the standalone arm."""
    if not isinstance(settings, Mapping):
        raise ValueError("pi_spectrum must be a mapping")
    unknown = set(settings) - set(PI_DEFAULTS) - {"gain_learning"}
    if unknown:
        raise ValueError(f"Unknown pi_spectrum keys: {sorted(unknown)}")
    result = {**PI_DEFAULTS, **settings}
    for name in ("fit_examples", "guard_examples", "probe_examples",
                 "plan_max_new_tokens", "rollout_max_new_tokens", "max_length"):
        if type(result[name]) is not int or result[name] <= 0:
            raise ValueError(f"pi_spectrum.{name} must be a positive integer")
    if result["max_length"] <= result["rollout_max_new_tokens"] + result["plan_max_new_tokens"]:
        raise ValueError("pi_spectrum.max_length leaves no room for the prompt")
    for name in ("plan_temperature", "rollout_temperature", "top_p"):
        value = result[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"pi_spectrum.{name} must be finite")
        if name.endswith("temperature") and value <= 0:
            raise ValueError(f"pi_spectrum.{name} must be positive")
        if name == "top_p" and not 0 < value <= 1:
            raise ValueError("pi_spectrum.top_p must be in (0,1]")
    if type(result["top_k"]) is not int or result["top_k"] < 0:
        raise ValueError("pi_spectrum.top_k must be nonnegative")
    layers = result["layers"]
    if layers is not None and (not isinstance(layers, list) or not layers or
                                any(type(v) is not int or v < 0 for v in layers)):
        raise ValueError("pi_spectrum.layers must be null or nonempty list of indices")
    raw = result.get("gain_learning", {})
    if not isinstance(raw, Mapping):
        raise ValueError("pi_spectrum.gain_learning must be a mapping")
    result["gain_learning"] = validate_gain_settings(raw)
    return result


def public_task(task):
    """Allowlist is the only model-facing train-task view: strip gold/test fields."""
    allowed = ("task_id", "prompt", "source", "split", "chat_template_kwargs")
    clean = {name: task[name] for name in allowed if name in task}
    if any(key not in clean for key in ("task_id", "prompt", "source", "split")):
        raise ValueError("PI task needs ID, prompt, source and split")
    return clean


def choose_pi_tasks(tasks, settings):
    count = sum(settings[k] for k in ("fit_examples", "guard_examples", "probe_examples"))
    if len(tasks) < count:
        raise ValueError(f"PI requires {count} distinct training prompts; found {len(tasks)}")
    selected = [public_task(t) for t in tasks[:count]]
    ids = [t["task_id"] for t in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("PI fit/guard/probe task IDs must be unique")
    a = settings["fit_examples"]
    b = a + settings["guard_examples"]
    return selected[:a], selected[a:b], selected[b:]


def _plan_task(task):
    clean = dict(public_task(task))
    clean["prompt"] = (
        task["prompt"] +
        "\n\nPrivileged self-teacher preparation (UNVERIFIED): "
        "Write only a short algorithmic plan. No implementation, no tests, "
        "no claim that a solution was checked. Stop after the plan."
    )
    return clean


def _teacher_task(task, plan):
    if not isinstance(plan, str) or not plan.strip():
        raise ValueError("Self-generated plan must be nonempty; do not fabricate a teacher")
    clean = dict(public_task(task))
    clean["prompt"] = (
        task["prompt"] +
        "\n\n[Unverified self-generated strategy note]\n" +
        plan.strip() +
        "\n[End note]\nUse this note if helpful to solve the original coding problem."
    )
    return clean


def build_pi_pairs(tokenizer, tasks, plan_records, rollout_records, max_length):
    """Pairs have exact common rollout suffixes, no gold text or test access."""
    plans = {}
    rollouts = {}
    for records, destination, role in ((plan_records, plans, "plan"),
                                       (rollout_records, rollouts, "rollout")):
        for record in records:
            identifier = record.get("task_id")
            if identifier in destination or record.get("sample_id") != 0:
                raise ValueError(f"PI {role}: exactly one sample per task is required")
            destination[identifier] = record
    ids = {task["task_id"] for task in tasks}
    if set(plans) != ids or set(rollouts) != ids:
        raise ValueError("PI plan/rollout coverage mismatch")
    pairs = []
    for task in tasks:
        identifier = task["task_id"]
        plan = plans[identifier]
        rollout = rollouts[identifier]
        if not isinstance(plan.get("completion"), str) or not plan["completion"].strip():
            raise ValueError(f"PI has no self-generated plan for {identifier}")
        suffix = rollout.get("completion_ids")
        if (not isinstance(suffix, list) or not suffix or
                any(type(v) is not int or v < 0 for v in suffix) or
                rollout.get("generation_tokens") != len(suffix)):
            raise ValueError("PI requires exact nonempty native rollout token IDs")
        student_prompt = render_prompt(tokenizer, task)
        teacher_prompt = render_prompt(tokenizer, _teacher_task(task, plan["completion"]))
        if rollout.get("prompt_tokens") != len(tokenizer.encode(student_prompt, add_special_tokens=False)):
            raise ValueError("PI rollout prompt-length binding mismatch")
        if rollout.get("prompt_sha256") != stable_hash(student_prompt):
            raise ValueError("PI rollout prompt SHA mismatch")
        if plan.get("prompt_sha256") != stable_hash(render_prompt(tokenizer, _plan_task(task))):
            raise ValueError("PI plan prompt SHA mismatch")
        student_prefix = tokenizer.encode(student_prompt, add_special_tokens=False)
        teacher_prefix = tokenizer.encode(teacher_prompt, add_special_tokens=False)
        if (not student_prefix or not teacher_prefix or
                max(len(student_prefix), len(teacher_prefix)) + len(suffix) > max_length):
            raise ValueError("PI exact plan/rollout exceeds max_length; no truncation is allowed")
        pairs.append({
            "task_id": identifier,
            "student_ids": student_prefix + suffix,
            "teacher_ids": teacher_prefix + suffix,
            "student_start": len(student_prefix) - 1,
            "teacher_start": len(teacher_prefix) - 1,
            "targets": len(suffix),
        })
    return pairs


def _get_logits(model, ids, *, embedded=False):
    device = model.get_input_embeddings().weight.device
    input_ids = torch.tensor([ids], device=device, dtype=torch.long)
    mask = torch.ones_like(input_ids)
    if embedded:
        embeddings = model.get_input_embeddings()(input_ids).detach().requires_grad_(True)
        output = model(inputs_embeds=embeddings, attention_mask=mask, use_cache=False)
    else:
        output = model(input_ids=input_ids, attention_mask=mask, use_cache=False)
    logits = output.logits if hasattr(output, "logits") else output["logits"]
    if logits.ndim != 3 or logits.shape[:2] != input_ids.shape:
        raise ValueError("PI model output must preserve causal token dimensions")
    return logits


def _completion_logits(logits, pair, role):
    start = pair[f"{role}_start"]
    stop = start + pair["targets"]
    selected = logits[:, start:stop, :]
    if selected.shape[1] != pair["targets"]:
        raise ValueError("PI teacher/student target positions are not aligned")
    return selected[0].float()


def prepare_targets(model, pairs, *, probes=False):
    """One target distribution per prefix; stored on CPU and treated as fixed."""
    output = []
    with torch.no_grad():
        for pair in pairs:
            teacher = _completion_logits(
                _get_logits(model, pair["teacher_ids"]), pair, "teacher"
            )
            if not torch.isfinite(teacher).all():
                raise FloatingPointError("PI self-teacher logits are nonfinite")
            record = {**pair, "teacher_p": teacher.log_softmax(-1).exp().cpu()}
            if probes:
                native = _completion_logits(
                    _get_logits(model, pair["student_ids"]), pair, "student"
                )
                if not torch.isfinite(native).all():
                    raise FloatingPointError("PI native probe logits are nonfinite")
                record["native_logits"] = native.cpu()
            output.append(record)
    return output


def _pi_kl(logits, pair):
    """Exact full-vocabulary teacher-to-student KL, response-token mean."""
    student = _completion_logits(logits, pair, "student")
    teacher = pair["teacher_p"].to(device=student.device, dtype=torch.float32)
    if not torch.isfinite(student).all() or teacher.shape != student.shape:
        raise ValueError("PI logits/teacher target mismatch")
    if not torch.isfinite(teacher).all():
        raise FloatingPointError("PI teacher distribution is nonfinite")
    logp = student.log_softmax(-1)
    logq = torch.where(teacher > 0, teacher.clamp_min(1e-30).log(), 0.)
    return (teacher * (logq - logp)).sum(-1).mean()


def _pi_mean(model, targets):
    with torch.no_grad():
        return sum(float(_pi_kl(_get_logits(model, pair["student_ids"]), pair))
                   for pair in targets) / len(targets)


def _pi_gradient(model, targets, wrappers):
    totals = [torch.zeros_like(w.gains) for w in wrappers.values()]
    with torch.enable_grad():
        for pair in targets:
            loss = _pi_kl(_get_logits(model, pair["student_ids"]), pair) / len(targets)
            grads = torch.autograd.grad(
                loss, [w.gains for w in wrappers.values()], allow_unused=True
            )
            for accumulator, grad in zip(totals, grads):
                if grad is not None:
                    if not torch.isfinite(grad).all():
                        raise FloatingPointError("PI spectral gain gradient nonfinite")
                    accumulator.add_(grad.detach())
    return totals


def _probe_kl(model, targets, chunk_tokens):
    total, count = 0., 0
    with torch.no_grad():
        for pair in targets:
            student = _completion_logits(
                _get_logits(model, pair["student_ids"]), pair, "student"
            ).cpu()
            mask = torch.ones(1, pair["targets"], dtype=torch.bool)
            value, n, _, _ = forward_kl_sum(
                pair["native_logits"][None], student[None], mask, chunk_tokens
            )
            total += value
            count += n
    return total / count


def collect_pi_covariances(model, targets, names):
    """PI KL gradients over *all* student projection positions, including prompt."""
    originals = {name: _native_linear(model, name) for name in names}
    wrappers = {name: _CaptureLinear(module) for name, module in originals.items()}
    acc = {name: {
        "second_moment_sum": torch.zeros(m.out_features, m.out_features, dtype=torch.float64),
        "token_count": 0, "example_count": 0, "target_token_count": 0,
    } for name, m in originals.items()}
    with _frozen_native(model), _installed(model, wrappers):
        with torch.enable_grad():
            for pair in targets:
                for wrapper in wrappers.values():
                    wrapper.output = None
                    wrapper.calls = 0
                logits = _get_logits(model, pair["student_ids"], embedded=True)
                loss = _pi_kl(logits, pair)
                if not torch.isfinite(loss):
                    raise FloatingPointError("PI geometry KL is nonfinite")
                if any(w.output is None or w.calls != 1 for w in wrappers.values()):
                    raise ValueError("PI K/V modules were not executed once per example")
                grads = torch.autograd.grad(
                    loss, [w.output for w in wrappers.values()], allow_unused=False
                )
                for (name, grad) in zip(names, grads):
                    if grad.ndim != 3 or grad.shape[0] != 1 or not torch.isfinite(grad).all():
                        raise ValueError("PI geometry gradient shape/numerical failure")
                    rows = grad.detach()[0].double().cpu()
                    record = acc[name]
                    record["second_moment_sum"].add_(rows.T @ rows)
                    record["token_count"] += len(rows)
                    record["target_token_count"] += pair["targets"]
                    record["example_count"] += 1
                for wrapper in wrappers.values():
                    wrapper.output = None
    for name, item in acc.items():
        if not item["token_count"]:
            raise ValueError("PI gradient geometry has no positions")
        item["covariance"] = item["second_moment_sum"] / item["token_count"]
    return acc


def solve_pi_gains(model, fit, guard, probe, covariances, gain_settings):
    """Projected descent with guard veto, full-vocab KL and actual BF16 folding."""
    cfg = validate_gain_settings(gain_settings)
    originals = {name: _native_linear(model, name) for name in covariances}
    audit = {
        "algorithm": "frozen_self_teacher_pi_kl_full_spectrum_v1",
        "source": "self_generated_plan_plus_native_on_policy_rollout",
        "fit_examples": len(fit), "guard_examples": len(guard),
        "probe_examples": len(probe), "settings": cfg,
        "quality_or_executable_feedback_used": False,
        "identity_fallback": True, "fallback_reason": None,
        "accepted_steps": 0, "history": [], "modules": {},
    }
    # No novelty in teacher targets is a legitimate, recorded identity outcome.
    if any(not bool((rec["covariance"].abs() > 0).any()) for rec in covariances.values()):
        identity = {name: torch.eye(m.out_features, dtype=torch.float64)
                    for name, m in originals.items()}
        audit["fallback_reason"] = "zero_self_teacher_geometry"
        audit["selected_identity"] = True
        return identity, audit
    bases, groups, wrappers = {}, {}, {}
    for name, rec in covariances.items():
        _, eigenvalues, basis = _covariance_eigh(rec["covariance"])
        groups[name] = spectral_groups(
            eigenvalues, cfg["degeneracy_rtol"], cfg["degeneracy_atol"]
        )
        bases[name] = basis
        wrappers[name] = SpectralGainLinear(originals[name], basis, groups[name])
    with _frozen_native(model):
        native_fit = _pi_mean(model, fit)
        native_guard = _pi_mean(model, guard)
        audit["native"] = {"fit_pi_kl": native_fit, "guard_pi_kl": native_guard}
        current = native_fit
        with _installed(model, wrappers):
            for step in range(cfg["max_steps"]):
                previous = [w.gains.detach().clone() for w in wrappers.values()]
                gradient = _pi_gradient(model, fit, wrappers)
                magnitude = max(float(g.abs().max()) for g in gradient)
                if not math.isfinite(magnitude):
                    raise FloatingPointError("PI gain gradient magnitude nonfinite")
                if magnitude == 0:
                    audit["stop_reason"] = "zero_gain_gradient"
                    break
                accepted = False
                for backtrack in range(cfg["max_backtracks"] + 1):
                    rate = cfg["learning_rate"] * cfg["backtrack_factor"] ** backtrack
                    candidate = [
                        (old - rate * g / magnitude).clamp(cfg["min_gain"], 1.)
                        for old, g in zip(previous, gradient)
                    ]
                    if all(torch.equal(old, new) for old, new in zip(previous, candidate)):
                        audit["history"].append({"step": step + 1, "backtrack": backtrack,
                                                 "accepted": False, "reason": "zero_projected_step"})
                        break
                    _set_gains(wrappers, candidate)
                    loss = _pi_mean(model, fit)
                    if not math.isfinite(loss):
                        raise FloatingPointError("PI candidate KL nonfinite")
                    if loss >= current - cfg["min_improvement"]:
                        audit["history"].append({"step": step + 1, "backtrack": backtrack,
                                                 "accepted": False, "fit_pi_kl": loss,
                                                 "reason": "no_fit_improvement"})
                        continue
                    kl = _probe_kl(model, probe, cfg["kl_chunk_tokens"])
                    permitted = kl <= cfg["kl_budget"] + 1e-6
                    audit["history"].append({
                        "step": step + 1, "backtrack": backtrack, "fit_pi_kl": loss,
                        "native_probe_kl": kl, "accepted": permitted,
                        "reason": "feasible" if permitted else "probe_kl_budget_exceeded"
                    })
                    if permitted:
                        current = loss
                        accepted = True
                        audit["accepted_steps"] += 1
                        break
                if not accepted:
                    _set_gains(wrappers, previous)
                    audit["stop_reason"] = "no_accepted_step"
                    break
            else:
                audit["stop_reason"] = "maximum_steps"
            guard_loss = _pi_mean(model, guard)
            operators = {}
            for name, wrapper in wrappers.items():
                a = wrapper.gains.detach().cpu().double()[groups[name]]
                basis = bases[name]
                operators[name] = torch.eye(len(a), dtype=torch.float64) + (
                    basis * (a - 1).unsqueeze(0)
                ) @ basis.T
                audit["modules"][name] = {
                    "gain_groups": int(wrapper.gains.numel()),
                    "gain_min": float(a.min()), "gain_mean": float(a.mean()),
                    "gain_max": float(a.max()),
                    "gain_values": a.tolist(),
                }
        audit["activation"] = {
            "fit_pi_kl": current, "guard_pi_kl": guard_loss
        }
        if audit["accepted_steps"] == 0:
            audit["fallback_reason"] = "no_feasible_improving_update"
        elif guard_loss > native_guard + cfg["guard_tolerance"] + 1e-6:
            audit["fallback_reason"] = "self_teacher_guard_deteriorated"
        else:
            with folded_operators(model, operators):
                folded_fit = _pi_mean(model, fit)
                folded_guard = _pi_mean(model, guard)
                folded_probe_kl = _probe_kl(model, probe, cfg["kl_chunk_tokens"])
            audit["folded"] = {
                "fit_pi_kl": folded_fit, "guard_pi_kl": folded_guard,
                "native_probe_kl": folded_probe_kl,
            }
            failed = []
            if folded_fit >= native_fit - cfg["min_improvement"]:
                failed.append("folded_fit_not_improved")
            if folded_guard > native_guard + cfg["guard_tolerance"] + 1e-6:
                failed.append("folded_guard_deteriorated")
            if folded_probe_kl > cfg["kl_budget"] + 1e-6:
                failed.append("folded_probe_kl_budget_exceeded")
            if not all(math.isfinite(v) for v in
                       (folded_fit, folded_guard, folded_probe_kl)):
                failed.append("nonfinite_folded_result")
            audit["fallback_reason"] = ",".join(failed) if failed else None
            audit["identity_fallback"] = bool(failed)
        if audit["identity_fallback"]:
            operators = {name: torch.eye(m.out_features, dtype=torch.float64)
                         for name, m in originals.items()}
    audit["selected_identity"] = audit["identity_fallback"]
    return operators, audit


def _generation_settings(settings, generation, *, plan):
    return {
        "samples": 1, "batch_size": 1, "task_batch_size": 1, "sequence_batch_size": 1,
        "max_new_tokens": settings["plan_max_new_tokens"] if plan else settings["rollout_max_new_tokens"],
        "max_prompt_tokens": generation.get("max_prompt_tokens", 2048),
        "temperature": settings["plan_temperature"] if plan else settings["rollout_temperature"],
        "top_p": settings["top_p"], "top_k": settings["top_k"],
    }


def _save_torch(path, content):
    import os
    import tempfile
    temporary = None
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp",
                                         prefix=f".{path.name}.", delete=False) as stream:
            temporary = Path(stream.name)
            torch.save(content, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def validate_saved_pi_round(directory, model_identity, settings, tasks, *,
                            seed, round_index):
    """Validate a committed policy without refitting against post-SFT weights."""
    from .pipeline import file_sha
    directory = Path(directory)
    conf = validate_pi_settings(settings)
    fit, guard, probe = choose_pi_tasks(tasks, conf)
    required = ("pi_plans.jsonl", "pi_rollouts.jsonl", "pi_covariances.pt",
                "pi_operators.pt", "pi_audit.json", "pi_provenance.json")
    for name in required:
        if not (directory / name).is_file():
            raise ValueError(f"Committed PI policy missing {name}; do not refit")
    provenance = {
        "method": "spectral_pi", "version": 1, "model_identity": model_identity,
        "round": round_index, "seed": seed,
        "settings": conf,
        "task_ids": {
            "fit": [t["task_id"] for t in fit],
            "guard": [t["task_id"] for t in guard],
            "probe": [t["task_id"] for t in probe],
        },
        "train_prompt_sha256": stable_hash(
            [(t["task_id"], t["prompt"]) for t in tasks]
        ),
        "pi_plans_sha256": file_sha(directory / "pi_plans.jsonl"),
        "pi_rollouts_sha256": file_sha(directory / "pi_rollouts.jsonl"),
        "pi_covariances_sha256": file_sha(directory / "pi_covariances.pt"),
    }
    stored = torch.load(directory / "pi_operators.pt", map_location="cpu", weights_only=True)
    if not isinstance(stored, dict) or stored.get("protocol") != provenance:
        raise ValueError("PI policy configuration or data provenance mismatch")
    covariances = torch.load(
        directory / "pi_covariances.pt", map_location="cpu", weights_only=True
    )
    operators, audit = _load_artifact(
        directory / "pi_operators.pt", provenance,
        covariances, conf["gain_learning"]["min_gain"]
    )
    if audit != json.loads((directory / "pi_audit.json").read_text()):
        raise ValueError("PI gain audit tampered")
    expected = {
        **provenance,
        "operator_sha256": stored["operator_sha256"],
        "operator_file_sha256": file_sha(directory / "pi_operators.pt"),
        "selected_identity": audit["identity_fallback"],
        "no_reference_answers": True, "no_verifier_or_environment_feedback": True,
    }
    if json.loads((directory / "pi_provenance.json").read_text()) != expected:
        raise ValueError("PI provenance receipt mismatch")
    return operators, covariances, audit, expected


def calibrate_pi_round(model, tokenizer, tasks, settings, generation, directory,
                       model_identity, *, seed, round_index, resume):
    """Build one round-specific, label-free self-teacher spectral controller."""
    from .pipeline import record_stage, file_sha
    conf = validate_pi_settings(settings)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    fit, guard, probe = choose_pi_tasks(tasks, conf)
    selected = fit + guard + probe
    forbidden = {"reference", "tests", "calibration_spans", "correct"}
    if any(forbidden.intersection(task) for task in selected):
        raise ValueError("PI input task view must not contain gold, tests or rewards")
    artifact = directory / "pi_operators.pt"
    if not artifact.exists() and any((directory / name).exists()
                                     for name in ("train.jsonl", "training_stats.json",
                                                  "generation_policy.jsonl", "gain_provenance.json")):
        raise ValueError("PI training generated before bound operator artifact")
    plan_tasks = [_plan_task(task) for task in selected]
    with record_stage(directory, "pi_plan_generation"):
        plans = generate_to_file(
            model, tokenizer, plan_tasks, directory / "pi_plans.jsonl",
            _generation_settings(conf, generation, plan=True), seed=seed,
            model_identity=model_identity, method="spectral_pi_native_plan",
            round_index=round_index, stage="pi_plan", resume=resume
        )
    with record_stage(directory, "pi_rollout_generation"):
        rollouts = generate_to_file(
            model, tokenizer, selected, directory / "pi_rollouts.jsonl",
            _generation_settings(conf, generation, plan=False), seed=seed,
            model_identity=model_identity, method="spectral_pi_native_rollout",
            round_index=round_index, stage="pi_rollout", resume=resume
        )
    pairs = build_pi_pairs(tokenizer, selected, plans, rollouts, conf["max_length"])
    length = len(fit)
    fit_pairs = pairs[:length]
    guard_pairs = pairs[length:length + len(guard)]
    probe_pairs = pairs[length + len(guard):]
    names = target_modules(model, layers=conf["layers"])
    covariance_path = directory / "pi_covariances.pt"
    if artifact.exists():
        operators, covariances, audit, provenance = validate_saved_pi_round(
            directory, model_identity, conf, tasks, seed=seed, round_index=round_index
        )
        if set(covariances) != set(names):
            raise ValueError("PI saved K/V topology mismatch")
        return operators, covariances, audit, provenance
    with record_stage(directory, "pi_target_collection"):
        with _frozen_native(model):
            fit_targets = prepare_targets(model, fit_pairs)
            guard_targets = prepare_targets(model, guard_pairs)
            probe_targets = prepare_targets(model, probe_pairs, probes=True)
    with record_stage(directory, "pi_geometry"):
        covariances = collect_pi_covariances(model, fit_targets, names)
    _save_torch(covariance_path, covariances)
    with record_stage(directory, "pi_gain_learning"):
        operators, audit = solve_pi_gains(
            model, fit_targets, guard_targets, probe_targets, covariances,
            conf["gain_learning"]
        )
    protocol = {
        "method": "spectral_pi", "version": 1, "model_identity": model_identity,
        "round": round_index, "seed": seed, "settings": conf,
        "task_ids": {"fit": [t["task_id"] for t in fit],
                     "guard": [t["task_id"] for t in guard],
                     "probe": [t["task_id"] for t in probe]},
        "train_prompt_sha256": stable_hash(
            [(t["task_id"], t["prompt"]) for t in tasks]
        ),
        "pi_plans_sha256": file_sha(directory / "pi_plans.jsonl"),
        "pi_rollouts_sha256": file_sha(directory / "pi_rollouts.jsonl"),
        "pi_covariances_sha256": file_sha(covariance_path),
    }
    _save_artifact(artifact, protocol, operators, audit)
    _bind_json(directory / "pi_audit.json", audit)
    stored = torch.load(artifact, map_location="cpu", weights_only=True)
    provenance = {
        **protocol, "operator_sha256": stored["operator_sha256"],
        "operator_file_sha256": file_sha(artifact),
        "selected_identity": audit["identity_fallback"],
        "no_reference_answers": True, "no_verifier_or_environment_feedback": True,
    }
    _bind_json(directory / "pi_provenance.json", provenance)
    return operators, covariances, audit, provenance
