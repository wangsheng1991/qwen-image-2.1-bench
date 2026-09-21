#!/usr/bin/env python3
"""2K 复测：Qwen 的两次翻车（长椅、紫酒杯+黑苹果）与一张长描述，抬到原生 2048² 再看。

FLUX klein 线上上限 1536，所以它按 1536 出。输出到 out2k/<model>/。
"""
import os
import base64, json, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
IDS = ["geneval-single_object-6", "geneval-color_attr-4", "dpg-global"]
P = {p["id"]: p for p in json.load(open(ROOT / "prompts.json", encoding="utf-8"))}


def post(url, payload, timeout=1800):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read()), round(time.time() - t0, 1)
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:  # noqa: BLE001
            body = {}
        return e.code, body, round(time.time() - t0, 1)


def save(url, path, out):
    with urllib.request.urlopen(url, timeout=180) as r:
        out.write_bytes(r.read())


rows = []
for pid in IDS:
    prompt = P[pid]["prompt"]
    # Qwen 2048²
    out = ROOT / "out2k" / "qwen" / f"{pid}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    code, d, wall = post(QWEN_URL + "/v1/images/generations",
                         {"prompt": prompt, "width": 2048, "height": 2048, "steps": 20, "seed": 42,
                          "response_format": "url"})
    if code == 200:
        save(QWEN_URL + d["data"][0]["url"], None, out)
        print(f"qwen  {pid:24s} 2048² ok {d['meta']['seconds']}s peak {d['meta']['peak_gib']}G", flush=True)
    else:
        print(f"qwen  {pid:24s} 2048² FAIL {json.dumps(d, ensure_ascii=False)[:150]}", flush=True)
    rows.append({"id": pid, "model": "qwen", "size": 2048, "ok": code == 200, "wall_s": wall})
    # SenseNova 2048²
    out = ROOT / "out2k" / "sense" / f"{pid}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    code, d, wall = post(SENSE_URL + "/v1/images/generations",
                         {"prompt": prompt, "size": "2048x2048", "steps": 8, "seed": 42,
                          "response_format": "b64_json"})
    if code == 200:
        out.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
        print(f"sense {pid:24s} 2048² ok {wall}s", flush=True)
    else:
        print(f"sense {pid:24s} 2048² FAIL {json.dumps(d, ensure_ascii=False)[:150]}", flush=True)
    rows.append({"id": pid, "model": "sense", "size": 2048, "ok": code == 200, "wall_s": wall})
json.dump(rows, open(ROOT / "results-2k.json", "w"), ensure_ascii=False, indent=1)
