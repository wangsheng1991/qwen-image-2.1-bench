#!/usr/bin/env python3
"""把同一题各家出的图拼成一张对比图（左 qwen / 中 sense / 右 flux），供人眼与视觉模型判读。

用法（本机）：python3 mk_compare.py
输出：compare/<id>.jpg + compare/_all.jpg（总览）
"""
import os
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
OUT = ROOT / "compare"
MODELS = [("qwen", "Qwen-Image-2.1"), ("sense", "SenseNova-U1.5"), ("flux", "FLUX.2-klein-KV")]
TILE = 560
PAD = 12
LABEL = 26


def load(p: Path, size=TILE):
    im = Image.open(p).convert("RGB")
    im.thumbnail((size, size), Image.LANCZOS)
    return im


def sheet(pid: str, tag: str) -> Image.Image | None:
    tiles = []
    for key, name in MODELS:
        p = ROOT / "out" / key / f"{pid}.png"
        if p.exists():
            tiles.append((name, load(p)))
    if not tiles:
        return None
    w = sum(t.width for _, t in tiles) + PAD * (len(tiles) + 1)
    h = max(t.height for _, t in tiles) + LABEL + PAD * 2
    canvas = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(canvas)
    d.text((PAD, 6), f"{pid} — {tag}", fill="#111111")
    x = PAD
    for name, t in tiles:
        canvas.paste(t, (x, LABEL + PAD))
        d.text((x + 4, LABEL + PAD - 2), name, fill="#666666")
        x += t.width + PAD
    return canvas


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    prompts = json.load(open(ROOT / "prompts.json", encoding="utf-8"))
    made = []
    for p in prompts:
        im = sheet(p["id"], p["tag"])
        if im is None:
            continue
        path = OUT / f"{p['id']}.jpg"
        im.save(path, quality=88, optimize=True)
        made.append(im)
        print("->", path, im.size, flush=True)
    # 总览：把每题的对比图竖着拼起来
    if made:
        W = max(i.width for i in made)
        H = sum(i.height + 16 for i in made)
        allim = Image.new("RGB", (W, H), "white")
        y = 0
        for i in made:
            allim.paste(i, (0, y))
            y += i.height + 16
        allim.thumbnail((1500, 20000), Image.LANCZOS)
        allim.save(OUT / "_all.jpg", quality=86, optimize=True)
        print("->", OUT / "_all.jpg", allim.size, flush=True)


if __name__ == "__main__":
    main()
