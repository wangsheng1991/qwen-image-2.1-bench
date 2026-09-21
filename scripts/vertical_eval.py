#!/usr/bin/env python3
"""垂直领域题单（建筑 / 人像 / App·UI / 商品 / 游戏图标）出图。

和公开评测集那轮一样的口径：题面固定、同 seed、逐题落盘 + 记时；
支持按模型各自的原生分辨率再跑一轮（Qwen/SenseNova 2048²，FLUX 1536）。

用法（250）：
  python3 vertical_eval.py --size 1024 --models qwen,sense
  python3 vertical_eval.py --size 2048 --models qwen,sense
"""
import os
import argparse, base64, json, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
PROMPTS = json.load(open(ROOT / "prompts-vertical.json", encoding="utf-8"))
SEED = 42


def post(url, payload, timeout=3600):
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


def run_qwen(p, size, out_dir):
    code, d, wall = post(QWEN_URL + "/v1/images/generations",
                         {"prompt": p["prompt"], "width": size, "height": size,
                          "steps": 20, "seed": SEED, "response_format": "url"})
    if code != 200:
        return {"ok": False, "wall_s": wall, "error": json.dumps(d, ensure_ascii=False)[:200]}
    out = out_dir / "qwen" / f"{p['id']}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(QWEN_URL + d["data"][0]["url"], timeout=180) as r:
        out.write_bytes(r.read())
    m = d.get("meta", {})
    return {"ok": True, "wall_s": wall, "backend_s": m.get("seconds"),
            "peak_gib": m.get("peak_gib"), "path": str(out)}


def run_sense(p, size, out_dir):
    code, d, wall = post(SENSE_URL + "/v1/images/generations",
                         {"prompt": p["prompt"], "size": f"{size}x{size}",
                          "steps": 8, "seed": SEED, "response_format": "b64_json"})
    if code != 200:
        return {"ok": False, "wall_s": wall, "error": json.dumps(d, ensure_ascii=False)[:200]}
    out = out_dir / "sense" / f"{p['id']}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
    return {"ok": True, "wall_s": wall, "path": str(out)}


RUNNERS = {"qwen": run_qwen, "sense": run_sense}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--models", default="qwen,sense")
    ap.add_argument("--only-missing", action="store_true")
    args = ap.parse_args()

    out_dir = ROOT / "out_vertical" / str(args.size)
    rows = []
    for model in args.models.split(","):
        fn = RUNNERS[model]
        for i, p in enumerate(PROMPTS, 1):
            if args.only_missing and (out_dir / model / f"{p['id']}.png").exists():
                continue
            r = fn(p, args.size, out_dir)
            print(f"[{model}] {i}/{len(PROMPTS)} {p['id']:26s} {'ok' if r['ok'] else 'FAIL'} {r['wall_s']}s"
                  f"{'' if r['ok'] else ' ' + r.get('error','')}", flush=True)
            rows.append({"id": p["id"], "domain": p["domain"], "model": model,
                         "size": args.size, **r})
            json.dump(rows, open(ROOT / f"results-vertical-{args.size}.json", "w"),
                      ensure_ascii=False, indent=1)
    print("done", len(rows), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
