"""One-time, checksum-verified integration; removed before publishing tested code."""
from pathlib import Path
import hashlib
import subprocess

root = Path.cwd()
p = root/'src/improving/pipeline.py'
s = p.read_text()
assert hashlib.sha256(p.read_bytes()).hexdigest() == 'ca210191e7d8ff4e42e978965992ab0e1c8f353ea13fae06790e2f2d3f5dfea6'
t = subprocess.check_output(['git', 'show', 'da70329c3d1cb07bbd3380d563e2cc600541a8dc:src/improving/pipeline.py'], text=True)
s = s.replace('    return config\n\n\n', '    from .transfer_diagnostics import transfer_settings\n    transfer_settings(config)\n    return config\n\n\n', 1)
start = t.index('    from .transfer_diagnostics import (', t.index('def run_experiment'))
end = t.index('    diagnostic_tasks,', start)
s = s.replace('    diagnostic_tasks, diagnostic_samples, diagnostic_evaluation = _diagnostic_protocol', t[start:end]+'    diagnostic_tasks, diagnostic_samples, diagnostic_evaluation = _diagnostic_protocol', 1)
start = t.index('            if trained and transfer_diag is not None')
end = t.index('            if not trained:', start)
pos = s.index('            if not trained:', s.index('def run_experiment'))
s = s[:pos]+t[start:end]+s[pos:]
start = t.index('                if transfer_diag is not None and should_evaluate')
end = t.index('                training_settings =', start)
s = s.replace('                training_settings = dict(train_gen)', t[start:end]+'                training_settings = dict(train_gen)', 1)
start = t.index("            if transfer_diag is not None and method == 'spectral_learned':")
end = t.index('            eval_path =', start)
block = t[start:end]
block = block.replace("            if transfer_diag is not None and method == 'spectral_learned':", "            if transfer_diag is not None:\n                reference_gap = {'available': False, 'reason': 'not_a_learned_gain_arm'}\n                if method == 'spectral_learned':", 1)
a = block.index('                # Cached')
b = block.index('                if should_evaluate')
block = block[:a]+''.join('    '+line if line.strip() else line for line in block[a:b].splitlines(keepends=True))+block[b:]
s = s.replace('            eval_path = directory /', block+'            eval_path = directory /', 1)
start = s.index("            if method == 'spectral_learned' and round_index > 1 and not trained:")
end = s.index('            if local_base_fingerprint', start)
s = s[:start]+'            require_predecessor(root, method, round_index, previous_checkpoint, trained=trained)\n'+s[end:]
helper = '''def require_predecessor(root, method, round_index, previous_checkpoint, *, trained):
    """All arms must resume from the immediate native student, never the base."""
    if round_index <= 1 or trained:
        return
    expected = Path(root) / method / f'round_{round_index - 1}' / 'model'
    if previous_checkpoint is None or Path(previous_checkpoint) != expected or not expected.is_dir():
        raise ValueError('Round requires its immediate native predecessor checkpoint; '
                         'restore the original checkpoint/completion receipt instead of restarting from base')


'''
s = s.replace('def run_experiment(config, *, resume=False):', helper+'def run_experiment(config, *, resume=False):')
p.write_text(s)
assert hashlib.sha256(p.read_bytes()).hexdigest() == '0adaf60af3f331849eb8e3a608f9efb4c1f9a6926c7ed8a0c026999100405461'
p = root/'src/improving/transfer_diagnostics.py'
s = p.read_text().replace('    if config.get("methods") != ["spectral_learned"]:\n        raise ValueError("Transfer-gap instrumentation is initially restricted to spectral_learned-only runs")', '''    from .pipeline import METHODS
    methods = config.get("methods", [])
    if not methods or any(method not in METHODS for method in methods):
        raise ValueError("transfer_gap requires supported text self-distillation methods")''')
s = s.replace('        summaries[role] = json.loads(path.read_text())', '''        marker = json.loads((directory / role / "complete.json").read_text())
        summaries[role] = _check_complete(directory / role, marker.get("binding"))''')
p.write_text(s)
assert hashlib.sha256(p.read_bytes()).hexdigest() == 'c14cd006729e536535a1c6cdebe9db044343ac34ba1f005187ae85803935b304'
p = root/'configs/spectrum_7b/transfer_gap_learned_4096.yaml'
s = p.read_text().replace('backend: local', 'backend: docker').replace('allow_unsafe_local: true', 'allow_unsafe_local: false').replace('runs/spectrum_transfer_gap_20261103/learned_7b_r10', 'runs/rebuttal_transfer_gap_standalone/learned_7b_r10')
p.write_text(s)
p = root/'.github/workflows/rebuttal-cpu.yml'
s = p.read_text().replace('Record exact source and pinned integration input', 'Record exact source')
s = '\n'.join(line for line in s.splitlines() if 'git fetch --depth=1 origin da703' not in line and 'transfer-source.tar.gz' not in line)+'\n'
p.write_text(s)
p = root/'.gitignore'
p.write_text(p.read_text()+'\n.venv-rebuttal/\n')
p = root/'README.md'
p.write_text(p.read_text().replace('# SPECTRUM\n', '''# SPECTRUM

## ICLR rebuttal: frozen replications and transfer diagnostics

[Runbook and exact commands](docs/ICLR_REBUTTAL_ZH.md) ·
[Dry-run / execution driver](scripts/run_iclr_rebuttal.py)

An isolated integration of the existing Learned multi-model code and three-state
DEV diagnostics. Core: Qwen7B, three independent training seeds, ten rounds,
Plain/SSD/original Fixed-soft/Learned; cross-family and mechanism/scope controls
are separately labeled. No PI/GUI changes or new benchmark results are claimed.
Use a NEW output root and pin the delivered commit; never mutate an active run.

''', 1))
p = root/'AGENTS.md'
p.write_text(p.read_text().replace('# SPECTRUM current agent entry\n', '''# SPECTRUM current agent entry

## ICLR rebuttal integration — 3 November 2026

Read `docs/ICLR_REBUTTAL_ZH.md` before running the new foreground driver.
Preserve original methods, main, historical output roots and active checkouts.
The new pipeline guards immediate-predecessor recovery for EVERY arm and
supports sealed three-state DEV diagnostics for all matched comparisons.
Core retains ordinary all-token SFT; completion-only is a separate four-arm
ablation, not a silent improvement to our method. No PI/GUI or SFT-KL merge.
Three Qwen training seeds are private, new and frozen; same data across seeds.
Report missing cells and failed outcomes. CPU regressions and generated launch
configs are not GPU qualification or scientific gains. Cross-family uses the
existing two-layer placement; Qwen native replication uses all layers.

''', 1))
print('Verified pipeline and diagnostic SHA256; preserved matched-reference code.')
