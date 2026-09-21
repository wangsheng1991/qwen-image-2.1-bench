#!/usr/bin/env python3
"""消融：把 GenEval 的「短题面」改写成官方增强器风格的长描述，看丢物体类失败是否消失。

背景：官方 README 明说 t2i 要配 `prompt_rewrite/`（微调的 Qwen3.5-VL 9B）把短请求扩写成
成品图描述；GenEval 的题面形如 "a photo of two clocks"，正是它要扩写的那种短请求。
本脚本只改「提示词」这一个变量（同为 2048²/20 步/seed 42），对比：
  * geneval-counting-0       短题面 vs 改写题面
  * geneval-color_attr-4     只有改写题面（它的 2048²/20 步短题面已在 out2k/qwen/）
输出 out_fair/rewritten/。
"""
import os
import json, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
OUT = ROOT / "out_fair" / "rewritten"
OUT.mkdir(parents=True, exist_ok=True)
P = {p["id"]: p for p in json.load(open(ROOT / "prompts.json", encoding="utf-8"))}

# 改写风格对齐官方增强器：一句成品图描述，把每个物体、属性和位置都写实、写足
REWRITTEN = {
    "geneval-counting-0": (
        "A realistic photograph of two antique analog clocks placed side by side on a polished "
        "wooden desk, both clocks fully inside the frame and clearly separated, each clock has "
        "its own round dial, hour and minute hands and printed numerals, soft window daylight "
        "from the left, shallow depth of field, 50mm lens, muted warm tones. Exactly two clocks."
    ),
    "geneval-color_attr-4": (
        "A still-life photograph on a rustic wooden table with two objects side by side on the "
        "left a translucent purple stemmed wine glass, empty and clean, and right beside it a "
        "matte black apple with a short green stem, both objects fully inside the frame and "
        "clearly separated, soft directional daylight, gentle contact shadows, shallow depth of "
        "field, 50mm lens. Exactly one purple wine glass and one black apple."
    ),
}

jobs = [("geneval-counting-0", "short", P["geneval-counting-0"]["prompt"]),
        ("geneval-counting-0", "rewritten", REWRITTEN["geneval-counting-0"]),
        ("geneval-color_attr-4", "rewritten", REWRITTEN["geneval-color_attr-4"])]

rows = []
for pid, arm, prompt in jobs:
    body = json.dumps({"prompt": prompt, "width": 2048, "height": 2048, "steps": 20,
                       "seed": 42, "response_format": "url"}).encode()
    req = urllib.request.Request(QWEN_URL + "/v1/images/generations", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=3600) as r:
            d = json.loads(r.read())
        with urllib.request.urlopen(QWEN_URL + d["data"][0]["url"], timeout=180) as r:
            (OUT / f"{pid}.{arm}.png").write_bytes(r.read())
        print(f"{pid:24s} {arm:10s} ok {d['meta']['seconds']}s peak {d['meta']['peak_gib']}G", flush=True)
        rows.append({"id": pid, "arm": arm, "prompt": prompt, "ok": True,
                     "seconds": d["meta"]["seconds"], "peak": d["meta"]["peak_gib"]})
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:200]
        print(f"{pid:24s} {arm:10s} FAIL {round(time.time()-t0,1)}s {msg}", flush=True)
        rows.append({"id": pid, "arm": arm, "prompt": prompt, "ok": False, "error": msg})
    json.dump(rows, open(ROOT / "results-rewritten.json", "w"), ensure_ascii=False, indent=1)
