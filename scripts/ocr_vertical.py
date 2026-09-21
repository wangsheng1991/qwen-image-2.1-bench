#!/usr/bin/env python3
"""垂直题单里「带文字」的那些题（App·UI 4 道 + 商品 1 道）的客观打分：OCR 逐字比对。

沿用公开评测集那轮的同一把尺子（ocr_score.py 的 score()），这样两轮数字可以直接并排看。

用法：PYTHONPATH=ocr-libs python3 -u ocr_vertical.py
"""
import os
import json, sys
from pathlib import Path

sys.path.insert(0, "仓库根")
from ocr_score import score  # noqa: E402

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
P = {p["id"]: p for p in json.load(open(ROOT / "prompts-vertical.json", encoding="utf-8"))}
TEXTED = [pid for pid, p in P.items() if p.get("expect_text")]

rows = []
for size_dir in sorted((ROOT / "out_vertical").glob("*")):
    for model_dir in sorted(p for p in size_dir.iterdir() if p.is_dir()):
        for pid in TEXTED:
            img = model_dir / f"{pid}.png"
            if not img.exists():
                continue
            r = score(P[pid], img)
            r.update({"size": size_dir.name, "model": model_dir.name})
            rows.append(r)
            print(f"{size_dir.name:>5} {model_dir.name:6s} {pid:22s} 字符 {r['char_acc']:>6.1%}  "
                  f"命中 {r['hits']}/{r['total']}", flush=True)

print("\n== 汇总（只算带文字的题）")
for size in sorted({r["size"] for r in rows}, key=int):
    for model in sorted({r["model"] for r in rows}):
        sel = [r for r in rows if r["size"] == size and r["model"] == model]
        if not sel:
            continue
        acc = sum(r["char_acc"] for r in sel) / len(sel)
        hit = sum(r["hits"] for r in sel) / max(1, sum(r["total"] for r in sel))
        print(f"{size:>5} {model:6s} 平均字符准确率 {acc:>6.1%}  逐条命中率 {hit:>6.1%}  ({len(sel)} 题)")

json.dump(rows, open(ROOT / "results-vertical-ocr.json", "w"), ensure_ascii=False, indent=1)
