#!/usr/bin/env python3
"""公平口径复测：Qwen-Image-2.1 按官方配方（原生 2048² + 40 步）重打 4 道长文本题，
看「宣传 vs 实测」的差距有多少来自我们自己的低配置（1024²/20 步）。输出 out_fair/qwen/。"""
import os
import json, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
OUT = ROOT / "out_fair" / "qwen"
IDS = ["ltb-print-long-en", "ltb-poster-long-en", "ltb-slide-long-zh", "ltb-poster-long-zh"]
P = {p["id"]: p for p in json.load(open(ROOT / "prompts.json", encoding="utf-8"))}
OUT.mkdir(parents=True, exist_ok=True)
rows = []
for pid in IDS:
    body = json.dumps({"prompt": P[pid]["prompt"], "width": 2048, "height": 2048,
                       "steps": 40, "seed": 42, "response_format": "url"}).encode()
    req = urllib.request.Request(QWEN_URL + "/v1/images/generations", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=3600) as r:
            d = json.loads(r.read())
        with urllib.request.urlopen(QWEN_URL + d["data"][0]["url"], timeout=180) as r:
            (OUT / f"{pid}.png").write_bytes(r.read())
        print(f"{pid:22s} ok {d['meta']['seconds']}s peak {d['meta']['peak_gib']}G", flush=True)
        rows.append({"id": pid, "ok": True, "seconds": d["meta"]["seconds"], "peak": d["meta"]["peak_gib"]})
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:200]
        print(f"{pid:22s} FAIL {round(time.time()-t0,1)}s {msg}", flush=True)
        rows.append({"id": pid, "ok": False, "error": msg})
    json.dump(rows, open(ROOT / "results-fair.json", "w"), ensure_ascii=False, indent=1)
