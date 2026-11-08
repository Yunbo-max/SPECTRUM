

# SPD

## **Self-Policy Distillation via Capability-Selective Subspace Projection.**
<p align="center">
  <a href="https://arxiv.org/abs/2605.22675">
    <img src="https://img.shields.io/badge/Arxiv-Paper-olivegreen" alt="Arxiv Paper">
  </a>
</p>


![SPD process overview](assets/spd_process.png)

## Overeview
A language model can improve a targeted capability by:

1. finding a low-rank subspace of its own K/V activations that matters for *correctness*, using correctness-aligned CE;
2. projecting K/V activations onto that subspace during self-sampling;
3. fine-tuning on the resulting self-samples with plain cross-entropy.

**No teacher, no external verifier, no gold labels during fine-tuning.**

---

## TL;DR

```bash
# Install
pip install -r requirements.txt

# Run one task (e.g. code) on the default student:
MODEL=Qwen/Qwen2.5-0.5B-Instruct bash scripts/run_single.sh code
MODEL=Qwen/Qwen2.5-0.5B-Instruct bash scripts/run_single.sh math
MODEL=Qwen/Qwen2.5-0.5B-Instruct bash scripts/run_single.sh mmlu

# Reproduce the full main table (3 runs, ~5-7h on a single 24 GB GPU):
MODEL=Qwen/Qwen2.5-0.5B-Instruct bash scripts/reproduce_all.sh
```

Each run writes `results.json` to `results/<task>/` with four methods:
`baseline`, `inference_hooks`, `SSD`, `SPD`.

---

## Repository layout

```
.
├── ssd_subspace.py        # main pipeline (all 4 methods, all 3 tasks)
├── utils.py               # gradient collection, SVD, projection helpers
├── requirements.txt       # pip dependencies
├── scripts/
│   ├── run_single.sh      # run one task
│   └── reproduce_all.sh   # run all 3 tasks + summary table
└── examples/              # sample outputs (see below)


### Students used in the paper

| Model | Family | Params | fp16 weights | Peak VRAM (LoRA r=8) | `transformers` |
|---|---|---|---|---|---|
| **`Qwen/Qwen2.5-0.5B-Instruct`** *(default)* | Qwen2.5 | 0.5B | 1 GB | ~4 GB | ≥ 4.44 |
| **`Qwen/Qwen2.5-7B-Instruct`** | Qwen2.5 | 7B | 14 GB | ~28 GB | ≥ 4.44 |
| **`Qwen/Qwen2.5-14B-Instruct`** | Qwen2.5 | 14B | 28 GB | ~48–56 GB | ≥ 4.44 |
| **`Qwen/Qwen3-4B-Instruct-2507`** | Qwen3 | 4B | 8 GB | ~16–20 GB | ≥ 4.51 |
| **`Qwen/Qwen3-14B-Instruct-2507`** | Qwen3 | 14B | 28 GB | ~48–56 GB | ≥ 4.51 |
| **`Meta-Llama-3.1-8B-Instruct`** | Meta | 8B | 16 GB | ~32 GB | ≥ 4.51 |

Pick your student by setting `MODEL`:

```bash

MODEL=Qwen/Qwen2.5-0.5B-Instruct   bash scripts/reproduce_all.sh   
MODEL=Qwen/Qwen2.5-7B-Instruct     bash scripts/reproduce_all.sh   
MODEL=Qwen/Qwen2.5-14B-Instruct    bash scripts/reproduce_all.sh  
MODEL=Qwen/Qwen3-4B-Instruct-2507  bash scripts/reproduce_all.sh   
MODEL=Qwen/Qwen3-14B-Instruct-2507 bash scripts/reproduce_all.sh
MODEL=Meta-Llama-3.1-8B-Instruct   bash scripts/reproduce_all.sh 
```

---

## Quickstart — running one task

```bash
# Code: MBPP training , assertion-only CE for subspace, dual-eval (MBPP + CodeAlpaca)
bash scripts/run_single.sh code

# Math: GSM8K training, answer-only CE, dual-eval (GSM8K + SVAMP)
bash scripts/run_single.sh math

# MMLU: MMLU training , answer-only CE, dual-eval (MMLU + BBH)
bash scripts/run_single.sh mmlu
```

Override the student via the `MODEL` env var:

```bash
MODEL=Qwen/Qwen3-4B-Instruct-2507  bash scripts/run_single.sh math
MODEL=Qwen/Qwen3-14B-Instruct-2507 bash scripts/run_single.sh mmlu
```

---
If you find this project useful, please consider citing our work:
```bash
@article{hao2026self,
  title={Self-Policy Distillation via Capability-Selective Subspace Projection},
  author={Hao, Guangya and Shang, Yitong and Long, Yunbo and Zhao, Zhuokai and Liang, Hanxue},
  journal={arXiv preprint arXiv:2605.22675},
  year={2026}
}
```








## License

The code in this repository is released under MIT. Dataset licenses follow their respective sources on HuggingFace.
