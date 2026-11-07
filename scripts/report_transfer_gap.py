#!/usr/bin/env python3
"""Inspect sealed transfer-gap diagnostics without loading a model.

Only reads frozen study artifacts and validates saved checksums. Missing stages
are never represented as zero. Does not score, tune, retrain or run code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(2**20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize(root, method=None):
    root = Path(root).resolve()
    manifest_file = root / "manifest.json"
    manifest = _json(manifest_file)
    config = manifest.get("config", {})
    from improving.transfer_diagnostics import transfer_settings
    settings = transfer_settings(config)
    if settings is None:
        raise ValueError("Source study has no transfer-gap diagnostic protocol")
    if len(manifest.get("selected_task_ids", {}).get("validation", [])) != 30:
        raise ValueError("Frozen study manifest must contain the 30 official validation task IDs")
    methods = config.get("methods", [])
    if method is None:
        if len(methods) != 1:
            raise ValueError("Select --method for a source with multiple methods")
        method = methods[0]
    if method not in methods:
        raise ValueError("Requested method is absent from the frozen source")
    rows = []
    for number in range(1, config["rounds"] + 1):
        stage = root / method / f"round_{number}"
        marker = stage / "complete.json"
        if not marker.exists():
            rows.append({"round": number, "status": "missing_or_incomplete"})
            continue
        state = _json(marker)
        paths = state.get("files", {})
        if state.get("status") != "completed" or not paths:
            raise ValueError(f"Round {number} has no completed native seal")
        for relative, expected in paths.items():
            sealed = (stage / relative).resolve()
            if not sealed.is_relative_to(stage.resolve()) or not sealed.is_file() or _sha(sealed) != expected:
                raise ValueError(f"Round {number} failed its original file seal: {relative}")
        nll_rel = "reference_transfer_nll.json"
        needs_nll = method == "spectral_learned" and settings["reference_nll_each_round"]
        if needs_nll and nll_rel not in paths:
            raise ValueError(f"Sealed round {number} lacks reference transfer NLL")
        row = {
            "round": number, "status": "complete",
            "reference_nll_available": nll_rel in paths,
        }
        if nll_rel in paths:
            value = _json(stage / nll_rel)
            row.update({
                "fit_transfer_gap": value["fit_transfer_gap"],
                "guard_transfer_gap": value["guard_transfer_gap"],
                "native_reference_fit_delta": value["fit_change_native_to_native"],
                "native_reference_guard_delta": value["guard_change_native_to_native"],
                "identity_fallback": value["identity_fallback"],
            })
        if number in settings["rounds"]:
            report_rel = "transfer_gap/report.json"
            if report_rel not in paths:
                raise ValueError(f"Diagnostic round {number} lacks sealed three-state comparison")
            path = stage / report_rel
            if _sha(path) != paths[report_rel]:
                raise ValueError(f"Development report checksum differs: {path}")
            report = _json(path)
            pair = report["paired_task_differences"]
            row["dev_states"] = report["states"]
            row["dev_paired_pass@1"] = {
                name: data["pass_at_k"]["1"] for name, data in pair.items()
            }
            row["dev_paired_pass@64"] = {
                name: data["pass_at_k"]["64"] for name, data in pair.items()
            }
            row["dev_paired_AST_C64"] = {
                name: data["implementation_proxy"]["coverage_at_k"]["64"]
                for name, data in pair.items()
            }
            row["dev_paired_AST_D4"] = {
                name: data["implementation_proxy"]["correct_matched_coverage_at_budgets"]["4"]
                for name, data in pair.items()
            }
            row["observed_rare_correctness"] = report["observed_rare_correctness"]
        rows.append(row)
    return {
        "status": "read_only_saved_artifact_summary",
        "source_manifest_sha256": _sha(manifest_file),
        "source": str(root),
        "method": method,
        "configured_dev_rounds": settings["rounds"],
        "per_round": rows,
        "uncertainty": "paired task bootstrap on 30 development tasks; one training seed",
        "limit": "No full-trajectory KL upper bound; no established causal transfer mechanism.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--method", help="Required only when the source contains several method arms")
    p.add_argument("--output", help="Optional new JSON summary file, outside frozen run")
    args = p.parse_args()
    result = summarize(args.run_dir, args.method)
    if args.output:
        dst = Path(args.output).expanduser().resolve()
        source = Path(args.run_dir).expanduser().resolve()
        if dst == source or source in dst.parents:
            raise ValueError("Read-only report must not overwrite frozen study outputs")
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open("x", encoding="utf-8") as file:
            json.dump(result, file, indent=2, ensure_ascii=False, allow_nan=False)
            file.write("\n")
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
