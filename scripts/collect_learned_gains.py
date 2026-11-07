#!/usr/bin/env python3
"""Collect small existing controller/metric receipts, never weights or raw samples."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


EXACT_NAMES = {
    'manifest.json', 'run_status.json', 'complete.json', 'training_stats.json',
    'learned_gains.json', 'gain_provenance.json', 'operator_diagnostics.json',
    'calibration_provenance.json', 'spectral_entropy_ref.json',
    'qualification_manifest.json', 'qualification_complete.json',
    'plan.json', 'config.json', 'case_receipt.json', 'case_status.json',
    'started.json', 'exit.json', 'operator_response.json', 'operator_probe_complete.json',
    'operator_probe_binding.json', 'reference_transfer_nll.json', 'report.json',
    'transfer_complete.json', 'decoder_complete.json', 'interpolation_complete.json',
    'annotation_status.json', 'semantic_summary.json',
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--output', required=True, help='New ZIP path; never overwrite an archive')
    args = parser.parse_args(argv)
    root, output = Path(args.run_dir), Path(args.output)
    if not root.is_dir():
        raise FileNotFoundError(root)
    if output.suffix.lower() != '.zip':
        raise ValueError('--output must end with .zip')
    summary_path = output.with_suffix('.summary.json')
    if output.exists() or summary_path.exists():
        raise FileExistsError('Collection output exists; choose a new snapshot filename')
    files = []
    for path in sorted(root.rglob('*.json')):
        relative = path.relative_to(root)
        if path.is_symlink() or any(part == 'model' or part.endswith('.parts')
                                    for part in relative.parts):
            continue
        if (path.name in EXACT_NAMES or path.name.endswith(
                ('.metrics.json', '.budget.json', '.resources.json'))):
            files.append(path)
    if not files:
        raise ValueError('No existing qualification or experiment receipts were found')
    inventory, rounds = [], []
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            relative = path.relative_to(root).as_posix()
            # One byte snapshot feeds both the archive and the digest.
            content = path.read_bytes()
            value = json.loads(content)
            archive.writestr(relative, content)
            inventory.append({'path': relative, 'bytes': len(content),
                              'sha256': hashlib.sha256(content).hexdigest()})
            if path.name == 'learned_gains.json':
                rounds.append({'path': relative, 'selected_identity': value.get('selected_identity'),
                               'fallback_reason': value.get('fallback_reason'),
                               'native': value.get('native'), 'selected': value.get('selected')})
        summary = {
            'scope': 'snapshot_of_existing_small_receipts_not_completion_or_scientific_verification',
            'run_dir': str(root), 'files': inventory, 'learned_calibrations': rounds,
            'excluded': ['model weights', 'raw train/evaluation/probe JSONL',
                         'gain_inputs.json token IDs', 'operator/calibration tensors'],
            'missing_outputs': 'Not inferred or filled with zero; inspect completion receipts.',
        }
        rendered = json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        archive.writestr('collection_summary.json', rendered)
    summary_path.write_text(rendered)
    print(json.dumps({'archive': str(output), 'summary': str(summary_path),
                      'collected_files': len(files)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
