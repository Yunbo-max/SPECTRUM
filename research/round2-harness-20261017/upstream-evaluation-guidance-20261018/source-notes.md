# MBPP upstream source inspection — no official evaluation completed

- Google MBPP author source: https://github.com/google-research/google-research/tree/master/mbpp . Inspected directory contains README.md, mbpp.jsonl, sanitized-mbpp.json. This provides data and the original protocol, not a runnable evaluator in that directory.
- Qwen model-author scripts: https://github.com/QwenLM/Qwen3-Coder/tree/33bc6aabd7791ad7b32f7e92104f11f2359ba890/qwencoder-eval/instruct/eval_plus . Local source: upstreams/Qwen3-Coder. README describes Qwen2.5-Coder evaluation; test.sh uses EvalPlus generation, sanitization and evaluation for MBPP and HumanEval.
- EvalPlus: https://github.com/evalplus/evalplus/tree/899b2b31bbe8d6e12337b865a8aa03fcd57c1121 . Local source: upstreams/evalplus, checked out at the Qwen embedded gitlink revision. Qwen requirements also names evalplus==0.2.1 (tag ae747121ca8e4bf52b432f75da15cf6ab8dee89a); resolve and report the actual imported implementation before executing, rather than silently mixing these versions.

The old custom run has 500 tasks × 16 outputs and project-specific generation and scoring. It is historical diagnostic evidence, not an official Qwen/EvalPlus reproduction. Determine compatibility with upstream task IDs, prompts and generation settings before reusing any output. Otherwise generate afresh. Preserve original results separately from upstream protocol results.

Current state: user pause; upstream code downloaded/read, no new official generation or evaluation launched. Select the applicable upstream protocol and adapt only necessary GPU/dependency execution settings after authorized resumption.
