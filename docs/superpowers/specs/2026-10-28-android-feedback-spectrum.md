# Android feedback-calibrated SPECTRUM

User-authorized scope: one AndroidWorld / UI-Voyager experiment in a new SPECTRUM branch. One Qwen3-VL-4B-Instruct backbone, one training trajectory per arm, no temperature/seed sweep. Preserve all historical code/results. Implement native image-conditioned collection, LoRA training, evaluation and receipts; no SE-GA implementation.

Two primary arms: UI-Voyager-style native collection with success RFT and author-code GRSD; our independent native+spectral collection with feedback-only self-distillation, current-checkpoint feedback/anchor geometry, generation-only modulation and native checkpoint evaluation. RFT may be an explicit common initialization. Do not call a controlled reimplementation an exact reproduction of paper results.

Episode schema: episode_id, instance_id, task_name, goal, split (train/calibration/eval), policy (native/spectral), checkpoint, round, success (native task verifier), steps. Each step: index, messages (HF chat-format prompt with local image paths), response, response_token_ids, screenshot, action, feedback, done. Raw failed/malformed outputs are retained. Evaluation never supplies training or calibration information. Exact instances fixed in a private manifest.

Training example: messages, response, response_token_ids, feedback (for distillation), episode_id, instance_id, policy, split. Teacher reads feedback in prompt; original student prompt and continuation IDs remain unchanged. Stop-gradient teacher snapshot; response-only KL; no GRSD in our arm. Spectral samples supply evidence, never masquerade as native on-policy responses.

Main APIs planned: QwenPolicy(checkpoint, config); generate(messages)->dict; train_sft(checkpoint, examples, output_dir, config)->dict; train_feedback(checkpoint, examples, output_dir, config)->dict. Calibration receives QwenPolicy and reference/feedback examples and produces projection-name-to-operator mapping. Android collection receives manifest instances and a generate callback. All GPU/emulator claims require real receipts.
