#!/usr/bin/env python3
"""在本机跑评测题单：qwen-image-2.1（8500）与 sensenova-u1.5（8400）各出一张，落盘 + 记时。

用法：python3 -u eval_run.py [--only qwen|sense] [--size 1024]
"""
from __future__ import annotations

import argparse, base64, json, os, threading, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
PROMPTS = json.load(open(ROOT / "prompts.json", encoding="utf-8"))
LOCK = threading.Lock()
RESULTS: list[dict] = []


def post(url: str, payload: dict, timeout: int = 1800):
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
            body = {"error": "unreadable"}
        return e.code, body, round(time.time() - t0, 1)


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def run_qwen(prompt: dict, size: int, seed: int) -> dict:
    code, d, wall = post(QWEN_URL + "/v1/images/generations",
                         {"prompt": prompt["prompt"], "width": size, "height": size,
                          "steps": 20, "seed": seed, "response_format": "url"})
    if code != 200:
        return {"ok": False, "code": code, "error": json.dumps(d, ensure_ascii=False)[:200], "wall_s": wall}
    out = ROOT / "out" / "qwen" / f"{prompt['id']}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(fetch(QWEN_URL + d["data"][0]["url"]))
    m = d.get("meta", {})
    return {"ok": True, "code": code, "wall_s": wall, "backend_s": m.get("seconds"),
            "peak_gib": m.get("peak_gib"), "path": str(out), "bytes": out.stat().st_size}


def run_sense(prompt: dict, size: int, seed: int) -> dict:
    code, d, wall = post(SENSE_URL + "/v1/images/generations",
                         {"prompt": prompt["prompt"], "size": f"{size}x{size}",
                          "steps": 8, "seed": seed, "response_format": "b64_json"})
    if code != 200:
        return {"ok": False, "code": code, "error": json.dumps(d, ensure_ascii=False)[:200], "wall_s": wall}
    out = ROOT / "out" / "sense" / f"{prompt['id']}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
    return {"ok": True, "code": code, "wall_s": wall, "size": d["data"][0].get("size"),
            "path": str(out), "bytes": out.stat().st_size}


RUNNERS = {"qwen": run_qwen, "sense": run_sense}


def work(model: str, size: int, seed: int, only_missing: bool = False):
    fn = RUNNERS[model]
    for i, p in enumerate(PROMPTS, 1):
        if p.get("qwen_only") and model != "qwen":
            continue
        if only_missing and (ROOT / "out" / model / f"{p['id']}.png").exists():
            continue
        r = fn(p, size, seed)
        row = {"id": p["id"], "model": model, "source": p["source"], "tag": p["tag"], **r}
        with LOCK:
            RESULTS.append(row)
            print(f"[{model}] {i}/{len(PROMPTS)} {p['id']:26s} {'ok' if r['ok'] else 'FAIL'} "
                  f"{r['wall_s']}s {('backend ' + str(r.get('backend_s')) + 's') if r.get('backend_s') else ''}"
                  f"{'' if r['ok'] else ' ' + r.get('error', '')}", flush=True)
            json.dump(RESULTS, open(ROOT / "results.json", "w"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="both")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--only-missing", action="store_true", help="已出过的题跳过（断点续跑）")
    a = ap.parse_args()
    models = ["qwen", "sense"] if a.only == "both" else [a.only]
    print(f"prompts={len(PROMPTS)} size={a.size} seed={a.seed} models={models} "
          f"only_missing={a.only_missing}", flush=True)
    ths = [threading.Thread(target=work, args=(m, a.size, a.seed, a.only_missing)) for m in models]
    t0 = time.time()
    [t.start() for t in ths]
    [t.join() for t in ths]
    ok = sum(1 for r in RESULTS if r["ok"])
    print(f"\n完成 {ok}/{len(RESULTS)} 张，用时 {round(time.time()-t0,1)}s", flush=True)


if __name__ == "__main__":
    main()
