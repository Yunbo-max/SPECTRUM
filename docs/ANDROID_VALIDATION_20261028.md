# Android branch verification — 28 October 2026

Status: **CPU integration verified; native 4B/CUDA/emulator execution pending.**

## Executed checks

The final focused suite completed with **65 passed** in 10.99 seconds on a
separate Python 3.11.17 environment using the declared core versions:

| Package | Tested version |
|---|---|
| torch | 2.8.0+cpu |
| torchvision | 0.23.0+cpu |
| transformers | 4.57.1 |
| peft | 0.17.1 |
| accelerate | 1.10.1 |
| numpy | 1.26.3 |
| Pillow | 11.3.0 |
| OpenCV | 4.10.0.84 |
| scikit-image | 0.25.2 |
| android_env | 1.2.3 |

One nonfatal test diagnostic warns about converting a requires-grad tensor to a
Python scalar for an assertion; it is not a training exception or failed test.
An earlier exploratory environment also passed all 65 checks on torch2.15 CPU.
The declared-version environment initially contained residual files from two
NumPy installations; removing that isolated environment's conflicting NumPy
packages and reinstalling 1.26.3 resolved its six import-related failures.
The final reported run used a coherent single NumPy installation.

```bash
SPECTRUM_UI_VOYAGER_ROOT=/path/to/pinned/UI-Voyager \
SPECTRUM_ANDROID_PROCESSOR_PATH=/path/to/pinned/qwen3vl/processor-metadata \
python -m pytest tests/test_android_*.py -q
```

Tests use temporary tiny models and synthetic fixtures, not benchmark outputs.
The two optional environment variables enable actual author-code and actual
processor integrations; without their assets those checks skip explicitly.
The processor assets came from model revision
`ebb281ec70b05090aa6165b016eac8ec08e71b17` without downloading model weights.

Verified behaviors:

- Actual tiny native Qwen3-VL pixel-conditioned forward, language LoRA gradient,
  frozen base teacher, response-logit alignment, merged checkpoint and reload.
- Both SFT and feedback training entrypoints honor fixed optimizer-update budgets.
- Real pinned processor handles local screenshots, enforces the pixel budget,
  preserves token continuations across feedback prompt lengths, and persists
  image settings on save/reload. Tool-call delimiters survive decoding.
- PSD moment mixing, low-signal fallback, actual visual tensors influencing
  calibration, and exact K/V restoration on exceptional exits.
- Native-only student prefixes, same-instance evidence, evaluation exclusion,
  actual pinned UI-Voyager backward matcher using OpenCV/SSIM.
- Raw invalid actions, native verifier error propagation, private instance
  identities, tagged native parameter round-trip, partial-result preservation.
- Empty supervision yields explicit no_update rather than fabricated training;
  completed-stage source/config/image/checkpoint identities are checked.

## Native registry preparation without emulator

The pinned upstream repository `67b65e2be093753ecaa2964f48739339b870813e`
was imported with its real registry and random-parameter generators.
The default configuration produced:

```json
{
  "registered": 116,
  "counts": {"train": 32, "calibration": 16, "eval": 116},
  "all_native_constructors": "passed",
  "unique_instances": 164
}
```

All 164 instances reconstructed native task objects and nonempty goals after
serialization. This detected and fixed the need to encode native SQL dataclasses
and a PIL target image, rather than assuming every parameter is plain JSON.
The frozen manifest is authoritative: upstream MarkorCreateFolder uses wall-clock
time, so a seed alone does not guarantee an identical newly generated manifest.

## Independent review

An independent reviewer read the implementation and native Android APIs.
Four material findings were addressed: loading the inner operator mapping on
resume; explicit no-update rounds; referenced-image/checkpoint hashing; and an
enforced update budget with separate token/teacher/calibration cost reporting.
The full final focused suite above passed after integration.

Dependency resolution for `requirements/android.txt`, source compilation,
CLI `--help`/`plan`, and `git diff --check` also completed successfully.

## Not executed

- Full 4.4B model loading or training.
- CUDA peak-memory or throughput measurement, including RTX4090 fit.
- Real Android emulator interaction, app initialization or benchmark scoring.
- End-to-end common RFT or either recursive arm.

No Android success-rate result, multi-round improvement, or scientific PASS is
claimed. The `qualify` command and runbook supply native-host acceptance steps.
