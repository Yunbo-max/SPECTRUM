# ARC-AGI-3: native interactive extension

Delivery status: **generated_unexecuted**. These are implemented source entry
points, not a claim of successful 27B inference, game wins or completed training.
Run through the admitted Local SSH/native harness described in
[LOCAL_AGENT_RUNBOOK.md](../LOCAL_AGENT_RUNBOOK.md). No API leaderboard submission
is performed. Evaluation runs offline and retains native SDK scorecards.

## Fixed model and scientific comparison

[`configs/multidomain/arc3.json`](../configs/multidomain/arc3.json) uses the text
decoder of `Qwen/Qwen3.8-27B`, revision
`1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, BF16, fixed non-thinking mode.
The same original checkpoint starts every method independently. The five rounds
compare raw action-trajectory Vanilla SD (`plain`), SSD-style higher-temperature
synthesis (`ssd`), and SPECTRUM (`spectral_soft`). SSD here is an adaptation of its
sampling policy to the common recursive trajectory-SFT harness, not evaluation
of Apple's released model. There is one private randomization file, no
temperature sweep and no independent training-seed grid. Four synthesis episodes
per game are data collection, not four training seeds.

SPECTRUM acts on the native raw K/V projection outputs in full-attention decoder
layers 31 and 63, before normalization/RoPE. The hybrid model's recurrent GDN
layers are not assigned fictitious K/V modules. LoRA trains the native Q/K/V/O
projections of full-attention layers. Calibration must use the same implementation
and fixed reference-action corpus every round.

The model receives lossless row run-length encodings of **all** frames returned
for an action. Every color remains an integer in 0..15, coordinates remain exact,
and frames are neither cropped nor interpreted by another model. The previous
three decision contexts and responses are included. Prompts over 12,000 tokens
fail explicitly; frames are never silently dropped. Outputs are at most256 tokens
and must be one JSON action object. Malformed responses consume a model decision,
are logged with interface feedback, and remain in training. Unavailable actions
are not sent to the engine. No random fallback action is substituted.

Each episode permits256 model decisions and256 native actions, with a10,800-second
wall budget. The initial native RESET is recorded by the SDK; later RESET is
allowed only after GAME_OVER. `ONLY_RESET_LEVELS` must be unset. Successful native
actions, all model decisions, malformed outputs, tokens, time, completed levels
and raw native scorecards are all retained. No locally reimplemented score formula
is used. Mean native scores aggregate one independently scored episode per heldout
game; this is not a full competition or official hidden-test result.

## Games and calibration reference

The default is an immediately discoverable three-game public study:

| Purpose | Game prefix | Use |
|---|---|---|
| Training and development | `ls20` | Interface qualification and unfiltered self-generated training trajectories |
| Fixed reference calibration | `ft09` | A genuinely successful trajectory, replay-verified in the native engine |
| Heldout evaluation | `vc33` | Evaluation only, with no wrapper, parameter or model selection |

Preparation resolves each prefix to an exact official version and freezes source
and metadata file hashes in `data/multidomain/arc3/assets.lock.json`. All later
commands use those exact versions in OFFLINE mode. Development intentionally
shares the training game; there is no claimed independent validation split.
Distinct versions of the same game family cannot cross splits.

This small public holdout establishes an operational extension. A broader study
uses an explicit JSON split file with `train`, `calibration`, and `eval` arrays,
nonempty and disjoint by game-family prefix, passed to `--split-file` **before**
preparation in a new `data_dir`. Registered access may be needed for additional
public games; use the official [API-key process](https://docs.arcprize.org/api-keys)
and keep `ARC_API_KEY` solely in the native host environment. No key is logged.
Prepared metadata must contain actual official human-action baselines; preparation
stops if they are absent, rather than calling unqualified zero scores RHAE.

The SDK does not bundle a trusted action-label corpus. The implementation provides
two concrete ways to acquire one:

1. `collect-reference` runs one bounded original-model attempt on each calibration
   game. A complete WIN with no invalid action outputs is replayed independently
   in the native engine, including every before/after frame. Its canonical actions
   become the fixed reference corpus. An unsuccessful attempt is kept and reported;
   it is not turned into a successful reference.
2. `import-reference` accepts a real SDK-format JSONL recording from a human or
   another independently sourced successful solver. It must start with RESET,
   contain all frames, belong to the frozen calibration split, replay exactly
   under the supplied game seed, and end in WIN. The source file hash, native
   replay scorecard and label provenance are retained. This demonstrates successful
   actions, not mathematically optimal actions.

Only reference acquisition uses a successful-trajectory requirement. Every raw
synthetic training attempt—including malformed outputs and failures—is retained
for SFT. Observation/history tokens are context; generated action completions are
the supervised targets. Evaluation trajectories never enter training/calibration.

## Download and prepare

Use a separate **Python3.12** native Conda environment with the27B requirements
and model preparation from the current main runbook. SDK sources are pinned:

```bash
python -m pip install 'arcengine @ git+https://github.com/arcprize/ARCEngine.git@b495c6acaf253c9681cd7b75c4299d352e9ce6f8' 'arc-agi @ git+https://github.com/arcprize/ARC-AGI.git@f12822c4d550121c35a275008d964afbbed47d2f'
python scripts/prepare_arc3.py --config configs/multidomain/arc3.json
python scripts/prepare_arc3.py --config configs/multidomain/arc3.json --verify-only
```

The first command pins arcengine0.9.3 and arc-agi0.9.9 and the source commits;
`direct_url.json` is checked at runtime. These commands need the normal SDK
dependencies resolved in the isolated environment. Record the resulting Conda/pip
environment. The SDK downloads native game source and initializes each game during
preparation, so this stage is a native CPU task, not merely a file download.
Model weights are acquired by the separate shared model-preparation command;
formal ARC loading uses `local_files_only=true` and never silently downloads them.

`prepare_arc3.py` creates `runs/private/multidomain_seed.json` atomically with0600
permissions only if absent. It never overwrites existing randomization. Preserve
this file privately and reuse it across domains. Preparation does not print its
value. Existing locked assets are verified and reused; a new split requires a new
data directory. Keep download/cache ownership exclusive.

## Qualification and execution

Run from the delivered repository root through the admitted Local harness:

```bash
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json baseline
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json collect-reference
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json run --method plain
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json run --method ssd
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json run --method spectral_soft
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json status
```

The baseline command uses the training/development game, so its feedback can
qualify the interface without seeing the evaluation game. Check raw frames,
parsed actions, invalid-output rate, context lengths, time/VRAM, and native score
receipts before admitting the full five-round study. A27B model is an experimental
choice, not a guarantee of ARC competence. If the native baseline never progresses,
preserve that evidence and review the development protocol before investing in
all rounds. Do not choose a wrapper using `vc33` outcomes.

If `collect-reference` does not solve its calibration game, Vanilla/SSD can still
run independently. SPECTRUM remains explicitly blocked on a real reference. Import
an actual existing successful recording using:

```bash
python scripts/run_arc3_study.py --config configs/multidomain/arc3.json import-reference --recording /absolute/path/to/actual-successful-calibration-recording.jsonl --game-seed 0
```

Here the recording path and game seed are the real recording's values, not an
included sample file. Do not use an evaluation recording or invent a winning
trajectory. Accepted references create `calibration.jsonl` and
`calibration.lock.json`; repeated import refuses replacement.

For interrupted matching runs append `--resume` to `baseline`, `collect-reference`
or `run`. The process takes an exclusive OS lock for the ARC output root. A partial
episode restarts the local native environment and replays saved actions, requiring
identical observations at every transition before generation continues. Saved
generation chunks are reused with their original sampling identity. Engine errors
are failures, not zero scores. Complete episode artifacts are content-checked.
Changed source/runtime/assets/config/seed/reference identities reject resume.
The original pinned snapshot is fingerprinted over its actual complete weights,
tokenizer and configuration. One shared study manifest binds all methods,
development baselines and reference collection, so differently configured arms
cannot be combined under the same study directory. Adding the first verified
reference after baseline qualification is supported; its bytes are separately
bound to the SPECTRUM lineage.

`checkpoint_retention=latest` keeps the latest checkpoint per method. The previous
checkpoint is removed only after the replacement checkpoint, training receipt,
raw corpus and native evaluation summary have been sealed; its fingerprint remains
in `pruned.json`. Resume walks the sealed lineage and loads the latest retained
checkpoint. All trajectories, scores, calibration artifacts and training statistics
remain. A27B BF16 text checkpoint is roughly54GB before file/layout overhead;
three final methods plus original assets and an in-flight predecessor/replacement
can require roughly270GB for this ARC domain. Actual sizes and GPU peaks must be
measured; the code does not assume a particular GPU allocation.

## Outputs and source audit

`runs/spectrum_multidomain/arc3/<method>/round-N/` contains synthesis trajectories,
the unfiltered action corpus, fixed-reference calibration, model/training receipts,
per-game native recordings and `evaluation/summary.json`. Round0 is the unadapted
model under the identical evaluation wrapper. The separate reference-collection
folder preserves calibration failures. Public reporting excludes private seed and
credentials. `status` describes stored artifacts, not current process liveness.

Official sources inspected for this implementation:

- [SDK source at the pinned commit](https://github.com/arcprize/ARC-AGI/tree/f12822c4d550121c35a275008d964afbbed47d2f): `base.py`, `local_wrapper.py`, `models.py`, `scorecard.py`.
- [Engine source at the pinned commit](https://github.com/arcprize/ARCEngine/tree/b495c6acaf253c9681cd7b75c4299d352e9ce6f8).
- [Arcade API](https://docs.arcprize.org/toolkit/arc_agi), [environment wrapper](https://docs.arcprize.org/toolkit/environment_wrapper), [actions](https://docs.arcprize.org/actions), [recording schema](https://docs.arcprize.org/recordings).

Required Local acceptance is native API/import/model generation, deterministic
replay, exact scorecard persistence, token masking and a complete saved/reloaded
training step on real development trajectories, under the actual hardware budget.
No such runtime or scientific PASS is asserted by this Web source delivery.
