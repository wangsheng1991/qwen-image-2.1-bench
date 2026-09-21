#!/usr/bin/env python3
"""把 仓库根 下的公开评测集出图打包成「可直接发给人看」的图片交付物。

产出 deliver/：
  <组>/<模型>/<题号>.jpg        —— 单图（长边 1440，q92；只有透明题保留 PNG）
  compare/*.jpg                 —— 按 benchmark 分组的「三家同题并排」大图
  round2/*.jpg                  —— 第二轮证据图（2K 复测 / 官方配方 / 题面消融）
  prompts.json                  —— 题面原文（含公开来源）
"""
import os
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
OUT = ROOT / "deliver"
TILE = 340           # 并排图里单张缩略图的边长
LABEL_W = 360        # 左侧题号栏宽度
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
FONT_S = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)

GROUPS = {
    "1k-1024": {m: ROOT / "out" / m for m in ("qwen", "sense", "flux")},
    "2k-retest": {m: ROOT / "out2k" / m for m in ("qwen", "sense", "flux")},
    "official-recipe": {"qwen-2048-40step": ROOT / "out_fair" / "qwen",
                        "sense-2048": ROOT / "out_fair" / "sense"},
    "prompt-rewrite": {"": ROOT / "out_fair" / "rewritten"},
}


def load(path: Path, side: int = 1440) -> Image.Image:
    im = Image.open(path)
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    if max(im.size) > side:
        r = side / max(im.size)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    return im


def emit_singles() -> int:
    n = 0
    for group, models in GROUPS.items():
        for label, d in models.items():
            if not d.is_dir():
                continue
            for p in sorted(d.glob("*.png")):
                target = OUT / group / label
                target.mkdir(parents=True, exist_ok=True)
                name = p.stem
                if group == "prompt-rewrite":
                    src_id, _, arm = p.stem.partition(".")
                    name = f"{src_id}--{arm}"
                if p.stem == "bonus-rgba":  # 透明能力是这张图的全部意义，保留 PNG
                    shutil.copy2(p, target / f"{name}.png")
                else:
                    load(p).save(target / f"{name}.jpg", "JPEG", quality=92)
                n += 1
    return n


def sheet(rows, cols, out_path: Path, title: str) -> None:
    """rows: [(row_label, [图片路径 or None, ...]), ...]"""
    top = 68
    w = LABEL_W + len(cols) * (TILE + 8)
    h = top + len(rows) * (TILE + 34)
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    dr = ImageDraw.Draw(canvas)
    dr.text((16, 12), title, fill=(17, 24, 39), font=FONT)
    for ci, cname in enumerate(cols):
        dr.text((LABEL_W + ci * (TILE + 8) + 6, 40), cname, fill=(75, 85, 99), font=FONT_S)
    y = top
    for rlabel, paths in rows:
        dr.text((16, y + 6), rlabel, fill=(17, 24, 39), font=FONT_S)
        for ci, p in enumerate(paths):
            x = LABEL_W + ci * (TILE + 8)
            if p is None or not Path(p).exists():
                dr.rectangle([x, y, x + TILE, y + TILE], outline=(229, 231, 235), fill=(246, 248, 250))
                dr.text((x + 10, y + TILE // 2), "(缺图)", fill=(156, 163, 175), font=FONT_S)
                continue
            im = load(Path(p), TILE)
            canvas.paste(im, (x + (TILE - im.width) // 2, y + (TILE - im.height) // 2))
        y += TILE + 34
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "JPEG", quality=90)
    print("sheet", out_path.name, canvas.size)


def main() -> None:
    if OUT.exists():
        for p in sorted(OUT.rglob("*"), reverse=True):
            p.rmdir() if p.is_dir() else p.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    n = emit_singles()
    print("singles", n)

    def g(group, model, pid):
        for cand in (OUT / group / model / f"{pid}.jpg", OUT / group / model / f"{pid}.png"):
            if cand.exists():
                return cand
        return None

    def gr(group, name):
        for cand in (OUT / group / f"{name}.jpg", OUT / group / f"{name}.png"):
            if cand.exists():
                return cand
        return None

    GENE = ["geneval-counting-0", "geneval-counting-1", "geneval-colors-2", "geneval-position-3",
            "geneval-color_attr-4", "geneval-two_object-5", "geneval-single_object-6"]
    DPG = ["dpg-entity", "dpg-attribute", "dpg-relation", "dpg-global"]
    LTB = ["ltb-sign-short-en", "ltb-sign-short-zh", "ltb-print-long-en", "ltb-poster-long-en",
           "ltb-slide-long-zh", "ltb-poster-long-zh"]
    cols = ["qwen", "sense", "flux"]
    sz = "1024^2 / seed 42 / qwen 20 steps, sense 8, flux 4"

    sheet([(p, [g("1k-1024", m, p) for m in cols]) for p in GENE],
          cols, OUT / "compare/geneval-3way.jpg", f"GenEval (7 prompts, origin text) - {sz}")
    sheet([(p, [g("1k-1024", m, p) for m in cols]) for p in DPG],
          cols, OUT / "compare/dpg-3way.jpg", f"DPG-Bench (4 prompts, origin text) - {sz}")
    sheet([(p, [g("1k-1024", m, p) for m in cols]) for p in LTB],
          cols, OUT / "compare/longtext-3way.jpg", f"LongText-Bench (6 prompts, origin text) - {sz}")
    sheet([("bonus-rgba", [g("1k-1024", "qwen", "bonus-rgba"), None, None])],
          ["qwen (RGBA, unique)", "", ""], OUT / "compare/bonus-rgba.jpg",
          "Native transparent RGBA - Qwen only (alpha kept)")

    retest = ["geneval-single_object-6", "geneval-color_attr-4", "dpg-global"]
    sheet([(p, [g("1k-1024", "qwen", p), g("2k-retest", "qwen", p), g("2k-retest", "sense", p),
                g("2k-retest", "flux", p)]) for p in retest],
          ["qwen 1024 20step", "qwen 2048 20step", "sense 2048", "flux 1536"],
          OUT / "round2/2k-retest.jpg", "Re-test the 3 failures at 2K (same seed 42)")

    fair_ids = ["ltb-print-long-en", "ltb-poster-long-en", "ltb-slide-long-zh", "ltb-poster-long-zh"]
    sheet([(p, [g("1k-1024", "qwen", p), g("official-recipe", "qwen-2048-40step", p),
                g("official-recipe", "sense-2048", p)]) for p in fair_ids],
          ["qwen 1024/20step", "qwen 2048/40step (official recipe)", "sense 2048"],
          OUT / "round2/official-recipe.jpg",
          "Official recipe re-run on the 4 long-text prompts")

    sheet([("geneval-counting-0", [gr("prompt-rewrite", "geneval-counting-0--short"),
                                   gr("prompt-rewrite", "geneval-counting-0--rewritten")]),
           ("geneval-color_attr-4", [g("2k-retest", "qwen", "geneval-color_attr-4"),
                                     gr("prompt-rewrite", "geneval-color_attr-4--rewritten")])],
          ["GenEval origin text", "enhancer-style long description"],
          OUT / "round2/prompt-rewrite.jpg",
          "Only the prompt changed: origin text vs enhancer-style description (2048/20step, seed 42)")

    shutil.copy2(ROOT / "prompts.json", OUT / "prompts.json")


if __name__ == "__main__":
    main()
