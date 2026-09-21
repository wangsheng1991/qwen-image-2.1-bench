#!/usr/bin/env python3
"""把 slides/slides.md 转成**可编辑**的 .pptx。

Slidev 负责渲染成网页/PDF，本脚本负责出一份能直接改字的 PPT：
同一份 slides.md 是唯一源，两套导出不改内容。

用法：
    python scripts/make_deck.py                       # 默认读写 slides/
    python scripts/make_deck.py -i slides/slides.md -o slides/dist/deck.pptx
    python scripts/make_deck.py --font "Microsoft YaHei"

只需要 python-pptx（不依赖 PIL / LibreOffice / Slidev）。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Emu, Inches, Pt

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

INK = RGBColor(0x11, 0x18, 0x27)
INK_SOFT = RGBColor(0x4B, 0x55, 0x63)
MUTED = RGBColor(0x6B, 0x72, 0x80)
ACCENT = RGBColor(0x09, 0x69, 0xDA)
LINE = RGBColor(0xE5, 0xE7, 0xEB)
HEAD_BG = RGBColor(0xF3, 0xF4, 0xF6)

TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")


# --------------------------------------------------------------------------- 解析
def strip_front_matter(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                return "\n".join(lines[j + 1:])
    return text


def split_slides(text: str) -> list[list[str]]:
    """按 --- 切页；纯 key: value 的块是 Slidev 的单页 front matter，不算页。"""
    slides, cur = [], []
    for line in strip_front_matter(text).splitlines():
        if line.strip() == "---":
            slides.append(cur)
            cur = []
        else:
            cur.append(line)
    slides.append(cur)

    def is_front_matter(block: list[str]) -> bool:
        body = [l for l in block if l.strip()]
        return bool(body) and all(re.match(r"^[A-Za-z_][\w-]*\s*:.*$", l.strip()) for l in body)

    return [s for s in slides if any(l.strip() for l in s) and not is_front_matter(s)]


def clean_inline(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<(https?://[^>]+)>", r"\1", s)          # 自动链接先落成纯文本
    s = TAG_RE.sub("", s)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)          # 图注丢弃
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", s)
    s = s.replace("`", "")
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", s)
    return s.strip()


def parse_slide(lines: list[str]) -> dict:
    while lines and (not lines[0].strip() or re.match(r"^[A-Za-z_][\w-]*\s*:.*$", lines[0].strip())):
        lines = lines[1:]
    slide: dict = {"title": "", "kicker": [], "bullets": [], "table": [], "images": [], "footer": []}
    table: list[list[str]] = []
    in_div = False
    div_buf: list[str] = []
    divs: list[str] = []

    for raw in lines:
        line = raw.rstrip()
        low = line.strip().lower()
        if low.startswith("<div"):
            inner = re.sub(r"^<div[^>]*>", "", line, flags=re.I)
            if "</div>" in inner.lower():                      # 单行 <div>…</div>
                divs.append(clean_inline(re.sub(r"</div>.*$", "", inner, flags=re.I)))
                continue
            in_div, div_buf = True, ([inner.strip()] if inner.strip() else [])
            continue
        if in_div:
            if "</div>" in low:
                in_div = False
                tail = re.sub(r"</div>.*$", "", line, flags=re.I | re.S).strip()
                if tail:
                    div_buf.append(tail)
                divs.append(clean_inline(" ".join(div_buf)))
            else:
                div_buf.append(line.strip())
            continue

        if not line.strip():
            continue
        if line.lstrip().startswith("# "):
            slide["title"] = clean_inline(line.lstrip()[2:])
            continue
        m = re.match(r"\s*!\[([^\]]*)\]\(([^)]+)\)", line)
        if m:
            slide["images"].append((m.group(1), m.group(2).strip()))
            continue
        if line.lstrip().startswith("|"):
            cells = [clean_inline(c) for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c.strip()) for c in cells):
                continue
            table.append(cells)
            continue
        if re.match(r"\s*[-*]\s+", line):
            indent = (len(line) - len(line.lstrip())) // 2
            slide["bullets"].append((indent, clean_inline(re.sub(r"^\s*[-*]\s+", "", line))))
            continue
        slide["kicker"].append(clean_inline(line))

    if in_div and div_buf:                                     # 兜底：漏了 </div>
        divs.append(clean_inline(" ".join(div_buf)))

    if table:
        slide["table"] = table
    slide["footer"] = [d for d in divs if d]
    return slide


# --------------------------------------------------------------------------- 绘制
def add_textbox(slide, x, y, w, h, *, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    return box, tf


def set_font(run, *, size, bold=False, color=INK, font="PingFang SC"):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font
    # 东亚字形也要跟着走，否则整片中文回落到默认字体
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = rPr.makeelement(qn(tag), {})
            rPr.append(el)
        el.set("typeface", font)


def put_paragraphs(tf, items, *, size, color=INK, gap=6, first_clear=True, bullet=True):
    """items: [(indent, text)]；text 里的换行拆成独立段落。"""
    if first_clear:
        tf.clear()
    lines: list[tuple[int, str]] = []
    for indent, text in items:
        for k, seg in enumerate(text.split("\n")):
            lines.append((indent, seg.strip()) if k else (indent, seg))
    for i, (indent, text) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 and first_clear else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.level = min(indent, 4)
        mark = ("• " if indent == 0 else "– ") if bullet else ""
        run = p.add_run()
        run.text = mark + text
        set_font(run, size=size if indent == 0 else size - 1.5, color=color)
    return tf


def emit_table(slide, rows, x, y, w, *, size=13):
    n_rows, n_cols = len(rows), max(len(r) for r in rows)
    row_h = Inches(0.34)
    shape = slide.shapes.add_table(n_rows, n_cols, x, y, w, row_h * n_rows)
    tbl = shape.table
    tbl.first_row = True
    for r_i, row in enumerate(rows):
        for c_i in range(n_cols):
            cell = tbl.cell(r_i, c_i)
            cell.text = ""
            cell.margin_top = cell.margin_bottom = Emu(0)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if c_i == 0 or n_cols > 2 else PP_ALIGN.LEFT
            run = p.add_run()
            run.text = row[c_i] if c_i < len(row) else ""
            set_font(run, size=size if r_i or n_cols > 3 else size,
                     bold=(r_i == 0), color=INK if r_i else INK_SOFT)
            cell.fill.solid()
            cell.fill.fore_color.rgb = HEAD_BG if r_i == 0 else RGBColor(0xFF, 0xFF, 0xFF)
    return shape


def emit_images(slide, images, base_dir: Path, x, y, w, h):
    n = len(images)
    gap = Inches(0.3)
    cell_w = int((w - gap * (n - 1)) / n)
    for i, (_alt, src) in enumerate(images):
        path = (base_dir / src).resolve()
        if not path.exists():
            print(f"  ! 缺图 {src}", file=sys.stderr)
            continue
        pic = slide.shapes.add_picture(str(path), x + i * (cell_w + gap), y, width=cell_w)
        px_w, px_h = pic.image.size
        scale = cell_w / pic.width
        nat_h = int(px_h / px_w * pic.width)
        if nat_h * scale > h:  # 太高就按高度回缩
            pic.height = int(nat_h * (h / (nat_h * scale)))
            pic.width = int(pic.height * px_w / px_h)
        pic.top = y + int((h - pic.height) / 2)
        pic.left = x + i * (cell_w + gap) + int((cell_w - pic.width) / 2)


def blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def render(prs, slide_data, base_dir: Path, font: str, index: int):
    s = slide_data
    slide = blank_slide(prs)
    is_cover = index == 0

    if is_cover:
        _, tf = add_textbox(slide, Inches(0.9), Inches(2.0), Inches(11.5), Inches(1.6),
                            anchor=MSO_ANCHOR.BOTTOM)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = s["title"]
        set_font(r, size=40, bold=True, color=INK, font=font)
        y = Inches(3.75)
        for line in s["kicker"]:
            _, tf2 = add_textbox(slide, Inches(0.9), y, Inches(11.5), Inches(0.5))
            p2 = tf2.paragraphs[0]; p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run(); r2.text = line
            set_font(r2, size=16, color=INK_SOFT, font=font)
            y += Inches(0.42)
        for line in s["footer"]:
            _, tf3 = add_textbox(slide, Inches(0.9), Inches(6.4), Inches(11.5), Inches(0.6))
            p3 = tf3.paragraphs[0]; p3.alignment = PP_ALIGN.CENTER
            r3 = p3.add_run(); r3.text = line
            set_font(r3, size=12, color=MUTED, font=font)
        return slide

    # 标题
    _, tf = add_textbox(slide, Inches(0.8), Inches(0.45), Inches(11.7), Inches(0.9),
                        anchor=MSO_ANCHOR.MIDDLE)
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = s["title"]
    set_font(r, size=26, bold=True, color=ACCENT, font=font)
    bar = slide.shapes.add_shape(1, Inches(0.8), Inches(1.34), Inches(1.1), Pt(3))
    bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT; bar.line.fill.background()
    bar.shadow.inherit = False

    y = Inches(1.62)
    if s["kicker"]:
        _, tf_k = add_textbox(slide, Inches(0.8), y, Inches(11.7), Inches(0.5))
        put_paragraphs(tf_k, [(0, k) for k in s["kicker"]], size=17, color=INK, bullet=False)
        y += Inches(0.55) * max(1, len(s["kicker"]))

    has_img = bool(s["images"])
    bottom = Inches(7.5 - 0.95) if s["footer"] else Inches(7.5 - 0.45)

    # 没有列表/表格/图时，<div> 就是这一页的正文；否则 <div> 是小字脚注
    body_div = None
    if not (s["bullets"] or s["table"] or has_img) and s["footer"]:
        body_div, s["footer"] = s["footer"][0], s["footer"][1:]

    if s["table"]:
        emit_table(slide, s["table"], Inches(0.8), y, Inches(11.7), size=13)
        y += Inches(0.34) * len(s["table"]) + Inches(0.25)

    if body_div:
        _, tf_v = add_textbox(slide, Inches(0.8), y, Inches(11.7), bottom - y)
        put_paragraphs(tf_v, [(0, p) for p in body_div.split("\n")], size=18, gap=14, bullet=False)
        y = bottom
    elif s["bullets"]:
        width = Inches(11.7) if not has_img else Inches(6.6)
        _, tf_b = add_textbox(slide, Inches(0.8), y, width, bottom - y)
        put_paragraphs(tf_b, s["bullets"], size=17, gap=8)
        if not has_img:
            y = bottom

    if has_img:
        img_w = Inches(11.7) if not s["bullets"] else Inches(4.7)
        img_x = Inches(0.8) if not s["bullets"] else Inches(7.6)
        emit_images(slide, s["images"], base_dir, img_x, y, img_w, bottom - y)

    if s["footer"]:
        _, tf_f = add_textbox(slide, Inches(0.8), Inches(6.72), Inches(11.7), Inches(0.6))
        put_paragraphs(tf_f, [(0, f) for f in s["footer"]], size=11.5, color=MUTED, gap=2, bullet=False)
    return slide


# --------------------------------------------------------------------------- main
def main() -> int:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", default=str(here / "slides" / "slides.md"))
    ap.add_argument("-o", "--output", default=str(here / "slides" / "dist" / "qwen-image-2.1-deck.pptx"))
    ap.add_argument("--font", default="PingFang SC", help="中文正文字体（默认 macOS 自带 PingFang SC）")
    args = ap.parse_args()

    src, out = Path(args.input), Path(args.output)
    if not src.exists():
        print(f"找不到 {src}", file=sys.stderr)
        return 1

    slides = [parse_slide(lines) for lines in split_slides(src.read_text(encoding="utf-8"))]
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H

    for i, s in enumerate(slides):
        render(prs, s, src.parent, args.font, i)

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    print(f"{len(slides)} 页 -> {out}  ({out.stat().st_size / 1024:.0f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
