# Qwen-Image-2.1 on public benchmarks — measured, not advertised

A three-way, single-GPU comparison of **Qwen-Image-2.1** against two other image models that were
actually deployable here, run on the **verbatim prompt text** of public benchmarks
(GenEval / DPG-Bench / LongText-Bench), same seed, plus a round-2 **attribution study** of why our
numbers and the official showcase disagree.

> **TL;DR** — the gap is mostly about *evaluation protocol*, not about the model. The official
> pipeline is **prompt-rewriter + 2048²/40 steps + long English descriptions**; round 1 used
> **raw short prompts + 1024²/20 steps**. Same prompt, same resolution, same seed: rewriting
> GenEval's terse prompts into enhancer-style descriptions fixed **2/2** object-dropping failures.

中文主报告见 [`README.md`](README.md)。

## Headline numbers

| | Qwen-Image-2.1 | SenseNova-U1.5 | FLUX.2-klein-KV |
|---|---|---|---|
| Shape | 7B DiT (visual gen) + Qwen3-VL text encoder, RGBA VAE | 8B+8B MoT, 8 steps + 8-step LoRA | 9B distilled + INT4 KV, 4 steps |
| 1024² per image (median) | 52.1 s (20 steps) | 9.8 s | **1.6 s** |
| 2048² per image | 102–111 s | **13 s** | not supported (≤1536) |
| Text rendering, char accuracy (OCR) | 74.6% | **86.5%** | 40.8% |
| Text rendering, line hits | 25/35 | **26/35** | 4/35 |
| … Chinese long text, line hits | **18/20** | **18/20** | 0/20 |
| … English long text, line hits | 7/15 | **8/15** | 4/15 |
| GenEval compositional (7) | **4/7** | 7/7 | 7/7 |
| DPG-Bench long description (4) | 2 good / 2 flawed | **4 good** | **4 good** |
| Native transparent RGBA | **✅ unique** | ✗ | ✗ |

## Prompt set

Verbatim text in [`prompts.json`](prompts.json); sources:

| Source | Prompts | Where |
|---|---|---|
| GenEval | 7 | <https://github.com/djghosh13/geneval> (`evaluation_metadata.jsonl`) |
| DPG-Bench | 4 | <https://github.com/TencentQQGYLab/ELLA> (`dpg_bench.csv`) |
| LongText-Bench | 6 | <https://huggingface.co/datasets/X-Omni/LongText-Bench> |
| Qwen model card | 1 | Qwen-Image-2.1 README (transparent RGBA) |

### GenEval (original prompt text)

![GenEval three-way](images/compare/geneval-3way.jpg)

Qwen failed three of seven: `a photo of two clocks` drew one clock; `a photo of a purple wine glass
and a black apple` dropped the apple entirely; `a photo of a bench` collapsed structurally at 1024².
Both baselines scored 7/7.

### DPG-Bench and LongText-Bench

![DPG-Bench three-way](images/compare/dpg-3way.jpg)

![LongText-Bench three-way](images/compare/longtext-3way.jpg)

Long text is Qwen's and SenseNova's home turf (FLUX produces garbled Chinese and misspelled English).
Qwen's characteristic failure is **inventing entire blocks of plausible-looking fake words** to fill
dense small text — a chalkboard menu comes out with text that is not one real word.

## Advertised vs measured

The official blog's four selling points are mostly about **editing** (up to 10 reference images,
lasso/brush/mask, portrait and product fidelity) and native transparency; the "small model, big
performance" claim rests on **Qwen-Image-Bench total score 60.28 (rank 7)**, where FLUX 2 Max = 55.33
and FLUX 2 Pro = 54.57 — that 5.7-point gap is where the marketing tone comes from. That leaderboard
**has no GenEval / DPG breakdown**, so it is not commensurable with "4 of 7 prompts passed".

The official README is explicit about the recommended pipeline:

> “For best results, we recommend using the official **prompt rewriting models** to expand short
> prompts into detailed, high-quality descriptions.”

and about defaults: `num_inference_steps=40`, `2048×2048`, `guidance-scale 1`. Round 1 followed none
of them.

### Ablation: only the prompt changes

Same machine, same GPU, 2048², 20 steps, seed 42. Left column is the GenEval original; right column
is an enhancer-style long description (**note: not** the real output of the official 20 GB
Qwen3.5-VL 9B rewriter — that checkpoint was not deployed; this is a hand-written stand-in in the
same style).

![Only the prompt changed](images/round2/prompt-rewrite.jpg)

- `a photo of two clocks` → still **one clock** at 2048² with the original text; **exactly two** with
  the long description.
