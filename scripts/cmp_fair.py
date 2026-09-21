#!/usr/bin/env python3
"""对比同一批题在「我们的服务默认 1024²/20 步」与「官方配方 2048²/40 步」下的客观文字指标。

用法（本机）：PYTHONPATH=ocr-libs python3 -u cmp_fair.py
"""
import os
import json, sys
from pathlib import Path

sys.path.insert(0, "仓库根")
from ocr_score import score  # noqa: E402

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
IDS = ["ltb-print-long-en", "ltb-poster-long-en", "ltb-slide-long-zh", "ltb-poster-long-zh"]
P = {p["id"]: p for p in json.load(open(ROOT / "prompts.json", encoding="utf-8"))}

rows = []
print(f"{'题':24s} {'口径':16s} {'字符准确率':>8s} {'逐行命中':>8s}")
for pid in IDS:
    for label, path in (("1024²/20步", ROOT / "out" / "qwen" / f"{pid}.png"),
                        ("2048²/40步", ROOT / "out_fair" / "qwen" / f"{pid}.png"),
                        ("SenseNova 2048²", ROOT / "out_fair" / "sense" / f"{pid}.png")):
        if not path.exists():
            print(f"{pid:24s} {label:16s} {'(缺图)':>8s}")
            continue
        r = score(P[pid], path)
        r.update({"id": pid, "arm": label})
        rows.append(r)
        print(f"{pid:24s} {label:16s} {r['char_acc']:>7.1%} {r['hits']}/{r['total']}")
    print()

for arm in ("1024²/20步", "2048²/40步"):
    sel = [r for r in rows if r["arm"] == arm]
    if not sel:
        continue
    acc = sum(r["char_acc"] for r in sel) / len(sel)
    hit = sum(r["hits"] for r in sel) / max(1, sum(r["total"] for r in sel))
    print(f"汇总 {arm}: 平均字符准确率 {acc:.1%}  逐行命中率 {hit:.1%} ({len(sel)} 题)")

json.dump(rows, open(ROOT / "ocr_compare_fair.json", "w"), ensure_ascii=False, indent=1)
