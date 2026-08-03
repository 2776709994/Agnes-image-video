---
name: agnes-ai
description: 调用 Agnes AI（国内版 API）生成图像和视频的 skill。当用户要求生成图片/图像/海报/插画，或对已有图片进行编辑/风格迁移/多图合成，或生成视频/动画片段时使用。图像模型 agnes-image-2.1-flash（文生图，高信息密度）与 agnes-image-2.0-flash（图生图/多图合成，编辑能力强），视频模型 agnes-video-v2.0（文生视频/图生视频/关键帧动画）。按场景默认推荐模型，用户点名时直接用指定模型。详细使用指南见 README.md。
---

# Agnes AI — 图像与视频生成（国内版 API）

## 概述

Agnes AI 提供 OpenAI 兼容协议的图像与视频生成 HTTP API。当用户想用 Agnes 生成图像或视频时使用本 skill。

* **API Base URL**: `https://api.agnes-ai.cn/v1`（国内版，**不要使用**国际版 apihub.agnes-ai.com，国内网络调不通）
* **认证**: `Authorization: Bearer <api_key>`
* **官方文档**: https://www.agnes-ai.cn/zh-Hans/docs/overview
* **API Key 获取**: https://platform.agnes-ai.cn/ （登录后进入 API Key 页面创建）

## API Key

脚本按以下顺序自动解析 key，任一位置存在即可：

1. 环境变量 `AGNES_API_KEY`
2. 文件 `~/.agnes-ai/api_key`
3. 本 skill 内嵌的 `scripts/api_key`（如果存在）

如果三个位置都没有 key，**停下来向用户索要**，并指引到 https://platform.agnes-ai.cn/ 获取。绝不把 key 打印到任何输出里。

## 模型选择（默认推荐 + 用户可覆盖）

**规则：用户点名了模型就用用户指定的；否则按场景给默认推荐。**

| 场景 | 默认推荐模型 | 说明 |
| --- | --- | --- |
| 文生图 | `agnes-image-2.1-flash` | 升级版，高信息密度、复杂构图；尺寸用 1K/2K/3K/4K 档位 + ratio |
| 图生图 / 图像编辑 / 多图合成 | `agnes-image-2.0-flash` | 图像编辑能力强（Artificial Analysis 编辑榜 ELO 1184）；尺寸用 1024x768 这类精确写法 |
| 文生视频 / 图生视频 / 关键帧动画 | `agnes-video-v2.0` | 异步任务 API，脚本自动轮询 |

用户说"用 2.1 做图生图"或"换 2.0 试试"等明确指定时，通过 `--model` 传给脚本即可，不要纠正用户。

## 使用方法

统一通过 `scripts/generate.py` 调用（Python 3，仅用标准库，无第三方依赖）：

```bash
# 文生图（默认 agnes-image-2.1-flash，推荐档位尺寸 + 宽高比）
python3 scripts/generate.py image \
  --prompt "<prompt>" \
  --size "2K" --ratio "16:9" \
  --output "<output_path.png>"

# 图生图 / 图像编辑（默认 agnes-image-2.0-flash）
python3 scripts/generate.py image \
  --prompt "<编辑指令>" \
  --image "<输入图片路径或URL>" \
  --size "1024x768" \
  --output "<output_path.png>"

# 多图合成（默认 agnes-image-2.0-flash）
python3 scripts/generate.py image \
  --prompt "<合成指令>" \
  --image "url_or_path_1" "url_or_path_2" \
  --size "1024x1024" \
  --output "<output_path.png>"

# 用户指定模型时
python3 scripts/generate.py image --prompt "..." --model "agnes-image-2.1-flash" --image "in.png" --size "2K" --output "out.png"

# 文生视频（默认 agnes-video-v2.0，自动轮询直到完成）
python3 scripts/generate.py video \
  --prompt "<prompt>" \
  --duration 5 \
  --output "<output_path.mp4>"

# 图生视频
python3 scripts/generate.py video \
  --prompt "<prompt>" \
  --image "<输入图片路径或URL>" \
  --duration 5 \
  --output "<output_path.mp4>"
```

本地图片作为输入时，脚本会自动编码为 Data URI 上传，无需手动处理。

## 国内网络注意（实测结论，2026-08）

* 图像响应里的 `url` 指向 `storage.googleapis.com`，国内**无法下载**。脚本已强制使用 Base64 输出（文生图 `return_base64: true`，图生图 `extra_body.response_format: "b64_json"`），不要改回 url 模式
* 视频结果 URL 托管在 `platform-outputs.agnes-ai.space`，部分国内网络同样无法直连；若下载失败，把 `metadata.url` 给用户并说明需自行下载（或换网络环境）

## 图像尺寸（重要）

`agnes-image-2.1-flash` 推荐使用**档位式 size + ratio**，输出可预期：

| ratio | 1K | 2K | 3K | 4K |
| --- | --- | --- | --- | --- |
| 1:1 | 1024x1024 | 2048x2048 | 3072x3072 | 4096x4096 |
| 16:9 | 1312x736 | 2624x1472 | 3936x2208 | 5248x2944 |
| 9:16 | 736x1312 | 1472x2624 | 2208x3936 | 2944x5248 |
| 4:3 / 3:4 | 1152x864 / 864x1152 | 2304x1728 / 1728x2304 | … | … |

* 支持的 ratio：`1:1`、`3:4`、`4:3`、`16:9`、`9:16`、`2:3`、`3:2`、`21:9`（默认 1:1）
* 想要 1920x1080 这类显示器尺寸时：请求 `size=2K, ratio=16:9`（得 2624x1472）再下游裁剪
* `agnes-image-2.0-flash` 用精确尺寸写法，如 `1024x1024`、`1024x768`、`768x1024`
* **不要**在请求顶层放 `response_format`，也**不要**传 `tags: ["img2img"]`（官方明确禁止，脚本已处理好）

## 视频参数（重要）

* 时长由 `num_frames / frame_rate` 决定，脚本用 `--duration` 自动换算（遵循 **8n+1 规则**，上限 441 帧）
  * ~3 秒：81 帧 @24fps ｜ ~5 秒：121 帧 ｜ ~10 秒：241 帧 ｜ ~18 秒（上限）：441 帧
* 分辨率默认 1152x768，服务端会自动映射到 480p/720p/1080p 标准档位
* 可用 `--negative-prompt` 排除不想要的内容，`--seed` 复现结果
* 视频生成是异步的，脚本自动轮询（最长约 10 分钟），优先用脚本而不是手写 curl
* 免费用户视频 RPM 极低（约 1-2 RPM），生成慢是正常现象，不要反复重试

## Prompt 建议结构

```
[主体] + [场景/环境] + [风格] + [光照] + [构图] + [质量要求]
```

图生图/图生视频时，同时描述**要改变什么**和**要保留什么**。

更多 API 细节（视频关键帧模式、错误码、RPM 限制）见 `references/api.md`；面向使用者的完整指南见 `README.md`。

## 生成之后

1. 告诉用户文件保存路径，并把文件交付给用户（调用 present_files）
2. 图像：能预览就内联预览；视频：提供查看/下载方式

## 错误处理

| 状态码 | 含义与处理 |
| --- | --- |
| 401 | key 无效 → 检查 key 配置 |
| 429 | 触发 RPM 限制 → 等一分钟重试，不要密集重发 |
| 400 | 参数错误 → 检查 size/ratio/num_frames 是否合法 |
| 503 | 服务繁忙 → 稍后重试 |

仍失败则把错误信息如实告诉用户，建议检查 Agnes AI 控制台（余额、配额）。
