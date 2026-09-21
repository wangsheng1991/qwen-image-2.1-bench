#!/usr/bin/env python3
"""FLUX.2-klein-9b-kv（线上同款 INT4 + nunchaku）跑同一份评测题单的文生图，用于三方对比。

注意：线上编辑服务只开了「编辑」接口（EditInput 里 image_ids 必填），所以 t2i 只能直跑管线；
这里跑的是**同一个 KV 权重**，4 步，其余和线上一致。

用法（容器内，CUDA_VISIBLE_DEVICES 指向空闲卡）：
  python flux_eval.py --size 1024 --min-free-gib 16
"""
import os
import argparse, json, pathlib, time

import torch

ROOT = pathlib.Path(os.environ.get("BENCH_ROOT", pathlib.Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
KV_ROOT = pathlib.Path(os.environ.get("FLUX_KV_ROOT", "models/klein-kv"))
KV_TF = KV_ROOT / "svdq-int4_r32-FLUX.2-klein-9b-kv-Nunchaku.safetensors"
TE_PATH = pathlib.Path(os.environ.get("FLUX_TE_PATH", "models/qwen3-int4/text.safetensors"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-free-gib", type=float, default=16.0)
    ap.add_argument("--ids", default="", help="逗号分隔的题号，只跑这些")
    ap.add_argument("--out", default="out/flux", help="输出子目录（相对 仓库根）")
    args = ap.parse_args()

    free_gib = torch.cuda.mem_get_info()[0] / 2**30
    print(f"GPU free {free_gib:.2f} GiB", flush=True)
    if free_gib < args.min_free_gib:
        print(f"ABORT: 空闲显存不足 {args.min_free_gib} GiB", flush=True)
        return 3

    from diffusers import Flux2KleinKVPipeline
    from nunchaku import NunchakuFlux2Transformer2DModel, NunchakuQwenEncoderModel
    import inspect
    print("call sig:", str(inspect.signature(Flux2KleinKVPipeline.__call__))[:300], flush=True)

    t0 = time.perf_counter()
    transformer = NunchakuFlux2Transformer2DModel.from_pretrained(str(KV_TF), torch_dtype=torch.bfloat16, device="cuda")
    text_encoder = NunchakuQwenEncoderModel.from_pretrained(str(TE_PATH), device="cuda", torch_dtype=torch.bfloat16)
    pipe = Flux2KleinKVPipeline.from_pretrained(str(KV_ROOT), transformer=transformer, text_encoder=text_encoder,
                                                torch_dtype=torch.bfloat16, local_files_only=True).to("cuda")
    print(f"loaded in {time.perf_counter()-t0:.1f}s", flush=True)

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    prompts = json.load(open(ROOT / "prompts.json", encoding="utf-8"))
    only = {s for s in args.ids.split(",") if s}
    results = []
    for i, p in enumerate(prompts, 1):
        if p.get("qwen_only") or (only and p["id"] not in only):
            continue
        path = out_dir / f"{p['id']}.png"
        gen = torch.Generator("cuda").manual_seed(args.seed)
        t = time.perf_counter()
        try:
            img = pipe(prompt=p["prompt"], width=args.size, height=args.size,
                       num_inference_steps=args.steps, generator=gen).images[0]
            img.save(path)
            ok, err, secs = True, None, round(time.perf_counter() - t, 2)
        except Exception as exc:  # noqa: BLE001
            ok, err, secs = False, f"{type(exc).__name__}: {exc}"[:200], round(time.perf_counter() - t, 2)
        print(f"[flux] {i}/{len(prompts)} {p['id']:26s} {'ok' if ok else 'FAIL'} {secs}s {err or ''}", flush=True)
        results.append({"id": p["id"], "model": "flux", "source": p["source"], "tag": p["tag"],
                        "ok": ok, "wall_s": secs, "error": err, "path": str(path) if ok else None})
        json.dump(results, open(ROOT / "results-flux.json", "w"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
