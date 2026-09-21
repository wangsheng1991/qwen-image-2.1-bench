#!/usr/bin/env python3
"""LongText-Bench 打分的客观口径：OCR 出图里的文字，和题目要求逐字比。

指标两个：
  * 字符准确率 = 1 - 编辑距离/参考长度（把要求渲染的文本拼起来 vs OCR 出来的文本拼起来）
  * 命中率     = 拼接后做子串匹配，逐条判断「这条要求有没有被完整写对」
用法（本机）：PYTHONPATH=ocr-libs python3 -u ocr_score.py
"""
import os
import json, re, unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR

ROOT = Path(os.environ.get("BENCH_ROOT", Path(__file__).resolve().parent))

QWEN_URL = os.environ.get("QWEN_URL", "http://127.0.0.1:8500").rstrip("/")
SENSE_URL = os.environ.get("SENSE_URL", "http://127.0.0.1:8400").rstrip("/")
OCR = RapidOCR()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", "", s).strip()


def ocr(path: Path) -> str:
    res, _ = OCR(str(path))
    if not res:
        return ""
    # res: [[box, text, score], ...] 从上到下、从左到右已排序
    return " ".join(r[1] for r in res if float(r[2]) > 0.4)


def expected(prompt: dict) -> list[str]:
    t = prompt.get("expect_text")
    if isinstance(t, str):
        try:
            t = json.loads(t.replace("'", '"'))
        except Exception:  # noqa: BLE001
            t = [t]
    return t or []


def partial_ratio(needle: str, hay: str) -> float:
    """needle 在 hay 里最好的那段相似度（容忍 OCR 换行/顺序错、少量错字）。"""
    if not needle or not hay:
        return 0.0
    if needle in hay:
        return 1.0
    w = max(len(needle), int(len(needle) * 1.3))
    best = 0.0
    for i in range(0, max(1, len(hay) - w // 2), max(1, w // 4)):
        best = max(best, SequenceMatcher(None, needle, hay[i:i + w]).ratio())
    return best


def score(prompt: dict, path: Path) -> dict:
    got = ocr(path)
    want = expected(prompt)
    want_join, got_n = norm("".join(want)), norm(got)
    ratio = SequenceMatcher(None, want_join, got_n).ratio() if want_join else 0.0
    hits, ratios = [], []
    for w in want:
        r = partial_ratio(norm(w), got_n)
        ratios.append(round(r, 2))
        if r >= 0.85:
            hits.append(w)
    return {"id": prompt["id"], "chars_want": len(want_join), "chars_ocr": len(got_n),
            "char_acc": round(ratio, 3), "hits": len(hits), "total": len(want),
            "hit_rate": round(len(hits) / len(want), 3) if want else 0.0,
            "line_ratios": ratios, "ocr_head": got[:220]}


def main():
    prompts = {p["id"]: p for p in json.load(open(ROOT / "prompts.json", encoding="utf-8"))}
    rows = []
    for model in ("qwen", "sense", "flux"):
        for p in prompts.values():
            if p["source"] != "LongText-Bench" or (p.get("qwen_only") and model != "qwen"):
                continue
            path = ROOT / "out" / model / f"{p['id']}.png"
            if not path.exists():
                continue
            r = score(p, path)
            r["model"] = model
            rows.append(r)
            print(f"{model:6s} {r['id']:22s} 字符准确率 {r['char_acc']:.1%}  命中 {r['hits']}/{r['total']}", flush=True)
    json.dump(rows, open(ROOT / "ocr_scores.json", "w"), ensure_ascii=False, indent=1)
    print("\n== 汇总（LongText-Bench）")
    for model in ("qwen", "sense", "flux"):
        sel = [r for r in rows if r["model"] == model]
        if not sel:
            continue
        acc = sum(r["char_acc"] for r in sel) / len(sel)
        hit = sum(r["hits"] for r in sel) / max(1, sum(r["total"] for r in sel))
        print(f"{model:6s} 平均字符准确率 {acc:.1%}  文本命中率 {hit:.1%}  ({len(sel)} 题)")


if __name__ == "__main__":
    main()