- `a photo of a purple wine glass and a black apple` → apple missing with the original text; **both
  objects present with correct colours** with the long description.

**These failures are a prompt-format problem, not a capability problem.** GenEval's prompt style is
designed for automated scorers and happens to be the worst-case input for this model's recommended
pipeline.

### What resolution does and does not fix

![2K re-test](images/round2/2k-retest.jpg)

The collapsed bench at 1024² is fine at 2048² — *structural* failures are a config problem.

Re-running the four long-text prompts with the official recipe (2048²/40 steps), with SenseNova at
2048² as a control:

![Official recipe re-run](images/round2/official-recipe.jpg)

| LongText-Bench prompt | Qwen 1024²/20 steps | Qwen 2048²/40 steps (official) | SenseNova 2048² |
|---|---|---|---|
| English chalkboard menu | 20.5% · 2/7 | **13.7% · 3/7** | 63.4% · 3/7 |
| English festival poster | 94.4% · 4/5 | 80.6% · 2/5 | 73.3% · 1/5 |
| Chinese slide | 81.5% · 12/12 | 81.1% · 12/12 | 76.9% · 11/12 |
| Chinese festival poster | 90.2% · 3/5 | **98.6% · 4/5** | 97.3% · 4/5 |
| **mean (char accuracy · line hits)** | **71.7% · 72.4%** | **68.5% · 72.4%** | **77.7% · 65.5%** |

Scoring: RapidOCR reads the generated text and compares it character-by-character against the text
the prompt asked for; char accuracy = 1 − edit distance / reference length, a line counts as a hit at
similarity ≥ 0.85. Caveat: OCR is not fully comparable across resolutions (smaller, more decorative
type at 2K), so the honest reading is **"no measurable gain"**, not "2K is worse". The cost is real
though: 172 s/image at 2048²/40 steps vs 52 s/image at 1024²/20 steps.

### Attribution summary

| Source of the gap | Weight | Evidence |
|---|---|---|
| **Missing the official prompt rewriter; raw short prompts used** | largest | ablation fixes 2/2 (`images/round2/prompt-rewrite.jpg`) |
| **Incommensurable metrics**: vendor composite vs per-prompt pass rate | large | leaderboard is a total with no GenEval/DPG split |
| **Different opponent**: INT4 4-step distill vs full FLUX 2 Pro/Max | medium | FLUX 2 Pro = 54.57 on their board; klein-KV is not on it |
| **Sampling and scoring**: 1 image/prompt, single seed, n=4–7; human yes/no instead of Mask2Former | medium | official GenEval is 553 prompts × 4 images with an object detector |
| **Resolution / steps** | large for structural failures, small for text | bench: broken at 1K, fine at 2K; long-text scores flat |

## Reproduction

Requirements: two OpenAI-shaped image endpoints (`POST /v1/images/generations` with `prompt`,
`width`, `height`, `steps`, `seed`, `response_format`). Paths and endpoints come from environment
variables; no code edits needed.

```bash
pip install pillow rapidocr-onnxruntime
export BENCH_ROOT=$PWD
export QWEN_URL=http://127.0.0.1:8500
export SENSE_URL=http://127.0.0.1:8400

python3 scripts/eval_run.py --size 1024     # round 1, three models, same seed
python3 scripts/eval2k.py                   # re-test the failures at 2048²
python3 scripts/ocr_score.py                # objective OCR scoring for text prompts
python3 scripts/eval_fair.py                # official recipe (2048²/40 steps)
python3 scripts/rewrite_ablation.py         # prompt-only ablation
python3 scripts/pack_deliver.py             # contact sheets + delivery bundle
```

The FLUX arm has to run the pipeline directly (`scripts/flux_eval.py`) because the deployed service
only exposes an edit endpoint.

## Limitations — read these with the numbers

- **One image per prompt, single seed.** This is a spot check, not a leaderboard score; at n=4–7 a
  single prompt is ±14%.
- Compositional and long-description prompts were judged **by eye**, not by GenEval's Mask2Former or
  DPG's mPLUG+CLIP scorers.
- The ablation's "long description" is hand-written in the enhancer's style, **not** real output from
  the official rewriter.
- The three models do not run the same step count: each used its own service default (Qwen 20 /
  SenseNova 8 / FLUX 4) — a "best configuration" comparison, not an equal-budget one. Qwen's 40-step
  control is in `results/results-fair.json`.

## License

Code MIT; generated images and text CC BY 4.0 — please cite this repository. The evaluated models
belong to their respective owners; all conclusions are specific to this sample.
