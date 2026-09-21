#!/usr/bin/env python3
"""把垂直题单（建筑 / 人像 / App·UI / 商品 / 游戏图标）的出图打包成可直接发人的图片交付物。

产出 deliver-vertical/：
  <size>/<model>/<题号>.jpg   —— 单图（长边 1440，q92）
  by-domain/<领域>.jpg        —— 每个领域一张：3 家 × 2 档分辨率并排
  prompts-vertical.json       —— 题面 + 评分点
"""
import os
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
OUT = ROOT / "deliver-vertical"
TILE = 300
LABEL_W = 330
# 领域名是中文，标题字体要带 CJK 字形，否则标签会渲染成方块：
#   PACK_FONT=/path/to/NotoSansCJK-Bold.ttc PACK_FONT_INDEX=0 python3 pack_vertical.py
FONT_PATH = os.environ.get("PACK_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FONT_INDEX = int(os.environ.get("PACK_FONT_INDEX", "0"))
FONT_S = ImageFont.truetype(FONT_PATH, 16, index=FONT_INDEX)
FONT = ImageFont.truetype(FONT_PATH, 20, index=FONT_INDEX)

ARMS = [("1024", "qwen"), ("1024", "sense"), ("1024", "flux"),
        ("2048", "qwen"), ("2048", "sense"), ("1536", "flux")]
COLS = ["qwen 1024", "sense 1024", "flux 1024", "qwen 2048", "sense 2048", "flux 1536"]


def load(path: Path, side: int = 1440) -> Image.Image:
    im = Image.open(path)
    if im.mode != "RGB":
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1] if im.mode == "RGBA" else None)
        im = bg
    if max(im.size) > side:
        r = side / max(im.size)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    return im


def main() -> None:
    prompts = json.load(open(ROOT / "prompts-vertical.json", encoding="utf-8"))
    if OUT.exists():
        for p in sorted(OUT.rglob("*"), reverse=True):
            p.rmdir() if p.is_dir() else p.unlink()
    OUT.mkdir(parents=True, exist_ok=True)

    n = 0
    for size, model in ARMS:
        src = ROOT / "out_vertical" / size / model
        if not src.is_dir():
            continue
        for f in sorted(src.glob("*.png")):
            dst = OUT / size / model
            dst.mkdir(parents=True, exist_ok=True)
            load(f).save(dst / f"{f.stem}.jpg", "JPEG", quality=92)
            n += 1
    print("singles", n)

    def g(size, model, pid):
        for ext in ("jpg", "png"):
            c = OUT / size / model / f"{pid}.{ext}"
            if c.exists():
                return c
        return None

    domains = []
    for p in prompts:
        if p["domain"] not in domains:
            domains.append(p["domain"])

    for dom in domains:
        ids = [p["id"] for p in prompts if p["domain"] == dom]
        w = LABEL_W + len(ARMS) * (TILE + 8)
        top = 68
        h = top + len(ids) * (TILE + 34)
        cv = Image.new("RGB", (w, h), (255, 255, 255))
        dr = ImageDraw.Draw(cv)
        dr.text((16, 12), f"{dom}  ({len(ids)} prompts)", fill=(17, 24, 39), font=FONT)
        for ci, cname in enumerate(COLS):
            dr.text((LABEL_W + ci * (TILE + 8) + 6, 40), cname, fill=(75, 85, 99), font=FONT_S)
        y = top
        for pid in ids:
            dr.text((16, y + 6), pid, fill=(17, 24, 39), font=FONT_S)
            for ci, (size, model) in enumerate(ARMS):
                x = LABEL_W + ci * (TILE + 8)
                p = g(size, model, pid)
                if p is None:
                    dr.rectangle([x, y, x + TILE, y + TILE], outline=(229, 231, 235), fill=(246, 248, 250))
                    dr.text((x + 10, y + TILE // 2), "(none)", fill=(156, 163, 175), font=FONT_S)
                    continue
                im = load(p, TILE)
                cv.paste(im, (x + (TILE - im.width) // 2, y + (TILE - im.height) // 2))
            y += TILE + 34
        name = next((p.get("domain_en") for p in prompts if p["domain"] == dom), dom)
        (OUT / "by-domain").mkdir(parents=True, exist_ok=True)
        cv.save(OUT / "by-domain" / f"{name}.jpg", "JPEG", quality=90)
        print("sheet", name, cv.size)

    shutil.copy2(ROOT / "prompts-vertical.json", OUT / "prompts-vertical.json")


if __name__ == "__main__":
    main()
