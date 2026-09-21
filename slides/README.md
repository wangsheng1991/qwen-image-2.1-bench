# 演示稿（Slidev）

`slides.md` 是唯一源文件，12 页中文。用 [Slidev](https://sli.dev) 出网页 / PDF / PPTX / 逐页 PNG。

`dist/` 里是已经出好的成品（提交进仓库，直接下载用）：

| 文件 | 用途 |
|---|---|
| `dist/qwen-image-2.1-deck.pptx` | **图片版 PPT**（每页是渲染好的图）——对外发、直接放映，样式最准 |
| `dist/qwen-image-2.1-deck-editable.pptx` | **可编辑 PPT**（原生形状 + 文字）——对方要改字时用 |
| `dist/png/*.png` | 逐页 PNG（1960×1104，2× 缩放）——公众号 / 小红书 / PPT 里嵌图 |
| `dist/qwen-image-2.1-deck-text.pptx` | 离线兜底版（`scripts/make_deck.py` 生成，本仓库未提交，见下） |

## 怎么重新出稿

**方式一：Slidev（推荐，样式最准）**

```bash
cd <一个装了 node 的目录>
npm i -D @slidev/cli @slidev/theme-default playwright-chromium   # 首次
npx slidev export slides/slides.md --format pptx          --output dist/qwen-image-2.1-deck.pptx
npx slidev export slides/slides.md --format pptx-editable --output dist/qwen-image-2.1-deck-editable.pptx
npx slidev export slides/slides.md --format png --scale 2 --output dist/png
```

两个**必须**知道的坑（都实测踩过）：

1. **图片路径**：Slidev 的站点根目录是 `slides.md` 所在目录，所以 md 里写的 `../images/xxx.jpg`
   会被当成站点绝对路径 `/images/xxx.jpg` → 404，页面里图片全是破图。
   解法：在 `slides.md` 旁边放一个软链接 `images` 指向仓库的 `images/`：

   ```bash
   ln -s ../images slides/images      # 只在本地/CI 的工作目录里做，不必提交
   ```

2. **中文字体**：Linux 上不装 CJK 字体，所有中文会渲染成方块（tofu）。
   `apt-get install -y fonts-noto-cjk` 即可（本次在 GPU 机上就是这么修的）。

> 本次实际是在一台带 node 的 Linux 机上跑的（macOS 本机装 Slidev 依赖时反复
> `ERR_SSL_WRONG_VERSION_NUMBER`）。流程：把 `slides/slides.md` + 用到的 `images/` 传过去 → 装依赖 → 导出 → 取回。

**方式二：离线兜底（不需要 npm / 浏览器）**

```bash
python scripts/make_deck.py        # -> slides/dist/qwen-image-2.1-deck-text.pptx
```

纯 `python-pptx` 排版：全部文字可编辑、16:9、字号较大，但版式和 Slidev 出的不一样（要自己重排样式）。
依赖：`pip install python-pptx`。

## 版式备注

- 图文页用 `layout: two-cols`（标题在左列上方）或 `layout: two-cols-header`（标题+导语横跨顶部）
- 图片用 `<img style="max-height:60vh">` 这类内联样式限高，否则长图会被裁掉下半截
- 块级 `<div>` 后面**留一个空行**，里面的 markdown（列表、加粗）才会被解析
