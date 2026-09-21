# Qwen-Image-2.1 实测笔记

同机同卡同题面，把 Qwen-Image-2.1 拉来和 SenseNova-U1.5、4 步蒸馏的 FLUX.2-klein-KV 打了一轮。
这里放**分篇结论**；完整数据、题面和 231 张出图在[主报告](https://wangsheng1991.github.io/qwen-image-2.1-bench/)。

> 一句话结论：**公开榜单那轮的差距主要是口径问题，垂直领域这轮的差距主要是分工问题。**

## 为什么值得看

- 题面**一字未改**：公开榜单用原题面（GenEval / DPG-Bench / LongText-Bench / RGBA），垂直题面自建并公开
- 两档分辨率都跑：1024²（可横向比）与各家推荐档（Qwen / SenseNova 2048²、FLUX 1536）
- 文字题同一把尺子：RapidOCR 逐字比对 → 字符准确率 + 逐行命中
- 失败也说：每一处掉坑都留了原图，不挑好看的放

## 分篇

| 篇 | 讲什么 |
|---|---|
| [九个垂直领域，没有通吃的](vertical-nine-domains.md) | 建筑、人像、App·UI、动漫、漫画、绘本…各自的赢家与翻车点 |
| [差距是口径，不是模型](prompt-rewrite-ablation.md) | 只改题面不改模型，组合题成绩怎么翻过来的 |

## 数据在哪

- 题面：`prompts.json`（公开榜单）｜ `prompts-vertical.json`（自建 26 题，含判定项）
- 逐题耗时：`results/*.csv` ｜ 文字渲染评分：`results/*ocr*.json`
- 出图：`images/` ｜ 复现脚本：`scripts/`

![人像领域：三家 × 两档分辨率 × 四个题面](../images/vertical/by-domain/portrait.jpg)
