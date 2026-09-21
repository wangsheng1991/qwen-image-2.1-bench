# 九个垂直领域，没有通吃的

<div style="color:#6b7280;font-size:14px;margin:-8px 0 20px">2026-09-21 · 26 道自建题 · 156 张出图 · 单 seed 抽样</div>

公开榜单的题面偏「学术」，跟实际接单要出的东西差得远。所以另起了一套自建题面：**9 个领域、26 道题、每题写明考点与判定项**，
三家（Qwen-Image-2.1 / SenseNova-U1.5 / FLUX.2-klein-KV）在同机同卡上各出 6 张（两档分辨率 × 3 次），一共 156 张。

## 结论表

| 领域 | 推荐 | 一句话 |
|---|---|---|
| 建筑·外景 | 三家都能用 | SenseNova / FLUX 会往玻璃幕墙上写幻觉招牌 |
| 建筑·室内 | **SenseNova** | 空间与灯光层次最稳 |
| 人像 | **SenseNova**（特写） | 老人特写的皮肤细节差距最大 |
| App·UI | **SenseNova** | 只有它 1024² 就把中文界面写对（文字命中 97.9%） |
| 商品·电商 | 三家都可用 | 白底图与场景图都能交付 |
| 游戏·图标 | **Qwen**（单个） | 12 个成套图标三家全崩 |
| 动漫·二次元 | Qwen / SenseNova | 中文海报两家全对，FLUX 乱码 |
| 漫画·分镜 | **SenseNova** | 只有它把台词放进对应画格 |
| 插画·绘本 | **SenseNova** | 水墨那题 Qwen 两档都太淡 |

## 掉坑点：Qwen 的四种失败模式

- **1024² 的 UI 稿会缩成小块**并留幽灵重影（2048² 才恢复，文字命中 5/12 → 11/12）
- **四格漫画台词串格**：四句都写出来了（逐句命中 4/4），但配到了错的画格、还夹乱码（字符准确率 34.8%）
- **国风水墨两档都太淡**：留白过头，山体几乎看不见
- **成套多元素崩**：12 个线性图标，数量、线宽、风格都不统一

反过来，Qwen 也有两项独占优势：**原生透明 RGBA**（另两家都不支持）、**中文海报标题排版满分**。

## 看几张

![建筑外景](../images/vertical/by-domain/architecture-exterior.jpg)

![人像](../images/vertical/by-domain/portrait.jpg)

![App·UI](../images/vertical/by-domain/app-ui.jpg)

## 一句话怎么用

- 要出**效果图 / 人像 / UI 稿 / 漫画分镜** → SenseNova
- 要出**番剧海报的大标题**、或要**透明背景 PNG** → Qwen
- 要**成套且严格一致的多元素** → 三家都别指望，老老实实后期对齐

<small>数据：`results/results-vertical-timings.csv`（156 行全 ok）、`results-vertical-ocr.json`（8 道文字题）｜
题面：`prompts-vertical.json`</small>
