#!/usr/bin/env python3
"""公平口径的另一半：SenseNova-U1.5 在同 4 道长文本题上按原生 2048² 重出，用于和
Qwen 的 2048²/40 步逐个对比（首轮 1024² 三方对打已经做过）。输出 out_fair/sense/。"""
import os
import base64, json, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
OUT = ROOT / "out_fair" / "sense"
IDS = ["ltb-print-long-en", "ltb-poster-long-en", "ltb-slide-long-zh", "ltb-poster-long-zh"]
P = {p["id"]: p for p in json.load(open(ROOT / "prompts.json", encoding="utf-8"))}
OUT.mkdir(parents=True, exist_ok=True)
rows = []
for pid in IDS:
    body = json.dumps({"prompt": P[pid]["prompt"], "size": "2048x2048", "steps": 8,
                       "seed": 42, "response_format": "b64_json"}).encode()
    req = urllib.request.Request(SENSE_URL + "/v1/images/generations", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            d = json.loads(r.read())
        (OUT / f"{pid}.png").write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
        print(f"{pid:22s} ok {round(time.time()-t0,1)}s", flush=True)
        rows.append({"id": pid, "ok": True, "wall_s": round(time.time() - t0, 1)})
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:200]
        print(f"{pid:22s} FAIL {msg}", flush=True)
        rows.append({"id": pid, "ok": False, "error": msg})
    json.dump(rows, open(ROOT / "results-fair-sense.json", "w"), ensure_ascii=False, indent=1)
