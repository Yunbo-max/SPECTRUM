# Qwen-author MBPP evaluation completed; C/B02 reassessment

Completed on hn01 on 2026-10-18 UTC with the cached Qwen2.5-Coder-1.5B-Instruct checkpoint. Fresh generation used the Qwen-author pipeline; the historical 500 × 16 outputs were not relabeled or regenerated for the old custom endpoint.

| Preserved endpoint | Base tests | Base + extended tests |
|---|---:|---:|
| Author pipeline, raw | 267/378 (70.635%) | 230/378 (60.847%) |
| Author pipeline, upstream sanitized | 266/378 (70.370%) | 229/378 (60.582%) |
| Separate diagnostic sanitizer repair | 267/378 (70.635%) | 230/378 (60.847%) |

All scores come from the pinned EvalPlus evaluator. The diagnostic third row is a local sanitizer patch, not the official result. The joint endpoint requires both base and extended statuses to pass; extended-only status counts must not be substituted. Task-bootstrap 95% intervals for raw base and joint pass@1 are [66.14%, 75.13%] and [56.08%, 65.87%]. These intervals reflect resampling tasks, not training-seed uncertainty or an independent confirmation experiment. There is only one greedy sample per task, so this run does not measure pass@16 or solution diversity.

## Actual protocol and implementation

Qwen source: commit `33bc6aabd7791ad7b32f7e92104f11f2359ba890`, `qwencoder-eval/instruct/eval_plus/{test.sh,generate.py,model.py}`. This directory explicitly documents Qwen2.5-Coder evaluation. The script prepends an embedded EvalPlus path. Its gitlink is `899b2b31bbe8d6e12337b865a8aa03fcd57c1121`, while requirements name 0.2.1 and the existing environment contained 0.3.1. We populated the embedded path with the gitlink checkout and set PYTHONPATH explicitly. Recorded actual imports resolve data/sanitize/evaluate to that checkout. `python -m evalplus.sanitize` and the unmodified pinned `evalplus.evaluate.main` were used; no deleted custom scorer was restored.

The pinned loader selected MBPP+ v0.2.0, 378 tasks, 1,174 base inputs and 39,841 extended inputs. Dataset SHA256 is `b54e762755248ca411b523c917fa9f93c07b5ff2966bf60b3917b853926a3dad`. Model revision is `2e1fd397ee46e1388853d2af2c993145b0f1098a`. The author ChatML prefix requests Python code and supplies the EvalPlus prompt with a visible example assertion. Generation is greedy, n=1, BF16, TP=1, batch=1, requested max_tokens=2048, engine max_model_len=1536, with the author's stop strings. vLLM resolves repetition penalty to 1.0. The original 500-task run had T=.8, top-p=.95, n=16, 512-token completion limit and a different prompt. Only 224 IDs overlap; no overlapping prompt is byte-identical. Thus score differences are not a controlled extraction-only effect or a comparison to a published paper number.

Dependencies were adapted on the GPU host: Torch2.7.1 retained, vLLM0.10.0/Transformers4.53.3 installed via the Tsinghua mirror, and tree-sitter0.21.3/tree-sitter-languages1.10.2 supplied in a separate dependency directory for the pinned sanitizer. The author model.py was copied to a working directory: only GPU allocation .98→.80 and raw engine-output logging were added. The patch, environment before/after, actual sampling parameters, commands and source identities are retained. No claim of bit-identical reproduction on the authors' hardware is made.

Generation completed in 421.08 seconds, producing 34,730 tokens. There were 376 stop terminations and two length terminations (tasks119 and446); both capped outputs failed. Replacing only these outputs could improve either endpoint by at most 2/378 = 0.529 percentage points. This is an upper bound, not a measured longer-context gain. 377/378 raw files parsed as Python. Sanitization changed 32 files.

## Isolation and real execution failure

