# Android Feedback SPECTRUM Implementation Plan

**Goal:** Deliver one runnable AndroidWorld study and UI-Voyager comparison on a new branch.
**Architecture:** Isolated `improving.android` package, pinned upstream environment/fork algorithm, native Qwen3-VL image processor, temporary K/V generation intervention and response-level self-distillation. CLI owns sealed manifests and complete round receipts.
**Tech Stack:** Python, PyTorch, Transformers Qwen3-VL, PEFT, AndroidWorld, author UI-Voyager fork extraction.
**Spec:** docs/superpowers/specs/2026-10-28-android-feedback-spectrum.md

## Constraints and review focus
- No changes to existing data/results or legacy runtime requirements.
- Match continuation token positions across different teacher/student prompt lengths; preserve all visual processor fields.
- Use real task verifier, retain malformed output, isolate training/calibration/evaluation instances.
- Restore K/V exactly on exceptions; reject wrapped projections during folding.
- Teacher is detached and fixed within an update; native prefixes only for KL.
- Runtime unavailable is reported as unverified, never synthetic success.

## Tasks
- [x] Native Android collection/action mapping and manifest preparation; test malformed actions and verifier failure propagation.
- [x] Visual model/LoRA/KL stack; test shifted logits, teacher detachment, sparse KL and masked SFT.
- [x] Feedback/anchor geometry; test PSD mixture, zero fallback, fold restoration.
- [x] Raw records, feedback building, author GRSD adapter; test split isolation and same-instance evidence.
- [x] CLI/configuration/acquisition/round orchestration; test dry-run and resume identity.
- [x] Focused CPU tests and independent branch review; document GPU/emulator qualification commands.
- [ ] Publish dedicated branch with expected-head lease and read back commit.

User explicitly requested implementation and branch publication after method discussion; execution proceeds without another approval gate. Parallel implementation is used for independent files, followed by integration review.
