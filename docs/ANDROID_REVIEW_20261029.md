# Android branch code review — 29 October 2026

Status: **82 CPU tests passed; full 4B/CUDA/emulator execution remains pending.**
This review follows the [initial validation](ANDROID_VALIDATION_20261028.md).
It changes neither the experiment configuration nor historical data/results.

## Confirmed issues and fixes

1. **Teacher feedback mixed coordinate systems and action vocabularies.**
   Successful paths were rendered from native Android commands: a model click
   at `[999,999]` on a 1080×2400 screen became `x=1079,y=2399` without identifying
   the pixel units, and action names differed from `mobile_use`. Feedback now
   preserves and labels the original sampled model response. The regression
   failed before the fix and passes afterward.
2. **A fresh emulator lacked the accessibility forwarder prerequisite.**
   The pinned UI-Voyager controller passes `install_a11y_forwarding_app=False`
   while immediately starting accessibility services. `setup-env` now installs
   the exact dated upstream APK before creating the native environment. It
   checks the configured device, content hash, installation result and package
   presence. Native code still enables services; ordinary collection never
   downloads or installs an APK. Three new setup regressions failed before the
   fix; all four setup cases pass afterward. These are interface tests, not an
   actual emulator installation.
3. **Acquired model files were checked by size only at load time.**
   A same-size replacement passed resolution despite a recorded SHA256. The
   loader now checks that hash before use. The replacement regression was
   reproduced before the fix and is rejected afterward.
4. **The complete instance manifest was not validated when loaded.**
   Individual collection validated instance identities, but did not establish
   cross-split disjointness. Both formal training and qualification now validate
   the full manifest hash, schema, upstream revision, semantic instance IDs,
   split uniqueness and task-selection metadata before checkpoint resolution.
   Changing only initialization seeds cannot hide a repeated semantic instance.

The existing frozen native manifest remains compatible: **164 instances**, with
32 training, 16 calibration and 116 evaluation instances across 116 registered
task templates. No manifest was regenerated for this check.

## Executed verification

The complete Android suite ran on the declared Python3.11/core dependency stack:

```text
82 passed, 1 warning in 10.90s
```

The warning is the pre-existing test assertion converting a gradient-bearing
tensor to a Python scalar; no training error was reported.

```bash
SPECTRUM_UI_VOYAGER_ROOT=/path/to/pinned/UI-Voyager \
SPECTRUM_ANDROID_PROCESSOR_PATH=/path/to/pinned/qwen3vl/processor-metadata \
python -m pytest tests/test_android_*.py -q
```

Both optional actual-asset integrations were enabled: pinned author GRSD code
and the actual Qwen3-VL processor/tokenizer metadata. Source compilation, CLI
`plan`, and `git diff --check` also passed.

An additional CPU probe exercised a tiny native Qwen3-VL with **BF16 + SDPA**:
all four selected K/V anchor/feedback moments were finite and nonzero; folded
forward remained finite; original weights were restored bit-exactly; language
LoRA with non-reentrant checkpointing and reverse-KL backpropagation had finite
loss and gradients. This does not measure the full model's GPU memory needs.

The accessibility APK was actually downloaded and hashed for the pin:

- Native artifact: `2024.05.13-accessibility_forwarder.apk`
- Size: 4,490,495 bytes
- SHA256: `97a56a544e44d79f9b3181fc7dbdd72cffa908efd3d53c82afad1773061a350a`

An independent reviewer checked the fixes and their regression tests. No further
blocking defect was identified in that review.

## Mathematical implementation audit

The implemented loss remains student-to-frozen-teacher reverse KL, with exact
sampled continuation IDs and response-token alignment. Visual inputs are retained.
The teacher's LoRA adapter is disabled and its logits are detached. Feedback and
reference gradient moments are recalculated at the current checkpoint; spectral
operators are temporary generation-only K/V transformations. No GRSD or GRPO loss
was added to our arm. No change to these mathematical mechanisms was needed.

## Remaining native validation

Full Qwen3-VL-4B loading/training, CUDA and RTX4090 capacity, actual emulator setup
and interaction, and end-to-end recursive benchmark results have not been run.
The review does not establish improved task success or multi-round stability.
Existing sealed runs must retain their recorded source/config identity; this
source revision must not be substituted into an already sealed experiment.