The unmodified evaluator ran in a chroot with a minimal read-only runtime, UID/GID61043, no host project/credential files, and seccomp blocking network, exec and escape-related operations. Its multiprocessing, original time limits and 4GiB per-generated-process memory guard remained intact. Evaluation parallelism was two. A live probe verified the filesystem/network boundary and shared-memory multiprocessing. Host user/network namespaces were unavailable.

The first raw evaluation failed while writing the trusted expected-output cache because the wrapper limited files to256MiB. No model score was emitted. The old wrapper, failed log, exit status and partial-cache hash are retained under `failures/file-limit-attempt1`; the partial cache remains on hn01. Raising only this outer file limit to4GiB allowed the unchanged evaluator to complete. The completed reference cache is792,816,418 bytes. Generation and sanitization were reused, not repeated. The final raw and sanitized stages exited0 at22:55:28 and22:56:56 UTC.

## A reproduced upstream sanitizer defect

Task635's raw `heap_sort` calls `heapify`, which mutates an array and intentionally has no return statement. The upstream sanitizer filters out every function without a return statement before computing dependency closure. It therefore deletes `heapify`. Raw code passes both endpoints; upstream-sanitized code fails the base tests. This is the only changed task outcome.

A separate minimal patch removes that function-node filter while retaining the upstream dependency closure and all other sanitization logic. The same378 raw outputs were sanitized again and scored through the unchanged isolated evaluator. Only task635's base outcome changed, restoring raw totals. The source diff, static reproduction, all generated inputs, results and process identity are in `sanitizer-helper-diagnostic/`. This establishes a concrete evaluator artifact, not a new model improvement. The original official raw/sanitized scores remain primary and immutable.

## Research decision and limitations

The old near-zero apparent capacity floor does not survive the qualified author protocol. Retain the historical custom2.325% endpoint as a format/protocol diagnostic, and reject using it as evidence for a weak model, a spectral mechanism, or a need to enlarge the model. The baseline here is neither near zero nor near perfect. No self-distillation effect has yet been measured in this continuation.

There are37 raw base-pass/extended-fail tasks. Their interpretation is mixed: task558's implementation indexes equal-length decimal strings and fails on unequal lengths; task781 uses an expensive linear divisor loop on a large integer. But task639's reference imposes lowercase suffixes on names although the prompt only describes the first letter, task113's reference returns None for an empty string while the model returns False, and task427's extended input does not follow the stated date format strictly. These examples are source-level case analyses, not a complete adjudication of all37 cases. Do not call every differential-test mismatch a substantive model reasoning failure.

A further data limitation: all112 extended inputs for task635 in this pinned release are the same empty list. That explains why deleting the helper changes its base status while its extended-only status still passes. The joint endpoint correctly rejects it. We preserve the dataset and do not silently repair or drop this task. Neither this observation nor the sanitizer fix supports a general indictment of EvalPlus.

Continue B/C with an actual strong self-distillation control: the released `apple/SimpleSD-4B-instruct` checkpoint and its actual `Qwen/Qwen3-4B-Instruct-2507` base, with author-recommended decoding and matched decoder/budget controls distinguished. This selection follows the scientific question, not the old cache or a forced7B choice. Primary-source refresh and mirror file manifests are retained. Direct Hugging Face access and hf-mirror failed from hn01; ModelScope metadata and file listing succeeded. Qwen mirror shard hashes match the official Hugging Face file pages. Apple mirror identity still needs equivalent cross-source checking; do not call that check complete. Author SSD source was retrieved as a codeload archive at commit2637d2021f1bc523385b48a1f88ea9aa4812b0a9 after the Git transport failed; archive and source hashes are recorded in ssd-source-resolution.json. Review its native LiveCodeBench data/protocol and actual4090 capacity before launching an inference comparison. MBPP results are exploratory and exposed; no D mechanism or E confirmation has been established.

Harness supervision remains active. This completed evaluation and follow-up diagnosis are milestones, not completion of SPECTRUM research. No runtime/scheduler change or new research worker was made.
